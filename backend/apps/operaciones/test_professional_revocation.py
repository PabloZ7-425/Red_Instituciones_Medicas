"""AUC-10: persisted native catalog state revokes clinical writes across sessions."""
import os
import time
import uuid
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import AccesoDenegado
from apps.identidad.models import PerfilInstitucional, Profesional
from apps.operaciones.repository import OperationsRepository


@skipUnless(os.getenv('OPERATIONS_REAL_TESTS') == '1', 'requires disposable four-engine runner')
class NativeRevocationTests(TestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{'POSTGRES_DB':'hospital_auc','MYSQL_DB':'pediatrico_auc'})
        self.environment.start();self.addCleanup(self.environment.stop)

    def client_for(self, institution, role, professional=None):
        user=get_user_model().objects.create_user('AUC10-'+uuid.uuid4().hex,password='Sample-AUC10-Password-2026!')
        profile=PerfilInstitucional.objects.create(usuario=user,institucion=institution,rol=role,profesional=professional)
        client=APIClient();client.force_login(user)
        session=client.session;session['clinical_authenticated_at']=time.time();session.save()
        return client,user,profile

    def exercise(self,institution):
        tag='AUC10-'+uuid.uuid4().hex[:12]
        admin=OperationsRepository(ContextoClinico(institution,'setup','admin'))
        if admin.sql:
            fields={'nombre':tag}
            if admin.hospital:fields['nivel_complejidad']=1
            specialty=admin.save('especialidad',fields)['id']
            data=({'id_especialidad':specialty,'nombre_completo':tag,'colegiado':tag,'habilitado':True} if admin.hospital else
                  {'especialidad_id':specialty,'nombre':tag,'apellido':'DEMO','colegiado':tag,'estado':'activo'})
            name='medico'
        else:
            name='profesional';data={'nombre':tag,'colegiado':tag,'habilitado':True,'activo':True}
        record=admin.save(name,data)
        reference=str(admin.internal(name,record['id']))
        mirror=Profesional.objects.create(institucion=institution,referencia_externa=reference,habilitado=True)
        physician,user,profile=self.client_for(institution,'medico',mirror)
        manager,_,_=self.client_for(institution,'admin')
        repo=OperationsRepository(ContextoClinico(institution,str(user.pk),'medico',reference))
        patient=repo.core.registrar_paciente({'identificacion':tag,'nombres':'DEMO','apellidos':tag,'fecha_nacimiento':'2000-01-01'})['id']
        url=f'/api/pacientes/{patient}/consultas/'
        payload={'fecha':'2020-01-01','notas_evolucion':'DEMO AUC10'}
        response=physician.post(url,payload,format='json')
        self.assertEqual(response.status_code,201,response.data)
        session_key=physician.session.session_key
        def edit(values):
            current=next(r for r in admin.page(name,limit=100)['results'] if r['id']==record['id'])
            response=manager.patch(f"/api/operaciones/{name}/{record['id']}/",{'values':values,'version':current['version']},format='json')
            self.assertEqual(response.status_code,200,response.data)
        flags=({'habilitado':False} if admin.hospital else {'estado':'inactivo'} if admin.sql else {'habilitado':False})
        edit(flags)
        mirror.refresh_from_db();self.assertTrue(mirror.habilitado,'Native eligibility cannot rely on mirror synchronization')
        self.assertEqual(physician.post(url,payload,format='json').status_code,403)
        self.assertEqual(physician.session.session_key,session_key)
        self.assertEqual(physician.get('/api/auth/me/').status_code,200)
        with self.assertRaises(AccesoDenegado):repo.core.registrar_consulta(patient,payload)
        # A new login cannot restore native eligibility either.
        fresh=APIClient()
        response=fresh.post('/api/auth/login/',{'username':user.username,'password':'Sample-AUC10-Password-2026!'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(fresh.post(url,payload,format='json').status_code,403)
        edit({'habilitado':True} if admin.hospital or not admin.sql else {'estado':'activo'})
        self.assertEqual(physician.post(url,payload,format='json').status_code,201)
        if not admin.sql:
            edit({'activo':False})
            self.assertEqual(physician.post(url,payload,format='json').status_code,403)
            edit({'activo':True})
        # B2 remains an additional gate even when the native catalog is active.
        mirror.habilitado=False;mirror.save(update_fields=['habilitado'])
        self.assertEqual(physician.post(url,payload,format='json').status_code,403)

    def test_hospital(self):self.exercise('hospital')
    def test_pediatrics(self):self.exercise('pediatrico')
    def test_laboratory(self):self.exercise('laboratorio')
    def test_dentistry(self):self.exercise('odontologica')
