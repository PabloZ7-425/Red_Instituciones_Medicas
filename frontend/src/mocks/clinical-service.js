// Doble exclusivamente de desarrollo, contrato normativo 1.0.0 del plan §5.
// Los ejemplos históricos se conservan intactos para comparar con la célula B.
import { getResponseFixture } from './contract-fixtures.js'
import { ApiError } from '../api/clinical.js'

export const DEMO_PASSWORD = 'DEMO-no-utilizar'
const institutions = ['hospital', 'pediatrico', 'laboratorio', 'odontologica']
const normalized = value => value.trim().normalize('NFC').toLowerCase()

export function createDemoClinicalService({ scenario = 'standard', role = 'medico' } = {}) {
  let user = null
  const history = getResponseFixture('API-05').body
  if (scenario === 'empty') history.consultas = []
  if (scenario === 'archived') history.paciente = getResponseFixture('API-10').body
  function authenticated() {
    if (!user) throw new ApiError(401, 'UNAUTHORIZED', 'Inicia sesión para continuar.')
  }
  return {
    mode: 'mock',
    async me() { authenticated(); return { usuario: structuredClone(user) } },
    async login({ username, password }) {
      const institution = institutions.find(name => username.trim() === `DEMO-medico-${name}`)
      if (!institution || password !== DEMO_PASSWORD) throw new ApiError(401, 'UNAUTHORIZED', 'Credenciales DEMO inválidas.')
      user = { id: `DEMO-U-${institution}`, username: username.trim(), rol: role, institucion: institution }
      return { usuario: structuredClone(user) }
    },
    async logout() { authenticated(); user = null },
    async listPatients({ q = '', limit = 20, offset = 0 } = {}) {
      authenticated()
      if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0 || q.trim().length > 100) {
        throw new ApiError(400, 'VALIDATION_ERROR', 'Parámetros de búsqueda inválidos.')
      }
      const patient = history.paciente
      const matches = ['identificacion', 'nombres', 'apellidos'].some(key => normalized(patient[key]).startsWith(normalized(q)))
      const all = matches ? [patient] : []
      return structuredClone({ count: all.length, limit, offset, results: all.slice(offset, offset + limit) })
    },
    async history(id) {
      authenticated()
      if (user.rol === 'secretaria') throw new ApiError(403, 'FORBIDDEN', 'Tu rol no permite consultar historiales.')
      if (id !== history.paciente.id) throw new ApiError(404, 'NOT_FOUND', 'Recurso no encontrado.')
      return structuredClone(history)
    },
  }
}
