import json
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

ENABLED = os.getenv("TEST_PEDIATRIA_MYSQL") == "1"
TUTOR = {"nombres": "DEMO", "apellidos": "Tutor", "parentesco": "Representante DEMO"}
VACUNA = {"vacuna_id": "PED-V-1", "fecha": "2020-01-02", "dosis": 1}
CONTROL = {"fecha": "2020-01-02", "peso_kg": "12.5", "talla_cm": "75"}


@skipUnless(ENABLED, "B4 real requiere TEST_PEDIATRIA_MYSQL=1 y destino aislado")
class MySQLRepositoryTests(RepositoryContract, TestCase):
    def setUp(self):
        from apps.historiales.testing.mysql import MySQLHarness
        self.harness = MySQLHarness()
        self.addCleanup(self.harness.close)
        self.context = ContextoClinico("pediatrico", "DEMO-U", "admin", "1")
        self.repo = self.harness.repo(self.context)
        self.service = HistorialService(self.context, self.repo, self.repo)

    def test_contract_duplicates_are_institutional(self):
        self.patient()
        with self.assertRaises(Conflicto):
            self.patient()
        with self.assertRaises(AccesoDenegado):
            self.harness.repo(ContextoClinico("hospital", "U", "admin", "1"))
        self.assertEqual(self.repo.listar_pacientes()["count"], 1)

    def test_contract_missing_and_foreign_parents(self):
        p, _, _, _, _ = self.chain()
        cases = (("obtener_historial", "P", ()), ("registrar_consulta", "P", (CONSULTA,)),
                 ("registrar_diagnostico", "C", (DIAGNOSTICO,)), ("registrar_tratamiento", "D", (TRATAMIENTO,)),
                 ("registrar_receta", "T", ({"medicamento_id": "PED-M-1", "dosis": "D", "frecuencia": "F"},)),
                 ("archivar_paciente", "P", ("DEMO",)))
        for operation, kind, args in cases:
            for key in (f"PED-{kind}-2147483647", f"H-{kind}-1", "1", "PED-P-0001", "PED-P-9999999999999"):
                with self.subTest(operation=operation, key=key), self.assertRaises(RecursoNoEncontrado):
                    getattr(self.repo, operation)(key, *args)
        self.assertEqual(len(self.repo.obtener_historial(p["id"])["consultas"]), 1)

    def test_health_auth_factory_and_professional(self):
        from apps.historiales.infrastructure.factory import AdapterFactory
        from apps.historiales.infrastructure.adapters.mysql_adapter import MySQLAdapter
        self.assertIsInstance(AdapterFactory.create_clinical(self.context), MySQLAdapter)
        self.assertTrue(self.harness.repo(None).health_check())
        with self.assertRaises(NoAutenticado):
            self.harness.repo(None).listar_pacientes()
        p = self.patient()
        for professional in (None, "missing", "2147483647"):
            repo = self.harness.repo(ContextoClinico("pediatrico", "U", "medico", professional))
            with self.assertRaises(AccesoDenegado):
                repo.registrar_consulta(p["id"], CONSULTA)
        self.harness.sql("UPDATE medico SET estado='inactivo' WHERE id=1")
        with self.assertRaises(AccesoDenegado):
            self.repo.registrar_consulta(p["id"], CONSULTA)
        self.assertEqual(self.repo.obtener_historial(p["id"])["consultas"], [])

    def test_actual_runtime_cannot_ddl_delete_or_read_legacy_passwords(self):
        import mysql.connector
        for sql in ("SELECT contrasena FROM usuario", "DELETE FROM paciente", "CREATE TABLE forbidden(id INT)",
                    "UPDATE medico SET estado='inactivo'", "INSERT INTO medicamento(nombre) VALUES('forbidden')"):
            with self.subTest(sql=sql), self.assertRaises(mysql.connector.Error):
                with self.harness.connect(runtime=True) as conn, conn.cursor() as c:
                    c.execute(sql)
        self.chain()

    def appointment(self, patient=1, professional=1, status="programada"):
        return self.harness.sql("INSERT INTO cita(paciente_id,medico_id,fecha,estado) VALUES(%s,%s,'2020-01-01',%s)",
                                (patient, professional, status))

    def test_optional_appointments_and_patient_professional_uniqueness_and_rollback(self):
        p = self.patient()
        self.patient(identificacion="DEMO-2")
        self.repo.registrar_consulta(p["id"], CONSULTA)
        self.repo.registrar_consulta(p["id"], CONSULTA)
        for patient, professional, state in ((2, 1, "programada"), (1, 2, "programada"), (1, 1, "cancelada")):
            key = self.appointment(patient, professional, state)
            with self.assertRaises(Conflicto):
                self.repo.registrar_consulta(p["id"], CONSULTA | {"cita_id": f"PED-CITA-{key}"})
        key = self.appointment()
        data = CONSULTA | {"cita_id": f"PED-CITA-{key}"}
        self.repo.fail = True
        with self.assertRaises(PersistenciaNoDisponible):
            self.repo.registrar_consulta(p["id"], data)
        self.assertEqual(self.harness.sql("SELECT estado FROM cita WHERE id=%s", (key,)), [("programada",)])
        self.assertEqual(self.repo.registrar_consulta(p["id"], data)["fecha"], CONSULTA["fecha"])
        with self.assertRaises(Conflicto):
            self.repo.registrar_consulta(p["id"], data)

    def test_header_detail_atomicity_and_prescription_civil_date(self):
        from unittest.mock import patch
        p, _, _, t, _ = self.chain()
        before = self.repo.obtener_historial(p["id"])
        self.repo.header_fail = True
        data = {"medicamento_id": "PED-M-1", "dosis": "DEMO", "frecuencia": "DEMO"}
        with self.assertRaises(PersistenciaNoDisponible):
            self.repo.registrar_receta(t["id"], data)
        self.assertEqual(self.harness.sql("SELECT COUNT(*) FROM receta"), [(1,)])
        self.assertEqual(self.repo.obtener_historial(p["id"]), before)
        with patch("apps.historiales.infrastructure.adapters.mysql_clinical.hoy_guatemala", return_value=date(2021, 3, 4)):
            self.repo.registrar_receta(t["id"], data)
        self.assertEqual(self.harness.sql("SELECT fecha FROM receta ORDER BY id DESC LIMIT 1"), [(date(2021, 3, 4),)])

    def test_occurrence_shared_catalog_and_multidetail_history_keep_exact_branches(self):
        p, c1, d1, t1, r1 = self.chain()
        c2 = self.repo.registrar_consulta(p["id"], CONSULTA)
        d2 = self.repo.registrar_diagnostico(c2["id"], DIAGNOSTICO)
        t2 = self.repo.registrar_tratamiento(d2["id"], TRATAMIENTO)
        self.assertEqual(self.harness.sql("SELECT COUNT(*) FROM diagnostico"), [(1,)])
        self.assertNotEqual(d1["id"], d2["id"])
        self.harness.sql("INSERT INTO detalle_receta(receta_id,medicamento_id,dosis,frecuencia) VALUES(1,1,'DEMO2','DEMO2')")
        history = self.repo.obtener_historial(p["id"])["consultas"]
        rows = history[0]["diagnosticos"][0]["tratamientos"][0]["recetas"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({r["id"] for r in rows}), 2)
        self.assertTrue(all(r["tratamiento_id"] == t1["id"] for r in rows))
        self.assertEqual(history[1]["diagnosticos"][0]["tratamientos"][0]["id"], t2["id"])
        self.assertEqual(history[1]["diagnosticos"][0]["tratamientos"][0]["recetas"], [])

    def test_database_rejects_cross_consultation_foreign_keys(self):
        import mysql.connector
        p, _, _, _, _ = self.chain()
        self.repo.registrar_consulta(p["id"], CONSULTA)
        for statement in (
            "INSERT INTO tratamiento(consulta_id,consulta_diagnostico_id) VALUES(2,1)",
            "INSERT INTO receta(consulta_id,tratamiento_id,fecha) VALUES(2,1,'2020-01-02')",
            "INSERT INTO consulta(paciente_id,medico_id,fecha,cita_id) VALUES(1,1,'2020-01-02',999)",
        ):
            with self.assertRaises(mysql.connector.IntegrityError):
                self.harness.sql(statement)

    def test_catalog_exact_unicode_and_disabled_medication(self):
        self.harness.sql("INSERT INTO medicamento(nombre,estado) VALUES('DEMO oculto','inactivo'),('Á%_ DEMO','activo')")
        self.assertEqual(self.repo.listar_medicamentos(q="a\u0301%_")["count"], 1)
        self.assertEqual(self.repo.listar_medicamentos(q="al")["count"], 0)
        self.assertEqual(self.repo.listar_medicamentos()["count"], 2)
        p, _, _, t, _ = self.chain()
        before = self.repo.obtener_historial(p["id"])
        with self.assertRaises(RecursoNoEncontrado):
            self.repo.registrar_receta(t["id"], {"medicamento_id": "PED-M-2", "dosis": "D", "frecuencia": "F"})
        self.assertEqual(self.repo.obtener_historial(p["id"]), before)

    def test_specializations_persist_json_and_archive_preserves_and_blocks(self):
        p = self.patient()
        tutor = self.repo.registrar_tutor(p["id"], TUTOR)
        vaccine = self.repo.registrar_vacuna(p["id"], VACUNA)
        growth = self.repo.registrar_crecimiento(p["id"], CONTROL)
        follow = self.repo.obtener_seguimiento(p["id"])
        self.assertEqual(json.loads(json.dumps(follow)), follow)
        self.assertEqual(follow["tutores"][0], tutor | {"parentesco_legacy": None})
        self.assertEqual(follow["vacunas"], [vaccine])
        self.assertEqual(follow["crecimiento"][0], growth | {"mediciones_legacy": dict.fromkeys(("peso", "talla", "altura", "percentil"))})
        self.assertEqual((growth["peso_kg"], growth["talla_cm"]), ("12.50", "75.00"))
        self.assertEqual(self.harness.sql("SELECT medico_id FROM aplicacion_vacuna UNION ALL SELECT medico_id FROM control_de_crecimiento"), [(1,), (1,)])
        self.assertEqual(self.repo.listar_vacunas()["results"][0]["id"], "PED-V-1")
        self.repo.archivar_paciente(p["id"], "DEMO")
        for method, body in (("registrar_tutor", TUTOR), ("registrar_vacuna", VACUNA), ("registrar_crecimiento", CONTROL)):
            with self.assertRaises(Conflicto):
                getattr(self.repo, method)(p["id"], body)
        self.assertEqual(self.repo.obtener_seguimiento(p["id"]), follow)

    def test_specialization_validation_permissions_and_atomic_rollback(self):
        p = self.patient()
        for value in ("0", "-1", "1.001", "NaN", "Infinity", 12.5, True, "10000", "1e2"):
            with self.subTest(value=value), self.assertRaises(DatosInvalidos):
                self.repo.registrar_crecimiento(p["id"], CONTROL | {"peso_kg": value})
        for body in (VACUNA | {"dosis": True}, VACUNA | {"dosis": 0}, VACUNA | {"fecha": "2999-01-01"}, VACUNA | {"medico_id": "1"}):
            with self.assertRaises(DatosInvalidos):
                self.repo.registrar_vacuna(p["id"], body)
        with self.assertRaises(RecursoNoEncontrado):
            self.repo.registrar_vacuna(p["id"], VACUNA | {"vacuna_id": "PED-V-999"})
        for method, body in (("registrar_tutor", TUTOR), ("registrar_vacuna", VACUNA), ("registrar_crecimiento", CONTROL)):
            before = self.repo.obtener_seguimiento(p["id"])
            self.repo.fail = True
            with self.assertRaises(PersistenciaNoDisponible):
                getattr(self.repo, method)(p["id"], body)
            self.assertEqual(self.repo.obtener_seguimiento(p["id"]), before)
        self.assertEqual(self.harness.sql("SELECT COUNT(*) FROM tutor"), [(0,)])
        secretary = self.harness.repo(ContextoClinico("pediatrico", "U", "secretaria"))
        secretary.registrar_tutor(p["id"], TUTOR)
        with self.assertRaises(AccesoDenegado):
            secretary.registrar_vacuna(p["id"], VACUNA)
        with self.assertRaises(AccesoDenegado):
            secretary.obtener_seguimiento(p["id"])

    def test_real_lock_wait_both_orders_and_writer_rollback(self):
        for archive_first, fail in ((True, False), (False, False), (False, True)):
            p = self.patient(identificacion=f"RACE-{archive_first}-{fail}")
            first = self.harness.repo(self.context)
            peer = self.harness.repo(self.context)
            entered, release = Event(), Event()
            self.harness.gate_next(first, entered, release)
            first.fail = fail
            a_call = lambda: first.archivar_paciente(p["id"], "DEMO") if archive_first else first.registrar_crecimiento(p["id"], CONTROL)
            b_call = lambda: peer.registrar_crecimiento(p["id"], CONTROL) if archive_first else peer.archivar_paciente(p["id"], "DEMO")
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(a_call)
                try:
                    self.assertTrue(entered.wait(5))
                    b = pool.submit(b_call)
                    deadline, waiting = monotonic()+4, False
                    while monotonic() < deadline:
                        # Server evidence, not a sleep pretending to prove locking.
                        rows = self.harness.sql("""SELECT COUNT(*) FROM performance_schema.data_lock_waits w
                            JOIN performance_schema.threads t ON t.thread_id=w.requesting_thread_id
                            WHERE t.processlist_id=%s""", (getattr(peer, "last_pid", -1),))
                        if rows[0][0]:
                            waiting = True
                            break
                    self.assertTrue(waiting, "MySQL did not report the competing root lock")
                finally:
                    release.set()
                if fail:
                    with self.assertRaises(PersistenciaNoDisponible):
                        a.result(timeout=10)
                else:
                    a.result(timeout=10)
                if archive_first:
                    with self.assertRaises(Conflicto):
                        b.result(timeout=10)
                else:
                    b.result(timeout=10)
            history = self.repo.obtener_seguimiento(p["id"])
            self.assertEqual(len(history["crecimiento"]), 0 if archive_first or fail else 1)
            self.assertEqual(self.repo.obtener_historial(p["id"])["paciente"]["estado"], "archivado")

    def test_duplicate_race_returns_one_patient_and_one_conflict(self):
        barrier = Barrier(2)
        def create():
            barrier.wait(timeout=5)
            try:
                return self.harness.repo(self.context).registrar_paciente(PACIENTE)
            except Conflicto:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(self.repo.listar_pacientes()["count"], 1)

    def test_read_snapshot_remains_coherent_while_another_connection_commits(self):
        p = self.patient()
        entered, release = Event(), Event()
        original = self.repo._patient_dto
        def gated(row):
            entered.set()
            if not release.wait(10):
                raise AssertionError("Snapshot gate timed out")
            return original(row)
        self.repo._patient_dto = gated
        peer = self.harness.repo(self.context)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.repo.obtener_historial, p["id"])
            try:
                self.assertTrue(entered.wait(5))
                peer.registrar_consulta(p["id"], CONSULTA)
            finally:
                release.set()
            self.assertEqual(pending.result(timeout=10)["consultas"], [])
        self.repo._patient_dto = original
        self.assertEqual(len(self.repo.obtener_historial(p["id"])["consultas"]), 1)

    def test_raw_input_is_validated_and_sql_metacharacters_remain_literal(self):
        with self.assertRaises(DatosInvalidos):
            self.repo.registrar_paciente(PACIENTE | {"institucion": "hospital"})
        p = self.patient(nombres="O'Neil; DROP TABLE paciente; --")
        self.assertEqual(self.repo.listar_pacientes(q="O'Neil;")["results"], [p])
        self.assertEqual(self.repo.listar_pacientes(q="% OR 1=1 --")["count"], 0)

    def test_history_orders_string_ids_after_nine_without_truncation(self):
        p = self.patient()
        for _ in range(12):
            self.repo.registrar_consulta(p["id"], CONSULTA)
        ids = [r["id"] for r in self.repo.obtener_historial(p["id"])["consultas"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), 12)


