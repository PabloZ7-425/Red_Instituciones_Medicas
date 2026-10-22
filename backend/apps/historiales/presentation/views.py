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
