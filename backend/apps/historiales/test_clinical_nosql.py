"""A3 real two-engine contracts. Opt in; destinations are generated and disposable.

Requires B1 (included in this branch); see docs/jennifer/A3_NOSQL.md. Never live data.
"""
import importlib.util
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from uuid import uuid4

ENABLED = os.environ.get('A3_NOSQL_TESTS') == '1'
if ENABLED:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore
    from pymongo import MongoClient
    from apps.historiales.domain.context import ContextoClinico
    from apps.historiales.domain.errors import (
        AccesoDenegado, Conflicto, DatosInvalidos, NoAutenticado,
        PersistenciaNoDisponible, RecursoNoEncontrado,
    )
    from apps.historiales.infrastructure.adapters.mongo_adapter import MongoAdapter
    from apps.historiales.infrastructure.adapters.firestore_adapter import FirestoreAdapter
    from apps.historiales.testing.repository_contract import (
        RepositoryContract, PACIENTE, CONSULTA, DIAGNOSTICO, TRATAMIENTO,
    )
else:
    class RepositoryContract:
        pass


class NoSQLHarness:
    def __init__(self):
        mongo_uri = os.environ['A3_MONGO_TEST_URI']
        firestore_host = os.environ['FIRESTORE_EMULATOR_HOST']
        if not re.fullmatch(r'mongodb://127\.0\.0\.1:[0-9]+/\?replicaSet=a3', mongo_uri):
            raise RuntimeError('Usar replica set a3 local dedicado, sin base activa')
        if not re.fullmatch(r'127\.0\.0\.1:[0-9]+', firestore_host):
            raise RuntimeError('Firestore requiere emulador local dedicado')
        self.mongo = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        self.dbname = 'a3_test_' + uuid4().hex
        self.db = self.mongo[self.dbname]
        self.project = 'demo-a3-' + uuid4().hex[:16]
        self.firestore = firestore.Client(project=self.project, credentials=AnonymousCredentials())
        schema_path = Path(os.environ['A3_MONGO_SCHEMA'])
        spec = importlib.util.spec_from_file_location('a3_schema', schema_path)
        schema = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema)
        schema.prepare(self.db)
        schema.prepare(self.db)  # idempotent; leaves legacy untouched
        self.db.clinico_medicamentos.insert_one({
            '_id': 'DEMO-M', 'nombre': 'DEMO no administrar', 'presentacion': None,
            'schema_version': 2, 'institucion': 'laboratorio',
        })
        self.firestore.collection('medicamentos').document('DEMO-M').set({
            'nombre': 'DEMO no administrar', 'presentacion': None,
            'schema_version': 2, 'institucion': 'odontologica',
        })
        self.commit_order = None

    def repo(self, contexto):
        harness = self
        base = MongoAdapter if contexto.institucion == 'laboratorio' else FirestoreAdapter

        class Instrumented(base):
            fail = False
            gate = None
            attempt = None

            def _client(self):
                if self.institution == 'laboratorio':
                    # Every repository call creates an independent client/session.
                    return MongoClient(os.environ['A3_MONGO_TEST_URI'].replace('/?', '/' + harness.dbname + '?'), serverSelectionTimeoutMS=3000)
                client = firestore.Client(project=harness.project, credentials=AnonymousCredentials())
                original_transaction = client.transaction

                def transaction(**kwargs):
                    tx = original_transaction(**kwargs)
                    original_commit = tx._commit

                    def commit(*args, **commit_kwargs):
                        order = harness.commit_order
                        if order is not None and order[0] is not self and not order[1].is_set():
                            # Release native read locks before waiting. Otherwise
                            # a commit gate would itself deadlock the emulator.
                            # SDK retries the rolled-back transaction, checking
                            # the freshly committed root again (no in-memory lock).
                            from google.api_core.exceptions import Aborted
                            tx._rollback()
                            if not order[1].wait(10):
                                raise AssertionError('No confirmó la primera transacción Firestore')
                            raise Aborted('DEMO: orden de commit controlado por la prueba')
                        result = original_commit(*args, **commit_kwargs)
                        if order is not None and order[0] is self:
                            order[1].set()
                        return result
                    tx._commit = commit
                    return tx
                client.transaction = transaction
                return client

            def _get(self, unit, collection, identifier):
                if self.attempt is not None and collection == 'pacientes':
                    self.attempt.set()
                return super()._get(unit, collection, identifier)

            def _after_root(self, unit):
                if self.gate:
                    entered, release = self.gate
                    self.gate = None
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError('No se liberó la barrera raíz')

            def _after_write(self, unit):
                if self.fail:
                    self.fail = False
                    raise PersistenciaNoDisponible()

        return Instrumented(contexto=contexto)

    def inactive(self, repo, patient_id):
        if repo.institution == 'laboratorio':
            self.db.clinico_pacientes.update_one({'_id': patient_id}, {'$set': {'estado': 'inactivo'}})
        else:
            self.firestore.collection('pacientes').document(patient_id).update({'estado': 'inactivo'})

    def fail_next(self, repo):
        repo.fail = True

    def gate_next(self, repo, entered, release):
        repo.gate = (entered, release)
        if repo.institution == 'odontologica':
            # Native overlapping transactions, deterministic COMMIT order. The
            # second may read the old root; native rollback releases its locks
            # and SDK retries/rechecks active. Unordered races have no such hook.
            self.commit_order = (repo, Event())

    def put(self, repo, collection, identifier, **fields):
        row = dict(fields, schema_version=2, institucion=repo.institution)
        if repo.institution == 'laboratorio':
            self.db['clinico_' + collection].insert_one(dict(row, _id=identifier))
        else:
            self.firestore.collection(collection).document(identifier).set(row)

    def close(self):
        if not re.fullmatch(r'a3_test_[a-f0-9]{32}', self.dbname) or not re.fullmatch(r'demo-a3-[a-f0-9]{16}', self.project):
            raise RuntimeError('Limpieza rechazada fuera del destino generado')
        self.mongo.drop_database(self.dbname)
        self.mongo.close()
        for collection in self.firestore.collections():
            for doc in collection.stream():
                doc.reference.delete()
        self.firestore.close()


