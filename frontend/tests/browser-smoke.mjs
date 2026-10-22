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
  const roleCheck = process.env.A4_DEMO_BROWSER_ROLE
  if (roleCheck) {
    assert.ok(['secretaria', 'enfermero', 'laboratorista'].includes(roleCheck))
    const institution = { secretaria: 'pediatrico', enfermero: 'hospital', laboratorista: 'laboratorio' }[roleCheck]
    await fill('#username', `DEMO-medico-${institution}`)
    await fill('#password', 'DEMO-no-utilizar')
    await click('Ingresar')
    await wait(textHas('1 pacientes encontrados'))
    await wait(textHas(`· ${roleCheck}`))
    if (roleCheck === 'secretaria') {
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(b => b.textContent === 'Ver historial')`), false)
      await click('Gestionar tutores · DEMO')
      await wait(textHas('Registrar tutor · DEMO'))
      await fill('[name="nombres"]', 'Tutor DEMO secretaría')
      await fill('[name="apellidos"]', 'Sintético')
      await fill('[name="parentesco"]', 'DEMO familiar')
      await evaluate(`(() => { const f = document.querySelector('[aria-label="Especialización DEMO"] form'); f.requestSubmit(); f.requestSubmit() })()`)
      await wait(textHas('Tutor DEMO secretaría'))
      assert.equal(await evaluate(`document.querySelectorAll('[aria-label="Especialización DEMO"] > section > ul > li').length`), 1)
      assert.equal(await evaluate(textHas('Registrar crecimiento · DEMO')), false)
      assert.equal(await evaluate(textHas('Registrar vacuna · DEMO')), false)
    } else {
      await click('Ver historial')
      await wait(textHas('Especialización institucional · DEMO'))
      if (roleCheck === 'enfermero') {
        assert.equal(await evaluate(`document.querySelectorAll('[aria-label="Especialización DEMO"] button').length`), 0)
        assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(b => ['Nuevo paciente', 'Nueva consulta'].includes(b.textContent))`), false)
      } else {
        await click('Registrar resultado · DEMO')
        await wait(`document.querySelector('[name="tipo_examen"]')?.options.length > 1`)
        await fill('[name="tipo_examen"]', await evaluate(`document.querySelector('[name="tipo_examen"]').options[1].value`))
        await fill('[name="fecha"]', '2020-01-01T12:00:00Z')
        await fill('[name="estado"]', 'finalizado')
        await fill('fieldset > fieldset label:nth-of-type(1) input', 'DEMO dato')
        await fill('fieldset > fieldset label:nth-of-type(3) input', 'DEMO laboratorista navegador')
        await click('Guardar especialización DEMO')
        await wait(textHas('DEMO laboratorista navegador'))
        assert.equal(await evaluate(textHas('Nuevo diagnóstico')), false)
        assert.equal(await evaluate(textHas('Nueva receta')), false)
      }
    }
    await click('Cerrar sesión')
    await wait(textHas('Iniciar sesión'))
    console.log(`OK navegador especialización/permisos/logout — ${roleCheck}`)
  }
  for (const [institution, heading] of roleCheck ? [] : [
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
    await wait(textHas('Especialización institucional · DEMO'))
    const specialtyRoot = '[aria-label="Especialización DEMO"]'
    const specialtyCount = section => evaluate(`(() => { const section = [...document.querySelectorAll(${JSON.stringify(specialtyRoot + ' > section')})].find(s => s.querySelector('h4')?.textContent === ${JSON.stringify(section)}); return section?.querySelectorAll(':scope > ul > li').length })()`)
    const saveSpecialty = async () => {
      await evaluate(`(() => { const f = document.querySelector(${JSON.stringify(specialtyRoot + ' form')}); f.requestSubmit(); f.requestSubmit() })()`)
      await wait(`!document.querySelector(${JSON.stringify(specialtyRoot + ' form')})`)
    }
    const selectFirst = async name => {
      await wait(`document.querySelector('[name="${name}"]')?.options.length > 1`)
      await fill(`[name="${name}"]`, await evaluate(`document.querySelector('[name="${name}"]').options[1].value`))
    }
    if (institution === 'hospital') {
      await click('Registrar ingreso · DEMO')
      await click('Guardar especialización DEMO')
      await wait(textHas('Selecciona una opción disponible.'))
      assert.equal(await evaluate('document.activeElement.name'), 'cama_id')
      await selectFirst('cama_id')
      await fill('[name="fecha_hora_ingreso"]', '2020-01-01T12:00:00Z')
      await fill('[name="tipo_ingreso"]', 'DEMO ingreso navegador')
      await saveSpecialty()
      await wait(textHas('DEMO ingreso navegador'))
      assert.equal(await specialtyCount('Ingresos'), 1)
      await click('Registrar alta hospitalaria · DEMO')
      await selectFirst('ingreso_id')
      await fill('[name="fecha_hora_alta"]', '2020-01-02T12:00:00Z')
      await saveSpecialty()
      await wait(textHas('2020-01-02T12:00:00Z'))
      assert.equal(await specialtyCount('Altas'), 1)
    } else if (institution === 'pediatrico') {
      await click('Registrar tutor · DEMO')
      await fill('[name="nombres"]', 'DEMO tutor navegador')
      await fill('[name="apellidos"]', 'Sintético')
      await fill('[name="parentesco"]', 'DEMO familiar')
      await saveSpecialty()
      await wait(textHas('DEMO tutor navegador'))
      assert.equal(await specialtyCount('Tutores'), 1)
      await click('Registrar vacuna · DEMO')
      await selectFirst('vacuna_id')
      await fill('[name="fecha"]', '2020-01-01')
      await fill('[name="dosis"]', '1')
      await saveSpecialty()
      await wait(textHas('DEMO · Vacuna ficticia'))
      assert.equal(await specialtyCount('Vacunas'), 1)
      await click('Registrar crecimiento · DEMO')
      await fill('[name="fecha"]', '2020-01-01')
      await fill('[name="peso_kg"]', '15.2')
      await fill('[name="talla_cm"]', '90')
      await saveSpecialty()
      await wait(textHas('15.20'))
      assert.equal(await specialtyCount('Crecimiento'), 1)
    } else if (institution === 'laboratorio') {
      await click('Registrar resultado · DEMO')
      await selectFirst('tipo_examen')
      await fill('[name="fecha"]', '2020-01-01T12:00:00Z')
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
      await saveSpecialty()
      await wait(textHas('DEMO resultado navegador'))
      assert.equal(await specialtyCount('Resultados de exámenes'), 1)
    } else {
      await click('Registrar procedimiento · DEMO')
      await selectFirst('tratamiento_id')
      await fill('[name="pieza"]', '16')
      await fill('[name="descripcion"]', 'DEMO procedimiento navegador')
      await fill('[name="estado"]', 'realizado')
      await saveSpecialty()
      await wait(textHas('DEMO procedimiento navegador'))
      assert.equal(await specialtyCount('Procedimientos odontológicos'), 1)
    }
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
      assert.equal(await evaluate(`document.querySelectorAll(${JSON.stringify(specialtyRoot + ' button')}).length`), 0)
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
