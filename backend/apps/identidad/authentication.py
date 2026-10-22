from rest_framework.authentication import SessionAuthentication

from apps.identidad.principal import contexto_sesion


class InstitutionalSessionAuthentication(SessionAuthentication):
    def authenticate_header(self, request):
        return 'Session realm="institucional"'

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        request.contexto_clinico = contexto_sesion(request._request)
        return result
