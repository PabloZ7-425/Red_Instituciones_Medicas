"""AUC-08: frozen permission expectations checked through authenticated HTTP."""
import csv
import os
import time
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.identidad.models import PerfilInstitucional, Profesional
from apps.operaciones.catalog import RESOURCES


class CoveragePermissionTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('auc08-permissions',password='test-password')
        self.profile=PerfilInstitucional.objects.create(usuario=self.user,institucion='hospital',rol='admin')
        self.client=APIClient();self.client.force_login(self.user)
        session=self.client.session;session['clinical_authenticated_at']=time.time();session.save()
        path=Path(os.environ.get('AUC08_PERMISSION_MATRIX',Path(__file__).with_name('permission_matrix.csv')))
        with path.open(encoding='utf-8',newline='') as f:self.rows=list(csv.DictReader(f))

    def actor(self,institution,role,professional=True):
        pro,_=Profesional.objects.get_or_create(institucion=institution,referencia_externa='1',defaults={'habilitado':True})
        self.profile.institucion=institution;self.profile.rol=role;self.profile.profesional=pro if professional else None
        self.profile.save()

    def test_every_declared_resource_and_verb_is_enforced_for_every_institution_role(self):
        self.assertEqual({(r['institucion'],r['recurso']) for r in self.rows},
                         {(i,n) for i,rs in RESOURCES.items() for n in rs})
        for institution in RESOURCES:
            for role in ['admin','medico','secretaria','enfermero']+(['laboratorista'] if institution=='laboratorio' else []):
                self.actor(institution,role)
                for row in [r for r in self.rows if r['institucion']==institution]:
                    for operation in ['leer','crear','editar','lookup']:
                        allowed=role in row[operation].split()
                        with self.subTest(institution=institution,role=role,resource=row['recurso'],operation=operation):
                            with patch('apps.operaciones.views.OperationsRepository') as provider:
                                provider.return_value.page.return_value={'count':0,'limit':20,'offset':0,'results':[]}
                                provider.return_value.save.return_value={'id':'synthetic','values':{},'version':'v2'}
                                url='/api/operaciones/'+row['recurso']+'/'
                                if operation in {'leer','lookup'}:
                                    response=self.client.get(url+('?lookup=1' if operation=='lookup' else ''))
                                elif operation=='crear':
                                    response=self.client.post(url,{} if allowed else '{',format='json' if allowed else None,content_type=None if allowed else 'application/json')
                                else:
                                    response=self.client.patch(url+'synthetic/',{'values':{},'version':'v1'} if allowed else '{',format='json' if allowed else None,content_type=None if allowed else 'application/json')
                                self.assertEqual(response.status_code,(201 if operation=='crear' else 200) if allowed else 403,response.data)
                                if allowed:self.assertTrue(provider.called)
                                else:provider.assert_not_called()

    def test_professional_requirement_and_manifest_match_for_each_documental_clinical_editor(self):
        for institution,name in [('laboratorio','resultado'),('odontologica','procedimiento')]:
            for role in ['admin','medico']+(['laboratorista'] if institution=='laboratorio' else []):
                self.actor(institution,role,professional=False)
                with patch('apps.operaciones.views.OperationsRepository') as provider:
                    response=self.client.patch('/api/operaciones/'+name+'/synthetic/',data='{',content_type='application/json')
                    self.assertEqual(response.status_code,403);provider.assert_not_called()
                manifest=self.client.get('/api/operaciones/').data
                self.assertFalse(next(r for r in manifest['resources'] if r['key']==name)['edit'])

    def test_financial_tasks_use_same_cashier_permissions_and_deny_before_provider(self):
        for institution in ['hospital','pediatrico']:
            for role in ['admin','secretaria','medico','enfermero']:
                self.actor(institution,role)
                for name,action in [('factura','emitir'),('factura','anular'),('pago','revertir')]:
                    with patch('apps.operaciones.views.OperationsRepository') as provider:
                        provider.return_value.financial_action.return_value={'id':'synthetic'}
                        response=self.client.post('/api/operaciones/'+name+'/synthetic/',{'accion':action,'version':'v1'},format='json')
                        self.assertEqual(response.status_code,200 if role in {'admin','secretaria'} else 403)
                        if role not in {'admin','secretaria'}:provider.assert_not_called()

    def test_logout_denies_every_resource_and_mutation_without_provider(self):
        self.client.logout()
        for row in self.rows:
            with patch('apps.operaciones.views.OperationsRepository') as provider:
                url='/api/operaciones/'+row['recurso']+'/'
                for response in [self.client.get(url),self.client.post(url,{},format='json'),
                                 self.client.patch(url+'synthetic/',{'values':{},'version':'v1'},format='json')]:
                    self.assertEqual(response.status_code,401)
                provider.assert_not_called()

    def test_account_administration_matrix_and_cross_institution_rejection(self):
        previous_id=None
        for institution in RESOURCES:
            for role in ['medico','secretaria','enfermero']+(['laboratorista'] if institution=='laboratorio' else []):
                self.actor(institution,role)
                for response in [self.client.get('/api/operaciones/cuentas/'),
                                 self.client.post('/api/operaciones/cuentas/',data='{',content_type='application/json'),
                                 self.client.patch('/api/operaciones/cuentas/',data='{',content_type='application/json')]:
                    self.assertEqual(response.status_code,403)
            self.actor(institution,'admin')
            response=self.client.post('/api/operaciones/cuentas/',{'username':'auc08-'+institution,
                'password':'AUC08-Good-Test-Password!789','rol':'secretaria'},format='json')
            self.assertEqual(response.status_code,201,response.data)
            user_id=response.data['id']
            if previous_id:
                self.assertEqual(self.client.patch('/api/operaciones/cuentas/',{'id':previous_id,'activo':False},format='json').status_code,404)
                self.assertNotIn(previous_id,[r['id'] for r in self.client.get('/api/operaciones/cuentas/').data['results']])
            self.assertEqual(self.client.patch('/api/operaciones/cuentas/',{'id':user_id,'activo':False},format='json').status_code,200)
            previous_id=user_id
        self.client.logout()
        self.assertEqual(self.client.get('/api/operaciones/cuentas/').status_code,401)
