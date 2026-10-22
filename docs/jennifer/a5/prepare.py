"""Prepare only the disposable A5 stack described in A5_INTEGRACION_REAL.md.

No active Compose services, migrations of shared data, or production credentials.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime', type=Path, required=True)
args = parser.parse_args()
root = args.runtime.resolve()
if root.parent.name != 'work' or root.name != 'a5-runtime':
    raise SystemExit('Se requiere work/a5-runtime dedicado')
for engine in ('postgres', 'mysql', 'mongo'):
    result = json.loads(subprocess.check_output(['docker', 'inspect', 'jennifer-a5-' + engine]))[0]
    if result['Config']['Labels'].get('codex.task') != 'jennifer-a5' or not result['State']['Running']:
        raise SystemExit('Contenedor A5 dedicado ausente/no iniciado')
pw = json.loads((root / 'private.json').read_text())
sys.path[:0] = [str(root), str(root / 'backend'), str(root / 'db/mongo')]
import psycopg
from psycopg import sql
import mysql.connector
from pymongo import MongoClient
from google.cloud import firestore
from google.auth.credentials import AnonymousCredentials
from apps.historiales.testing.mysql import execute_script
from clinical_schema import prepare

with psycopg.connect(host='127.0.0.1', port=15435, dbname='postgres', user='postgres', password=pw['postgres'], autocommit=True) as conn:
    for name in ('hospital', 'identidad'):
        if conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', (name,)).fetchone():
            raise SystemExit('A5 requiere cluster nuevo; no se sobrescribe una base previa')
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    for role, key in [('hospital_runtime', 'hospital'), ('identidad_app', 'identity_app'), ('identidad_migrator', 'identity_migrator')]:
        conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD {}').format(sql.Identifier(role), sql.Literal(pw[key])))
with psycopg.connect(host='127.0.0.1', port=15435, dbname='hospital', user='postgres', password=pw['postgres']) as conn:
    conn.execute((root / 'db/postgres/init.sql').read_text())
    conn.execute("INSERT INTO especialidad(id_especialidad,nombre,nivel_complejidad) VALUES(1,'DEMO',1)")
    conn.execute("INSERT INTO medico(id_medico,id_especialidad,nombre_completo,colegiado) VALUES(1,1,'DEMO A5','DEMO-A5')")
    conn.execute("INSERT INTO medicamento(nombre_comercial,principio_activo) VALUES('DEMO A5 no administrar','DEMO')")
    grants = (root / 'db/postgres/runtime_role.sql').read_text()
    conn.execute(grants[grants.index('GRANT USAGE ON SCHEMA public'):])
with psycopg.connect(host='127.0.0.1', port=15435, dbname='identidad', user='postgres', password=pw['postgres']) as conn:
    conn.execute('ALTER DATABASE identidad OWNER TO identidad_migrator')
    conn.execute('REVOKE ALL ON DATABASE identidad FROM PUBLIC')
    conn.execute('GRANT CONNECT ON DATABASE identidad TO identidad_app')
    conn.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
    conn.execute('GRANT USAGE,CREATE ON SCHEMA public TO identidad_migrator')
    conn.execute('GRANT USAGE ON SCHEMA public TO identidad_app')
    conn.execute('ALTER DEFAULT PRIVILEGES FOR ROLE identidad_migrator IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO identidad_app')
    conn.execute('ALTER DEFAULT PRIVILEGES FOR ROLE identidad_migrator IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO identidad_app')
with mysql.connector.connect(host='127.0.0.1', port=3306, user='root', password=pw['mysql']) as conn:
    with conn.cursor() as c:
        c.execute("SHOW DATABASES LIKE 'pediatrico'")
        if c.fetchone():
            raise SystemExit('A5 requiere MySQL nuevo; no se sobrescribe pediatrico')
        c.execute('CREATE DATABASE pediatrico CHARACTER SET utf8mb4')
        c.execute('USE pediatrico')
        c.execute("CREATE USER 'pediatria_runtime'@'%' IDENTIFIED BY %s", (pw['pediatria'],))
    execute_script(conn, (root / 'db/mysql/init.sql').read_text())
    with conn.cursor() as c:
        c.execute("INSERT INTO especialidad(id,nombre) VALUES(1,'DEMO')")
        c.execute("INSERT INTO medico(id,nombre,apellido,colegiado,especialidad_id) VALUES(1,'DEMO','A5','DEMO-A5',1)")
        c.execute("INSERT INTO medicamento(nombre) VALUES('DEMO A5 no administrar')")
    grants = (root / 'db/mysql/runtime_role.sql').read_text()
    execute_script(conn, grants[grants.index('GRANT SELECT'):])
    conn.commit()
with MongoClient('mongodb://127.0.0.1:27039/laboratorio?replicaSet=a5', serverSelectionTimeoutMS=3000) as client:
    if client.laboratorio.list_collection_names():
        raise SystemExit('A5 requiere Mongo vacío dedicado')
    prepare(client.laboratorio)
    client.laboratorio.clinico_medicamentos.insert_one({'_id':'DEMO-A5-M','nombre':'DEMO A5 no administrar','presentacion':None,'schema_version':2,'institucion':'laboratorio'})
os.environ['FIRESTORE_EMULATOR_HOST'] = '127.0.0.1:8093'
client = firestore.Client(project='demo-jennifer-a5', credentials=AnonymousCredentials())
try:
    if list(client.collections()):
        raise SystemExit('A5 requiere proyecto emulado vacío dedicado')
    client.collection('medicamentos').document('DEMO-A5-M').set({'nombre':'DEMO A5 no administrar','presentacion':None,'schema_version':2,'institucion':'odontologica'})
finally:
    client.close()
env = {
    'DJANGO_SETTINGS_MODULE':'a5_settings', 'DJANGO_DEBUG':'true',
    'IDENTITY_DB_MODE':'postgres', 'IDENTITY_DB_HOST':'127.0.0.1','IDENTITY_DB_PORT':'15435',
    'IDENTITY_APP_PASSWORD':pw['identity_app'],
    'POSTGRES_HOST':'127.0.0.1','POSTGRES_PORT':'15435','POSTGRES_DB':'hospital', 'PG_USER':'hospital_runtime','PG_PASSWORD':pw['hospital'],
    'MYSQL_HOST':'127.0.0.1','MYSQL_PORT':'3306','MYSQL_DB':'pediatrico','MYSQL_USER':'pediatria_runtime','MYSQL_PASSWORD':pw['pediatria'],
    'MONGO_URI':'mongodb://127.0.0.1:27039/laboratorio?replicaSet=a5',
    'FIRESTORE_EMULATOR_HOST':'127.0.0.1:8093','FIREBASE_PROJECT_ID':'demo-jennifer-a5',
}
os.environ.update(env)
os.environ['IDENTITY_MIGRATOR_PASSWORD'] = pw['identity_migrator']
import django
django.setup()
from django.core.management import call_command
call_command('migrate', database='identity_migration', interactive=False, verbosity=0)
from django.contrib.auth.models import User
from apps.identidad.models import PerfilInstitucional, Profesional
for institution in ('hospital','pediatrico','laboratorio','odontologica'):
    pro = Profesional.objects.create(institucion=institution, referencia_externa='1')
    for role in ('admin','medico','secretaria','enfermero', *(['laboratorista'] if institution=='laboratorio' else [])):
        user = User.objects.create_user(username=f'DEMO-A5-{role}-{institution}', password='DEMO-only-isolated-A5-2026')
        PerfilInstitucional.objects.create(usuario=user, institucion=institution, rol=role, profesional=pro if role in {'admin','medico','laboratorista'} else None)
p=root/'server.json';p.write_text(json.dumps(env));p.chmod(0o600)
print('A5 preparado: cuatro motores vacíos con catálogos DEMO y PostgreSQL técnico; roles runtime limitados SQL')
