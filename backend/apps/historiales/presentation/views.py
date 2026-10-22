from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.historiales.application.database_health import DatabaseHealthService


@api_view(["GET"])
def api_root(request):
    return Response(
        {
            "project": "Historiales clinicos",
            "endpoints": {
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
