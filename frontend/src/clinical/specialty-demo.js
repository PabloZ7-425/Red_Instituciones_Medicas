// Shared editor fields/validation for SPECIALTY-API-01 and the explicit DEMO.
// Export names are retained from the earlier UI prototype; transport is separate.
import { validCivilDate, todayInGuatemala } from './patient-form.js'

const text = (label, max = 100, optional = false) => ({ label, type: 'text', max, optional })
const date = { label: 'Fecha', type: 'date' }
const timestamp = label => ({ label, type: 'utc' })
const catalog = label => ({ label, type: 'catalog' })
export const specialtyActions = {
  admission: { institution: 'hospital', title: 'Registrar ingreso', section: 'Ingresos', fields: {
    cama_id: catalog('Cama'), fecha_hora_ingreso: timestamp('Fecha y hora de ingreso (Guatemala)'), tipo_ingreso: text('Tipo de ingreso', 50),
  } },
  discharge: { institution: 'hospital', title: 'Registrar alta hospitalaria', section: 'Altas', fields: {
    ingreso_id: catalog('Ingreso abierto'), fecha_hora_alta: timestamp('Fecha y hora de alta (Guatemala)'),
  } },
  tutor: { institution: 'pediatrico', title: 'Registrar tutor', section: 'Tutores', fields: {
    nombres: text('Nombres'), apellidos: text('Apellidos'), parentesco: text('Parentesco'), telefono: text('Teléfono', 100, true), correo: text('Correo', 150, true), dpi: text('DPI', 100, true),
  } },
  vaccine: { institution: 'pediatrico', title: 'Registrar vacuna', section: 'Vacunas', fields: {
    vacuna_id: catalog('Vacuna'), fecha: date, dosis: { label: 'Número de dosis', type: 'integer' }, lote: text('Lote', 100, true), observaciones: text('Observaciones', 5000, true),
  } },
  growth: { institution: 'pediatrico', title: 'Registrar crecimiento', section: 'Crecimiento', fields: {
    fecha: date, peso_kg: { label: 'Peso (kg)', type: 'decimal' }, talla_cm: { label: 'Talla (cm)', type: 'decimal' }, observaciones: text('Observaciones', 5000, true),
  } },
  result: { institution: 'laboratorio', title: 'Registrar resultado', section: 'Resultados de exámenes', fields: {
    tipo_examen: catalog('Tipo de examen'), fecha: timestamp('Fecha y hora del resultado (Guatemala)'),
    estado: { label: 'Estado', type: 'choice', options: ['pendiente', 'en_proceso', 'finalizado', 'anulado'] }, campos: { label: 'Campos del resultado', type: 'resultFields' },
  } },
  procedure: { institution: 'odontologica', title: 'Registrar procedimiento', section: 'Procedimientos odontológicos', fields: {
    tratamiento_id: catalog('Tratamiento de esta historia'), pieza: { label: 'Pieza dental FDI', type: 'choice', options: Array.from({ length: 8 }, (_, q) => Array.from({ length: q < 4 ? 8 : 5 }, (_, p) => String((q + 1) * 10 + p + 1))).flat() },
    descripcion: text('Descripción', 5000), estado: { label: 'Estado', type: 'choice', options: ['pendiente', 'realizado'] },
  } },
}

export function canWriteSpecialtyDemo(user, kind) {
  const action = specialtyActions[kind]
  return !!action && user?.institucion === action.institution && (
    ['admin', 'medico'].includes(user.rol) || (kind === 'tutor' && user.rol === 'secretaria') || (kind === 'result' && user.rol === 'laboratorista')
  )
}

export function validateSpecialtyDemo(kind, input, { today = todayInGuatemala(), now = new Date().toISOString(), birth } = {}) {
  const action = specialtyActions[kind], data = {}, fields = {}
  if (!action || !input || typeof input !== 'object' || Array.isArray(input)) return { data, fields: { non_field_errors: ['Datos inválidos.'] } }
  for (const [name, field] of Object.entries(action.fields)) {
    const raw = input[name]
    if (field.optional && (raw === undefined || raw === '')) continue
    let value = typeof raw === 'string' ? raw.trim() : raw
    let valid = true
    if (field.type === 'resultFields') {
      valid = Array.isArray(raw) && raw.length > 0 && raw.length <= 50
      const names = new Set()
      value = []
      if (valid) for (const row of raw) {
        if (!row || typeof row !== 'object' || Array.isArray(row) || Object.keys(row).some(k => !['nombre', 'tipo', 'valor', 'unidad', 'rango'].includes(k))) { valid = false; break }
        const name = typeof row.nombre === 'string' ? row.nombre.trim() : ''
        if (!name || name.length > 100 || names.has(name) || !['texto', 'numero', 'booleano'].includes(row.tipo)) { valid = false; break }
        names.add(name)
        let result = row.valor
        if (typeof result !== 'string' || !result.trim() || result.length > 5000) { valid = false; break }
        if (row.tipo === 'numero') {
          if (!/^-?\d+(?:\.\d+)?$/.test(result.trim()) || !Number.isFinite(Number(result))) { valid = false; break }
          result = Number(result)
        } else if (row.tipo === 'booleano') {
          if (!['true', 'false'].includes(result)) { valid = false; break }
          result = result === 'true'
        } else result = result.trim()
        const converted = { nombre: name, valor: result }
        for (const key of ['unidad', 'rango']) {
          if (row[key] !== undefined && (typeof row[key] !== 'string' || row[key].length > 100)) valid = false
          else if (row[key]?.trim()) converted[key] = row[key].trim()
        }
        value.push(converted)
      }
    } else if (field.type === 'integer') {
      valid = typeof raw === 'string' && /^[1-9]\d*$/.test(value) && Number.isSafeInteger(Number(value)) && Number(value) <= 2147483647
      value = Number(value)
    } else if (field.type === 'decimal') {
      valid = typeof raw === 'string' && /^\d{1,4}(?:\.\d{1,2})?$/.test(value) && Number(value) > 0 && Number(value) <= 9999.99
      if (valid) value = Number(value).toFixed(2)
    } else if (field.type === 'date') {
      valid = typeof raw === 'string' && validCivilDate(value) && value <= today && (!birth || value >= birth)
    } else if (field.type === 'utc') {
      valid = typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value)
      if (valid) {
        const parsed = new Date(value)
        valid = Number.isFinite(parsed.getTime()) && parsed.toISOString() === (value.includes('.') ? value : value.replace('Z', '.000Z')) && parsed.getTime() <= new Date(now).getTime()
      }
    } else {
      valid = typeof raw === 'string' && !!value && (field.type !== 'choice' || field.options.includes(value)) && (field.type !== 'text' || [...value].length <= field.max)
      if (field.type === 'catalog') value = raw // IDs remain opaque.
    }
    if (valid) data[name] = value
    else fields[name] = [`${field.label}: revisa el valor indicado.`]
  }
  if (kind === 'tutor' && data.correo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.correo)) fields.correo = ['Introduce un correo válido.']
  if (Object.keys(input).some(key => !Object.hasOwn(action.fields, key))) fields.non_field_errors = ['Hay campos no permitidos.']
  return { data, fields }
}
