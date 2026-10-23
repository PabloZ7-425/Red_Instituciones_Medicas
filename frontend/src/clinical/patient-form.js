// Fechas civiles: nunca construir Date desde el valor introducido por el paciente.
export function todayInGuatemala(now = new Date()) {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: 'America/Guatemala', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now)
  const get = type => parts.find(part => part.type === type).value
  return `${get('year')}-${get('month')}-${get('day')}`
}

export function canRegisterPatient(user) {
  return ['admin', 'medico', 'secretaria'].includes(user?.rol)
    || (user?.rol === 'laboratorista' && user?.institucion === 'laboratorio')
}

export function validCivilDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const [year, month, day] = value.split('-').map(Number)
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  return year >= 1 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1]
}

export function validatePatientCreate(input, { today = todayInGuatemala() } = {}) {
  const fields = {}
  const data = {}
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return { data, fields: { non_field_errors: ['Se requiere un objeto con los datos del paciente.'] } }
  }
  const names = { identificacion: ['Identificación', 20], nombres: ['Nombres', 100], apellidos: ['Apellidos', 100] }
  for (const [key, [label, max]] of Object.entries(names)) {
    if (typeof input[key] !== 'string' || !input[key].trim()) fields[key] = [`${label}: este campo es obligatorio.`]
    else {
      data[key] = input[key].trim()
      if ([...data[key]].length > max) fields[key] = [`${label}: máximo ${max} caracteres.`]
    }
  }
  const birth = input.fecha_nacimiento
  if (typeof birth !== 'string' || !validCivilDate(birth)) {
    fields.fecha_nacimiento = ['Introduce una fecha válida con formato AAAA-MM-DD.']
  } else if (birth > today) {
    fields.fecha_nacimiento = ['La fecha de nacimiento no puede ser futura.']
  } else data.fecha_nacimiento = birth
  for (const key of Object.keys(input)) {
    if (!Object.hasOwn(names, key) && key !== 'fecha_nacimiento') {
      Object.defineProperty(fields, key, { value: ['Campo no permitido.'], enumerable: true })
    }
  }
  return { data, fields }
}
