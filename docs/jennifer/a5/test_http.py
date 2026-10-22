"""Real HTTP/session/native persistence checks against the disposable A5 stack."""
import json
import os
from pathlib import Path
import sys
import unittest

import requests

ROOT = Path(os.environ.get('A5_RUNTIME', '/workspace/work/a5-runtime')).resolve()
BASE = 'http://127.0.0.1:18005/api'
ORIGIN = 'http://127.0.0.1:18173'
PASSWORD = 'DEMO-only-isolated-A5-2026'
INSTITUTIONS = ('hospital', 'pediatrico', 'laboratorio', 'odontologica')
PATIENT = {'identificacion':'DEMO-A5-HTTP','nombres':'Persona HTTP','apellidos':'Sintética','fecha_nacimiento':'2000-01-01'}
CONSULTATION = {'fecha':'2026-10-20','notas_evolucion':'DEMO HTTP A5'}


class RealHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('A5_REAL_HTTP') != '1' or ROOT.name!='a5-runtime' or ROOT.parent.name!='work':
            raise RuntimeError('A5 requiere activación y work/a5-runtime dedicado')
        env=json.loads((ROOT/'server.json').read_text())
        if env.get('MONGO_URI')!='mongodb://127.0.0.1:27039/laboratorio?replicaSet=a5' or env.get('FIREBASE_PROJECT_ID')!='demo-jennifer-a5':
            raise RuntimeError('Configuración fuera de A5')
        sys.path[:0]=[str(ROOT),str(ROOT/'backend')]
        os.environ.update(env)
        import django
        django.setup()
        cls.admins={}
        cls.histories={}
        from apps.historiales.domain.context import ContextoClinico
        from apps.historiales.infrastructure.factory import AdapterFactory
        cls.repos={name:AdapterFactory.create_clinical(ContextoClinico(name,'DEMO-A5-probe','admin','1')) for name in INSTITUTIONS}
        for institution in INSTITUTIONS:
            client,token=cls.login(institution,'admin')
            cls.admins[institution]=(client,token)
            page=client.get(BASE+'/pacientes/?q=DEMO-A5-BROWSER',timeout=10)
            assert page.status_code==200 and page.json()['count']==1, 'Ejecutar primero navegador real A5'
            patient=page.json()['results'][0]
            response=client.get(BASE+f"/pacientes/{patient['id']}/historial/",timeout=10)
            assert response.status_code==200
            cls.histories[institution]=response.json()

    @classmethod
    def tearDownClass(cls):
        for client,token in cls.admins.values():
            client.post(BASE+'/auth/logout/',json={},headers={'X-CSRFToken':token,'Origin':ORIGIN},timeout=10)
            client.close()

    @classmethod
    def login(cls,institution,role):
        client=requests.Session()
        initial=client.get(BASE+'/auth/csrf/',timeout=10)
        assert initial.status_code==200
        response=client.post(BASE+'/auth/login/',json={'username':f'DEMO-A5-{role}-{institution}','password':PASSWORD},headers={'X-CSRFToken':initial.json()['csrfToken'],'Origin':ORIGIN},timeout=10)
        assert response.status_code==200, 'Fallo login DEMO A5'
        token=client.get(BASE+'/auth/csrf/',timeout=10).json()['csrfToken']
        return client,token

    def send(self,institution,method,path,body):
        client,token=self.admins[institution]
        return client.request(method,BASE+path,json=body,headers={'X-CSRFToken':token,'Origin':ORIGIN},timeout=15)

    def error(self,response,status):
        self.assertEqual(response.status_code,status)
        self.assertEqual(set(response.json()),{'error'})
        self.assertEqual(set(response.json()['error']),{'code','message','fields'})
        self.assertIsInstance(response.json()['error']['fields'],dict)
        self.assertIn('no-store',response.headers.get('Cache-Control',''))
        self.assertNotIn('Traceback',response.text)

    def test_browser_writes_are_persisted_in_all_four_native_repositories(self):
        for institution,history in self.histories.items():
            with self.subTest(institution=institution):
                self.assertEqual(history['paciente']['estado'],'archivado')
                self.assertEqual(history['paciente']['motivo_archivo'],'DEMO archivo A5')
                self.assertEqual(len(history['consultas']),1)
                diagnosis=history['consultas'][0]['diagnosticos']
                self.assertEqual(len(diagnosis),1)
                self.assertEqual(len(diagnosis[0]['tratamientos']),1)
                prescription=diagnosis[0]['tratamientos'][0]['recetas']
                self.assertEqual(len(prescription),1)
                self.assertIsNone(prescription[0]['via_administracion'])
                self.assertEqual(self.repos[institution].obtener_historial(history['paciente']['id']),history)

    def test_archive_is_idempotent_and_rejects_all_later_child_writes(self):
        for institution,h in self.histories.items():
            p=h['paciente'];c=h['consultas'][0];d=c['diagnosticos'][0];t=d['tratamientos'][0]
            with self.subTest(institution=institution):
                response=self.send(institution,'PATCH',f"/pacientes/{p['id']}/estado/",{'estado':'archivado','motivo':'DEMO archivo A5'})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.json(),p)
                self.error(self.send(institution,'PATCH',f"/pacientes/{p['id']}/estado/",{'estado':'archivado','motivo':'otro'}),409)
                for path,body in [(f"/pacientes/{p['id']}/consultas/",CONSULTATION),(f"/consultas/{c['id']}/diagnosticos/",{'codigo_cie10':'DEMO','descripcion':'DEMO'}),(f"/diagnosticos/{d['id']}/tratamientos/",{'indicaciones_generales':'DEMO'}),(f"/tratamientos/{t['id']}/recetas/",{'medicamento_id':'DEMO-inexistente','dosis':'DEMO','frecuencia':'DEMO'})]:
                    self.error(self.send(institution,'POST',path,body),409)
                self.assertEqual(self.repos[institution].obtener_historial(p['id']),h)

    def test_foreign_parents_have_the_same_404_as_missing_in_all_four_engines(self):
        for index,institution in enumerate(INSTITUTIONS):
            h=self.histories[INSTITUTIONS[(index+1)%4]]
            p=h['paciente']['id'];c=h['consultas'][0];d=c['diagnosticos'][0];t=d['tratamientos'][0]
            for method,path,missing,body in [
                ('GET',f'/pacientes/{p}/historial/','/pacientes/DEMO-ausente/historial/',None),
                ('POST',f'/pacientes/{p}/consultas/','/pacientes/DEMO-ausente/consultas/',CONSULTATION),
                ('POST',f"/consultas/{c['id']}/diagnosticos/",'/consultas/DEMO-ausente/diagnosticos/',{'codigo_cie10':'DEMO','descripcion':'DEMO'}),
                ('POST',f"/diagnosticos/{d['id']}/tratamientos/",'/diagnosticos/DEMO-ausente/tratamientos/',{'indicaciones_generales':'DEMO'}),
                ('POST',f"/tratamientos/{t['id']}/recetas/",'/tratamientos/DEMO-ausente/recetas/',{'medicamento_id':'DEMO','dosis':'D','frecuencia':'F'}),
                ('PATCH',f'/pacientes/{p}/estado/','/pacientes/DEMO-ausente/estado/',{'estado':'archivado','motivo':'DEMO'}),
            ]:
                with self.subTest(institution=institution,path=missing):
                    foreign=self.send(institution,method,path,body)
                    absent=self.send(institution,method,missing,body)
                    self.error(foreign,404)
                    self.assertEqual(foreign.json(),absent.json())

    def test_validation_and_duplicate_identification_are_real_http(self):
        for institution in INSTITUTIONS:
            response=self.send(institution,'POST','/pacientes/',PATIENT)
            self.assertEqual(response.status_code,201)
            self.assertEqual(self.repos[institution].obtener_historial(response.json()['id'])['consultas'],[])
            self.error(self.send(institution,'POST','/pacientes/',PATIENT),409)
            self.error(self.send(institution,'POST','/pacientes/',PATIENT|{'motor':'otro'}),400)
            self.error(self.send(institution,'POST','/pacientes/',PATIENT|{'fecha_nacimiento':'2026-02-30'}),400)
            client,_=self.admins[institution]
            self.error(client.get(BASE+'/pacientes/?limit=0',timeout=10),400)
            self.error(client.get(BASE+'/pacientes/?q=a&q=b',timeout=10),400)
            self.error(client.get(BASE+'/pacientes/?institucion=hospital',timeout=10),400)

    def test_roles_are_enforced_by_backend_not_buttons(self):
        for institution in INSTITUTIONS:
            for role in ('medico','secretaria','enfermero', *(['laboratorista'] if institution=='laboratorio' else [])):
                client,token=self.login(institution,role)
                try:
                    headers={'X-CSRFToken':token,'Origin':ORIGIN}
                    patient=self.histories[institution]['paciente']['id']
                    self.assertEqual(client.get(BASE+'/pacientes/',timeout=10).status_code,200)
                    if role=='secretaria':
                        self.error(client.get(BASE+f'/pacientes/{patient}/historial/',timeout=10),403)
                    self.error(client.patch(BASE+f'/pacientes/{patient}/estado/',json={'estado':'archivado','motivo':'DEMO'},headers=headers,timeout=10),403)
                    if role in ('secretaria','enfermero','laboratorista'):
                        self.error(client.get(BASE+'/medicamentos/',timeout=10),403)
                        self.error(client.post(BASE+'/consultas/ausente/diagnosticos/',json={'codigo_cie10':'DEMO','descripcion':'DEMO'},headers=headers,timeout=10),403)
                finally:
                    client.post(BASE+'/auth/logout/',json={},headers={'X-CSRFToken':token,'Origin':ORIGIN},timeout=10)
                    client.close()

    def test_csrf_rotation_and_logout_replay_are_real(self):
        for institution in INSTITUTIONS:
            client=requests.Session()
            try:
                initial=client.get(BASE+'/auth/csrf/',timeout=10).json()['csrfToken']
                login=client.post(BASE+'/auth/login/',json={'username':f'DEMO-A5-admin-{institution}','password':PASSWORD},headers={'X-CSRFToken':initial,'Origin':ORIGIN},timeout=10)
                self.assertEqual(login.status_code,200)
                self.assertIn('HttpOnly',login.headers['Set-Cookie'])
                self.error(client.post(BASE+'/pacientes/',json=PATIENT,headers={'X-CSRFToken':initial,'Origin':ORIGIN},timeout=10),403)
                self.error(client.post(BASE+'/pacientes/',json=PATIENT,headers={'Origin':ORIGIN},timeout=10),403)
                replay=requests.Session();replay.cookies.update(client.cookies)
                token=client.get(BASE+'/auth/csrf/',timeout=10).json()['csrfToken']
                logout=client.post(BASE+'/auth/logout/',json={},headers={'X-CSRFToken':token,'Origin':ORIGIN},timeout=10)
                self.assertEqual(logout.status_code,204)
                try:
                    self.error(replay.get(BASE+'/auth/me/',timeout=10),401)
                    self.error(replay.get(BASE+'/pacientes/',timeout=10),401)
                finally: replay.close()
            finally: client.close()

    def test_disabled_professional_is_revalidated_before_writing(self):
        from apps.identidad.models import Profesional
        for institution in INSTITUTIONS:
            pro=Profesional.objects.get(institucion=institution,referencia_externa='1')
            try:
                Profesional.objects.filter(pk=pro.pk).update(habilitado=False)
                self.error(self.send(institution,'POST','/pacientes/ausente/consultas/',CONSULTATION),403)
            finally:
                Profesional.objects.filter(pk=pro.pk).update(habilitado=True)

    def test_sql_identity_and_clinical_runtime_roles_have_no_ddl_or_legacy_users(self):
        from django.db import connection
        with connection.cursor() as c:
            c.execute("SELECT current_user,has_schema_privilege(current_user,'public','CREATE')")
            role,ddl=c.fetchone()
            self.assertEqual(role,'identidad_app');self.assertFalse(ddl)
        with self.repos['hospital']._connect() as conn:
            row=conn.execute("SELECT current_user,has_schema_privilege(current_user,'public','CREATE'),has_table_privilege(current_user,'usuario','SELECT'),has_table_privilege(current_user,'paciente','DELETE')").fetchone()
            self.assertEqual(row,('hospital_runtime',False,False,False))
        conn=self.repos['pediatrico']._connect()
        try:
            with conn.cursor() as c:
                c.execute('SELECT CURRENT_USER()')
                self.assertTrue(c.fetchone()[0].startswith('pediatria_runtime@'))
                c.execute('SHOW GRANTS')
                grants=' '.join(row[0] for row in c.fetchall()).upper()
                self.assertNotIn('CREATE',grants);self.assertNotIn('DELETE',grants)
                self.assertNotIn('`USUARIO`',grants)
        finally:conn.close()


if __name__=='__main__':
    unittest.main(verbosity=2)
