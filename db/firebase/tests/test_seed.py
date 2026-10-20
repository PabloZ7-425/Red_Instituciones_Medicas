import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seed_demo as model


class ModelTests(unittest.TestCase):
    def test_fixture_and_stable_values(self):
        self.assertEqual(model.load_fixture(), model.load_fixture())
        self.assertEqual(sum(map(len, model.load_fixture().values())), 7)

    def test_invalid_documents_and_relations(self):
        mutations = [
            ("pacientes", "DEMO-PAC-001", "fecha_nacimiento", "2001-02-30"),
            ("pacientes", "DEMO-PAC-001", "estado", "borrado"),
            ("pacientes", "DEMO-PAC-001", "identificacion", "persona-real"),
            ("consultas", "DEMO-CON-001", "paciente_id", "DEMO-PAC-002"),
            ("consultas", "DEMO-CON-001", "diagnosticos", []),
            ("citas", "DEMO-CITA-001", "paciente_id", "DEMO-NO-EXISTE"),
            ("citas", "DEMO-CITA-001", "fecha", "2026-10-20T15:00:00"),
            ("citas", "DEMO-CITA-001", "fecha", "20261020T15:00:00Z"),
            ("procedimientos", "DEMO-PROC-001", "pieza", "99"),
            ("recetas", "DEMO-REC-001", "indicaciones", []),
            ("recetas", "DEMO-REC-001", "indicaciones", [{"medicamento": "DEMO-incompleto"}]),
            ("pagos", "DEMO-PAGO-001", "monto_centavos", True),
            ("pagos", "DEMO-PAGO-001", "monto_centavos", -1),
            ("pagos", "DEMO-PAGO-001", "moneda", "USD"),
        ]
        for collection, key, field, value in mutations:
            with self.subTest(field=field, value=value):
                data = model.load_fixture()
                data[collection][key][field] = value
                with self.assertRaises(ValueError):
                    model.validate(data)

    def test_unknown_fields_and_duplicate_identification(self):
        data = model.load_fixture()
        data["pacientes"]["DEMO-PAC-001"]["token"] = "not-allowed"
        with self.assertRaises(ValueError):
            model.validate(data)
        data = model.load_fixture()
        data["pacientes"]["DEMO-PAC-002"]["identificacion"] = "DEMO-ODONTO-001"
        with self.assertRaises(ValueError):
            model.validate(data)

    def test_rejects_missing_remote_or_wrong_project(self):
        for env in [{}, {"FIRESTORE_EMULATOR_HOST": "production.example:443"}, {"FIRESTORE_EMULATOR_HOST": "localhost:8082/path"}, {"FIRESTORE_EMULATOR_HOST": "localhost:8082", "FIREBASE_PROJECT_ID": "real-project"}]:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError):
                    model.emulator_host()


@unittest.skipUnless(os.getenv("FIRESTORE_EMULATOR_HOST"), "Requiere emulador local y SDK oficial")
class EmulatorTests(unittest.TestCase):
    def setUp(self):
        self.client = model.client_for_emulator()
        # IDs exclusivos de esta ejecución; nunca eliminamos colecciones ni fixtures compartidos.
        suffix = "-" + uuid4().hex
        original = model.load_fixture()
        self.data = {c: {i + suffix: copy.deepcopy(d) for i, d in docs.items()} for c, docs in original.items()}
        for docs in self.data.values():
            for doc in docs.values():
                for field in ("paciente_id", "cita_id", "consulta_id", "procedimiento_id"):
                    if field in doc:
                        doc[field] += suffix
        self.refs = [self.client.collection(c).document(i) for c, docs in self.data.items() for i in docs]
        self.addCleanup(self.client.close)
        self.addCleanup(self.cleanup_documents)

    def cleanup_documents(self):
        for ref in self.refs:
            ref.delete(timeout=10)

    def test_write_read_and_repeat(self):
        self.assertEqual(model.seed(self.client, self.data), {"created": 7, "unchanged": 0})
        for collection, docs in self.data.items():
            for key, expected in docs.items():
                self.assertEqual(self.client.collection(collection).document(key).get(timeout=10).to_dict(), model.stored_document(collection, expected))
        self.assertEqual(model.seed(self.client, self.data), {"created": 0, "unchanged": 7})

    def test_invalid_dataset_writes_nothing(self):
        data = copy.deepcopy(self.data)
        next(iter(data["pagos"].values()))["monto_centavos"] = -1
        with self.assertRaises(ValueError):
            model.seed(self.client, data)
        self.assertTrue(all(not ref.get(timeout=10).exists for ref in self.refs))

    def test_conflict_aborts_without_overwriting_or_partial_seed(self):
        # Conflicto al final: ninguna escritura anterior debe aplicarse.
        self.refs[-1].create({"nota": "Contenido ajeno que se preserva"}, timeout=10)
        with self.assertRaisesRegex(ValueError, "Conflicto DEMO"):
            model.seed(self.client, self.data)
        self.assertEqual(self.refs[-1].get(timeout=10).to_dict(), {"nota": "Contenido ajeno que se preserva"})
        self.assertTrue(all(not ref.get(timeout=10).exists for ref in self.refs[:-1]))


if __name__ == "__main__":
    unittest.main()
