import { todayInGuatemala, validCivilDate } from './patient-form.js'

// El DTO /me no expone el vínculo profesional: el servidor debe comprobarlo.
export function canRegisterConsultation(user) {
  return ['admin', 'medico'].includes(user?.rol)
    || (user?.rol === 'laboratorista' && user?.institucion === 'laboratorio')
}

export function validateConsultationCreate(input, { today = todayInGuatemala() } = {}) {
  const data = {}
  const fields = {}
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return { data, fields: { non_field_errors: ['Se requieren los datos de la consulta.'] } }
  }
  if (typeof input.fecha !== 'string' || !validCivilDate(input.fecha)) fields.fecha = ['Introduce una fecha válida con formato AAAA-MM-DD.']
  else if (input.fecha > today) fields.fecha = ['La fecha de consulta no puede ser futura.']
  else data.fecha = input.fecha
  if (typeof input.notas_evolucion !== 'string' || !input.notas_evolucion.trim()) {
    fields.notas_evolucion = ['Las notas de evolución son obligatorias.']
  } else {
    data.notas_evolucion = input.notas_evolucion.trim()
    if ([...data.notas_evolucion].length > 5000) fields.notas_evolucion = ['Las notas admiten un máximo de 5000 caracteres.']
  }
  if (Object.hasOwn(input, 'cita_id')) {
    if (typeof input.cita_id !== 'string' || !input.cita_id.trim()) fields.cita_id = ['La cita debe tener un identificador válido o se debe omitir.']
    else data.cita_id = input.cita_id.trim()
  }
  for (const key of Object.keys(input)) {
    if (!['fecha', 'notas_evolucion', 'cita_id'].includes(key)) {
      Object.defineProperty(fields, key, { value: ['Campo no permitido.'], enumerable: true })
    }
  }
  return { data, fields }
}
