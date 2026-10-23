"""AUC-06: execute repository SQL on disposable SQLite; no native lock claims."""
import os
import sqlite3
import time
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch
from unittest import skipUnless

from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import AccesoDenegado, Conflicto, DatosInvalidos
from apps.operaciones.catalog import RESOURCES, manifest
from apps.operaciones.repository import OperationsRepository
from apps.identidad.models import PerfilInstitucional


class Cursor:
    def __init__(self,connection):
        self.cursor=connection.cursor()
        self.statements=[]

    def execute(self,query,args=()):
        self.statements.append(query)
        args=tuple(str(v) if isinstance(v,Decimal) else v.isoformat(' ') if isinstance(v,datetime) else v for v in args)
        self.cursor.execute(query.replace('%s','?').replace(' FOR UPDATE',''),args)

    @property
    def lastrowid(self):return self.cursor.lastrowid
    def fetchone(self):
        row=self.cursor.fetchone()
        return dict(row) if row is not None else None
    def fetchall(self):return [dict(row) for row in self.cursor.fetchall()]


class FinanceTests(SimpleTestCase):
    def repository(self,institution):
        connection=sqlite3.connect(':memory:')
        connection.row_factory=sqlite3.Row
        self.addCleanup(connection.close)
        r=object.__new__(OperationsRepository)
        r.context=ContextoClinico(institution,'finance-test','admin','1')
        r.specs=RESOURCES[institution];r.sql=True;r.hospital=institution=='hospital'
        r.core=Mock()
        for name in ['paciente','consulta','factura','detalle_factura','pago','metodo_pago',
                     'servicio_medico','reclamacion_seguro','poliza_paciente','autorizacion_seguro']:
            if name not in r.specs:continue
            spec=r.specs[name]
            columns=[spec['pk']+' INTEGER PRIMARY KEY AUTOINCREMENT']
            columns += [key+(' INTEGER' if field['type'] in {'integer','reference','boolean'} else ' TEXT') for key,field in spec['fields'].items() if key!=spec['pk']]
            connection.execute('CREATE TABLE '+spec['table']+' ('+','.join(columns)+')')
        patient_key='id_paciente' if r.hospital else 'paciente_id'
        connection.execute('INSERT INTO paciente ('+r.specs['paciente']['pk']+",estado) VALUES (1,'activo')")
        connection.execute('INSERT INTO consulta ('+r.specs['consulta']['pk']+','+patient_key+') VALUES (1,1)')
        if not r.hospital:
            connection.execute("INSERT INTO metodo_pago (id,nombre,estado) VALUES (1,'DEMO','activo')")
            connection.execute("INSERT INTO servicio_medico (id,nombre,precio_base,estado) VALUES (1,'DEMO','20.00','activo')")
            connection.execute("INSERT INTO poliza_paciente (id,paciente_id,estado) VALUES (1,1,'activo')")
        connection.commit()
        @contextmanager
        def session(**kwargs):
            with connection:
                r.cursor=Cursor(connection)
                yield r.cursor
        r.core._session=session
        return r

    def current(self,r,name,identifier):
        return r._run(lambda u:r.dto(name,r._get(u,name,r.internal(name,identifier))),read=True)

    def action(self,r,name,identifier,action):
        row=self.current(r,name,identifier)
        return r.financial_action(name,identifier,action,row['version'])

    def invoice(self,r,covered='0.00'):
        if r.hospital:
            bill=r.save('factura',{'id_paciente':'H-P-1','id_consulta':'H-C-1'})
            r.save('detalle_factura',{'id_factura':bill['id'],'concepto':'DEMO','cantidad':1,'precio_unitario':'20.00'})
        else:
            bill=r.save('factura',{'paciente_id':'PED-P-1','consulta_id':'PED-C-1'})
            r.save('detalle_factura',{'factura_id':bill['id'],'servicio_id':'PED-OP_servicio_medico-1','cantidad':1,'precio_unitario':'20.00','monto_cubierto':covered})
        return bill['id']

    def pay(self,r,bill,amount,payer='paciente'):
        data={'id_factura':bill,'monto':amount,'metodo_pago':'Efectivo'} if r.hospital else {
            'factura_id':bill,'monto':amount,'metodo_pago_id':'PED-OP_metodo_pago-1','tipo_pagador':payer}
        return r.save('pago',data)

    def claim(self,r,bill,amount='10.00',state='aprobado'):
        return r.save('reclamacion_seguro',{'factura_id':bill,'poliza_paciente_id':'PED-OP_poliza_paciente-1',
            'numero_reclamo':'DEMO','monto_reclamado':amount,'monto_aprobado':amount,'estado':state})

    def summary(self,r,bill):
        return r._run(lambda u:r._financial_summary(u,r._get(u,'factura',r.internal('factura',bill))),read=True)

    def test_draft_issue_partial_total_reversal_and_cancellation_in_both_institutions(self):
        for institution in ['hospital','pediatrico']:
            with self.subTest(institution=institution):
                r=self.repository(institution);bill=self.invoice(r)
                self.assertEqual(self.current(r,'factura',bill)['values']['estado'].lower(),'borrador')
                with self.assertRaises(Conflicto):self.pay(r,bill,'1.00')
                self.action(r,'factura',bill,'emitir')
                partial=self.pay(r,bill,'12.00')
                self.assertEqual(self.current(r,'factura',bill)['values']['estado'].lower(),'parcial')
                self.assertEqual(self.summary(r,bill)['saldo_paciente'],'8.00')
                total=self.pay(r,bill,'8.00')
                self.assertEqual(self.current(r,'factura',bill)['values']['estado'].lower(),'pagada')
                with self.assertRaises(DatosInvalidos):self.pay(r,bill,'0.01')
                with self.assertRaises(DatosInvalidos):self.action(r,'factura',bill,'anular')
                self.action(r,'pago',partial['id'],'revertir')
                self.assertEqual(self.current(r,'factura',bill)['values']['estado'].lower(),'parcial')
                self.assertEqual(self.summary(r,bill)['saldo_paciente'],'12.00')
                self.action(r,'pago',total['id'],'revertir')
                self.assertEqual(self.current(r,'factura',bill)['values']['estado'].lower(),'pendiente')
                self.action(r,'factura',bill,'anular')
                self.assertEqual(self.current(r,'factura',bill)['values']['estado'].lower(),'anulada')
                self.assertEqual(self.summary(r,bill)['saldo_paciente'],'0.00')
                self.assertEqual(self.current(r,'factura',bill)['values']['total'],'20.00')
                self.assertEqual(self.current(r,'pago',partial['id'])['values']['monto'],'12.00')
                with self.assertRaises(Conflicto):self.pay(r,bill,'1.00')
                with self.assertRaises(Conflicto):self.action(r,'factura',bill,'emitir')

    def test_patient_payment_does_not_settle_insurance_and_approval_is_not_cash(self):
        r=self.repository('pediatrico');bill=self.invoice(r,covered='10.00')
        self.action(r,'factura',bill,'emitir')
        self.pay(r,bill,'10.00')
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'parcial')
        with self.assertRaises(DatosInvalidos):self.pay(r,bill,'0.01')
        with self.assertRaises(DatosInvalidos):self.pay(r,bill,'1.00','aseguradora')
        claim=self.claim(r,bill)
        self.assertEqual(self.summary(r,bill)['saldo_seguro'],'10.00')
        payment=self.pay(r,bill,'10.00','aseguradora')
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'pagada')
        with self.assertRaises(DatosInvalidos):self.pay(r,bill,'0.01','aseguradora')
        with self.assertRaises(DatosInvalidos):
            r.save('reclamacion_seguro',{'estado':'anulado'},identifier=claim['id'],version=claim['version'])
        self.action(r,'pago',payment['id'],'revertir')
        r.save('reclamacion_seguro',{'estado':'anulado'},identifier=claim['id'],version=claim['version'])
        self.assertEqual(self.summary(r,bill)['saldo_seguro'],'10.00')

    def test_claim_and_insurance_payment_block_invoice_annulment(self):
        r=self.repository('pediatrico');bill=self.invoice(r,covered='20.00')
        self.action(r,'factura',bill,'emitir');claim=self.claim(r,bill,'20.00','pendiente')
        with self.assertRaises(DatosInvalidos):self.action(r,'factura',bill,'anular')
        r.save('reclamacion_seguro',{'estado':'anulado'},identifier=claim['id'],version=claim['version'])
        self.action(r,'factura',bill,'anular')
        with self.assertRaises(Conflicto):self.claim(r,bill)

    def test_cannot_add_concepts_after_issue_or_partial_payment(self):
        for institution in ['hospital','pediatrico']:
            r=self.repository(institution);bill=self.invoice(r)
            self.action(r,'factura',bill,'emitir')
            data={'id_factura':bill,'concepto':'extra','precio_unitario':'1.00'} if r.hospital else {
                'factura_id':bill,'servicio_id':'PED-OP_servicio_medico-1','precio_unitario':'1.00'}
            for pay in [False,True]:
                if pay:self.pay(r,bill,'1.00')
                with self.assertRaises(Conflicto):r.save('detalle_factura',data)
            self.assertEqual(self.current(r,'factura',bill)['values']['total'],'20.00')

    def test_cannot_issue_empty_invoice_and_can_cancel_draft(self):
        r=self.repository('hospital')
        bill=r.save('factura',{'id_paciente':'H-P-1','id_consulta':'H-C-1'})['id']
        with self.assertRaises(DatosInvalidos):self.action(r,'factura',bill,'emitir')
        self.action(r,'factura',bill,'anular')

    def test_payment_and_reversal_roll_back_with_invoice_state(self):
        for institution in ['hospital','pediatrico']:
            r=self.repository(institution);bill=self.invoice(r);self.action(r,'factura',bill,'emitir')
            with patch.object(r.core,'_after_write',side_effect=RuntimeError('rollback')):
                with self.assertRaises(RuntimeError):self.pay(r,bill,'12.00')
            self.assertEqual(self.summary(r,bill)['cobrado_paciente'],'0.00')
            payment=self.pay(r,bill,'12.00')
            with patch.object(r.core,'_after_write',side_effect=RuntimeError('rollback')):
                with self.assertRaises(RuntimeError):self.action(r,'pago',payment['id'],'revertir')
            self.assertEqual(self.summary(r,bill)['cobrado_paciente'],'12.00')
            self.assertEqual(self.current(r,'pago',payment['id'])['values']['estado'].lower(),'procesado')
            self.assertEqual(self.current(r,'factura',bill)['values']['estado'].lower(),'parcial')

    def test_versions_invalid_actions_repeat_and_role_permissions(self):
        r=self.repository('hospital');bill=self.invoice(r)
        before=self.current(r,'factura',bill)
        self.action(r,'factura',bill,'emitir')
        with self.assertRaises(Conflicto):r.financial_action('factura',bill,'anular',before['version'])
        with self.assertRaises(DatosInvalidos):r.financial_action('factura',bill,'revertir',before['version'])
        with self.assertRaises(DatosInvalidos):r.financial_action('factura',bill,['anular'],before['version'])
        payment=self.pay(r,bill,'12.00');self.action(r,'pago',payment['id'],'revertir')
        with self.assertRaises(Conflicto):self.action(r,'pago',payment['id'],'revertir')
        for role in ['medico','enfermero']:
            r.context=ContextoClinico('hospital','finance-test',role,'1')
            with self.assertRaises(AccesoDenegado):self.action(r,'factura',bill,'anular')
            if role=='medico':
                self.assertFalse(next(s for s in manifest(r.context)['resources'] if s['key']=='factura')['actions'])
        r.context=ContextoClinico('hospital','finance-test','secretaria')
        self.assertEqual(next(s for s in manifest(r.context)['resources'] if s['key']=='factura')['actions'],['emitir','anular'])
        self.action(r,'factura',bill,'anular')

    def test_annulled_payments_are_preserved_and_not_reused_as_live_balance(self):
        r=self.repository('hospital');bill=self.invoice(r);self.action(r,'factura',bill,'emitir')
        payment=self.pay(r,bill,'20.00');self.action(r,'pago',payment['id'],'revertir')
        self.pay(r,bill,'20.00')
        self.assertEqual(self.summary(r,bill)['cobrado_paciente'],'20.00')
        self.assertEqual(self.current(r,'pago',payment['id'])['values']['estado'],'Anulado')

    def test_reversal_locks_invoice_before_payment_and_balance_reads(self):
        r=self.repository('pediatrico');bill=self.invoice(r);self.action(r,'factura',bill,'emitir')
        payment=self.pay(r,bill,'12.00')
        with patch.object(r,'_get',wraps=r._get) as get:
            r.financial_action('pago',payment['id'],'revertir',payment['version'])
        calls=[(call.args[1],call.kwargs.get('lock',False)) for call in get.call_args_list]
        self.assertEqual(calls[:3],[('pago',False),('factura',True),('pago',True)])

    def test_invoice_lookup_suggests_patient_balance_and_list_exposes_both_balances(self):
        r=self.repository('pediatrico');bill=self.invoice(r,covered='10.00');self.action(r,'factura',bill,'emitir')
        self.pay(r,bill,'4.00')
        self.assertEqual(r.page('factura',lookup=True)['results'][0]['defaults']['monto'],'6.00')
        self.assertEqual(r.page('factura')['results'][0]['financial']['saldo_seguro'],'10.00')


class FinanceApiTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('finance-admin',password='test-password')
        self.profile=PerfilInstitucional.objects.create(usuario=self.user,institucion='hospital',rol='admin')
        self.client=APIClient();self.client.force_login(self.user)
        session=self.client.session;session['clinical_authenticated_at']=time.time();session.save()

    def test_action_endpoint_executes_issue_and_rejects_stale_version(self):
        harness=FinanceTests();self.addCleanup(harness.doCleanups)
        r=harness.repository('hospital');bill=harness.invoice(r)
        current=harness.current(r,'factura',bill)
        with patch('apps.operaciones.views.OperationsRepository',return_value=r):
            url='/api/operaciones/factura/'+bill+'/'
            response=self.client.post(url,{'accion':'emitir','version':current['version']},format='json')
            self.assertEqual(response.status_code,200,response.data)
            self.assertEqual(response.data['values']['estado'],'Pendiente')
            response=self.client.post(url,{'accion':'anular','version':current['version']},format='json')
            self.assertEqual(response.status_code,409)

    def test_permission_rejection_precedes_body_and_provider(self):
        self.profile.rol='medico';self.profile.save()
        with patch('apps.operaciones.views.OperationsRepository') as provider:
            response=self.client.post('/api/operaciones/factura/H-OP_factura-1/',data='{',content_type='application/json')
            self.assertEqual(response.status_code,403)
            provider.assert_not_called()

    def test_action_body_requires_exact_keys(self):
        for body in [{}, {'accion':'emitir'}, {'accion':'emitir','version':'v','total':'1.00'},
                     {'accion':[],'version':'v'}]:
            with patch('apps.operaciones.views.OperationsRepository') as provider:
                response=self.client.post('/api/operaciones/factura/H-OP_factura-1/',body,format='json')
                self.assertEqual(response.status_code,400)
                provider.assert_not_called()


