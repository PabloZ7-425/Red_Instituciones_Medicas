from apps.historiales.domain.institutions import Institution
from apps.historiales.infrastructure.adapters.firestore_adapter import FirestoreAdapter
from apps.historiales.infrastructure.adapters.mongo_adapter import MongoAdapter
from apps.historiales.infrastructure.adapters.mysql_adapter import MySQLAdapter
from apps.historiales.infrastructure.adapters.postgres_adapter import PostgreSQLAdapter


class AdapterFactory:
    _adapters = {
        Institution.HOSPITAL: PostgreSQLAdapter,
        Institution.PEDIATRICO: MySQLAdapter,
        Institution.LABORATORIO: MongoAdapter,
        Institution.ODONTOLOGICA: FirestoreAdapter,
    }

    @classmethod
    def create(cls, institution):
        adapter_class = cls._adapters[institution]
        return adapter_class()
