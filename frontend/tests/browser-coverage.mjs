import assert from 'node:assert/strict'
import { readFile,writeFile } from 'node:fs/promises'
import { coverageBrowser } from './coverage-browser.mjs'

const scenarios=JSON.parse(await readFile('/checks/scenarios.json','utf8'))
const b=await coverageBrowser(),{evaluate,wait,fill,click,screenshot,pause}=b
const results=[]
let data,resources
const rowSelector=id=>`tr[data-record-id=${JSON.stringify(id)}]`
const mark=(test,detail={})=>{results.push({test,...detail});console.log('PASS '+test)}
const api=path=>evaluate(`fetch('/api/'+${JSON.stringify(path)},{credentials:'same-origin'}).then(async r=>{if(!r.ok)throw new Error('Read failed '+r.status);return r.json()})`)
async function record(name,id,lookup=false){
  for(let offset=0;offset<10000;offset+=100){
    const page=await api(`operaciones/${name}/?limit=100&offset=${offset}${lookup?'&lookup=1':''}`)
    const row=page.results.find(r=>r.id===id);if(row)return row
    if(offset+100>=page.count)break
  }
  throw new Error(`Missing ${name}/${id}`)
}
async function login(institution,role='admin'){
  await wait(`!!document.querySelector('#username')`)
  await fill('#username',`DEMO-A8-${role}-${institution}`);await fill('#password',process.env.AUC_TEST_PASSWORD)
  await click('Ingresar');await wait(`!!document.querySelector('.workspace-nav')`)
  await wait(`!!document.querySelector('.task-grid')`)
}
async function open(name){
  const r=resources.find(r=>r.key===name);assert.ok(r,name)
  await click(r.group,'.workspace-nav')
  await wait(`!![...document.querySelectorAll('.task-card strong')].find(e=>e.textContent===${JSON.stringify(r.label)})`)
  await evaluate(`[...document.querySelectorAll('.task-card')].find(e=>e.querySelector('strong').textContent===${JSON.stringify(r.label)}).click()`)
  await wait(`document.querySelector('.resource-panel h2')?.textContent===${JSON.stringify(r.label)}`)
  await pause(120)
}
async function locate(name,id){
  await open(name)
  for(let i=0;i<200;i++){
    if(await evaluate(`!!document.querySelector(${JSON.stringify(rowSelector(id))})`))return
    await pause(80)
    if(await evaluate(`!![...document.querySelectorAll('.pagination button')].find(e=>e.textContent==='Siguiente'&&!e.disabled)`)){await click('Siguiente','.pagination');await pause(200)}
  }
  throw new Error('Row not visible '+name+'/'+id)
}
async function form(values,name){
  const fields=resources.find(r=>r.key===name).fields
  // References can suggest amounts; enter them before explicit amounts.
  for(const [key,value] of Object.entries(values).sort(([a],[c])=>Number(fields[c].type==='reference')-Number(fields[a].type==='reference'))){
    const field=fields[key],selector='#operation-'+key
    await wait(`!!document.querySelector(${JSON.stringify(selector)})`)
    if(field.type==='reference'){
      const current=await record(field.resource,value,true)
      let search=current.label.split(' · ')[0]
      if(search.includes(value)||/^\d{4}-\d{2}-\d{2}/.test(search))search=''
      const input=`[id="operation-${key}"]`
      await evaluate(`document.querySelector(${JSON.stringify(input)}).parentElement.querySelector('input').setAttribute('data-auc-ref',${JSON.stringify(key)})`)
      await fill(`[data-auc-ref="${key}"]`,search)
      for(let i=0;i<100;i++){
        if(await evaluate(`[...document.querySelector(${JSON.stringify(selector)}).options].some(o=>o.value===${JSON.stringify(value)})`))break
        await pause(100)
        await evaluate(`(()=>{const p=document.querySelector(${JSON.stringify(selector)}).parentElement;const next=[...p.querySelectorAll('button')].find(e=>e.textContent==='Más opciones'&&!e.disabled);if(next)next.click()})()`)
        await pause(250)
      }
      await wait(`!document.querySelector(${JSON.stringify(selector)}).disabled&&[...document.querySelector(${JSON.stringify(selector)}).options].some(o=>o.value===${JSON.stringify(value)})`)
    }
    const v=field.type==='datetime'?new Date(new Date(value).getTime()-6*3600000).toISOString().slice(0,19):value
    await fill(selector,v)
  }
}
async function save(expected,button='Guardar registro'){
  const before=await evaluate('window.__aucWrites.length')
  await evaluate(`(()=>{const f=document.querySelector('dialog[open] form');if(!f.checkValidity())throw new Error([...f.querySelectorAll(':invalid')].map(e=>e.id||e.name).join(','));f.requestSubmit();f.requestSubmit()})()`)
  await wait(`window.__aucWrites.length>${before}`)
  const writes=await evaluate(`window.__aucWrites.slice(${before})`)
  assert.equal(writes.length,1,'One submission even on repeated click')
  assert.equal(writes[0].status,expected,JSON.stringify(writes[0].body))
  if(expected<300)await wait(`!document.querySelector('dialog[open]')`)
  else await click('Cancelar','dialog[open]')
  return writes[0].body
}
async function create(name,values){await open(name);await click('Nuevo registro');await wait(`!!document.querySelector('dialog[open]')`);await form(values,name);return save(201)}
async function update(name,id,values,expected=200){await locate(name,id);await click('Editar',rowSelector(id));await wait(`!!document.querySelector('dialog[open]')`);await form(values,name);return save(expected)}
async function action(name,id,label,expected=200){await locate(name,id);await click(label,rowSelector(id));await wait(`!!document.querySelector('dialog[open]')`);return save(expected,label)}
async function state(name,id,expected){assert.equal((await record(name,id)).values.estado,expected)}
function equalValues(actual,expected){for(const [key,value] of Object.entries(expected))assert.equal(typeof value==='number'?Number(actual[key]):actual[key],value,key)}

