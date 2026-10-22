"""Opt-in HTTP/native specialty checks against only the disposable A5 stack."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from threading import Barrier
import sys
import unittest
from uuid import uuid4

ROOT = Path(os.environ.get('A5_RUNTIME', '/workspace/work/a5-runtime')).resolve()


class SpecialtyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('A5_REAL_HTTP') != '1' or ROOT.name != 'a5-runtime' or ROOT.parent.name != 'work':
            raise RuntimeError('Solo A5 explícito y desechable')
        env = json.loads((ROOT / 'server.json').read_text())
        if env.get('MONGO_URI') != 'mongodb://127.0.0.1:27039/laboratorio?replicaSet=a5' or env.get('FIREBASE_PROJECT_ID') != 'demo-jennifer-a5':
            raise RuntimeError('Destino fuera de A5')
        os.environ.update(env)
        sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]
        import django
        django.setup()
        from apps.historiales.domain.context import ContextoClinico
        from apps.historiales.infrastructure.factory import AdapterFactory
        from test_http import RealHTTPTests
        cls.login = staticmethod(RealHTTPTests.login)
        cls.contexts = {name: ContextoClinico(name, 'DEMO-A4-native', 'admin', '1') for name in ('hospital', 'pediatrico', 'laboratorio', 'odontologica')}
        cls.repos = {name: AdapterFactory.create_clinical(context) for name, context in cls.contexts.items()}
        cls.clients, cls.patients = {}, {}
        for name in cls.repos:
            cls.clients[name] = cls.login(name, 'admin')
            client, _ = cls.clients[name]
            response = client.get('http://127.0.0.1:18005/api/pacientes/?q=DEMO-A5-BROWSER', timeout=15)
            assert response.status_code == 200 and response.json()['count'] == 1, 'Ejecutar primero navegador A5'
            cls.patients[name] = response.json()['results'][0]

    @classmethod
    def tearDownClass(cls):
        for client, token in cls.clients.values():
            client.post('http://127.0.0.1:18005/api/auth/logout/', headers={'X-CSRFToken': token, 'Origin': 'http://127.0.0.1:18173'}, timeout=10)
            client.close()

    def http(self, institution, method, route, body=None, account=None):
        client, token = account or self.clients[institution]
        return client.request(method, 'http://127.0.0.1:18005/api/' + route, json=body,
                              headers={'X-CSRFToken': token, 'Origin': 'http://127.0.0.1:18173'}, timeout=20)

    def test_browser_specialties_persist_in_native_connections_and_match_http(self):
        patient = {name: row['id'] for name, row in self.patients.items()}
        admissions = self.repos['hospital'].listar_ingresos(patient['hospital'])
        self.assertEqual(len(admissions['ingresos']), 1)
        self.assertIsNotNone(admissions['ingresos'][0]['fecha_hora_alta'])
        followup = self.repos['pediatrico'].obtener_seguimiento(patient['pediatrico'])
        self.assertEqual([len(followup[k]) for k in ('tutores', 'vacunas', 'crecimiento')], [1, 1, 1])
        self.assertEqual(followup['crecimiento'][0]['peso_kg'], '15.20')
        results = self.repos['laboratorio'].listar_resultados(patient['laboratorio'])
        self.assertEqual(len(results['resultados']), 1)
        self.assertEqual([row['valor'] for row in results['resultados'][0]['campos']], [3.5, False, 'DEMO resultado navegador'])
        procedures = self.repos['odontologica'].listar_procedimientos(patient['odontologica'])
        self.assertEqual(len(procedures['procedimientos']), 1)
        self.assertEqual(procedures['procedimientos'][0]['pieza'], '16')
        for institution, route, expected in [('hospital', 'ingresos', admissions), ('pediatrico', 'seguimiento', followup), ('laboratorio', 'resultados', results), ('odontologica', 'procedimientos', procedures)]:
            response = self.http(institution, 'GET', f'pacientes/{patient[institution]}/{route}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), expected)
            self.assertIn('no-store', response.headers['Cache-Control'])

    def test_all_specialty_writes_reject_archived_patient_without_losing_rows(self):
        for institution, kinds in [('hospital', ['admission', 'discharge']), ('pediatrico', ['tutor', 'vaccine', 'growth']), ('laboratorio', ['result']), ('odontologica', ['procedure'])]:
            p = self.patients[institution]['id']
            repo = self.repos[institution]
            for kind in kinds:
                if kind == 'admission':
                    body = {'cama_id': repo.listar_camas()['results'][0]['id'], 'fecha_hora_ingreso': '2020-01-01T12:00:00Z', 'tipo_ingreso': 'DEMO'}
                    route = f'pacientes/{p}/ingresos/nuevo/'
                elif kind == 'discharge':
                    row = repo.listar_ingresos(p)['ingresos'][0]
                    route, body = f"ingresos/{row['id']}/alta/", {'fecha_hora_alta': row['fecha_hora_alta']}
                elif kind == 'tutor':
                    route, body = f'pacientes/{p}/tutores/nuevo/', {'nombres': 'DEMO', 'apellidos': 'DEMO', 'parentesco': 'DEMO'}
                elif kind == 'vaccine':
                    route, body = f'pacientes/{p}/vacunas/', {'vacuna_id': repo.listar_vacunas()['results'][0]['id'], 'fecha': '2020-01-01', 'dosis': 1}
                elif kind == 'growth':
                    route, body = f'pacientes/{p}/crecimiento/', {'fecha': '2020-01-01', 'peso_kg': '15.20', 'talla_cm': '90.00'}
                elif kind == 'result':
                    route, body = f'pacientes/{p}/resultados/nuevo/', self.result_body(repo)
                else:
                    row = repo.listar_procedimientos(p)['procedimientos'][0]
                    route, body = f'pacientes/{p}/procedimientos/nuevo/', {key: row[key] for key in ('tratamiento_id', 'pieza', 'descripcion', 'estado')}
                self.assertEqual(self.http(institution, 'POST', route, body).status_code, 409, kind)

    def test_roles_tutor_privacy_and_institution_before_body(self):
        secret = self.login('pediatrico', 'secretaria')
        nurse = self.login('pediatrico', 'enfermero')
        try:
            p = self.patients['pediatrico']['id']
            response = self.http('pediatrico', 'GET', f'pacientes/{p}/tutores/', account=secret)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(set(response.json()), {'paciente_id', 'tutores'})
            self.assertEqual(self.http('pediatrico', 'GET', f'pacientes/{p}/seguimiento/', account=secret).status_code, 403)
            self.assertEqual(self.http('pediatrico', 'POST', f'pacientes/{p}/crecimiento/', {}, account=secret).status_code, 403)
            self.assertEqual(self.http('pediatrico', 'GET', f'pacientes/{p}/seguimiento/', account=nurse).status_code, 200)
            self.assertEqual(self.http('pediatrico', 'POST', f'pacientes/{p}/tutores/nuevo/', {}, account=nurse).status_code, 403)
            self.assertEqual(self.http('hospital', 'POST', 'pacientes/missing/resultados/nuevo/', {}).status_code, 403)
            self.assertEqual(self.http('laboratorio', 'POST', 'pacientes/missing/procedimientos/nuevo/', {}).status_code, 403)
        finally:
            for client, token in (secret, nurse):
                client.post('http://127.0.0.1:18005/api/auth/logout/', headers={'X-CSRFToken': token, 'Origin': 'http://127.0.0.1:18173'}, timeout=10)
                client.close()

    @staticmethod
    def result_body(repo):
        return {'tipo_examen': repo.listar_tipos_examen()['results'][0]['id'], 'fecha': '2020-01-01T12:00:00Z', 'estado': 'finalizado', 'campos': [{'nombre': 'DEMO', 'valor': False}]}

    def new_patient(self, repo):
        return repo.registrar_paciente({'identificacion': 'A4-' + uuid4().hex[:16], 'nombres': 'DEMO', 'apellidos': 'Sintético', 'fecha_nacimiento': '2000-01-01'})

    def payload(self, institution, repo, p):
        if institution == 'laboratorio':
            return 'registrar_resultado', 'listar_resultados', self.result_body(repo)
        c = repo.registrar_consulta(p, {'fecha': '2020-01-01', 'notas_evolucion': 'DEMO'})
        d = repo.registrar_diagnostico(c['id'], {'codigo_cie10': 'DEMO', 'descripcion': 'DEMO'})
        t = repo.registrar_tratamiento(d['id'], {'indicaciones_generales': 'DEMO'})
        return 'registrar_procedimiento', 'listar_procedimientos', {'tratamiento_id': t['id'], 'pieza': '16', 'descripcion': 'DEMO', 'estado': 'realizado'}

    def test_native_nosql_rollback_and_cross_patient_reference(self):
        from apps.historiales.domain.errors import PersistenciaNoDisponible, RecursoNoEncontrado
        for institution in ('laboratorio', 'odontologica'):
            repo = self.repos[institution]
            p = self.new_patient(repo)['id']
            write, read, body = self.payload(institution, repo, p)

            class Broken(type(repo)):
                def _after_write(self, unit):
                    raise PersistenciaNoDisponible()

            broken = Broken(contexto=self.contexts[institution])
            before = getattr(repo, read)(p)
            def root_version():
                client = repo._client()
                try:
                    if institution == 'laboratorio':
                        return client.get_default_database().clinico_pacientes.find_one({'_id': p})['version']
                    return client.collection('pacientes').document(p).get().to_dict()['version']
                finally:
                    client.close()
            version = root_version()
            with self.assertRaises(PersistenciaNoDisponible):
                getattr(broken, write)(p, body)
            self.assertEqual(getattr(repo, read)(p), before)
            self.assertEqual(root_version(), version)
            if institution == 'odontologica':
                other = self.new_patient(repo)['id']
                with self.assertRaises(RecursoNoEncontrado):
                    repo.registrar_procedimiento(other, body)

    def test_result_instants_order_and_bad_catalog_are_safe(self):
        from apps.historiales.domain.errors import RecursoNoEncontrado
        repo = self.repos['laboratorio']
        p = self.new_patient(repo)['id']
        body = self.result_body(repo)
        later = repo.registrar_resultado(p, body | {'fecha': '2020-01-01T12:00:00.001Z'})
        earlier = repo.registrar_resultado(p, body)
        self.assertEqual([row['id'] for row in repo.listar_resultados(p)['resultados']], [earlier['id'], later['id']])
        for identifier in ('missing', self.patients['odontologica']['id']):
            with self.assertRaises(RecursoNoEncontrado):
                repo.registrar_resultado(p, body | {'tipo_examen': identifier})
        self.assertEqual(len(repo.listar_resultados(p)['resultados']), 2)

    def test_native_nosql_overlapping_archive_specialty_write(self):
        from apps.historiales.domain.errors import Conflicto
        for institution in ('laboratorio', 'odontologica'):
            repo = self.repos[institution]
            for _ in range(2):
                p = self.new_patient(repo)['id']
                write, read, body = self.payload(institution, repo, p)
                barrier = Barrier(2)

                def writer():
                    barrier.wait(timeout=10)
                    try:
                        getattr(repo, write)(p, body)
                        return True
                    except Conflicto:
                        return False

                def archiver():
                    barrier.wait(timeout=10)
                    return repo.archivar_paciente(p, 'DEMO carrera especializada')

                with ThreadPoolExecutor(max_workers=2) as pool:
                    write_future, archive_future = pool.submit(writer), pool.submit(archiver)
                    committed = write_future.result(timeout=30)
                    self.assertEqual(archive_future.result(timeout=30)['estado'], 'archivado')
                key = 'resultados' if institution == 'laboratorio' else 'procedimientos'
                self.assertEqual(len(getattr(repo, read)(p)[key]), 1 if committed else 0)
                with self.assertRaises(Conflicto):
                    getattr(repo, write)(p, body)


if __name__ == '__main__':
    unittest.main(verbosity=2)
