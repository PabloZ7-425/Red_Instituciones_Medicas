// Smoke real sin dependencias npm adicionales. Requiere Node 22+ y Chromium.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as pause } from 'node:timers/promises'

const url = process.env.BROWSER_URL ?? 'http://127.0.0.1:5173/'
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
  const click = label => evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find(element => element.textContent.trim() === ${JSON.stringify(label)});
    if (!button || button.disabled) throw new Error('Botón no disponible'); button.click();
  })()`)
  await command('Runtime.enable')
  await command('Page.navigate', { url })
  await wait(textHas('Iniciar sesión'))
  assert.ok(await evaluate(textHas('DEMO · Datos ficticios')), 'Smoke exige modo mock explícito')
  for (const [institution, heading] of [
    ['hospital', 'Hospital'], ['pediatrico', 'Clínica Pediátrica'],
    ['laboratorio', 'Laboratorio Clínico'], ['odontologica', 'Clínica Odontológica'],
  ]) {
    await fill('#username', `DEMO-medico-${institution}`)
    await fill('#password', 'DEMO-no-utilizar')
    await click('Ingresar')
    await wait(textHas('1 pacientes encontrados'))
    assert.ok(await evaluate(`!![...document.querySelectorAll('h2')].find(h => h.textContent === ${JSON.stringify(heading)})`))
    assert.equal(await evaluate(`document.querySelector('input[type="password"]') === null`), true)
    await fill('#search', 'sin-coincidencias')
    await click('Buscar')
    await wait(textHas('No hay pacientes que coincidan'))
    await fill('#search', ' PAC ')
    await click('Buscar')
    await wait(textHas('1 pacientes encontrados'))
    await click('Ver historial')
    await wait(textHas('Consulta sintética DEMO'))
    assert.ok(await evaluate(textHas('2001-02-03')))
    assert.ok(await evaluate(textHas('Evaluación sintética DEMO')))
    assert.ok(await evaluate(textHas('Indicaciones sintéticas DEMO')))
    assert.ok(await evaluate(textHas('Dosis DEMO')))
    await click('Nuevo paciente')
    await click('Guardar paciente')
    await wait(textHas('Revisa los campos indicados'))
    assert.equal(await evaluate(`document.activeElement.id`), 'patient-identificacion')
    await fill('#patient-identificacion', `DEMO-A-${institution}`)
    await fill('#patient-nombres', 'Persona nueva')
    await fill('#patient-apellidos', 'Sintética')
    await fill('#patient-fecha_nacimiento', '2099-01-01')
    await click('Guardar paciente')
    await wait(textHas('La fecha de nacimiento no puede ser futura.'))
    await fill('#patient-fecha_nacimiento', '2000-02-29')
    // Dos submits en el mismo turno: solo uno puede crear el paciente.
    await evaluate(`(() => {
      const form = document.querySelector('.patient-form form');
      form.requestSubmit(); form.requestSubmit();
    })()`)
    await wait(textHas('registrado correctamente.'))
    await wait(textHas('No hay consultas registradas.'))
    assert.ok(await evaluate(textHas('2000-02-29')))
    assert.ok(await evaluate(textHas('1 pacientes encontrados')))
    await click('Nueva consulta')
    await click('Guardar consulta')
    await wait(textHas('Las notas de evolución son obligatorias.'))
    await fill('#consultation-fecha', '2099-01-01')
    await fill('#consultation-notas', `Atención DEMO-${institution}\nSeguimiento ficticio`)
    await click('Guardar consulta')
    await wait(textHas('La fecha de consulta no puede ser futura.'))
    await fill('#consultation-fecha', '2026-10-20')
    await evaluate(`(() => {
      const form = document.querySelector('.consultation-form form');
      form.requestSubmit(); form.requestSubmit();
    })()`)
    await wait(textHas('Consulta registrada correctamente.'))
    await wait(textHas(`Atención DEMO-${institution}`))
    assert.equal(await evaluate(`document.querySelectorAll('.consultation').length`), 1)
    assert.ok(await evaluate(textHas('Sin diagnósticos registrados.')))
    await click('Nueva consulta')
    await click('Cancelar consulta')
    assert.equal(await evaluate(`document.querySelector('.consultation-form')`), null)
    await click('Nuevo diagnóstico')
    await click('Registrar diagnóstico')
    await wait(textHas('Revisa los campos indicados.'))
    assert.equal(await evaluate(`document.activeElement.name`), 'codigo_cie10')
    await fill('[name="codigo_cie10"]', 'DEMO-A4')
    await fill('[name="descripcion"]', `Diagnóstico ficticio ${institution}`)
    await evaluate(`(() => { const f = document.querySelector('.consultation-form form'); f.requestSubmit(); f.requestSubmit() })()`)
    await wait(textHas(`Diagnóstico ficticio ${institution}`))
    assert.equal(await evaluate(`document.querySelectorAll('.consultation h4').length`), 1)
    await click('Nuevo tratamiento')
    await fill('[name="indicaciones_generales"]', `Tratamiento ficticio ${institution}`)
    await click('Registrar tratamiento')
    await wait(textHas(`Tratamiento ficticio ${institution}`))
    await click('Nueva receta')
    await wait(`document.querySelector('[name="medicamento_id"]')?.options.length > 1`)
    await fill('[aria-label="Catálogo de medicamentos"] input', 'sin-coincidencia')
    await click('Buscar medicamento')
    await wait(textHas('No hay medicamentos que coincidan.'))
    assert.equal(await evaluate(`document.querySelector('[name="medicamento_id"]').value`), '')
    await fill('[aria-label="Catálogo de medicamentos"] input', 'DEMO')
    await click('Buscar medicamento')
    await wait(`document.querySelector('[name="medicamento_id"]')?.options.length > 1`)
    const medicineId = await evaluate(`document.querySelector('[name="medicamento_id"]').options[1].value`)
    await fill('[name="medicamento_id"]', medicineId)
    await fill('[name="dosis"]', `Dosis ficticia ${institution}`)
    await fill('[name="frecuencia"]', 'Frecuencia ficticia')
    await evaluate(`(() => { const f = document.querySelector('.consultation-form form'); f.requestSubmit(); f.requestSubmit() })()`)
    await wait(textHas(`Dosis ficticia ${institution}`))
    await wait(textHas('DEMO · Medicamento ficticio'))
    assert.equal(await evaluate(`document.querySelectorAll('.consultation li').length`), 1)
    const archiveAvailable = await evaluate(`!![...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Archivar paciente')`)
    if (archiveAvailable) {
      await click('Archivar paciente')
      await fill('[name="motivo"]', `Baja administrativa DEMO ${institution}`)
      await evaluate(`document.querySelector('.consultation-form form').requestSubmit()`)
      await wait(textHas('Confirma que deseas archivar'))
      await evaluate(`document.querySelector('[name="confirmar"]').click()`)
      await evaluate(`document.querySelector('.consultation-form form').requestSubmit()`)
      await wait(textHas('Paciente archivado; el historial se conserva.'))
      await wait(textHas(`Baja administrativa DEMO ${institution}`))
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(b => ['Nueva consulta', 'Nuevo diagnóstico', 'Nuevo tratamiento', 'Nueva receta'].includes(b.textContent.trim()))`), false)
      assert.ok(await evaluate(textHas(`Dosis ficticia ${institution}`)))
    }
    await click('Nuevo paciente')
    await fill('#patient-identificacion', `DEMO-A-${institution}`)
    await fill('#patient-nombres', 'Persona nueva')
    await fill('#patient-apellidos', 'Sintética')
    await fill('#patient-fecha_nacimiento', '2000-02-29')
    await click('Guardar paciente')
    await wait(textHas('la identificación ya existe en esta institución.'))
    assert.equal(await evaluate(`document.querySelector('#patient-identificacion').value`), `DEMO-A-${institution}`)
    assert.equal(await evaluate(`document.activeElement.id`), 'patient-identificacion')
    await click('Cancelar')
    await click('Cerrar sesión')
    await wait(textHas('Iniciar sesión'))
    assert.equal(await evaluate(textHas('Consulta sintética DEMO')), false)
    console.log(`OK navegador: login/alta/consulta/diagnóstico/tratamiento/catálogo/receta/archivo-si-admin/doble-submit/logout — ${institution}`)
  }
  assert.deepEqual(exceptions, [], 'Sin excepciones JavaScript durante el flujo')
} finally {
  for (const task of pending.values()) { clearTimeout(task.timeout); task.reject(new Error('Navegador cerrado')) }
  socket?.close()
  browser.kill('SIGTERM')
}