try{
  for(const [institution,scenario] of Object.entries(scenarios)){
    data=scenario;resources=data.resources
    await login(institution)
    for(const c of data.catalogues){
      const row=await create(c.resource,c.values)
      equalValues((await record(c.resource,row.id)).values,c.values)
      await update(c.resource,row.id,c.edit)
      equalValues((await record(c.resource,row.id)).values,c.edit)
      assert.ok(Object.keys(c.deactivate).length,'Catalogue has a deactivation task')
      await update(c.resource,row.id,c.deactivate)
      equalValues((await record(c.resource,row.id)).values,c.deactivate)
      mark(`catalogue:${institution}:${c.resource}:create-edit-deactivate`)
    }
    await screenshot(institution+'-catalogues')
    const refs=Object.fromEntries(Object.entries(data.references).map(([n,r])=>[n,r.id]))
    const appointmentValues=institution==='hospital'?{id_paciente:refs.paciente,id_medico:refs.medico,fecha_hora:'2020-03-01T12:00:00Z'}:
      institution==='pediatrico'?{paciente_id:refs.paciente,medico_id:refs.medico,fecha:'2020-03-01',hora:'06:00',motivo:'DEMO A8'}:
      {paciente_id:refs.paciente,profesional_id:refs.profesional,fecha_hora:'2020-03-01T12:00:00Z',motivo:'DEMO A8'}
    const appointment=await create('cita',appointmentValues)
    await update('cita',appointment.id,institution==='pediatrico'?{fecha:'2020-03-02',hora:'07:00'}:{fecha_hora:'2020-03-02T13:00:00Z'})
    await locate('cita',appointment.id);await click('Atender cita',rowSelector(appointment.id))
    await wait(`!!document.querySelector('#consultation-notas')`)
    await fill('#consultation-fecha','2020-03-02');await fill('#consultation-notas','DEMO A8 cita atendida '+institution)
    const consultation=await save(201,'Guardar consulta')
    assert.equal(consultation.cita_id,appointment.id)
    const history=await api(`pacientes/${encodeURIComponent(refs.paciente)}/historial/`)
    assert.ok(history.consultas.some(c=>c.cita_id===appointment.id),'Consultation persisted with appointment')
    await click('Inicio y operaciones');await state('cita',appointment.id,'atendida')
    const cancelled=await create('cita',appointmentValues)
    await update('cita',cancelled.id,{estado:'cancelada'});await state('cita',cancelled.id,'cancelada')
    await locate('cita',cancelled.id)
    assert.equal(await evaluate(`[...document.querySelectorAll(${JSON.stringify(rowSelector(cancelled.id)+' button')})].some(e=>e.textContent==='Atender cita')`),false)
    mark(`agenda:${institution}:create-reschedule-attend-cancel`);await screenshot(institution+'-agenda')

    if(institution==='hospital'||institution==='pediatrico'){
      if(institution==='pediatrico'){
        const policy=await create('poliza_paciente',{paciente_id:refs.paciente,plan_seguro_id:refs.plan_seguro,numero_poliza:'DEMO-A8-UI-POLIZA',estado:'activo',fecha_inicio:'2020-01-01',fecha_fin:'2027-01-01'})
        await state('poliza_paciente',policy.id,'activo')
        await update('poliza_paciente',policy.id,{fecha_fin:'2019-12-31'},400)
        await update('poliza_paciente',policy.id,{fecha_fin:'2028-01-01',numero_afiliado:'DEMO-A8-AFILIADO'})
        refs.poliza_paciente=policy.id
        mark('insurance:pediatrico:policy-create-edit-invalid-dates')
      }
      const hospital=institution==='hospital',bill=await create('factura',hospital?{id_paciente:refs.paciente,id_consulta:refs.consulta}:{paciente_id:refs.paciente,consulta_id:refs.consulta})
      const detail=hospital?{id_factura:bill.id,concepto:'DEMO A8 concepto',precio_unitario:'20.00',cantidad:1}:
        {factura_id:bill.id,servicio_id:refs.servicio_medico,precio_unitario:'20.00',cantidad:1,monto_cubierto:'10.00'}
      await create('detalle_factura',detail);await action('factura',bill.id,'Emitir factura')
      const pay=amount=>create('pago',hospital?{id_factura:bill.id,monto:amount,metodo_pago:'Efectivo'}:
        {factura_id:bill.id,metodo_pago_id:refs.metodo_pago,monto:amount,tipo_pagador:'paciente'})
      const first=await pay(hospital?'12.00':'6.00');await state('factura',bill.id,hospital?'Parcial':'parcial')
      await open('detalle_factura');await click('Nuevo registro');await form(detail,'detalle_factura');await save(409)
      const second=await pay(hospital?'8.00':'4.00')
      let authorization,claim
      if(!hospital){
        await state('factura',bill.id,'parcial')
        authorization=await create('autorizacion_seguro',{poliza_paciente_id:refs.poliza_paciente,consulta_id:refs.consulta,numero_autorizacion:'DEMO-A8-AUTH'})
        await update('autorizacion_seguro',authorization.id,{estado:'aprobado',monto_autorizado:'10.00'})
        claim=await create('reclamacion_seguro',{factura_id:bill.id,poliza_paciente_id:refs.poliza_paciente,autorizacion_id:authorization.id,numero_reclamo:'DEMO-A8-CLAIM',monto_reclamado:'10.00'})
        await update('reclamacion_seguro',claim.id,{estado:'aprobado',monto_aprobado:'10.00'})
        await update('autorizacion_seguro',authorization.id,{estado:'anulado'},400)
        const recovery=await create('pago',{factura_id:bill.id,metodo_pago_id:refs.metodo_pago,monto:'10.00',tipo_pagador:'aseguradora'})
        await state('factura',bill.id,'pagada')
        await action('pago',recovery.id,'Revertir pago');await state('factura',bill.id,'parcial')
        await update('reclamacion_seguro',claim.id,{estado:'anulado'})
        await update('autorizacion_seguro',authorization.id,{estado:'anulado'})
        mark('states:pediatrico:authorization-claim-approve-dependent-cancel')
        const rejectedAuthorization=await create('autorizacion_seguro',{poliza_paciente_id:refs.poliza_paciente,consulta_id:refs.consulta,numero_autorizacion:'DEMO-A8-AUTH-REJECT'})
        await update('autorizacion_seguro',rejectedAuthorization.id,{estado:'rechazado'})
        const rejectedClaim=await create('reclamacion_seguro',{factura_id:bill.id,poliza_paciente_id:refs.poliza_paciente,numero_reclamo:'DEMO-A8-CLAIM-REJECT',monto_reclamado:'10.00'})
        await update('reclamacion_seguro',rejectedClaim.id,{estado:'rechazado'})
        mark('states:pediatrico:authorization-claim-reject')
      }else await state('factura',bill.id,'Pagada')
      await action('factura',bill.id,'Anular factura',400)
      await action('pago',first.id,'Revertir pago');await action('pago',second.id,'Revertir pago')
      await action('factura',bill.id,'Anular factura');await state('factura',bill.id,hospital?'Anulada':'anulada')
      equalValues((await record('factura',bill.id)).financial,{saldo_paciente:'0.00',saldo_seguro:'0.00'})
      mark(`finance:${institution}:issue-partial-total-reverse-annul`);await screenshot(institution+'-finance')
    }
    if(institution==='hospital'){
      const values={id_ingreso:refs.ingreso_hospitalario,id_quirofano:refs.quirofano,fecha_hora_inicio:'2020-01-01T14:00:00Z',fecha_hora_fin:'2020-01-01T15:00:00Z'}
      const surgery=await create('cirugia',values)
      await update('cirugia',surgery.id,{estado:'realizado'},400)
      await create('equipo_quirurgico',{id_cirugia:surgery.id,id_medico:refs.medico,rol_en_cirugia:'DEMO A8'})
      await update('cirugia',surgery.id,{estado:'realizado'});await state('cirugia',surgery.id,'realizado')
      const cancelled=await create('cirugia',{...values,fecha_hora_inicio:'2020-01-01T16:00:00Z',fecha_hora_fin:'2020-01-01T17:00:00Z'})
      await update('cirugia',cancelled.id,{estado:'cancelado'})
      mark('states:hospital:surgery-team-complete-cancel')
    }
    if(institution==='pediatrico'){
      const exam=await create('examen',{consulta_id:refs.consulta,tipo_examen_id:refs.tipo_examen})
      await update('examen',exam.id,{estado:'en_proceso'})
      await update('examen',exam.id,{estado:'finalizado'},400)
      const result=await create('resultado_examen',{examen_id:exam.id,valor:'DEMO A8',estado:'pendiente'})
      await update('resultado_examen',result.id,{estado:'en_proceso'})
      await update('resultado_examen',result.id,{estado:'finalizado'});await state('examen',exam.id,'finalizado')
      const other=await create('examen',{consulta_id:refs.consulta,tipo_examen_id:refs.tipo_examen})
      await update('examen',other.id,{estado:'anulado'})
      mark('states:pediatrico:exam-result-complete-cancel')
      const pendingExam=await create('examen',{consulta_id:refs.consulta,tipo_examen_id:refs.tipo_examen})
      const pendingResult=await create('resultado_examen',{examen_id:pendingExam.id,valor:'DEMO A8 cancelar',estado:'pendiente'})
      await update('resultado_examen',pendingResult.id,{estado:'en_proceso'})
      await update('resultado_examen',pendingResult.id,{estado:'anulado'})
      await update('examen',pendingExam.id,{estado:'anulado'})
      mark('states:pediatrico:result-in-process-cancel-exam-cancel')
    }
    if(institution==='laboratorio'||institution==='odontologica'){
      const name=institution==='laboratorio'?'resultado':'procedimiento'
      if(name==='resultado')await update(name,data.pending[0],{estado:'en_proceso'})
      await update(name,data.pending[0],{estado:name==='resultado'?'finalizado':'realizado'})
      await update(name,data.pending[1],{estado:'anulado'})
      if(name==='resultado'){
        await update(name,data.pending[2],{estado:'en_proceso'})
        await update(name,data.pending[2],{estado:'anulado'})
      }
      for(const id of data.pending.slice(0,name==='resultado'?3:2)){
        await locate(name,id)
        assert.equal(await evaluate(`[...document.querySelectorAll(${JSON.stringify(rowSelector(id)+' button')})].some(e=>e.textContent==='Editar')`),false)
      }
      mark(`states:${institution}:complete-existing-cancel-existing`)
    }
    await screenshot(institution+'-states');await click('Cerrar sesión');await wait(`!!document.querySelector('#username')`)
    await login(institution)
    await click('Usuarios y permisos','.workspace-nav');await wait(`!!document.querySelector('.resource-panel h2')`)
    await click('Crear usuario')
    const username='DEMO-A8-created-'+institution
    await wait(`[...document.querySelector('[name="rol"]').options].some(o=>o.value==='secretaria')`)
    await fill('[name="username"]',username);await fill('[name="password"]',process.env.AUC_TEST_PASSWORD);await fill('[name="rol"]','secretaria')
    const accountSubmit=async(expected)=>{
      const before=await evaluate('window.__aucWrites.length')
      await evaluate(`document.querySelector('.resource-panel form').requestSubmit()`)
      await wait(`window.__aucWrites.length>${before}`)
      const response=await evaluate(`window.__aucWrites[${before}]`)
      assert.equal(response.status,expected,JSON.stringify(response.body))
      await wait(`!document.querySelector('.resource-panel form')`)
      return response.body
    }
    const account=await accountSubmit(201)
    const accountRow=async()=>{
      await wait(`!![...document.querySelectorAll('.resource-panel li')].find(e=>e.querySelector('strong')?.textContent===${JSON.stringify(username)})`)
      await evaluate(`[...document.querySelectorAll('.resource-panel li')].find(e=>e.querySelector('strong')?.textContent===${JSON.stringify(username)}).setAttribute('data-auc-account','created')`)
    }
    await accountRow();await click('Vincular profesional','[data-auc-account="created"]')
    await wait(`document.querySelector('[name="profesional_id"]')?.options.length>1`)
    await fill('[name="profesional_id"]',refs[institution==='hospital'||institution==='pediatrico'?'medico':'profesional'])
    const bound=await accountSubmit(200);assert.ok(bound.profesional_id)
    for(const label of ['Desactivar','Activar']){
      await accountRow();const before=await evaluate('window.__aucWrites.length')
      await click(label,'[data-auc-account="created"]');await wait(`window.__aucWrites.length>${before}`)
      const response=await evaluate(`window.__aucWrites[${before}]`);assert.equal(response.status,200)
      assert.equal(response.body.activo,label==='Activar')
      await wait(`[...document.querySelectorAll('.resource-panel li')].find(e=>e.querySelector('strong')?.textContent===${JSON.stringify(username)})?.innerText.includes(${JSON.stringify(label==='Activar'?'Desactivar':'Activar')})`)
    }
    assert.equal((await api('operaciones/cuentas/')).results.find(r=>r.id===account.id).activo,true)
    mark(`accounts:${institution}:create-bind-deactivate-reactivate`)
    await click('Cerrar sesión');await wait(`!!document.querySelector('#username')`)
    for(const [role,manifest] of Object.entries(data.roles)){
      await login(institution,role)
      const visible=await evaluate(`[...document.querySelectorAll('.task-card strong')].map(e=>e.textContent).sort()`)
      assert.deepEqual(visible,manifest.resources.filter(r=>r.create||r.key==='paciente').map(r=>r.label).sort())
      assert.equal(await evaluate(`[...document.querySelectorAll('.workspace-nav button')].some(e=>e.textContent==='Usuarios y permisos')`),role==='admin')
      for(const group of new Set(manifest.resources.map(r=>r.group))){
        await click(group,'.workspace-nav')
        await wait(`JSON.stringify([...document.querySelectorAll('.task-card strong')].map(e=>e.textContent).sort())===${JSON.stringify(JSON.stringify(manifest.resources.filter(r=>r.group===group).map(r=>r.label).sort()))}`)
        assert.deepEqual(await evaluate(`[...document.querySelectorAll('.task-card strong')].map(e=>e.textContent).sort()`),manifest.resources.filter(r=>r.group===group).map(r=>r.label).sort())
      }
      if(role==='secretaria'){
        const values=institution==='pediatrico'?{...appointmentValues,fecha:'2020-03-04',hora:'08:00'}:{...appointmentValues,fecha_hora:'2020-03-04T14:00:00Z'}
        const scheduled=await create('cita',values)
        await update('cita',scheduled.id,institution==='pediatrico'?{fecha:'2020-03-05',hora:'09:00'}:{fecha_hora:'2020-03-05T15:00:00Z'})
        await update('cita',scheduled.id,{estado:'cancelada'});await state('cita',scheduled.id,'cancelada')
        mark(`role-write:${institution}:secretaria-agenda`)
        if(institution==='hospital'||institution==='pediatrico'){
          const hospital=institution==='hospital'
          const bill=await create('factura',hospital?{id_paciente:refs.paciente,id_consulta:refs.consulta}:{paciente_id:refs.paciente,consulta_id:refs.consulta})
          await create('detalle_factura',hospital?{id_factura:bill.id,concepto:'DEMO A8 secretaria',precio_unitario:'5.00',cantidad:1}:
            {factura_id:bill.id,servicio_id:refs.servicio_medico,precio_unitario:'5.00',cantidad:1,monto_cubierto:'0.00'})
          await action('factura',bill.id,'Emitir factura')
          const payment=await create('pago',hospital?{id_factura:bill.id,monto:'5.00',metodo_pago:'Efectivo'}:
            {factura_id:bill.id,metodo_pago_id:refs.metodo_pago,monto:'5.00',tipo_pagador:'paciente'})
          await state('factura',bill.id,hospital?'Pagada':'pagada')
          await action('pago',payment.id,'Revertir pago');await action('factura',bill.id,'Anular factura')
          mark(`role-write:${institution}:secretaria-cash`)
        }
      }
      if(role==='medico'){
        const values=institution==='pediatrico'?{...appointmentValues,fecha:'2020-03-06',hora:'06:00'}:{...appointmentValues,fecha_hora:'2020-03-06T12:00:00Z'}
        const scheduled=await create('cita',values)
        await locate('cita',scheduled.id);await click('Atender cita',rowSelector(scheduled.id))
        await wait(`!!document.querySelector('#consultation-notas')`)
        await fill('#consultation-fecha','2020-03-06');await fill('#consultation-notas','DEMO A8 medico '+institution)
        const consultation=await save(201,'Guardar consulta');assert.equal(consultation.cita_id,scheduled.id)
        await click('Inicio y operaciones');await state('cita',scheduled.id,'atendida')
        mark(`role-write:${institution}:medico-attend`)
      }
      if(role==='enfermero'&&(institution==='hospital'||institution==='pediatrico')){
        await create('signos_vitales',institution==='hospital'?{id_ingreso:refs.ingreso_hospitalario,id_enfermero:refs.enfermero,frecuencia_cardiaca:75,oximetria:98}:
          {consulta_id:refs.consulta,frecuencia_cardiaca:75,saturacion_oxigeno:98})
        mark(`role-write:${institution}:enfermero-vitals`)
      }
      if(role==='laboratorista'){
        await update('resultado',data.pending[3],{estado:'en_proceso'})
        await update('resultado',data.pending[3],{estado:'finalizado'});await state('resultado',data.pending[3],'finalizado')
        mark('role-write:laboratorio:laboratorista-result')
      }
      await click('Cerrar sesión');await wait(`!!document.querySelector('#username')`)
      mark(`role-ui:${institution}:${role}`)
    }
  }
  assert.deepEqual(b.exceptions,[])
  const writes=await evaluate('window.__aucWrites.map(({url,method,status})=>({url,method,status}))')
  assert.ok(writes.every(w=>['POST','PATCH'].includes(w.method)))
  await writeFile('/checks/browser-report.json',JSON.stringify({passed:results.length,failed:0,write_requests:writes.length,
    successful_writes:writes.filter(w=>w.status<300).length,expected_rejections:writes.filter(w=>w.status>=400).length,results,writes},null,2))
  console.log(`AUC-08 browser: ${results.length} scenarios passed`)
}catch(error){
  await screenshot('failure').catch(()=>{})
  await writeFile('/checks/browser-report.json',JSON.stringify({passed:results.length,failed:1,error:String(error.stack),exceptions:b.exceptions,results},null,2))
  throw error
}finally{await b.close()}
