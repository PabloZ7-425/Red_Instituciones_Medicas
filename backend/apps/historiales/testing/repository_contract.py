"""Reusable unittest mixin. Implement make_harness(); see docs/pablo/B1_CONTRATOS.md.

All fixtures are synthetic. Each harness owns its isolated destination and cleanup.
No skipped transaction tests: providers must supply real failure/concurrency hooks.
"""
import json
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from apps.historiales.application.clinical import HistorialService
from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import Conflicto, PersistenciaNoDisponible, RecursoNoEncontrado

PACIENTE = {"identificacion": "DEMO-0001", "nombres": "Paciente", "apellidos": "Álvarez",
            "fecha_nacimiento": "2000-01-01"}
CONSULTA = {"fecha": "2020-01-02", "notas_evolucion": "DEMO sin uso clínico"}
DIAGNOSTICO = {"codigo_cie10": "DEMO", "descripcion": "Diagnóstico sintético"}
TRATAMIENTO = {"indicaciones_generales": "DEMO no administrar"}


class RepositoryContract:
    institutions = ("hospital", "pediatrico")

    def setUp(self):
        super().setUp()
        self.harness = self.make_harness()
        self.addCleanup(self.harness.close)
        self.context = ContextoClinico(self.institutions[0], "DEMO-U", "admin", "DEMO-PRO")
        self.other_context = ContextoClinico(self.institutions[1], "DEMO-U2", "admin", "DEMO-PRO2")
        self.repo = self.harness.repo(self.context)
        self.other = self.harness.repo(self.other_context)
        self.service = HistorialService(self.context, self.repo, self.repo)

    def patient(self, **extra):
        return self.service.registrar_paciente(PACIENTE | extra)

    def chain(self):
        p = self.patient()
        c = self.service.registrar_consulta(p["id"], CONSULTA)
        d = self.service.registrar_diagnostico(c["id"], DIAGNOSTICO)
        t = self.service.registrar_tratamiento(d["id"], TRATAMIENTO)
        medicine = self.repo.listar_medicamentos()["results"][0]
        r = self.service.registrar_receta(t["id"], {"medicamento_id": medicine["id"], "dosis": "DEMO", "frecuencia": "DEMO"})
        return p, c, d, t, r

    def test_contract_chain_and_json_dtos(self):
        p, c, d, t, r = self.chain()
        self.assertEqual((c["paciente_id"], d["consulta_id"], t["diagnostico_id"], r["tratamiento_id"]),
                         (p["id"], c["id"], d["id"], t["id"]))
        self.assertIsNone(c["cita_id"])
        self.assertIsNone(r["via_administracion"])
        history = self.repo.obtener_historial(p["id"])
        self.assertEqual(json.loads(json.dumps(history)), history)
        def inspect(value):
            if isinstance(value, list):
                for item in value:
                    inspect(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(key, {"motor", "engine", "password", "contrasena", "_id", "$oid", "$date"})
                    if (key == "id" or key.endswith("_id")) and item is not None:
                        self.assertIsInstance(item, str)
                        self.assertTrue(item)
                    inspect(item)
        inspect(history)
        self.assertEqual(history["paciente"], p)
        actual_c = history["consultas"][0]
        actual_d = actual_c["diagnosticos"][0]
        actual_t = actual_d["tratamientos"][0]
        self.assertEqual(actual_t["recetas"], [r])
        self.assertEqual({k: v for k, v in actual_t.items() if k != "recetas"}, t)
        self.assertEqual({k: v for k, v in actual_d.items() if k != "tratamientos"}, d)
        self.assertEqual({k: v for k, v in actual_c.items() if k != "diagnosticos"}, c)
        for row in (p, c, d, t, r):
            self.assertIsInstance(row["id"], str)
            self.assertTrue(row["id"])

    def test_contract_duplicates_are_institutional(self):
        p = self.patient()
        with self.assertRaises(Conflicto):
            self.patient()
        self.other.registrar_paciente(PACIENTE)
        self.assertEqual(self.repo.listar_pacientes()["count"], 1)
        self.assertEqual(self.repo.obtener_historial(p["id"])["consultas"], [])

    def test_contract_search_prefix_nfc_literal_and_pagination(self):
        for number, name in enumerate(("Paciente", "A%_uno", "Axx", "A_otra", "A%dos")):
            self.patient(identificacion=f"DEMO-{number:04}", nombres=name)
        for q, expected in ((" pac ", 1), ("aci", 0), ("A%", 2), ("A_", 1), ("A%_", 1),
                            ("a\u0301l", 5), ("al", 0), ("DEMO-", 5), ("[", 0)):
            with self.subTest(q=q):
                page = self.service.listar_pacientes(q=q, limit=2, offset=1)
                self.assertEqual(page["count"], expected)
                self.assertEqual((page["limit"], page["offset"]), (2, 1))
                self.assertEqual(len(page["results"]), min(2, max(0, expected-1)))
        all_rows = self.repo.listar_pacientes()["results"]
        self.assertEqual(all_rows, sorted(all_rows, key=lambda p: (p["identificacion"], p["id"])))
        self.assertEqual(self.repo.listar_pacientes(offset=99)["results"], [])

    def test_contract_missing_and_foreign_parents(self):
        p, c, d, t, _ = self.chain()
        operations = (("obtener_historial", p["id"], ()), ("registrar_consulta", p["id"], (CONSULTA,)),
                      ("registrar_diagnostico", c["id"], (DIAGNOSTICO,)),
                      ("registrar_tratamiento", d["id"], (TRATAMIENTO,)),
                      ("registrar_receta", t["id"], ({"medicamento_id": "missing", "dosis": "D", "frecuencia": "D"},)),
                      ("archivar_paciente", p["id"], ("DEMO",)))
        for method, identifier, args in operations:
            for target in (identifier, "DEMO-no-existe"):
                with self.subTest(method=method, target=target), self.assertRaises(RecursoNoEncontrado):
                    getattr(self.other, method)(target, *args)
        self.assertEqual(self.other.listar_pacientes()["count"], 0)

    def test_contract_missing_references_leave_no_children(self):
        p, _, _, t, _ = self.chain()
        before = self.repo.obtener_historial(p["id"])
        with self.assertRaises(RecursoNoEncontrado):
            self.repo.registrar_receta(t["id"], {"medicamento_id": "DEMO-missing", "dosis": "D", "frecuencia": "D"})
        with self.assertRaises(RecursoNoEncontrado):
            self.repo.registrar_consulta(p["id"], CONSULTA | {"cita_id": "DEMO-missing"})
        self.assertEqual(self.repo.obtener_historial(p["id"]), before)

    def test_contract_archive_idempotency_and_history(self):
        p, c, d, t, _ = self.chain()
        before = self.repo.obtener_historial(p["id"])
        archived = self.repo.archivar_paciente(p["id"], "DEMO baja")
        self.assertEqual(archived, self.repo.archivar_paciente(p["id"], "DEMO baja"))
        self.assertEqual(archived["estado"], "archivado")
        self.assertEqual(archived["motivo_archivo"], "DEMO baja")
        self.assertRegex(archived["fecha_archivo"], r"^\d{4}-\d{2}-\d{2}$")
        date.fromisoformat(archived["fecha_archivo"])
        with self.assertRaises(Conflicto):
            self.repo.archivar_paciente(p["id"], "otro motivo")
        for method, key, dto in (("registrar_consulta", p["id"], CONSULTA),
                                 ("registrar_diagnostico", c["id"], DIAGNOSTICO),
                                 ("registrar_tratamiento", d["id"], TRATAMIENTO),
                                 ("registrar_receta", t["id"], {"medicamento_id": "missing"})):
            with self.subTest(method=method), self.assertRaises(Conflicto):
                getattr(self.repo, method)(key, dto)
        self.assertEqual(self.repo.obtener_historial(p["id"])["consultas"], before["consultas"])
        self.assertEqual(self.repo.listar_pacientes()["results"][0], archived)

    def test_contract_inactive_rejects_writes(self):
        p = self.patient()
        self.harness.inactive(self.repo, p["id"])
        with self.assertRaises(Conflicto):
            self.repo.registrar_consulta(p["id"], CONSULTA)
        self.assertEqual(self.repo.listar_pacientes()["results"][0]["estado"], "inactivo")

    def test_contract_rollback_after_intermediate_failure(self):
        p, c, d, t, _ = self.chain()
        before = self.repo.obtener_historial(p["id"])
        medicine = self.repo.listar_medicamentos()["results"][0]["id"]
        for method, args in (("registrar_consulta", (p["id"], CONSULTA)),
                             ("registrar_diagnostico", (c["id"], DIAGNOSTICO)),
                             ("registrar_tratamiento", (d["id"], TRATAMIENTO)),
                             ("registrar_receta", (t["id"], {"medicamento_id": medicine, "dosis": "D", "frecuencia": "D"})),
                             ("archivar_paciente", (p["id"], "DEMO"))):
            self.harness.fail_next(self.repo)
            with self.assertRaises(PersistenciaNoDisponible):
                getattr(self.repo, method)(*args)
            self.assertEqual(self.repo.obtener_historial(p["id"]), before)

    def test_contract_failed_patient_creation_leaves_no_patient(self):
        self.harness.fail_next(self.repo)
        with self.assertRaises(PersistenciaNoDisponible):
            self.patient()
        self.assertEqual(self.repo.listar_pacientes()["count"], 0)
        self.patient()  # No phantom uniqueness conflict after rollback.

    def test_contract_diagnoses_are_occurrences(self):
        p = self.patient()
        c1 = self.repo.registrar_consulta(p["id"], CONSULTA)
        c2 = self.repo.registrar_consulta(p["id"], CONSULTA)
        d1 = self.repo.registrar_diagnostico(c1["id"], DIAGNOSTICO)
        d2 = self.repo.registrar_diagnostico(c2["id"], DIAGNOSTICO)
        self.assertNotEqual(d1["id"], d2["id"])
        t = self.repo.registrar_tratamiento(d2["id"], TRATAMIENTO)
        rows = self.repo.obtener_historial(p["id"])["consultas"]
        self.assertEqual(rows[0]["diagnosticos"][0]["tratamientos"], [])
        self.assertEqual(rows[1]["diagnosticos"][0]["tratamientos"][0]["id"], t["id"])

    def _race(self, archive_first):
        p = self.patient()
        peer = self.harness.repo(self.context)  # MUST be an independent connection/client.
        entered, release, requested = Event(), Event(), Event()
        self.harness.gate_next(self.repo, entered, release)
        first = (lambda: self.repo.archivar_paciente(p["id"], "DEMO")) if archive_first else (
            lambda: self.repo.registrar_consulta(p["id"], CONSULTA))

        def second():
            requested.set()
            if archive_first:
                return peer.registrar_consulta(p["id"], CONSULTA)
            return peer.archivar_paciente(p["id"], "DEMO")

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(first)
            try:
                self.assertTrue(entered.wait(5), "First transaction never reached its root lock")
                b = pool.submit(second)
                self.assertTrue(requested.wait(5))
            finally:
                release.set()
            a.result(timeout=10)
            if archive_first:
                with self.assertRaises(Conflicto):
                    b.result(timeout=10)
            else:
                b.result(timeout=10)
        history = self.repo.obtener_historial(p["id"])
        self.assertEqual(history["paciente"]["estado"], "archivado")
        self.assertEqual(len(history["consultas"]), 0 if archive_first else 1)

    def test_contract_archive_commits_first(self):
        self._race(True)

    def test_contract_write_commits_first(self):
        self._race(False)

    def test_contract_history_order_and_empty_branches(self):
        p = self.patient()
        self.assertEqual(self.repo.obtener_historial(p["id"])["consultas"], [])
        for when in ("2020-02-01", "2020-01-01", "2020-01-01"):
            c = self.repo.registrar_consulta(p["id"], CONSULTA | {"fecha": when})
            for _ in range(3):
                self.repo.registrar_diagnostico(c["id"], DIAGNOSTICO)
        rows = self.repo.obtener_historial(p["id"])["consultas"]
        self.assertEqual(rows, sorted(rows, key=lambda c: (c["fecha"], c["id"])))
        for c in rows:
            self.assertEqual(c["diagnosticos"], sorted(c["diagnosticos"], key=lambda d: d["id"]))
            self.assertTrue(all(d["tratamientos"] == [] for d in c["diagnosticos"]))

    def test_contract_catalog(self):
        page = self.service.listar_medicamentos()
        self.assertGreater(page["count"], 0)
        self.assertEqual(page["results"], sorted(page["results"], key=lambda m: (m["nombre"].strip().lower(), m["id"])))
        for medicine in page["results"]:
            self.assertEqual(set(medicine), {"id", "nombre", "presentacion"})
            self.assertIsInstance(medicine["id"], str)
            self.assertTrue(medicine["id"])
        self.assertEqual(self.service.listar_medicamentos(q="DEMO-no-existe")["count"], 0)
