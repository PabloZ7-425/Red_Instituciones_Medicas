// Smoke real sin dependencias npm adicionales. Requiere Node 22+ y Chromium.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as pause } from 'node:timers/promises'

assert.equal(process.env.A5_REAL_HTTP, '1', 'A5 debe activarse explícitamente')
const url = process.env.BROWSER_URL ?? 'http://127.0.0.1:18175/'
assert.equal(new URL(url).port, '18175', 'Solo frontend operativo dedicado')
const accountPassword = process.env.A5_BROWSER_PASSWORD
assert.ok(accountPassword, 'Se requiere contraseña de las cuentas DEMO A5 locales')
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(url).hostname), 'Solo probar entorno local DEMO')
const profile = await mkdtemp(join(tmpdir(), 'jennifer-ui-'))
const browser = spawn(process.env.CHROMIUM_PATH ?? 'chromium', [
  '--headless', '--no-sandbox', '--disable-gpu', '--remote-debugging-port=0',
  '--remote-debugging-address=127.0.0.1', `--user-data-dir=${profile}`, 'about:blank',
], { stdio: 'ignore' })
let launchError
browser.on('error', error => { launchError = error })
let socket
const pending = new Map()
try {
  let port
  for (let attempt = 0; attempt < 100; attempt++) {
    if (launchError) throw launchError
    try { port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; break } catch { await pause(100) }
  }
  assert.ok(port, 'Chromium no inició')
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }) })
  let id = 0
  const exceptions = []
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text)
    const task = pending.get(message.id)
    if (!task) return
    pending.delete(message.id); clearTimeout(task.timeout)
    if (message.error) task.reject(new Error(message.error.message)); else task.resolve(message.result)
  })
  function command(method, params = {}) {
    return new Promise((resolve, reject) => {
      const requestId = ++id
      const timeout = setTimeout(() => { pending.delete(requestId); reject(new Error(`Timeout: ${method}`)) }, 10000)
      pending.set(requestId, { resolve, reject, timeout })
      socket.send(JSON.stringify({ id: requestId, method, params }))
    })
  }
  async function evaluate(expression) {
    const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text)
    return result.result.value
  }
  async function wait(expression) {
    for (let attempt = 0; attempt < 100; attempt++) {
      if (await evaluate(expression)) return
      await pause(50)
    }
    throw new Error(`No se cumplió: ${expression}`)
  }
  const textHas = text => `(document.body?.innerText ?? '').includes(${JSON.stringify(text)})`
  const rawFill = (selector, value) => evaluate(`(() => {
    const input = document.querySelector(${JSON.stringify(selector)});
    const prototype = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, 'value').set.call(input, ${JSON.stringify(value)});
    input.dispatchEvent(new Event('input', { bubbles: true }));
    if (input instanceof HTMLSelectElement) input.dispatchEvent(new Event('change', { bubbles: true }));
  })()`)
  const rawClick = async label => {
    await wait(`!![...document.querySelectorAll('button')].find(b => b.textContent.trim() === ${JSON.stringify(label)} && !b.disabled)`);
    return evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find(element => element.textContent.trim() === ${JSON.stringify(label)});
    if (!button || button.disabled) throw new Error('Botón no disponible'); button.click();
  })()`)
  }
  let metric=null
  const fill=async (selector,value)=>{if(metric){metric.actions++;metric.fields.add(selector);metric.events.push({kind:'field',selector})}return rawFill(selector,value)}
  const click=async label=>{if(metric){metric.actions++;metric.events.push({kind:'button',label})}return rawClick(label)}
  await command('Runtime.enable')
  await command('Page.navigate', { url })
  const card=async label=>{await wait(`!![...document.querySelectorAll('.task-card strong')].find(e=>e.textContent===${JSON.stringify(label)})`);await evaluate(`(()=>{[...document.querySelectorAll('.task-card')].find(e=>e.querySelector('strong').textContent===${JSON.stringify(label)}).click()})()`)}
  const apiBase='http://127.0.0.1:18015/api/'
  const api=async (route,body)=>evaluate(`(async()=>{
    const token=document.cookie.split('; ').find(c=>c.startsWith('csrftoken='))?.split('=')[1];
    const r=await fetch(${JSON.stringify(apiBase)}+${JSON.stringify(route)},{method:${JSON.stringify(body?'POST':'GET')},credentials:'include',headers:{'Content-Type':'application/json','X-CSRFToken':token},${body?'body:'+JSON.stringify(JSON.stringify(body)):''}});
    const value=await r.json();if(!r.ok)throw new Error('Fixture/verification API '+r.status+' '+JSON.stringify(value));return value;
  })()`)
  const select=async (selector,label='')=>{
    await wait(`!![...document.querySelector(${JSON.stringify(selector)})?.options??[]].find(o=>o.value&&o.textContent.includes(${JSON.stringify(label)}))`)
    await fill(selector,await evaluate(`[...document.querySelector(${JSON.stringify(selector)}).options].find(o=>o.value&&o.textContent.includes(${JSON.stringify(label)})).value`))
  }
  const reports=[]
  const scenarios=[['hospital','atencion'],['pediatrico','vacuna'],['hospital','ingreso'],['hospital','traslado'],['laboratorio','resultado'],['hospital','pago']]
  for(const [institution,scenario] of scenarios)for(const mode of ['manual_controlado','asistido']) {
    await wait(textHas('Iniciar sesión'))
    await fill('#username',`DEMO-OPS-admin-${institution}`);await fill('#password',accountPassword);await click('Ingresar')
    await wait(textHas('¿Qué necesitas hacer?'));await click('Pacientes y expedientes');await click('Nuevo paciente')
    const tag='AUC11-'+crypto.randomUUID().slice(0,8)
    await fill('#patient-identificacion',tag);await fill('#patient-nombres','DEMO eficiencia');await fill('#patient-apellidos',tag);await fill('#patient-fecha_nacimiento','2000-01-01')
    await evaluate(`document.querySelector('.patient-form form').requestSubmit()`);await wait(textHas('No hay consultas registradas.'))
    const patient=(await api('pacientes/?q='+tag+'&limit=20&offset=0')).results[0].id
    let bed,admission,bill
    if(['ingreso','traslado'].includes(scenario)) {
      const room=(await api('operaciones/habitacion/?limit=20&offset=0')).results[0].id
      bed=(await api('operaciones/cama/',{id_habitacion:room,codigo_cama:tag,estado_limpieza:'limpia'})).id
      if(scenario==='traslado') {
        const initial=(await api('operaciones/cama/',{id_habitacion:room,codigo_cama:tag+'-ORIGEN',estado_limpieza:'limpia'})).id
        admission=(await api(`pacientes/${patient}/ingresos/nuevo/`,{cama_id:initial,fecha_hora_ingreso:'2020-01-01T12:00:00Z',tipo_ingreso:'DEMO eficiencia'})).id
      }
    }
    if(scenario==='pago') {
      bill=(await api('operaciones/factura/',{id_paciente:patient})).id
      await api('operaciones/detalle_factura/',{id_factura:bill,concepto:'DEMO eficiencia',cantidad:1,precio_unitario:'12.50'})
    }
    // Identical task boundary: patient and prerequisites ready, task not opened.
    metric={institution,scenario,mode,actions:0,fields:new Set(),events:[],errors:0,backtracks:0,time_seconds:null}
    const defaultField=async selector=>{
      await wait(`!!document.querySelector(${JSON.stringify(selector)})?.value`)
      const value=await evaluate(`document.querySelector(${JSON.stringify(selector)}).value`)
      if(mode==='manual_controlado') {
        // Disable only the observed convenience in this control case. Clearing
        // is test setup, outside the recorded user actions, never app behavior.
        await rawFill(selector,'');await fill(selector,value)
      }
      return value
    }
    const saveSpecialty=async()=>{await click('Guardar especialización');await wait(`!document.querySelector('dialog[open]')`)}
    if(scenario==='atencion') {
      await click('Nueva consulta');await defaultField('#consultation-fecha')
      await fill('#consultation-notas','DEMO eficiencia');await click('Guardar consulta')
      await wait(`!document.querySelector('#consultation-notas')`)
      assert.equal((await api(`pacientes/${patient}/historial/`)).consultas.length,1)
    } else if(['vacuna','ingreso','resultado'].includes(scenario)) {
      await click('Seguimiento institucional')
      await click({vacuna:'Registrar vacuna',ingreso:'Registrar ingreso',resultado:'Registrar resultado'}[scenario])
      if(scenario==='vacuna') {
        await select('[name="vacuna_id"]','DEMO vacuna A4');await defaultField('[name="fecha"]');await fill('[name="dosis"]','1')
      } else if(scenario==='ingreso') {
        await select('[name="cama_id"]',tag);await defaultField('[name="fecha_hora_ingreso"]');await fill('[name="tipo_ingreso"]','DEMO eficiencia')
      } else {
        await select('[name="tipo_examen"]','DEMO examen A4');await defaultField('[name="fecha"]');await fill('[name="estado"]','finalizado')
        await fill('dialog[open] fieldset > fieldset label:nth-of-type(1) input','DEMO campo')
        await fill('dialog[open] fieldset > fieldset label:nth-of-type(3) input','DEMO resultado')
      }
      await saveSpecialty()
      const [route,key]=({vacuna:['seguimiento','vacunas'],ingreso:['ingresos','ingresos'],resultado:['resultados','resultados']})[scenario]
      assert.equal((await api(`pacientes/${patient}/${route}/`))[key].length,1)
    } else {
      await click('Inicio y operaciones');await click(scenario==='traslado'?'Hospitalización':'Caja y seguros')
      // Task card selection is an action too (same boundary in both modes).
      metric.actions++;metric.events.push({kind:'task',label:scenario})
      await card(scenario==='traslado'?'Traslados de cama':'Pagos');await click('Nuevo registro')
      if(scenario==='traslado') {
        await select('#operation-id_ingreso');await select('#operation-id_cama',tag)
        await defaultField('#operation-fecha_hora_inicio');await fill('#operation-motivo_traslado','DEMO eficiencia')
      } else {
        await select('#operation-id_factura')
        await defaultField('#operation-fecha_hora_pago');await defaultField('#operation-referencia_pago')
        assert.equal(await evaluate(`document.querySelector('#operation-monto').value`),'12.50')
        await defaultField('#operation-monto');await fill('#operation-metodo_pago','Efectivo')
      }
      await click('Guardar registro');await wait(`!document.querySelector('dialog[open]')`);await wait(textHas('Registro guardado correctamente.'))
      assert.equal((await api(`operaciones/${scenario==='traslado'?'movimiento_cama':'pago'}/?patient=${patient}&limit=20&offset=0`)).count,scenario==='traslado'?2:1)
    }
    // Read validation messages after a successful persisted task. No failed
    // submit or backtrack is intentionally injected in either controlled path.
    metric.errors=await evaluate(`document.querySelectorAll('[role="alert"]').length`)
    assert.equal(metric.errors,0)
    reports.push({...metric,fields_entered:metric.fields.size,fields:undefined,persisted:true});metric=null
    await click('Cerrar sesión')
    console.log(`OK eficiencia HTTP ${scenario} / ${mode}`)
  }
  assert.deepEqual(exceptions,[])
  const pairs=scenarios.map(([,scenario])=>{
    const manual=reports.find(r=>r.scenario===scenario&&r.mode==='manual_controlado')
    const assisted=reports.find(r=>r.scenario===scenario&&r.mode==='asistido')
    assert.ok(assisted.actions<manual.actions);assert.ok(assisted.fields_entered<manual.fields_entered)
    return {scenario,manual_actions:manual.actions,assisted_actions:assisted.actions,manual_fields:manual.fields_entered,assisted_fields:assisted.fields_entered,errors:[manual.errors,assisted.errors],backtracks:[manual.backtracks,assisted.backtracks],time_seconds:null}
  })
  const output={method:'Controlled automated UI comparison in the same version; manual control clears and re-enters observed prefills. Not a historical UI or human productivity/time benchmark.',boundary:'Patient and prerequisites ready; includes opening task, field adjustments and submit; excludes login/catalog setup and verification requests.',pairs,runs:reports}
  assert.ok(process.env.AUC11_REPORT,'Private report path required')
  await writeFile(process.env.AUC11_REPORT,JSON.stringify(output,null,2)+'\n')
} finally {
  for(const task of pending.values()){clearTimeout(task.timeout);task.reject(new Error('Navegador cerrado'))}
  socket?.close();browser.kill('SIGTERM')
}
