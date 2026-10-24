"""Read-only inventory executed inside the user's existing backend container.

Output is aggregate technical JSON. Never prints environment values, credentials,
patient rows, usernames, password hashes or session cookies. No seed/migrate/DDL.
"""
import hashlib
import json
import os
import re
from pathlib import Path


def safe_error(error):
    """Only publish allowlisted codes and fixed diagnoses, never driver text."""
    result={'error_type':type(error).__name__,'diagnosis':'undetermined'}
    current=error;seen=set()
    diagnoses={'28P01':'authentication_failed','28000':'authentication_failed',
               '3D000':'database_missing','42P01':'table_missing','42703':'column_missing',
               '42501':'permission_denied','08001':'connection_unavailable','08006':'connection_unavailable'}
    mysql_diagnoses={1044:'permission_denied',1045:'authentication_failed',1049:'database_missing',
                     1054:'column_missing',1142:'permission_denied',1146:'table_missing',
                     2003:'connection_unavailable',2005:'connection_unavailable'}
    while current is not None and id(current) not in seen and len(seen)<8:
        seen.add(id(current))
        state=getattr(current,'sqlstate',None)
        if isinstance(state,str) and re.fullmatch(r'[A-Z0-9]{5}',state):
            result['sqlstate']=state
            if state in diagnoses:result['diagnosis']=diagnoses[state]
        number=getattr(current,'errno',None)
        if type(number) is int and 0<number<100000:
            result['errno']=number
            if number in mysql_diagnoses:result['diagnosis']=mysql_diagnoses[number]
        # libpq connection errors often have no SQLSTATE. Inspect locally, then
        # discard all message text: it may contain passwords/hosts/row values.
        message=str(current).lower()
        if result['diagnosis']=='undetermined':
            if 'password authentication failed' in message:result['diagnosis']='authentication_failed'
            elif 'no such table' in message:result['diagnosis']='table_missing'
            elif 'connection refused' in message or 'could not translate host name' in message:result['diagnosis']='connection_unavailable'
            elif isinstance(current,KeyError):result['diagnosis']='configuration_missing'
        current=current.__cause__ or current.__context__
    return result


def observe(callback):
    try:return {'status':'ok','data':callback()}
    except Exception as error:
        return {'status':'unavailable',**safe_error(error),
                'note':'No se pudo consultar con la configuracion actual; no se cambiaron datos.'}


def identity():
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup()
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.contrib.auth import get_user_model
    from django.contrib.sessions.models import Session
    from apps.identidad.models import PerfilInstitucional, Profesional
    with connection.cursor() as cursor:
        if connection.vendor=='postgresql':
            cursor.execute('SET default_transaction_read_only=on')
            cursor.execute('SET statement_timeout=10000')
        elif connection.vendor=='sqlite':cursor.execute('PRAGMA query_only=ON')
        else:raise RuntimeError('Unsupported identity provider')
    try:
        def pending():
            executor=MigrationExecutor(connection)
            return [migration.app_label+'.'+migration.name for migration,_ in
                    executor.migration_plan(executor.loader.graph.leaf_nodes())]
        def read(callback):
            # Failed PostgreSQL reads must roll back before the next probe.
            from django.db import transaction
            with transaction.atomic():return callback()
        result={'provider':connection.vendor,'mode':os.getenv('IDENTITY_DB_MODE','legacy')}
        checks={'pending_migrations':pending,'users':get_user_model().objects.count,
                'profiles':PerfilInstitucional.objects.count,'professionals':Profesional.objects.count,
                'enabled_professionals':lambda:Profesional.objects.filter(habilitado=True).count(),
                'sessions':Session.objects.count}
        for name,callback in checks.items():result[name]=observe(lambda f=callback:read(f))
        return result
    finally:connection.close()


def postgres():
    import psycopg
    with psycopg.connect(host=os.getenv('POSTGRES_HOST','postgres'),port=int(os.getenv('POSTGRES_PORT','5432')),
                          dbname=os.getenv('POSTGRES_DB','hospital'),user=os.environ['PG_USER'],password=os.environ['PG_PASSWORD'],
                          connect_timeout=5,options='-c default_transaction_read_only=on -c statement_timeout=10000') as c:
        flags=c.execute("SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema='public' AND column_name='activo_operativo' ORDER BY table_name").fetchall()
        result={'provider':'postgresql','operations_flags':[dict(zip(['table','column','type','nullable'],row)) for row in flags]}
        for label,query in {
            'patients':'SELECT COUNT(*) FROM paciente',
            'enabled_professionals':'SELECT COUNT(*) FROM medico WHERE habilitado',
            'closed_admissions_with_open_movements':"SELECT COUNT(*) FROM movimiento_cama m JOIN ingreso_hospitalario i USING(id_ingreso) WHERE i.alta_utc IS NOT NULL AND m.fecha_hora_fin IS NULL",
            'schema_version':"SELECT version FROM hospital_schema_version",
        }.items():
            # Roll back a failed read before classifying it; the runtime may
            # deliberately lack permission on technical version tables.
            def read(statement):
                with c.transaction():return c.execute(statement).fetchall()
            result[label]=observe(lambda q=query:read(q))
        return result


