import os

from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore

from apps.historiales.domain.ports import DatabaseAdapter


class FirestoreAdapter(DatabaseAdapter):
    def health_check(self):
        if not os.getenv("FIRESTORE_EMULATOR_HOST"):
            raise RuntimeError("FIRESTORE_EMULATOR_HOST no esta configurado")

        client = firestore.Client(
            project=os.getenv("FIREBASE_PROJECT_ID", "demo-historiales"),
            credentials=AnonymousCredentials(),
        )
        next(client.collections(), None)
        return True
