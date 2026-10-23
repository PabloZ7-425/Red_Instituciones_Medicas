from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.historiales.application.database_health import DatabaseHealthService


@api_view(["GET"])
def api_root(request):
    return Response(
        {
            "project": "Historiales clinicos",
            "contracts": {"specialties": "SPECIALTY-API-01@1.0.0", "operations": "OPERACIONES-01@1.0.0"},
            "endpoints": {
                "operaciones": "/api/operaciones/",
                "health": "/api/health/",
                "databases": "/api/health/databases/",
                "csrf": "/api/auth/csrf/",
                "login": "/api/auth/login/",
                "me": "/api/auth/me/",
                "logout": "/api/auth/logout/",
                "pacientes": "/api/pacientes/",
                "historial": "/api/pacientes/{id}/historial/",
                "consultas": "/api/pacientes/{id}/consultas/",
                "diagnosticos": "/api/consultas/{id}/diagnosticos/",
                "tratamientos": "/api/diagnosticos/{id}/tratamientos/",
                "recetas": "/api/tratamientos/{id}/recetas/",
                "archivo": "/api/pacientes/{id}/estado/",
                "medicamentos": "/api/medicamentos/",
                "ingresos": "/api/pacientes/{id}/ingresos/",
                "ingreso_nuevo": "/api/pacientes/{id}/ingresos/nuevo/",
                "alta": "/api/ingresos/{id}/alta/",
                "camas": "/api/camas/",
                "seguimiento": "/api/pacientes/{id}/seguimiento/",
                "tutores": "/api/pacientes/{id}/tutores/",
                "tutor_nuevo": "/api/pacientes/{id}/tutores/nuevo/",
                "aplicacion_vacuna": "/api/pacientes/{id}/vacunas/",
                "crecimiento": "/api/pacientes/{id}/crecimiento/",
                "vacunas": "/api/vacunas/",
                "tipos_examen": "/api/tipos-examen/",
                "resultados": "/api/pacientes/{id}/resultados/",
                "resultado_nuevo": "/api/pacientes/{id}/resultados/nuevo/",
                "procedimientos": "/api/pacientes/{id}/procedimientos/",
                "procedimiento_nuevo": "/api/pacientes/{id}/procedimientos/nuevo/",
            },
        }
    )


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "service": "django-backend"})


@api_view(["GET"])
def database_health(request):
    result = DatabaseHealthService().execute()
    return Response({"databases": result})
