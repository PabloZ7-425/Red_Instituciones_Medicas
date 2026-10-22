from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.historiales.domain.context import ROLES
from apps.historiales.domain.institutions import Institution

INSTITUCIONES = [(i.value.slug, i.value.name) for i in Institution]
SLUGS = [slug for slug, _ in INSTITUCIONES]


class Profesional(models.Model):
    institucion = models.CharField(max_length=20, choices=INSTITUCIONES)
    referencia_externa = models.CharField(max_length=100)
    habilitado = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["institucion", "referencia_externa"], name="profesional_institucional_unico"),
            models.CheckConstraint(condition=models.Q(institucion__in=SLUGS), name="profesional_institucion_valida"),
            models.CheckConstraint(condition=~models.Q(referencia_externa=""), name="profesional_referencia_no_vacia"),
        ]

    def clean(self):
        if not self.referencia_externa or not self.referencia_externa.strip():
            raise ValidationError({"referencia_externa": "Se requiere una referencia profesional"})


class PerfilInstitucional(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_institucional")
    institucion = models.CharField(max_length=20, choices=INSTITUCIONES)
    rol = models.CharField(max_length=20, choices=[(r, r) for r in sorted(ROLES)])
    activo = models.BooleanField(default=True)
    profesional = models.ForeignKey(Profesional, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(institucion__in=SLUGS), name="perfil_institucion_valida"),
            models.CheckConstraint(condition=models.Q(rol__in=sorted(ROLES)), name="perfil_rol_valido"),
            models.CheckConstraint(condition=~models.Q(rol="laboratorista") | models.Q(institucion="laboratorio"), name="laboratorista_solo_laboratorio"),
        ]

    def clean(self):
        if self.rol == "laboratorista" and self.institucion != "laboratorio":
            raise ValidationError({"rol": "Laboratorista requiere laboratorio"})
        if self.profesional_id and self.profesional.institucion != self.institucion:
            raise ValidationError({"profesional": "El profesional debe pertenecer a la misma institución"})
