import { useEffect, useId, useRef, useState } from 'react'
import TaskDialog from './TaskDialog.jsx'
import { localNow, localToUtc } from '../operations/helpers.js'
import { todayInGuatemala } from './patient-form.js'
import { canWriteSpecialtyDemo, specialtyActions, validateSpecialtyDemo } from './specialty-demo.js'

function ResultFields({ value, onChange, disabled, errorId }) {
  const change = (index, key, next) => onChange(value.map((row, i) => i === index ? { ...row, [key]: next } : row))
  return <fieldset disabled={disabled} aria-invalid={!!errorId} aria-describedby={errorId}><legend>Campos del resultado</legend>
    {value.map((row, index) => <fieldset key={row.key}><legend>Campo {index + 1}</legend>
      <label>Nombre del campo<input value={row.nombre} maxLength={100} onChange={e => change(index, 'nombre', e.target.value)} /></label>
      <label>Tipo de valor<select value={row.tipo} onChange={e => onChange(value.map((r, i) => i === index ? { ...r, tipo: e.target.value, valor: '' } : r))}>
        <option value="texto">Texto</option><option value="numero">Número</option><option value="booleano">Sí / No</option>
      </select></label>
      <label>Valor{row.tipo === 'booleano' ? <select value={row.valor} onChange={e => change(index, 'valor', e.target.value)}><option value="">Selecciona</option><option value="true">Sí</option><option value="false">No</option></select>
        : <input value={row.valor} maxLength={5000} inputMode={row.tipo === 'numero' ? 'decimal' : 'text'} onChange={e => change(index, 'valor', e.target.value)} />}</label>
      <label>Unidad (opcional)<input value={row.unidad} maxLength={100} onChange={e => change(index, 'unidad', e.target.value)} /></label>
      <label>Referencia (opcional)<input value={row.rango} maxLength={100} onChange={e => change(index, 'rango', e.target.value)} /></label>
      <button type="button" disabled={value.length === 1} onClick={() => onChange(value.filter((_, i) => i !== index))}>Quitar campo {index + 1}</button>
    </fieldset>)}
    <button type="button" disabled={value.length >= 50} onClick={() => onChange([...value, { key: crypto.randomUUID(), nombre: '', tipo: 'texto', valor: '', unidad: '', rango: '' }])}>Añadir campo</button>
  </fieldset>
}

