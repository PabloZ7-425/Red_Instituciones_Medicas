import { useCallback, useEffect, useState } from 'react'
import ClinicalShell from '../components/ClinicalShell.jsx'
import Badge from '../components/ui/Badge.jsx'
import Button from '../components/ui/Button.jsx'
import ErrorBanner from '../components/ui/ErrorBanner.jsx'
import OperationsWorkspace from '../operations/OperationsWorkspace.jsx'
import History from './History.jsx'
import PatientForm from './PatientForm.jsx'
import SpecialtyDemoPanel from './SpecialtyDemoPanel.jsx'
import { canRegisterPatient } from './patient-form.js'

export default function ClinicalPage({ service, onBusyChange }) {
  const [appointment,setAppointment]=useState(null)
  const [clinicalTask,setClinicalTask]=useState(null)
  const [workspace,setWorkspace] = useState('operations')
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState({ q: '', offset: 0 })
  const [page, setPage] = useState(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(null)
  const [history, setHistory] = useState(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [revision, setRevision] = useState(0)
  const [registering, setRegistering] = useState(false)
  const [success, setSuccess] = useState('')
  const [tutorPatient, setTutorPatient] = useState(null), [tutorEditor, setTutorEditor] = useState(null)

  const handleError = useCallback(failure => {
    if (failure.name === 'AbortError') return
    if (failure.status === 401) {
      setWorkspace('operations'); setClinicalTask(null); setAppointment(null); setUser(null); setPage(null); setHistory(null); setSelected(null)
      setRegistering(false); setSuccess('')
      setTutorPatient(null); setTutorEditor(null)
    }
    setError(failure)
  }, [])

  useEffect(() => { onBusyChange?.(busy) }, [busy, onBusyChange])

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    service.me({ signal: controller.signal }).then(result => {
      if (active) setUser(result.usuario)
    }).catch(failure => {
      if (active && failure.status !== 401 && failure.name !== 'AbortError') setError(failure)
    }).finally(() => { if (active) setChecking(false) })
    return () => { active = false; controller.abort() }
  }, [service])

  useEffect(() => {
    if (!user) return
    const controller = new AbortController()
    let active = true
    setLoading(true); setPage(null); setError(null)
    service.listPatients({ ...query, limit: 20, signal: controller.signal })
      .then(result => { if (active) setPage(result) })
      .catch(failure => { if (active) handleError(failure) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false; controller.abort() }
  }, [service, user, query, revision])

  useEffect(() => {
    if (!user || !selected) { setHistoryLoading(false); return }
    const controller = new AbortController()
    let active = true
    setHistoryLoading(true); setHistory(previous=>previous?.paciente.id===selected?previous:null); setError(null)
    service.history(selected, { signal: controller.signal })
      .then(result => { if (active) setHistory(result) })
      .catch(failure => { if (active) handleError(failure) })
      .finally(() => { if (active) setHistoryLoading(false) })
    return () => { active = false; controller.abort() }
  }, [service, user, selected, revision])

  async function login(event) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    const password = data.get('password')
    form.elements.password.value = ''
    setBusy(true); setError(null)
    try {
      const result = await service.login({ username: data.get('username'), password })
      setWorkspace('operations'); setUser(result.usuario); setQuery({ q: '', offset: 0 }); setDraft('')
      setRegistering(false); setSuccess('')
      setTutorPatient(null); setTutorEditor(null)
    } catch (failure) { handleError(failure) }
    finally { setBusy(false) }
  }

  async function logout() {
    setBusy(true); setError(null)
    try {
      await service.logout()
      setWorkspace('operations'); setClinicalTask(null); setAppointment(null); setUser(null); setPage(null); setSelected(null); setHistory(null)
      setRegistering(false); setSuccess('')
      setTutorPatient(null); setTutorEditor(null)
    } catch (failure) { handleError(failure) }
    finally { setBusy(false) }
  }

  return <ClinicalShell user={user} hasOperations={!!service.operations} workspace={workspace} busy={busy}
    onWorkspaceChange={setWorkspace} onLogout={logout}>
    {service.mode === 'mock' && <aside className="notice" aria-label="Modo demostración">
      <strong>DEMO · Datos ficticios, sin sesión ni persistencia reales.</strong>
      <p>Usuario: DEMO-medico-hospital, DEMO-medico-pediatrico, DEMO-medico-laboratorio o DEMO-medico-odontologica. Clave de demostración: DEMO-no-utilizar.</p>
    </aside>}
    {checking ? <p className="ui-feedback" role="status">Comprobando sesión…</p> : !user ? <section className="login-panel" aria-labelledby="login-title">
      <p className="shell-overline">Acceso institucional</p>
      <h2 id="login-title">Iniciar sesión</h2>
      <p className="login-copy">Ingresa con la cuenta de tu institución para abrir tu espacio de trabajo.</p>
      <ErrorBanner error={error} />
      <form onSubmit={login}>
        <label htmlFor="username">Usuario</label><input id="username" name="username" required autoComplete="username" disabled={busy} />
        <label htmlFor="password">Contraseña</label><input id="password" name="password" type="password" required autoComplete="current-password" disabled={busy} />
        <Button disabled={busy}>{busy ? 'Ingresando…' : 'Ingresar'}</Button>
      </form>
    </section> : <>
      <ErrorBanner error={error}>
        <Button disabled={busy} variant="secondary" type="button" onClick={() => setRevision(value => value + 1)}>Reintentar consulta</Button>
      </ErrorBanner>
      {success && <p className="ui-feedback ui-feedback--success" role="status">{success}</p>}
      {service.operations && <div hidden={workspace!=='operations'}><OperationsWorkspace service={service.operations} user={user} patient={selected} onBusy={setBusy} busy={busy} onSessionExpired={handleError} onOpenClinical={task=>{
        setWorkspace('patients');setClinicalTask(typeof task==='string'?task:null)
        if(task==='patient'){setRegistering(true);setSelected(null);setHistory(null);setClinicalTask(null)}
      }} onAttend={(patient,id)=>{setClinicalTask(null);setSelected(patient);setAppointment(id);setWorkspace('patients')}} /></div>}
      {(!service.operations || workspace==='patients') && <>
      {clinicalTask && !selected && <p className="notice" role="status">Selecciona un paciente para continuar con la tarea clínica elegida.</p>}
      {canRegisterPatient(user) && !registering && <div className="directory-actions">
        <Button type="button" disabled={busy} onClick={() => { setRegistering(true); setSuccess(''); setSelected(null); setHistory(null); setTutorPatient(null) }}>Nuevo paciente</Button>
      </div>}
      {registering && <PatientForm service={service} onBusyChange={setBusy} onSessionExpired={handleError}
        onCancel={() => setRegistering(false)} onCreated={patient => {
          setRegistering(false); setError(null)
          setSuccess(`Paciente ${patient.nombres} ${patient.apellidos} registrado correctamente.`)
          setDraft(patient.identificacion); setQuery({ q: patient.identificacion, offset: 0 })
          setHistory(null); setSelected(user.rol === 'secretaria' ? null : patient.id)
        }} />}
      <div className="clinical-layout">
        <section className="clinical-panel directory-panel" aria-label="Pacientes">
          <header className="directory-heading">
            <p className="shell-overline">Directorio</p>
            <h2>Pacientes</h2>
          </header>
          <form className="search-form" onSubmit={event => {
            event.preventDefault(); if (busy) return; setSelected(null); setHistory(null); setTutorPatient(null); setQuery({ q: draft.trim(), offset: 0 })
          }}>
            <label htmlFor="search">Buscar por inicio de identificación, nombre o apellido</label>
            <input id="search" disabled={busy} maxLength={100} value={draft} onChange={event => setDraft(event.target.value)} />
            <button disabled={busy}>Buscar</button>
          </form>
          {loading && <p className="ui-feedback" role="status">Cargando pacientes…</p>}
          {!loading && page?.count === 0 && <p className="ui-feedback" role="status">No hay pacientes que coincidan con la búsqueda.</p>}
          {page && <>
            <p className="directory-count" aria-live="polite">{page.count} pacientes encontrados</p>
            <ul className="patient-list">{page.results.map(patient => <li key={patient.id}>
              <strong>{patient.nombres} {patient.apellidos}</strong>
              <div className="patient-list__meta"><span>{patient.identificacion}</span>
                <Badge tone={patient.estado === 'activo' ? 'success' : 'neutral'}>{patient.estado}</Badge>
              </div>
              {user.rol !== 'secretaria' && <button type="button" disabled={busy || registering} aria-pressed={selected === patient.id} onClick={() => {setAppointment(null);setSelected(patient.id)}}>Ver historial</button>}
              {(service.specialty || (service.mode === 'mock' && service.specialtyDemo)) && user.rol === 'secretaria' && user.institucion === 'pediatrico' && <button type="button" disabled={busy || registering} onClick={() => { setTutorPatient(patient); setTutorEditor('tutor') }}>Gestionar tutores{service.mode === 'mock' ? ' · DEMO' : ''}</button>}
            </li>)}</ul>
            <nav className="pagination" aria-label="Páginas de pacientes">
              <button disabled={busy || loading || query.offset === 0} onClick={() => { setSelected(null); setHistory(null); setQuery({ ...query, offset: Math.max(0, query.offset - 20) }) }}>Anterior</button>
              <button disabled={busy || loading || query.offset + page.limit >= page.count} onClick={() => { setSelected(null); setHistory(null); setQuery({ ...query, offset: query.offset + 20 }) }}>Siguiente</button>
            </nav>
          </>}
        </section>
        <div aria-live="polite" aria-busy={historyLoading}>
          {tutorPatient && user.rol === 'secretaria' && (service.specialty || service.mode === 'mock') && <SpecialtyDemoPanel key={tutorPatient.id} history={{ paciente: tutorPatient }} user={user} service={service} busy={busy} editor={tutorEditor} onEdit={setTutorEditor}
            onCreated={setSuccess} onBusyChange={setBusy} onSessionExpired={handleError} />}
          {historyLoading && <p className="ui-feedback" role="status">Cargando historial…</p>}
          {history ? <History key={history.paciente.id} history={history} user={user} service={service} busy={busy || historyLoading}
            requestedTask={clinicalTask} onTaskOpened={()=>setClinicalTask(null)} appointment={appointment} onAppointmentConsumed={()=>setAppointment(null)} onActionCreated={message => { setSuccess(message); setRevision(value => value + 1) }} onRefresh={() => setRevision(value => value + 1)}
            onBusyChange={setBusy} onSessionExpired={handleError} onConsultationCreated={() => {
              setSuccess('Consulta registrada correctamente.'); setRevision(value => value + 1)
            }} /> : !historyLoading && <section className="clinical-panel directory-placeholder" aria-label="Historial clínico">
              <p className="shell-overline">Expediente</p>
              <h2>{user.rol === 'secretaria' ? 'Consulta administrativa' : 'Historial clínico'}</h2>
              <p>{user.rol === 'secretaria' ? 'Tu rol permite consultar el listado de pacientes.' : 'Selecciona un paciente para consultar su historial.'}</p>
            </section>}
        </div>
      </div>
      </>}
    </>}
  </ClinicalShell>
}
