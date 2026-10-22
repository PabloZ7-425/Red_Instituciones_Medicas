import math
import time

from django.contrib.auth import logout

from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import AccesoDenegado, NoAutenticado
from apps.identidad.models import PerfilInstitucional

SESSION_STARTED = "clinical_authenticated_at"
MAX_SESSION_SECONDS = 8 * 60 * 60


def contexto_usuario(user):
    if not user.is_authenticated or not user.is_active:
        raise NoAutenticado()
    try:
        profile = PerfilInstitucional.objects.select_related("profesional").get(usuario_id=user.pk)
    except PerfilInstitucional.DoesNotExist:
        raise AccesoDenegado() from None
    if not profile.activo:
        raise AccesoDenegado()
    professional = profile.profesional
    if professional and professional.institucion != profile.institucion:
        raise AccesoDenegado()
    return ContextoClinico(
        profile.institucion, str(user.pk), profile.rol,
        professional.referencia_externa if professional and professional.habilitado else None,
    )


def contexto_sesion(request):
    started = request.session.get(SESSION_STARTED)
    now = time.time()
    if (type(started) not in (int, float) or not math.isfinite(started)
            or not 0 <= now - started < MAX_SESSION_SECONDS):
        logout(request)
        raise NoAutenticado()
    return contexto_usuario(request.user)


def usuario_json(user, contexto):
    return {"usuario": {"id": str(user.pk), "username": user.username,
                        "rol": contexto.rol, "institucion": contexto.institucion}}
