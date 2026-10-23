from django.contrib import admin
from django.urls import include, path
from apps.operaciones.accounts import AccountsView
from apps.operaciones.views import ManifestView, ResourceView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.identidad.urls")),
    path("api/operaciones/cuentas/", AccountsView.as_view()),
    path("api/operaciones/", ManifestView.as_view()),
    path("api/operaciones/<slug:name>/", ResourceView.as_view()),
    path("api/operaciones/<slug:name>/<str:identifier>/", ResourceView.as_view()),
    path("api/", include("apps.historiales.presentation.urls")),
]
