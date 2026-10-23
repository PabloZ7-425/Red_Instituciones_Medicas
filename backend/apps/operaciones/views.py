"""Additive OPERACIONES-01 API, sharing institutional session, CSRF and JSON policy."""
from rest_framework.response import Response
from apps.historiales.application.validation import invalid, validar_query
from apps.historiales.domain.errors import AccesoDenegado
from apps.historiales.presentation.clinical import ClinicalView
from .catalog import manifest, resource
from .repository import OperationsRepository


class ManifestView(ClinicalView):
    def get(self,request):
        if request.query_params:invalid('query','No se permiten parámetros')
        return Response(manifest(request.contexto_clinico))


class ResourceView(ClinicalView):
    def initial(self, request, *args, **kwargs):
        super().initial(request,*args,**kwargs)
        # Authorize before constructing a database adapter or parsing JSON.
        name=kwargs['name'];write=request.method in {'POST','PATCH'}
        if request.query_params.get('lookup')=='1' and request.method in {'GET','HEAD'}:
            from .catalog import RESOURCES
            context=request.contexto_clinico
            allowed=any(context.rol in r['write_roles'] and any(f.get('resource')==name for f in r['fields'].values()) for r in RESOURCES[context.institucion].values())
            if not allowed:resource(context,name)
        else: resource(request.contexto_clinico,name,write=write,edit=request.method=='PATCH')
        if write and request.query_params:invalid('query','No se permiten parámetros al guardar')

    def get(self,request,name,identifier=None):
        if identifier:invalid('id','Use el listado o su búsqueda')
        query=request.query_params.copy();patient=query.pop('patient',None);lookup=query.pop('lookup',None)
        if patient and len(patient)!=1 or lookup and lookup!=['1']:invalid('query','Parámetro repetido o inválido')
        page=validar_query((k,v) for k,values in query.lists() for v in values)
        return Response(OperationsRepository(request.contexto_clinico).page(name,**page,patient=patient[0] if patient else None,lookup=bool(lookup)))

    def post(self,request,name,identifier=None):
        if identifier:
            if not isinstance(request.data,dict) or set(request.data)!={'accion','version'}:
                invalid('body','Se requieren accion y version')
            if not isinstance(request.data['accion'],str):invalid('accion','Acción inválida')
            return Response(OperationsRepository(request.contexto_clinico).financial_action(name,identifier,request.data['accion'],request.data['version']))
        return Response(OperationsRepository(request.contexto_clinico).save(name,request.data),status=201)

    def patch(self,request,name,identifier=None):
        if not identifier:invalid('id','Se requiere identificador')
        if not isinstance(request.data,dict) or set(request.data)!={'values','version'}:invalid('body','Se requieren values y version')
        return Response(OperationsRepository(request.contexto_clinico).save(name,request.data['values'],identifier=identifier,version=request.data['version']))