class ExtraNoSQL:
    def test_context_and_permissions_before_database(self):
        cls = MongoAdapter if self.context.institucion == 'laboratorio' else FirestoreAdapter
        with self.assertRaises(NoAutenticado):
            cls().listar_pacientes()
        with self.assertRaises(AccesoDenegado):
            cls(contexto=self.other_context)
        for role, method, args in (
            ('secretaria', 'obtener_historial', ('missing',)),
            ('enfermero', 'registrar_paciente', (PACIENTE,)),
            ('medico', 'archivar_paciente', ('missing', 'DEMO')),
        ):
            ctx = ContextoClinico(self.context.institucion, 'DEMO-U', role)
            with self.assertRaises(AccesoDenegado):
                getattr(cls(contexto=ctx), method)(*args)
        ctx = ContextoClinico(self.context.institucion, 'DEMO-U', 'medico')
        with self.assertRaises(AccesoDenegado):
            cls(contexto=ctx).registrar_consulta('missing', CONSULTA)

    def test_validation_and_safe_opaque_ids(self):
        for payload in (PACIENTE | {'motor': 'DEMO'}, PACIENTE | {'fecha_nacimiento': '2026-02-30'}):
            with self.assertRaises(DatosInvalidos):
                self.repo.registrar_paciente(payload)
        for identifier in ('../DEMO', '/', '.', '..', 'x' * 1501, '__reserved__', '\ud800'):
            with self.assertRaises(RecursoNoEncontrado):
                self.repo.obtener_historial(identifier)
        for params in ({'limit': True}, {'offset': -1}, {'q': None}):
            with self.assertRaises(DatosInvalidos):
                self.repo.listar_pacientes(**params)

    def test_foreign_document_in_same_engine_is_not_visible(self):
        p = self.patient()
        collection = 'clinico_pacientes'
        foreign = dict(PACIENTE, estado='activo', motivo_archivo=None, fecha_archivo=None, schema_version=2, institucion=self.other_context.institucion, version=0)
        if self.repo.institution == 'laboratorio':
            # Dedicated collection validator deliberately rejects other institutions.
            from pymongo.errors import WriteError
            with self.assertRaises(WriteError):
                self.harness.db[collection].insert_one(dict(foreign, _id='DEMO-foreign'))
        else:
            self.harness.firestore.collection('pacientes').document('DEMO-foreign').set(foreign)
            with self.assertRaises(RecursoNoEncontrado):
                self.repo.obtener_historial('DEMO-foreign')
        self.assertEqual(self.repo.listar_pacientes()['count'], 1)
        self.assertEqual(self.repo.obtener_historial(p['id'])['paciente'], p)

    def test_appointment_patient_professional_consumption_and_rollback(self):
        p = self.patient()
        self.harness.put(self.repo, 'citas', 'DEMO-CITA', paciente_id=p['id'], profesional_id=self.context.profesional_id, estado='programada')
        dto = CONSULTA | {'cita_id': 'DEMO-CITA'}
        self.harness.fail_next(self.repo)
        with self.assertRaises(PersistenciaNoDisponible):
            self.repo.registrar_consulta(p['id'], dto)
        c = self.repo.registrar_consulta(p['id'], dto)
        self.assertEqual(c['cita_id'], 'DEMO-CITA')
        with self.assertRaises(Conflicto):
            self.repo.registrar_consulta(p['id'], dto)
        other = self.patient(identificacion='DEMO-0002')
        with self.assertRaises(RecursoNoEncontrado):
            self.repo.registrar_consulta(other['id'], dto)
        self.assertEqual(len(self.repo.obtener_historial(p['id'])['consultas']), 1)

    def test_connection_error_is_safe(self):
        if self.repo.institution == 'laboratorio':
            from pymongo.errors import ConnectionFailure
            error = ConnectionFailure('DEMO private endpoint and secret')
        else:
            from google.api_core.exceptions import ServiceUnavailable
            error = ServiceUnavailable('DEMO private endpoint and secret')
        with patch.object(self.repo, '_client', side_effect=error), self.assertRaises(PersistenciaNoDisponible) as caught:
            self.repo.listar_pacientes()
        self.assertNotIn('secret', str(caught.exception.as_dict()))

    def test_birth_date_and_archive_civil_clock(self):
        from datetime import date
        p = self.patient()
        with self.assertRaises(DatosInvalidos):
            self.repo.registrar_consulta(p['id'], CONSULTA | {'fecha': '1999-12-31'})
        with patch('apps.historiales.application.validation.hoy_guatemala', return_value=date(2026, 10, 21)):
            archived = self.repo.archivar_paciente(p['id'], ' DEMO ')
        self.assertEqual(archived['fecha_archivo'], '2026-10-21')
        self.assertEqual(archived, self.repo.archivar_paciente(p['id'], 'DEMO'))

    def test_unordered_native_archive_race(self):
        for number in range(3):
            p = self.patient(identificacion=f'DEMO-RACE-{number}')
            peer = self.harness.repo(self.context)
            with ThreadPoolExecutor(max_workers=2) as pool:
                write = pool.submit(self.repo.registrar_consulta, p['id'], CONSULTA)
                archive = pool.submit(peer.archivar_paciente, p['id'], 'DEMO')
                try:
                    write.result(timeout=20)
                    count = 1
                except Conflicto:
                    count = 0
                archive.result(timeout=20)
            history = self.repo.obtener_historial(p['id'])
            self.assertEqual(history['paciente']['estado'], 'archivado')
            self.assertEqual(len(history['consultas']), count)
            with self.assertRaises(Conflicto):
                peer.registrar_consulta(p['id'], CONSULTA)

    def test_archive_blocks_concurrent_nested_writes(self):
        for number, method in enumerate(('registrar_diagnostico', 'registrar_tratamiento', 'registrar_receta')):
            p = self.repo.registrar_paciente(PACIENTE | {'identificacion': f'DEMO-NEST-{number}'})
            c = self.repo.registrar_consulta(p['id'], CONSULTA)
            d = self.repo.registrar_diagnostico(c['id'], DIAGNOSTICO)
            t = self.repo.registrar_tratamiento(d['id'], TRATAMIENTO)
            parent, dto = {
                'registrar_diagnostico': (c['id'], DIAGNOSTICO),
                'registrar_tratamiento': (d['id'], TRATAMIENTO),
                'registrar_receta': (t['id'], {'medicamento_id': 'DEMO-M', 'dosis': 'DEMO', 'frecuencia': 'DEMO'}),
            }[method]
            before = self.repo.obtener_historial(p['id'])['consultas']
            peer = self.harness.repo(self.context)
            entered, release, attempted = Event(), Event(), Event()
            self.harness.gate_next(self.repo, entered, release)
            peer.attempt = attempted
            with ThreadPoolExecutor(max_workers=2) as pool:
                archive = pool.submit(self.repo.archivar_paciente, p['id'], 'DEMO')
                try:
                    self.assertTrue(entered.wait(5))
                    writer = pool.submit(getattr(peer, method), parent, dto)
                    self.assertTrue(attempted.wait(5))
                finally:
                    release.set()
                archive.result(timeout=20)
                with self.assertRaises(Conflicto):
                    writer.result(timeout=20)
            self.assertEqual(self.repo.obtener_historial(p['id'])['consultas'], before)

    def test_duplicate_patient_race(self):
        peer = self.harness.repo(self.context)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks = [pool.submit(repo.registrar_paciente, PACIENTE) for repo in (self.repo, peer)]
            outcomes = []
            for task in tasks:
                try:
                    outcomes.append(task.result(timeout=20))
                except Conflicto:
                    outcomes.append('conflict')
        self.assertEqual(outcomes.count('conflict'), 1)
        self.assertEqual(self.repo.listar_pacientes()['count'], 1)


