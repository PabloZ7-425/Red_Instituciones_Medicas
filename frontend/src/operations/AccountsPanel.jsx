import { useEffect, useRef, useState } from 'react'
import TaskDialog from '../clinical/TaskDialog.jsx'

export default function AccountsPanel({service,onBusy,onSessionExpired}) {
  const [page,setPage]=useState(null),[error,setError]=useState(null),[editor,setEditor]=useState(null),[saving,setSaving]=useState(false),[revision,setRevision]=useState(0)
  const [q,setQ]=useState(''),[query,setQuery]=useState({q:'',offset:0}),[loading,setLoading]=useState(false)
  const [draft,setDraft]=useState({username:'',password:'',rol:'secretaria',profesional_id:''}),[bindings,setBindings]=useState({})
  const inFlight=useRef(false)
  useEffect(()=>{
    const controller=new AbortController();let active=true
    setLoading(true);setError(null)
    service.accounts({...query,signal:controller.signal}).then(r=>{if(active){
      if(query.offset>0&&query.offset>=r.count)setQuery(v=>({...v,offset:Math.max(0,Math.floor((r.count-1)/r.limit)*r.limit)}))
      else setPage(r)
    }}).catch(e=>{if(active&&e.name!=='AbortError'){setError(e);if(e.status===401)onSessionExpired(e)}}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false;controller.abort()}
  },[service,query,revision,onSessionExpired])
  const close=()=>{if(!saving){setEditor(null);setDraft(v=>({...v,password:''}))}}
  async function mutate(task,created=false){
    if(inFlight.current)return
    inFlight.current=true;setSaving(true);onBusy(true);setError(null)
    try{await task();setEditor(null);if(created)setDraft({username:'',password:'',rol:'secretaria',profesional_id:''});setRevision(v=>v+1)}
    catch(e){setError(e);if(e.status===401)onSessionExpired(e)}
    finally{inFlight.current=false;setSaving(false);onBusy(false)}
  }
  const open=account=>{setError(null);setEditor(account?{account}:{create:true})}
  const values=editor?.account?{profesional_id:bindings[editor.account.id]??''}:draft
  const change=(name,value)=>editor.account?setBindings(v=>({...v,[editor.account.id]:value})):setDraft(v=>({...v,[name]:value}))
  return <section className="resource-panel" aria-label="Administración de usuarios"><h2>Usuarios y permisos</h2><p>Administra únicamente las cuentas de tu institución. Los usuarios nuevos no reciben acceso al administrador técnico de Django.</p>
    {!editor&&error&&<AccountError error={error}/>}
    <button disabled={saving||loading||!page} onClick={()=>open()}>Crear usuario</button>
    <form className="search-form" onSubmit={e=>{e.preventDefault();setQuery({q:q.trim(),offset:0})}}><label htmlFor="account-search">Buscar por inicio del usuario</label><input id="account-search" value={q} maxLength={100} onChange={e=>setQ(e.target.value)}/><button disabled={saving}>Buscar usuarios</button></form>
    {loading&&<p role="status">Cargando usuarios…</p>}
    {error&&!editor&&<button onClick={()=>setRevision(v=>v+1)}>Reintentar usuarios</button>}
    {!loading&&page&&<><p aria-live="polite">{page.count} usuarios encontrados</p>{!page.count&&<p>No hay usuarios que coincidan con la búsqueda.</p>}
      <ul className="patient-list">{page.results.map(r=><li key={r.id}><strong>{r.username}</strong><span>{r.rol} · {r.activo?'Activo':'Desactivado'}</span><button disabled={saving} onClick={()=>open(r)}>Vincular profesional</button><button disabled={saving} onClick={()=>mutate(()=>service.setAccountActive(r.id,!r.activo))}>{r.activo?'Desactivar':'Activar'}</button></li>)}</ul>
      <nav className="pagination" aria-label="Páginas de usuarios"><button disabled={saving||query.offset===0} onClick={()=>setQuery(v=>({...v,offset:Math.max(0,v.offset-page.limit)}))}>Anterior</button><span>{page.count?query.offset+1:0}–{Math.min(query.offset+page.limit,page.count)} de {page.count}</span><button disabled={saving||query.offset+page.limit>=page.count} onClick={()=>setQuery(v=>({...v,offset:v.offset+page.limit}))}>Siguiente</button></nav>
    </>}
    {editor&&<TaskDialog title={editor.create?'Nueva cuenta institucional':`Vincular profesional a ${editor.account.username}`} busy={saving} onCancel={close}>
      <h3>{editor.create?'Nueva cuenta institucional':`Vincular profesional a ${editor.account.username}`}</h3>
      <p>Al cancelar se conservan los campos para retomarlos. La contraseña se borra por seguridad.</p>
      {error&&<AccountError error={error}/>}
      <form onSubmit={e=>{e.preventDefault();if(editor.create){const data={...draft};if(!data.profesional_id)delete data.profesional_id;mutate(()=>service.createAccount(data),true)}else mutate(()=>service.bindProfessional(editor.account.id,values.profesional_id))}}>
        <fieldset disabled={saving}>
          {editor.create&&<><label>Usuario<input name="username" required maxLength={150} autoComplete="off" value={draft.username} onChange={e=>change('username',e.target.value)}/></label><label>Contraseña inicial<input name="password" type="password" required minLength={12} autoComplete="new-password" value={draft.password} onChange={e=>change('password',e.target.value)}/></label><label>Rol<select name="rol" required value={draft.rol} onChange={e=>change('rol',e.target.value)}>{page?.roles.map(r=><option key={r}>{r}</option>)}</select></label></>}
          <ProfessionalPicker service={service} value={values.profesional_id} required={!editor.create||['medico','laboratorista'].includes(draft.rol)} disabled={saving} onChange={v=>change('profesional_id',v)} onSessionExpired={onSessionExpired}/>
          <button>{editor.create?'Guardar usuario':'Guardar vínculo'}</button><button type="button" onClick={close}>{editor.create?'Cancelar':'Cancelar vínculo'}</button>
        </fieldset>
      </form>
    </TaskDialog>}
  </section>
}

