import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createClinicalClient, ApiError } from '../src/api/clinical.js'
import { createDemoClinicalService, DEMO_PASSWORD } from '../src/mocks/clinical-service.js'

function scripted(responses) {
  const calls = []
  const client = createClinicalClient({ baseUrl: 'http://localhost:8000/api/', fetchImpl: async (url, options) => {
    calls.push({ url, ...options })
    const next = responses.shift()
    if (next instanceof Error) throw next
    assert.ok(next, 'Solicitud inesperada')
    return new Response(next.status === 204 ? null : JSON.stringify(next.body), { status: next.status ?? 200 })
  } })
  return { client, calls }
}

const token = value => ({ body: { csrfToken: value } })

test('login anónimo usa CSRF, conserva password y rota token antes del logout 204', async () => {
  const { client, calls } = scripted([token('antes'), { body: { usuario: { id: 'DEMO-U' } } }, token('despues'), { status: 204 }])
  await client.login({ username: ' DEMO ', password: ' con espacios ' })
  await client.logout()
  assert.deepEqual(calls.map(c => new URL(c.url).pathname), ['/api/auth/csrf/', '/api/auth/login/', '/api/auth/csrf/', '/api/auth/logout/'])
  assert.deepEqual(JSON.parse(calls[1].body), { username: 'DEMO', password: ' con espacios ' })
  assert.equal(calls[1].headers['X-CSRFToken'], 'antes')
  assert.equal(calls[3].headers['X-CSRFToken'], 'despues')
  assert.ok(calls.every(c => c.credentials === 'include'))
})

test('CSRF anónimo fallido impide enviar credenciales y no simula login', async () => {
  const { client, calls } = scripted([{ status: 503, body: { error: { code: 'SERVICE_UNAVAILABLE', message: 'No disponible', fields: {} } } }])
  await assert.rejects(client.login({ username: 'DEMO', password: DEMO_PASSWORD }), error => error.status === 503)
  assert.equal(calls.length, 1)
})

test('errores HTTP mantienen estado, código y campos; no se reintenta POST automáticamente', async () => {
  for (const [status, code] of [[400, 'VALIDATION_ERROR'], [401, 'UNAUTHORIZED'], [403, 'FORBIDDEN'], [404, 'NOT_FOUND'], [409, 'CONFLICT'], [503, 'SERVICE_UNAVAILABLE']]) {
    const fields = { username: ['DEMO inválido'] }
    const { client, calls } = scripted([token('demo'), { status, body: { error: { code, message: 'Error DEMO', fields } } }])
    await assert.rejects(client.login({ username: 'DEMO', password: DEMO_PASSWORD }), error => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, status); assert.equal(error.code, code); assert.deepEqual(error.fields, fields)
      return true
    })
    assert.equal(calls.length, 2)
  }
})

test('error de red no se transforma en lista vacía ni en datos DEMO', async () => {
  const { client, calls } = scripted([new TypeError('fetch failed')])
  await assert.rejects(client.listPatients(), error => error.status === 0 && error.code === 'NETWORK_ERROR')
  assert.equal(calls.length, 1)
})

test('lecturas codifican ID opaco y query literal; no incluyen contraseña ni CSRF', async () => {
  const { client, calls } = scripted([{ body: { count: 0, limit: 20, offset: 0, results: [] } }, { body: {} }])
  const controller = new AbortController()
  await client.listPatients({ q: '%_.* Á', offset: 20, signal: controller.signal })
  await client.history('opaco/á?x')
  const query = new URL(calls[0].url).searchParams
  assert.equal(query.get('q'), '%_.* Á'); assert.equal(query.get('offset'), '20')
  assert.ok(calls[1].url.endsWith('/pacientes/opaco%2F%C3%A1%3Fx/historial/'))
  assert.equal(calls[0].signal, controller.signal)
  assert.equal(calls[0].headers['X-CSRFToken'], undefined)
})

test('cancelación conserva AbortError y respuesta no JSON produce error explícito', async () => {
  const aborted = new DOMException('DEMO cancelado', 'AbortError')
  const { client } = scripted([aborted])
  await assert.rejects(client.me(), error => error === aborted)
  const malformed = createClinicalClient({ fetchImpl: async () => new Response('<html>error</html>', { status: 503 }) })
  await assert.rejects(malformed.me(), error => error.status === 503 && error.code === 'INVALID_RESPONSE')
})

test('sesión DEMO exige login y logout la invalida en cuatro instituciones', async () => {
  for (const institution of ['hospital', 'pediatrico', 'laboratorio', 'odontologica']) {
    const client = createDemoClinicalService()
    await assert.rejects(client.me(), error => error.status === 401)
    await assert.rejects(client.login({ username: `DEMO-medico-${institution}`, password: 'incorrecta' }), error => error.status === 401)
    const result = await client.login({ username: `DEMO-medico-${institution}`, password: DEMO_PASSWORD })
    assert.equal(result.usuario.institucion, institution)
    await client.logout()
    await assert.rejects(client.listPatients(), error => error.status === 401)
  }
})

test('búsqueda DEMO es prefijo literal, case-insensitive, y count precede paginación', async () => {
  const client = createDemoClinicalService()
  await client.login({ username: 'DEMO-medico-hospital', password: DEMO_PASSWORD })
  assert.equal((await client.listPatients({ q: ' PAC ' })).count, 1)
  for (const q of ['aci', '.*', '%', '_']) assert.equal((await client.listPatients({ q })).count, 0)
  const page = await client.listPatients({ q: 'DEMO-', offset: 20 })
  assert.equal(page.count, 1); assert.deepEqual(page.results, [])
  await assert.rejects(client.listPatients({ limit: 0 }), error => error.status === 400)
})

test('historia DEMO preserva fechas civiles, archivo y [] sin mutación entre consumidores', async () => {
  for (const scenario of ['standard', 'empty', 'archived']) {
    const client = createDemoClinicalService({ scenario })
    await client.login({ username: 'DEMO-medico-hospital', password: DEMO_PASSWORD })
    const history = await client.history('DEMO-P-1')
    assert.equal(history.paciente.fecha_nacimiento, '2001-02-03')
    if (scenario === 'empty') assert.deepEqual(history.consultas, [])
    if (scenario === 'archived') { assert.equal(history.paciente.estado, 'archivado'); assert.equal(history.consultas.length, 1) }
    history.consultas.length = 0; history.paciente.nombres = 'DEMO alterado'
    assert.notEqual((await client.history('DEMO-P-1')).paciente.nombres, 'DEMO alterado')
    await assert.rejects(client.history('ajeno'), error => error.status === 404)
  }
})

test('mock secretaria permite lista, pero rechaza lectura clínica', async () => {
  const client = createDemoClinicalService({ role: 'secretaria' })
  await client.login({ username: 'DEMO-medico-hospital', password: DEMO_PASSWORD })
  assert.equal((await client.listPatients()).count, 1)
  await assert.rejects(client.history('DEMO-P-1'), error => error.status === 403)
})
