// Smoke real sin dependencias npm adicionales. Requiere Node 22+ y Chromium.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile } from 'node:fs/promises'
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
  const fill = (selector, value) => evaluate(`(() => {
    const input = document.querySelector(${JSON.stringify(selector)});
    const prototype = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, 'value').set.call(input, ${JSON.stringify(value)});
    input.dispatchEvent(new Event('input', { bubbles: true }));
    if (input instanceof HTMLSelectElement) input.dispatchEvent(new Event('change', { bubbles: true }));
  })()`)
  const click = async label => {
    await wait(`!![...document.querySelectorAll('button')].find(b => b.textContent.trim() === ${JSON.stringify(label)} && !b.disabled)`);
    return evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find(element => element.textContent.trim() === ${JSON.stringify(label)});
    if (!button || button.disabled) throw new Error('Botón no disponible'); button.click();
  })()`)
  }
  await command('Runtime.enable')
  await command('Page.navigate', { url })
  const card=async label=>{await wait(`!![...document.querySelectorAll('.task-card strong')].find(e=>e.textContent===${JSON.stringify(label)})`);await evaluate(`(()=>{[...document.querySelectorAll('.task-card')].find(e=>e.querySelector('strong').textContent===${JSON.stringify(label)}).click()})()`)}
  for(const institution of ['hospital','pediatrico','laboratorio','odontologica']) {
    await wait(textHas('Iniciar sesión'))
    await fill('#username',`DEMO-OPS-admin-${institution}`)
    await fill('#password',accountPassword)
    await click('Ingresar')
    await wait(textHas('¿Qué necesitas hacer?'))
    await click('Catálogos')
    await card('Medicamentos')
    await wait(`!!document.querySelector('.resource-panel table')`)
    await click('Nuevo registro')
    await wait(`!!document.querySelector('dialog[open]')`)
    assert.equal(await evaluate(`document.querySelectorAll('dialog[open]').length`),1)
    const name=institution==='hospital'?'nombre_comercial':'nombre'
    await fill(`#operation-${name}`,`DEMO Browser ${institution}`)
    if(institution==='hospital'){await fill('#operation-principio_activo','DEMO no administrar');await fill('#operation-stock_farmacia','5')}
    await fill('#operation-presentacion','DEMO presentación')
    await click('Guardar registro')
    await wait(textHas('Registro guardado correctamente.'))
    await fill('#operation-search',`DEMO Browser ${institution}`)
    await click('Buscar')
    await wait(textHas('1 registros'))
    await wait(`!!document.querySelector('tbody tr')`)
    await click('Editar')
    await wait(`!!document.querySelector('dialog[open]')`)
    await fill('#operation-presentacion','DEMO presentación actualizada')
    await click('Guardar registro')
    await wait(textHas('DEMO presentación actualizada'))
    assert.equal(await evaluate(`document.querySelectorAll('dialog[open]').length`),0)
    if(institution==='hospital') {
      const select = async (selector, label='') => {
        await wait(`!![...document.querySelector(${JSON.stringify(selector)})?.options??[]].find(o=>o.value&&o.textContent.includes(${JSON.stringify(label)}))`)
        await fill(selector,await evaluate(`[...document.querySelector(${JSON.stringify(selector)}).options].find(o=>o.value&&o.textContent.includes(${JSON.stringify(label)})).value`))
      }
      const save = async () => {await click('Guardar registro');await wait(`!document.querySelector('dialog[open]')`);await wait(textHas('Registro guardado correctamente.'))}
      await click('Pacientes y expedientes')
      await click('Nuevo paciente')
      await fill('#patient-identificacion','DEMO-AUC-BROWSER')
      await fill('#patient-nombres','Persona AUC')
      await fill('#patient-apellidos','Sintética')
      await fill('#patient-fecha_nacimiento','2000-01-01')
      await evaluate(`document.querySelector('.patient-form form').requestSubmit()`)
      await wait(textHas('No hay consultas registradas.'))
      await click('Seguimiento institucional')
      await click('Registrar ingreso')
      await select('[name="cama_id"]')
      await fill('[name="fecha_hora_ingreso"]','2020-01-01T12:00:00')
      await fill('[name="tipo_ingreso"]','DEMO ingreso AUC')
      await click('Guardar especialización')
      await wait(textHas('DEMO ingreso AUC'))
      await click('Inicio y operaciones')
      await click('Hospitalización')
      await card('Diagnósticos de hospitalización')
      await click('Nuevo registro')
      await select('#operation-id_ingreso')
      await fill('#operation-codigo_cie10','DEMO')
      await fill('#operation-descripcion','DEMO diagnóstico de ingreso AUC')
      await save()
      await click('Continuar con tratamientos →')
      await click('Nuevo registro')
      await select('#operation-id_diagnostico','DEMO diagnóstico de ingreso AUC')
      await fill('#operation-indicaciones_generales','DEMO tratamiento de ingreso AUC')
      await save()
      await click('Continuar con prescripciones →')
      await click('Nuevo registro')
      await select('#operation-id_tratamiento','DEMO tratamiento de ingreso AUC')
      await select('#operation-id_medicamento','DEMO Browser hospital')
      await fill('#operation-dosis','DEMO sin uso clínico')
      await fill('#operation-frecuencia','DEMO')
      await save()
      await click('Continuar con despachos de farmacia →')
      await click('Nuevo registro')
      await select('#operation-id_receta')
      await fill('#operation-cantidad_entregada','2')
      await save()
      await click('Pacientes y expedientes')
      await click('Seguimiento institucional')
      await click('Registrar alta hospitalaria')
      await select('[name="ingreso_id"]')
      await fill('[name="fecha_hora_alta"]','2020-01-02T12:00:00')
      await click('Guardar especialización')
      await wait(textHas('2020-01-02 12:00:00'))
      await click('Inicio y operaciones')
      console.log('OK hospitalización HTTP: ingreso → diagnóstico → tratamiento → prescripción → despacho → alta, sin consulta ficticia')
    }
    await click('Agenda')
    await card('Agenda de citas')
    await click('Nuevo registro')
    const dateField=institution==='pediatrico'?'fecha':'fecha_hora'
    await wait(`!!document.querySelector('#operation-${dateField}')`)
    assert.ok(await evaluate(`document.querySelector('#operation-${dateField}').value`),'Fecha/hora prellenada')
    assert.ok(await evaluate(`document.querySelectorAll('dialog[open] select').length>=2`),'Relaciones seleccionables por nombre')
    await click('Cancelar')
    await click('Usuarios y permisos')
    await wait(textHas(`DEMO-OPS-admin-${institution}`))
    await click('Vincular profesional')
    await wait(`document.querySelector('[name="profesional_id"]')?.options.length>1`)
    await fill('[name="profesional_id"]',await evaluate(`document.querySelector('[name="profesional_id"]').options[1].value`))
    await click('Guardar vínculo')
    await wait(`!document.querySelector('[name="profesional_id"]')`)
    await click('Cerrar sesión')
    await wait(textHas('Iniciar sesión'))
    console.log(`OK operaciones HTTP: navegación/catálogo/edición/búsqueda/fecha automática/usuarios/logout — ${institution}`)
  }
  assert.deepEqual(exceptions, [], 'Sin excepciones JavaScript')
} finally {
  for (const task of pending.values()) { clearTimeout(task.timeout); task.reject(new Error('Navegador cerrado')) }
  socket?.close()
  browser.kill('SIGTERM')
}
