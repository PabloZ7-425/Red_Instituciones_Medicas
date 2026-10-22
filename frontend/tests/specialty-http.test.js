import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createClinicalClient } from '../src/api/clinical.js'

test('HTTP especializado convierte tipos, conserva IDs opacos y usa CSRF sin enviar institución', async () => {
  const calls = []
  const client = createClinicalClient({ fetchImpl: async (url, options) => {
    calls.push({ url, ...options })
    return new Response(JSON.stringify(url.endsWith('/auth/csrf/') ? { csrfToken: 'CSRF' } : { id: 'R', paciente_id: ' P opaco ' }))
  } })
  await client.specialty.save('result', ' P opaco ', { tipo_examen: ' EX opaco ', fecha: '2020-01-01T12:00:00Z', estado: 'finalizado', campos: [{ nombre: 'X', tipo: 'booleano', valor: 'false' }] })
  const call = calls[1]
  assert.ok(call.url.includes(encodeURIComponent(' P opaco ')))
  assert.ok(call.url.endsWith('/resultados/nuevo/'))
  assert.equal(call.headers['X-CSRFToken'], 'CSRF')
  assert.equal(call.credentials, 'include')
  const body = JSON.parse(call.body)
  assert.equal(body.tipo_examen, ' EX opaco ')
  assert.deepEqual(body.campos, [{ nombre: 'X', valor: false }])
  assert.equal(Object.hasOwn(body, 'institucion'), false)
  await client.specialty.save('vaccine', ' P opaco ', { vacuna_id: 'V', fecha: '2020-01-01', dosis: '2', lote: '' })
  assert.deepEqual(JSON.parse(calls[2].body), { vacuna_id: 'V', fecha: '2020-01-01', dosis: 2 })
  await client.specialty.save('discharge', ' P opaco ', { ingreso_id: ' ING opaco ', fecha_hora_alta: '2020-01-01T12:00:00Z' })
  assert.ok(calls[3].url.includes(encodeURIComponent(' ING opaco ')))
  assert.deepEqual(JSON.parse(calls[3].body), { fecha_hora_alta: '2020-01-01T12:00:00Z' })
})

test('HTTP: secretaría pide solo tutores; respuestas incompletas son error', async () => {
  const calls = []
  const client = createClinicalClient({ fetchImpl: async url => {
    calls.push(url)
    return new Response(JSON.stringify({ paciente_id: 'P', tutores: [] }))
  } })
  assert.deepEqual(await client.specialty.list('P', { institucion: 'pediatrico', rol: 'secretaria' }), { tutor: [] })
  assert.equal(calls.length, 1)
  assert.ok(calls[0].endsWith('/tutores/'))
  const broken = createClinicalClient({ fetchImpl: async () => new Response('{}') })
  await assert.rejects(broken.specialty.list('P', { institucion: 'pediatrico', rol: 'secretaria' }), e => e.code === 'INVALID_RESPONSE')
  const malformedHistory = createClinicalClient({ fetchImpl: async () => new Response(JSON.stringify({ paciente: { id: 'P' }, consultas: [{ fecha: '2020-01-01', diagnosticos: null }] })) })
  await assert.rejects(malformedHistory.specialty.catalog('procedure', 'P'), e => e.code === 'INVALID_RESPONSE')
})

test('HTTP: catálogo recorre páginas y no acepta metadatos inválidos ni vacíos prematuros', async () => {
  const calls = []
  const client = createClinicalClient({ fetchImpl: async url => {
    calls.push(url)
    const offset = Number(new URL(url, 'http://localhost').searchParams.get('offset'))
    return new Response(JSON.stringify({ count: 101, limit: 100, offset, results: Array.from({ length: offset ? 1 : 100 }, (_, n) => ({ id: String(offset + n), nombre: `DEMO ${offset + n}` })) }))
  } })
  assert.equal((await client.specialty.catalog('result', 'P')).length, 101)
  assert.equal(calls.length, 2)
  const broken = createClinicalClient({ fetchImpl: async () => new Response(JSON.stringify({ count: 101, limit: 100, offset: 0, results: [] })) })
  await assert.rejects(broken.specialty.catalog('result', 'P'), e => e.code === 'INVALID_RESPONSE')
})

test('HTTP: errores especializados conservan estado y no reintentan escrituras', async () => {
  for (const status of [401, 403, 404, 409, 503]) {
    let writes = 0
    const client = createClinicalClient({ fetchImpl: async url => {
      if (url.endsWith('/auth/csrf/')) return new Response(JSON.stringify({ csrfToken: 'CSRF' }))
      writes++
      return new Response(JSON.stringify({ error: { code: 'DEMO', message: 'DEMO', fields: {} } }), { status })
    } })
    await assert.rejects(client.specialty.save('tutor', 'P', { nombres: 'N', apellidos: 'A', parentesco: 'DEMO' }), e => e.status === status)
    assert.equal(writes, 1)
  }
})

test('logout cancela la cadena de lecturas especializadas y login vuelve a habilitarla', async () => {
  const calls = []
  let started
  const pendingRead = new Promise(resolve => { started = resolve })
  const client = createClinicalClient({ fetchImpl: async (url, options) => {
    calls.push(url)
    if (url.endsWith('/auth/csrf/')) return new Response(JSON.stringify({ csrfToken: 'CSRF' }))
    if (url.endsWith('/seguimiento/')) {
      started()
      return new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Cancelado', 'AbortError')), { once: true }))
    }
    if (url.endsWith('/auth/logout/')) return new Response(null, { status: 204 })
    if (url.endsWith('/auth/login/')) return new Response(JSON.stringify({ usuario: { id: 'U' } }))
    if (url.includes('/vacunas/')) return new Response(JSON.stringify({ count: 0, limit: 100, offset: 0, results: [] }))
    throw new Error('Solicitud inesperada')
  } })
  const reading = client.specialty.list('P', { institucion: 'pediatrico', rol: 'admin' })
  const rejected = assert.rejects(reading, error => error.name === 'AbortError')
  await pendingRead
  await client.logout()
  await rejected
  await assert.rejects(client.specialty.catalog('vaccine', 'P'), error => error.name === 'AbortError')
  assert.equal(calls.filter(url => url.includes('/vacunas/')).length, 0)
  await client.login({ username: 'DEMO', password: 'DEMO' })
  assert.deepEqual(await client.specialty.catalog('vaccine', 'P'), [])
})
