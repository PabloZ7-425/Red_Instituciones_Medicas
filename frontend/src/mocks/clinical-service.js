// Doble exclusivamente de desarrollo, contrato normativo 1.0.0 del plan §5.
// Los ejemplos históricos se conservan intactos para comparar con la célula B.
import { getResponseFixture } from './contract-fixtures.js'
import { ApiError } from '../api/clinical.js'
import { createSpecialtyDemo } from './specialty-service.js'
import { canRegisterPatient, todayInGuatemala, validatePatientCreate } from '../clinical/patient-form.js'
import { canRegisterConsultation, validateConsultationCreate } from '../clinical/consultation-form.js'

import { canPrescribe, canArchive, validateClinicalAction } from '../clinical/clinical-actions.js'

export const DEMO_PASSWORD = 'DEMO-no-utilizar'
const institutions = ['hospital', 'pediatrico', 'laboratorio', 'odontologica']
const normalized = value => value.trim().normalize('NFC').toLowerCase()
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0

export function createDemoClinicalService({ scenario = 'standard', role = 'medico', professionalEnabled = true, today = todayInGuatemala() } = {}) {
  let user = null
  const stores = new Map()
  let sequence = 0
  const medicines = [{ id: 'DEMO-M-1', nombre: 'DEMO · Medicamento ficticio', presentacion: null }]
  function writable(kind) {
    const records = store()
    if (!(kind === 'archive' ? canArchive(user) : canPrescribe(user)) || (kind !== 'archive' && !professionalEnabled)) {
      throw new ApiError(403, 'FORBIDDEN', 'Tu rol o vínculo profesional no permite esta operación.')
    }
    return records
  }
  function validate(kind, input) {
    const result = validateClinicalAction(kind, input)
    if (Object.keys(result.fields).length) throw new ApiError(400, 'VALIDATION_ERROR', 'Datos inválidos.', result.fields)
    return result.data
  }
  function append(kind, parentId, input) {
    const records = writable(kind)
    const data = validate(kind, input)
    for (const history of records.values()) {
      const candidates = kind === 'diagnosis' ? history.consultas
        : kind === 'treatment' ? history.consultas.flatMap(c => c.diagnosticos)
          : history.consultas.flatMap(c => c.diagnosticos.flatMap(d => d.tratamientos))
      const parent = candidates.find(row => row.id === parentId)
      if (!parent) continue
      if (history.paciente.estado !== 'activo') throw new ApiError(409, 'CONFLICT', 'El paciente no está activo.')
      if (kind === 'prescription' && !medicines.some(m => m.id === data.medicamento_id)) throw new ApiError(404, 'NOT_FOUND', 'Medicamento no encontrado.')
      const parentField = { diagnosis: 'consulta_id', treatment: 'diagnostico_id', prescription: 'tratamiento_id' }[kind]
      const row = { ...data, id: `DEMO-${user.institucion}-${kind}-${String(++sequence).padStart(8, '0')}`, [parentField]: parentId }
      if (kind === 'prescription') row.via_administracion ??= null
      const children = { diagnosis: 'diagnosticos', treatment: 'tratamientos', prescription: 'recetas' }[kind]
      const nested = { diagnosis: 'tratamientos', treatment: 'recetas' }[kind]
      parent[children].push(nested ? { ...row, [nested]: [] } : row)
      parent[children].sort((a, b) => compare(a.id, b.id))
      return structuredClone(row)
    }
    throw new ApiError(404, 'NOT_FOUND', 'Recurso no encontrado.')
  }
  function store() {
    if (!user) throw new ApiError(401, 'UNAUTHORIZED', 'Inicia sesión para continuar.')
    return stores.get(user.institucion)
  }
  return {
    mode: 'mock',
    specialtyDemo: createSpecialtyDemo({ getUser: () => user, getRecords: store, professionalEnabled, today }),
    createDiagnosis: async (id, data) => append('diagnosis', id, data),
    createTreatment: async (id, data) => append('treatment', id, data),
    createPrescription: async (id, data) => append('prescription', id, data),
    async listMedicines({ q = '', limit = 20, offset = 0 } = {}) {
      store()
      if (!canPrescribe(user)) throw new ApiError(403, 'FORBIDDEN', 'Acceso denegado.')
      if (typeof q !== 'string' || normalized(q).length > 100 || !Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0) throw new ApiError(400, 'VALIDATION_ERROR', 'Parámetros inválidos.')
      const rows = medicines.filter(m => normalized(m.nombre).startsWith(normalized(q)))
      return structuredClone({ count: rows.length, limit, offset, results: rows.slice(offset, offset + limit) })
    },
    async archivePatient(id, input) {
      const records = writable('archive')
      const { motivo } = validate('archive', input)
      const history = records.get(id)
      if (!history) throw new ApiError(404, 'NOT_FOUND', 'Recurso no encontrado.')
      if (history.paciente.estado === 'archivado') {
        if (history.paciente.motivo_archivo !== motivo) throw new ApiError(409, 'CONFLICT', 'El motivo de archivo es diferente.')
      } else Object.assign(history.paciente, { estado: 'archivado', motivo_archivo: motivo, fecha_archivo: today })
      return structuredClone(history.paciente)
    },
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
