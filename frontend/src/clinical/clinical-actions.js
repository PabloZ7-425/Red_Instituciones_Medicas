export const canPrescribe = user => ['admin', 'medico'].includes(user?.rol)
export const canArchive = user => user?.rol === 'admin'
export const actionFields = {
  diagnosis: { codigo_cie10: ['Código CIE-10', 20], descripcion: ['Descripción', 5000] },
  treatment: { indicaciones_generales: ['Indicaciones generales', 5000] },
  prescription: { medicamento_id: ['Medicamento', null], dosis: ['Dosis', 100], frecuencia: ['Frecuencia', 100], via_administracion: ['Vía de administración (opcional)', 100] },
  archive: { motivo: ['Motivo del archivo', 200] },
}
export function validateClinicalAction(kind, input) {
  const schema = actionFields[kind]
  if (!schema) throw new Error('Operación desconocida')
  const fields = {}, data = {}
  if (!input || typeof input !== 'object' || Array.isArray(input)) return { data, fields: { body: ['Se requiere un objeto.'] } }
  if (Object.keys(input).some(key => !Object.hasOwn(schema, key))) fields.body = ['Campos no permitidos.']
  for (const [key, [, maximum]] of Object.entries(schema)) {
    const value = input[key]
    if (key === 'via_administracion' && (value === undefined || value === '')) continue
    if (typeof value !== 'string' || !value.trim()) fields[key] = ['Completa este campo.']
    else if (maximum && [...value.trim()].length > maximum) fields[key] = [`Máximo ${maximum} caracteres.`]
    else data[key] = key === 'medicamento_id' ? value : value.trim()
  }
  return { data, fields }
}