@skipUnless(os.getenv('OPERATIONS_REAL_TESTS')=='1','requires fresh hospital_auc/pediatrico_auc databases')
class NativeFinanceTests(SimpleTestCase):
    def setUp(self):
        from apps.operaciones.test_audit_blockers import NativeBlockerTests
        self.fixtures=NativeBlockerTests()
        self.fixtures.setUp()
        self.addCleanup(self.fixtures.doCleanups)

    def current(self,r,name,identifier):
        return FinanceTests.current(self,r,name,identifier)

    def action(self,r,name,identifier,action):
        return FinanceTests.action(self,r,name,identifier,action)

    def test_hospital_issue_partial_total_reverse_rollback_and_annul(self):
        r,beds,patients,admissions=self.fixtures.hospital()
        consultation=r.core.registrar_consulta(patients[0],{'fecha':'2020-01-01','notas_evolucion':'DEMO'})['id']
        bill=r.save('factura',{'id_paciente':patients[0],'id_consulta':consultation})['id']
        r.save('detalle_factura',{'id_factura':bill,'concepto':'DEMO','precio_unitario':'20.00','cantidad':1})
        self.action(r,'factura',bill,'emitir')
        payment=r.save('pago',{'id_factura':bill,'monto':'12.00','metodo_pago':'Efectivo'})
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'Parcial')
        other=r.save('pago',{'id_factura':bill,'monto':'8.00','metodo_pago':'Efectivo'})
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'Pagada')
        with patch.object(r.core,'_after_write',side_effect=RuntimeError('rollback')):
            with self.assertRaises(RuntimeError):self.action(r,'pago',payment['id'],'revertir')
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'Pagada')
        self.assertEqual(self.current(r,'pago',payment['id'])['values']['estado'],'Procesado')
        with self.assertRaises(DatosInvalidos):self.action(r,'factura',bill,'anular')
        def reverse(row):
            actor=OperationsRepository(r.context)
            return actor.financial_action('pago',row['id'],'revertir',row['version'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            reversed_payments=list(pool.map(reverse,[payment,other]))
        self.assertTrue(all(row['values']['estado']=='Anulado' for row in reversed_payments))
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'Pendiente')
        self.action(r,'factura',bill,'anular')
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'Anulada')

    def test_pediatric_insurance_collection_and_reversal(self):
        r,policy,authorization,bills=self.fixtures.pediatrics();bill=bills[0]
        method=r.save('metodo_pago',{'nombre':self.fixtures.tag,'estado':'activo'})['id']
        data={'factura_id':bill,'metodo_pago_id':method,'monto':'10.00','tipo_pagador':'aseguradora'}
        with self.assertRaises(DatosInvalidos):r.save('pago',data)
        claim=r.save('reclamacion_seguro',{'factura_id':bill,'poliza_paciente_id':policy,'autorizacion_id':authorization,
            'numero_reclamo':self.fixtures.tag,'monto_reclamado':'10.00','monto_aprobado':'10.00','estado':'aprobado'})
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'pendiente')
        payment=r.save('pago',data)
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'pagada')
        with self.assertRaises(DatosInvalidos):
            r.save('reclamacion_seguro',{'estado':'anulado'},identifier=claim['id'],version=claim['version'])
        self.action(r,'pago',payment['id'],'revertir')
        r.save('reclamacion_seguro',{'estado':'anulado'},identifier=claim['id'],version=claim['version'])
        self.action(r,'factura',bill,'anular')
        self.assertEqual(self.current(r,'factura',bill)['values']['estado'],'anulada')