function AccountError({error}) {return <div role="alert">{error.message}{Object.entries(error.fields??{}).map(([k,v])=><p key={k}>{k}: {v.join(' ')}</p>)}</div>}

function ProfessionalPicker({service,value,onChange,required,disabled,onSessionExpired}) {
  const [q,setQ]=useState(''),[offset,setOffset]=useState(0),[page,setPage]=useState(null),[error,setError]=useState(null),[retry,setRetry]=useState(0)
  useEffect(()=>{
    let active=true;const controller=new AbortController();setPage(null);setError(null)
    const timer=setTimeout(async()=>{try{
      const manifest=await service.manifest({signal:controller.signal})
      const name=['hospital','pediatrico'].includes(manifest.institucion)?'medico':'profesional'
      const result=await service.list(name,{lookup:true,q,offset,limit:20,signal:controller.signal})
      if(active)setPage(result)
    }catch(e){if(active&&e.name!=='AbortError'){setError(e);if(e.status===401)onSessionExpired(e)}}},200)
    return()=>{active=false;clearTimeout(timer);controller.abort()}
  },[service,q,offset,retry,onSessionExpired])
  return <div className="reference-input"><label>Buscar profesional<input value={q} disabled={disabled} onChange={e=>{setQ(e.target.value);setOffset(0)}}/></label>
    <label>Profesional vinculado<select name="profesional_id" required={required} value={value} disabled={disabled||!page} onChange={e=>onChange(e.target.value)}><option value="">{page?'Sin vínculo profesional':'Cargando opciones…'}</option>{value&&!page?.results.some(r=>r.id===value)&&<option value={value}>Selección actual</option>}{page?.results.map(r=><option key={r.id} value={r.id}>{r.label}</option>)}</select></label>
    {error&&<p role="alert">{error.message} <button type="button" onClick={()=>setRetry(v=>v+1)}>Reintentar profesionales</button></p>}
    {page&&<nav aria-label="Páginas de profesionales"><button type="button" disabled={disabled||offset===0} onClick={()=>setOffset(v=>Math.max(0,v-20))}>Opciones anteriores</button><span>{page.count?offset+1:0}–{Math.min(offset+20,page.count)} de {page.count}</span><button type="button" disabled={disabled||offset+20>=page.count} onClick={()=>setOffset(v=>v+20)}>Más opciones</button></nav>}
  </div>
}
