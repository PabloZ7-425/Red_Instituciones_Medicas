from importlib import import_module

from apps.historiales.domain.institutions import Institution
from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import NoAutenticado, PersistenciaNoDisponible
from apps.historiales.domain.ports import HistorialRepository, MedicamentoCatalogo


class AdapterFactory:
    _adapters = {
        Institution.HOSPITAL: "postgres_adapter.PostgreSQLAdapter",
        Institution.PEDIATRICO: "mysql_adapter.MySQLAdapter",
        Institution.LABORATORIO: "mongo_adapter.MongoAdapter",
        Institution.ODONTOLOGICA: "firestore_adapter.FirestoreAdapter",
    }

    @classmethod
    def _adapter_class(cls, institution):
        entry = cls._adapters[institution]
        if isinstance(entry, str):
            module, name = entry.rsplit(".", 1)
            return getattr(import_module(f"apps.historiales.infrastructure.adapters.{module}"), name)
        return entry

    @classmethod
    def create(cls, institution):
        adapter_class = cls._adapter_class(institution)
        return adapter_class()

    @classmethod
    def create_clinical(cls, contexto):
        """Adapter constructors accept contexto= once they implement both clinical ports.

        Never fall back to a test double or a health-only adapter in production.
        """
        if not isinstance(contexto, ContextoClinico):
            raise NoAutenticado()
        adapter_class = cls._adapter_class(Institution.from_slug(contexto.institucion))
        if not issubclass(adapter_class, HistorialRepository) or not issubclass(
            adapter_class, MedicamentoCatalogo
        ):
            raise PersistenciaNoDisponible()
        return adapter_class(contexto=contexto)
