"""Explicit disposable PostgreSQL rehearsal of identity consolidation; no shared DBs."""
import argparse
import sys
import os, subprocess, secrets, time, pathlib, json
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', action='store_true', required=True)
parser.add_argument('--work', type=pathlib.Path, required=True)
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[2];py=sys.executable
work=args.work.resolve()
if work.exists() or work==root or root in work.parents:
    raise RuntimeError('Use a new work directory outside the repository')
work.mkdir(parents=True,mode=0o700)
env=os.environ.copy()
for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
def docker(*args,**kw):return subprocess.check_output(['docker','--host=unix:///var/run/docker.sock',*args],env=env,text=True,**kw).strip()
pw=secrets.token_urlsafe(24);container=docker('run','-d','--label','codex.task=single-pg-identity','-p','127.0.0.1:15438:5432','-e','POSTGRES_PASSWORD='+pw,'postgres:16')
def run(args,e,code=None):
 r=subprocess.run([py,*args],input=code,env=e,cwd=root/'backend',text=True,capture_output=True)
 if r.returncode:print(r.stdout);print(r.stderr);raise RuntimeError('Subprocess failed')
 print(r.stdout.strip())
try:
 for attempt in range(80):
  try:
   docker('exec',container,'pg_isready','-U','postgres');break
  except subprocess.CalledProcessError:time.sleep(.5)
 docker('exec',container,'createdb','-U','postgres','identidad')
 docker('exec',container,'createdb','-U','postgres','hospital')
 docker('exec','-i','-e','POSTGRES_USER=postgres','-e','POSTGRES_DB=identidad','-e','IDENTITY_APP_PASSWORD='+pw,'-e','IDENTITY_MIGRATOR_PASSWORD='+pw,container,'sh',input=(root/'db/identity/01-roles.sh').read_text())
 base=env|{'DJANGO_SETTINGS_MODULE':'config.settings','PYTHONPATH':str(root/'backend'),'IDENTITY_DB_MODE':'postgres','IDENTITY_DB_HOST':'127.0.0.1','IDENTITY_DB_PORT':'15438','IDENTITY_DB_NAME':'identidad','IDENTITY_DB_SCHEMA':'public','IDENTITY_APP_PASSWORD':pw,'IDENTITY_MIGRATOR_PASSWORD':pw}
 run(['manage.py','migrate','--database','identity_migration','--noinput'],base)
 run(['-c',"""import django;django.setup()
from django.contrib.auth.models import User,Group,Permission
from apps.identidad.models import Profesional,PerfilInstitucional
from django.contrib.sessions.backends.db import SessionStore
for inst in ['hospital','pediatrico','laboratorio','odontologica']:
 u=User.objects.create_user(username='single-'+inst,password='demo-proof-only-12')
 p=Profesional.objects.create(institucion=inst,referencia_externa='proof-'+inst)
 PerfilInstitucional.objects.create(usuario=u,institucion=inst,rol='admin',profesional=p)
 g=Group.objects.create(name=inst);g.permissions.add(Permission.objects.first());u.groups.add(g)
s=SessionStore();s['proof']='preserved';s.save()
print('Seeded four identities/professionals/profiles/groups and a session')
"""],base)
 docker('exec','-i','-e','PGUSER=postgres','-e','PGDATABASE=hospital','-e','IDENTITY_APP_PASSWORD='+pw,'-e','IDENTITY_MIGRATOR_PASSWORD='+pw,container,'sh',input=(root/'db/identity/consolidated-roles.sh').read_text())
 target=base|{'IDENTITY_DB_NAME':'hospital','IDENTITY_DB_SCHEMA':'identidad','IDENTITY_SOURCE_HOST':'127.0.0.1','IDENTITY_SOURCE_PORT':'15438','AUC12_SETUP':'consolidate-identity','AUC12_BACKUP_DIR':str(work)}
 run(['manage.py','migrate','--database','identity_migration','--noinput'],target)
 for i in range(2):run([str(root/'ops/auc12/consolidate_identity.py')],target)
 run(['-c',"""import django;django.setup()
from django.db import connection
from django.contrib.auth.models import User
from apps.identidad.models import PerfilInstitucional
from django.contrib.sessions.models import Session
assert User.objects.count()==4 and PerfilInstitucional.objects.count()==4
assert all(u.check_password('demo-proof-only-12') and u.groups.count()==1 for u in User.objects.all())
assert Session.objects.get().get_decoded()['proof']=='preserved'
with connection.cursor() as c:
 c.execute('SELECT current_database(),current_schema()');assert c.fetchone()==('hospital','identidad')
for stmt in ['CREATE TABLE forbidden(id int)','ALTER TABLE auth_user ADD COLUMN forbidden int']:
 try:
  with connection.cursor() as c:c.execute(stmt)
 except Exception as exc:assert getattr(exc.__cause__,'sqlstate',None)=='42501'
 else:raise AssertionError('Runtime DDL allowed')
print('PASS passwords, groups, profiles, professional links, sessions, runtime DDL isolation')
"""],target)
 # A conflicting destination must fail, without overwriting it or the original.
 run(['-c',"import django;django.setup();from django.contrib.auth.models import User;u=User.objects.first();u.first_name='changed';u.save()"],target)
 r=subprocess.run([py,str(root/'ops/auc12/consolidate_identity.py')],env=target,cwd=root/'backend',capture_output=True,text=True)
 assert r.returncode!=0 and 'Destination contains different identities' in r.stderr
 print('PASS differing destination rejected without overwrite')
 # Clinical public schema remains usable and identity app cannot read it.
 docker('exec',container,'psql','-U','postgres','-d','hospital','-c','CREATE TABLE public.clinical_proof(id int); INSERT INTO public.clinical_proof VALUES(7)')
 run(['-c',"""import django;django.setup()
from django.db import connection
try:
 with connection.cursor() as c:c.execute('SELECT * FROM public.clinical_proof')
except Exception as e:assert getattr(e.__cause__,'sqlstate',None)=='42501'
else:raise AssertionError('Identity read clinical data')
print('PASS identity role denied clinical tables')
"""],target)
 (work/'report.json').write_text(json.dumps({'single_postgres':True,'same_hospital_database':True,'schema':'identidad','four_accounts_preserved':True,'sessions_preserved':True,'idempotent':True,'conflict_rejected':True,'runtime_ddl_denied':True,'clinical_access_denied':True,'desktop_cutover_performed':False},indent=2))
finally:docker('rm','-fv',container)
