import copy
from datetime import date, datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import uuid4
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clinical_model as model
import export_demo
import seed_clinical_demo
import seed_demo


class ClinicalModelTests(unittest.TestCase):
    def test_dtos_preserve_contract_fields_without_storage_metadata(self):
        reference = Path(__file__).resolve().parents[3] / "backend/apps/historiales/fixtures/contrato_v1.json"
        cases = {c["id"]: c["response"]["body"] for c in json.loads(reference.read_text())["cases"]}
        data = model.load_fixture()
        for collection, operation in {"pacientes": "API-04", "consultas": "API-06", "diagnosticos": "API-07", "tratamientos": "API-08", "recetas": "API-09"}.items():
            for key, doc in data[collection].items():
                result = model.project_document(collection, key, doc)
                self.assertEqual(set(result), set(cases[operation]))
                self.assertEqual(result["id"], key)
                self.assertNotIn("institucion", result)
                self.assertNotIn("profesional_id", result)
                self.assertEqual(json.loads(json.dumps(result)), result)
        for key, doc in data["medicamentos"].items():
            self.assertEqual(set(model.project_document("medicamentos", key, doc)), {"id", "nombre", "presentacion"})

    def test_repeated_code_keeps_occurrences_and_archived_history_separate(self):
        data = model.load_fixture()
        histories = [model.project_history(data, key) for key in data["pacientes"]]
        diagnoses = [h["consultas"][0]["diagnosticos"][0] for h in histories]
        self.assertEqual(diagnoses[0]["codigo_cie10"], diagnoses[1]["codigo_cie10"])
        self.assertNotEqual(diagnoses[0]["id"], diagnoses[1]["id"])
        self.assertEqual(histories[1]["paciente"]["estado"], "archivado")
        for history, diagnosis in zip(histories, diagnoses):
            treatment = diagnosis["tratamientos"][0]
            recipe = treatment["recetas"][0]
            self.assertEqual(diagnosis["consulta_id"], history["consultas"][0]["id"])
            self.assertEqual(treatment["diagnostico_id"], diagnosis["id"])
            self.assertEqual(recipe["tratamiento_id"], treatment["id"])
            self.assertIn(recipe["medicamento_id"], data["medicamentos"])

    def test_civil_date_is_not_inferred_from_utc_appointment(self):
        data = model.load_fixture()
        appointment = data["citas"]["DEMO-A1-CITA-001"]
        instant = datetime.fromisoformat(appointment["fecha_hora"].replace("Z", "+00:00"))
        self.assertEqual(instant.date().isoformat(), "2026-10-20")
        self.assertEqual(instant.astimezone(ZoneInfo("America/Guatemala")).date().isoformat(), "2026-10-19")
        entries = {(c, key): doc for c, key, doc in model.entries(data)}
        self.assertEqual(entries["consultas", "DEMO-A1-CON-001"]["fecha"], "2026-10-19")
        self.assertIsInstance(entries["citas", "DEMO-A1-CITA-001"]["fecha_hora"], datetime)
        self.assertEqual(entries["pacientes", "DEMO-A1-PAC-001"]["fecha_nacimiento"], "2001-02-03")

    def test_invalid_types_dates_lengths_states_and_prescriptions(self):
        cases = [
            ("pacientes", "identificacion", 123), ("pacientes", "identificacion", "DEMO-" + "x" * 20),
            ("pacientes", "fecha_nacimiento", "2001-02-30"), ("pacientes", "fecha_nacimiento", "2999-01-01"),
            ("pacientes", "estado", []), ("pacientes", "nombres", "x" * 101),
            ("consultas", "fecha", "2026-10-19T00:00:00.000Z"), ("consultas", "fecha", "2999-01-01"),
            ("consultas", "notas_evolucion", " "), ("consultas", "profesional_id", None),
            ("diagnosticos", "codigo_cie10", ""), ("diagnosticos", "descripcion", "x" * 5001),
            ("tratamientos", "indicaciones_generales", None), ("recetas", "dosis", ""),
            ("recetas", "frecuencia", "x" * 101), ("recetas", "via_administracion", 1),
            ("medicamentos", "nombre", "medicamento real"), ("medicamentos", "presentacion", []),
            ("citas", "fecha_hora", "2026-10-20T02:30:00-06:00"),
            ("procedimientos", "pieza", "99"), ("procedimientos", "estado", {}),
            ("pagos", "monto_centavos", True), ("pagos", "monto_centavos", -1), ("pagos", "moneda", "USD"),
        ]
        for collection, field, invalid in cases:
            with self.subTest(collection=collection, field=field, value=invalid):
                data = model.load_fixture()
                next(iter(data[collection].values()))[field] = invalid
                with self.assertRaises(ValueError):
                    model.validate(data, today=date(2026, 10, 20))

    def test_archive_metadata_duplicates_and_unknown_fields(self):
        data = model.load_fixture()
        data["pacientes"]["DEMO-A1-PAC-002"]["motivo_archivo"] = None
        with self.assertRaises(ValueError):
            model.validate(data)
        data = model.load_fixture()
        data["pacientes"]["DEMO-A1-PAC-002"]["identificacion"] = data["pacientes"]["DEMO-A1-PAC-001"]["identificacion"]
        with self.assertRaises(ValueError):
            model.validate(data)
        data = model.load_fixture()
        data["consultas"]["DEMO-A1-CON-001"]["motor"] = "otro"
        with self.assertRaises(ValueError):
            model.validate(data)

    def test_cross_patient_and_ambiguous_relationships_rejected(self):
        for collection, field, value in [
            ("consultas", "cita_id", "DEMO-A1-CITA-002"),
            ("diagnosticos", "consulta_id", "DEMO-A1-CON-002"),
            ("tratamientos", "diagnostico_id", "DEMO-A1-DIAG-002"),
            ("recetas", "tratamiento_id", "DEMO-A1-TRAT-002"),
            ("recetas", "medicamento_id", "DEMO-INEXISTENTE"),
            ("procedimientos", "tratamiento_id", "DEMO-A1-TRAT-002"),
            ("pagos", "procedimiento_id", "DEMO-A1-PROC-002"),
        ]:
            with self.subTest(collection=collection, field=field):
                data = model.load_fixture()
                next(iter(data[collection].values()))[field] = value
                with self.assertRaises(ValueError):
                    model.validate(data)

    def test_optional_appointment_and_temporary_teeth_are_supported(self):
        data = model.load_fixture()
        data["consultas"]["DEMO-A1-CON-001"]["cita_id"] = None
        data["procedimientos"]["DEMO-A1-PROC-001"]["pieza"] = "51"
        self.assertIs(model.validate(data), data)
        self.assertIsNone(model.project_document("recetas", "DEMO-A1-REC-001", data["recetas"]["DEMO-A1-REC-001"])["via_administracion"])

    def test_reservations_and_versions_are_deterministic(self):
        data = model.load_fixture()
        self.assertEqual(model.entries(data), model.entries(data))
        self.assertEqual(len(model.entries(data)), 20)
        claims = [(key, doc) for c, key, doc in model.entries(data) if c == "identificaciones"]
        self.assertEqual(len(claims), 2)
        self.assertEqual(len({key for key, _ in claims}), 2)
        self.assertTrue(all(d["seed_version"] == model.VERSION and d["schema_version"] == 2 and d["institucion"] == "odontologica" for _, _, d in model.entries(data)))

    def test_search_keys_normalize_nfc_without_losing_original_names(self):
        data = model.load_fixture()
        data["pacientes"]["DEMO-A1-PAC-001"]["nombres"] = "Jose\u0301"
        entries = {(c, key): doc for c, key, doc in model.entries(data)}
        patient = entries["pacientes", "DEMO-A1-PAC-001"]
        self.assertEqual(patient["nombres"], "Jose\u0301")
        self.assertEqual(patient["busqueda"]["nombres"], "josé")
        self.assertNotEqual(patient["busqueda"]["nombres"], "jose")
        self.assertEqual(entries["medicamentos", "DEMO-A1-MED-001"]["nombre_busqueda"], data["medicamentos"]["DEMO-A1-MED-001"]["nombre"].lower())


