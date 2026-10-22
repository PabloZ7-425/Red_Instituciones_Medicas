import { useEffect, useId, useRef, useState } from 'react'
import { actionFields, validateClinicalAction } from './clinical-actions.js'

const titles = { diagnosis: 'Registrar diagnóstico', treatment: 'Registrar tratamiento', prescription: 'Registrar receta', archive: 'Archivar paciente' }
const methods = { diagnosis: 'createDiagnosis', treatment: 'createTreatment', prescription: 'createPrescription', archive: 'archivePatient' }

export default function ClinicalActionForm({ kind, parentId, service, onCreated, onCancel, onBusyChange, onSessionExpired }) {
  const id = useId(), form = useRef(null), inFlight = useRef(false)
  const [saving, setSaving] = useState(false), [fields, setFields] = useState({}), [message, setMessage] = useState('')
  const [query, setQuery] = useState({ q: '', offset: 0 }), [draft, setDraft] = useState('')
  const [page, setPage] = useState(null), [loading, setLoading] = useState(false), [catalogError, setCatalogError] = useState('')
  const [selected, setSelected] = useState(''), [retry, setRetry] = useState(0)
  useEffect(() => {
    form.current?.querySelector('input, textarea, select')?.focus()
  }, [])
  useEffect(() => {
    const first = Object.keys(actionFields[kind]).find(key => fields[key]) ?? (fields.confirmar ? 'confirmar' : null)
    if (!saving && first) form.current?.elements[first]?.focus()
  }, [fields, saving, kind])
  useEffect(() => {
    if (kind !== 'prescription') return
    const controller = new AbortController()
    let active = true
    setLoading(true); setPage(null); setCatalogError(''); setSelected('')
    service.listMedicines({ ...query, limit: 20, signal: controller.signal }).then(result => {
      if (active) setPage(result)
    }).catch(error => {
      if (!active || error.name === 'AbortError') return
      if (error.status === 401) onSessionExpired(error)
      else setCatalogError(error.message)
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false; controller.abort() }
  }, [kind, service, query, retry, onSessionExpired])

  async function submit(event) {
    event.preventDefault()
    if (inFlight.current) return
    const values = Object.fromEntries(new FormData(event.currentTarget))
    delete values.confirmar
    const { data, fields: errors } = validateClinicalAction(kind, values)
    if (kind === 'archive' && !event.currentTarget.elements.confirmar.checked) errors.confirmar = ['Confirma que deseas archivar conservando la historia.']
    if (kind === 'prescription' && (!page?.results.some(m => m.id === data.medicamento_id) || loading || catalogError)) errors.medicamento_id = ['Selecciona un medicamento del catálogo disponible.']
    if (Object.keys(errors).length) { setFields(errors); setMessage('Revisa los campos indicados.'); return }
    inFlight.current = true; setSaving(true); onBusyChange(true); setFields({}); setMessage('')
    try {
      const result = await service[methods[kind]](parentId, data)
      onCreated(result)
    } catch (error) {
      if (error.status === 401) onSessionExpired(error)
      else {
        setFields(error.fields ?? {})
        setMessage(error.status === 0 || error.code === 'INVALID_RESPONSE'
          ? 'No se pudo confirmar el resultado. Actualiza el historial antes de repetir el envío.'
          : error.status === 409 ? 'El estado del paciente cambió o existe un conflicto. Actualiza el historial antes de continuar.' : error.message)
      }
    } finally { inFlight.current = false; setSaving(false); onBusyChange(false) }
  }
  return <section className="consultation-form" aria-labelledby={`${id}-title`}>
    <h3 id={`${id}-title`}>{titles[kind]}</h3>
    {kind === 'prescription' && <div aria-label="Catálogo de medicamentos">
      <label htmlFor={`${id}-search`}>Buscar medicamento por inicio del nombre</label>
      <input id={`${id}-search`} value={draft} maxLength={100} disabled={saving} onChange={e => setDraft(e.target.value)} />
      <button type="button" disabled={saving || loading} onClick={() => setQuery({ q: draft.trim(), offset: 0 })}>Buscar medicamento</button>
      {loading && <p role="status">Cargando medicamentos…</p>}
      {catalogError && <div role="alert"><p>{catalogError}</p><button type="button" disabled={saving} onClick={() => setRetry(v => v + 1)}>Reintentar catálogo</button></div>}
      {page && <><p role="status">{page.count ? `${page.count} medicamentos encontrados` : 'No hay medicamentos que coincidan.'}</p>
        <button type="button" disabled={saving || query.offset === 0} onClick={() => setQuery({ ...query, offset: Math.max(0, query.offset - 20) })}>Medicamentos anteriores</button>
        <button type="button" disabled={saving || query.offset + page.limit >= page.count} onClick={() => setQuery({ ...query, offset: query.offset + 20 })}>Más medicamentos</button></>}
    </div>}
    {message && <div role="alert" className="error-message">{message}
      {Object.entries(fields).filter(([key]) => !Object.hasOwn(actionFields[kind], key)).map(([key, errors]) => <p key={key} id={`${id}-error-${key}`}>{Array.isArray(errors) ? errors.join(' ') : ''}</p>)}
    </div>}
    <form ref={form} onSubmit={submit} noValidate aria-busy={saving}>
      {Object.entries(actionFields[kind]).map(([name, [label, maximum]]) => <div key={name}>
        <label htmlFor={`${id}-${name}`}>{label}</label>
        {name === 'medicamento_id' ? <select id={`${id}-${name}`} name={name} required value={selected} disabled={saving || loading || !!catalogError} onChange={e => setSelected(e.target.value)} aria-invalid={!!fields[name]} aria-describedby={fields[name] ? `${id}-error-${name}` : undefined}>
          <option value="">Selecciona un medicamento</option>
          {page?.results.map(m => <option key={m.id} value={m.id}>{m.nombre}{m.presentacion ? ` · ${m.presentacion}` : ''}</option>)}
        </select> : maximum > 200 ? <textarea id={`${id}-${name}`} name={name} maxLength={maximum} rows={4} disabled={saving} required aria-invalid={!!fields[name]} aria-describedby={fields[name] ? `${id}-error-${name}` : undefined} />
          : <input id={`${id}-${name}`} name={name} maxLength={maximum} disabled={saving} required={name !== 'via_administracion'} aria-invalid={!!fields[name]} aria-describedby={fields[name] ? `${id}-error-${name}` : undefined} />}
        {fields[name] && <p id={`${id}-error-${name}`} className="field-error">{fields[name].join(' ')}</p>}
      </div>)}
      {kind === 'archive' && <label><input name="confirmar" type="checkbox" disabled={saving} aria-invalid={!!fields.confirmar} aria-describedby={fields.confirmar ? `${id}-error-confirmar` : undefined} /> Confirmo el archivo. Se conservará el historial y no se permitirán nuevas escrituras clínicas.</label>}
      <div className="form-actions"><button disabled={saving || (kind === 'prescription' && (loading || !!catalogError || !page?.results.length))}>{saving ? 'Guardando…' : titles[kind]}</button>
        <button type="button" disabled={saving} onClick={onCancel}>Cancelar</button></div>
    </form>
  </section>
}
