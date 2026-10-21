import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createClinicalClient } from '../src/api/clinical.js'
import { canRegisterConsultation, validateConsultationCreate } from '../src/clinical/consultation-form.js'
import { createDemoClinicalService, DEMO_PASSWORD } from '../src/mocks/clinical-service.js'

const input = { fecha: '2026-10-20', notas_evolucion: 'Notas DEMO\nSegunda línea' }
const today = '2026-10-20'
const login = (client, institution = 'hospital') => client.login({ username: `DEMO-medico-${institution}`, password: DEMO_PASSWORD })

test('consulta conserva fecha civil, trim y saltos de línea; cita opcional se omite', () => {
  assert.deepEqual(validateConsultationCreate({ ...input, notas_evolucion: ` ${input.notas_evolucion} ` }, { today }), { data: input, fields: {} })
  assert.equal(validateConsultationCreate({ ...input, cita_id: ' DEMO-CITA ' }, { today }).data.cita_id, 'DEMO-CITA')
  for (const fecha of ['2026-02-30', '2026-10-21', '1900-02-29', '0000-01-01', '2026-10-20T00:00:00Z', '', null]) {
    assert.ok(validateConsultationCreate({ ...input, fecha }, { today }).fields.fecha)
  }
  assert.deepEqual(validateConsultationCreate({ ...input, fecha: '2000-02-29' }, { today }).fields, {})
})

test('rechaza notas inválidas, campos ajenos, citas null/vacías y cuerpos no objeto', () => {
  for (const patch of [{ notas_evolucion: ' ' }, { notas_evolucion: null }, { notas_evolucion: 3 }, { notas_evolucion: 'x'.repeat(5001) }, { cita_id: null }, { cita_id: '' }, { cita_id: 1 }, { medico_id: 'ajeno' }, { institucion: 'hospital' }, { id: 'inyectado' }, JSON.parse('{"__proto__":"extra"}')]) {
    assert.notEqual(Object.keys(validateConsultationCreate({ ...input, ...patch }, { today }).fields).length, 0)
  }
  for (const invalid of [null, [], 'consulta']) assert.notEqual(Object.keys(validateConsultationCreate(invalid, { today }).fields).length, 0)
  assert.deepEqual(validateConsultationCreate({ ...input, notas_evolucion: 'Á'.repeat(5000) }, { today }).fields, {})
})

test('HTTP API-06 codifica paciente, envía ConsultaCreate con CSRF y lee respuesta 201', async () => {
  const calls = []
  const response = { ...input, id: 'DEMO-C', paciente_id: 'opaco/?', cita_id: null }
  const client = createClinicalClient({ fetchImpl: async (url, options) => {
    calls.push({ url, ...options })
    return url.endsWith('/csrf/') ? Response.json({ csrfToken: 'DEMO-CSRF' }) : Response.json(response, { status: 201 })
  } })
  assert.deepEqual(await client.createConsultation('opaco/?', input), response)
  assert.equal(calls[1].url, '/api/pacientes/opaco%2F%3F/consultas/')
  assert.equal(calls[1].method, 'POST'); assert.equal(calls[1].credentials, 'include')
  assert.equal(calls[1].headers['X-CSRFToken'], 'DEMO-CSRF')
  assert.deepEqual(JSON.parse(calls[1].body), input)
})

test('HTTP conserva errores clínicos y de red sin reintentar el registro', async () => {
  for (const [status, code] of [[400, 'VALIDATION_ERROR'], [401, 'UNAUTHORIZED'], [403, 'FORBIDDEN'], [404, 'NOT_FOUND'], [409, 'CONFLICT'], [503, 'SERVICE_UNAVAILABLE'], [0, 'NETWORK_ERROR']]) {
    let writes = 0
    const client = createClinicalClient({ fetchImpl: async url => {
      if (url.endsWith('/csrf/')) return Response.json({ csrfToken: 'DEMO' })
      writes++
      if (status === 0) throw new TypeError('DEMO sin conexión')
      return Response.json({ error: { code, message: 'Error DEMO', fields: { notas_evolucion: ['Revisar notas'] } } }, { status })
    } })
    await assert.rejects(client.createConsultation('DEMO-P-1', input), error => error.status === status && error.code === code)
    assert.equal(writes, 1)
  }
})