@unittest.skipUnless(os.getenv("FIRESTORE_EMULATOR_HOST"), "Requiere emulador local y SDK")
class ClinicalEmulatorTests(unittest.TestCase):
    def setUp(self):
        self.client = seed_demo.client_for_emulator()
        self.addCleanup(self.client.close)
        suffix = uuid4().hex[:8]
        raw = model.load_fixture()
        self.data = {c: {key + "-" + suffix: copy.deepcopy(doc) for key, doc in docs.items()} for c, docs in raw.items()}
        for collection, docs in self.data.items():
            for n, doc in enumerate(docs.values()):
                for field in list(doc):
                    if field.endswith("_id") and doc[field] is not None:
                        doc[field] += "-" + suffix
                if collection == "pacientes":
                    doc["identificacion"] = f"DEMO-A1-{n:02}-{suffix}"
        self.entries = model.entries(self.data)
        self.refs = [self.client.collection(c).document(key) for c, key, _ in self.entries]
        self.assertTrue(all(not ref.get(timeout=10).exists for ref in self.refs))
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for ref in self.refs:
            ref.delete(timeout=10)

    def test_write_read_repeat_and_typed_storage(self):
        self.assertEqual(seed_clinical_demo.seed(self.client, self.data), {"created": 20, "unchanged": 0})
        for ref, (_, _, expected) in zip(self.refs, self.entries):
            self.assertEqual(ref.get(timeout=10).to_dict(), expected)
        self.assertEqual(seed_clinical_demo.seed(self.client, self.data), {"created": 0, "unchanged": 20})
        from google.cloud.firestore_v1.base_query import FieldFilter
        patient_id = next(iter(self.data["pacientes"]))
        query = self.client.collection("consultas")
        for field, value in [("institucion", "odontologica"), ("schema_version", 2), ("paciente_id", patient_id)]:
            query = query.where(filter=FieldFilter(field, "==", value))
        snapshots = query.order_by("fecha").get(timeout=10)
        self.assertEqual([s.id for s in snapshots], [i for i, d in self.data["consultas"].items() if d["paciente_id"] == patient_id])

    def test_conflict_at_last_reservation_aborts_all_writes(self):
        self.refs[-1].create({"nota": "DEMO preservar"}, timeout=10)
        with self.assertRaises(ValueError):
            seed_clinical_demo.seed(self.client, self.data)
        self.assertTrue(all(not ref.get(timeout=10).exists for ref in self.refs[:-1]))
        self.assertEqual(self.refs[-1].get(timeout=10).to_dict(), {"nota": "DEMO preservar"})

    def test_existing_patient_without_claim_still_blocks_duplicate(self):
        ref = self.client.collection("pacientes").document("DEMO-COLLISION-" + uuid4().hex)
        self.refs.append(ref)
        doc = {"identificacion": next(iter(self.data["pacientes"].values()))["identificacion"], "nota": "DEMO previo sin reserva"}
        ref.create(doc, timeout=10)
        with self.assertRaisesRegex(ValueError, "Identificación existente"):
            seed_clinical_demo.seed(self.client, self.data)
        self.assertEqual(ref.get(timeout=10).to_dict(), doc)
        self.assertTrue(all(not ref.get(timeout=10).exists for ref in self.refs[:-1]))

    def test_invalid_dataset_never_writes(self):
        data = copy.deepcopy(self.data)
        next(iter(data["recetas"].values()))["medicamento_id"] = "DEMO-AUSENTE"
        with self.assertRaises(ValueError):
            seed_clinical_demo.seed(self.client, data)
        self.assertTrue(all(not ref.get(timeout=10).exists for ref in self.refs))


