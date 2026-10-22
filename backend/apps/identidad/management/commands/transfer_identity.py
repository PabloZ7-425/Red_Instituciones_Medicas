from django.core.management import BaseCommand, CommandError
from django.db import connections

from apps.identidad.transfer import fingerprint, identity_payload, transfer


class Command(BaseCommand):
    help = "Traslada cuentas Django con respaldo/conciliación. Nunca copia sesiones ni datos clínicos."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument("--target", required=True)
        parser.add_argument("--backup-dir", required=True)
        parser.add_argument("--verify-only", action="store_true")

    def handle(self, *args, **options):
        source, target = options["source"], options["target"]
        if source not in connections or target not in connections:
            raise CommandError("Alias de base no configurado")
        if source == target:
            raise CommandError("Origen y destino deben ser distintos")
        if options["verify_only"]:
            if fingerprint(identity_payload(source)) != fingerprint(identity_payload(target)):
                raise CommandError("Las identidades no coinciden")
            self.stdout.write("Conciliación de identidades correcta")
            return
        counts = transfer(source, target, options["backup_dir"])
        self.stdout.write(f"Traslado conciliado: {counts['users']} usuarios, {counts['groups']} grupos. Sesiones no copiadas.")
