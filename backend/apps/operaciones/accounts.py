"""Institution-local account administration; legacy user/password tables stay unused."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from rest_framework.response import Response

from apps.historiales.application.validation import invalid, validar_query
from apps.historiales.domain.context import ROLES
from apps.historiales.domain.errors import AccesoDenegado, Conflicto, RecursoNoEncontrado
from apps.historiales.presentation.clinical import ClinicalView
from apps.identidad.models import PerfilInstitucional, Profesional
from .repository import OperationsRepository


def account_dto(profile):
    return {'id':str(profile.usuario_id),'username':profile.usuario.username,'rol':profile.rol,
            'activo':profile.activo and profile.usuario.is_active,
            'profesional_id':profile.profesional.referencia_externa if profile.profesional else None}


class AccountsView(ClinicalView):
    def initial(self,request,*args,**kwargs):
        super().initial(request,*args,**kwargs)
        if request.contexto_clinico.rol!='admin':raise AccesoDenegado()
        if request.method not in {'GET','HEAD'} and request.query_params:invalid('query','No se permiten parámetros al guardar')

    def get(self,request):
        page=validar_query((k,v) for k,values in request.query_params.lists() for v in values)
        profiles=PerfilInstitucional.objects.select_related('usuario','profesional').filter(institucion=request.contexto_clinico.institucion)
        if page['q']:profiles=profiles.filter(usuario__username__istartswith=page['q'])
        profiles=profiles.order_by('usuario__username','usuario_id')
        count=profiles.count();offset=page['offset'];limit=page['limit']
        return Response({'count':count,'limit':limit,'offset':offset,'results':[account_dto(p) for p in profiles[offset:offset+limit]], 'roles':sorted(r for r in ROLES if r!='laboratorista' or request.contexto_clinico.institucion=='laboratorio')})

    def post(self,request):
        data=request.data
        if not isinstance(data,dict) or set(data)-{'username','password','rol','profesional_id'}:invalid('body','Campos no permitidos')
        if not isinstance(data.get('username'),str) or not data['username'].strip() or len(data['username'])>150:invalid('username','Usuario requerido, máximo 150 caracteres')
        role=data.get('rol');context=request.contexto_clinico
        if role not in ROLES or role=='laboratorista' and context.institucion!='laboratorio':invalid('rol','Rol inválido para la institución')
        professional=None;reference=data.get('profesional_id')
        if role in {'medico','laboratorista'} and not reference:invalid('profesional_id','Vincula un profesional habilitado')
        if reference:
            repo=OperationsRepository(context);name='medico' if repo.sql else 'profesional';number=repo.internal(name,reference)
            row=repo._run(lambda u:repo._get(u,name,number),read=True)
            if row.get('habilitado') is False or row.get('activo') is False or row.get('estado') not in {None,'activo'}:invalid('profesional_id','Profesional no habilitado')
            reference=str(number)
        password=data.get('password')
        if not isinstance(password,str):invalid('password','Contraseña requerida')
        user=get_user_model()(username=data['username'].strip(),is_staff=False,is_superuser=False)
        try:validate_password(password,user=user)
        except ValidationError as error:invalid('password',' '.join(error.messages))
        try:
            with transaction.atomic():
                if reference:professional,_=Profesional.objects.get_or_create(institucion=context.institucion,referencia_externa=reference,defaults={'habilitado':True})
                user.set_password(password);user.save()
                profile=PerfilInstitucional.objects.create(usuario=user,institucion=context.institucion,rol=role,activo=True,profesional=professional)
                return Response(account_dto(profile),status=201)
        except IntegrityError:raise Conflicto() from None

    def patch(self,request):
        data=request.data
        if not isinstance(data,dict) or set(data) not in [{'id','activo'},{'id','profesional_id'}]:invalid('body','Se requieren id y activo, o id y profesional_id')
        if 'activo' in data and type(data['activo']) is not bool:invalid('activo','Se requiere Sí o No')
        if not isinstance(data['id'],str) or not data['id'].isdigit():invalid('id','Identificador inválido')
        if 'activo' in data and data['id']==request.contexto_clinico.usuario_id:invalid('id','No puedes desactivar tu propia cuenta desde esta pantalla')
        reference=None
        if 'profesional_id' in data:
            repo=OperationsRepository(request.contexto_clinico);name='medico' if repo.sql else 'profesional'
            number=repo.internal(name,data['profesional_id']);row=repo._run(lambda u:repo._get(u,name,number),read=True)
            if row.get('habilitado') is False or row.get('activo') is False or row.get('estado') not in {None,'activo'}:invalid('profesional_id','Profesional no habilitado')
            reference=str(number)
        with transaction.atomic():
            profiles=list(PerfilInstitucional.objects.select_for_update().select_related('usuario','profesional').filter(institucion=request.contexto_clinico.institucion).order_by('pk'))
            profile=next((p for p in profiles if str(p.usuario_id)==data['id']),None)
            if profile is None:raise RecursoNoEncontrado()
            if reference:
                profile.profesional,_=Profesional.objects.get_or_create(institucion=request.contexto_clinico.institucion,referencia_externa=reference,defaults={'habilitado':True})
                profile.save(update_fields=['profesional'])
            else:
                profile.activo=data['activo'];profile.save(update_fields=['activo'])
            # Identity is revalidated on every clinical request: existing sessions lose access.
            return Response(account_dto(profile))
