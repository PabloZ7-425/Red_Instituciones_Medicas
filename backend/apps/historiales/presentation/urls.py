from django.urls import path, re_path

from apps.historiales.presentation.views import api_root, database_health, health
from apps.historiales.presentation.clinical import (
    ArchivoView, ConsultaView, DiagnosticoView, HistorialView, MedicamentosView,
    MissingRoute, PacientesView, RecetaView, TratamientoView,
)


urlpatterns = [
    path("", api_root, name="api-root"),
    path("health/", health, name="health"),
    path("health/databases/", database_health, name="database-health"),
    path("pacientes/", PacientesView.as_view(), name="pacientes"),
    path("pacientes/<str:paciente_id>/historial/", HistorialView.as_view(), name="historial"),
    path("pacientes/<str:paciente_id>/consultas/", ConsultaView.as_view(), name="consulta"),
    path("consultas/<str:consulta_id>/diagnosticos/", DiagnosticoView.as_view(), name="diagnostico"),
    path("diagnosticos/<str:diagnostico_id>/tratamientos/", TratamientoView.as_view(), name="tratamiento"),
    path("tratamientos/<str:tratamiento_id>/recetas/", RecetaView.as_view(), name="receta"),
    path("pacientes/<str:paciente_id>/estado/", ArchivoView.as_view(), name="archivo"),
    path("medicamentos/", MedicamentosView.as_view(), name="medicamentos"),
    re_path(r"^.*$", MissingRoute.as_view(), name="api-not-found"),
]
