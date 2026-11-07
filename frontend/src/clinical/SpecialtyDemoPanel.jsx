import { useEffect, useId, useRef, useState } from 'react'
import { institutionProfile } from '../features/institutions.js'
import TaskDialog from './TaskDialog.jsx'
import { localNow, localToUtc } from '../operations/helpers.js'
import { todayInGuatemala } from './patient-form.js'
import { canWriteSpecialtyDemo, specialtyActions, validateSpecialtyDemo } from './specialty-demo.js'

function SpecialtyForm({ kind, history, service, onCreated, onCancel, onBusyChange, onSessionExpired }) {
  const id = useId(), form = useRef(null), inFlight = useRef(false)
  const [saving, setSaving] = useState(false), [errors, setErrors] = useState({}), [message, setMessage] = useState('')
  const [catalog, setCatalog] = useState(null), [loading, setLoading] = useState(false), [catalogError, setCatalogError] = useState(''), [retry, setRetry] = useState(0)
  const [results, setResults] = useState([{ key: 'first', nombre: '', tipo: 'texto', valor: '', unidad: '', rango: '' }])
  const [examName, setExamName] = useState('')
  const action = specialtyActions[kind]
  const { ResultFields, resultTemplate, fieldControls } = institutionProfile(action.institution)
  const suggested = kind === 'result' && examName ? resultTemplate?.(examName) : null
  const specialty = service.specialty ?? service.specialtyDemo
  const suffix = service.mode === 'mock' ? ' · DEMO' : ''
  const catalogField = Object.keys(action.fields).find(key => action.fields[key].type === 'catalog')
  useEffect(() => { form.current?.querySelector('input, textarea, select')?.focus() }, [])
  useEffect(() => {
    if (!catalogField) return
    let active = true
    setLoading(true); setCatalog(null); setCatalogError('')
    specialty.catalog(kind, history.paciente.id).then(rows => { if (active) setCatalog(rows) }).catch(error => {
      if (active && error.status === 401) onSessionExpired(error)
      else if (active && error.name !== 'AbortError') setCatalogError(error.message)
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [service, kind, history.paciente.id, catalogField, retry, onSessionExpired])
  useEffect(() => {
    const first = Object.keys(action.fields).find(name => errors[name])
    if (first && !saving) {
      const element = form.current?.elements[first]
      if (element?.focus) element.focus()
      else form.current?.querySelector('fieldset input')?.focus()
    }
  }, [errors, saving, action])
  async function submit(event) {
    event.preventDefault()
    if (inFlight.current) return
    const input = Object.fromEntries(new FormData(event.currentTarget))
    const confirmed = input.confirmar_ingreso === 'on'
    delete input.confirmar_ingreso
    for(const [name,field] of Object.entries(action.fields)) if(field.type==='utc' && input[name] && !input[name].endsWith('Z')) input[name]=localToUtc(input[name])
    if (kind === 'result') input.campos = results.map(({ key, ...row }) => row)
    const { fields } = validateSpecialtyDemo(kind, input, { birth: history.paciente.fecha_nacimiento })
    if (kind === 'admission' && !confirmed) fields.confirmar_ingreso = ['Confirma el ingreso del paciente en la cama seleccionada.']
    if (catalogField && (!catalog?.some(row => row.id === input[catalogField]) || loading || catalogError)) fields[catalogField] = ['Selecciona una opción disponible.']
    if (Object.keys(fields).length) { setErrors(fields); setMessage('Revisa los campos indicados.'); return }
    inFlight.current = true; setSaving(true); onBusyChange(true); setErrors({}); setMessage('')
    try { await specialty.save(kind, history.paciente.id, input); onCreated() }
    catch (error) {
      if (error.status === 401) onSessionExpired(error)
      else { setErrors(error.fields ?? {}); setMessage(error.status === 409 ? 'El estado cambió o existe un conflicto. Actualiza el historial antes de continuar.' : error.status === 0 || error.code === 'INVALID_RESPONSE' ? 'No se pudo confirmar el resultado. Actualiza el historial antes de repetir el envío.' : error.message) }
    } finally { inFlight.current = false; setSaving(false); onBusyChange(false) }
  }
  return <TaskDialog title={action.title} busy={saving} onCancel={onCancel}><section aria-labelledby={`${id}-title`} className="consultation-form"><h4 id={`${id}-title`}>{action.title}{suffix}</h4>
    <p className="task-patient-context">Paciente · {history.paciente.nombres} {history.paciente.apellidos} · {history.paciente.identificacion}</p>
    {message && <p role="alert">{message}</p>}
    {loading && <p role="status">Cargando opciones…</p>}
    {catalogError && <p role="alert">{catalogError} <button type="button" disabled={saving} onClick={() => setRetry(v => v + 1)}>Reintentar opciones</button></p>}
    {!loading && catalog && !catalog.length && <p role="status">No hay opciones disponibles para este registro.</p>}
    <form ref={form} onSubmit={submit} noValidate aria-busy={saving}>
      {Object.entries(action.fields).map(([name, field]) => {
        const FieldControl = fieldControls?.[name]
        return <div key={name}>
          {field.type !== 'resultFields' && <label htmlFor={`${id}-${name}`}>{field.label}{field.optional ? ' (opcional)' : ''}</label>}
          {FieldControl ? <FieldControl id={`${id}-${name}`} name={name} options={field.options} disabled={saving}
            errorId={errors[name] ? `${id}-error-${name}` : undefined} />
            : field.type === 'resultFields' ? <>
              {suggested && !results.some(row => row.nombre || row.valor !== '' || row.unidad || row.rango) &&
                <button type="button" className="text-button" disabled={saving} onClick={() => setResults(suggested)}>Usar campos sugeridos para {examName}</button>}
              <ResultFields value={results} onChange={setResults} disabled={saving} errorId={errors[name] ? `${id}-error-${name}` : undefined} />
            </>
            : ['catalog', 'choice'].includes(field.type) ? <select id={`${id}-${name}`} name={name} disabled={saving || (field.type === 'catalog' && (loading || !!catalogError))} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${id}-error-${name}` : undefined} defaultValue=""
              onChange={kind === 'result' && field.type === 'catalog' ? event => setExamName(catalog?.find(row => row.id === event.target.value)?.nombre ?? '') : undefined}>
              <option value="">Selecciona</option>{(field.type === 'catalog' ? catalog ?? [] : field.options.map(value => ({ id: value, nombre: value }))).map(row => <option value={row.id} key={row.id}>{row.nombre}</option>)}
            </select> : field.max > 200 ? <textarea id={`${id}-${name}`} name={name} maxLength={field.max} disabled={saving} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${id}-error-${name}` : undefined} />
              : <input id={`${id}-${name}`} name={name} defaultValue={field.type==='date'?todayInGuatemala():field.type==='utc'?localNow():undefined} step={field.type==='utc'?1:undefined} type={field.type === 'date' ? 'date' : field.type==='utc'?'datetime-local':'text'} maxLength={field.max ?? 100} inputMode={['decimal', 'integer'].includes(field.type) ? 'decimal' : undefined} disabled={saving} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${id}-error-${name}` : undefined} />}
          {errors[name] && <p id={`${id}-error-${name}`} className="field-error">{errors[name].join(' ')}</p>}
        </div>
      })}
      {kind === 'admission' && <div>
        <label><input type="checkbox" name="confirmar_ingreso" disabled={saving} aria-invalid={!!errors.confirmar_ingreso}
          aria-describedby={errors.confirmar_ingreso ? `${id}-error-confirmar` : undefined} /> Confirmo el ingreso del paciente en la cama seleccionada.</label>
        {errors.confirmar_ingreso && <p id={`${id}-error-confirmar`} className="field-error">{errors.confirmar_ingreso[0]}</p>}
      </div>}
      <button disabled={saving || loading || !!catalogError || (!!catalogField && !catalog?.length)}>{saving ? 'Guardando…' : `Guardar especialización${service.mode === 'mock' ? ' DEMO' : ''}`}</button>
      <button type="button" disabled={saving} onClick={onCancel}>Cancelar especialización</button>
    </form>
  </section></TaskDialog>
}

function Record({ row, kind }) {
  const { RecordDetails } = institutionProfile(specialtyActions[kind].institution)
  return <dl>{Object.entries(specialtyActions[kind].fields).filter(([name, field]) => !['catalog', 'resultFields'].includes(field.type) && row[name] != null).map(([name, field]) => <div key={name}><dt>{field.label}</dt><dd className="preserve-lines">{field.type==='utc'?localNow(new Date(row[name])).replace('T',' ')+' (Guatemala)':String(row[name])}</dd></div>)}
    {RecordDetails && <RecordDetails row={row} kind={kind} />}
  </dl>
}

function DefaultSpecialtySection({ action, children }) {
  return <section><h4>{action.section}</h4>{children}</section>
}

export default function SpecialtyDemoPanel({ history, user, service, editor, onEdit, onCreated, busy, onBusyChange, onSessionExpired, summaryOnly, sectionKind }) {
  const specialty = service.specialty ?? service.specialtyDemo
  const suffix = service.mode === 'mock' ? ' · DEMO' : ''
  const [rows, setRows] = useState(null), [error, setError] = useState(''), [retry, setRetry] = useState(0)
  const [section, setSection] = useState(sectionKind ?? 'all')
  useEffect(() => { setSection(sectionKind ?? 'all') }, [sectionKind])
  useEffect(() => {
    let active = true
    setRows(null); setError('')
    specialty.list(history.paciente.id, user).then(result => { if (active) setRows(result) }).catch(failure => {
      if (active && failure.status === 401) onSessionExpired(failure)
      else if (active && failure.name !== 'AbortError') setError(failure.message)
    })
    return () => { active = false }
  }, [service, history, retry, onSessionExpired])
  const profile = institutionProfile(user.institucion)
  const { FollowUpSummary } = profile
  const Section = profile.SpecialtySection ?? DefaultSpecialtySection
  const actions = Object.entries(specialtyActions).filter(([kind, action]) => action.institution === user.institucion && (user.rol !== 'secretaria' || kind === 'tutor'))
  if (summaryOnly) return <section className="specialty-summary" aria-label="Resumen institucional">
    <h3>Seguimiento institucional</h3>
    {!rows && !error && <p role="status">Cargando seguimiento…</p>}
    {error && <p role="alert">No se pudo cargar el seguimiento. <button type="button" className="text-button" onClick={() => setRetry(value => value + 1)}>Reintentar</button></p>}
    {rows && <dl>{actions.map(([kind, action]) => <div key={kind}><dt>{action.section}</dt><dd>
      {kind === 'tutor' && rows.tutor?.length ? rows.tutor.map(tutor => `${tutor.nombres} ${tutor.apellidos}`).join(', ') : (rows[kind]?.length ?? 0)}
    </dd></div>)}</dl>}
  </section>
  return <section aria-label={service.mode === 'mock' ? 'Especialización DEMO' : 'Especialización institucional'}><h3>Especialización institucional{suffix}</h3>
    <p>Paciente: {history.paciente.nombres} {history.paciente.apellidos} · {history.paciente.identificacion}</p>
    {service.mode === 'mock' && <p className="notice">Simulación local: estos registros no se envían al servidor y se pierden al recargar.</p>}
    {!rows && !error && <p role="status">Cargando especialización…</p>}
    {error && <p role="alert">{error} <button disabled={busy} onClick={() => setRetry(v => v + 1)}>Reintentar especialización</button></p>}
    {rows && FollowUpSummary && <FollowUpSummary rows={rows} />}
    {rows && user.institucion === 'pediatrico' && actions.length > 1 && <nav className="section-tabs" aria-label="Seguimiento pediátrico">
      <button type="button" disabled={busy} aria-current={section === 'all' ? 'page' : undefined} onClick={() => setSection('all')}>Ver todo</button>
      {actions.map(([kind, action]) => <button key={kind} type="button" disabled={busy}
        aria-current={section === kind ? 'page' : undefined} onClick={() => setSection(kind)}>{action.section}</button>)}
    </nav>}
    {rows && actions.filter(([kind]) => section === 'all' || section === kind).map(([kind, action]) => <Section key={kind} kind={kind} action={action} rows={rows[kind] ?? []}>
      {!rows[kind]?.length && <p>Sin registros de {action.section.toLowerCase()}.</p>}
      <ul>{rows[kind]?.map(row => <li key={row.id}><Record row={row} kind={kind} /></li>)}</ul>
      {history.paciente.estado === 'activo' && canWriteSpecialtyDemo(user, kind) && <button disabled={busy} type="button" onClick={() => onEdit(kind)}>{action.title}{suffix}</button>}
    </Section>)}
    {editor && <SpecialtyForm key={editor} kind={editor} history={history} service={service} onCreated={() => { onEdit(null); setRetry(v => v + 1); onCreated(service.mode === 'mock' ? 'Especialización guardada solo en la demostración local.' : 'Registro especializado guardado correctamente.') }}
      onCancel={() => onEdit(null)} onBusyChange={onBusyChange} onSessionExpired={onSessionExpired} />}
  </section>
}