@unittest.skipUnless(ENABLED, 'A3 requiere núcleo B1 y destinos locales aislados; no certifica integración')
class MongoClinicalTests(ExtraNoSQL, RepositoryContract, unittest.TestCase):
    institutions = ('laboratorio', 'odontologica')

    def test_schema_is_strict_and_legacy_is_unchanged(self):
        from pymongo.errors import WriteError
        legacy = {'_id': 'DEMO-legacy', 'nota': 'Documento sintético A2 preservado'}
        self.harness.db.pacientes.insert_one(legacy)
        before = self.harness.db.pacientes.find_one({'_id': legacy['_id']})
        self.patient()
        invalid = dict(PACIENTE, _id='DEMO-bad', institucion='laboratorio', schema_version=2, version=0, estado='desconocido')
        with self.assertRaises(WriteError):
            self.harness.db.clinico_pacientes.insert_one(invalid)
        self.assertEqual(self.harness.db.pacientes.find_one({'_id': legacy['_id']}), before)

    def test_unprepared_namespace_is_not_created_implicitly(self):
        self.harness.db.drop_collection('clinico_consultas')
        with self.assertRaises(PersistenciaNoDisponible):
            self.repo.registrar_paciente(PACIENTE)
        self.assertEqual(self.harness.db.clinico_pacientes.count_documents({}), 0)
        self.assertNotIn('clinico_consultas', self.harness.db.list_collection_names())

    def make_harness(self):
        return NoSQLHarness()


