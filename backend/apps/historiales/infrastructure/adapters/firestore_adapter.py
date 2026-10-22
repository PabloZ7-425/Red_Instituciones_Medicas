"""A3 native Firestore transactions over A1 schema_version=2 documents."""
import os

from google.api_core import exceptions as api_errors
from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from apps.historiales.domain.ports import DatabaseAdapter
from apps.historiales.infrastructure.adapters.mongo_adapter import _ClinicalNoSQL, _runtime


class _FirestoreUnit:
    def __init__(self, client, transaction, institution):
        self.client, self.transaction, self.institution = client, transaction, institution

    def _row(self, snapshot):
        if not snapshot.exists:
            return None
        row = snapshot.to_dict()
        if row.get('institucion') != self.institution or row.get('schema_version') != 2:
            return None
        return dict(row, id=snapshot.id)

    def get(self, collection, identifier):
        return self._row(self.client.collection(collection).document(identifier).get(transaction=self.transaction, timeout=10))

    def rows(self, collection):
        query = self.client.collection(collection).where(filter=FieldFilter('institucion', '==', self.institution)).where(filter=FieldFilter('schema_version', '==', 2))
        return [self._row(snapshot) for snapshot in query.get(transaction=self.transaction, timeout=10)]

    def create(self, collection, identifier, row):
        self.transaction.create(self.client.collection(collection).document(identifier), row)

    def update(self, collection, identifier, changes):
        self.transaction.update(self.client.collection(collection).document(identifier), changes)

    def touch(self, patient):
        self.update('pacientes', patient['id'], {'version': patient.get('version', 0) + 1})


class FirestoreAdapter(_ClinicalNoSQL, DatabaseAdapter):
    institution = 'odontologica'

    def _client(self):
        if not os.getenv('FIRESTORE_EMULATOR_HOST'):
            # No implicit production Firebase authentication in this project.
            raise RuntimeError('FIRESTORE_EMULATOR_HOST no esta configurado')
        return firestore.Client(project=os.getenv('FIREBASE_PROJECT_ID', 'demo-historiales'), credentials=AnonymousCredentials())

    def health_check(self):
        client = self._client()
        try:
            next(client.collections(), None)
            return True
        finally:
            client.close()

    def _transaction(self, callback, *, read=False):
        r = _runtime()
        if not os.getenv('FIRESTORE_EMULATOR_HOST'):
            raise r.e.PersistenciaNoDisponible()
        client = None
        try:
            client = self._client()
            @firestore.transactional
            def apply(transaction):
                return callback(_FirestoreUnit(client, transaction, self.institution))
            return apply(client.transaction(max_attempts=5, read_only=read))
        except api_errors.AlreadyExists:
            raise r.e.Conflicto() from None
        except (api_errors.GoogleAPICallError, ValueError):
            # SDK uses ValueError for exhausted transaction retries.
            raise r.e.PersistenciaNoDisponible() from None
        finally:
            if client is not None:
                client.close()
