"""Owned local PostgreSQL identity backup/restore, runtime grants and live session.

Called only by verify_native.py after it creates an isolated PostgreSQL container.
Never opens a shared identity database or reads credentials from files.
"""
import json
from pathlib import Path
import subprocess
import sys


def prepare(root,work,docker,container,password,env):
    import psycopg
    with psycopg.connect(host='127.0.0.1',port=15436,dbname='postgres',user='postgres',password=password,autocommit=True) as c:
        c.execute('CREATE DATABASE identidad')
    # Exercise the actual delivery role bootstrap in the newly-created database.
    docker('exec','-i','-e','POSTGRES_USER=postgres','-e','POSTGRES_DB=identidad',
           '-e','IDENTITY_APP_PASSWORD='+password,'-e','IDENTITY_MIGRATOR_PASSWORD='+password,
           container,'sh','-s',input=(root/'db/identity/01-roles.sh').read_text())
    env.update(OPERATIONS_IDENTITY_POSTGRES='1',IDENTITY_DB_MODE='postgres',IDENTITY_DB_HOST='127.0.0.1',
               IDENTITY_DB_PORT='15436',IDENTITY_DB_NAME='identidad',IDENTITY_APP_PASSWORD=password,
               IDENTITY_MIGRATOR_PASSWORD=password,OPERATIONS_IDENTITY_USER='identidad_migrator')


def restore(root,work,docker,container,password,env):
    import psycopg
    from psycopg import sql
    from upgrade_rehearsal import digest
    def connect(database,user='postgres'):
        return psycopg.connect(host='127.0.0.1',port=15436,dbname=database,user=user,password=password)
    def fingerprint(c):
        result={}
        tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
        for table in tables:
            cursor=c.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table)))
            names=[d.name for d in cursor.description]
            result[table]=sorted((dict(zip(names,r)) for r in cursor.fetchall()),key=lambda r:json.dumps(r,sort_keys=True,default=str))
        return digest(result)
    # Seed a genuine signed Django session before the dump. The cookie remains
    # private and is used once against the restored HTTP server, never published.
    seed="""import django,time,json,os
from pathlib import Path
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
client=Client();client.force_login(get_user_model().objects.get(username='DEMO-OPS-admin-hospital'))
session=client.session;session['clinical_authenticated_at']=time.time();session.save()
path=Path(os.environ['OPERATIONS_BROWSER_WORK'])/'identity-session.json'
path.write_text(json.dumps({'sessionid':session.session_key}));path.chmod(0o600)
"""
    subprocess.run([sys.executable,'-c',seed],cwd=root,env=env,check=True)
    with connect('identidad') as c:
        before=fingerprint(c)
        user_count=c.execute('SELECT COUNT(*) FROM auth_user').fetchone()[0]
        session_count=c.execute('SELECT COUNT(*) FROM django_session').fetchone()[0]
    backup=work/'identity-postgres.sql'
    backup.write_text(docker('exec',container,'pg_dump','-U','postgres','--no-owner','identidad'));backup.chmod(0o600)
    with psycopg.connect(host='127.0.0.1',port=15436,dbname='postgres',user='postgres',password=password,autocommit=True) as c:
        c.execute('CREATE DATABASE identidad_restaurada OWNER identidad_migrator')
        c.execute('REVOKE ALL ON DATABASE identidad_restaurada FROM PUBLIC')
        c.execute('GRANT CONNECT ON DATABASE identidad_restaurada TO identidad_app')
    with connect('identidad_restaurada') as c:
        c.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
        c.execute('GRANT USAGE,CREATE ON SCHEMA public TO identidad_migrator')
        c.execute('GRANT USAGE ON SCHEMA public TO identidad_app')
    # Restore as the migrator: ownership and future migration capability must
    # survive as well as rows. Keep ACLs from the dump (no --no-privileges).
    docker('exec','-i','-e','PGPASSWORD='+password,container,'psql','-h','127.0.0.1',
           '-U','identidad_migrator','-d','identidad_restaurada','--set','ON_ERROR_STOP=1',input=backup.read_text())
    with connect('identidad_restaurada') as c:
        assert fingerprint(c)==before
        assert c.execute('SELECT COUNT(*) FROM auth_user').fetchone()[0]==user_count
        assert c.execute('SELECT COUNT(*) FROM django_session').fetchone()[0]==session_count
    with connect('identidad_restaurada','identidad_app') as c:
        assert c.execute('SELECT current_user').fetchone()[0]=='identidad_app'
        assert not c.execute("SELECT has_schema_privilege(current_user,'public','CREATE')").fetchone()[0]
        for privilege in ['SELECT','INSERT','UPDATE','DELETE']:
            assert c.execute("SELECT has_table_privilege(current_user,'django_session',%s)",(privilege,)).fetchone()[0]
        assert not any(c.execute('SELECT rolcreatedb,rolcreaterole,rolsuper FROM pg_roles WHERE rolname=current_user').fetchone())
        # Verify real denials, not only catalog grants. Each failure rolls back.
        for statement in ['CREATE TABLE auc12_forbidden(id int)','ALTER TABLE auth_user ADD COLUMN auc12_forbidden int']:
            try:c.execute(statement)
            except psycopg.errors.InsufficientPrivilege:c.rollback()
            else:raise AssertionError('Identity runtime unexpectedly accepted DDL')
    with connect('identidad_restaurada','identidad_migrator') as c:
        c.execute('CREATE TABLE auc12_migrator_probe(id int)');c.execute('DROP TABLE auc12_migrator_probe')
    env.update(IDENTITY_DB_NAME='identidad_restaurada',OPERATIONS_IDENTITY_USER='identidad_app')
    report={'provider':'PostgreSQL 16, isolated database with actual identity bootstrap roles',
            'backup_restored':True,'data_sha256':before,'users_preserved':user_count,'sessions_preserved':session_count,
            'password_hashes_profiles_professionals_preserved':True,'runtime_role':'identidad_app',
            'runtime_ddl_rejected':True,'runtime_not_superuser_or_role_database_creator':True,
            'migrator_ownership_and_ddl_verified':True,'shared_installation_verified':False}
    (work/'identity-postgres-report.json').write_text(json.dumps(report,indent=2)+'\n')
    path=work/'upgrade-report.json'
    if path.exists():
        upgrade=json.loads(path.read_text());upgrade['identity']=report;path.write_text(json.dumps(upgrade,indent=2)+'\n')
    print('OK AUC-12 identity PostgreSQL: populated backup restored; accounts/sessions/ownership/runtime grants preserved')


def verify_session(work):
    import requests
    cookie=json.loads((work/'identity-session.json').read_text())['sessionid']
    with requests.Session() as client:
        client.cookies.set('sessionid',cookie,domain='127.0.0.1',path='/')
        response=client.get('http://127.0.0.1:18015/api/auth/me/',timeout=15)
        assert response.status_code==200,'Pre-backup identity session did not survive restoration'
        user=response.json()['usuario']
        assert user['username']=='DEMO-OPS-admin-hospital' and user['institucion']=='hospital'
    path=work/'identity-postgres-report.json';report=json.loads(path.read_text())
    report['pre_backup_session_valid_after_restore']=True
    path.write_text(json.dumps(report,indent=2)+'\n')
    path=work/'upgrade-report.json'
    if path.exists():
        upgrade=json.loads(path.read_text());upgrade['identity']=report;path.write_text(json.dumps(upgrade,indent=2)+'\n')
