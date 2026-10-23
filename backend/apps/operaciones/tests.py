import os
import time
from unittest import skipUnless
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import AccesoDenegado, Conflicto, DatosInvalidos
from apps.historiales.infrastructure.factory import AdapterFactory
from apps.identidad.models import PerfilInstitucional
from apps.operaciones.catalog import RESOURCES, manifest, resource, validate
from apps.operaciones.repository import OperationsRepository


class DefinitionTests(SimpleTestCase):
    def test_every_definition_has_primary_key_valid_references_and_no_legacy_auth(self):
        for institution,rs in RESOURCES.items():
            self.assertNotIn('usuario',rs);self.assertNotIn('rol',rs)
            for name,s in rs.items():
                self.assertTrue(s['pk'],(institution,name))
                for f in s['fields'].values():
                    if f['type']=='reference':self.assertIn(f['resource'],rs)
    def test_manifest_filters_roles_and_cannot_cross_institutions(self):
        c=ContextoClinico('pediatrico','1','secretaria')
        keys={r['key'] for r in manifest(c)['resources']}
        self.assertIn('factura',keys);self.assertNotIn('signos_vitales',keys)
        with self.assertRaises(AccesoDenegado):resource(c,'medicamento',write=True)
    def test_decimal_date_and_unknown_field_validation(self):
        s=RESOURCES['hospital']['detalle_factura']
        for data in [{'precio_unitario':'NaN'},{'precio_unitario':'100.001'},{'subtotal':'99'},{'inject':'DROP TABLE'}]:
            with self.assertRaises(DatosInvalidos):validate(s,data)
        with self.assertRaises(DatosInvalidos):validate(RESOURCES['pediatrico']['cita'],{'paciente_id':'x','medico_id':'x','fecha':'2026-02-30','hora':'11:00','estado':'programada'})
    def test_identifier_rejects_other_institution_and_wrong_resource(self):
        repo=OperationsRepository(ContextoClinico('hospital','1','admin','1'))
        for value in ['PED-P-1','H-C-1','1;DROP TABLE','H-P-2147483648']:
            from apps.historiales.domain.errors import RecursoNoEncontrado
            with self.assertRaises(RecursoNoEncontrado):repo.internal('paciente',value)


class PermissionTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('ops-admin',password='some-test-pass')
        self.profile=PerfilInstitucional.objects.create(usuario=self.user,institucion='pediatrico',rol='admin')
        self.client=APIClient();self.client.force_login(self.user)
        session=self.client.session;session['clinical_authenticated_at']=time.time();session.save()
    def test_manifest_is_real_and_anonymous_is_rejected(self):
        self.assertEqual(self.client.get('/api/operaciones/').status_code,200)
        self.client.logout();self.assertEqual(self.client.get('/api/operaciones/').status_code,401)
    def test_denial_precedes_json_and_provider_construction(self):
        self.profile.rol='secretaria';self.profile.save()
        with patch('apps.operaciones.repository.AdapterFactory.create_clinical') as factory:
            r=self.client.post('/api/operaciones/medicamento/',data='{',content_type='application/json')
            self.assertEqual(r.status_code,403);factory.assert_not_called()
    def test_accounts_are_institution_scoped_without_technical_privileges(self):
        r=self.client.post('/api/operaciones/cuentas/',{'username':'ops-secretary','password':'Sample-Operations-Pass-240!','rol':'secretaria'},format='json')
        self.assertEqual(r.status_code,201,r.data)
        user=get_user_model().objects.get(username='ops-secretary');self.assertFalse(user.is_staff);self.assertFalse(user.is_superuser)
        other=get_user_model().objects.create_user('other');PerfilInstitucional.objects.create(usuario=other,institucion='hospital',rol='admin')
        r=self.client.patch('/api/operaciones/cuentas/',{'id':str(other.pk),'activo':False},format='json');self.assertEqual(r.status_code,404)
        r=self.client.patch('/api/operaciones/cuentas/',{'id':str(self.user.pk),'activo':False},format='json');self.assertEqual(r.status_code,400)
    def test_csrf_enforced_on_writes(self):
        client=APIClient(enforce_csrf_checks=True);client.force_login(self.user)
        session=client.session;session['clinical_authenticated_at']=time.time();session.save()
        self.assertEqual(client.post('/api/operaciones/cuentas/',{},format='json').status_code,403)


