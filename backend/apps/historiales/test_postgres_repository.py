import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier, Event
from time import monotonic
from unittest import TestCase, skipUnless

from apps.historiales.application.clinical import HistorialService
from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import (
    AccesoDenegado, Conflicto, DatosInvalidos, NoAutenticado,
    PersistenciaNoDisponible, RecursoNoEncontrado,
)
from apps.historiales.testing.repository_contract import RepositoryContract, PACIENTE, CONSULTA, DIAGNOSTICO, TRATAMIENTO

ENABLED = os.getenv("TEST_HOSPITAL_POSTGRES") == "1"


@skipUnless(ENABLED, "B3 real requiere TEST_HOSPITAL_POSTGRES=1 y destino aislado")
class PostgreSQLRepositoryTests(RepositoryContract, TestCase):
    def setUp(self):
        from apps.historiales.testing.postgres import PostgreSQLHarness
        self.harness = PostgreSQLHarness()
        self.addCleanup(self.harness.close)
        self.context = ContextoClinico("hospital", "DEMO-U", "admin", "1")
        self.other_context = ContextoClinico("pediatrico", "DEMO-U2", "admin", "1")
        self.repo = self.harness.repo(self.context)
        self.service = HistorialService(self.context, self.repo, self.repo)

    def test_contract_duplicates_are_institutional(self):
        """Hospital is a single-institution provider; the other engine belongs to B4.

        Verify duplicate in the real hospital and reject a foreign construction.
        No fake MySQL repository is substituted to claim two-engine coverage.
        """
        self.patient()
        with self.assertRaises(Conflicto):
            self.patient()
        with self.assertRaises(AccesoDenegado):
            self.harness.repo(self.other_context)
        self.assertEqual(self.repo.listar_pacientes()["count"], 1)

    def test_contract_missing_and_foreign_parents(self):
        p, c, d, t, _ = self.chain()
        cases = (("obtener_historial", "P", ()), ("registrar_consulta", "P", (CONSULTA,)),
                 ("registrar_diagnostico", "C", (DIAGNOSTICO,)), ("registrar_tratamiento", "D", (TRATAMIENTO,)),
                 ("registrar_receta", "T", ({"medicamento_id": "H-M-1", "dosis": "D", "frecuencia": "F"},)),
                 ("archivar_paciente", "P", ("DEMO",)))
        for operation, kind, args in cases:
            for key in (f"H-{kind}-2147483647", f"OTRA-{kind}-1", "1", "H-P-0001", "H-P-999999999999999"):
                with self.subTest(operation=operation, key=key), self.assertRaises(RecursoNoEncontrado):
                    getattr(self.repo, operation)(key, *args)
        self.assertEqual(len(self.repo.obtener_historial(p["id"])["consultas"]), 1)

    def test_health_without_context_and_clinical_without_context_denied(self):
        repo = self.harness.repo(None)
        self.assertTrue(repo.health_check())
        with self.assertRaises(NoAutenticado):
            repo.listar_pacientes()

    def test_runtime_privileges_allow_operations_without_owner_or_legacy_credentials(self):
        with self.harness.connect(runtime=True) as conn:
            row = conn.execute("""SELECT current_user,rolsuper,rolcreatedb,rolcreaterole
                                FROM pg_roles WHERE rolname=current_user""").fetchone()
            self.assertEqual(row, (self.harness.role, False, False, False))
            self.assertFalse(conn.execute("SELECT has_schema_privilege(current_schema(),'CREATE')").fetchone()[0])
            self.assertFalse(conn.execute("SELECT has_table_privilege('usuario','SELECT')").fetchone()[0])
            self.assertFalse(conn.execute("SELECT has_table_privilege('paciente','DELETE')").fetchone()[0])
        self.chain()  # Same real provider, now using only the limited runtime grants.

    def test_fresh_schema_accepts_incremental_migrations_idempotently(self):
        with self.harness.connect() as conn:
            for phase in ("001_expand.sql", "002_finalize.sql"):
                conn.execute((self.harness.schema_dir / "migrations" / phase).read_text(encoding="utf-8"))
            self.assertEqual(conn.execute("SELECT count(*) FROM hospital_schema_version").fetchone()[0], 1)
        self.chain()

    def test_factory_selects_real_hospital_provider(self):
        from apps.historiales.infrastructure.factory import AdapterFactory
        from apps.historiales.infrastructure.adapters.postgres_adapter import PostgreSQLAdapter
        self.assertIsInstance(AdapterFactory.create_clinical(self.context), PostgreSQLAdapter)

    def test_professional_must_exist_and_be_enabled_and_is_bound_to_consultation(self):
        p = self.patient()
        for professional in (None, "DEMO-no-existe", "2147483647"):
            repo = self.harness.repo(ContextoClinico("hospital", "U", "medico", professional))
            with self.subTest(professional=professional), self.assertRaises(AccesoDenegado):
                repo.registrar_consulta(p["id"], CONSULTA)
        with self.harness.connect() as conn:
            conn.execute("UPDATE medico SET habilitado=false WHERE id_medico=1")
        with self.assertRaises(AccesoDenegado):
            self.repo.registrar_consulta(p["id"], CONSULTA)
        with self.harness.connect() as conn:
            conn.execute("UPDATE medico SET habilitado=true WHERE id_medico=1")
        self.repo.registrar_consulta(p["id"], CONSULTA)
        with self.harness.connect() as conn:
            self.assertEqual(conn.execute("SELECT id_medico FROM consulta").fetchone()[0], 1)

    def appointment(self, patient=1, professional=1, status="programada"):
        with self.harness.connect() as conn:
            return conn.execute("""INSERT INTO cita(id_paciente,id_medico,fecha_hora,estado)
                                VALUES(%s,%s,'2020-01-01 12:00:00',%s) RETURNING id_cita""", (patient, professional, status)).fetchone()[0]

    def test_appointments_require_matching_patient_professional_and_available_state(self):
        p = self.patient()
        self.patient(identificacion="DEMO-2")
        for patient, professional, state in ((2, 1, "programada"), (1, 2, "programada"), (1, 1, "cancelada")):
            appointment = self.appointment(patient, professional, state)
            with self.subTest(patient=patient, professional=professional, state=state), self.assertRaises(Conflicto):
                self.repo.registrar_consulta(p["id"], CONSULTA | {"cita_id": f"H-CITA-{appointment}"})
        appointment = self.appointment()
        created = self.repo.registrar_consulta(p["id"], CONSULTA | {"cita_id": f"H-CITA-{appointment}"})
        self.assertEqual(created["fecha"], CONSULTA["fecha"])
        with self.assertRaises(Conflicto):
            self.repo.registrar_consulta(p["id"], CONSULTA | {"cita_id": f"H-CITA-{appointment}"})

    def test_failed_consultation_rolls_back_appointment_consumption(self):
        p = self.patient()
        appointment = self.appointment()
        self.harness.fail_next(self.repo)
        with self.assertRaises(PersistenciaNoDisponible):
            self.repo.registrar_consulta(p["id"], CONSULTA | {"cita_id": f"H-CITA-{appointment}"})
        with self.harness.connect() as conn:
            self.assertEqual(conn.execute("SELECT estado FROM cita WHERE id_cita=%s", (appointment,)).fetchone()[0], "programada")
        self.assertEqual(self.repo.obtener_historial(p["id"])["consultas"], [])

    def test_raw_port_rejects_client_identity_and_sql_injection_is_literal(self):
        with self.assertRaises(DatosInvalidos):
            self.repo.registrar_paciente(PACIENTE | {"medico_id": "2"})
        p = self.patient(nombres="O'Neil; DROP TABLE paciente; --")
        self.assertEqual(self.repo.listar_pacientes(q="o'neil")["results"][0], p)
        self.assertEqual(self.repo.listar_pacientes(q="%'; DROP TABLE paciente")["count"], 0)

    def test_all_child_writes_and_archive_are_denied_by_role(self):
        p, c, d, t, _ = self.chain()
        repo = self.harness.repo(ContextoClinico("hospital", "U", "enfermero", "1"))
        for method, args in (("registrar_consulta", (p["id"], CONSULTA)), ("registrar_diagnostico", (c["id"], DIAGNOSTICO)),
                             ("registrar_tratamiento", (d["id"], TRATAMIENTO)),
                             ("registrar_receta", (t["id"], {"medicamento_id": "H-M-1", "dosis": "D", "frecuencia": "F"})),
                             ("archivar_paciente", (p["id"], "DEMO"))):
            with self.subTest(method=method), self.assertRaises(AccesoDenegado):
                getattr(repo, method)(*args)

    def test_duplicate_creation_race_is_atomic(self):
        barrier = Barrier(2)
        def write():
            barrier.wait(timeout=5)
            try:
                return self.harness.repo(self.context).registrar_paciente(PACIENTE)
            except Conflicto:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: write(), range(2)))
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(self.repo.listar_pacientes()["count"], 1)

    def test_postgresql_confirms_second_client_is_waiting_on_root_lock(self):
        p = self.patient()
        peer = self.harness.repo(self.context)
        entered, release = Event(), Event()
        self.harness.gate_next(self.repo, entered, release)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.repo.archivar_paciente, p["id"], "DEMO")
            try:
                self.assertTrue(entered.wait(5))
                second = pool.submit(peer.registrar_consulta, p["id"], CONSULTA)
                deadline = monotonic()+3
                blocked = False
                while monotonic() < deadline:
                    pid = getattr(peer, "last_pid", None)
                    if pid:
                        with self.harness.connect() as conn:
                            blockers = conn.execute("SELECT pg_blocking_pids(%s)", (pid,)).fetchone()[0]
                        if self.repo.last_pid in blockers:
                            blocked = True
                            break
                    Event().wait(0.01)
                self.assertTrue(blocked, "Server never observed competing root lock")
            finally:
                release.set()
            first.result(timeout=10)
            with self.assertRaises(Conflicto):
                second.result(timeout=10)
        self.assertEqual(self.repo.obtener_historial(p["id"])["consultas"], [])

    def admission(self, patient_id, bed="H-CAMA-1"):
        return self.repo.ingresar_paciente(patient_id, {"cama_id": bed, "tipo_ingreso": "DEMO",
                                                       "fecha_hora_ingreso": "2020-01-01T12:00:00Z"})

    def test_hospital_admission_discharge_and_archive_preserve_history(self):
        p = self.patient()
        admission = self.admission(p["id"])
        self.assertIsNone(admission["fecha_hora_alta"])
        with self.assertRaises(Conflicto):
            self.repo.archivar_paciente(p["id"], "DEMO")
        with self.assertRaises(Conflicto):
            self.admission(p["id"], "H-CAMA-2")
        with self.assertRaises(DatosInvalidos):
            self.repo.dar_alta(admission["id"], "2019-01-01T00:00:00Z")
        discharged = self.repo.dar_alta(admission["id"], "2020-01-02T12:00:00Z")
        self.assertEqual(discharged, self.repo.dar_alta(admission["id"], "2020-01-02T12:00:00Z"))
        with self.assertRaises(Conflicto):
            self.repo.dar_alta(admission["id"], "2020-01-03T12:00:00Z")
        self.repo.archivar_paciente(p["id"], "DEMO")
        self.assertEqual(self.repo.listar_ingresos(p["id"])["ingresos"], [discharged])
        with self.assertRaises(Conflicto):
            self.admission(p["id"])

    def test_hospital_occupied_bed_race_and_reuse_after_discharge(self):
        p = self.patient()
        other = self.patient(identificacion="DEMO-2")
        barrier = Barrier(2)
        def enter(patient_id):
            repo = self.harness.repo(self.context)
            barrier.wait(timeout=5)
            try:
                return repo.ingresar_paciente(patient_id, {"cama_id": "H-CAMA-1", "tipo_ingreso": "DEMO", "fecha_hora_ingreso": "2020-01-01T12:00:00Z"})
            except Conflicto:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(enter, (p["id"], other["id"])))
        self.assertEqual(results.count(None), 1)
        winner = next(r for r in results if r)
        self.repo.dar_alta(winner["id"], "2020-01-02T12:00:00Z")
        loser = other if winner["paciente_id"] == p["id"] else p
        self.assertEqual(self.admission(loser["id"])["cama_id"], "H-CAMA-1")

    def test_hospital_failure_rolls_back_admission_and_discharge(self):
        p = self.patient()
        self.harness.fail_next(self.repo)
        with self.assertRaises(PersistenciaNoDisponible):
            self.admission(p["id"])
        self.assertEqual(self.repo.listar_ingresos(p["id"])["ingresos"], [])
        admission = self.admission(p["id"])
        self.harness.fail_next(self.repo)
        with self.assertRaises(PersistenciaNoDisponible):
            self.repo.dar_alta(admission["id"], "2020-01-02T00:00:00Z")
        self.assertEqual(self.repo.listar_ingresos(p["id"])["ingresos"], [admission])

    def test_history_snapshot_does_not_mix_concurrent_commits(self):
        from unittest.mock import patch
        p = self.patient()
        consultation = self.repo.registrar_consulta(p["id"], CONSULTA)
        peer = self.harness.repo(self.context)
        entered, release = Event(), Event()
        original = self.repo._consultation_dto

        def pause(row):
            result = original(row)
            entered.set()
            if not release.wait(5):
                raise AssertionError("Read gate timed out")
            return result

        with patch.object(self.repo, "_consultation_dto", side_effect=pause), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.repo.obtener_historial, p["id"])
            try:
                self.assertTrue(entered.wait(5))
                peer.registrar_diagnostico(consultation["id"], DIAGNOSTICO)
            finally:
                release.set()
            self.assertEqual(future.result(timeout=10)["consultas"][0]["diagnosticos"], [])
        self.assertEqual(len(self.repo.obtener_historial(p["id"])["consultas"][0]["diagnosticos"]), 1)

    def test_child_order_is_string_order_even_with_multi_digit_ids(self):
        p = self.patient()
        consultation = self.repo.registrar_consulta(p["id"], CONSULTA)
        for _ in range(12):
            d = self.repo.registrar_diagnostico(consultation["id"], DIAGNOSTICO)
            self.repo.registrar_tratamiento(d["id"], TRATAMIENTO)
        diagnoses = self.repo.obtener_historial(p["id"])["consultas"][0]["diagnosticos"]
        ids = [d["id"] for d in diagnoses]
        self.assertEqual(ids, sorted(ids))
        self.assertLess(ids.index("H-D-10"), ids.index("H-D-2"))

    def test_archive_uses_guatemala_civil_date_and_requires_metadata(self):
        from unittest.mock import patch
        import psycopg
        p = self.patient()
        with patch("apps.historiales.infrastructure.adapters.postgres_clinical.hoy_guatemala", return_value=date(2026, 10, 21)):
            self.assertEqual(self.repo.archivar_paciente(p["id"], "DEMO")["fecha_archivo"], "2026-10-21")
        with self.assertRaises(psycopg.errors.CheckViolation), self.harness.connect() as conn:
            conn.execute("UPDATE paciente SET motivo_baja=NULL")

    def test_database_fk_rejects_appointment_of_another_patient(self):
        import psycopg
        self.patient()
        self.patient(identificacion="DEMO-2")
        appointment = self.appointment(patient=2)
        with self.assertRaises(psycopg.errors.ForeignKeyViolation), self.harness.connect() as conn:
            conn.execute("""INSERT INTO consulta(id_paciente,id_medico,id_cita,fecha,notas_evolucion)
                            VALUES(1,1,%s,'2020-01-01','DEMO')""", (appointment,))
