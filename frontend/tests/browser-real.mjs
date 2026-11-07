// Smoke real sin dependencias npm adicionales. Requiere Node 22+ y Chromium.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, mkdir, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as pause } from 'node:timers/promises'

assert.equal(process.env.A5_REAL_HTTP, '1', 'A5 debe activarse explícitamente')
const url = process.env.BROWSER_URL ?? 'http://127.0.0.1:18173/'
const configuredApi = process.env.OPERATIONS_BROWSER_API ?? new URL('/api', url).href
const apiBase = configuredApi.endsWith('/') ? configuredApi.slice(0, -1) : configuredApi
assert.ok(['18173','18175'].includes(new URL(url).port), 'Solo frontend de pruebas dedicado')
const accountPassword = process.env.A5_BROWSER_PASSWORD
const accounts = process.env.A5_ACCESS_FILE ? JSON.parse(await readFile(process.env.A5_ACCESS_FILE, 'utf8')) : null
assert.ok(accounts || accountPassword, 'Se requiere archivo privado de cuentas o contraseña DEMO A5')
const selectedInstitutions = process.env.A5_INSTITUTIONS?.split(',') ?? ['hospital', 'pediatrico', 'laboratorio', 'odontologica']
assert.ok(selectedInstitutions.length && selectedInstitutions.every(value => ['hospital', 'pediatrico', 'laboratorio', 'odontologica'].includes(value)), 'Instituciones de prueba válidas')
const patientIdentification = process.env.A5_PATIENT_IDENTIFICATION ?? 'DEMO-A5-BROWSER'
assert.ok(patientIdentification.length > 0 && patientIdentification.length <= 20, 'Identificación de prueba de 1 a 20 caracteres')
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
  async function inspectInstitution(institution) {
    if (!process.env.A5_EVIDENCE_DIR) return
    await mkdir(process.env.A5_EVIDENCE_DIR, { recursive: true })
    for (const width of [360, 768, 1280]) {
      await command('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false })
      await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
      assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth'), `Sin desbordamiento: ${institution}, ${width}px`)
      const { data } = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
      await writeFile(join(process.env.A5_EVIDENCE_DIR, `${institution}-real-${width}.png`), Buffer.from(data, 'base64'))
    }
  }
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
  await command('Network.enable')
  const responses = []
  const expectedFailures = []
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Network.responseReceived' && message.params.response.url.startsWith(process.env.OPERATIONS_BROWSER_API ?? 'http://127.0.0.1:18005/api/')) responses.push({ url: message.params.response.url, status: message.params.response.status })
  })
  async function probeSaveFailures(formSelector, retainedSelector, expectedValue) {
    if (process.env.A5_ERROR_CHECKS !== '1') return
    let paused
    const listener = event => {
      const message = JSON.parse(event.data)
      if (message.method === 'Fetch.requestPaused') paused = message.params
    }
    socket.addEventListener('message', listener)
    await command('Fetch.enable', { patterns: [{ urlPattern: '*api/pacientes/*', requestStage: 'Request' }] })
    try {
      for (const status of [400, 403, 409, 503]) {
        paused = null
        await evaluate(`(() => { const form = document.querySelector(${JSON.stringify(formSelector)}); form.requestSubmit(); form.requestSubmit() })()`)
        for (let attempt = 0; !paused && attempt < 100; attempt++) await pause(50)
        assert.ok(paused, `Solicitud interceptada ${status}`)
        assert.equal(paused.request.method, 'POST')
        assert.ok(await evaluate(`document.querySelector(${JSON.stringify(formSelector)}).getAttribute('aria-busy') === 'true'`))
        await command('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape' })
        await command('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape' })
        assert.ok(await evaluate(`!!document.querySelector('dialog[open]')`), 'Escape no cierra durante guardado')
        expectedFailures.push({ url: paused.request.url, status })
        await command('Fetch.fulfillRequest', {
          requestId: paused.requestId, responseCode: status,
          responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
          body: Buffer.from(JSON.stringify({ error: { code: 'UI_TEST_ERROR', message: `Error de prueba ${status}`, fields: {} } })).toString('base64'),
        })
        await wait(`document.querySelector(${JSON.stringify(formSelector)})?.getAttribute('aria-busy') === 'false'`)
        assert.equal(await evaluate(`document.querySelector(${JSON.stringify(retainedSelector)}).value`), expectedValue, `Borrador conservado ante ${status}`)
        assert.ok(await evaluate(`!!document.querySelector('dialog [role="alert"]')`), 'Error anunciado con texto')
      }
    } finally {
      await command('Fetch.disable')
      socket.removeEventListener('message', listener)
    }
  }
  await command('Page.navigate', { url })
  await wait(textHas('Iniciar sesión'))
  assert.equal(await evaluate(textHas('DEMO · Datos ficticios')), false, 'El cliente debe usar HTTP real')
  const roleCheck = process.env.A4_HTTP_BROWSER_ROLE
  if (roleCheck) {
    assert.ok(!accounts, 'La prueba de roles usa las identidades dedicadas A5')
    assert.ok(['secretaria', 'enfermero', 'laboratorista'].includes(roleCheck))
    const institution = { secretaria: 'pediatrico', enfermero: 'hospital', laboratorista: 'laboratorio' }[roleCheck]
    await fill('#username', `DEMO-A5-${roleCheck}-${institution}`)
    await fill('#password', accountPassword)
    await click('Ingresar')
    await click('Pacientes')
    await wait(textHas({ secretaria: 'Secretaría', enfermero: 'Enfermería', laboratorista: 'Laboratorio' }[roleCheck]))
    if (roleCheck !== 'enfermero') {
      await click('Nuevo paciente')
      await fill('#patient-identificacion', `DEMO-ROLE-${roleCheck === 'secretaria' ? 'S' : 'L'}`)
      await fill('#patient-nombres', 'Persona de prueba')
      await fill('#patient-apellidos', 'Sintética')
      await fill('#patient-fecha_nacimiento', '2000-01-01')
      await click('Guardar paciente')
      await wait(textHas('registrado correctamente.'))
    }
    if (roleCheck === 'secretaria') {
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(b => b.textContent === 'Ver historial')`), false)
      await click('Gestionar tutores')
      await wait(`document.querySelector('[name="parentesco"]') !== null`)
      await fill('[name="nombres"]', 'Tutor HTTP secretaría')
      await fill('[name="apellidos"]', 'Sintético')
      await fill('[name="parentesco"]', 'DEMO familiar')
      await click('Guardar especialización')
      await wait(textHas('Tutor HTTP secretaría'))
      assert.equal(await evaluate(textHas('Registrar vacuna')), false)
      assert.equal(await evaluate(textHas('Registrar crecimiento')), false)
    } else if (roleCheck === 'enfermero') {
      await fill('#search', 'DEMO-A5-BROWSER')
      await click('Buscar')
      await wait(textHas('1 pacientes encontrados'))
      await click('Ver historial')
      await click('Seguimiento institucional')
    await wait(textHas('Especialización institucional'))
      assert.equal(await evaluate(`document.querySelectorAll('[aria-label="Especialización institucional"] button').length`), 0)
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(b => ['Nuevo paciente', 'Nueva consulta'].includes(b.textContent))`), false)
    } else {
      await click('Seguimiento institucional')
      await click('Registrar resultado')
      await wait(`document.querySelector('[name="tipo_examen"]')?.options.length > 1`)
      await fill('[name="tipo_examen"]', await evaluate(`document.querySelector('[name="tipo_examen"]').options[1].value`))
      await fill('[name="fecha"]', '2020-01-01T12:00:00')
      await fill('[name="estado"]', 'finalizado')
      await fill('fieldset > fieldset label:nth-of-type(1) input', 'DEMO dato')
      await fill('fieldset > fieldset label:nth-of-type(3) input', 'Resultado HTTP laboratorista')
      await click('Guardar especialización')
      await wait(textHas('Resultado HTTP laboratorista'))
      assert.equal(await evaluate(textHas('Nuevo diagnóstico')), false)
      assert.equal(await evaluate(textHas('Nueva receta')), false)
    }
    await click('Cerrar sesión')
    await wait(textHas('Iniciar sesión'))
    console.log(`OK HTTP real permisos/especialización/logout — ${roleCheck}`)
  }
  for (const institution of roleCheck ? [] : selectedInstitutions) {
    const credentials = accounts?.[institution] ?? { username: `DEMO-A5-admin-${institution}`, password: accountPassword }
    assert.ok(typeof credentials.username === 'string' && typeof credentials.password === 'string', 'Credenciales locales requeridas')
    await fill('#username', credentials.username)
    await fill('#password', credentials.password)
    await click('Ingresar')
    await click('Pacientes')
    await wait(`!!document.querySelector('#search')`)
    await fill('#search', patientIdentification)
    await click('Buscar')
    await wait(textHas('No hay pacientes que coincidan'))
    await click('Nuevo paciente')
    await fill('#patient-identificacion', patientIdentification)
    await fill('#patient-nombres', 'Persona A5')
    await fill('#patient-apellidos', 'Sintética')
    await fill('#patient-fecha_nacimiento', '2000-02-29')
    await evaluate(`(() => { const f = document.querySelector('.patient-form form'); f.requestSubmit(); f.requestSubmit() })()`)
    await wait(textHas('registrado correctamente.'))
    await wait(textHas('No hay consultas registradas.'))
    assert.equal(await evaluate(textHas('Simulación local:')), false)
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
    const medicineLabel = await evaluate(`document.querySelector('[name="medicamento_id"]').options[1].textContent`)
    const medicine = await evaluate(`document.querySelector('[name="medicamento_id"]').options[1].value`)
    await fill('[name="medicamento_id"]', medicine)
    await fill('[name="dosis"]', `Dosis ficticia A5 ${institution}`)
    await fill('[name="frecuencia"]', 'Frecuencia ficticia A5')
    await evaluate(`(() => { const f = document.querySelector('.consultation-form form'); f.requestSubmit(); f.requestSubmit() })()`)
    await wait(textHas(`Dosis ficticia A5 ${institution}`))
    await wait(textHas(medicineLabel))
    assert.equal(await evaluate(`document.querySelectorAll('.consultation li').length`), 1)
    await click('Seguimiento institucional')
    await wait(textHas('Especialización institucional'))
    const specialtyRoot = '[aria-label="Especialización institucional"]'
    const specialtyCount = section => evaluate(`(() => { const section = [...document.querySelectorAll(${JSON.stringify(specialtyRoot + ' > section')})].find(s => s.querySelector('h4')?.textContent === ${JSON.stringify(section)}); return section?.querySelectorAll(':scope > ul > li').length })()`)
    const saveSpecialty = async () => {
      await evaluate(`(() => { const f = document.querySelector(${JSON.stringify(specialtyRoot + ' form')}); f.requestSubmit(); f.requestSubmit() })()`)
      await wait(`!document.querySelector(${JSON.stringify(specialtyRoot + ' form')})`)
    }
    const selectFirst = async name => {
      await wait(`document.querySelector('[name="${name}"]')?.options.length > 1`)
      await fill(`[name="${name}"]`, await evaluate(`([...document.querySelector('[name="${name}"]').options].find(o=>${JSON.stringify(name)}==='vacuna_id'&&o.textContent.includes('DEMO vacuna A4'))??document.querySelector('[name="${name}"]').options[1]).value`))
    }
    if (institution === 'hospital') {
      await click('Registrar ingreso')
      await click('Guardar especialización')
      await wait(textHas('Selecciona una opción disponible.'))
      assert.equal(await evaluate('document.activeElement.name'), 'cama_id')
      await selectFirst('cama_id')
      await fill('[name="fecha_hora_ingreso"]', '2020-01-01T12:00:00')
      await fill('[name="tipo_ingreso"]', 'DEMO ingreso navegador')
      await evaluate(`document.querySelector('[name="confirmar_ingreso"]').click()`)
      await saveSpecialty()
      await wait(textHas('DEMO ingreso navegador'))
      assert.equal(await specialtyCount('Ingresos'), 1)
      await click('Registrar alta hospitalaria')
      await selectFirst('ingreso_id')
      await fill('[name="fecha_hora_alta"]', '2020-01-02T12:00:00')
      await saveSpecialty()
      await wait(textHas('2020-01-02 12:00:00'))
      assert.equal(await specialtyCount('Altas'), 1)
    } else if (institution === 'pediatrico') {
      await click('Registrar tutor')
      await fill('[name="nombres"]', 'DEMO tutor navegador')
      await fill('[name="apellidos"]', 'Sintético')
      await fill('[name="parentesco"]', 'DEMO familiar')
      await saveSpecialty()
      await wait(textHas('DEMO tutor navegador'))
      assert.equal(await specialtyCount('Tutores'), 1)
      await click('Registrar vacuna')
      await selectFirst('vacuna_id')
      const vaccineLabel = await evaluate(`document.querySelector('[name="vacuna_id"]').selectedOptions[0].textContent`)
      await fill('[name="fecha"]', '2020-01-01')
      await fill('[name="dosis"]', '1')
      await saveSpecialty()
      await wait(textHas(vaccineLabel))
      assert.equal(await specialtyCount('Vacunas'), 1)
      await click('Registrar crecimiento')
      await fill('[name="fecha"]', '2020-01-01')
      await fill('[name="peso_kg"]', '15.2')
      await fill('[name="talla_cm"]', '90')
      await probeSaveFailures(specialtyRoot + ' form', '[name="peso_kg"]', '15.2')
      await saveSpecialty()
      await wait(textHas('15.20'))
      assert.equal(await specialtyCount('Crecimiento'), 1)
    } else if (institution === 'laboratorio') {
      await click('Registrar resultado')
      await selectFirst('tipo_examen')
      await fill('[name="fecha"]', '2020-01-01T12:00:00')
      await fill('[name="estado"]', 'finalizado')
      const row = n => `${specialtyRoot} fieldset > fieldset:nth-of-type(${n})`
      await fill(`${row(1)} label:nth-of-type(1) input`, 'DEMO numérico')
      await fill(`${row(1)} label:nth-of-type(2) select`, 'numero')
      await fill(`${row(1)} label:nth-of-type(3) input`, '3.5')
      await click('Añadir campo')
      await fill(`${row(2)} label:nth-of-type(1) input`, 'DEMO booleano')
      await fill(`${row(2)} label:nth-of-type(2) select`, 'booleano')
      await fill(`${row(2)} label:nth-of-type(3) select`, 'false')
      await click('Añadir campo')
      await fill(`${row(3)} label:nth-of-type(1) input`, 'DEMO texto')
      await fill(`${row(3)} label:nth-of-type(3) input`, 'DEMO resultado navegador')
      await probeSaveFailures(specialtyRoot + ' form', `${row(3)} label:nth-of-type(3) input`, 'DEMO resultado navegador')
      await saveSpecialty()
      await wait(textHas('DEMO resultado navegador'))
      assert.equal(await specialtyCount('Resultados de exámenes'), 1)
    } else {
      await click('Registrar procedimiento')
      await selectFirst('tratamiento_id')
      await fill('[name="pieza"]', '16')
      await fill('[name="descripcion"]', 'DEMO procedimiento navegador')
      await fill('[name="estado"]', 'realizado')
      await saveSpecialty()
      await wait(textHas('DEMO procedimiento navegador'))
      assert.equal(await specialtyCount('Procedimientos odontológicos'), 1)
    }
    await inspectInstitution(institution)
    await click('Archivar paciente')
    await fill('[name="motivo"]', 'DEMO archivo A5')
    await evaluate(`document.querySelector('[name="confirmar"]').click()`)
    await evaluate(`document.querySelector('.consultation-form form').requestSubmit()`)
    await wait(textHas('Paciente archivado. Se conserva su historial.'))
    await wait(textHas('DEMO archivo A5'))
    await click('Consultas y tratamientos')
    assert.ok(await evaluate(textHas(`Dosis ficticia A5 ${institution}`)))
    assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Nueva consulta')`), false)
    assert.equal(await evaluate(`document.querySelectorAll('[aria-label="Especialización institucional"] button').length`), 0)
    if (process.env.A5_RELOAD_CHECK === '1') {
      await evaluate('window.__a5BeforeReload = true')
      await command('Page.reload')
      await wait(`document.readyState === 'complete' && !window.__a5BeforeReload`)
      await click('Pacientes')
      await wait(`!!document.querySelector('#search')`)
      await fill('#search', patientIdentification)
      await click('Buscar')
      await click('Ver historial')
      await wait(textHas('DEMO archivo A5'))
      await wait(textHas(`Dosis ficticia A5 ${institution}`))
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Nueva consulta')`), false)
      await click('Seguimiento institucional')
      await wait(textHas(institution === 'pediatrico' ? '15.20' : institution === 'laboratorio' ? 'DEMO resultado navegador' : institution === 'hospital' ? 'DEMO ingreso navegador' : 'DEMO procedimiento navegador'))
      assert.equal(await evaluate(`document.querySelectorAll('[aria-label="Especialización institucional"] button').length`), 0)
    }
    if (process.env.A5_ERROR_CHECKS === '1') {
      const historyUrl = responses.findLast(row => row.url.includes('/historial/')).url
      expectedFailures.push({ url: historyUrl, status: 401 })
      const patientsUrl = responses.findLast(row => new URL(row.url).pathname === '/api/pacientes/').url
      expectedFailures.push({ url: patientsUrl, status: 401 })
      await evaluate(`(async () => {
        const base = ${JSON.stringify(apiBase)};
        const { csrfToken } = await (await fetch(base + '/auth/csrf/', { credentials: 'include' })).json();
        const response = await fetch(base + '/auth/logout/', { method: 'POST', credentials: 'include', headers: { 'X-CSRFToken': csrfToken } });
        if (response.status !== 204) throw new Error('No se pudo invalidar la sesion de prueba');
      })()`)
      await click('Actualizar historial')
    } else await click('Cerrar sesión')
    await wait(textHas('Iniciar sesión'))
    assert.equal(await evaluate(textHas(patientIdentification)), false, 'Se limpia el contexto clínico al cerrar o vencer la sesión')
    console.log(`OK HTTP real React/API/motor/especialización/archivo/logout — ${institution}`)
  }
  assert.ok(responses.length > (roleCheck ? 8 : selectedInstitutions.length * 10), 'Se requieren llamadas HTTP reales')
  assert.deepEqual(responses.filter(r => {
    if (r.status < 400 || (r.status === 401 && r.url.endsWith('/auth/me/'))) return false
    const index = expectedFailures.findIndex(expected => expected.status === r.status && expected.url === r.url)
    if (index < 0) return true
    expectedFailures.splice(index, 1)
    return false
  }), [], 'Sin fallos HTTP inesperados durante el flujo real')
  assert.deepEqual(expectedFailures, [], 'Se observaron todos los errores previstos')
  assert.deepEqual(exceptions, [], 'Sin excepciones JavaScript')
} finally {
  for (const task of pending.values()) { clearTimeout(task.timeout); task.reject(new Error('Navegador cerrado')) }
  socket?.close()
  browser.kill('SIGTERM')
}
