"""Create identity only in the new private SQLite test file selected by the runner."""
import os
from pathlib import Path
import django
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.historiales.domain.context import ContextoClinico
from apps.identidad.models import PerfilInstitucional, Profesional
from apps.operaciones.repository import OperationsRepository

work=Path(os.environ['OPERATIONS_BROWSER_WORK']).resolve()
if not os.environ.get('OPERATIONS_REAL_TESTS')=='1' or (work/'identity.sqlite3').exists():raise RuntimeError('Requiere identidad de prueba nueva')
call_command('migrate',verbosity=0)
for institution in ['hospital','pediatrico','laboratorio','odontologica']:
    repo=OperationsRepository(ContextoClinico(institution,'setup','admin','1'))
    reference='1' if repo.sql else repo.page('profesional')['results'][0]['id']
    professional,_=Profesional.objects.get_or_create(institucion=institution,referencia_externa=reference)
    for role in ['admin','medico','secretaria','enfermero']+(['laboratorista'] if institution=='laboratorio' else []):
        for prefix in (['DEMO-OPS-','DEMO-A5-'] if role=='admin' else ['DEMO-A5-']):
            user=get_user_model().objects.create_user(prefix+role+'-'+institution,password='DEMO-Operations-2026-Only!',is_staff=False,is_superuser=False)
            PerfilInstitucional.objects.create(usuario=user,institucion=institution,rol=role,profesional=professional if role in {'admin','medico','laboratorista'} else None)
    # The published clinical browser fixtures use these explicit synthetic catalog names.
    if institution=='hospital':
        repo.save('medicamento',{'nombre_comercial':'DEMO A5 no administrar','principio_activo':'DEMO'})
    else:repo.save('medicamento',{'nombre':'DEMO A5 no administrar'})
    if institution=='pediatrico':repo.save('vacuna',{'nombre':'DEMO vacuna A4 no aplicar'})
    if institution=='laboratorio':repo.save('tipo_examen',{'nombre':'DEMO examen A4'})
print('Cuatro cuentas de prueba preparadas en identidad desechable')