def mysql():
    import mysql.connector
    c=mysql.connector.connect(host=os.getenv('MYSQL_HOST','mysql'),port=int(os.getenv('MYSQL_PORT','3306')),
                              database=os.getenv('MYSQL_DB','pediatrico'),user=os.environ['MYSQL_USER'],password=os.environ['MYSQL_PASSWORD'],connection_timeout=5)
    try:
        c.start_transaction(readonly=True)
        with c.cursor() as u:
            u.execute('SET SESSION MAX_EXECUTION_TIME=10000')
            u.execute("SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema=DATABASE() AND column_name='activo_operativo' ORDER BY table_name")
            result={'provider':'mysql','operations_flags':[dict(zip(['table','column','type','nullable'],r)) for r in u.fetchall()]}
            def query(statement):u.execute(statement);return u.fetchall()
            for label,statement in {'patients':'SELECT COUNT(*) FROM paciente','enabled_professionals':"SELECT COUNT(*) FROM medico WHERE estado='activo'",'schema_version':'SELECT version FROM pediatria_schema_version'}.items():
                result[label]=observe(lambda q=statement:query(q))
            return result
    finally:c.rollback();c.close()


def mongo():
    from pymongo import MongoClient
    with MongoClient(os.environ['MONGO_URI'],serverSelectionTimeoutMS=5000,socketTimeoutMS=10000) as client:
        database=client.get_default_database();names=sorted(database.list_collection_names())
        result={'provider':'mongodb','collections':names,'replica_set':bool(client.admin.command('hello').get('setName'))}
        for name in ['clinico_pacientes','clinico_consultas','clinico_resultados','clinico_profesionales_operativos']:
            result[name]=observe(lambda n=name:database[n].count_documents({'schema_version':2,'institucion':'laboratorio'},maxTimeMS=10000))
        result['enabled_professionals']=database.clinico_profesionales_operativos.count_documents({'schema_version':2,'institucion':'laboratorio','activo':True,'habilitado':True},maxTimeMS=10000)
        return result


def firestore():
    # This application currently supports the explicitly configured emulator.
    # Refuse implicit cloud credentials or an accidental production connection.
    if not os.getenv('FIRESTORE_EMULATOR_HOST'):raise RuntimeError('Explicit emulator is required')
    from google.cloud import firestore as sdk
    from google.auth.credentials import AnonymousCredentials
    from google.cloud.firestore_v1.base_query import FieldFilter
    client=sdk.Client(project=os.getenv('FIREBASE_PROJECT_ID','demo-historiales'),credentials=AnonymousCredentials())
    try:
        result={'provider':'firestore-emulator','collections':sorted(c.id for c in client.collections(timeout=10))}
        for name in ['pacientes','consultas','procedimientos','profesionales_operativos']:
            query=client.collection(name).where(filter=FieldFilter('schema_version','==',2)).where(filter=FieldFilter('institucion','==','odontologica'))
            rows=[snapshot.to_dict() for snapshot in query.select(['activo','habilitado']).stream(timeout=10)]
            result[name]=len(rows)
            if name=='profesionales_operativos':result['enabled_professionals']=sum(r.get('activo') is True and r.get('habilitado') is True for r in rows)
        return result
    finally:client.close()


def collect():
    report={'inventory_version':2,'purpose':'AUC-12 desktop installation inventory; not an upgrade or acceptance certificate',
            'read_only':True,'contains_patient_records_or_credentials':False,
            'identity':observe(identity),'hospital':observe(postgres),'pediatrico':observe(mysql),
            'laboratorio':observe(mongo),'odontologica':observe(firestore)}
    report['installed_code']={}
    for file in ['apps/operaciones/resources.json','apps/operaciones/accounts.py','config/urls.py']:
        path=Path(file)
        report['installed_code'][file]=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return report


if __name__=='__main__':print(json.dumps(collect(),sort_keys=True,indent=2))
