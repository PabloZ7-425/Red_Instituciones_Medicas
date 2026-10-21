import { useEffect, useState } from 'react'
import History from './History.jsx'
import PatientForm from './PatientForm.jsx'
import { canRegisterPatient } from './patient-form.js'

const institutions = { hospital: 'Hospital', pediatrico: 'Clínica Pediátrica', laboratorio: 'Laboratorio Clínico', odontologica: 'Clínica Odontológica' }

function ErrorNotice({ error }) {
  if (!error) return null
  return <div role="alert" className="error-message"><p>{error.message}</p>
    {Object.entries(error.fields ?? {}).map(([field, messages]) => <p key={field}>{field}: {Array.isArray(messages) ? messages.join(' ') : ''}</p>)}
  </div>
}

export default function ClinicalPage({ service }) {
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

  function handleError(failure) {
    if (failure.name === 'AbortError') return
    if (failure.status === 401) {
      setUser(null); setPage(null); setHistory(null); setSelected(null)
      setRegistering(false); setSuccess('')
    }
    setError(failure)
  }

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
    setHistoryLoading(true); setHistory(null); setError(null)
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
      setUser(result.usuario); setQuery({ q: '', offset: 0 }); setDraft('')
      setRegistering(false); setSuccess('')
    } catch (failure) { handleError(failure) }
    finally { setBusy(false) }
  }

  async function logout() {
    setBusy(true); setError(null)
    try {
      await service.logout()
      setUser(null); setPage(null); setSelected(null); setHistory(null)
      setRegistering(false); setSuccess('')
    } catch (failure) { handleError(failure) }
    finally { setBusy(false) }
  }

  return <main className="page-shell clinical-shell">
    <header className="clinical-header"><p className="eyebrow">Red de Instituciones Médicas</p><h1>Historiales clínicos</h1></header>
    {service.mode === 'mock' && <aside className="notice" aria-label="Modo demostración">
      <strong>DEMO · Datos ficticios, sin sesión ni persistencia reales.</strong>
      <p>Usuario: DEMO-medico-hospital, DEMO-medico-pediatrico, DEMO-medico-laboratorio o DEMO-medico-odontologica. Clave de demostración: DEMO-no-utilizar.</p>
    </aside>}
    {checking ? <p role="status">Comprobando sesión…</p> : !user ? <section className="clinical-panel login-panel">
      <h2>Iniciar sesión</h2>
      <ErrorNotice error={error} />
      <form onSubmit={login}>
        <label htmlFor="username">Usuario</label><input id="username" name="username" required autoComplete="username" disabled={busy} />
        <label htmlFor="password">Contraseña</label><input id="password" name="password" type="password" required autoComplete="current-password" disabled={busy} />
        <button disabled={busy}>{busy ? 'Ingresando…' : 'Ingresar'}</button>
      </form>
    </section> : <>
      <section className="section-heading"><div><h2>{institutions[user.institucion] ?? 'Institución'}</h2><p>{user.username} · {user.rol}</p></div>
        <button onClick={logout} disabled={busy}>Cerrar sesión</button>
      </section>
      <ErrorNotice error={error} />
      {success && <p className="notice" role="status">{success}</p>}
      {error && <button type="button" onClick={() => setRevision(value => value + 1)}>Reintentar consulta</button>}
      {canRegisterPatient(user) && !registering && <button className="register-button" type="button" disabled={busy} onClick={() => { setRegistering(true); setSuccess('') }}>Nuevo paciente</button>}
      {registering && <PatientForm service={service} onBusyChange={setBusy} onSessionExpired={handleError}
        onCancel={() => setRegistering(false)} onCreated={patient => {
          setRegistering(false); setError(null)
          setSuccess(`Paciente ${patient.nombres} ${patient.apellidos} registrado correctamente.`)
          setDraft(patient.identificacion); setQuery({ q: patient.identificacion, offset: 0 })
          setHistory(null); setSelected(user.rol === 'secretaria' ? null : patient.id)
        }} />}
      <div className="clinical-layout">
        <section className="clinical-panel" aria-label="Pacientes">
          <h2>Pacientes</h2>
          <form className="search-form" onSubmit={event => {
            event.preventDefault(); setSelected(null); setHistory(null); setQuery({ q: draft.trim(), offset: 0 })
          }}>
            <label htmlFor="search">Buscar por inicio de identificación, nombre o apellido</label>
            <input id="search" maxLength={100} value={draft} onChange={event => setDraft(event.target.value)} />
            <button>Buscar</button>
          </form>
          {loading && <p role="status">Cargando pacientes…</p>}
          {!loading && page?.count === 0 && <p role="status">No hay pacientes que coincidan con la búsqueda.</p>}
          {page && <>
            <p aria-live="polite">{page.count} pacientes encontrados</p>
            <ul className="patient-list">{page.results.map(patient => <li key={patient.id}>
              <strong>{patient.nombres} {patient.apellidos}</strong><span>{patient.identificacion} · {patient.estado}</span>
              {user.rol !== 'secretaria' && <button type="button" aria-pressed={selected === patient.id} onClick={() => setSelected(patient.id)}>Ver historial</button>}
            </li>)}</ul>
            <nav className="pagination" aria-label="Páginas de pacientes">
              <button disabled={loading || query.offset === 0} onClick={() => { setSelected(null); setHistory(null); setQuery({ ...query, offset: Math.max(0, query.offset - 20) }) }}>Anterior</button>
              <button disabled={loading || query.offset + page.limit >= page.count} onClick={() => { setSelected(null); setHistory(null); setQuery({ ...query, offset: query.offset + 20 }) }}>Siguiente</button>
            </nav>
          </>}
        </section>
        <div aria-live="polite" aria-busy={historyLoading}>
          {historyLoading ? <p role="status">Cargando historial…</p> : history ? <History history={history} /> : <p className="clinical-panel">{user.rol === 'secretaria' ? 'Tu rol permite consultar el listado de pacientes.' : 'Selecciona un paciente para consultar su historial.'}</p>}
        </div>
      </div>
    </>}
  </main>
}
