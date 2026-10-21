// Estados de presentación derivados del candidato; nunca se conectan al HTTP real.
import { getFixtureMetadata, getResponseFixture } from './contract-fixtures.js'

function errorFixture(status, code, message) {
  return { status, body: { error: { code, message, fields: {} } } }
}

export function getUiScenarios() {
  const history = getResponseFixture('API-05')
  const archivedPatient = getResponseFixture('API-10').body
  const page = getResponseFixture('API-03')
  return {
    metadata: getFixtureMetadata(),
    emptyPatients: { status: 200, body: { ...page.body, count: 0, results: [] } },
    emptyHistory: { status: 200, body: { paciente: structuredClone(history.body.paciente), consultas: [] } },
    archivedHistory: { status: 200, body: { ...history.body, paciente: archivedPatient } },
    errors: {
      validation: getResponseFixture('API-04', { invalid: true }),
      expiredSession: getResponseFixture('API-02', { invalid: true }),
      forbidden: errorFixture(403, 'FORBIDDEN', 'Acceso denegado'),
      notFound: getResponseFixture('API-05', { invalid: true }),
      duplicatePatient: errorFixture(409, 'CONFLICT', 'La identificación ya existe'),
      archivedWrite: errorFixture(409, 'CONFLICT', 'El paciente no está activo'),
      unavailable: errorFixture(503, 'SERVICE_UNAVAILABLE', 'Servicio temporalmente no disponible'),
      internal: errorFixture(500, 'INTERNAL_ERROR', 'Error interno'),
      unsupportedContent: errorFixture(415, 'UNSUPPORTED_MEDIA_TYPE', 'El cuerpo requiere JSON'),
      wrongMethod: errorFixture(405, 'METHOD_NOT_ALLOWED', 'Método no permitido'),
    },
  }
}
