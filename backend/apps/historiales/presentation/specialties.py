"""Thin HTTP transport for SPECIALTY-API-01; no native database calls here."""
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from apps.historiales.application.specialties import ACTIONS, READS, CATALOGS, SpecialtyService
from apps.historiales.infrastructure.factory import AdapterFactory
from apps.historiales.presentation.clinical import ClinicalView


class SpecialtyView(ClinicalView):
    action = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.operations = {'POST' if self.action in ACTIONS else 'GET': (ACTIONS.get(self.action) or READS[self.action])[1]}
        self.paginated = self.action in CATALOGS
        self.http_method_names = ['get', 'head', 'options'] if self.action in READS else ['post', 'options']

    def use_case(self, request):
        return SpecialtyService(request.contexto_clinico, AdapterFactory.create_clinical)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        method = 'GET' if request.method == 'HEAD' else request.method
        if method == 'OPTIONS':
            self.use_case(request).authorize(self.action)
            return
        if method not in self.operations:
            raise MethodNotAllowed(request.method)
        self.use_case(request).authorize(self.action)

    def get(self, request, identifier=None):
        page = self.page(request) if self.paginated else None
        return Response(self.use_case(request).execute(self.action, identifier, page=page))

    def post(self, request, identifier):
        result = self.use_case(request).execute(self.action, identifier, body=request.data)
        return Response(result, status=200 if self.action == 'discharge' else 201)
