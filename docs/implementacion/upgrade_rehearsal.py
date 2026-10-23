"""AUC-12 rehearsal on generated copies only; called by the disposable runner.

Does not accept shared destinations. Returns restored destinations for HTTP tests.
Backups stay private in the runner directory and are not application artifacts.
"""
import hashlib
import json
import os
from pathlib import Path
import uuid


def digest(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,default=str,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def rehearse(root,work,docker,pg,my,password,env):
    from unittest.mock import patch
    if env.get('FIRESTORE_EMULATOR_HOST') != '127.0.0.1:8099':
        raise RuntimeError('Rehearsal requires the owned local Firestore emulator')
    with patch.dict(os.environ,env):
        return _rehearse(root,work,docker,pg,my,password,env)


def _rehearse(root,work,docker,pg,my,password,env):
    import psycopg
    from psycopg import sql
    import mysql.connector
    from pymongo import MongoClient
    from bson import json_util
    from google.cloud import firestore
    from google.auth.credentials import AnonymousCredentials
    from apps.historiales.testing.mysql import execute_script
    from apps.historiales.domain.context import ContextoClinico
    from apps.operaciones.repository import OperationsRepository
    suffix=uuid.uuid4().hex[:12]
    report={'scope':'populated synthetic copies; no shared installation accessed','engines':{}}
    destinations={}

    def private(name,content):
        path=work/name;path.write_text(content);path.chmod(0o600)
        return path

    def pg_connect(database,**kwargs):
        return psycopg.connect(host='127.0.0.1',port=15436,dbname=database,user='postgres',password=password,**kwargs)
    def pg_rows(c):
        tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
        result={}
        for table in tables:
            cursor=c.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table)))
            names=[d.name for d in cursor.description]
            result[table]=sorted((dict(zip(names,row)) for row in cursor.fetchall()),key=lambda row:json.dumps(row,sort_keys=True,default=str))
            for row in result[table]:row.pop('activo_operativo',None)
        return result
    pg_flags=['especialidad','enfermero','pabellon_edificio','habitacion','cama','quirofano','medicamento']
    pg_copy='hospital_restore_'+suffix
    dump=docker('exec',pg,'pg_dump','-U','postgres','--no-owner','--no-privileges','hospital')
    with pg_connect('postgres',autocommit=True) as c:c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(pg_copy)))
    docker('exec','-i',pg,'psql','-U','postgres','--dbname',pg_copy,'--set','ON_ERROR_STOP=1',input=dump)
    with pg_connect(pg_copy) as c:
        for table in pg_flags:c.execute(sql.SQL('ALTER TABLE {} DROP COLUMN activo_operativo').format(sql.Identifier(table)))
        before=digest(pg_rows(c))
    # Back up the populated pre-operations copy, then prove restoration before upgrade.
    backup=private('hospital-pre-operations.sql',docker('exec',pg,'pg_dump','-U','postgres','--no-owner','--no-privileges',pg_copy))
    with pg_connect('postgres',autocommit=True) as c:
        c.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(pg_copy)))
        c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(pg_copy)))
    docker('exec','-i',pg,'psql','-U','postgres','--dbname',pg_copy,'--set','ON_ERROR_STOP=1',input=backup.read_text())
    with pg_connect(pg_copy) as c:
        assert digest(pg_rows(c))==before
        for _ in range(2):
            c.execute((root/'db/postgres/operations_upgrade.sql').read_text())
            c.execute('GRANT USAGE ON SCHEMA public TO hospital_runtime')
            c.execute((root/'db/postgres/operations_runtime.sql').read_text())
        assert digest(pg_rows(c))==before
        c.execute('UPDATE especialidad SET activo_operativo=FALSE WHERE id_especialidad=(SELECT MIN(id_especialidad) FROM especialidad)')
        c.execute((root/'db/postgres/operations_upgrade.sql').read_text())
        assert c.execute('SELECT activo_operativo FROM especialidad ORDER BY id_especialidad LIMIT 1').fetchone()[0] is False
        c.execute('UPDATE especialidad SET activo_operativo=TRUE WHERE id_especialidad=(SELECT MIN(id_especialidad) FROM especialidad)')
    report['engines']['hospital']={'backup_restored':True,'clinical_data_sha256':before,'upgrade_repeated':True,'inactive_flag_preserved':True}
    destinations['POSTGRES_DB']=pg_copy

    def my_connect(database=None):
        return mysql.connector.connect(host='127.0.0.1',port=13307,user='root',password=password,**({'database':database} if database else {}))
    def my_rows(c):
        with c.cursor(dictionary=True) as u:
            u.execute('SHOW TABLES');tables=sorted(next(iter(row.values())) for row in u.fetchall())
            result={}
            for table in tables:
                # Table names are returned by the private server, never HTTP input.
                assert table.replace('_','').isalnum()
                u.execute('SELECT * FROM `'+table+'`')
                rows=u.fetchall()
                for row in rows:row.pop('activo_operativo',None)
                result[table]=sorted(rows,key=lambda row:json.dumps(row,sort_keys=True,default=str))
            return result
    my_copy='pediatrico_restore_'+suffix
    dump=docker('exec','-e','MYSQL_PWD='+password,my,'mysqldump','-uroot','--no-tablespaces','--skip-lock-tables','--set-gtid-purged=OFF','pediatrico')
    with my_connect() as c:
        with c.cursor() as u:u.execute('CREATE DATABASE `'+my_copy+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin')
    with my_connect(my_copy) as c:
        execute_script(c,dump)
        with c.cursor() as u:
            for table in ['especialidad','tutor','vacuna','tipo_examen']:u.execute('ALTER TABLE '+table+' DROP COLUMN activo_operativo')
        c.commit();before=digest(my_rows(c))
    backup=private('pediatrico-pre-operations.sql',docker('exec','-e','MYSQL_PWD='+password,my,'mysqldump','-uroot','--no-tablespaces','--skip-lock-tables','--set-gtid-purged=OFF',my_copy))
    with my_connect() as c:
        with c.cursor() as u:
            u.execute('DROP DATABASE `'+my_copy+'`');u.execute('CREATE DATABASE `'+my_copy+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin')
    with my_connect(my_copy) as c:
        execute_script(c,backup.read_text());assert digest(my_rows(c))==before
        for _ in range(2):
            execute_script(c,(root/'db/mysql/operations_upgrade.sql').read_text())
            execute_script(c,(root/'db/mysql/operations_runtime.sql').read_text().replace('pediatrico.',my_copy+'.'))
        with c.cursor() as u:
            u.execute("GRANT SELECT ON "+my_copy+".pediatria_schema_version TO 'pediatria_runtime'@'%'")
            u.execute('UPDATE especialidad SET activo_operativo=FALSE WHERE id=(SELECT n FROM (SELECT MIN(id) n FROM especialidad) s)')
        c.commit();assert digest(my_rows(c))==before
        execute_script(c,(root/'db/mysql/operations_upgrade.sql').read_text())
        with c.cursor() as u:
            u.execute('SELECT activo_operativo FROM especialidad ORDER BY id LIMIT 1');assert u.fetchone()[0]==0
            u.execute('UPDATE especialidad SET activo_operativo=TRUE WHERE id=(SELECT n FROM (SELECT MIN(id) n FROM especialidad) s)')
        c.commit()
    report['engines']['pediatrico']={'backup_restored':True,'clinical_data_sha256':before,'upgrade_repeated':True,'inactive_flag_preserved':True}
    destinations['MYSQL_DB']=my_copy

    with MongoClient(env['MONGO_URI']) as client:
        source=client.get_default_database();target=client['auc12_restore_'+suffix]
        assert not target.list_collection_names()
        payload=[]
        for name in sorted(source.list_collection_names()):
            collection=source[name]
            payload.append({'name':name,'options':collection.options(),'indexes':list(collection.list_indexes()),'documents':list(collection.find())})
        backup=private('mongo-backup.json',json_util.dumps(payload))
        for item in json_util.loads(backup.read_text()):
            collection=target.create_collection(item['name'],**item['options'])
            if item['documents']:collection.insert_many(item['documents'])
            for index in item['indexes']:
                if index['name']=='_id_':continue
                options={k:v for k,v in index.items() if k not in {'key','v','ns'}}
                collection.create_index(list(index['key'].items()),**options)
        before=digest([(item['name'],sorted(item['documents'],key=lambda d:str(d['_id']))) for item in payload])
        restored=digest([(name,sorted(list(target[name].find()),key=lambda d:str(d['_id']))) for name in sorted(target.list_collection_names())])
        assert before==restored
        from operations_schema import prepare
        prepare(target);prepare(target)
        assert before==digest([(name,sorted(list(target[name].find()),key=lambda d:str(d['_id']))) for name in sorted(target.list_collection_names())])
        report['engines']['laboratorio']={'backup_restored':True,'documents_sha256':before,'validators_indexes_restored':True,'provisioning_repeated':True}
        destinations['MONGO_URI']=env['MONGO_URI'].replace('/operaciones?','/'+target.name+'?')

    # Native Firestore Value protobufs preserve timestamps, references and numbers.
    from google.cloud.firestore_v1 import _helpers
    from google.cloud.firestore_v1.types import document
    source=firestore.Client(project=env['FIREBASE_PROJECT_ID'],credentials=AnonymousCredentials())
    target=firestore.Client(project='demo-auc12-'+suffix,credentials=AnonymousCredentials())
    try:
        payload=[]
        for collection in sorted(source.collections(),key=lambda c:c.id):
            for snapshot in collection.stream():
                value=document.Value(map_value=document.MapValue(fields=_helpers.encode_dict(snapshot.to_dict())))
                payload.append({'collection':collection.id,'id':snapshot.id,'value':document.Value.to_json(value)})
        backup=private('firestore-backup.json',json.dumps(payload))
        assert not list(target.collections())
        for item in json.loads(backup.read_text()):
            value=document.Value.from_json(item['value'])
            target.collection(item['collection']).document(item['id']).set(_helpers.decode_dict(value.map_value.fields,target))
        restored=[]
        for collection in sorted(target.collections(),key=lambda c:c.id):
            for snapshot in collection.stream():
                value=document.Value(map_value=document.MapValue(fields=_helpers.encode_dict(snapshot.to_dict())))
                restored.append({'collection':collection.id,'id':snapshot.id,'value':document.Value.to_json(value)})
        def canonical(items):return sorted([(i['collection'],i['id'],json.loads(i['value'])) for i in items],key=lambda i:(i[0],i[1]))
        before=digest(canonical(payload));assert before==digest(canonical(restored))
        report['engines']['odontologica']={'backup_restored':True,'documents_sha256':before,'native_value_types_preserved':True}
        destinations['FIREBASE_PROJECT_ID']=target.project
    finally:source.close();target.close()

    # Actual restricted runtime credentials must read every restored resource.
    previous={key:os.environ.get(key) for key in env}
    try:
        os.environ.update(env|destinations)
        for institution in ['hospital','pediatrico','laboratorio','odontologica']:
            repo=OperationsRepository(ContextoClinico(institution,'restore-probe','admin','1'))
            for name in repo.specs:repo.page(name)
            report['engines'][institution]['runtime_all_resources_readable']=True
        # Assert privileges without granting or exercising destructive operations.
        with psycopg.connect(host='127.0.0.1',port=15436,dbname=pg_copy,user='hospital_runtime',password=password) as c:
            assert c.execute("SELECT has_table_privilege(current_user,'paciente','SELECT'),has_table_privilege(current_user,'paciente','DELETE'),has_schema_privilege(current_user,'public','CREATE')").fetchone()==(True,False,False)
        with mysql.connector.connect(host='127.0.0.1',port=13307,database=my_copy,user='pediatria_runtime',password=password) as c:
            with c.cursor() as u:
                u.execute('SHOW GRANTS');grants=' '.join(row[0] for row in u.fetchall()).upper()
                assert 'DELETE' not in grants and 'CREATE' not in grants and 'DROP' not in grants
        report['restricted_runtime_verified']=True
    finally:
        for key,value in previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        for key in destinations:
            if key not in previous:os.environ.pop(key,None)
    (work/'upgrade-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('OK AUC-12: populated copies restored, upgrades repeated, data and runtime grants verified (four engines)')
    return destinations
