"""Run operational tests only in newly-created, disposable local engines.

Requires Docker, Firestore emulator jar and installed backend dependencies.
Never reads .env/shared credentials or mounts any shared clinical volume.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',action='store_true',required=True)
parser.add_argument('--work',type=Path,required=True)
parser.add_argument('--browser',action='store_true')
parser.add_argument('--jar',type=Path,required=True)
args=parser.parse_args()
work=args.work.resolve()
if work.exists() or ROOT in work.parents or not args.jar.is_file():raise SystemExit('Se requiere directorio nuevo fuera del repo y JAR existente')
for port in [15436,13307,27059,8099]+([18015,18175] if args.browser else []):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:s.bind(('127.0.0.1',port))
        except OSError:raise SystemExit('Puerto ocupado; no se modifica el servicio existente')
work.mkdir(parents=True,mode=0o700)
pw=secrets.token_urlsafe(24);task='implementacion-'+uuid.uuid4().hex[:10];containers=[];java=None;servers=[]
base_env={k:v for k,v in os.environ.items() if k not in {'DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'}}

def docker(*cmd,**kw):return subprocess.check_output(['docker','--host=unix:///var/run/docker.sock',*cmd],env=base_env,text=True,**kw).strip()

def create(image,port,mapped,envs=(),command=()):
    argv=['run','-d','--label','codex.task='+task,'-p',f'127.0.0.1:{port}:{mapped}']
    for name,value in envs:argv+=['-e',name+'='+value]
    identifier=docker(*argv,image,*command);containers.append(identifier);return identifier

def wait(callback):
    for _ in range(120):
        try:return callback()
        except Exception:time.sleep(.5)
    raise RuntimeError('El motor de prueba no inició')

try:
    docker('info','--format','{{.ServerVersion}}')
    pg=create('postgres:16',15436,5432,[('POSTGRES_PASSWORD',pw)])
    my=create('mysql:8.4',13307,3306,[('MYSQL_ROOT_PASSWORD',pw)])
    mo=create('mongo:7',27059,27059,command=['mongod','--replSet','a3','--bind_ip_all','--port','27059'])
    log=(work/'firestore.log').open('w')
    java=subprocess.Popen(['java','-jar',str(args.jar.resolve()),'--host=127.0.0.1','--port=8099','--project_id=demo-operaciones'],stdout=log,stderr=subprocess.STDOUT)
    import psycopg
    import mysql.connector
    from pymongo import MongoClient
    sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'db/mongo')]
    from apps.historiales.testing.mysql import execute_script
    wait(lambda:psycopg.connect(host='127.0.0.1',port=15436,dbname='postgres',user='postgres',password=pw).close())
    with psycopg.connect(host='127.0.0.1',port=15436,dbname='postgres',user='postgres',password=pw,autocommit=True) as c:c.execute('CREATE DATABASE hospital')
    with psycopg.connect(host='127.0.0.1',port=15436,dbname='hospital',user='postgres',password=pw) as c:
        c.execute((ROOT/'db/postgres/init.sql').read_text())
        c.execute('CREATE ROLE hospital_runtime LOGIN PASSWORD %s' % ("'"+pw+"'"))
        c.execute('GRANT USAGE ON SCHEMA public TO hospital_runtime')
        c.execute((ROOT/'db/postgres/operations_runtime.sql').read_text())
    with psycopg.connect(host='127.0.0.1',port=15436,dbname='postgres',user='postgres',password=pw,autocommit=True) as c:c.execute('CREATE DATABASE hospital_auc')
    with psycopg.connect(host='127.0.0.1',port=15436,dbname='hospital_auc',user='postgres',password=pw) as c:
        c.execute((ROOT/'db/postgres/init.sql').read_text())
        c.execute('GRANT USAGE ON SCHEMA public TO hospital_runtime')
        c.execute((ROOT/'db/postgres/operations_runtime.sql').read_text())
    wait(lambda:mysql.connector.connect(host='127.0.0.1',port=13307,user='root',password=pw).close())
    with mysql.connector.connect(host='127.0.0.1',port=13307,user='root',password=pw) as c:
        with c.cursor() as cursor:
            cursor.execute('CREATE DATABASE pediatrico CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin');cursor.execute('USE pediatrico')
            execute_script(c,(ROOT/'db/mysql/init.sql').read_text())
            cursor.execute("CREATE USER 'pediatria_runtime'@'%' IDENTIFIED BY %s",(pw,))
            execute_script(c,(ROOT/'db/mysql/operations_runtime.sql').read_text())
            cursor.execute("GRANT SELECT ON pediatrico.pediatria_schema_version TO 'pediatria_runtime'@'%'")
    with mysql.connector.connect(host='127.0.0.1',port=13307,user='root',password=pw) as c:
        with c.cursor() as cursor:
            cursor.execute('CREATE DATABASE pediatrico_auc CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin');cursor.execute('USE pediatrico_auc')
            execute_script(c,(ROOT/'db/mysql/init.sql').read_text())
            execute_script(c,(ROOT/'db/mysql/operations_runtime.sql').read_text().replace('pediatrico.','pediatrico_auc.'))
            cursor.execute("GRANT SELECT ON pediatrico_auc.pediatria_schema_version TO 'pediatria_runtime'@'%'")
    with MongoClient('mongodb://127.0.0.1:27059/?directConnection=true',serverSelectionTimeoutMS=500) as c:
        wait(lambda:c.admin.command('ping'))
        c.admin.command('replSetInitiate',{'_id':'a3','members':[{'_id':0,'host':'127.0.0.1:27059'}]})
    uri='mongodb://127.0.0.1:27059/operaciones?replicaSet=a3'
    with MongoClient(uri,serverSelectionTimeoutMS=500) as c:
        wait(lambda:c.admin.command('hello')['isWritablePrimary'] or (_ for _ in ()).throw(RuntimeError()))
        from clinical_schema import prepare
        from specialty_schema import prepare as specialty
        from operations_schema import prepare as operations
        prepare(c.get_default_database());specialty(c.get_default_database());operations(c.get_default_database())
    def firestore_ready():
        with socket.create_connection(('127.0.0.1',8099),timeout=.5):pass
    wait(firestore_ready)
    env=os.environ|{'PYTHONPATH':str(ROOT/'backend'),'OPERATIONS_REAL_TESTS':'1','POSTGRES_HOST':'127.0.0.1','POSTGRES_PORT':'15436','POSTGRES_DB':'hospital','PG_USER':'hospital_runtime','PG_PASSWORD':pw,'MYSQL_HOST':'127.0.0.1','MYSQL_PORT':'13307','MYSQL_DB':'pediatrico','MYSQL_USER':'pediatria_runtime','MYSQL_PASSWORD':pw,'MONGO_URI':uri,'FIRESTORE_EMULATOR_HOST':'127.0.0.1:8099','FIREBASE_PROJECT_ID':'demo-operaciones'}
    private=work/'environment.json';private.write_text(json.dumps({k:env[k] for k in ['POSTGRES_HOST','POSTGRES_PORT','POSTGRES_DB','PG_USER','PG_PASSWORD','MYSQL_HOST','MYSQL_PORT','MYSQL_DB','MYSQL_USER','MYSQL_PASSWORD','MONGO_URI','FIRESTORE_EMULATOR_HOST','FIREBASE_PROJECT_ID']}));private.chmod(0o600)
    env.update(OPERATIONS_NOSQL_TRANSITIONS='1',A3_NOSQL_TESTS='1',A3_MONGO_TEST_URI='mongodb://127.0.0.1:27059/?replicaSet=a3',A3_MONGO_SCHEMA=str(ROOT/'db/mongo/clinical_schema.py'))
    result=subprocess.run([sys.executable,'backend/manage.py','test','apps.operaciones','apps.historiales.test_clinical_nosql','--settings=config.test_settings','-v','2'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (work/'tests.log').write_text(result.stdout);print(result.stdout)
    (work/'report.json').write_text(json.dumps({'exit_code':result.returncode,'suite':'operaciones','source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'working_tree':True}))
    if result.returncode:raise SystemExit(result.returncode)
    if args.browser:
        settings=work/'operations_browser_settings.py'
        settings.write_text("from config.settings import *\nimport os\nDATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':os.environ['OPERATIONS_BROWSER_WORK']+'/identity.sqlite3'}}\nSECRET_KEY='disposable-operations-only'\nDEBUG=True\nSESSION_COOKIE_SECURE=False\nCSRF_COOKIE_SECURE=False\nCORS_ALLOWED_ORIGINS=['http://127.0.0.1:18175']\nCSRF_TRUSTED_ORIGINS=CORS_ALLOWED_ORIGINS\nALLOWED_HOSTS=['127.0.0.1','localhost']\n")
        env.update(PYTHONPATH=str(work)+os.pathsep+str(ROOT/'backend'),DJANGO_SETTINGS_MODULE='operations_browser_settings',OPERATIONS_BROWSER_WORK=str(work))
        setup="import django;django.setup();exec(compile(open('docs/implementacion/browser_setup.py').read(),'browser_setup.py','exec'))"
        subprocess.run([sys.executable,'-c',setup],cwd=ROOT,env=env,check=True)
        subprocess.run(['npm','--prefix','frontend','run','build'],cwd=ROOT,env=env|{'VITE_API_URL':'http://127.0.0.1:18015/api'},check=True)
        for name,cmd in [('backend',[sys.executable,'backend/manage.py','runserver','127.0.0.1:18015','--noreload']),('frontend',['npm','--prefix','frontend','run','preview','--','--host','127.0.0.1','--port','18175','--strictPort'])]:
            handle=(work/(name+'.log')).open('w');proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True);servers.append((proc,handle))
        for port in [18015,18175]:
            wait(lambda:socket.create_connection(('127.0.0.1',port),timeout=.5).close())
        browser=subprocess.run(['node','frontend/tests/browser-operations.mjs'],cwd=ROOT,env=env|{'BROWSER_URL':'http://127.0.0.1:18175/','A5_BROWSER_PASSWORD':'DEMO-Operations-2026-Only!','A5_REAL_HTTP':'1'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (work/'browser.log').write_text(browser.stdout);print(browser.stdout)
        if browser.returncode:raise SystemExit(browser.returncode)
        for role in ['admin','secretaria','enfermero','laboratorista']:
            clinical_env=env|{'BROWSER_URL':'http://127.0.0.1:18175/','A5_BROWSER_PASSWORD':'DEMO-Operations-2026-Only!','A5_REAL_HTTP':'1','OPERATIONS_BROWSER_API':'http://127.0.0.1:18015/api/'}
            if role!='admin':clinical_env['A4_HTTP_BROWSER_ROLE']=role
            clinical=subprocess.run(['node','frontend/tests/browser-real.mjs'],cwd=ROOT,env=clinical_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            (work/('clinical-'+role+'.log')).write_text(clinical.stdout);print(clinical.stdout)
            if clinical.returncode:raise SystemExit(clinical.returncode)
        (work/'report.json').write_text(json.dumps({'exit_code':0,'suite':'operaciones+HTTP-browser','native_tests_log':'tests.log','operations_browser':4,'clinical_browser':7,'source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'working_tree':True}))
finally:
    import signal
    for process,handle in reversed(servers):
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        handle.close()
    if java:
        java.terminate()
        try:java.wait(timeout=10)
        except subprocess.TimeoutExpired:java.kill();java.wait()
    for identifier in reversed(containers):
        state=json.loads(docker('inspect',identifier))[0]
        if state['Id']==identifier and state['Config']['Labels'].get('codex.task')==task:
            docker('rm','-fv',identifier)
