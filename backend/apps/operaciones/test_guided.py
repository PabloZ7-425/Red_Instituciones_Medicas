"""AUC-09: complete institution-local account navigation, beyond the old 200 cap."""
import time
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from apps.identidad.models import PerfilInstitucional


class AccountNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users=get_user_model().objects.bulk_create([get_user_model()(username=f'auc09-{n:03d}') for n in range(225)])
        PerfilInstitucional.objects.bulk_create([PerfilInstitucional(usuario=u,institucion='hospital',rol='admin' if n==0 else 'secretaria') for n,u in enumerate(users)])
        foreign=get_user_model().objects.create(username='auc09-foreign')
        PerfilInstitucional.objects.create(usuario=foreign,institucion='pediatrico',rol='admin')

    def setUp(self):
        self.client=APIClient();self.client.force_login(get_user_model().objects.get(username='auc09-000'))
        session=self.client.session;session['clinical_authenticated_at']=time.time();session.save()

    def test_all_accounts_are_reachable_with_stable_order_without_foreign_accounts(self):
        seen=[]
        for offset in range(0,240,20):
            response=self.client.get(f'/api/operaciones/cuentas/?limit=20&offset={offset}')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.data['count'],225)
            self.assertEqual(response.data['offset'],offset)
            self.assertEqual(response.data['limit'],20)
            seen.extend(r['username'] for r in response.data['results'])
        self.assertEqual(seen,[f'auc09-{n:03d}' for n in range(225)])

    def test_search_is_case_insensitive_literal_prefix_and_count_precedes_slice(self):
        response=self.client.get('/api/operaciones/cuentas/',{'q':' AUC09-22 ','limit':2,'offset':2})
        self.assertEqual(response.data['count'],5)
        self.assertEqual([r['username'] for r in response.data['results']],['auc09-222','auc09-223'])
        self.assertEqual(self.client.get('/api/operaciones/cuentas/',{'q':'auc09-%'}).data['count'],0)
        empty=self.client.get('/api/operaciones/cuentas/?offset=9999').data
        self.assertEqual(empty['count'],225);self.assertEqual(empty['results'],[])

    def test_invalid_repeated_queries_and_mutation_queries_are_rejected(self):
        for query in ['limit=0','limit=101','offset=-1','offset=1.0','q=a&q=b','limit=1&limit=2','institucion=pediatrico','q='+'x'*101]:
            with self.subTest(query=query):self.assertEqual(self.client.get('/api/operaciones/cuentas/?'+query).status_code,400)
        self.assertEqual(self.client.post('/api/operaciones/cuentas/?limit=1',{},format='json').status_code,400)

    def test_non_admin_cannot_search_or_page_accounts(self):
        profile=PerfilInstitucional.objects.get(usuario__username='auc09-000');profile.rol='medico';profile.save()
        self.assertEqual(self.client.get('/api/operaciones/cuentas/?q=auc09&offset=200').status_code,403)
