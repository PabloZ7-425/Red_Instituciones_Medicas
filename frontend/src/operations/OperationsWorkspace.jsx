import { useEffect, useRef, useState } from 'react'
import AccountsPanel from './AccountsPanel.jsx'
import { initialValues, labelFor, serializeFields } from './helpers.js'

const nextSteps = { especialidad:'medico', pabellon_edificio:'habitacion', habitacion:'cama', aseguradora:'plan_seguro', plan_seguro:'cobertura_servicio', servicio_medico:'detalle_factura', factura:'detalle_factura', detalle_factura:'pago', tipo_examen:'examen', examen:'resultado_examen', cirugia:'equipo_quirurgico', despacho_farmacia:'aplicacion_enfermeria', tutor:'paciente_tutor' }
const hints = { 'Agenda':'Programa la atención y evita citas duplicadas para el mismo profesional y horario.', 'Catálogos':'Prepara las opciones que utilizará el equipo. Busca antes de registrar para evitar duplicados.', 'Hospitalización':'Gestiona el ingreso, seguimiento, traslados y cirugía del paciente.', 'Farmacia':'Registra entregas y administración de medicamentos con control de existencias.', 'Caja y seguros':'Registra conceptos, consulta los totales calculados y aplica pagos al saldo.', 'Atención y seguimiento':'Consulta los registros clínicos y realiza el seguimiento del paciente.' }

function ReferenceInput({ name, field, value, onChange, service, patient, disabled, onPrefill }) {
  const [q,setQ]=useState(''),[page,setPage]=useState(null),[offset,setOffset]=useState(0),[error,setError]=useState('')
  useEffect(()=>{
    const controller=new AbortController();setPage(null);setError('')
    const timer=setTimeout(()=>service.list(field.resource,{q,offset,limit:20,lookup:true,patient:field.context==='patient'?undefined:patient,signal:controller.signal}).then(setPage).catch(e=>{if(e.name!=='AbortError')setError(e.message)}),200)
    return()=>{clearTimeout(timer);controller.abort()}
  },[service,field.resource,q,offset,patient])
  return <div className="reference-input">
    <input aria-label={`Buscar ${field.label}`} placeholder="Buscar por nombre…" value={q} disabled={disabled} onChange={e=>{setQ(e.target.value);setOffset(0)}} />
    <select id={`operation-${name}`} name={name} value={value} required={field.required} disabled={disabled || !page} onChange={e=>{onChange(e.target.value);const row=page.results.find(r=>r.id===e.target.value);if(row?.defaults)onPrefill(row.defaults)}}>
      <option value="">{page?'Selecciona una opción':'Cargando opciones…'}</option>
      {value && !page?.results.some(r=>r.id===value) && <option value={value}>Selección actual</option>}
      {page?.results.map(row=><option key={row.id} value={row.id}>{labelFor(row)}</option>)}
    </select>
    {error && <p role="alert">{error}</p>}
    {page?.count===0 && <p>No hay opciones. Registra primero {field.reference_label?.toLowerCase()} en su sección.</p>}
    {page && page.count>20 && <div className="reference-pages"><button type="button" disabled={disabled||offset===0} onClick={()=>setOffset(v=>Math.max(0,v-20))}>Opciones anteriores</button><span>{offset+1}–{Math.min(offset+20,page.count)} de {page.count}</span><button type="button" disabled={disabled||offset+20>=page.count} onClick={()=>setOffset(v=>v+20)}>Más opciones</button></div>}
  </div>
}

