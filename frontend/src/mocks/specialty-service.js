import { ApiError } from '../api/clinical.js'
import { canWriteSpecialtyDemo, specialtyActions, validateSpecialtyDemo } from '../clinical/specialty-demo.js'

// Entirely ephemeral. No HTTP routes, backend fallback, seed or production data.
export function createSpecialtyDemo({ getUser, getRecords, professionalEnabled, today }) {
  const stores = new Map()
  let sequence = 0
  const catalogs = {
    admission: [{ id: 'DEMO-BED-1', nombre: 'DEMO · Cama 1' }, { id: 'DEMO-BED-2', nombre: 'DEMO · Cama 2' }],
    vaccine: [{ id: 'DEMO-VACCINE-1', nombre: 'DEMO · Vacuna ficticia (no aplicar)' }],
    result: [{ id: 'DEMO-EXAM-1', nombre: 'DEMO · Examen ficticio' }],
  }
  function context(patientId) {
    const records = getRecords(), user = getUser()
    if (user.rol === 'secretaria' && user.institucion !== 'pediatrico') throw new ApiError(403, 'FORBIDDEN', 'Acceso denegado.')
    const history = records.get(patientId)
    if (!history) throw new ApiError(404, 'NOT_FOUND', 'Recurso no encontrado.')
    if (!stores.has(user.institucion)) stores.set(user.institucion, new Map())
    const institution = stores.get(user.institucion)
    if (!institution.has(patientId)) institution.set(patientId, Object.fromEntries(Object.keys(specialtyActions).map(k => [k, []])))
    return { history, user, rows: institution.get(patientId), institution }
  }
  function catalog(kind, patientId) {
    const { history, rows, user } = context(patientId)
    if (!canWriteSpecialtyDemo(user, kind)) throw new ApiError(403, 'FORBIDDEN', 'Acceso denegado.')
    if (kind === 'discharge') return rows.admission.filter(row => row.fecha_hora_alta === null).map(row => ({ id: row.id, nombre: `${catalogs.admission.find(b => b.id === row.cama_id)?.nombre} · ${row.fecha_hora_ingreso}` }))
    if (kind === 'procedure') return history.consultas.flatMap(c => c.diagnosticos.flatMap(d => d.tratamientos.map(t => ({ id: t.id, nombre: `${c.fecha} · ${d.codigo_cie10} · ${t.indicaciones_generales}` }))))
    return catalogs[kind] ?? []
  }
  return {
    async list(patientId) {
      const { rows, user } = context(patientId)
      return structuredClone(user.rol === 'secretaria' ? { tutor: rows.tutor } : rows)
    },
    async catalog(kind, patientId) { return structuredClone(catalog(kind, patientId)) },
    async save(kind, patientId, input) {
      getRecords() // Authenticate before kind/parent validation.
      if (!canWriteSpecialtyDemo(getUser(), kind) || (kind !== 'tutor' && !professionalEnabled)) throw new ApiError(403, 'FORBIDDEN', 'Tu rol o vínculo profesional no permite esta operación.')
      const { history, rows, institution } = context(patientId)
      if (history.paciente.estado !== 'activo') throw new ApiError(409, 'CONFLICT', 'El paciente no está activo.')
      const { data, fields } = validateSpecialtyDemo(kind, input, { today, birth: history.paciente.fecha_nacimiento })
      if (Object.keys(fields).length) throw new ApiError(400, 'VALIDATION_ERROR', 'Revisa los campos indicados.', fields)
      const reference = Object.keys(specialtyActions[kind].fields).find(key => specialtyActions[kind].fields[key].type === 'catalog')
      // Discharge idempotency must still resolve an already closed admission.
      if (kind === 'discharge') {
        const admission = rows.admission.find(row => row.id === data.ingreso_id)
        if (!admission) throw new ApiError(404, 'NOT_FOUND', 'Ingreso no encontrado.')
        if (new Date(data.fecha_hora_alta) < new Date(admission.fecha_hora_ingreso)) throw new ApiError(400, 'VALIDATION_ERROR', 'El alta no puede ser anterior al ingreso.', { fecha_hora_alta: ['Revisa la fecha.'] })
        if (admission.fecha_hora_alta) {
          if (new Date(admission.fecha_hora_alta).getTime() !== new Date(data.fecha_hora_alta).getTime()) throw new ApiError(409, 'CONFLICT', 'El ingreso ya tiene otra fecha de alta.')
          return structuredClone(rows.discharge.find(row => row.ingreso_id === admission.id))
        }
        admission.fecha_hora_alta = data.fecha_hora_alta
      } else if (reference && !catalog(kind, patientId).some(row => row.id === data[reference])) throw new ApiError(404, 'NOT_FOUND', 'Selección no encontrada.')
      if (kind === 'admission' && ([...institution.values()].some(record => record.admission.some(row => row.cama_id === data.cama_id && !row.fecha_hora_alta)) || rows.admission.some(row => !row.fecha_hora_alta))) throw new ApiError(409, 'CONFLICT', 'La cama o el paciente ya tienen un ingreso abierto.')
      const row = { ...data, id: `DEMO-SPECIALTY-${++sequence}`, paciente_id: patientId }
      if (kind === 'admission') { row.fecha_hora_alta = null; row.cama_nombre = catalogs.admission.find(b => b.id === row.cama_id).nombre }
      if (kind === 'discharge') { const admission = rows.admission.find(a => a.id === row.ingreso_id); row.ingreso_descripcion = `${admission.cama_nombre} · ${admission.fecha_hora_ingreso}` }
      if (kind === 'procedure') {
        row.consulta_id = history.consultas.find(c => c.diagnosticos.some(d => d.tratamientos.some(t => t.id === data.tratamiento_id))).id
        row.tratamiento_descripcion = catalog(kind, patientId).find(t => t.id === row.tratamiento_id).nombre
      }
      if (kind === 'tutor') {
        row.tutor_id = `DEMO-TUTOR-${sequence}`
        for (const key of ['telefono', 'correo', 'dpi']) row[key] ??= null
      }
      if (kind === 'result') row.tipo_examen_nombre = catalogs.result.find(e => e.id === row.tipo_examen).nombre
      if (kind === 'vaccine') row.vacuna_nombre = catalogs.vaccine.find(v => v.id === row.vacuna_id).nombre
      if (kind === 'vaccine') for (const key of ['lote', 'observaciones']) row[key] ??= null
      if (kind === 'growth') row.observaciones ??= null
      rows[kind].push(row)
      return structuredClone(row)
    },
  }
}
