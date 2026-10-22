"""Create a fresh work/a5-runtime from pinned Git sources; no service or branch writes."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import secrets
import subprocess
import tarfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--runtime',type=Path,required=True)
p.add_argument('--pablo-ref',default='HEAD',help='Backend/base snapshot; defaults to the assembled current branch')
p.add_argument('--jennifer-ref',default='HEAD',help='Frontend/NoSQL snapshot; defaults to the assembled current branch')
a=p.parse_args()
root=a.runtime.resolve()
if root.parent.name!='work' or root.name!='a5-runtime' or root.exists():
    raise SystemExit('Requiere destino nuevo work/a5-runtime; no se sobrescribe contenido')
repo=Path(__file__).resolve().parents[3]
def git(*args):
    return subprocess.check_output(['git',*args],cwd=repo)
b=git('rev-parse',a.pablo_ref+'^{commit}').decode().strip()
creator=git('rev-parse',a.jennifer_ref+'^{commit}').decode().strip()
root.mkdir(parents=True)
def extract(ref,*paths):
    with tarfile.open(fileobj=BytesIO(git('archive',ref,*paths)),mode='r:') as archive:
        archive.extractall(root,filter='data')
extract(b)
extract(creator,'frontend','db/firebase','db/mongo',
        'backend/apps/historiales/infrastructure/adapters/mongo_adapter.py',
        'backend/apps/historiales/infrastructure/adapters/firestore_adapter.py')
(root/'a5_settings.py').write_text("from config.settings import *\nCORS_ALLOWED_ORIGINS = ['http://127.0.0.1:18173']\nCSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS\nALLOWED_HOSTS = ['127.0.0.1','localhost','testserver']\n")
passwords={k:secrets.token_urlsafe(30) for k in ['postgres','mysql','hospital','pediatria','identity_app','identity_migrator']}
for name,value in {
    'private.json':json.dumps(passwords),
    'postgres.env':'POSTGRES_PASSWORD='+passwords['postgres']+'\nPOSTGRES_USER=postgres\n',
    'mysql.env':'MYSQL_ROOT_PASSWORD='+passwords['mysql']+'\n',
}.items():
    path=root/name
    path.write_text(value)
    path.chmod(0o600)
(root/'sources.json').write_text(json.dumps({'pablo':b,'jennifer':creator},indent=2))
print('Copia A5 preparada; secretos locales protegidos y sin cambios de Git')