test('DEMO registra ocurrencias independientes, ordenadas, sin alterar diagnósticos previos', async () => {
  const client = createDemoClinicalService({ today })
  await login(client)
  const original = await client.history('DEMO-P-1')
  const first = await client.createConsultation('DEMO-P-1', input)
  const earlier = await client.createConsultation('DEMO-P-1', { ...input, fecha: '2026-10-19' })
  const second = await client.createConsultation('DEMO-P-1', input)
  assert.notEqual(first.id, second.id) // Notas iguales no significan duplicado de consulta.
  assert.equal(first.paciente_id, 'DEMO-P-1'); assert.equal(first.cita_id, null)
  assert.ok(!Object.hasOwn(first, 'diagnosticos'))
  first.notas_evolucion = 'Cambio externo'
  const history = await client.history('DEMO-P-1')
  assert.equal(history.consultas.length, 4); assert.equal(history.consultas[0].id, earlier.id)
  assert.deepEqual(history.consultas.find(c => c.id === first.id).diagnosticos, [])
  assert.equal(history.consultas.find(c => c.id === first.id).notas_evolucion, input.notas_evolucion)
  assert.deepEqual(history.consultas.find(c => c.id === original.consultas[0].id), original.consultas[0])
})

test('DEMO rechaza archivo/inactivo, datos inválidos y citas inexistentes sin modificar historia', async () => {
  for (const scenario of ['standard', 'archived', 'inactive']) {
    const client = createDemoClinicalService({ scenario, today })
    await login(client)
    const before = await client.history('DEMO-P-1')
    if (scenario !== 'standard') await assert.rejects(client.createConsultation('DEMO-P-1', input), error => error.status === 409)
    else {
      await assert.rejects(client.createConsultation('DEMO-P-1', { ...input, fecha: '2026-02-30' }), error => error.status === 400)
      await assert.rejects(client.createConsultation('DEMO-P-1', { ...input, cita_id: 'ausente' }), error => error.status === 404)
    }
    assert.deepEqual(await client.history('DEMO-P-1'), before)
  }
})

test('DEMO respeta sesión, matriz de roles, vínculo profesional y aislamiento del padre', async () => {
  const anonymous = createDemoClinicalService({ today })
  await assert.rejects(anonymous.createConsultation('DEMO-P-1', input), error => error.status === 401)
  for (const role of ['admin', 'medico', 'secretaria', 'enfermero', 'laboratorista']) {
    for (const institution of ['hospital', 'laboratorio']) {
      const allowed = ['admin', 'medico'].includes(role) || (role === 'laboratorista' && institution === 'laboratorio')
      const client = createDemoClinicalService({ role, today })
      await login(client, institution)
      assert.equal(canRegisterConsultation({ rol: role, institucion: institution }), allowed)
      if (allowed) await client.createConsultation('DEMO-P-1', input)
      else await assert.rejects(client.createConsultation('ausente', input), error => error.status === 403)
    }
  }
  const disabled = createDemoClinicalService({ professionalEnabled: false, today })
  await login(disabled)
  await assert.rejects(disabled.createConsultation('DEMO-P-1', input), error => error.status === 403)
  const client = createDemoClinicalService({ today })
  await login(client)
  const patient = await client.createPatient({ identificacion: 'DEMO-NUEVO', nombres: 'Paciente', apellidos: 'DEMO', fecha_nacimiento: '2000-01-01' })
  await client.logout(); await login(client, 'laboratorio')
  await assert.rejects(client.createConsultation(patient.id, input), error => error.status === 404)
})
