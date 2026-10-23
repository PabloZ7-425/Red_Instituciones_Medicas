"""AUC-06 SQL verification in new Docker containers; never uses project volumes/.env."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
PREPARE_NOSQL = r'''
import socket, sys
from pymongo import MongoClient
host=os.environ['AUC_MONGO_HOST']
direct=MongoClient('mongodb://'+host+':27017/?directConnection=true',serverSelectionTimeoutMS=500)
wait(lambda:(direct.admin.command('ping'),direct)[1])
direct=MongoClient('mongodb://'+host+':27017/?directConnection=true',serverSelectionTimeoutMS=1000)
direct.admin.command('replSetInitiate',{'_id':'a7','members':[{'_id':0,'host':host+':27017'}]})
direct.close()
client=MongoClient(os.environ['MONGO_URI'],serverSelectionTimeoutMS=1000)
for _ in range(120):
    try:
        if client.admin.command('hello')['isWritablePrimary']:break
    except Exception:pass
    time.sleep(.5)
else:raise RuntimeError('Temporary replica set did not become writable')
sys.path.insert(0,'/schema/mongo')
from clinical_schema import prepare as clinical
from specialty_schema import prepare as specialty
from operations_schema import prepare as operations
db=client.get_default_database();clinical(db);specialty(db);operations(db);client.close()
def emulator():
    c=socket.create_connection((os.environ['AUC_FIRESTORE_HOST'],8080),timeout=1)
    return c
wait(emulator)
print('Prepared temporary Mongo replica set and Firestore emulator',flush=True)
'''
PREPARE = r'''
import os, time
from pathlib import Path
import psycopg
import mysql.connector
from apps.historiales.testing.mysql import execute_script

password=os.environ['AUC_TEST_PASSWORD']
def wait(connect):
    for _ in range(120):
        try:
            c=connect();c.close();return
        except Exception:time.sleep(.5)
    raise RuntimeError('Temporary database did not start')
pg=lambda **kw:psycopg.connect(host=os.environ['POSTGRES_HOST'],user='postgres',password=password,**kw)
my=lambda:mysql.connector.connect(host=os.environ['MYSQL_HOST'],user='root',password=password)
wait(lambda:pg(dbname='postgres'));wait(my)
with pg(dbname='postgres',autocommit=True) as c:
    c.execute("CREATE ROLE hospital_runtime LOGIN PASSWORD %s" % ("'"+password+"'"))
    for name in ['hospital','hospital_auc']:c.execute('CREATE DATABASE '+name)
for name in ['hospital','hospital_auc']:
    with pg(dbname=name) as c:
        c.execute(Path('/schema/postgres/init.sql').read_text())
        c.execute('GRANT USAGE ON SCHEMA public TO hospital_runtime')
        c.execute(Path('/schema/postgres/operations_runtime.sql').read_text())
    # Exercise the explicit upgrade twice; it preserves the new schema/data.
    with pg(dbname=name,autocommit=True) as c:
        for _ in range(2):c.execute(Path('/schema/postgres/operations_upgrade.sql').read_text())
with my() as c:
    with c.cursor() as cursor:
        cursor.execute("CREATE USER 'pediatria_runtime'@'%' IDENTIFIED BY %s",(password,))
        for name in ['pediatrico','pediatrico_auc']:
            cursor.execute('CREATE DATABASE '+name+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin')
            cursor.execute('USE '+name)
            execute_script(c,Path('/schema/mysql/init.sql').read_text())
            execute_script(c,Path('/schema/mysql/operations_runtime.sql').read_text().replace('pediatrico.',name+'.'))
            cursor.execute("GRANT SELECT ON "+name+".pediatria_schema_version TO 'pediatria_runtime'@'%'")
print('Prepared four disposable SQL databases and limited runtime roles',flush=True)
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',default='docker')
    parser.add_argument('--image',default='red_instituciones_medicas-backend:latest')
    parser.add_argument('--transitions',action='store_true',help='Include AUC-07 and dedicated document engines')
    parser.add_argument('--coverage',action='store_true',help='Include AUC-08 frozen API permission matrix')
    parser.add_argument('--browser',action='store_true',help='Include AUC-08 Chromium UI scenarios on a new identity database')
    parser.add_argument('--browser-only',action='store_true',help='Run UI scenarios with fresh engines without repeating the native suite')
    parser.add_argument('--guided',action='store_true',help='Include AUC-09 guided navigation and paginated accounts')
    parser.add_argument('--firestore-jar',type=Path,default=ROOT/'.local'/'validation'/'firestore.jar')
    args=parser.parse_args()
    if args.guided:args.browser=True
    if args.browser_only:args.browser=True
    if args.browser:args.coverage=True
    if args.coverage:args.transitions=True
    if args.transitions and not args.firestore_jar.is_file():parser.error('Provide an existing Firestore emulator JAR')
    task=('auc08-' if args.coverage else 'auc07-' if args.transitions else 'auc06-')+uuid.uuid4().hex[:12]
    work=ROOT/'.local'/'validation'/task
    work.mkdir(parents=True)
    password=secrets.token_urlsafe(32)
    containers=[];network=None

    def docker(*argv,check=True):
        result=subprocess.run([args.docker,*argv],capture_output=True,text=True,encoding='utf-8',errors='replace')
        if check and result.returncode:
            raise RuntimeError((result.stdout+result.stderr).replace(password,'[redacted]'))
        return result

    try:
        network=docker('network','create','--label','codex.task='+task,task).stdout.strip()
        for suffix,image,env in [('pg','postgres:16',{'POSTGRES_PASSWORD':password}),
                                 ('mysql','mysql:8.4',{'MYSQL_ROOT_PASSWORD':password,'MYSQL_ROOT_HOST':'%'})]:
            envpath=work/(suffix+'.env')
            envpath.write_text(''.join(k+'='+v+'\n' for k,v in env.items()),encoding='utf-8')
            name=task+'-'+suffix
            identifier=docker('run','-d','--name',name,'--label','codex.task='+task,'--network',task,
                              '--env-file',str(envpath),image).stdout.strip()
            containers.append(identifier)
        environment={'AUC_TEST_PASSWORD':password,'PYTHONPATH':'/app','DJANGO_SETTINGS_MODULE':'config.test_settings',
                     'OPERATIONS_REAL_TESTS':'1','POSTGRES_HOST':task+'-pg','POSTGRES_PORT':'5432',
                     'POSTGRES_DB':'hospital','PG_USER':'hospital_runtime','PG_PASSWORD':password,
                     'MYSQL_HOST':task+'-mysql','MYSQL_PORT':'3306','MYSQL_DB':'pediatrico',
                     'MYSQL_USER':'pediatria_runtime','MYSQL_PASSWORD':password}
        if args.transitions:
            containers.append(docker('run','-d','--name',task+'-mongo','--label','codex.task='+task,'--network',task,
                                     'mongo:7','mongod','--replSet','a7','--bind_ip_all').stdout.strip())
            containers.append(docker('run','-d','--name',task+'-firestore','--label','codex.task='+task,'--network',task,
                '--mount','type=bind,source='+str(args.firestore_jar.resolve())+',target=/emulator.jar,readonly',
                '--entrypoint','java','red_instituciones_medicas-firestore:latest','-jar','/emulator.jar',
                '--host=0.0.0.0','--port=8080','--project_id=demo-auc07').stdout.strip())
            environment.update(OPERATIONS_NOSQL_TRANSITIONS='1',AUC_MONGO_HOST=task+'-mongo',
                MONGO_URI='mongodb://'+task+'-mongo:27017/auc07?replicaSet=a7',
                AUC_FIRESTORE_HOST=task+'-firestore',FIRESTORE_EMULATOR_HOST=task+'-firestore:8080',FIREBASE_PROJECT_ID='demo-auc07')
        if args.coverage:environment['AUC08_PERMISSION_MATRIX']='/permission_matrix.csv'
        if args.guided:environment['RUN_AUC09_GUIDED']='1'
        envpath=work/'runner.env'
        envpath.write_text(''.join(k+'='+v+'\n' for k,v in environment.items()),encoding='utf-8')
        script=work/'prepare.py';script.write_text(PREPARE+(PREPARE_NOSQL if args.transitions else ''),encoding='utf-8')
        base=['run','--rm','--label','codex.task='+task,'--network',task,'--env-file',str(envpath),
              '--mount','type=bind,source='+str(ROOT/'backend')+',target=/app,readonly',
              '--mount','type=bind,source='+str(ROOT/'db')+',target=/schema,readonly',
              '--mount','type=bind,source='+str(ROOT/'backend/apps/operaciones/permission_matrix.csv')+',target=/permission_matrix.csv,readonly',
              '--mount','type=bind,source='+str(work)+',target=/checks,readonly','--workdir','/app',args.image]
        setup=docker(*base,'python','-u','/checks/prepare.py')
        print(setup.stdout,flush=True)
        tests=['apps.operaciones.test_finance','apps.operaciones.test_chronology',
               'apps.operaciones.tests.DefinitionTests','apps.operaciones.tests.PermissionTests',
               'apps.operaciones.tests.NativeOperationsTests.test_hospital_full_operational_chain',
               'apps.operaciones.tests.NativeOperationsTests.test_pediatrics_full_operational_chain',
               'apps.operaciones.test_audit_blockers']
        if args.transitions:
            tests+=['apps.operaciones.test_transitions','apps.operaciones.tests.NativeOperationsTests.test_documental_catalog_agenda_and_payments']
        if args.coverage:tests+=['apps.operaciones.test_coverage']
        if args.guided:tests+=['apps.operaciones.test_guided']
        result=(subprocess.CompletedProcess([],0,'Native suite not repeated (--browser-only); see separate native report\n','')
                if args.browser_only else docker(*base,'python','manage.py','test',*tests,'--settings=config.test_settings','-v','2',check=False))
        output=(result.stdout+result.stderr).replace(password,'[redacted]')
        (work/'tests.log').write_text(output,encoding='utf-8')
        (work/'report.json').write_text(json.dumps({'exit_code':result.returncode,'source':subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'working_tree':True,'native_executed':not args.browser_only,'tests':tests,
            'scope':'fresh PostgreSQL16/MySQL8.4'+('/Mongo7/Firestore' if args.transitions else '')+'; limited SQL runtime roles; no shared data'},indent=2),encoding='utf-8')
        print(output,flush=True)
        print('Report: '+str(work/'report.json'),flush=True)
        if result.returncode==0 and args.browser:
            if not (ROOT/'frontend/dist/index.html').exists():raise RuntimeError('Build frontend with VITE_API_URL=/api first')
            (work/'auc08_settings.py').write_text("from config.test_settings import *\nDATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':'/checks/identity.sqlite3'}}\nALLOWED_HOSTS=['127.0.0.1','localhost',"+repr(task+'-backend')+"]\nCSRF_TRUSTED_ORIGINS=['http://127.0.0.1:18175']\nSESSION_COOKIE_SECURE=False\nCSRF_COOKIE_SECURE=False\nDEBUG=True\n",encoding='utf-8')
            (work/'seed_coverage.py').write_text((ROOT/'docs/implementacion/seed_coverage.py').read_text(encoding='utf-8'),encoding='utf-8')
            browserbase=['run','--label','codex.task='+task,'--network',task,'--env-file',str(envpath),
                '-e','RUN_AUC08_BROWSER=1','-e','PYTHONPATH=/checks:/app','-e','DJANGO_SETTINGS_MODULE=auc08_settings',
                '--mount','type=bind,source='+str(ROOT/'backend')+',target=/app,readonly',
                '--mount','type=bind,source='+str(work)+',target=/checks','--workdir','/app']
            seeded=docker(*browserbase,'--rm',args.image,'python','/checks/seed_coverage.py')
            print(seeded.stdout,flush=True)
            backend=docker(*browserbase,'-d','--name',task+'-backend',args.image,
                           'python','manage.py','runserver','0.0.0.0:8000','--noreload').stdout.strip()
            containers.append(backend)
            browser=docker('run','--rm','--label','codex.task='+task,'--network',task,'--env-file',str(envpath),
                '-e','RUN_AUC08_BROWSER=1','-e','AUC_API_HOST='+task+'-backend',
                '--mount','type=bind,source='+str(work)+',target=/checks',
                '--mount','type=bind,source='+str(ROOT/'frontend/tests')+',target=/workspace/frontend/tests,readonly',
                '--mount','type=bind,source='+str(ROOT/'frontend/dist')+',target=/site,readonly',
                '--mount','type=bind,source='+str(ROOT/'ops')+',target=/workspace/ops,readonly',
                '--entrypoint','node','pablo-validation-runner:latest','/workspace/frontend/tests/browser-coverage.mjs',check=False)
            output=(browser.stdout+browser.stderr).replace(password,'[redacted]')
            (work/'browser.log').write_text(output,encoding='utf-8');print(output,flush=True)
            report=json.loads((work/'report.json').read_text(encoding='utf-8'))
            report.update(native_exit_code=result.returncode,browser_exit_code=browser.returncode,exit_code=browser.returncode,browser_report='browser-report.json')
            (work/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            if browser.returncode:
                logs=docker('logs',backend,check=False)
                (work/'backend.log').write_text((logs.stdout+logs.stderr).replace(password,'[redacted]'),encoding='utf-8')
                return browser.returncode
        return result.returncode
    finally:
        for identifier in reversed(containers):
            label=docker('inspect','--format','{{ index .Config.Labels "codex.task" }}',identifier,check=False)
            if label.returncode==0 and label.stdout.strip()==task:
                docker('rm','-f','-v',identifier,check=False)
        if network:
            label=docker('network','inspect','--format','{{ index .Labels "codex.task" }}',network,check=False)
            if label.returncode==0 and label.stdout.strip()==task:docker('network','rm',network,check=False)


if __name__=='__main__':
    sys.exit(main())
