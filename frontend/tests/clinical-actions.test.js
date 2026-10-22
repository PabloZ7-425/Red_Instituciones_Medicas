import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createClinicalClient } from '../src/api/clinical.js'
import { createDemoClinicalService, DEMO_PASSWORD } from '../src/mocks/clinical-service.js'
import { canPrescribe, canArchive, validateClinicalAction } from '../src/clinical/clinical-actions.js'

const patient = { identificacion: 'DEMO-A4', nombres: 'Persona', apellidos: 'Sintética', fecha_nacimiento: '2000-01-01' }
const diagnosis = { codigo_cie10: 'DEMO', descripcion: 'Descripción ficticia' }
const treatment = { indicaciones_generales: 'DEMO no administrar' }
async function login(service, institution = 'hospital') {
  await service.login({ username: `DEMO-medico-${institution}`, password: DEMO_PASSWORD })
}
async function chain(service, institution) {
  await login(service, institution)
  const p = await service.createPatient(patient)
  const c = await service.createConsultation(p.id, { fecha: '2020-01-01', notas_evolucion: 'DEMO' })
  const d = await service.createDiagnosis(c.id, diagnosis)
  const t = await service.createTreatment(d.id, treatment)
  const m = (await service.listMedicines()).results[0]
  const r = await service.createPrescription(t.id, { medicamento_id: m.id, dosis: 'DEMO', frecuencia: 'DEMO' })
  return { p, c, d, t, m, r }
}

test('validación clínica conserva IDs opacos y normaliza solo textos; opcional vacío omitido', () => {
  assert.deepEqual(validateClinicalAction('diagnosis', { codigo_cie10: ' DEMO ', descripcion: ' Texto\nDEMO ' }), { data: { codigo_cie10: 'DEMO', descripcion: 'Texto\nDEMO' }, fields: {} })
  assert.deepEqual(validateClinicalAction('prescription', { medicamento_id: ' ID opaco ', dosis: ' D ', frecuencia: ' F ', via_administracion: '' }), { data: { medicamento_id: ' ID opaco ', dosis: 'D', frecuencia: 'F' }, fields: {} })
  for (const [kind, input] of [['diagnosis', {}], ['treatment', { indicaciones_generales: ' ' }], ['archive', { motivo: 'x'.repeat(201) }], ['prescription', { medicamento_id: 'M', dosis: 'x'.repeat(101), frecuencia: 'D' }], ['diagnosis', { ...diagnosis, medico_id: 'intruso' }], ['archive', null]]) {
    assert.ok(Object.keys(validateClinicalAction(kind, input).fields).length)
  }
  assert.equal(canPrescribe({ rol: 'laboratorista' }), false)
  assert.equal(canArchive({ rol: 'medico' }), false)
  assert.equal(canArchive({ rol: 'admin' }), true)
})

test('HTTP: cuatro escrituras usan rutas/IDs opacos, CSRF y PATCH de archivo', async () => {
  const calls = []
  const client = createClinicalClient({ fetchImpl: async (url, options) => {
    calls.push({ url, ...options })
    return new Response(JSON.stringify(url.endsWith('/auth/csrf/') ? { csrfToken: 'DEMO-token' } : { id: 'DEMO' }), { status: 200 })
  } })
  await client.createDiagnosis('consulta / opaca', diagnosis)
  await client.createTreatment('diagnóstico / opaco', treatment)
  await client.createPrescription('tratamiento / opaco', { medicamento_id: 'M', dosis: 'D', frecuencia: 'F' })
  await client.archivePatient('paciente / opaco', { motivo: 'DEMO' })
  assert.deepEqual(calls.map(c => c.method), ['GET', 'POST', 'POST', 'POST', 'PATCH'])
  assert.ok(calls[1].url.includes(encodeURIComponent('consulta / opaca')))
  assert.ok(calls[2].url.includes(encodeURIComponent('diagnóstico / opaco')))
  assert.ok(calls[3].url.endsWith('/recetas/'))
  assert.deepEqual(JSON.parse(calls[4].body), { estado: 'archivado', motivo: 'DEMO' })
  assert.ok(calls.every(c => c.credentials === 'include'))
  assert.ok(calls.slice(1).every(c => c.headers['X-CSRFToken'] === 'DEMO-token'))
})

test('HTTP: catálogo pagina/cancela, valida respuesta y no disfraza errores de red', async () => {
  const controller = new AbortController(), calls = []
  const client = createClinicalClient({ fetchImpl: async (url, options) => {
    calls.push({ url, ...options })
    return new Response(JSON.stringify({ count: 21, limit: 20, offset: 20, results: [{ id: 'M', nombre: 'DEMO', presentacion: null }] }))
  } })
  await client.listMedicines({ q: 'Á%_', offset: 20, signal: controller.signal })
  assert.equal(new URL(calls[0].url, 'http://localhost').searchParams.get('q'), 'Á%_')
  assert.equal(calls[0].signal, controller.signal)
  for (const body of [{}, { count: 1, limit: 0, offset: 0, results: [] }, { count: 1, limit: 20, offset: 0, results: [{ id: {}, nombre: 'DEMO', presentacion: null }] }]) {
    const broken = createClinicalClient({ fetchImpl: async () => new Response(JSON.stringify(body)) })
    await assert.rejects(broken.listMedicines(), e => e.code === 'INVALID_RESPONSE')
  }
  const offline = createClinicalClient({ fetchImpl: async () => { throw new TypeError('DEMO offline') } })
  await assert.rejects(offline.listMedicines(), e => e.status === 0)
})

