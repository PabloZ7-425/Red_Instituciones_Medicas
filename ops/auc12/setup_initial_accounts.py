"""Explicit initial DEMO staff/accounts, using restricted application credentials.

No patients, clinical decisions, superusers, password resets or legacy mutations.
Passwords are written only to a private file; never returned on stdout.
"""
import json
import os
from pathlib import Path
import secrets


def main():
    if os.getenv('AUC12_SETUP')!='create-initial-accounts':
        raise RuntimeError('Explicit initial setup flag required')
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup()
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from apps.identidad.models import PerfilInstitucional,Profesional
    from apps.historiales.domain.context import ContextoClinico
    from apps.operaciones.repository import OperationsRepository

    path=Path(os.getenv('AUC12_ACCESS_FILE','/tmp/auc12-accesos.json'))
    if path.is_symlink():raise RuntimeError('Credential path must not be a symbolic link')
    institutions=['hospital','pediatrico','laboratorio','odontologica']
    accounts=json.loads(path.read_text()) if path.exists() else {}
    for institution in institutions:
        accounts.setdefault(institution,{'username':'DEMO-AUC12-'+institution,'password':secrets.token_urlsafe(24)})
    # Reserve the file exclusively and keep the same credentials on partial retry.
    if not path.exists():
        with open(path,'x',opener=lambda p,f:os.open(p,f,0o600)) as handle:json.dump(accounts,handle,indent=2)
    else:path.chmod(0o600)

    for institution in institutions:
        repo=OperationsRepository(ContextoClinico(institution,'auc12-setup','admin'))
        label='DEMO AUC12 '+institution
        def ensure(name,values,key):
            matches=[];offset=0
            while True:
                page=repo.page(name,limit=100,offset=offset)
                matches.extend(row for row in page['results'] if row['values'].get(key)==values[key])
                offset+=100
                if offset>=page['count']:break
            if len(matches)>1:raise RuntimeError('Duplicate initial catalog entry; review required')
            if not matches:return repo.save(name,values)['id']
            row=matches[0]
            if any(row['values'].get(k) is False for k in ['habilitado','activo','activo_operativo']) or row['values'].get('estado')=='inactivo':
                raise RuntimeError('Initial professional/catalog is disabled; not reactivated')
            for field,value in values.items():
                if row['values'].get(field)!=value:raise RuntimeError('Existing initial catalog differs; not overwritten')
            return row['id']
        if repo.sql:
            fields={'nombre':label,'activo_operativo':True}
            if repo.hospital:fields['nivel_complejidad']=1
            specialty=ensure('especialidad',fields,'nombre')
            data=({'id_especialidad':specialty,'nombre_completo':label,'colegiado':'DEMO-AUC12-H','habilitado':True} if repo.hospital else
                  {'nombre':'DEMO AUC12','apellido':'pediatrico','colegiado':'DEMO-AUC12-P','estado':'activo','especialidad_id':specialty})
            resource='medico'
        else:
            data={'nombre':label,'colegiado':'DEMO-AUC12-'+institution,'habilitado':True,'activo':True};resource='profesional'
        identifier=ensure(resource,data,'colegiado')
        reference=str(repo.internal(resource,identifier))
        credentials=accounts[institution]
        with transaction.atomic():
            professional,_=Profesional.objects.get_or_create(institucion=institution,referencia_externa=reference,defaults={'habilitado':True})
            if not professional.habilitado:raise RuntimeError('Identity professional is disabled; not reactivated')
            user=get_user_model().objects.filter(username=credentials['username']).first()
            if user is None:
                user=get_user_model().objects.create_user(username=credentials['username'],password=credentials['password'],is_staff=False,is_superuser=False)
                PerfilInstitucional.objects.create(usuario=user,institucion=institution,rol='admin',activo=True,profesional=professional)
            else:
                profile=PerfilInstitucional.objects.get(usuario=user)
                if not user.is_active or user.is_superuser or user.is_staff or not user.check_password(credentials['password']) or not profile.activo or profile.rol!='admin' or profile.institucion!=institution or profile.profesional_id!=professional.id:
                    raise RuntimeError('Existing account differs; no password/profile reset performed')
        print('OK initial professional and clinical admin: '+institution)
    print('Credentials saved privately in /tmp/auc12-accesos.json. No patients created.')


if __name__=='__main__':main()