function OperationForm({ resource, record, service, patient, onClose, onSaved, onBusy, onSessionExpired }) {
  const editorFields=Object.fromEntries(Object.entries(resource.fields).map(([key,f])=>[key,{...f,computed:f.computed||!!(record&&resource.editable_fields&&!resource.editable_fields.includes(key))}]))
  const [values,setValues]=useState(()=>initialValues(editorFields,record?.values,patient)),[error,setError]=useState(null),[saving,setSaving]=useState(false)
  const inFlight=useRef(false),dialog=useRef(null),form=useRef(null)
  useEffect(()=>{dialog.current.showModal();form.current?.querySelector('input:not([disabled]),select')?.focus()},[])
  async function submit(e) {
    e.preventDefault();if(inFlight.current)return
    inFlight.current=true;setSaving(true);onBusy(true);setError(null)
    try {
      const payload=serializeFields(editorFields,values)
      if(record)for(const [key,f] of Object.entries(editorFields))if(!f.computed&&!f.required&&values[key]==='')payload[key]=null
      if(record)await service.update(resource.key,record.id,payload,record.version)
      else await service.create(resource.key,payload)
      onSaved()
    } catch(failure){if(failure.status===401)onSessionExpired(failure);else setError(failure)}
    finally{inFlight.current=false;setSaving(false);onBusy(false)}
  }
  const cancel=()=>{if(!saving)onClose()}
  return <dialog className="operation-dialog" ref={dialog} onCancel={e=>{e.preventDefault();cancel()}} aria-labelledby="operation-title">
    <header><div><p className="eyebrow">{resource.group}</p><h2 id="operation-title">{record?'Editar':'Registrar'} · {resource.label}</h2></div><button type="button" onClick={cancel} disabled={saving} aria-label="Cerrar formulario">×</button></header>
    <p>Los campos con * son obligatorios. Las horas se muestran en horario de Guatemala.</p>
    {error && <div role="alert" className="error-message"><p>{error.status===409?'El registro cambió o la operación entra en conflicto. Cierra y actualiza la lista antes de repetir.':error.status===0?'No se pudo confirmar el resultado. Revisa la lista antes de volver a guardar.':error.message}</p>{Object.entries(error.fields??{}).map(([k,m])=><p key={k}>{resource.fields[k]?.label??k}: {m.join(' ')}</p>)}</div>}
    <form ref={form} onSubmit={submit}>
      <div className="operation-fields">{Object.entries(editorFields).filter(([,f])=>!f.computed).map(([name,field])=>{
        const value=values[name]??'', change=next=>setValues(v=>({...v,[name]:next}))
        return <div className="operation-field" key={name}><label htmlFor={`operation-${name}`}>{field.label}{field.required?' *':' (opcional)'}</label>
          {field.choices?<select id={`operation-${name}`} value={value} onChange={e=>change(e.target.value)} required={field.required} disabled={saving}><option value="">Selecciona</option>{field.choices.map(v=><option key={v}>{v}</option>)}</select>:field.type==='reference'?<ReferenceInput name={name} field={field} value={value} onChange={change} service={service} patient={patient} disabled={saving} onPrefill={defaults=>setValues(v=>({...v,...Object.fromEntries(Object.entries(defaults).filter(([key])=>editorFields[key]&&!editorFields[key].computed))}))}/>
            :field.type==='boolean'?<select id={`operation-${name}`} value={String(value)} required={field.required} onChange={e=>change(e.target.value===''?'':e.target.value==='true')} disabled={saving}><option value="">Selecciona</option><option value="true">Sí</option><option value="false">No</option></select>
            :field.max>200?<textarea id={`operation-${name}`} value={value} onChange={e=>change(e.target.value)} disabled={saving} required={field.required} maxLength={field.max} rows={3}/>
            :<input id={`operation-${name}`} name={name} type={field.type==='datetime'?'datetime-local':['date','time'].includes(field.type)?field.type:['decimal','integer'].includes(field.type)?'number':name==='correo'?'email':'text'} value={value} onChange={e=>change(e.target.value)} disabled={saving} required={field.required} maxLength={field.max} min={field.min} max={field.max_value} step={field.type==='datetime'||field.type==='time'?1:field.type==='integer'?1:field.type==='decimal'?10**-(field.scale??2):undefined} aria-invalid={!!error?.fields?.[name]} />}
        </div>
      })}</div>
      {Object.values(resource.fields).some(f=>f.computed) && <p className="notice">Los importes calculados y los datos derivados se completan al guardar.</p>}
      <footer><button disabled={saving}>{saving?'Guardando…':'Guardar registro'}</button><button className="secondary" type="button" disabled={saving} onClick={cancel}>Cancelar</button></footer>
    </form>
  </dialog>
}

