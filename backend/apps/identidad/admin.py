from django.contrib import admin

from apps.identidad.models import PerfilInstitucional, Profesional

admin.site.register(PerfilInstitucional)
admin.site.register(Profesional)
