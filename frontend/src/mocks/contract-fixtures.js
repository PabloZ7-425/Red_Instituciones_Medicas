// Copia de los ejemplos candidatos de B: datos estáticos, no una API ni auth real.
import candidate from './contrato_v1.json' with { type: 'json' }

const sourceCommit = 'f35207d7854e06122cfb30ee475b806cf0650c1e'

export function getFixtureMetadata() {
  return {
    mode: 'mock',
    status: candidate.status,
    version: candidate.version,
    sourceCommit,
    sourcePath: 'backend/apps/historiales/fixtures/contrato_v1.json',
    warning: 'PROVISIONAL: ejemplos candidatos, sin sesión ni persistencia real',
  }
}

export function getOperationIds() {
  return candidate.cases.map(({ id }) => id)
}

export function getContractCase(operationId) {
  const fixture = candidate.cases.find(({ id }) => id === operationId)
  if (!fixture) throw new RangeError(`Operación sin fixture: ${operationId}`)
  // Cada consumidor puede transformar su copia sin contaminar otras pantallas.
  return structuredClone(fixture)
}

export function getResponseFixture(operationId, { invalid = false } = {}) {
  const fixture = getContractCase(operationId)
  return invalid ? fixture.invalid.response : fixture.response
}
