"""Safe DRF envelopes, including framework parsing/CSRF/method errors."""
import logging

from django.http import JsonResponse
from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from rest_framework import exceptions
from rest_framework.response import Response

from apps.historiales.domain.errors import AccesoDenegado, DatosInvalidos, ErrorDominio, PersistenciaNoDisponible
from apps.historiales.presentation.errors import error_response

logger = logging.getLogger(__name__)


def csrf_failure(request, reason=""):
    # Django's reason can contain request details; never expose it.
    return JsonResponse(AccesoDenegado().as_dict(), status=403)


def exception_handler(error, context):
    if isinstance(error, ErrorDominio):
        status, body = error_response(error)
    elif isinstance(error, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        status, body = 401, {"error": {"code": "UNAUTHORIZED", "message": "Autenticación requerida", "fields": {}}}
    elif isinstance(error, (exceptions.PermissionDenied, DjangoPermissionDenied)):
        status, body = error_response(AccesoDenegado())
    elif isinstance(error, (Http404, exceptions.NotFound)):
        from apps.historiales.domain.errors import RecursoNoEncontrado
        status, body = error_response(RecursoNoEncontrado())
    elif isinstance(error, (exceptions.ParseError, exceptions.ValidationError)):
        status, body = error_response(DatosInvalidos(fields={"body": ["Datos JSON inválidos"]}))
    elif isinstance(error, (exceptions.MethodNotAllowed, exceptions.UnsupportedMediaType)):
        status = error.status_code
        code = "METHOD_NOT_ALLOWED" if status == 405 else "UNSUPPORTED_MEDIA_TYPE"
        body = {"error": {"code": code, "message": "Método no permitido" if status == 405 else "Formato no soportado", "fields": {}}}
    else:
        from django.db import DatabaseError
        if isinstance(error, DatabaseError):
            status, body = error_response(PersistenciaNoDisponible())
        else:
            status, body = error_response(error)
        # No raw exception text, credentials, request body or traceback.
        logger.error("Fallo API: %s", type(error).__name__)
    response = Response(body, status=status)
    if status == 401:
        response["WWW-Authenticate"] = 'Session realm="institucional"'
    return response
