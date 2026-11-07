export function resultTemplate(examName) {
  const name = examName.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  let fields
  if (/hematolog|hemograma/.test(name)) fields = [['Hemoglobina', 'numero'], ['Hematocrito', 'numero'], ['Leucocitos', 'numero']]
  else if (/orina|uroanalisis/.test(name)) fields = [['Aspecto', 'texto'], ['pH', 'numero'], ['Densidad', 'numero']]
  else if (/cultivo/.test(name)) fields = [['Crecimiento', 'booleano'], ['Microorganismo', 'texto']]
  return fields?.map(([nombre, tipo], index) => ({ key: `suggested-${index}`, nombre, tipo, valor: '', unidad: '', rango: '' }))
}

export function outsideReference(value, reference) {
  if (typeof value !== 'number' || !Number.isFinite(value) || typeof reference !== 'string') return false
  const interval = reference.match(/^\s*(-?\d+(?:[.,]\d+)?)\s*(?:-|–|a)\s*(-?\d+(?:[.,]\d+)?)\s*$/)
  if (!interval) return false
  const [lower, upper] = interval.slice(1).map(number => Number(number.replace(',', '.')))
  return lower <= upper && (value < lower || value > upper)
}
