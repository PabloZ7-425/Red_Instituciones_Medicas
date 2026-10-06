from django.urls import path

from apps.historiales.presentation.views import api_root, database_health, health


urlpatterns = [
    path("", api_root, name="api-root"),
    path("health/", health, name="health"),
    path("health/databases/", database_health, name="database-health"),
]
