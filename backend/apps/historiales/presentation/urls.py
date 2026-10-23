from django.urls import path, re_path
from apps.historiales.presentation.specialties import SpecialtyView

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
    path('pacientes/<str:identifier>/ingresos/', SpecialtyView.as_view(action='admissions')),
    path('pacientes/<str:identifier>/ingresos/nuevo/', SpecialtyView.as_view(action='admission')),
    path('ingresos/<str:identifier>/alta/', SpecialtyView.as_view(action='discharge')),
    path('camas/', SpecialtyView.as_view(action='beds')),
    path('pacientes/<str:identifier>/seguimiento/', SpecialtyView.as_view(action='followup')),
    path('pacientes/<str:identifier>/tutores/', SpecialtyView.as_view(action='tutors')),
    path('pacientes/<str:identifier>/tutores/nuevo/', SpecialtyView.as_view(action='tutor')),
    path('pacientes/<str:identifier>/vacunas/', SpecialtyView.as_view(action='vaccine')),
    path('pacientes/<str:identifier>/crecimiento/', SpecialtyView.as_view(action='growth')),
    path('vacunas/', SpecialtyView.as_view(action='vaccines')),
    path('tipos-examen/', SpecialtyView.as_view(action='exams')),
    path('pacientes/<str:identifier>/resultados/', SpecialtyView.as_view(action='results')),
    path('pacientes/<str:identifier>/resultados/nuevo/', SpecialtyView.as_view(action='result')),
    path('pacientes/<str:identifier>/procedimientos/', SpecialtyView.as_view(action='procedures')),
    path('pacientes/<str:identifier>/procedimientos/nuevo/', SpecialtyView.as_view(action='procedure')),
    re_path(r"^.*$", MissingRoute.as_view(), name="api-not-found"),
]