@unittest.skipUnless(ENABLED, 'A3 requiere núcleo B1 y destinos locales aislados; no certifica integración')
class FirestoreClinicalTests(ExtraNoSQL, RepositoryContract, unittest.TestCase):
    institutions = ('odontologica', 'laboratorio')

    def test_existing_a1_model_is_readable_and_writable(self):
        import sys
        model_dir = Path(os.environ['A3_MONGO_SCHEMA']).parents[1] / 'firebase'
        sys.path.insert(0, str(model_dir))
        self.addCleanup(sys.path.remove, str(model_dir))
        import clinical_model
        data = clinical_model.load_fixture()
        for collection, identifier, row in clinical_model.entries(data):
            self.harness.firestore.collection(collection).document(identifier).set(row)
        for patient_id in data['pacientes']:
            self.assertEqual(self.repo.obtener_historial(patient_id), clinical_model.project_history(data, patient_id))
        patient_id = next(key for key, p in data['pacientes'].items() if p['estado'] == 'activo')
        self.repo.registrar_consulta(patient_id, CONSULTA | {'fecha': '2026-10-20'})
        self.assertEqual(len(self.repo.obtener_historial(patient_id)['consultas']), 2)
        with self.assertRaises(Conflicto):
            self.repo.registrar_paciente({k: data['pacientes'][patient_id][k] for k in PACIENTE})

    def make_harness(self):
        return NoSQLHarness()