export default function OperationsWorkspace({ service, user, patient, onBusy, busy, onSessionExpired, onOpenClinical, onAttend }) {
  const [manifestRetry,setManifestRetry]=useState(0)
  const [manifest,setManifest]=useState(null),[group,setGroup]=useState('Inicio'),[resourceKey,setResourceKey]=useState(null),[q,setQ]=useState(''),[search,setSearch]=useState(''),[page,setPage]=useState(null),[offset,setOffset]=useState(0),[editor,setEditor]=useState(null),[error,setError]=useState(null),[revision,setRevision]=useState(0),[success,setSuccess]=useState('')
  const resource=manifest?.resources.find(r=>r.key===resourceKey)
  useEffect(()=>{
    const controller=new AbortController()
    service.manifest({signal:controller.signal}).then(setManifest).catch(e=>{if(e.name!=='AbortError'){setError(e);if(e.status===401)onSessionExpired(e)}})
    return()=>controller.abort()
  },[service,onSessionExpired,manifestRetry])
  useEffect(()=>{
    if(!resource)return
    const controller=new AbortController();setPage(null);setError(null)
    service.list(resource.key,{q:search,offset,patient,signal:controller.signal}).then(setPage).catch(e=>{if(e.name!=='AbortError'){setError(e);if(e.status===401)onSessionExpired(e)}})
    return()=>controller.abort()
  },[resource,service,search,offset,revision,patient,onSessionExpired])
  function choose(r){setResourceKey(r.key);setSearch('');setQ('');setOffset(0);setSuccess('');setError(null)}
  const groups=['Inicio',...new Set(manifest?.resources.map(r=>r.group)??[]),...(user.rol==='admin'?['Usuarios y permisos']:[])]
  return <section className="operations-workspace" aria-label="Centro de operaciones">
    <nav className="workspace-nav" aria-label="Áreas de trabajo">{groups.map(g=><button key={g} disabled={busy} aria-current={group===g?'page':undefined} onClick={()=>{setGroup(g);setResourceKey(null);setError(null);setSuccess('')}}>{g}</button>)}<button disabled={busy} onClick={onOpenClinical}>Expediente del paciente</button></nav>
    {patient && <p className="notice">Trabajando con el paciente seleccionado. Los registros relacionados se filtran por su expediente.</p>}
    {error && <div role="alert" className="error-message">{error.message} <button onClick={()=>manifest?setRevision(v=>v+1):setManifestRetry(v=>v+1)}>Reintentar</button></div>}
    {!manifest && !error && <p role="status">Cargando áreas de trabajo…</p>}
    {group==='Usuarios y permisos' && <AccountsPanel service={service} onBusy={onBusy} onSessionExpired={onSessionExpired}/>}
    {manifest && !resource && group!=='Usuarios y permisos' && <>
      <div className="workspace-intro"><p className="eyebrow">{group==='Inicio'?'Tu espacio de trabajo':group}</p><h2>{group==='Inicio'?'¿Qué necesitas hacer?':group}</h2><p>{hints[group]??'Selecciona una tarea. El sistema reutiliza los datos del paciente y presenta únicamente las funciones de tu rol.'}</p></div>
      <div className="task-grid">{manifest.resources.filter(r=>group==='Inicio'?r.create||r.key==='paciente':r.group===group).map(r=><button className="task-card" key={r.key} onClick={()=>choose(r)}><strong>{r.label}</strong><span>{r.create?'Consultar y registrar':r.edit?'Administrar':'Consultar registros'}</span></button>)}</div>
    </>}
    {resource && <section className="resource-panel" aria-label={resource.label}>
      <header><div><button className="text-button" onClick={()=>setResourceKey(null)}>← Volver a {group}</button><h2>{resource.label}</h2></div><div>{resource.create && <button onClick={()=>setEditor({})}>Nuevo registro</button>}<button className="secondary" onClick={()=>setRevision(v=>v+1)}>Actualizar lista</button></div></header>
      {!resource.create && !resource.edit && <p className="notice">Estos registros se generan durante la atención del paciente. <button className="text-button" onClick={onOpenClinical}>Ir al expediente</button></p>}
      {success && <p role="status" className="notice">{success}{nextSteps[resource.key] && manifest.resources.some(r=>r.key===nextSteps[resource.key]) && <button className="text-button" onClick={()=>choose(manifest.resources.find(r=>r.key===nextSteps[resource.key]))}>Continuar con {manifest.resources.find(r=>r.key===nextSteps[resource.key]).label.toLowerCase()} →</button>}</p>}
      <form className="search-form" onSubmit={e=>{e.preventDefault();setSearch(q.trim());setOffset(0)}}><label htmlFor="operation-search">Buscar en {resource.label.toLowerCase()}</label><input id="operation-search" value={q} maxLength={100} onChange={e=>setQ(e.target.value)}/><button>Buscar</button></form>
      {!page&&!error&&<p role="status">Cargando registros…</p>}
      {page && <><p aria-live="polite">{page.count} registros</p>{page.count===0?<p>No hay registros. {resource.create?'Puedes registrar el primero con el botón Nuevo registro.':'Registra primero la atención correspondiente.'}</p>:<div className="table-scroll"><table><thead><tr>{Object.entries(resource.fields).slice(0,6).map(([key,f])=><th key={key} scope="col">{f.label}</th>)}<th scope="col">Acciones</th></tr></thead><tbody>{page.results.map(row=><tr key={row.id}>{Object.entries(resource.fields).slice(0,6).map(([key,f])=><td key={key}>{typeof row.values[key]==='boolean'?row.values[key]?'Sí':'No':row.display?.[key]??row.values[key]??'—'}</td>)}<td>{resource.key==='cita' && row.values.estado==='programada' && ['admin','medico','laboratorista'].includes(user.rol) && <button onClick={()=>onAttend(row.values.id_paciente??row.values.paciente_id,row.id)}>Atender cita</button>}<button className="secondary" onClick={()=>setEditor({record:row,view:!resource.edit})}>{resource.edit?'Editar':'Ver detalle'}</button></td></tr>)}</tbody></table></div>}<nav className="pagination" aria-label="Páginas de registros"><button disabled={offset===0} onClick={()=>setOffset(v=>Math.max(0,v-20))}>Anterior</button><span>{page.count?offset+1:0}–{Math.min(offset+20,page.count)} de {page.count}</span><button disabled={offset+20>=page.count} onClick={()=>setOffset(v=>v+20)}>Siguiente</button></nav></>}
    </section>}
    {editor && resource && (editor.view?<RecordDetail resource={resource} record={editor.record} onClose={()=>setEditor(null)} />:<OperationForm key={resource.key+ (editor.record?.id??'new')} resource={resource} record={editor.record} service={service} patient={patient} onClose={()=>setEditor(null)} onSaved={()=>{setEditor(null);setSuccess('Registro guardado correctamente.');setRevision(v=>v+1)}} onBusy={onBusy} onSessionExpired={onSessionExpired}/>)}
  </section>
}

function RecordDetail({resource,record,onClose}) {
  const dialog=useRef(null)
  useEffect(()=>dialog.current.showModal(),[])
  return <dialog ref={dialog} className="operation-dialog" onCancel={e=>{e.preventDefault();onClose()}} aria-label={`Detalle de ${resource.label}`}><h2>{resource.label}</h2><dl>{Object.entries(resource.fields).map(([key,f])=><div key={key}><dt>{f.label}</dt><dd>{typeof record.values[key]==='boolean'?record.values[key]?'Sí':'No':record.display?.[key]??record.values[key]??'—'}</dd></div>)}</dl><button onClick={onClose}>Cerrar detalle</button></dialog>
}
