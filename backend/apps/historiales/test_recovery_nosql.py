"""Opt-in cold recovery of actual A3/A4 writes and specialties, using native artifacts."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

ENABLED = os.environ.get('RECOVERY_NOSQL_TESTS') == '1'
ROOT = Path(__file__).resolve().parents[3]


def module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


if ENABLED:
    from datetime import datetime, timezone
    from bson import ObjectId, Binary
    from google.cloud import firestore
    from google.auth.credentials import AnonymousCredentials
    from google.api_core.datetime_helpers import DatetimeWithNanoseconds
    from pymongo import MongoClient
    from apps.historiales.domain.context import ContextoClinico
    from apps.historiales.domain.errors import Conflicto
    from apps.historiales.infrastructure.adapters.mongo_adapter import MongoAdapter
    from apps.historiales.infrastructure.adapters.firestore_adapter import FirestoreAdapter
    mongo=module('mongo_recovery',ROOT/'db/mongo/clinical_recovery.py')
    firebase=module('firestore_recovery',ROOT/'db/firebase/clinical_recovery.py')
    schema=module('mongo_schema',ROOT/'db/mongo/clinical_schema.py')
    specialty_schema=module('mongo_specialty_schema',ROOT/'db/mongo/specialty_schema.py')


def fill(repo):
    expected={};specialties={}
    for number in range(2):
        p=repo.registrar_paciente({'identificacion':f'DEMO-REC-{number}','nombres':'Persona sintética','apellidos':'Recuperación','fecha_nacimiento':'2000-02-29'})
        c=repo.registrar_consulta(p['id'],{'fecha':'2020-02-29','notas_evolucion':'Texto DEMO\nUTF-8: Á ñ 🧪'})
        d=repo.registrar_diagnostico(c['id'],{'codigo_cie10':'DEMO','descripcion':'Ocurrencia independiente'})
        t=repo.registrar_tratamiento(d['id'],{'indicaciones_generales':'DEMO no administrar'})
        repo.registrar_receta(t['id'],{'medicamento_id':'DEMO-REC-M','dosis':'DEMO','frecuencia':'DEMO'})
        if repo.institution == 'laboratorio':
            repo.registrar_resultado(p['id'], {'tipo_examen':'DEMO-REC-EXAM','fecha':'2020-02-29T12:00:00.123Z','estado':'finalizado',
                'campos':[{'nombre':'Número','valor':3.5,'unidad':'DEMO'},{'nombre':'Texto','valor':'DEMO 🧪'},{'nombre':'Booleano','valor':False}]})
            specialties[p['id']]=repo.listar_resultados(p['id'])
        else:
            repo.registrar_procedimiento(p['id'], {'tratamiento_id':t['id'],'pieza':'16','descripcion':'DEMO procedimiento recuperable','estado':'realizado'})
            specialties[p['id']]=repo.listar_procedimientos(p['id'])
        if number:repo.archivar_paciente(p['id'],'DEMO archivo antes de respaldo')
        expected[p['id']]=repo.obtener_historial(p['id'])
    return expected,specialties


def check_restored(test,repo,expected,specialties):
    for key,history in expected.items():test.assertEqual(repo.obtener_historial(key),history)
    read = repo.listar_resultados if repo.institution == 'laboratorio' else repo.listar_procedimientos
    for key,rows in specialties.items():test.assertEqual(read(key),rows)
    active=next(h['paciente'] for h in expected.values() if h['paciente']['estado']=='activo')
    archived=next(h['paciente'] for h in expected.values() if h['paciente']['estado']=='archivado')
    with test.assertRaises(Conflicto):
        repo.registrar_paciente({k:active[k] for k in ('identificacion','nombres','apellidos','fecha_nacimiento')})
    test.assertEqual(repo.archivar_paciente(archived['id'],archived['motivo_archivo']),archived)
    with test.assertRaises(Conflicto):repo.registrar_consulta(archived['id'],{'fecha':'2020-02-29','notas_evolucion':'DEMO'})
    repo.registrar_consulta(active['id'],{'fecha':'2020-03-01','notas_evolucion':'DEMO escritura tras recuperación'})
    test.assertEqual(len(repo.obtener_historial(active['id'])['consultas']),2)
    if repo.institution == 'laboratorio':
        test.assertEqual(repo.listar_tipos_examen()['results'],[{'id':'DEMO-REC-EXAM','nombre':'DEMO examen recuperable'}])
        write=repo.registrar_resultado;key='resultados'
        names=('tipo_examen','fecha','estado','campos')
    else:
        write=repo.registrar_procedimiento;key='procedimientos'
        names=('tratamiento_id','pieza','descripcion','estado')
    payload={name:specialties[active['id']][key][0][name] for name in names}
    archived_payload={name:specialties[archived['id']][key][0][name] for name in names}
    with test.assertRaises(Conflicto):write(archived['id'],archived_payload)
    test.assertEqual(read(archived['id']),specialties[archived['id']])
    write(active['id'],payload)
    test.assertEqual(len(read(active['id'])[key]),2)


@unittest.skipUnless(ENABLED,'Recuperación requiere servidores locales dedicados y activación explícita')
class MongoRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name in ('jennifer-recovery-mongo','jennifer-recovery-target'):
            data=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
            if data['Config']['Labels'].get('codex.task')!='jennifer-recovery' or not data['State']['Running']:
                raise RuntimeError('Solo contenedores de recuperación dedicados y activos')
        cls.temp=tempfile.TemporaryDirectory(dir='/workspace/work/recovery')
        cls.directory=Path(cls.temp.name)
        cls.source='recovery_source_'+uuid4().hex
        cls.target='lab_recovery_'+uuid4().hex
        cls.source_uri=f'mongodb://127.0.0.1:27039/{cls.source}?replicaSet=recovery'
        cls.target_uri=f'mongodb://127.0.0.1:27049/{cls.target}?replicaSet=recoveryTarget'
        cls.dump=Path(os.environ['MONGO_DUMP_BIN']);cls.restore_bin=Path(os.environ['MONGO_RESTORE_BIN'])
        with MongoClient(cls.source_uri,serverSelectionTimeoutMS=3000) as client:
            db=client.get_default_database();schema.prepare(db);specialty_schema.prepare(db)
            db.clinico_tipos_examen.insert_one({'_id':'DEMO-REC-EXAM','nombre':'DEMO examen recuperable','schema_version':2,'institucion':'laboratorio'})
            db.clinico_medicamentos.insert_one({'_id':'DEMO-REC-M','nombre':'DEMO no administrar','presentacion':None,'schema_version':2,'institucion':'laboratorio'})
            db.legacy_pacientes.insert_one({'_id':ObjectId(),'nombres':'DEMO heredado','apellidos':'Recuperación','fecha':datetime(2001,2,3,tzinfo=timezone.utc),'binario':Binary(b'\x00\xff')})
            db.legacy_pacientes.create_index([('apellidos',1),('nombres',-1)])
        with patch.dict(os.environ,{'MONGO_URI':cls.source_uri}):
            cls.expected,cls.specialties=fill(MongoAdapter(contexto=ContextoClinico('laboratorio','DEMO-U','admin','1')))
        cls.backup=cls.directory/'backup'
        cls.manifest=mongo.backup(cls.source_uri,cls.backup,writers_stopped=True,mongodump=cls.dump)

    @classmethod
    def tearDownClass(cls):
        # Containers are dedicated and removed by the runbook; no shared DB drops.
        cls.temp.cleanup()

    def test_archive_hash_and_private_permissions(self):
        manifest,_=mongo.read_backup(self.backup)
        self.assertEqual(manifest,self.manifest)
        self.assertEqual(self.backup.stat().st_mode & 0o777,0o700)
        self.assertEqual((self.backup/'manifest.json').stat().st_mode & 0o777,0o600)
        self.assertIn('legacy_pacientes',manifest['collections'])
        self.assertTrue(manifest['collections']['clinico_pacientes']['indexes']['institucion_1_identificacion_1']['unique'])
        self.assertTrue(manifest['collections']['clinico_tipos_examen']['indexes']['institucion_1_nombre_1']['unique'])
        self.assertIn('clinico_resultados',manifest['collections'])

    def test_backup_requires_stopped_writers_and_new_external_directory(self):
        with self.assertRaises(ValueError):mongo.backup(self.source_uri,self.directory/'no-pause',mongodump=self.dump)
        with self.assertRaises(ValueError):mongo.backup(self.source_uri,self.backup,writers_stopped=True,mongodump=self.dump)
        with self.assertRaises(ValueError):mongo.backup(self.source_uri,ROOT/'db/mongo/forbidden-backup',writers_stopped=True,mongodump=self.dump)

    def test_corruption_is_rejected_before_restore(self):
        bad=self.directory/'bad';shutil.copytree(self.backup,bad)
        with (bad/'database.archive.gz').open('ab') as target:target.write(b'corrupted')
        with self.assertRaises(ValueError):mongo.restore(self.target_uri,bad,mongorestore=self.restore_bin)
        with MongoClient(self.target_uri) as client:self.assertEqual(client.get_default_database().list_collection_names(),[])

    def test_populated_target_is_never_overwritten(self):
        name='occupied_recovery_'+uuid4().hex
        uri=f'mongodb://127.0.0.1:27049/{name}?replicaSet=recoveryTarget'
        with MongoClient(uri) as client:client.get_default_database().sentinel.insert_one({'_id':'DEMO','value':'conservar'})
        with self.assertRaises(ValueError):mongo.restore(uri,self.backup,mongorestore=self.restore_bin)
        with MongoClient(uri) as client:self.assertEqual(client.get_default_database().sentinel.find_one({'_id':'DEMO'})['value'],'conservar')
        with self.assertRaises(ValueError):mongo.restore(self.source_uri,self.backup,mongorestore=self.restore_bin)

    def test_z_cold_restore_on_another_server_without_seed(self):
        data=json.loads(subprocess.check_output(['docker','inspect','jennifer-recovery-mongo']))[0]
        self.assertEqual(data['Config']['Labels'].get('codex.task'),'jennifer-recovery')
        subprocess.run(['docker','stop','jennifer-recovery-mongo'],check=True,stdout=subprocess.DEVNULL)
        verified=mongo.restore(self.target_uri,self.backup,mongorestore=self.restore_bin)
        self.assertEqual(verified['verified_collections'],11)
        with patch.dict(os.environ,{'MONGO_URI':self.target_uri}):
            check_restored(self,MongoAdapter(contexto=ContextoClinico('laboratorio','DEMO-U','admin','1')),self.expected,self.specialties)
        with MongoClient(self.target_uri) as client:
            from pymongo.errors import WriteError
            with self.assertRaises(WriteError):
                client.get_default_database().clinico_pacientes.insert_one({'_id':'DEMO-malformed'})


@unittest.skipUnless(ENABLED,'Recuperación requiere emulador local dedicado y activación explícita')
class FirestoreRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source_pid=int(os.environ['FIRESTORE_RECOVERY_SOURCE_PID'])
        argv=Path(f'/proc/{source_pid}/cmdline').read_bytes().split(b'\0')
        if b'--project_id=demo-clinical-recovery' not in argv or b'--port=8093' not in argv:
            raise RuntimeError('Solo JVM de recuperación dedicada')
        cls.temp=tempfile.TemporaryDirectory(dir='/workspace/work/recovery')
        cls.directory=Path(cls.temp.name);cls.backup=cls.directory/'backup'
        cls.project='demo-clinical-recovery'
        os.environ['FIRESTORE_EMULATOR_HOST']='127.0.0.1:8093'
        os.environ['FIREBASE_PROJECT_ID']=cls.project
        client=firebase.local_client(cls.project)
        try:
            if list(client.collections()):raise RuntimeError('Emulador origen debe estar vacío')
            client.collection('medicamentos').document('DEMO-REC-M').set({'nombre':'DEMO no administrar','presentacion':None,'schema_version':2,'institucion':'odontologica'})
            client.collection('legacy').document('DEMO-typed').set({'timestamp':DatetimeWithNanoseconds.from_rfc3339('2001-02-03T04:05:06.123456789Z'),'bytes':b'\x00\xff','location':firestore.GeoPoint(14.6,-90.5),'reference':client.collection('legacy').document('DEMO-typed'),'map':{'array':[1,True,None,2.5]}})
        finally:client.close()
        cls.expected,cls.specialties=fill(FirestoreAdapter(contexto=ContextoClinico('odontologica','DEMO-U','admin','1')))
        cls.metadata=firebase.backup(cls.project,cls.backup,writers_stopped=True)
        cls.manifest,_=firebase.read_backup(cls.backup)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_artifacts_hashes_and_private_permissions(self):
        self.assertEqual(firebase.read_backup(self.backup)[0],self.manifest)
        self.assertEqual(self.backup.stat().st_mode & 0o777,0o700)
        self.assertEqual((self.backup/'manifest.json').stat().st_mode & 0o777,0o600)
        self.assertIn('legacy',self.manifest['collections'])
        self.assertIn('procedimientos',self.manifest['collections'])

    def test_backup_requires_pause_and_new_external_directory(self):
        with self.assertRaises(ValueError):firebase.backup(self.project,self.directory/'no-pause')
        with self.assertRaises(ValueError):firebase.backup(self.project,self.backup,writers_stopped=True)
        with self.assertRaises(ValueError):firebase.backup(self.project,ROOT/'db/firebase/forbidden-backup',writers_stopped=True)
        with self.assertRaises(ValueError):firebase.local_client('real-project')

    def test_corrupted_export_or_extra_file_is_rejected(self):
        bad=self.directory/'bad';shutil.copytree(self.backup,bad)
        (bad/'unexpected').write_text('DEMO')
        with self.assertRaises(ValueError):firebase.read_backup(bad)
        (bad/'unexpected').unlink()
        metadata=bad/'firestore_export/firestore_export.overall_export_metadata'
        with metadata.open('ab') as target:target.write(b'corrupt')
        with self.assertRaises(ValueError):firebase.read_backup(bad)

    def test_nested_documents_are_not_silently_omitted(self):
        client=firebase.local_client(self.project)
        ref=client.collection('legacy').document('DEMO-typed').collection('nested').document('DEMO')
        try:
            ref.set({'value':'conservar'})
            with self.assertRaises(ValueError):firebase.backup(self.project,self.directory/'nested',writers_stopped=True)
            self.assertTrue(ref.get().exists)
        finally:ref.delete();client.close()

    def test_z_cold_restore_new_jvm_without_seed(self):
        source_pid=int(os.environ['FIRESTORE_RECOVERY_SOURCE_PID'])
        argv=Path(f'/proc/{source_pid}/cmdline').read_bytes().split(b'\0')
        self.assertIn(b'--project_id=demo-clinical-recovery',argv)
        os.kill(source_pid,signal.SIGTERM)
        manifest,metadata=firebase.read_backup(self.backup)
        log=(self.directory/'restore.log').open('w')
        server=subprocess.Popen(['java','-jar',os.environ['FIRESTORE_RECOVERY_JAR'],'--host=127.0.0.1','--port=8095','--project_id='+self.project,'--import-data='+str(metadata)],stdout=log,stderr=subprocess.STDOUT)
        try:
            with patch.dict(os.environ,{'FIRESTORE_EMULATOR_HOST':'127.0.0.1:8095'}):
                for attempt in range(50):
                    if server.poll() is not None:self.fail('JVM restaurada no inició: '+(self.directory/'restore.log').read_text()[-1000:])
                    import requests
                    try:
                        response=requests.get('http://127.0.0.1:8095/',timeout=0.3)
                        if response.status_code in {200,404}:break
                    except requests.RequestException:pass
                    time.sleep(0.1)
                verified=firebase.verify_restored(self.project,self.backup)
                self.assertEqual(verified['verified_collections'],9)
                check_restored(self,FirestoreAdapter(contexto=ContextoClinico('odontologica','DEMO-U','admin','1')),self.expected,self.specialties)
        finally:
            server.terminate();server.wait(timeout=15);log.close()
