"""AUC-07: state graphs, conditions and native transactional lifecycles."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from unittest import skipUnless
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import AccesoDenegado, Conflicto, DatosInvalidos
from apps.operaciones.catalog import RESOURCES, manifest, resource
from apps.operaciones.repository import OperationsRepository
from apps.operaciones.transitions import TRANSITIONS, validate_transition
from apps.identidad.models import PerfilInstitucional, Profesional


class TransitionRulesTests(SimpleTestCase):
    def test_each_edge_and_terminal_in_every_machine(self):
        for (institution,name),machine in TRANSITIONS.items():
            for before,targets in machine.items():
                for after in machine:
                    with self.subTest(institution=institution,resource=name,before=before,after=after):
                        row={'estado':after,'monto_autorizado':'10.00','monto_aprobado':'0.00' if after=='pendiente' else '5.00',
                             'fecha_hora_fin':'2020-01-01T12:00:00Z'}
                        allowed=bool(targets) and (after in targets or after==before and before!='aprobado')
                        if allowed:validate_transition(institution,name,row,{'estado':before})
                        else:
                            with self.assertRaises(Conflicto):validate_transition(institution,name,row,{'estado':before})

    def test_invalid_initial_and_unknown_states_are_rejected(self):
        for institution,name in [('hospital','cirugia'),('pediatrico','examen'),
                                 ('pediatrico','autorizacion_seguro'),('pediatrico','reclamacion_seguro')]:
            for state in ['finalizado','aprobado','inventado',None]:
                with self.assertRaises(DatosInvalidos):validate_transition(institution,name,{'estado':state},None)

    def test_decisions_require_positive_amount_and_resolution_is_derived(self):
        for name,amount,datefield in [('autorizacion_seguro','monto_autorizado','fecha_respuesta'),
                                     ('reclamacion_seguro','monto_aprobado','fecha_resolucion')]:
            row={'estado':'aprobado',amount:'0.00'}
            with self.assertRaises(DatosInvalidos):validate_transition('pediatrico',name,row,{'estado':'pendiente'})
            row[amount]='1.00'
            validate_transition('pediatrico',name,row,{'estado':'pendiente'})
            self.assertRegex(row[datefield],r'^\d{4}-\d{2}-\d{2}$')
            row[datefield]='2999-01-01'
            with self.assertRaises(DatosInvalidos):validate_transition('pediatrico',name,row,{'estado':'pendiente'})

    def test_future_surgery_cannot_be_completed(self):
        with self.assertRaises(DatosInvalidos):
            validate_transition('hospital','cirugia',{'estado':'realizado','fecha_hora_fin':'2999-01-01T12:00:00Z'},{'estado':'pendiente'})

    def test_nosql_edit_requires_professional_and_exposes_only_status(self):
        for institution,name in [('laboratorio','resultado'),('odontologica','procedimiento')]:
            with self.assertRaises(AccesoDenegado):resource(ContextoClinico(institution,'test','medico'),name,write=True,edit=True)
            self.assertFalse(next(s for s in manifest(ContextoClinico(institution,'test','medico'))['resources'] if s['key']==name)['edit'])
            with self.assertRaises(AccesoDenegado):resource(ContextoClinico(institution,'test','enfermero','1'),name,write=True,edit=True)
            context=ContextoClinico(institution,'test','medico','1')
            spec=resource(context,name,write=True,edit=True)
            self.assertEqual(spec['editable_fields'],['estado'])
            definition=next(s for s in manifest(context)['resources'] if s['key']==name)
            self.assertTrue(definition['edit']);self.assertFalse(definition['create'])
            self.assertEqual(definition['state_transitions']['anulado'],[])


class LifecycleMixin:
    def current(self,r,name,identifier):
        return r._run(lambda u:r.dto(name,r._get(u,name,r.internal(name,identifier))),read=True)

    def update(self,r,name,identifier,values):
        return r.save(name,values,identifier=identifier,version=self.current(r,name,identifier)['version'])


class TransitionApiTests(TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user('transition-user',password='test-password')
        self.profile=PerfilInstitucional.objects.create(usuario=user,institucion='laboratorio',rol='medico')
        self.client=APIClient();self.client.force_login(user)
        session=self.client.session;session['clinical_authenticated_at']=time.time();session.save()

    def test_missing_professional_denies_before_body_and_provider(self):
        with patch('apps.operaciones.views.OperationsRepository') as provider:
            response=self.client.patch('/api/operaciones/resultado/opaque/',data='{',content_type='application/json')
            self.assertEqual(response.status_code,403)
            provider.assert_not_called()

    def test_authorized_patch_forwards_only_explicit_status_and_version(self):
        self.profile.profesional=Profesional.objects.create(institucion='laboratorio',referencia_externa='1',habilitado=True)
        self.profile.save()
        with patch('apps.operaciones.views.OperationsRepository') as provider:
            provider.return_value.save.return_value={'id':'opaque','values':{'estado':'en_proceso'},'version':'v2'}
            response=self.client.patch('/api/operaciones/resultado/opaque/',{'values':{'estado':'en_proceso'},'version':'v1'},format='json')
            self.assertEqual(response.status_code,200,response.data)
            provider.return_value.save.assert_called_once_with('resultado',{'estado':'en_proceso'},identifier='opaque',version='v1')


@skipUnless(os.getenv('OPERATIONS_REAL_TESTS')=='1','requires new hospital_auc/pediatrico_auc databases')
class NativeSQLTransitionTests(LifecycleMixin,SimpleTestCase):
    def setUp(self):
        from apps.operaciones.test_audit_blockers import NativeBlockerTests
        self.fixtures=NativeBlockerTests();self.fixtures.setUp();self.addCleanup(self.fixtures.doCleanups)

    def test_surgery_requires_team_freezes_completed_and_releases_cancelled_slot(self):
        r,beds,patients,admissions=self.fixtures.hospital()
        pavilion=r.save('pabellon_edificio',{'nombre_pabellon':self.fixtures.tag+'-Q'})['id']
        theatre=r.save('quirofano',{'id_pabellon':pavilion,'nombre_sala':self.fixtures.tag})['id']
        def schedule(start,end):
            return r.save('cirugia',{'id_ingreso':admissions[0],'id_quirofano':theatre,
                'fecha_hora_inicio':start,'fecha_hora_fin':end})['id']
        surgery=schedule('2020-01-01T14:00:00Z','2020-01-01T15:00:00Z')
        with self.assertRaises(DatosInvalidos):self.update(r,'cirugia',surgery,{'estado':'realizado'})
        r.save('equipo_quirurgico',{'id_cirugia':surgery,'id_medico':r.public_id('medico',int(r.context.profesional_id)),'rol_en_cirugia':'DEMO'})
        self.update(r,'cirugia',surgery,{'estado':'realizado'})
        with self.assertRaises(Conflicto):self.update(r,'cirugia',surgery,{'riesgo_quirurgico':'editado'})
        other=schedule('2020-01-01T16:00:00Z','2020-01-01T17:00:00Z')
        self.update(r,'cirugia',other,{'estado':'cancelado'})
        self.assertTrue(schedule('2020-01-01T16:00:00Z','2020-01-01T17:00:00Z'))
        with self.assertRaises(Conflicto):self.update(r,'cirugia',other,{'estado':'pendiente'})

    def test_exam_result_lifecycle_cancellation_and_rollback(self):
        r,policy,authorization,bills=self.fixtures.pediatrics()
        bill=r._run(lambda u:r._get(u,'factura',r.internal('factura',bills[0])),read=True)
        kind=r.save('tipo_examen',{'nombre':self.fixtures.tag})['id']
        def exam():return r.save('examen',{'consulta_id':r.public_id('consulta',bill['consulta_id']),'tipo_examen_id':kind})['id']
        exam_id=exam()
        with self.assertRaises(Conflicto):self.update(r,'examen',exam_id,{'estado':'finalizado'})
        result=r.save('resultado_examen',{'examen_id':exam_id,'valor':'DEMO','estado':'pendiente'})['id']
        self.assertEqual(self.current(r,'examen',exam_id)['values']['estado'],'en_proceso')
        with self.assertRaises(DatosInvalidos):self.update(r,'examen',exam_id,{'estado':'finalizado'})
        with self.assertRaises(DatosInvalidos):r.save('resultado_examen',{'examen_id':exam_id,'valor':'duplicado'})
        self.update(r,'resultado_examen',result,{'estado':'en_proceso'})
        with patch.object(r.core,'_after_write',side_effect=RuntimeError('rollback')):
            with self.assertRaises(RuntimeError):self.update(r,'resultado_examen',result,{'estado':'finalizado'})
        self.assertEqual(self.current(r,'resultado_examen',result)['values']['estado'],'en_proceso')
        self.update(r,'resultado_examen',result,{'estado':'finalizado'})
        self.assertEqual(self.current(r,'examen',exam_id)['values']['estado'],'finalizado')
        with self.assertRaises(Conflicto):self.update(r,'resultado_examen',result,{'valor':'editado'})
        cancelled=exam();pending=r.save('resultado_examen',{'examen_id':cancelled,'valor':'DEMO','estado':'pendiente'})['id']
        with self.assertRaises(DatosInvalidos):self.update(r,'examen',cancelled,{'estado':'anulado'})
        self.update(r,'resultado_examen',pending,{'estado':'anulado'})
        self.update(r,'examen',cancelled,{'estado':'anulado'})
        with self.assertRaises(Conflicto):self.update(r,'examen',cancelled,{'estado':'pendiente'})

    def test_authorization_and_claim_decisions_and_revocation_dependencies(self):
        r,policy,authorization,bills=self.fixtures.pediatrics()
        claim=r.save('reclamacion_seguro',{'factura_id':bills[0],'poliza_paciente_id':policy,'autorizacion_id':authorization,
            'numero_reclamo':self.fixtures.tag,'monto_reclamado':'10.00'})['id']
        with self.assertRaises(DatosInvalidos):self.update(r,'autorizacion_seguro',authorization,{'estado':'anulado'})
        with self.assertRaises(DatosInvalidos):self.update(r,'reclamacion_seguro',claim,{'estado':'aprobado','monto_aprobado':'0.00'})
        self.update(r,'reclamacion_seguro',claim,{'estado':'aprobado','monto_aprobado':'10.00'})
        with self.assertRaises(Conflicto):self.update(r,'reclamacion_seguro',claim,{'estado':'pendiente'})
        self.update(r,'reclamacion_seguro',claim,{'estado':'anulado'})
        self.update(r,'autorizacion_seguro',authorization,{'estado':'anulado'})
        with self.assertRaises(Conflicto):self.update(r,'autorizacion_seguro',authorization,{'estado':'aprobado'})

    def test_plan_and_coverage_deactivation_preserves_records_and_checks_parent_on_reactivation(self):
        r,policy,authorization,bills=self.fixtures.pediatrics()
        policy_row=r._run(lambda u:r._get(u,'poliza_paciente',r.internal('poliza_paciente',policy)),read=True)
        plan=r.public_id('plan_seguro',policy_row['plan_seguro_id'])
        service=r.save('servicio_medico',{'codigo':self.fixtures.tag+'C','nombre':self.fixtures.tag+'C','precio_base':'1.00','estado':'activo'})['id']
        coverage=r.save('cobertura_servicio',{'plan_seguro_id':plan,'servicio_id':service,'porcentaje_cobertura':'50.00'})['id']
        self.update(r,'plan_seguro',plan,{'estado':'inactivo'})
        self.update(r,'cobertura_servicio',coverage,{'estado':'inactivo'})
        with self.assertRaises(DatosInvalidos):self.update(r,'cobertura_servicio',coverage,{'estado':'activo'})
        self.update(r,'plan_seguro',plan,{'estado':'activo'})
        self.update(r,'cobertura_servicio',coverage,{'estado':'activo'})


@skipUnless(os.getenv('OPERATIONS_NOSQL_TRANSITIONS')=='1','requires dedicated Mongo replica set and Firestore emulator')
class NativeDocumentTransitionTests(LifecycleMixin,SimpleTestCase):
    def record(self,institution):
        tag='A7-'+uuid4().hex[:10]
        r=OperationsRepository(ContextoClinico(institution,'auc07','admin'))
        professional=r.save('profesional',{'nombre':tag,'colegiado':tag,'activo':True,'habilitado':True})['id']
        r=OperationsRepository(ContextoClinico(institution,'auc07','admin',professional))
        patient=r.core.registrar_paciente({'identificacion':tag,'nombres':'DEMO','apellidos':'Transiciones','fecha_nacimiento':'2000-01-01'})['id']
        if institution=='laboratorio':
            kind=r.save('tipo_examen',{'nombre':tag})['id']
            row=r.core.registrar_resultado(patient,{'tipo_examen':kind,'fecha':'2020-01-01T12:00:00Z','estado':'pendiente','campos':[{'nombre':'DEMO','valor':1}]})
            return r,'resultado',patient,row['id']
        consultation=r.core.registrar_consulta(patient,{'fecha':'2020-01-01','notas_evolucion':'DEMO'})['id']
        diagnosis=r.core.registrar_diagnostico(consultation,{'codigo_cie10':'DEMO','descripcion':'DEMO'})['id']
        treatment=r.core.registrar_tratamiento(diagnosis,{'indicaciones_generales':'DEMO'})['id']
        row=r.core.registrar_procedimiento(patient,{'tratamiento_id':treatment,'pieza':'16','descripcion':'DEMO','estado':'pendiente'})
        return r,'procedimiento',patient,row['id']

    def test_complete_existing_document_preserves_hidden_clinical_fields_and_version(self):
        for institution in ['laboratorio','odontologica']:
            r,name,patient,identifier=self.record(institution)
            old=r._run(lambda u:deepcopy(r._get(u,name,identifier)),read=True)
            if name=='resultado':self.update(r,name,identifier,{'estado':'en_proceso'})
            final='finalizado' if name=='resultado' else 'realizado'
            row=self.update(r,name,identifier,{'estado':final})
            self.assertEqual(row['version'],self.current(r,name,identifier)['version'])
            stored=r._run(lambda u:r._get(u,name,identifier),read=True)
            for key,value in old.items():
                if key!='estado':self.assertEqual(stored[key],value,key)
            with self.assertRaises(Conflicto):self.update(r,name,identifier,{'estado':'pendiente'})
            with self.assertRaises(DatosInvalidos):self.update(r,name,identifier,{'descripcion':'editado'})

    def test_competing_transitions_one_winner_and_archive_blocks_followup(self):
        for institution in ['laboratorio','odontologica']:
            r,name,patient,identifier=self.record(institution)
            version=self.current(r,name,identifier)['version']
            def change(state):
                actor=OperationsRepository(r.context)
                try:actor.save(name,{'estado':state},identifier=identifier,version=version);return 'saved'
                except Conflicto:return 'conflict'
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes=list(pool.map(change,['en_proceso' if name=='resultado' else 'realizado','anulado']))
            self.assertEqual(sorted(outcomes),['conflict','saved'])
            r,name,patient,identifier=self.record(institution)
            r.core.archivar_paciente(patient,'DEMO')
            with self.assertRaises(Conflicto):self.update(r,name,identifier,{'estado':'anulado'})

    def test_document_state_and_patient_version_roll_back_together(self):
        for institution in ['laboratorio','odontologica']:
            r,name,patient,identifier=self.record(institution)
            before=r._run(lambda u:deepcopy(r._get(u,'paciente',patient)),read=True)
            with patch.object(r.core,'_after_write',side_effect=RuntimeError('rollback')):
                with self.assertRaises(RuntimeError):self.update(r,name,identifier,{'estado':'anulado'})
            self.assertEqual(self.current(r,name,identifier)['values']['estado'],'pendiente')
            self.assertEqual(r._run(lambda u:r._get(u,'paciente',patient),read=True),before)