test('HTTP: 400/401/403/404/409/503 se preservan, escrituras no se reintentan', async () => {
  for (const status of [400, 401, 403, 404, 409, 503]) {
    let writes = 0
    const client = createClinicalClient({ fetchImpl: async (url) => {
      if (url.endsWith('/auth/csrf/')) return new Response(JSON.stringify({ csrfToken: 'DEMO' }))
      writes++
      return new Response(JSON.stringify({ error: { code: 'DEMO', message: 'Error DEMO', fields: { descripcion: ['DEMO'] } } }), { status })
    } })
    await assert.rejects(client.createDiagnosis('D', diagnosis), e => e.status === status && e.fields.descripcion[0] === 'DEMO')
    assert.equal(writes, 1)
  }
})

test('DEMO: cadena completa y archivo idempotente en las cuatro instituciones', async () => {
  const service = createDemoClinicalService({ role: 'admin', today: '2026-10-22' })
  for (const institution of ['hospital', 'pediatrico', 'laboratorio', 'odontologica']) {
    const { p, c, d, t, r, m } = await chain(service, institution)
    assert.equal(d.consulta_id, c.id)
    assert.equal(t.diagnostico_id, d.id)
    assert.equal(r.tratamiento_id, t.id)
    assert.equal(r.medicamento_id, m.id)
    assert.equal(r.via_administracion, null)
    const before = (await service.history(p.id)).consultas
    const archived = await service.archivePatient(p.id, { motivo: ' DEMO ' })
    assert.equal(archived.fecha_archivo, '2026-10-22')
    assert.deepEqual(await service.archivePatient(p.id, { motivo: 'DEMO' }), archived)
    await assert.rejects(service.archivePatient(p.id, { motivo: 'otro' }), e => e.status === 409)
    for (const call of [() => service.createDiagnosis(c.id, diagnosis), () => service.createTreatment(d.id, treatment), () => service.createPrescription(t.id, { medicamento_id: m.id, dosis: 'D', frecuencia: 'F' })]) await assert.rejects(call(), e => e.status === 409)
    assert.deepEqual((await service.history(p.id)).consultas, before)
    await service.logout()
  }
})

test('DEMO: diagnósticos son ocurrencias, medicamento inexistente no crea receta', async () => {
  const service = createDemoClinicalService()
  const { p, c, d, t } = await chain(service)
  const second = await service.createDiagnosis(c.id, diagnosis)
  assert.notEqual(second.id, d.id)
  const before = await service.history(p.id)
  await assert.rejects(service.createPrescription(t.id, { medicamento_id: 'NO-EXISTE', dosis: 'D', frecuencia: 'F' }), e => e.status === 404)
  assert.deepEqual(await service.history(p.id), before)
  const page = await service.listMedicines({ q: 'sin-coincidencia' })
  assert.equal(page.count, 0)
  assert.equal((await service.listMedicines({ offset: 100 })).results.length, 0)
})

test('DEMO: roles y vínculo profesional se comprueban independientemente de la UI', async () => {
  for (const role of ['secretaria', 'enfermero', 'laboratorista']) {
    const service = createDemoClinicalService({ role })
    await login(service, role === 'laboratorista' ? 'laboratorio' : 'hospital')
    await assert.rejects(service.listMedicines(), e => e.status === 403)
    await assert.rejects(service.createDiagnosis('missing', diagnosis), e => e.status === 403)
    await assert.rejects(service.archivePatient('missing', { motivo: 'DEMO' }), e => e.status === 403)
  }
  const service = createDemoClinicalService({ professionalEnabled: false })
  await login(service)
  await assert.rejects(service.createTreatment('missing', treatment), e => e.status === 403)
})

test('DEMO: padres de otra institución y sesión cerrada no permiten escribir', async () => {
  const service = createDemoClinicalService({ role: 'admin' })
  const { p, c, d, t } = await chain(service)
  await service.logout(); await login(service, 'pediatrico')
  for (const action of [() => service.createDiagnosis(c.id, diagnosis), () => service.createTreatment(d.id, treatment), () => service.createPrescription(t.id, { medicamento_id: 'DEMO-M-1', dosis: 'D', frecuencia: 'F' }), () => service.archivePatient(p.id, { motivo: 'DEMO' })]) await assert.rejects(action(), e => e.status === 404)
  await service.logout()
  await assert.rejects(service.listMedicines(), e => e.status === 401)
})