@skipUnless(os.getenv('OPERATIONS_REAL_TESTS')=='1','requires disposable four-engine runner')
class NativeOperationsTests(SimpleTestCase):
    def test_hospital_full_operational_chain(self):
        repo=OperationsRepository(ContextoClinico('hospital','native','admin','1'));core=repo.core
        save=lambda n,**v:repo.save(n,v)['id']
        specialty=save('especialidad',nombre='DEMO Operaciones',nivel_complejidad=1)
        doctor=save('medico',id_especialidad=specialty,nombre_completo='DEMO Médico',colegiado='DEMO-OPS-1',habilitado=True)
        nurse=save('enfermero',nombre_completo='DEMO Enfermería',licencia_enfermeria='DEMO-OPS-N')
        pavilion=save('pabellon_edificio',nombre_pabellon='DEMO Operaciones',director_responsable=doctor)
        room=save('habitacion',id_pabellon=pavilion,numero_habitacion='OPS-01')
        bed=save('cama',id_habitacion=room,codigo_cama='OPS-01',estado_limpieza='limpia')
        bed2=save('cama',id_habitacion=room,codigo_cama='OPS-02',estado_limpieza='limpia')
        theater=save('quirofano',id_pabellon=pavilion,nombre_sala='DEMO Quirófano')
        medicine=save('medicamento',nombre_comercial='DEMO no administrar',principio_activo='DEMO',stock_farmacia=10)
        patient=core.registrar_paciente({'identificacion':'DEMO-OPS-H','nombres':'DEMO','apellidos':'Hospital','fecha_nacimiento':'2000-01-01'})['id']
        appointment=save('cita',id_paciente=patient,id_medico=doctor,fecha_hora='2020-01-01T12:00:00Z',estado='programada')
        with self.assertRaises(Conflicto):save('cita',id_paciente=patient,id_medico=doctor,fecha_hora='2020-01-01T12:00:00Z',estado='programada')
        consult=core.registrar_consulta(patient,{'fecha':'2020-01-01','notas_evolucion':'DEMO','cita_id':appointment})['id']
        diagnosis=core.registrar_diagnostico(consult,{'codigo_cie10':'DEMO','descripcion':'DEMO'})['id']
        treatment=core.registrar_tratamiento(diagnosis,{'indicaciones_generales':'DEMO'})['id']
        rx=core.registrar_receta(treatment,{'medicamento_id':medicine,'dosis':'DEMO','frecuencia':'DEMO'})['id']
        dispatch=save('despacho_farmacia',id_receta=rx,cantidad_entregada=2)
        save('aplicacion_enfermeria',id_despacho=dispatch,id_enfermero=nurse)
        with self.assertRaises(DatosInvalidos):save('despacho_farmacia',id_receta=rx,cantidad_entregada=99)
        admission=core.ingresar_paciente(patient,{'cama_id':bed,'fecha_hora_ingreso':'2020-01-01T12:00:00Z','tipo_ingreso':'DEMO'})['id']
        save('emergencia',id_ingreso=admission,motivo_consulta='DEMO',nivel_triaje='DEMO')
        save('signos_vitales',id_ingreso=admission,id_enfermero=nurse,frecuencia_cardiaca=75,oximetria=99)
        save('movimiento_cama',id_ingreso=admission,id_cama=bed2,fecha_hora_inicio='2020-01-01T13:00:00Z',motivo_traslado='DEMO')
        surgery=save('cirugia',id_ingreso=admission,id_quirofano=theater,fecha_hora_inicio='2020-01-01T14:00:00Z',fecha_hora_fin='2020-01-01T15:00:00Z',estado='pendiente')
        save('equipo_quirurgico',id_cirugia=surgery,id_medico=doctor,rol_en_cirugia='DEMO')
        save('diagnostico_ingreso',id_ingreso=admission,codigo_cie10='DEMO',descripcion='DEMO ingreso')
        invoice=save('factura',id_paciente=patient,id_consulta=consult,impuestos='0.00')
        save('detalle_factura',id_factura=invoice,concepto='DEMO atención',cantidad=2,precio_unitario='10.00')
        rows=repo.page('factura')['results'];bill=next(r for r in rows if r['id']==invoice)
        self.assertEqual(bill['values']['total'],'20.00')
        # A failure after detail + total calculation must roll the entire transaction back.
        with patch.object(core,'_after_write',side_effect=RuntimeError('injected rollback')):
            with self.assertRaises(RuntimeError):save('detalle_factura',id_factura=invoice,concepto='DEMO rollback',cantidad=1,precio_unitario='50.00')
        self.assertEqual(repo.page('factura')['results'][0]['values']['total'],'20.00')
        repo.financial_action('factura',invoice,'emitir',bill['version'])
        from concurrent.futures import ThreadPoolExecutor
        def payment():
            actor=OperationsRepository(ContextoClinico('hospital','race','admin','1'))
            try:actor.save('pago',{'id_factura':invoice,'monto':'12.00','metodo_pago':'Efectivo'});return 'saved'
            except DatosInvalidos:return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(lambda _:payment(),range(2)))
        self.assertEqual(sorted(outcomes),['rejected','saved'])
        self.assertEqual(repo.page('factura')['results'][0]['values']['estado'],'Parcial')
        save('pago',id_factura=invoice,monto='8.00',metodo_pago='Efectivo')
        with self.assertRaises(DatosInvalidos):save('pago',id_factura=invoice,monto='1.00',metodo_pago='Efectivo')
        self.assertEqual(repo.page('medicamento')['results'][0]['values']['stock_farmacia'],8)
        core.dar_alta(admission,'2020-01-02T12:00:00Z')
        core.archivar_paciente(patient,'DEMO cierre')
        with self.assertRaises(Conflicto):save('signos_vitales',id_ingreso=admission,id_enfermero=nurse,frecuencia_cardiaca=80)
        self.assertEqual(repo.page('cirugia',patient=patient)['count'],1)
        for name in repo.specs:repo.page(name)
        record=repo.page('medicamento')['results'][0]
        repo.save('medicamento',{'activo_operativo':False},identifier=record['id'],version=record['version'])
        self.assertEqual(core.listar_medicamentos()['count'],0)

    def test_pediatrics_full_operational_chain(self):
        repo=OperationsRepository(ContextoClinico('pediatrico','native','admin','1'));core=repo.core;save=lambda n,**v:repo.save(n,v)['id']
        specialty=save('especialidad',nombre='DEMO Pediatría')
        doctor=save('medico',nombre='DEMO',apellido='Pediatra',colegiado='DEMO-PED-1',especialidad_id=specialty,estado='activo')
        medicine=save('medicamento',nombre='DEMO no administrar',estado='activo')
        vaccine=save('vacuna',nombre='DEMO no aplicar',numero_dosis=2)
        examtype=save('tipo_examen',nombre='DEMO Examen')
        service=save('servicio_medico',codigo='DEMO-C',nombre='DEMO Consulta',precio_base='10.00',estado='activo')
        insurer=save('aseguradora',nombre='DEMO Aseguradora',estado='activo')
        plan=save('plan_seguro',aseguradora_id=insurer,nombre='DEMO Plan',deducible='0.00',limite_anual='100.00',estado='activo')
        save('cobertura_servicio',plan_seguro_id=plan,servicio_id=service,porcentaje_cobertura='50.00',copago='0.00',estado='activo')
        method=save('metodo_pago',nombre='DEMO Efectivo',estado='activo')
        tutor=save('tutor',nombres='DEMO',apellidos='Tutor',dpi='DEMO-TUTOR')
        patient=core.registrar_paciente({'identificacion':'DEMO-OPS-P','nombres':'DEMO','apellidos':'Pediatría','fecha_nacimiento':'2010-01-01'})['id']
        save('paciente_tutor',paciente_id=patient,tutor_id=tutor,parentesco='madre')
        appointment=save('cita',paciente_id=patient,medico_id=doctor,fecha='2020-01-01',hora='12:00:00',estado='programada')
        consult=core.registrar_consulta(patient,{'fecha':'2020-01-01','notas_evolucion':'DEMO','cita_id':appointment})['id']
        diagnosis=core.registrar_diagnostico(consult,{'codigo_cie10':'DEMO','descripcion':'DEMO'})['id']
        treatment=core.registrar_tratamiento(diagnosis,{'indicaciones_generales':'DEMO'})['id']
        core.registrar_receta(treatment,{'medicamento_id':medicine,'dosis':'DEMO','frecuencia':'DEMO'})
        core.registrar_vacuna(patient,{'vacuna_id':vaccine,'fecha':'2020-01-01','dosis':1})
        core.registrar_crecimiento(patient,{'fecha':'2020-01-01','peso_kg':'25.00','talla_cm':'120.00'})
        save('antecedente_medico',paciente_id=patient,tipo='DEMO',descripcion='DEMO')
        save('signos_vitales',consulta_id=consult,temperatura='36.5',frecuencia_cardiaca=80,saturacion_oxigeno='99.00')
        exam=save('examen',consulta_id=consult,tipo_examen_id=examtype,estado='pendiente')
        save('resultado_examen',examen_id=exam,valor='DEMO',unidad='DEMO',estado='finalizado')
        policy=save('poliza_paciente',paciente_id=patient,plan_seguro_id=plan,numero_poliza='DEMO-OPS',estado='activo')
        auth=save('autorizacion_seguro',poliza_paciente_id=policy,consulta_id=consult,numero_autorizacion='DEMO-1',monto_autorizado='10.00',estado='aprobado')
        invoice=save('factura',paciente_id=patient,consulta_id=consult,impuestos='0.00',descuento='0.00')
        save('detalle_factura',factura_id=invoice,servicio_id=service,cantidad=1,precio_unitario='10.00',monto_cubierto='5.00')
        bill=next(row for row in repo.page('factura')['results'] if row['id']==invoice)
        repo.financial_action('factura',invoice,'emitir',bill['version'])
        save('reclamacion_seguro',factura_id=invoice,poliza_paciente_id=policy,autorizacion_id=auth,numero_reclamo='DEMO-RECLAMO',monto_reclamado='5.00',estado='pendiente')
        save('pago',factura_id=invoice,metodo_pago_id=method,monto='5.00',tipo_pagador='paciente')
        bill=repo.page('factura')['results'][0];self.assertEqual(bill['values']['total'],'10.00');self.assertEqual(bill['values']['total_paciente'],'5.00')
        self.assertEqual(bill['values']['estado'],'parcial')
        self.assertEqual(repo.page('resultado_examen',patient=patient)['count'],1)
        # Cross-patient insurance references must fail before insertion.
        other=core.registrar_paciente({'identificacion':'DEMO-OPS-P2','nombres':'DEMO','apellidos':'Otro','fecha_nacimiento':'2010-01-01'})['id']
        other_policy=save('poliza_paciente',paciente_id=other,plan_seguro_id=plan,numero_poliza='DEMO-OTHER',estado='activo')
        with self.assertRaises(DatosInvalidos):save('autorizacion_seguro',poliza_paciente_id=other_policy,consulta_id=consult,numero_autorizacion='DEMO-X')

    def test_documental_catalog_agenda_and_payments(self):
        for institution in ['laboratorio','odontologica']:
            with self.subTest(institution=institution):
                repo=OperationsRepository(ContextoClinico(institution,'native','admin','1'));core=repo.core;save=lambda n,**v:repo.save(n,v)['id']
                professional=save('profesional',nombre='DEMO Profesional',colegiado='DEMO-1',habilitado=True)
                medicine=save('medicamento',nombre='DEMO Medicamento',presentacion='DEMO')
                with self.assertRaises(Conflicto):save('medicamento',nombre='DEMO Medicamento')
                catalog=repo.page('medicamento')['results'][0]
                updated=repo.save('medicamento',{'presentacion':'DEMO actualizada'},identifier=catalog['id'],version=catalog['version'])
                self.assertEqual(updated['values']['presentacion'],'DEMO actualizada')
                with self.assertRaises(Conflicto):repo.save('medicamento',{'presentacion':'stale'},identifier=catalog['id'],version=catalog['version'])
                patient=core.registrar_paciente({'identificacion':'DEMO-OPS','nombres':'DEMO','apellidos':institution,'fecha_nacimiento':'2000-01-01'})['id']
                save('cita',paciente_id=patient,profesional_id=professional,fecha_hora='2020-01-01T12:00:00Z',motivo='DEMO',estado='programada')
                with self.assertRaises(Conflicto):save('cita',paciente_id=patient,profesional_id=professional,fecha_hora='2020-01-01T12:00:00Z',motivo='DEMO',estado='programada')
                consult=core.registrar_consulta(patient,{'fecha':'2020-01-01','notas_evolucion':'DEMO'})['id']
                extra={}
                if institution=='odontologica':
                    diagnosis=core.registrar_diagnostico(consult,{'codigo_cie10':'DEMO','descripcion':'DEMO'})['id'];treatment=core.registrar_tratamiento(diagnosis,{'indicaciones_generales':'DEMO'})['id']
                    extra['procedimiento_id']=core.registrar_procedimiento(patient,{'tratamiento_id':treatment,'pieza':'16','descripcion':'DEMO','estado':'realizado'})['id']
                else:
                    exam=save('tipo_examen',nombre='DEMO Examen')
                    core.registrar_resultado(patient,{'tipo_examen':exam,'fecha':'2020-01-01T12:00:00Z','estado':'finalizado','campos':[{'nombre':'DEMO','valor':1}]})
                save('pago',paciente_id=patient,monto_centavos=100,moneda='GTQ',referencia='DEMO',**extra)
                self.assertEqual(repo.page('pago',patient=patient)['count'],1)
                with self.assertRaises(Conflicto):save('pago',paciente_id=patient,monto_centavos=100,moneda='GTQ',referencia='DEMO',**extra)
                for name in repo.specs:repo.page(name)
                core.archivar_paciente(patient,'DEMO')
                with self.assertRaises(Conflicto):save('cita',paciente_id=patient,profesional_id=professional,fecha_hora='2020-01-02T12:00:00Z',motivo='DEMO',estado='programada')
