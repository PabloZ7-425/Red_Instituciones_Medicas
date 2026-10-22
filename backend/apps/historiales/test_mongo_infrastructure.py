"""Infrastructure capability only. Does not certify Jennifer's clinical provider."""
import os
import re
from unittest import TestCase, skipUnless
from uuid import uuid4


@skipUnless(os.getenv("TEST_MONGO_REPLICA") == "1", "Requiere Mongo rs0 aislado por namespace B5")
class MongoInfrastructureTests(TestCase):
    def setUp(self):
        from pymongo import MongoClient
        if os.getenv("MONGO_INFRA_TEST_DB") != "test_b5_infra":
            raise RuntimeError("Se requiere MONGO_INFRA_TEST_DB=test_b5_infra")
        self.name = "test_b5_" + uuid4().hex
        self.client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=3000, socketTimeoutMS=10000)
        self.addCleanup(self.client.close)
        self.addCleanup(self.cleanup)
        self.db = self.client[self.name]

    def cleanup(self):
        if not re.fullmatch(r"test_b5_[a-f0-9]{32}", self.name):
            raise RuntimeError("Limpieza Mongo fuera del namespace aislado")
        self.client.drop_database(self.name)

    def test_primary_topology_and_multidocument_commit_and_abort(self):
        from pymongo.write_concern import WriteConcern
        hello = self.client.admin.command("hello")
        self.assertEqual(hello["setName"], "rs0")
        self.assertTrue(hello["isWritablePrimary"])
        self.assertEqual(hello["hosts"], ["mongo:27017"])
        self.db.create_collection("roots")
        self.db.create_collection("events")
        self.db.roots.insert_one({"_id": "DEMO-root", "version": 0})
        with self.client.start_session() as session:
            with self.assertRaises(RuntimeError):
                with session.start_transaction(write_concern=WriteConcern("majority")):
                    self.db.roots.update_one({"_id": "DEMO-root"}, {"$inc": {"version": 1}}, session=session)
                    self.db.events.insert_one({"_id": "DEMO-event"}, session=session)
                    raise RuntimeError("DEMO abort")
            self.assertEqual(self.db.roots.find_one({})["version"], 0)
            self.assertEqual(self.db.events.count_documents({}), 0)
            with session.start_transaction(write_concern=WriteConcern("majority")):
                self.db.roots.update_one({"_id": "DEMO-root"}, {"$inc": {"version": 1}}, session=session)
                self.db.events.insert_one({"_id": "DEMO-event"}, session=session)
        self.assertEqual(self.db.roots.find_one({})["version"], 1)
        self.assertEqual(self.db.events.count_documents({}), 1)