function SpecialtyForm({ kind, history, service, onCreated, onCancel, onBusyChange, onSessionExpired }) {
  const id = useId(), form = useRef(null), inFlight = useRef(false)
  const [saving, setSaving] = useState(false), [errors, setErrors] = useState({}), [message, setMessage] = useState('')
  const [catalog, setCatalog] = useState(null), [loading, setLoading] = useState(false), [catalogError, setCatalogError] = useState(''), [retry, setRetry] = useState(0)
  const [results, setResults] = useState([{ key: 'first', nombre: '', tipo: 'texto', valor: '', unidad: '', rango: '' }])
  const action = specialtyActions[kind]
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
    for(const [name,field] of Object.entries(action.fields)) if(field.type==='utc' && input[name] && !input[name].endsWith('Z')) input[name]=localToUtc(input[name])
    if (kind === 'result') input.campos = results.map(({ key, ...row }) => row)
    const { fields } = validateSpecialtyDemo(kind, input, { birth: history.paciente.fecha_nacimiento })
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
    {message && <p role="alert">{message}</p>}
    {loading && <p role="status">Cargando opciones…</p>}
    {catalogError && <p role="alert">{catalogError} <button type="button" disabled={saving} onClick={() => setRetry(v => v + 1)}>Reintentar opciones</button></p>}
    {!loading && catalog && !catalog.length && <p role="status">No hay opciones disponibles para este registro.</p>}
    <form ref={form} onSubmit={submit} noValidate aria-busy={saving}>
      {Object.entries(action.fields).map(([name, field]) => <div key={name}>
        {field.type !== 'resultFields' && <label htmlFor={`${id}-${name}`}>{field.label}{field.optional ? ' (opcional)' : ''}</label>}
        {field.type === 'resultFields' ? <ResultFields value={results} onChange={setResults} disabled={saving} errorId={errors[name] ? `${id}-error-${name}` : undefined} />
          : ['catalog', 'choice'].includes(field.type) ? <select id={`${id}-${name}`} name={name} disabled={saving || (field.type === 'catalog' && (loading || !!catalogError))} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${id}-error-${name}` : undefined} defaultValue="">
            <option value="">Selecciona</option>{(field.type === 'catalog' ? catalog ?? [] : field.options.map(value => ({ id: value, nombre: value }))).map(row => <option value={row.id} key={row.id}>{row.nombre}</option>)}
          </select> : field.max > 200 ? <textarea id={`${id}-${name}`} name={name} maxLength={field.max} disabled={saving} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${id}-error-${name}` : undefined} />
            : <input id={`${id}-${name}`} name={name} defaultValue={field.type==='date'?todayInGuatemala():field.type==='utc'?localNow():undefined} step={field.type==='utc'?1:undefined} type={field.type === 'date' ? 'date' : field.type==='utc'?'datetime-local':'text'} maxLength={field.max ?? 100} inputMode={['decimal', 'integer'].includes(field.type) ? 'decimal' : undefined} disabled={saving} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${id}-error-${name}` : undefined} />}
        {errors[name] && <p id={`${id}-error-${name}`} className="field-error">{errors[name].join(' ')}</p>}
      </div>)}
      <button disabled={saving || loading || !!catalogError || (!!catalogField && !catalog?.length)}>{saving ? 'Guardando…' : `Guardar especialización${service.mode === 'mock' ? ' DEMO' : ''}`}</button>
      <button type="button" disabled={saving} onClick={onCancel}>Cancelar especialización</button>
    </form>
  </section></TaskDialog>
}

function Record({ row, kind }) {
  return <dl>{Object.entries(specialtyActions[kind].fields).filter(([name, field]) => !['catalog', 'resultFields'].includes(field.type) && row[name] != null).map(([name, field]) => <div key={name}><dt>{field.label}</dt><dd className="preserve-lines">{field.type==='utc'?localNow(new Date(row[name])).replace('T',' ')+' (Guatemala)':String(row[name])}</dd></div>)}
    {row.cama_nombre && <div><dt>Cama</dt><dd>{row.cama_nombre}</dd></div>}
    {row.ingreso_descripcion && <div><dt>Ingreso</dt><dd>{row.ingreso_descripcion}</dd></div>}
    {row.tratamiento_descripcion && <div><dt>Tratamiento</dt><dd>{row.tratamiento_descripcion}</dd></div>}
    {row.parentesco == null && row.parentesco_legacy && <div><dt>Parentesco histórico sin confirmar</dt><dd>{row.parentesco_legacy}</dd></div>}
    {row.mediciones_legacy && Object.entries(row.mediciones_legacy).filter(([, value]) => value != null).map(([name, value]) => <div key={name}><dt>{name} histórico (unidades sin confirmar)</dt><dd>{String(value)}</dd></div>)}
    {row.fecha_hora_alta && kind === 'admission' && <div><dt>Alta (hora de Guatemala)</dt><dd>{localNow(new Date(row.fecha_hora_alta)).replace('T',' ')}</dd></div>}
    {row.vacuna_nombre && <div><dt>Vacuna</dt><dd>{row.vacuna_nombre}</dd></div>}
    {row.tipo_examen_nombre && <div><dt>Examen</dt><dd>{row.tipo_examen_nombre}</dd></div>}
    {row.campos?.map(field => <div key={field.nombre}><dt>{field.nombre}</dt><dd>{typeof field.valor === 'boolean' ? field.valor ? 'Sí' : 'No' : String(field.valor)} {field.unidad ?? ''}{field.rango ? ` · Referencia: ${field.rango}` : ''}</dd></div>)}
  </dl>
}

export default function SpecialtyDemoPanel({ history, user, service, editor, onEdit, onCreated, busy, onBusyChange, onSessionExpired }) {
  const specialty = service.specialty ?? service.specialtyDemo
  const suffix = service.mode === 'mock' ? ' · DEMO' : ''
  const [rows, setRows] = useState(null), [error, setError] = useState(''), [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setRows(null); setError('')
    specialty.list(history.paciente.id, user).then(result => { if (active) setRows(result) }).catch(failure => {
      if (active && failure.status === 401) onSessionExpired(failure)
      else if (active && failure.name !== 'AbortError') setError(failure.message)
    })
    return () => { active = false }
  }, [service, history, retry, onSessionExpired])
  const actions = Object.entries(specialtyActions).filter(([kind, action]) => action.institution === user.institucion && (user.rol !== 'secretaria' || kind === 'tutor'))
  return <section aria-label={service.mode === 'mock' ? 'Especialización DEMO' : 'Especialización institucional'}><h3>Especialización institucional{suffix}</h3>
    <p>Paciente: {history.paciente.nombres} {history.paciente.apellidos} · {history.paciente.identificacion}</p>
    {service.mode === 'mock' && <p className="notice">Simulación local: estos registros no se envían al servidor y se pierden al recargar.</p>}
    {!rows && !error && <p role="status">Cargando especialización…</p>}
    {error && <p role="alert">{error} <button disabled={busy} onClick={() => setRetry(v => v + 1)}>Reintentar especialización</button></p>}
    {rows && actions.map(([kind, action]) => <section key={kind}><h4>{action.section}</h4>
      {!rows[kind]?.length && <p>Sin registros de {action.section.toLowerCase()}.</p>}
      <ul>{rows[kind]?.map(row => <li key={row.id}><Record row={row} kind={kind} /></li>)}</ul>
      {history.paciente.estado === 'activo' && canWriteSpecialtyDemo(user, kind) && <button disabled={busy} type="button" onClick={() => onEdit(kind)}>{action.title}{suffix}</button>}
    </section>)}
    {editor && <SpecialtyForm key={editor} kind={editor} history={history} service={service} onCreated={() => { onEdit(null); setRetry(v => v + 1); onCreated(service.mode === 'mock' ? 'Especialización guardada solo en la demostración local.' : 'Registro especializado guardado correctamente.') }}
      onCancel={() => onEdit(null)} onBusyChange={onBusyChange} onSessionExpired={onSessionExpired} />}
  </section>
}
