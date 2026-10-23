"""Synthetic AUC-08 parents only; actions under test are performed in the browser."""
import json
import os
from pathlib import Path

import django
django.setup()
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.identidad.models import PerfilInstitucional, Profesional
from apps.historiales.domain.context import ContextoClinico
from apps.operaciones.catalog import RESOURCES, manifest
from apps.operaciones.repository import OperationsRepository

work=Path('/checks')
if os.getenv('RUN_AUC08_BROWSER')!='1' or (work/'identity.sqlite3').exists():raise RuntimeError('Requires new disposable identity')
call_command('migrate',verbosity=0)
scenarios={}
for institution,specs in RESOURCES.items():
    repo=OperationsRepository(ContextoClinico(institution,'auc08-seed','admin','1'))
    parents={}
    def reference(name):
        row=repo._run(lambda u:repo._get(u,name,repo.internal(name,parents[name])),read=True)
        label=repo.lookup_dto(name,row)['label']
        return {'id':parents[name],'search':label.split(' · ')[0]}
    def payload(name,tag):
        result={}
        for key,field in specs[name]['fields'].items():
            if field.get('computed'):continue
            if field['type']=='reference':
                result[key]=base(field['resource']);continue
            if not field['required'] or 'default' in field:continue
            if field.get('choices'):result[key]=field['choices'][0]
            elif field['type']=='text':result[key]=(tag+'-'+key)[:field['max']] if key!='correo' else 'demo@example.invalid'
            elif field['type']=='boolean':result[key]=True
            elif field['type'] in {'decimal','integer'}:result[key]=max(1,field.get('min',0))
        return result
    def base(name):
        if name not in parents:
            if not specs[name]['catalog']:raise RuntimeError('Unexpected non-catalogue parent '+name)
            parents[name]=repo.save(name,payload(name,'DEMO-A8-base-'+name))['id']
        return parents[name]
    for name,spec in specs.items():
        if spec['catalog']:base(name)
    professional_name='medico' if repo.sql else 'profesional'
    professional_reference=str(repo.internal(professional_name,parents[professional_name]))
    repo=OperationsRepository(ContextoClinico(institution,'auc08-seed','admin',professional_reference))
    professional=Profesional.objects.create(institucion=institution,referencia_externa=professional_reference,habilitado=True)
    roles=['admin','medico','secretaria','enfermero']+(['laboratorista'] if institution=='laboratorio' else [])
    role_manifests={}
    for role in roles:
        user=get_user_model().objects.create_user('DEMO-A8-'+role+'-'+institution,password=os.environ['AUC_TEST_PASSWORD'])
        PerfilInstitucional.objects.create(usuario=user,institucion=institution,rol=role,profesional=professional if role in {'admin','medico','laboratorista'} else None)
        role_manifests[role]=manifest(ContextoClinico(institution,str(user.pk),role,professional_reference if role in {'admin','medico','laboratorista'} else None))
    patient=repo.core.registrar_paciente({'identificacion':'A8-'+institution[:3]+'-ROOT','nombres':'DEMO A8 '+institution,'apellidos':'Sintetico','fecha_nacimiento':'2000-01-01'})['id']
    parents['paciente']=patient
    parents['consulta']=repo.core.registrar_consulta(patient,{'fecha':'2020-01-01','notas_evolucion':'DEMO A8 semilla'})['id']
    pending=[]
    if institution=='hospital':
        parents['ingreso_hospitalario']=repo.core.ingresar_paciente(patient,{'cama_id':parents['cama'],'fecha_hora_ingreso':'2020-01-01T12:00:00Z','tipo_ingreso':'DEMO A8'})['id']
    if institution=='pediatrico':
        parents['poliza_paciente']=repo.save('poliza_paciente',{'paciente_id':patient,'plan_seguro_id':parents['plan_seguro'],'numero_poliza':'DEMO-A8-POLIZA','estado':'activo'})['id']
    if institution=='laboratorio':
        for _ in range(4):pending.append(repo.core.registrar_resultado(patient,{'tipo_examen':parents['tipo_examen'],'fecha':'2020-01-01T12:00:00Z','estado':'pendiente','campos':[{'nombre':'DEMO A8','valor':1}]})['id'])
    if institution=='odontologica':
        diagnosis=repo.core.registrar_diagnostico(parents['consulta'],{'codigo_cie10':'DEMO','descripcion':'DEMO A8'})['id']
        treatment=repo.core.registrar_tratamiento(diagnosis,{'indicaciones_generales':'DEMO A8'})['id']
        for _ in range(2):pending.append(repo.core.registrar_procedimiento(patient,{'tratamiento_id':treatment,'pieza':'16','descripcion':'DEMO A8','estado':'pendiente'})['id'])
    cases=[]
    for name,spec in specs.items():
        if not spec['catalog']:continue
        values=payload(name,'DEMO-A8-new-'+name)
        candidates=[key for key,f in spec['fields'].items() if f['type']=='text' and not f.get('choices') and not f.get('computed') and key!='correo']
        edit=candidates[0] if candidates else next(key for key,f in spec['fields'].items() if f['type'] in {'decimal','integer'} and not f.get('computed'))
        field=spec['fields'][edit]
        if edit not in values:values[edit]=('DEMO-A8-new-'+name)[:field.get('max',100)] if field['type']=='text' else 1
        edited=('DEMO-A8-edit-'+name)[:field.get('max',100)] if field['type']=='text' else 2
        deactivate={key:False for key in ['activo_operativo','activo','habilitado'] if key in spec['fields']}
        if 'inactivo' in spec['fields'].get('estado',{}).get('choices',[]):deactivate['estado']='inactivo'
        cases.append({'resource':name,'values':values,'edit':{edit:edited},'deactivate':deactivate})
    scenarios[institution]={'resources':role_manifests['admin']['resources'],'roles':role_manifests,'references':{name:reference(name) for name in parents},
                            'catalogues':cases,'pending':pending,'patient':patient}
if os.getenv('RUN_AUC09_GUIDED')=='1':
    users=get_user_model().objects.bulk_create([get_user_model()(username=f'DEMO-A9-page-{n:03d}') for n in range(225)])
    PerfilInstitucional.objects.bulk_create([PerfilInstitucional(usuario=u,institucion='hospital',rol='secretaria') for u in users])
(work/'scenarios.json').write_text(json.dumps(scenarios,ensure_ascii=False,indent=2),encoding='utf-8')
print('AUC-08: synthetic parents, role accounts and 24 catalogue cases prepared',flush=True)
