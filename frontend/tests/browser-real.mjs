// Smoke real sin dependencias npm adicionales. Requiere Node 22+ y Chromium.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as pause } from 'node:timers/promises'

assert.equal(process.env.A5_REAL_HTTP, '1', 'A5 debe activarse explícitamente')
const url = process.env.BROWSER_URL ?? 'http://127.0.0.1:18173/'
assert.equal(new URL(url).port, '18173', 'Solo frontend A5 dedicado')
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
  const click = label => evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find(element => element.textContent.trim() === ${JSON.stringify(label)});
    if (!button || button.disabled) throw new Error('Botón no disponible'); button.click();
  })()`)
  await command('Runtime.enable')
  await command('Network.enable')
  const responses = []
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Network.responseReceived' && message.params.response.url.startsWith('http://127.0.0.1:18005/api/')) responses.push({ url: message.params.response.url, status: message.params.response.status })
  })
  await command('Page.navigate', { url })
  await wait(textHas('Iniciar sesión'))
  assert.equal(await evaluate(textHas('DEMO · Datos ficticios')), false, 'El cliente debe usar HTTP real')
  for (const institution of ['hospital', 'pediatrico', 'laboratorio', 'odontologica']) {
    await fill('#username', `DEMO-A5-admin-${institution}`)
    await fill('#password', accountPassword)
    await click('Ingresar')
    await wait(textHas('No hay pacientes que coincidan'))
    await click('Nuevo paciente')
    await fill('#patient-identificacion', 'DEMO-A5-BROWSER')
    await fill('#patient-nombres', 'Persona A5')
    await fill('#patient-apellidos', 'Sintética')
    await fill('#patient-fecha_nacimiento', '2000-02-29')
    await evaluate(`(() => { const f = document.querySelector('.patient-form form'); f.requestSubmit(); f.requestSubmit() })()`)
    await wait(textHas('registrado correctamente.'))
    await wait(textHas('No hay consultas registradas.'))
    await click('Nueva consulta')
    await fill('#consultation-fecha', '2026-10-20')
    await fill('#consultation-notas', `Atención real de prueba ${institution}`)
    await click('Guardar consulta')
    await wait(textHas(`Atención real de prueba ${institution}`))
    await click('Nuevo diagnóstico')
    await fill('[name="codigo_cie10"]', 'DEMO-A5')
    await fill('[name="descripcion"]', `Diagnóstico real de prueba ${institution}`)
    await click('Registrar diagnóstico')
    await wait(textHas(`Diagnóstico real de prueba ${institution}`))
    await click('Nuevo tratamiento')
    await fill('[name="indicaciones_generales"]', `Tratamiento real de prueba ${institution}`)
    await click('Registrar tratamiento')
    await wait(textHas(`Tratamiento real de prueba ${institution}`))
    await click('Nueva receta')
    await wait(`document.querySelector('[name="medicamento_id"]')?.options.length > 1`)
    const medicine = await evaluate(`document.querySelector('[name="medicamento_id"]').options[1].value`)
    await fill('[name="medicamento_id"]', medicine)
    await fill('[name="dosis"]', `Dosis ficticia A5 ${institution}`)
    await fill('[name="frecuencia"]', 'Frecuencia ficticia A5')
    await evaluate(`(() => { const f = document.querySelector('.consultation-form form'); f.requestSubmit(); f.requestSubmit() })()`)
    await wait(textHas(`Dosis ficticia A5 ${institution}`))
    await wait(textHas('DEMO A5 no administrar'))
    assert.equal(await evaluate(`document.querySelectorAll('.consultation li').length`), 1)
    await click('Archivar paciente')
    await fill('[name="motivo"]', 'DEMO archivo A5')
    await evaluate(`document.querySelector('[name="confirmar"]').click()`)
    await evaluate(`document.querySelector('.consultation-form form').requestSubmit()`)
    await wait(textHas('Paciente archivado; el historial se conserva.'))
    await wait(textHas('DEMO archivo A5'))
    assert.ok(await evaluate(textHas(`Dosis ficticia A5 ${institution}`)))
    assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Nueva consulta')`), false)
    await click('Cerrar sesión')
    await wait(textHas('Iniciar sesión'))
    console.log(`OK HTTP real React/API/motor/archivo/logout — ${institution}`)
  }
  assert.ok(responses.length > 40, 'Se requieren llamadas HTTP reales')
  assert.deepEqual(responses.filter(r => r.status >= 400 && !(r.status === 401 && r.url.endsWith('/auth/me/'))), [], 'Sin fallos HTTP durante el flujo real')
  assert.deepEqual(exceptions, [], 'Sin excepciones JavaScript')
} finally {
  for (const task of pending.values()) { clearTimeout(task.timeout); task.reject(new Error('Navegador cerrado')) }
  socket?.close()
  browser.kill('SIGTERM')
}