@skipUnless(ENABLED and os.getenv("TEST_HOSPITAL_POSTGRES") == "1", "Requiere ambos proveedores SQL reales")
class SQLInstitutionIsolationTests(TestCase):
    def test_same_identification_is_separate_and_foreign_ids_cannot_cross_any_parent(self):
        from apps.historiales.testing.mysql import MySQLHarness
        from apps.historiales.testing.postgres import PostgreSQLHarness
        providers = []
        for institution, constructor in (("pediatrico", MySQLHarness), ("hospital", PostgreSQLHarness)):
            harness = constructor()
            self.addCleanup(harness.close)
            providers.append(harness.repo(ContextoClinico(institution, "U", "admin", "1")))
        patients = [r.registrar_paciente(PACIENTE) for r in providers]
        chains = []
        for repo, p in zip(providers, patients):
            c = repo.registrar_consulta(p["id"], CONSULTA)
            d = repo.registrar_diagnostico(c["id"], DIAGNOSTICO)
            t = repo.registrar_tratamiento(d["id"], TRATAMIENTO)
            chains.append((p, c, d, t))
        for own, foreign in ((0, 1), (1, 0)):
            repo = providers[own]
            p, c, d, t = chains[foreign]
            medicine = repo.listar_medicamentos()["results"][0]["id"]
            cases = (("obtener_historial", p["id"], ()), ("archivar_paciente", p["id"], ("DEMO",)),
                     ("registrar_consulta", p["id"], (CONSULTA,)), ("registrar_diagnostico", c["id"], (DIAGNOSTICO,)),
                     ("registrar_tratamiento", d["id"], (TRATAMIENTO,)),
                     ("registrar_receta", t["id"], ({"medicamento_id": medicine, "dosis": "D", "frecuencia": "F"},)))
            for method, key, args in cases:
                with self.subTest(method=method, institution=own), self.assertRaises(RecursoNoEncontrado):
                    getattr(repo, method)(key, *args)
            self.assertEqual(repo.listar_pacientes()["count"], 1)
