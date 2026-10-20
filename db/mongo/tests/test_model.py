import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import seed_demo as model


def manifest():
    return json.loads(subprocess.check_output(["node", str(ROOT / "schema_manifest.js")], text=True))


class OfflineTests(unittest.TestCase):
    def test_initializer_repeats_and_keeps_six_collections(self):
        schema = manifest()
        self.assertEqual(set(schema["schemas"]), {"usuarios", "pacientes", "consultas", "medicamentos", "tipos_examen", "resultados_examen"})
        self.assertEqual(schema["updates"], 4)
        self.assertEqual(len(schema["indexes"]["pacientes"]), 2)
        self.assertTrue(schema["indexes"]["pacientes"][0]["options"]["unique"])

    def test_fixture_is_reproducible_and_references_patient(self):
        self.assertEqual(model.fixture(), model.fixture())
        data = model.fixture()
        self.assertEqual(sum(map(len, data.values())), 9)
        patient = data["pacientes"][0]["_id"]
        for collection in ("consultas", "resultados_examen"):
            self.assertTrue(all(d["paciente_id"] == patient for d in data[collection]))
        kinds = {d["nombre"] for d in data["tipos_examen"]}
        self.assertEqual(kinds, {d["tipo_examen"] for d in data["resultados_examen"]})

    def test_rejects_remote_missing_wrong_db_or_credentials(self):
        for uri in ("", "mongodb://example.com:27017/laboratorio_demo", "mongodb://localhost:27017/laboratorio", "mongodb://user:password@localhost:27017/laboratorio_demo"):
            with self.subTest(uri=uri), patch.dict(os.environ, {"MONGO_DEMO_URI": uri}):
                with self.assertRaises(ValueError):
                    model.local_uri()


@unittest.skipUnless(os.getenv("MONGO_DEMO_URI"), "Requiere instancia local AISLADA de MongoDB 7 y PyMongo")
class MongoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pymongo import MongoClient
        cls.client = MongoClient(model.local_uri(), serverSelectionTimeoutMS=3000, socketTimeoutMS=5000, tz_aware=True)
        cls.addClassCleanup(cls.client.close)
        cls.db = cls.client.laboratorio_demo
        # Evitar tocar una base poblada, incluso con fixtures de otra persona.
        if any(cls.db[c].find_one() is not None for c in cls.db.list_collection_names()):
            raise RuntimeError("Las pruebas requieren laboratorio_demo vacía en instancia aislada")
        cls.schema = manifest()
        model.initialize_demo(cls.db, cls.schema)

    def tearDown(self):
        # Solo IDs de este dataset que fueron escritos en la instancia vacía verificada.
        for name, docs in model.fixture().items():
            self.db[name].delete_many({"_id": {"$in": [d["_id"] for d in docs]}})

    def test_seed_read_repeat_and_schema_repeat(self):
        self.assertEqual(model.seed(self.db), {"created": 9, "unchanged": 0})
        model.initialize_demo(self.db, self.schema)
        self.assertEqual(model.seed(self.db), {"created": 0, "unchanged": 9})
        for collection, docs in model.fixture().items():
            for doc in docs:
                self.assertEqual(self.db[collection].find_one({"_id": doc["_id"]}), doc)
        self.assertEqual(self.db.resultados_examen.count_documents({"paciente_id": model.fixture()["pacientes"][0]["_id"]}), 3)

    def test_server_rejects_bad_dates_states_and_results(self):
        from pymongo.errors import WriteError
        cases = [("pacientes", "fecha_nacimiento", "2001-02-03"), ("pacientes", "estado", "borrado"), ("resultados_examen", "campos", []), ("resultados_examen", "campos", [{"nombre": "DEMO-sin-valor"}]), ("consultas", "paciente_id", "string-interno-invalido")]
        for collection, key, value in cases:
            with self.subTest(collection=collection, key=key):
                doc = copy.deepcopy(model.fixture()[collection][0])
                doc[key] = value
                with self.assertRaises(WriteError) as error:
                    self.db[collection].insert_one(doc)
                self.assertEqual(error.exception.code, 121)

    def test_duplicate_identification_rejected(self):
        from bson import ObjectId
        from pymongo.errors import DuplicateKeyError
        doc = model.fixture()["pacientes"][0]
        self.db.pacientes.insert_one(doc)
        other = dict(doc, _id=ObjectId())
        with self.assertRaises(DuplicateKeyError):
            self.db.pacientes.insert_one(other)

    def test_conflict_preserves_existing_and_creates_nothing(self):
        doc = model.fixture()["pacientes"][0]
        doc["nombres"] = "DEMO editado"
        self.db.pacientes.insert_one(doc)
        with self.assertRaises(ValueError):
            model.seed(self.db)
        self.assertEqual(self.db.pacientes.find_one({"_id": doc["_id"]})["nombres"], "DEMO editado")
        self.assertEqual(self.db.resultados_examen.count_documents({}), 0)


if __name__ == "__main__":
    unittest.main()
