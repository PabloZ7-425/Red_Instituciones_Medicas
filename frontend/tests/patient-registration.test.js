import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createClinicalClient } from '../src/api/clinical.js'
import { createDemoClinicalService, DEMO_PASSWORD } from '../src/mocks/clinical-service.js'
import { canRegisterPatient, todayInGuatemala, validatePatientCreate } from '../src/clinical/patient-form.js'

const input = { identificacion: 'DEMO-NUEVO', nombres: 'Ana', apellidos: 'Ejemplo', fecha_nacimiento: '2000-02-29' }
const today = '2026-10-20'
async function login(client, institution = 'hospital') {
  await client.login({ username: `DEMO-medico-${institution}`, password: DEMO_PASSWORD })
}

test('normaliza los textos y conserva exactamente la fecha civil, sin mutar la entrada', () => {
  const draft = { ...input, nombres: ' Ana ', identificacion: ' DEMO-NUEVO ' }
  const result = validatePatientCreate(draft, { today })
  assert.deepEqual(result, { data: input, fields: {} })
  assert.equal(draft.nombres, ' Ana ')
  assert.equal(todayInGuatemala(new Date('2026-10-21T03:00:00Z')), today)
})

test('rechaza campos vacíos, tipos incorrectos, longitudes y campos generados o ajenos', () => {
  for (const patch of [
    { identificacion: ' ' }, { identificacion: 'x'.repeat(21) }, { nombres: 'x'.repeat(101) },
    { apellidos: null }, { nombres: 123 }, { id: 'inyectado' }, { institucion: 'hospital' },
    { motor: 'mongo' }, { usuario_id: 'ajeno' }, { constructor: 'extra' }, JSON.parse('{"__proto__":"extra"}'),
  ]) {
    const result = validatePatientCreate({ ...input, ...patch }, { today })
    assert.notEqual(Object.keys(result.fields).length, 0, JSON.stringify(patch))
  }
  for (const invalid of [null, [], 'paciente']) assert.notEqual(Object.keys(validatePatientCreate(invalid, { today }).fields).length, 0)
  assert.deepEqual(validatePatientCreate({ ...input, nombres: 'Á'.repeat(100), identificacion: '0'.repeat(20) }, { today }).fields, {})
})

test('valida calendario gregoriano y futuro sin desplazar fechas por zona horaria', () => {
  for (const value of ['2026-02-30', '1900-02-29', '2026-13-01', '0000-01-01', '2000-1-01', '2026-10-21', '', null, '2026-10-20T00:00:00Z']) {
    assert.ok(validatePatientCreate({ ...input, fecha_nacimiento: value }, { today }).fields.fecha_nacimiento, String(value))
  }
  for (const value of ['2000-02-29', '0001-01-01', today]) {
    assert.deepEqual(validatePatientCreate({ ...input, fecha_nacimiento: value }, { today }).fields, {})
  }
})

test('registro HTTP envía solo PacienteCreate con sesión y CSRF y lee la respuesta 201', async () => {
  const calls = []
  const patient = { ...input, id: 'opaco', estado: 'activo', motivo_archivo: null, fecha_archivo: null }
  const client = createClinicalClient({ fetchImpl: async (url, options) => {
    calls.push({ url, ...options })
    return url.endsWith('/auth/csrf/') ? Response.json({ csrfToken: 'DEMO-CSRF' }) : Response.json(patient, { status: 201 })
  } })
  assert.deepEqual(await client.createPatient(input), patient)
  assert.equal(calls.length, 2)
  assert.equal(calls[1].url, '/api/pacientes/')
  assert.equal(calls[1].method, 'POST')
  assert.equal(calls[1].headers['X-CSRFToken'], 'DEMO-CSRF')
  assert.equal(calls[1].credentials, 'include')
  assert.deepEqual(JSON.parse(calls[1].body), input)
})

test('registro fallido conserva errores de campo y no se reintenta automáticamente', async () => {
  for (const [status, code] of [[400, 'VALIDATION_ERROR'], [401, 'UNAUTHORIZED'], [403, 'FORBIDDEN'], [409, 'CONFLICT'], [503, 'SERVICE_UNAVAILABLE']]) {
    let writes = 0
    const client = createClinicalClient({ fetchImpl: async (url) => {
      if (url.endsWith('/csrf/')) return Response.json({ csrfToken: 'DEMO' })
      writes++
      return Response.json({ error: { code, message: 'Error DEMO', fields: { identificacion: ['Error de identificación'] } } }, { status })
    } })
    await assert.rejects(client.createPatient(input), error => error.status === status && error.fields.identificacion[0] === 'Error de identificación')
    assert.equal(writes, 1)
  }
})

test('alta DEMO permite listado/lectura posteriores y rechaza duplicados sin cambios', async () => {
  const client = createDemoClinicalService({ today })
  await login(client)
  const patient = await client.createPatient(input)
  assert.equal(typeof patient.id, 'string'); assert.equal(patient.estado, 'activo')
  assert.equal(patient.motivo_archivo, null); assert.equal(patient.fecha_archivo, null)
  assert.deepEqual(await client.history(patient.id), { paciente: patient, consultas: [] })
  const before = await client.listPatients()
  assert.equal(before.count, 2)
  await assert.rejects(client.createPatient({ ...input, identificacion: ' DEMO-NUEVO ' }), error => error.status === 409)
  assert.deepEqual(await client.listPatients(), before)
  patient.nombres = 'Cambio externo'
  assert.equal((await client.history(patient.id)).paciente.nombres, 'Ana')
})

test('DEMO aísla altas por institución y mantiene count/orden/paginación después de varias altas', async () => {
  const client = createDemoClinicalService({ today })
  await login(client)
  const hospitalPatient = await client.createPatient(input)
  for (let n = 0; n < 22; n++) await client.createPatient({ ...input, identificacion: `ALTA-${String(n).padStart(2, '0')}` })
  const page = await client.listPatients({ q: 'alta-', limit: 20, offset: 20 })
  assert.equal(page.count, 22); assert.deepEqual(page.results.map(p => p.identificacion), ['ALTA-20', 'ALTA-21'])
  await client.logout(); await login(client, 'laboratorio')
  assert.equal((await client.listPatients()).count, 1)
  await assert.rejects(client.history(hospitalPatient.id), error => error.status === 404)
  await client.createPatient(input) // Duplicado se evalúa por institución.
  await client.logout(); await login(client)
  assert.equal((await client.listPatients()).count, 24)
})

test('datos inválidos no alteran el estado DEMO y roles siguen la matriz API-04', async () => {
  const client = createDemoClinicalService({ today })
  await assert.rejects(client.createPatient(input), error => error.status === 401)
  await login(client)
  await assert.rejects(client.createPatient({ ...input, fecha_nacimiento: '2026-02-30' }), error => error.status === 400)
  assert.equal((await client.listPatients()).count, 1)
  for (const role of ['admin', 'medico', 'secretaria', 'enfermero', 'laboratorista']) {
    for (const institution of ['hospital', 'laboratorio']) {
      const allowed = ['admin', 'medico', 'secretaria'].includes(role) || (role === 'laboratorista' && institution === 'laboratorio')
      assert.equal(canRegisterPatient({ rol: role, institucion: institution }), allowed)
      const mock = createDemoClinicalService({ role, today })
      await login(mock, institution)
      if (allowed) assert.equal((await mock.createPatient(input)).estado, 'activo')
      else await assert.rejects(mock.createPatient(input), error => error.status === 403)
    }
  }
})
