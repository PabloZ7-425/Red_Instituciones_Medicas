// Doble exclusivamente de desarrollo, contrato normativo 1.0.0 del plan §5.
// Los ejemplos históricos se conservan intactos para comparar con la célula B.
import { getResponseFixture } from './contract-fixtures.js'
import { ApiError } from '../api/clinical.js'
import { canRegisterPatient, todayInGuatemala, validatePatientCreate } from '../clinical/patient-form.js'
import { canRegisterConsultation, validateConsultationCreate } from '../clinical/consultation-form.js'

export const DEMO_PASSWORD = 'DEMO-no-utilizar'
const institutions = ['hospital', 'pediatrico', 'laboratorio', 'odontologica']
const normalized = value => value.trim().normalize('NFC').toLowerCase()
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0

export function createDemoClinicalService({ scenario = 'standard', role = 'medico', professionalEnabled = true, today = todayInGuatemala() } = {}) {
  let user = null
  const stores = new Map()
  function store() {
    if (!user) throw new ApiError(401, 'UNAUTHORIZED', 'Inicia sesión para continuar.')
    return stores.get(user.institucion)
  }
  return {
    mode: 'mock',
    async me() { store(); return { usuario: structuredClone(user) } },
    async login({ username, password }) {
      const institution = institutions.find(name => username.trim() === `DEMO-medico-${name}`)
      if (!institution || password !== DEMO_PASSWORD) throw new ApiError(401, 'UNAUTHORIZED', 'Credenciales DEMO inválidas.')
      if (!stores.has(institution)) {
        const history = getResponseFixture('API-05').body
        if (scenario === 'empty') history.consultas = []
        if (scenario === 'archived') history.paciente = getResponseFixture('API-10').body
        if (scenario === 'inactive') history.paciente.estado = 'inactivo'
        stores.set(institution, new Map([[history.paciente.id, history]]))
      }
      user = { id: `DEMO-U-${institution}`, username: username.trim(), rol: role, institucion: institution }
      return { usuario: structuredClone(user) }
    },
    async logout() { store(); user = null },
    async createPatient(input) {
      const records = store()
      if (!canRegisterPatient(user)) throw new ApiError(403, 'FORBIDDEN', 'Tu rol no permite registrar pacientes.')
      const { data, fields } = validatePatientCreate(input, { today })
      if (Object.keys(fields).length) throw new ApiError(400, 'VALIDATION_ERROR', 'Datos inválidos.', fields)
      if ([...records.values()].some(record => record.paciente.identificacion === data.identificacion)) {
        throw new ApiError(409, 'CONFLICT', 'La identificación ya existe.', { identificacion: ['Esta identificación ya está registrada.'] })
      }
      const patient = { ...data, id: `DEMO-${user.institucion}-P-${records.size + 1}`, estado: 'activo', motivo_archivo: null, fecha_archivo: null }
      records.set(patient.id, { paciente: patient, consultas: [] })
      return structuredClone(patient)
    },
    async createConsultation(patientId, input) {
      const records = store()
      if (!canRegisterConsultation(user) || !professionalEnabled) throw new ApiError(403, 'FORBIDDEN', 'Se requiere un rol y vínculo profesional habilitados.')
      const history = records.get(patientId)
      if (!history) throw new ApiError(404, 'NOT_FOUND', 'Recurso no encontrado.')
      if (history.paciente.estado !== 'activo') throw new ApiError(409, 'CONFLICT', 'El paciente no está activo.')
      const { data, fields } = validateConsultationCreate(input, { today })
      if (Object.keys(fields).length) throw new ApiError(400, 'VALIDATION_ERROR', 'Datos inválidos.', fields)
      // No hay catálogo de citas en estos fixtures; no inventar una cita válida.
      if (data.cita_id !== undefined) throw new ApiError(404, 'NOT_FOUND', 'Recurso no encontrado.')
      const count = [...records.values()].reduce((sum, record) => sum + record.consultas.length, 0)
      const consultation = { ...data, id: `DEMO-${user.institucion}-C-${count + 1}`, paciente_id: patientId, cita_id: null }
      history.consultas.push({ ...consultation, diagnosticos: [] })
      history.consultas.sort((a, b) => compare(a.fecha, b.fecha) || compare(a.id, b.id))
      return structuredClone(consultation)
    },
    async listPatients({ q = '', limit = 20, offset = 0 } = {}) {
      const records = store()
      if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0 || q.trim().length > 100) {
        throw new ApiError(400, 'VALIDATION_ERROR', 'Parámetros de búsqueda inválidos.')
      }
      const all = [...records.values()].map(record => record.paciente)
        .filter(patient => ['identificacion', 'nombres', 'apellidos'].some(key => normalized(patient[key]).startsWith(normalized(q))))
        .sort((a, b) => compare(a.identificacion, b.identificacion) || compare(a.id, b.id))
      return structuredClone({ count: all.length, limit, offset, results: all.slice(offset, offset + limit) })
    },
    async history(id) {
      const records = store()
      if (user.rol === 'secretaria') throw new ApiError(403, 'FORBIDDEN', 'Tu rol no permite consultar historiales.')
      if (!records.has(id)) throw new ApiError(404, 'NOT_FOUND', 'Recurso no encontrado.')
      return structuredClone(records.get(id))
    },
  }
}
