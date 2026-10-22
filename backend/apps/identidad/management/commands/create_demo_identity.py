from getpass import getpass

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import BaseCommand, CommandError
from django.db import transaction

from apps.historiales.domain.context import ROLES
from apps.identidad.models import INSTITUCIONES, PerfilInstitucional, Profesional


class Command(BaseCommand):
    help = "Crea una cuenta DEMO local con contraseña solicitada sin eco; nunca imprime contraseñas."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--institucion", choices=[slug for slug, _ in INSTITUCIONES], required=True)
        parser.add_argument("--rol", choices=sorted(ROLES), required=True)
        parser.add_argument("--professional-id")
        parser.add_argument("--database", required=True)

    def handle(self, *args, **options):
        alias = options["database"]
        username = options["username"]
        if not username.startswith("DEMO-"):
            raise CommandError("El nombre de cuenta DEMO debe comenzar con DEMO-")
        if User.objects.using(alias).filter(username=username).exists():
            raise CommandError("La cuenta ya existe; no se cambia su contraseña")
        password = getpass("Contraseña local: ")
        if password != getpass("Repita contraseña: "):
            raise CommandError("Las contraseñas no coinciden")
        user = User(username=username)
        user._state.db = alias
        try:
            validate_password(password, user)
            user.full_clean(exclude=["password"])
            with transaction.atomic(using=alias):
                user.set_password(password)
                user.save(using=alias)
                professional = None
                if options["professional_id"]:
                    professional, _ = Profesional.objects.using(alias).get_or_create(
                        institucion=options["institucion"], referencia_externa=options["professional_id"])
                profile = PerfilInstitucional(usuario=user, institucion=options["institucion"],
                                               rol=options["rol"], profesional=professional)
                profile.full_clean()
                profile.save(using=alias)
        except ValidationError as error:
            raise CommandError("Datos de cuenta o contraseña inválidos: " + "; ".join(error.messages)) from None
        self.stdout.write("Cuenta DEMO creada; sin privilegios de administrador técnico")
