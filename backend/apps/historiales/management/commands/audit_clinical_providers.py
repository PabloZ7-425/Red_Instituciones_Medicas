"""Report actual port availability; connectivity alone never certifies a provider."""
import inspect
import json

from django.core.management.base import BaseCommand, CommandError

from apps.historiales.domain.institutions import Institution
from apps.historiales.domain.ports import HistorialRepository, MedicamentoCatalogo
from apps.historiales.infrastructure.factory import AdapterFactory


class Command(BaseCommand):
    help = "Audita CONTRACT-REPO-01@1.0.0/CAT-01 sin consultar datos ni simular proveedores"

    def add_arguments(self, parser):
        parser.add_argument("--require-all", action="store_true", help="Falla si falta un proveedor clínico")

    def handle(self, *args, **options):
        result = {}
        expected = HistorialRepository.__abstractmethods__ | MedicamentoCatalogo.__abstractmethods__
        for institution in Institution:
            provider = AdapterFactory._adapter_class(institution)
            missing = sorted(name for name in expected if not callable(getattr(provider, name, None))
                             or getattr(getattr(provider, name, None), "__isabstractmethod__", False))
            ready = (not missing and not inspect.isabstract(provider) and
                     issubclass(provider, HistorialRepository) and issubclass(provider, MedicamentoCatalogo))
            result[institution.value.slug] = {"provider": provider.__name__, "implements_ports": ready,
                                             "missing_methods": missing}
        self.stdout.write(json.dumps({"contract": "CONTRACT-REPO-01@1.0.0", "providers": result}, ensure_ascii=False))
        if options["require_all"] and not all(r["implements_ports"] for r in result.values()):
            raise CommandError("Certificacion de cuatro proveedores pendiente; revisar missing_methods")
