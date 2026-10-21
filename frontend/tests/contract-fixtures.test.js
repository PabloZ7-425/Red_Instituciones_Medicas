import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import {
  getContractCase,
  getFixtureMetadata,
  getOperationIds,
  getResponseFixture,
} from '../src/mocks/contract-fixtures.js'
import { getUiScenarios } from '../src/mocks/ui-scenarios.js'

const serverSource = new URL('../../backend/apps/historiales/fixtures/contrato_v1.json', import.meta.url)
const clientCopy = new URL('../src/mocks/contrato_v1.json', import.meta.url)
const source = JSON.parse(readFileSync(serverSource, 'utf8'))

test('los diez fixtures cliente coinciden byte a byte con los ejemplos versionados de B', () => {
  assert.equal(readFileSync(clientCopy, 'utf8'), readFileSync(serverSource, 'utf8'),
    'El candidato B cambió: revisar DTOs y actualizar explícitamente la copia cliente')
  assert.equal(source.cases.length, 10)
  assert.equal(new Set(getOperationIds()).size, 10)
  for (const fixture of source.cases) assert.deepEqual(getContractCase(fixture.id), fixture)
  assert.deepEqual(getOperationIds(), Array.from({ length: 10 }, (_, n) => `API-${String(n + 1).padStart(2, '0')}`))
})

test('el cliente identifica el origen y mantiene visible el estado provisional', () => {
  const metadata = getFixtureMetadata()
  assert.equal(metadata.mode, 'mock')
  assert.equal(metadata.status, 'propuesto-no-ratificado')
  assert.equal(metadata.version, source.version)
  assert.match(metadata.sourceCommit, /^[a-f0-9]{40}$/)
  assert.match(metadata.warning, /PROVISIONAL/)
  assert.equal(getUiScenarios().metadata.status, metadata.status)
})

test('transformar un fixture para una pantalla no contamina los otros consumidores', () => {
  const expected = getContractCase('API-05')
  const altered = getContractCase('API-05')
  altered.response.body.paciente.nombres = 'DEMO modificado'
  altered.response.body.consultas[0].diagnosticos.length = 0
  assert.deepEqual(getContractCase('API-05'), expected)
  const scenarios = getUiScenarios()
  scenarios.archivedHistory.body.consultas.length = 0
  assert.deepEqual(getResponseFixture('API-05'), expected.response)
  assert.equal(getUiScenarios().archivedHistory.body.consultas.length, 1)
})

test('las respuestas son JSON para React, con IDs string y sin secretos o tipos del driver', () => {
  function inspect(value) {
    if (Array.isArray(value)) return value.forEach(inspect)
    if (value === null || typeof value !== 'object') return
    for (const [key, item] of Object.entries(value)) {
      assert.ok(!['password', 'contrasena', 'contrasena_hash', 'token', 'engine', 'motor', '_id', '$oid', '$date'].includes(key), key)
      if ((key === 'id' || key.endsWith('_id')) && item !== null) {
        assert.equal(typeof item, 'string', key)
        assert.notEqual(item.length, 0)
      }
      inspect(item)
    }
  }
  for (const id of getOperationIds()) {
    for (const invalid of [false, true]) {
      const response = getResponseFixture(id, { invalid })
      assert.deepEqual(JSON.parse(JSON.stringify(response)), response)
      inspect(response.body)
    }
  }
  const writes = getOperationIds().map(id => getContractCase(id).request)
  for (const request of writes) {
    for (const key of ['motor', 'institucion', 'usuario_id', 'medico_id']) assert.ok(!(key in request))
  }
})

test('el historial permite navegar toda la cadena con los IDs usados por las operaciones siguientes', () => {
  const { paciente, consultas } = getResponseFixture('API-05').body
  assert.deepEqual(paciente, getResponseFixture('API-04').body)
  const consulta = consultas[0]
  const diagnostico = consulta.diagnosticos[0]
  const tratamiento = diagnostico.tratamientos[0]
  const receta = tratamiento.recetas[0]
  assert.equal(consulta.paciente_id, paciente.id)
  assert.equal(diagnostico.consulta_id, consulta.id)
  assert.equal(tratamiento.diagnostico_id, diagnostico.id)
  assert.equal(receta.tratamiento_id, tratamiento.id)
  for (const [id, path] of [
    ['API-05', `/api/pacientes/${paciente.id}/historial/`],
    ['API-06', `/api/pacientes/${paciente.id}/consultas/`],
    ['API-07', `/api/consultas/${consulta.id}/diagnosticos/`],
    ['API-08', `/api/diagnosticos/${diagnostico.id}/tratamientos/`],
    ['API-09', `/api/tratamientos/${tratamiento.id}/recetas/`],
  ]) assert.equal(getContractCase(id).path, path)
})

test('fechas civiles y campos opcionales llegan sin conversiones UTC ni cambios de null', () => {
  const patient = getResponseFixture('API-04').body
  assert.equal(patient.fecha_nacimiento, '2001-02-03')
  assert.equal(patient.fecha_archivo, null)
  assert.equal(patient.motivo_archivo, null)
  assert.equal(getResponseFixture('API-06').body.cita_id, null)
  assert.ok(!('cita_id' in getContractCase('API-06').request))
  assert.equal(getResponseFixture('API-10').body.fecha_archivo, '2026-10-20')
  assert.equal(getResponseFixture('API-09').body.via_administracion, 'Vía DEMO')
  assert.ok(!JSON.stringify(source).includes('\ufffd'))
})

test('vacío y archivo conservan las formas de respuesta y el historial existente', () => {
  const scenarios = getUiScenarios()
  assert.deepEqual(scenarios.emptyPatients.body, { count: 0, limit: 20, offset: 0, results: [] })
  assert.deepEqual(scenarios.emptyHistory.body.consultas, [])
  assert.deepEqual(scenarios.archivedHistory.body.paciente, getResponseFixture('API-10').body)
  assert.deepEqual(scenarios.archivedHistory.body.consultas, getResponseFixture('API-05').body.consultas)
  assert.equal(getResponseFixture('API-04').body.estado, 'activo')
})

test('errores utilizables por formularios, sesión y conflictos respetan HTTP y envoltorio candidato', () => {
  const codes = new Map([[400, 'VALIDATION_ERROR'], [401, 'UNAUTHORIZED'], [403, 'FORBIDDEN'], [404, 'NOT_FOUND'], [409, 'CONFLICT'], [503, 'SERVICE_UNAVAILABLE'], [500, 'INTERNAL_ERROR'], [415, 'UNSUPPORTED_MEDIA_TYPE'], [405, 'METHOD_NOT_ALLOWED']])
  const errors = getUiScenarios().errors
  for (const { status, body } of Object.values(errors)) {
    assert.equal(body.error.code, codes.get(status))
    assert.deepEqual(Object.keys(body.error).sort(), ['code', 'fields', 'message'])
    assert.equal(typeof body.error.message, 'string')
    assert.equal(typeof body.error.fields, 'object')
    assert.ok(!Array.isArray(body.error.fields))
    assert.notEqual(body.error.fields, null)
  }
  assert.deepEqual(errors.validation.body.error.fields.identificacion, ['Valor inválido'])
  assert.deepEqual(errors.expiredSession, getContractCase('API-02').invalid.response)
  assert.equal(errors.archivedWrite.status, 409)
  assert.equal(errors.duplicatePatient.status, 409)
})
