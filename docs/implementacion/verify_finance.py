"""AUC-06 SQL verification in new Docker containers; never uses project volumes/.env."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
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
    args=parser.parse_args()
    task='auc06-'+uuid.uuid4().hex[:12]
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
        envpath=work/'runner.env'
        envpath.write_text(''.join(k+'='+v+'\n' for k,v in environment.items()),encoding='utf-8')
        script=work/'prepare.py';script.write_text(PREPARE,encoding='utf-8')
        base=['run','--rm','--label','codex.task='+task,'--network',task,'--env-file',str(envpath),
              '--mount','type=bind,source='+str(ROOT/'backend')+',target=/app,readonly',
              '--mount','type=bind,source='+str(ROOT/'db')+',target=/schema,readonly',
              '--mount','type=bind,source='+str(work)+',target=/checks,readonly','--workdir','/app',args.image]
        setup=docker(*base,'python','-u','/checks/prepare.py')
        print(setup.stdout,flush=True)
        tests=['apps.operaciones.test_finance','apps.operaciones.test_chronology',
               'apps.operaciones.tests.DefinitionTests','apps.operaciones.tests.PermissionTests',
               'apps.operaciones.tests.NativeOperationsTests.test_hospital_full_operational_chain',
               'apps.operaciones.tests.NativeOperationsTests.test_pediatrics_full_operational_chain',
               'apps.operaciones.test_audit_blockers']
        result=docker(*base,'python','manage.py','test',*tests,'--settings=config.test_settings','-v','2',check=False)
        output=(result.stdout+result.stderr).replace(password,'[redacted]')
        (work/'tests.log').write_text(output,encoding='utf-8')
        (work/'report.json').write_text(json.dumps({'exit_code':result.returncode,'source':subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'working_tree':True,'tests':tests,
            'scope':'fresh PostgreSQL16/MySQL8.4; limited runtime roles; no shared data'},indent=2),encoding='utf-8')
        print(output,flush=True)
        print('Report: '+str(work/'report.json'),flush=True)
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
