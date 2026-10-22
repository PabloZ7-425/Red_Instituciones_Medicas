"""CONTRACT-API-01@1.0.0. HTTP composition only; clinical SQL stays in providers."""
import codecs
import json

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.historiales.application.clinical import HistorialService
from apps.historiales.application.validation import identificador, invalid, validar_dto, validar_query
from apps.historiales.domain.context import autorizar
from apps.historiales.domain.errors import RecursoNoEncontrado
from apps.historiales.infrastructure.factory import AdapterFactory
from apps.identidad.authentication import InstitutionalSessionAuthentication


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def finite_constant(value):
    raise ValueError("Nonfinite JSON value")


class ClinicalJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        try:
            encoding = (parser_context or {}).get("encoding", "utf-8")
            return json.load(codecs.getreader(encoding)(stream), object_pairs_hook=unique_object,
                             parse_constant=finite_constant)
        except (ValueError, UnicodeError, LookupError):
            raise ParseError("Datos JSON inválidos") from None


@method_decorator(never_cache, name="dispatch")
class ClinicalView(APIView):
    authentication_classes = [InstitutionalSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [ClinicalJSONParser]
    operations = {}
    paginated = False

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        method = "GET" if request.method == "HEAD" else request.method
        operation = self.operations.get(method)
        if operation:
            # Deny before reading body, constructing providers or looking up IDs.
            autorizar(request.contexto_clinico, operation)
        if operation and request.query_params and not (self.paginated and method == "GET"):
            invalid("query", "No se permiten parámetros de consulta")

    def service(self, request):
        repo = AdapterFactory.create_clinical(request.contexto_clinico)
        return HistorialService(request.contexto_clinico, repo, repo)

    def page(self, request):
        return validar_query((key, value) for key, values in request.query_params.lists() for value in values)


class PacientesView(ClinicalView):
    operations = {"GET": "listar_pacientes", "POST": "registrar_paciente"}
    paginated = True

    def get(self, request):
        page = self.page(request)
        return Response(self.service(request).listar_pacientes(**page))

    def post(self, request):
        data = validar_dto("paciente", request.data)
        return Response(self.service(request).registrar_paciente(data), status=201)


class HistorialView(ClinicalView):
    operations = {"GET": "obtener_historial"}

    def get(self, request, paciente_id):
        identificador(paciente_id)
        return Response(self.service(request).obtener_historial(paciente_id))


class ConsultaView(ClinicalView):
    operations = {"POST": "registrar_consulta"}

    def post(self, request, paciente_id):
        identificador(paciente_id)
        data = validar_dto("consulta", request.data)
        return Response(self.service(request).registrar_consulta(paciente_id, data), status=201)


class DiagnosticoView(ClinicalView):
    operations = {"POST": "registrar_diagnostico"}

    def post(self, request, consulta_id):
        identificador(consulta_id)
        data = validar_dto("diagnostico", request.data)
        return Response(self.service(request).registrar_diagnostico(consulta_id, data), status=201)


class TratamientoView(ClinicalView):
    operations = {"POST": "registrar_tratamiento"}

    def post(self, request, diagnostico_id):
        identificador(diagnostico_id)
        data = validar_dto("tratamiento", request.data)
        return Response(self.service(request).registrar_tratamiento(diagnostico_id, data), status=201)


class RecetaView(ClinicalView):
    operations = {"POST": "registrar_receta"}

    def post(self, request, tratamiento_id):
        identificador(tratamiento_id)
        data = validar_dto("receta", request.data)
        return Response(self.service(request).registrar_receta(tratamiento_id, data), status=201)


class ArchivoView(ClinicalView):
    operations = {"PATCH": "archivar_paciente"}

    def patch(self, request, paciente_id):
        identificador(paciente_id)
        data = validar_dto("archivo", request.data)
        return Response(self.service(request).archivar_paciente(paciente_id, data["motivo"]))


class MedicamentosView(ClinicalView):
    operations = {"GET": "listar_medicamentos"}
    paginated = True

    def get(self, request):
        page = self.page(request)
        return Response(self.service(request).listar_medicamentos(**page))


class MissingRoute(APIView):
    authentication_classes = []
    permission_classes = []

    def initial(self, request, *args, **kwargs):
        # Also return a safe envelope for unknown API paths when DEBUG=True.
        raise RecursoNoEncontrado()
