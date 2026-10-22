import time
from collections.abc import Mapping

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.historiales.application.validation import invalid, texto
from apps.historiales.domain.errors import AccesoDenegado, NoAutenticado
from apps.identidad.authentication import InstitutionalSessionAuthentication
from apps.identidad.principal import SESSION_STARTED, contexto_usuario, usuario_json


@method_decorator(never_cache, name="dispatch")
class IdentityView(APIView):
    authentication_classes = [InstitutionalSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.query_params:
            invalid("query", "No se permiten parámetros de consulta")


class CsrfView(IdentityView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request._request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(IdentityView):
    # Anonymous login must still enforce Django CSRF; DRF alone would not.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        if not isinstance(data, Mapping) or set(data) != {"username", "password"}:
            invalid("body", "Se requieren únicamente username y password")
        username = texto(data["username"], "username", 150)
        password = data["password"]
        if not isinstance(password, str) or not password:
            invalid("password", "Se requiere contraseña no vacía")
        user = authenticate(request=request._request, username=username, password=password)
        if user is None:
            raise NoAutenticado()
        try:
            contexto = contexto_usuario(user)
        except (AccesoDenegado, NoAutenticado):
            # Missing/inactive/invalid profile has the same response as bad credentials.
            raise NoAutenticado() from None
        request.session.flush()
        login(request._request, user)
        request.session[SESSION_STARTED] = time.time()
        request.session.set_expiry(0)  # browser cookie; absolute cap is checked server-side.
        return Response(usuario_json(user, contexto))


class MeView(IdentityView):
    def get(self, request):
        return Response(usuario_json(request.user, request.contexto_clinico))


class LogoutView(IdentityView):
    def post(self, request):
        # Empty body parses as {}; supplied bodies must also be an empty JSON object.
        if request.data != {}:
            invalid("body", "Logout no recibe campos")
        logout(request._request)
        return Response(status=204)