@unittest.skipUnless(os.getenv("FIRESTORE_RECOVERY_TESTS") == "1", "Requiere emulador vacío dedicado y mismo filesystem")
class ClinicalCoexistenceTests(unittest.TestCase):
    def test_legacy_preserved_and_both_versions_export(self):
        client = seed_demo.client_for_emulator()
        self.addCleanup(client.close)
        self.assertFalse(any(next(c.list_documents(), None) is not None for c in client.collections()))
        legacy = seed_demo.load_fixture()
        clinical = model.load_fixture()
        entries = [(c, key, seed_demo.stored_document(c, doc)) for c, docs in legacy.items() for key, doc in docs.items()] + model.entries(clinical)
        refs = [client.collection(c).document(key) for c, key, _ in entries]
        def cleanup():
            for ref in refs:
                ref.delete(timeout=10)
        self.addCleanup(cleanup)
        self.assertEqual(seed_demo.seed(client, legacy)["created"], 7)
        self.assertEqual(seed_clinical_demo.seed(client, clinical)["created"], 20)
        self.assertEqual(seed_clinical_demo.seed(client, clinical)["unchanged"], 20)
        for ref, (_, _, expected) in zip(refs, entries):
            self.assertEqual(ref.get(timeout=10).to_dict(), expected)
        self.assertEqual(export_demo.verify_demo(client, "both"), 27)
        with self.assertRaises(ValueError):
            export_demo.verify_demo(client, "clinical")
        with tempfile.TemporaryDirectory() as temp:
            result = export_demo.export_demo(Path(temp) / "both", "both")
            self.assertTrue((result / "firestore_export.overall_export_metadata").exists())


if __name__ == "__main__":
    unittest.main()
