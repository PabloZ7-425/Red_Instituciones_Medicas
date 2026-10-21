import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_demo
import seed_demo


class ExportValidationTests(unittest.TestCase):
    def test_destination_does_not_overwrite_or_write_in_repo(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(export_demo.destination(Path(temp) / "new"), Path(temp) / "new")
            for target in (Path(temp), Path(temp) / "missing" / "new", Path(seed_demo.__file__).parent / "exports"):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    export_demo.destination(target)

    def test_docker_hostname_rejected_before_client_creation(self):
        with patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "firestore:8080", "FIREBASE_PROJECT_ID": seed_demo.PROJECT, "GOOGLE_CLOUD_PROJECT": seed_demo.PROJECT}), patch.object(seed_demo, "client_for_emulator") as client:
            with self.assertRaises(ValueError):
                export_demo.export_demo("unused")
            client.assert_not_called()


@unittest.skipUnless(os.getenv("FIRESTORE_RECOVERY_TESTS") == "1", "Requiere emulador AISLADO vacío, mismo filesystem y FIRESTORE_RECOVERY_TESTS=1")
class ExportEmulatorTests(unittest.TestCase):
    def setUp(self):
        self.client = seed_demo.client_for_emulator()
        self.addCleanup(self.client.close)
        if any(next(c.list_documents(), None) is not None for c in self.client.collections()):
            self.fail("Prueba de exportación requiere emulador vacío dedicado")
        self.data = seed_demo.load_fixture()
        self.refs = [self.client.collection(c).document(i) for c, docs in self.data.items() for i in docs]
        self.addCleanup(self.cleanup_documents)
        seed_demo.seed(self.client, self.data)

    def cleanup_documents(self):
        for ref in self.refs:
            ref.delete(timeout=10)

    def test_export_readback_and_rejects_existing_destination(self):
        self.assertEqual(export_demo.verify_demo(self.client), 7)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "export"
            result = export_demo.export_demo(target)
            metadata = result / "firestore_export.overall_export_metadata"
            self.assertTrue(metadata.is_file())
            self.assertGreater(metadata.stat().st_size, 0)
            with self.assertRaises(ValueError):
                export_demo.export_demo(target)

    def test_foreign_data_prevents_export_without_deleting_it(self):
        ref = self.client.collection("pacientes").document("DEMO-EXTRA-TEST")
        self.refs.append(ref)
        ref.create({"nota": "DEMO fuera del fixture"}, timeout=10)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "export"
            with self.assertRaises(ValueError):
                export_demo.export_demo(target)
            self.assertFalse(target.exists())
        self.assertEqual(ref.get(timeout=10).to_dict(), {"nota": "DEMO fuera del fixture"})

    def test_nested_data_prevents_export(self):
        ref = self.refs[0].collection("extra").document("DEMO-NESTED")
        self.refs.append(ref)
        ref.create({"nota": "DEMO subcolección"}, timeout=10)
        with self.assertRaisesRegex(ValueError, "Subcolección"):
            export_demo.verify_demo(self.client)


if __name__ == "__main__":
    unittest.main()
