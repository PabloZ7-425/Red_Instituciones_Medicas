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
from validate_demo import validate_dataset


def manifest():
    return json.loads(subprocess.check_output(["node", str(ROOT / "schema_manifest.js")], text=True))


class OfflineTests(unittest.TestCase):
    def test_initializer_repeats_and_keeps_six_collections(self):
        schema = manifest()
        self.assertEqual(set(schema["schemas"]), {"usuarios", "pacientes", "consultas", "medicamentos", "tipos_examen", "resultados_examen"})
        self.assertEqual(schema["updates"], 6)
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

    def test_semantic_validation_rejects_orphans_and_bad_results(self):
        from bson import ObjectId
        cases = [
            ("consultas", "paciente_id", ObjectId("0000000000000000000000ff")),
            ("resultados_examen", "tipo_examen", "DEMO-inexistente"),
            ("resultados_examen", "campos", [{"nombre": "DEMO", "valor": float("nan")}]),
            ("resultados_examen", "campos", [{"nombre": "DEMO", "valor": float("inf")}]),
            ("resultados_examen", "campos", [{"nombre": "DEMO", "valor": None}]),
            ("resultados_examen", "campos", [{"nombre": "DEMO", "valor": []}]),
            ("resultados_examen", "campos", [{"nombre": "DEMO", "valor": 2 ** 100}]),
            ("resultados_examen", "campos", [{"nombre": "DEMO", "valor": 1}] * 2),
            ("pacientes", "fecha_nacimiento", model.datetime(2001, 2, 3)),
        ]
        validate_dataset(model.fixture())
        for collection, key, value in cases:
            with self.subTest(collection=collection, key=key, value=value):
                data = model.fixture()
                data[collection][0][key] = value
                with self.assertRaises(ValueError):
                    validate_dataset(data)

    def test_invalid_fixture_is_rejected_before_database_access(self):
        from unittest.mock import Mock
        data = model.fixture()
        data["resultados_examen"][0]["tipo_examen"] = "DEMO-inexistente"
        database = Mock(name="isolated_database")
        database.name = "laboratorio_demo"
        with patch.object(model, "fixture", return_value=data):
            with self.assertRaisesRegex(ValueError, "Tipo de examen"):
                model.seed(database)
        self.assertEqual(database.mock_calls, [])

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
        cases = [("pacientes", "fecha_nacimiento", "2001-02-03"), ("pacientes", "estado", "borrado"), ("resultados_examen", "campos", []), ("resultados_examen", "campos", [{"nombre": "DEMO-sin-valor"}]), ("consultas", "paciente_id", "string-interno-invalido"), ("pacientes", "identificacion", "X" * 21), ("pacientes", "nombres", "   "), ("medicamentos", "nombre", ""), ("medicamentos", "presentacion", 123), ("tipos_examen", "nombre", None), ("resultados_examen", "campos", [{"nombre": "DEMO", "valor": []}])]
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

    def test_legacy_patient_states_and_optional_catalog_presentation(self):
        for state in ("activo", "inactivo", "archivado"):
            doc = model.fixture()["pacientes"][0]
            doc["estado"] = state
            self.db.pacientes.replace_one({"_id": doc["_id"]}, doc, upsert=True)
            self.assertEqual(self.db.pacientes.find_one({"_id": doc["_id"]})["estado"], state)
        for presentation in (None, "DEMO sin administración real"):
            doc = model.fixture()["medicamentos"][0]
            doc["presentacion"] = presentation
            self.db.medicamentos.replace_one({"_id": doc["_id"]}, doc, upsert=True)
            self.assertEqual(self.db.medicamentos.find_one({"_id": doc["_id"]})["presentacion"], presentation)

    def test_unique_catalog_collision_is_detected_before_patient_write(self):
        from bson import ObjectId
        # Clave única ocupada por un ID distinto al esperado, sin tocar datos ajenos.
        doc = model.fixture()["tipos_examen"][0]
        doc["_id"] = ObjectId("0000000000000000000000ff")
        self.db.tipos_examen.insert_one(doc)
        try:
            with self.assertRaisesRegex(ValueError, "clave única ocupada"):
                model.seed(self.db)
            self.assertEqual(self.db.pacientes.count_documents({}), 0)
            self.assertEqual(self.db.tipos_examen.find_one({"_id": doc["_id"]}), doc)
        finally:
            self.db.tipos_examen.delete_one({"_id": doc["_id"]})

    def test_growth_is_separate_from_patient_and_query_uses_index(self):
        from bson import ObjectId
        model.seed(self.db)
        patient = model.fixture()["pacientes"][0]
        ids = [ObjectId(f"{1000 + index:024x}") for index in range(30)]
        try:
            for result_id in ids:
                result = model.fixture()["resultados_examen"][0]
                result["_id"] = result_id
                self.db.resultados_examen.insert_one(result)
            self.assertEqual(self.db.pacientes.find_one({"_id": patient["_id"]}), patient)
            query = {"paciente_id": patient["_id"]}
            results = list(self.db.resultados_examen.find(query).sort("fecha", -1).hint([("paciente_id", 1), ("fecha", -1)]))
            self.assertEqual(len(results), 33)
            self.assertEqual(self.db.resultados_examen.index_information()["paciente_id_1_fecha_-1"]["key"], [("paciente_id", 1), ("fecha", -1)])
        finally:
            self.db.resultados_examen.delete_many({"_id": {"$in": ids}})

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
