"""Regression coverage for AUC-01..04; native cases run only in fresh runner databases."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest import skipUnless
from unittest.mock import patch

from django.test import SimpleTestCase
from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import AccesoDenegado, Conflicto, DatosInvalidos, RecursoNoEncontrado
from apps.historiales.infrastructure.adapters.postgres_clinical import PostgreSQLClinical
from apps.operaciones.catalog import RESOURCES, resource
from apps.operaciones.repository import OperationsRepository


class RuleCursor:
    def __init__(self, occupied=()):self.occupied=list(occupied);self.statements=[]
    def execute(self,query,args=()):self.statements.append(query)
    def fetchall(self):return self.occupied
    def fetchone(self):return {'n':0}


class BlockerRulesTests(SimpleTestCase):
    def repo(self,institution):
        r=object.__new__(OperationsRepository);r.context=ContextoClinico(institution,'audit','admin','1')
        r.specs=RESOURCES[institution];r.sql=True;r.hospital=institution=='hospital';return r

    def test_occupied_bed_rejects_with_domain_conflict(self):
        r=self.repo('hospital')
        with self.assertRaises(Conflicto):
            r._rules(RuleCursor([{'id_ingreso':9}]),'movimiento_cama',
                     {'id_cama':2,'fecha_hora_inicio':'2020-01-01T13:00:00Z'},
                     {'id_ingreso':{'alta_utc':None,'id_cama':1,'fecha_hora_ingreso':datetime(2020,1,1,12)}},None)

    def test_discharge_closes_bed_movement_in_same_unit(self):
        r=object.__new__(PostgreSQLClinical);r.contexto=ContextoClinico('hospital','audit','admin','1')
        admission={'id_paciente':1,'ingreso_utc':datetime(2020,1,1,tzinfo=timezone.utc),'alta_utc':None}
        class Cursor(RuleCursor):
            def fetchone(self):
                return {'id_paciente':1} if self.statements[-1].startswith('SELECT id_paciente') else admission
            def fetchall(self):return [{'id_movimiento':1,'fecha_hora_inicio':datetime(2020,1,1)}]
        cursor=Cursor()
        @contextmanager
        def session(**kwargs):yield cursor
        r._session=session;r._lock_patient=lambda *args:None;r._professional=lambda *args:1;r._admission_dto=lambda row:{'id':'H-I-1'}
        r.dar_alta('H-I-1','2020-01-02T12:00:00Z')
        self.assertTrue(any(q.startswith('UPDATE movimiento_cama') for q in cursor.statements))

    def test_hospital_prescription_has_accessible_create_task(self):
        self.assertTrue(resource(ContextoClinico('hospital','audit','medico','1'),'receta_prescripcion',write=True)['create'])
        with self.assertRaises(AccesoDenegado):resource(ContextoClinico('hospital','audit','enfermero'),'receta_prescripcion',write=True)

    def test_claim_rejects_authorization_for_another_consultation(self):
        r=self.repo('pediatrico')
        with self.assertRaises(DatosInvalidos):
            r._rules(RuleCursor(),'reclamacion_seguro',{'monto_reclamado':'5.00','poliza_paciente_id':1},
                     {'factura_id':{'id':1,'total_seguro':'5.00','consulta_id':10,'estado':'pendiente'},
                      'autorizacion_id':{'id':2,'poliza_paciente_id':1,'estado':'aprobado','monto_autorizado':'5.00','consulta_id':20}},None)


@skipUnless(os.getenv('OPERATIONS_REAL_TESTS')=='1','requires fresh, dedicated hospital_auc/pediatrico_auc databases')
class NativeBlockerTests(SimpleTestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{'POSTGRES_DB':'hospital_auc','MYSQL_DB':'pediatrico_auc'})
        self.environment.start();self.addCleanup(self.environment.stop)
        self.tag='AUC-'+uuid.uuid4().hex[:8]

    def hospital(self):
        r=OperationsRepository(ContextoClinico('hospital','audit','admin','1'))
        e=r.save('especialidad',{'nombre':self.tag,'nivel_complejidad':1})['id']
        doctor=r.save('medico',{'id_especialidad':e,'nombre_completo':self.tag,'colegiado':self.tag,'habilitado':True})['id']
        r=OperationsRepository(ContextoClinico('hospital','audit','admin',str(r.internal('medico',doctor))))
        pavilion=r.save('pabellon_edificio',{'nombre_pabellon':self.tag})['id']
        room=r.save('habitacion',{'id_pabellon':pavilion,'numero_habitacion':self.tag})['id']
        beds=[r.save('cama',{'id_habitacion':room,'codigo_cama':self.tag+str(i),'estado_limpieza':'limpia'})['id'] for i in range(3)]
        patients=[r.core.registrar_paciente({'identificacion':self.tag+str(i),'nombres':'DEMO','apellidos':'Auditoría','fecha_nacimiento':'2000-01-01'})['id'] for i in range(2)]
        admissions=[r.core.ingresar_paciente(p,{'cama_id':beds[i],'fecha_hora_ingreso':'2020-01-01T12:00:00Z','tipo_ingreso':'DEMO'})['id'] for i,p in enumerate(patients)]
        return r,beds,patients,admissions

    def movement(self,r,admission,bed):return r.save('movimiento_cama',{'id_ingreso':admission,'id_cama':bed,'fecha_hora_inicio':'2020-01-01T13:00:00Z','motivo_traslado':'DEMO'})

    def test_occupied_bed_and_two_transfers_competing_for_one_bed(self):
        r,beds,patients,admissions=self.hospital()
        with self.assertRaises(Conflicto):self.movement(r,admissions[0],beds[1])
        def move(admission):
            actor=OperationsRepository(r.context)
            try:self.movement(actor,admission,beds[2]);return 'saved'
            except Conflicto:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(move,admissions))
        self.assertEqual(sorted(results),['conflict','saved'])
        all_rows=[r.core.listar_ingresos(p)['ingresos'][0] for p in patients]
        self.assertEqual(sum(row['cama_id']==beds[2] for row in all_rows),1)
        for i,p in enumerate(patients):
            rows=r.page('movimiento_cama',patient=p)['results']
            self.assertEqual(len(rows),2 if all_rows[i]['cama_id']==beds[2] else 0)

    def test_discharge_closes_movement_rejects_bad_time_and_rolls_back(self):
        r,beds,patients,admissions=self.hospital();self.movement(r,admissions[0],beds[2])
        with self.assertRaises(DatosInvalidos):r.core.dar_alta(admissions[0],'2020-01-01T12:30:00Z')
        with patch.object(r.core,'_after_write',side_effect=RuntimeError('test rollback')):
            with self.assertRaises(RuntimeError):r.core.dar_alta(admissions[0],'2020-01-02T12:00:00Z')
        self.assertIsNone(r.core.listar_ingresos(patients[0])['ingresos'][0]['fecha_hora_alta'])
        self.assertEqual(sum(row['values']['fecha_hora_fin'] is None for row in r.page('movimiento_cama',patient=patients[0])['results']),1)
        r.core.dar_alta(admissions[0],'2020-01-02T12:00:00Z')
        closed=r.page('movimiento_cama',patient=patients[0])['results']
        self.assertTrue(all(row['values']['fecha_hora_fin'] for row in closed))
        r.core.dar_alta(admissions[0],'2020-01-02T12:00:00Z')
        self.assertEqual(closed,r.page('movimiento_cama',patient=patients[0])['results'])
        with self.assertRaises(Conflicto):r.core.dar_alta(admissions[0],'2020-01-03T12:00:00Z')

    def test_inpatient_treatment_prescription_dispatch_and_patient_scope(self):
        r,beds,patients,admissions=self.hospital()
        diagnosis=r.save('diagnostico_ingreso',{'id_ingreso':admissions[0],'codigo_cie10':'DEMO','descripcion':'DEMO ingreso'})['id']
        treatment=r.core.registrar_tratamiento(diagnosis,{'indicaciones_generales':'DEMO ingreso'})['id']
        medicine=r.save('medicamento',{'nombre_comercial':self.tag,'principio_activo':'DEMO','stock_farmacia':5})['id']
        prescription=r.save('receta_prescripcion',{'id_tratamiento':treatment,'id_medicamento':medicine,'dosis':'DEMO','frecuencia':'DEMO'})['id']
        dispatch=r.save('despacho_farmacia',{'id_receta':prescription,'cantidad_entregada':2})['id']
        self.assertTrue(dispatch)
        self.assertTrue(any(row['id']==prescription for row in r.page('receta_prescripcion',patient=patients[0])['results']))
        self.assertFalse(r.page('receta_prescripcion',patient=patients[1])['results'])
        row=r._run(lambda u:r._get(u,'medicamento',r.internal('medicamento',medicine)),read=True)
        self.assertEqual(row['stock_farmacia'],3)
        r.core.dar_alta(admissions[0],'2020-01-02T12:00:00Z')
        with self.assertRaises(RecursoNoEncontrado):r.core.registrar_receta(treatment,{'medicamento_id':medicine,'dosis':'DEMO','frecuencia':'DEMO'})

    def pediatrics(self):
        r=OperationsRepository(ContextoClinico('pediatrico','audit','admin','1'))
        e=r.save('especialidad',{'nombre':self.tag})['id']
        doctor=r.save('medico',{'nombre':'DEMO','apellido':self.tag,'colegiado':self.tag,'especialidad_id':e,'estado':'activo'})['id']
        r=OperationsRepository(ContextoClinico('pediatrico','audit','admin',str(r.internal('medico',doctor))))
        patient=r.core.registrar_paciente({'identificacion':self.tag,'nombres':'DEMO','apellidos':'Auditoría','fecha_nacimiento':'2000-01-01'})['id']
        consultations=[r.core.registrar_consulta(patient,{'fecha':'2020-01-01','notas_evolucion':'DEMO'})['id'] for _ in range(2)]
        insurer=r.save('aseguradora',{'nombre':self.tag,'estado':'activo'})['id']
        plan=r.save('plan_seguro',{'aseguradora_id':insurer,'nombre':self.tag,'estado':'activo'})['id']
        policy=r.save('poliza_paciente',{'paciente_id':patient,'plan_seguro_id':plan,'numero_poliza':self.tag,'estado':'activo'})['id']
        service=r.save('servicio_medico',{'codigo':self.tag,'nombre':self.tag,'precio_base':'10.00','estado':'activo'})['id']
        invoices=[]
        for c in consultations:
            bill=r.save('factura',{'paciente_id':patient,'consulta_id':c})['id']
            r.save('detalle_factura',{'factura_id':bill,'servicio_id':service,'cantidad':1,'precio_unitario':'10.00','monto_cubierto':'10.00'})
            current=next(row for row in r.page('factura')['results'] if row['id']==bill)
            r.financial_action('factura',bill,'emitir',current['version'])
            invoices.append(bill)
        auth=r.save('autorizacion_seguro',{'poliza_paciente_id':policy,'consulta_id':consultations[0],'numero_autorizacion':self.tag,'monto_autorizado':'10.00','estado':'aprobado'})['id']
        return r,policy,auth,invoices

    def test_claim_consultation_aggregate_concurrency_and_update_exclusion(self):
        r,policy,auth,bills=self.pediatrics()
        def claim(repo,bill,amount):return repo.save('reclamacion_seguro',{'factura_id':bill,'poliza_paciente_id':policy,'autorizacion_id':auth,'numero_reclamo':uuid.uuid4().hex,'monto_reclamado':amount,'estado':'pendiente'})
        with self.assertRaises(DatosInvalidos):claim(r,bills[1],'5.00')
        def compete(_):
            actor=OperationsRepository(r.context)
            try:claim(actor,bills[0],'6.00');return 'saved'
            except DatosInvalidos:return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(compete,range(2)))
        self.assertEqual(sorted(results),['rejected','saved'])
        claim(r,bills[0],'4.00')
        rows=[row for row in r.page('reclamacion_seguro',limit=100)['results'] if row['values']['factura_id']==bills[0]]
        self.assertEqual(sum(float(row['values']['monto_reclamado']) for row in rows),10)
        current=rows[0]
        r.save('reclamacion_seguro',{'estado':'aprobado','monto_aprobado':current['values']['monto_reclamado']},identifier=current['id'],version=current['version'])
        with self.assertRaises(DatosInvalidos):claim(r,bills[0],'1.00')

        # A second invoice for the same consultation has its own balance, but
        # must share the authorization's remaining reservation across invoices.
        invoice=r._run(lambda u:r._get(u,'factura',r.internal('factura',bills[0])),read=True)
        patient=r.public_id('paciente',invoice['paciente_id'])
        consultation=r.public_id('consulta',invoice['consulta_id'])
        second=r.save('factura',{'paciente_id':patient,'consulta_id':consultation})['id']
        service=r.save('servicio_medico',{'codigo':self.tag+'-2','nombre':self.tag+'-2','precio_base':'10.00','estado':'activo'})['id']
        r.save('detalle_factura',{'factura_id':second,'servicio_id':service,'cantidad':1,'precio_unitario':'10.00','monto_cubierto':'10.00'})
        current_bill=next(row for row in r.page('factura')['results'] if row['id']==second)
        r.financial_action('factura',second,'emitir',current_bill['version'])
        with self.assertRaises(DatosInvalidos):claim(r,second,'1.00')
        remaining=next(row for row in rows if row['id']!=current['id'])
        r.save('reclamacion_seguro',{'estado':'rechazado'},identifier=remaining['id'],version=remaining['version'])
        self.assertTrue(claim(r,second,'1.00')['id'])
