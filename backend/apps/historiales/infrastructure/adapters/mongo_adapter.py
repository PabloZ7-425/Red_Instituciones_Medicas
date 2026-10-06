import os

from pymongo import MongoClient

from apps.historiales.domain.ports import DatabaseAdapter


class MongoAdapter(DatabaseAdapter):
    def health_check(self):
        client = MongoClient(
            os.getenv("MONGO_URI", "mongodb://mongo:27017/laboratorio?replicaSet=rs0"),
            serverSelectionTimeoutMS=3000,
        )
        try:
            return client.admin.command("ping")["ok"] == 1
        finally:
            client.close()
