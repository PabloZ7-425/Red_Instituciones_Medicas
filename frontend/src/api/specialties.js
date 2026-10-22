import { validateSpecialtyDemo } from '../clinical/specialty-demo.js'

export function createSpecialtyClient(request, ApiError) {
  const reads = new Set()
  let paused = false
  function startRead() {
    if (paused) throw new DOMException('Lectura cancelada', 'AbortError')
    const controller = new AbortController(); reads.add(controller); return controller
  }
  const path = id => `/pacientes/${encodeURIComponent(id)}`
  const invalid = () => { throw new ApiError(200, 'INVALID_RESPONSE', 'La especialización devolvió una respuesta no válida.') }
  async function allCatalog(route, signal) {
    const rows = []
    let offset = 0
    while (true) {
      const page = await request(`/${route}/?limit=100&offset=${offset}`, { signal })
      if (!page || !Number.isInteger(page.count) || page.count < 0 || page.limit !== 100 || page.offset !== offset || !Array.isArray(page.results) || page.results.length > 100 || page.results.some(row => typeof row?.id !== 'string' || !row.id.trim() || typeof row.nombre !== 'string' || !row.nombre.trim())) invalid()
      rows.push(...page.results)
      offset += 100
      if (offset >= page.count) return rows
      if (page.results.length === 0) invalid()
    }
  }
  function collection(response, key, patientId) {
    const rows = response?.[key]
    if (response?.paciente_id !== patientId || !Array.isArray(rows) || rows.some(row => typeof row?.id !== 'string' || !row.id || row.paciente_id !== patientId)) invalid()
    return rows
  }
  async function admissions(id, signal) { return collection(await request(`${path(id)}/ingresos/`, { signal }), 'ingresos', id) }
  async function treatments(id, signal) {
    const history = await request(`${path(id)}/historial/`, { signal })
    if (history?.paciente?.id !== id || !Array.isArray(history.consultas)) invalid()
    if (history.consultas.some(c => !c || typeof c.fecha !== 'string' || !Array.isArray(c.diagnosticos)
      || c.diagnosticos.some(d => !d || typeof d.codigo_cie10 !== 'string' || !Array.isArray(d.tratamientos)
        || d.tratamientos.some(t => !t || typeof t.id !== 'string' || !t.id || typeof t.indicaciones_generales !== 'string')))) invalid()
    return history.consultas.flatMap(c => c.diagnosticos.flatMap(d => d.tratamientos.map(t => ({ id: t.id, nombre: `${c.fecha} · ${d.codigo_cie10} · ${t.indicaciones_generales}` }))))
  }
  return {
    pauseReads() { paused = true; for (const controller of reads) controller.abort() },
    resumeReads() { paused = false },
    async catalog(kind, patientId) {
      const controller = startRead(), signal = controller.signal
      try {
      if (kind === 'admission') return allCatalog('camas', signal)
      if (kind === 'vaccine') return allCatalog('vacunas', signal)
      if (kind === 'result') return allCatalog('tipos-examen', signal)
      if (kind === 'procedure') return treatments(patientId, signal)
      if (kind === 'discharge') {
        const [rows, beds] = await Promise.all([admissions(patientId, signal), allCatalog('camas', signal)])
        return rows.filter(row => row.fecha_hora_alta === null).map(row => ({ id: row.id, nombre: `${beds.find(b => b.id === row.cama_id)?.nombre ?? 'Cama no disponible'} · ${row.fecha_hora_ingreso}` }))
      }
      return []
      } finally { reads.delete(controller) }
    },
    async list(id, user) {
      const controller = startRead(), signal = controller.signal
      try {
      if (user.institucion === 'hospital') {
        const [rows, beds] = await Promise.all([admissions(id, signal), allCatalog('camas', signal)])
        const decorated = rows.map(row => ({ ...row, cama_nombre: beds.find(b => b.id === row.cama_id)?.nombre ?? 'Cama no disponible' }))
        return { admission: decorated, discharge: decorated.filter(row => row.fecha_hora_alta !== null).map(row => ({ ...row, ingreso_id: row.id, ingreso_descripcion: `${row.cama_nombre} · ${row.fecha_hora_ingreso}` })) }
      }
      if (user.institucion === 'pediatrico') {
        const response = await request(`${path(id)}/${user.rol === 'secretaria' ? 'tutores' : 'seguimiento'}/`, { signal })
        const tutor = collection(response, 'tutores', id)
        if (user.rol === 'secretaria') return { tutor }
        const vaccines = await allCatalog('vacunas', signal)
        return { tutor, vaccine: collection(response, 'vacunas', id).map(row => ({ ...row, vacuna_nombre: vaccines.find(v => v.id === row.vacuna_id)?.nombre ?? 'Vacuna no disponible' })), growth: collection(response, 'crecimiento', id) }
      }
      if (user.institucion === 'laboratorio') {
        const [response, exams] = await Promise.all([request(`${path(id)}/resultados/`, { signal }), allCatalog('tipos-examen', signal)])
        return { result: collection(response, 'resultados', id).map(row => ({ ...row, tipo_examen_nombre: exams.find(e => e.id === row.tipo_examen)?.nombre ?? 'Examen no disponible' })) }
      }
      if (user.institucion === 'odontologica') {
        const [response, items] = await Promise.all([request(`${path(id)}/procedimientos/`, { signal }), treatments(id, signal)])
        return { procedure: collection(response, 'procedimientos', id).map(row => ({ ...row, tratamiento_descripcion: items.find(t => t.id === row.tratamiento_id)?.nombre ?? 'Tratamiento no disponible' })) }
      }
      invalid()
      } finally { reads.delete(controller) }
    },
    async save(kind, patientId, input) {
      const { data, fields } = validateSpecialtyDemo(kind, input)
      if (Object.keys(fields).length) throw new ApiError(400, 'VALIDATION_ERROR', 'Revisa los campos indicados.', fields)
      let route
      if (kind === 'discharge') {
        route = `/ingresos/${encodeURIComponent(data.ingreso_id)}/alta/`
        delete data.ingreso_id
      } else route = `${path(patientId)}/${{ admission: 'ingresos/nuevo', tutor: 'tutores/nuevo', vaccine: 'vacunas', growth: 'crecimiento', result: 'resultados/nuevo', procedure: 'procedimientos/nuevo' }[kind]}/`
      const row = await request(route, { method: 'POST', body: data })
      if (typeof row?.id !== 'string' || !row.id || row.paciente_id !== patientId) invalid()
      return row
    },
  }
}
