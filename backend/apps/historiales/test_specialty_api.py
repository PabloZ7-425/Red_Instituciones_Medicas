"""Specialty transport permission, validation and error ordering with explicit doubles."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.historiales.application.specialties import validate_specialty
from apps.historiales.domain.errors import DatosInvalidos, PersistenciaNoDisponible
from apps.historiales.test_clinical_api import APIHelpers


class SpecialtyAPITests(APIHelpers, TestCase):
    def setUp(self):
        self.user = self.account('laboratorio')
        self.browser, self.token = self.signin(self.user)
        self.repo = SimpleNamespace(registrar_resultado=lambda identifier, data: dict(data, id='R', paciente_id=identifier))
        self.factory_patch = patch('apps.historiales.presentation.specialties.AdapterFactory.create_clinical', return_value=self.repo)
        self.factory = self.factory_patch.start()
        self.addCleanup(self.factory_patch.stop)
        self.body = {'tipo_examen': 'E', 'fecha': '2020-01-01T12:00:00Z', 'estado': 'finalizado', 'campos': [{'nombre': 'DEMO', 'valor': False}]}

    def test_result_route_accepts_typed_values_without_professional_from_body(self):
        response = self.send('POST', '/api/pacientes/P/resultados/nuevo/', self.body)
        self.assertEqual(response.status_code, 201)
        self.assertIs(response.json()['campos'][0]['valor'], False)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.send('POST', '/api/pacientes/P/resultados/nuevo/', self.body | {'profesional_id': 'intruso'}).status_code, 400)

    def test_institution_and_role_are_checked_before_ids_body_and_factory(self):
        self.assertEqual(self.send('POST', '/api/pacientes/missing/crecimiento/', {}).status_code, 403)
        self.factory.assert_not_called()
        nurse = self.account('laboratorio', 'enfermero')
        browser, token = self.signin(nurse)
        response = self.send('POST', '/api/pacientes/missing/resultados/nuevo/', {}, browser=browser, token=token)
        self.assertEqual(response.status_code, 403)
        self.factory.assert_not_called()

    def test_bad_dto_query_and_duplicate_json_rejected_before_provider(self):
        url = '/api/pacientes/P/resultados/nuevo/'
        self.assertEqual(self.send('POST', url + '?institucion=hospital', self.body).status_code, 400)
        self.assertEqual(self.send('POST', url, self.body | {'campos': []}).status_code, 400)
        response = self.browser.post(url, '{"estado":"finalizado","estado":"anulado"}', content_type='application/json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 400)
        self.factory.assert_not_called()

    def test_catalog_head_pagination_and_method_allow_header(self):
        self.repo.listar_tipos_examen = lambda **page: dict(page, count=0, results=[])
        response = self.browser.get('/api/tipos-examen/?q=%25_&limit=1&offset=0')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['limit'], 1)
        self.assertEqual(self.browser.head('/api/tipos-examen/').status_code, 200)
        self.assertEqual(self.browser.get('/api/tipos-examen/?q=a&q=b').status_code, 400)
        self.assertEqual(self.browser.get('/api/pacientes/P/resultados/nuevo/').status_code, 405)
        self.assertNotIn('GET', self.browser.options('/api/pacientes/P/resultados/nuevo/')['Allow'])

    def test_csrf_and_missing_provider_safe_503(self):
        response = self.browser.post('/api/pacientes/P/resultados/nuevo/', self.body, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.factory.assert_not_called()
        del self.repo.registrar_resultado
        response = self.send('POST', '/api/pacientes/P/resultados/nuevo/', self.body)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), PersistenciaNoDisponible().as_dict())

    def test_pure_validation_rejects_nonfinite_numbers_unknowns_and_bad_dates(self):
        for body in (self.body | {'campos': [{'nombre': 'X', 'valor': float('nan')}]},
                     self.body | {'campos': [{'nombre': 'X', 'valor': 10**1000}]},
                     self.body | {'fecha': '2020-02-30T00:00:00Z'},
                     self.body | {'campos': [{'nombre': 'X', 'valor': None}]}):
            with self.assertRaises(DatosInvalidos):
                validate_specialty('result', body)
