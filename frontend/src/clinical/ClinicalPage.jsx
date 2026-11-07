import { useCallback, useEffect, useRef, useState } from 'react'
import ClinicalShell from '../components/ClinicalShell.jsx'
import { workspaceNavigation } from '../components/workspace-navigation.js'
import Button from '../components/ui/Button.jsx'
import ErrorBanner from '../components/ui/ErrorBanner.jsx'
import Toast from '../components/ui/Toast.jsx'
import PatientHeader from '../components/ui/PatientHeader.jsx'
import OperationsWorkspace from '../operations/OperationsWorkspace.jsx'
import LoginPage from '../pages/LoginPage.jsx'
import PatientsPage from '../pages/PatientsPage.jsx'
import History from './History.jsx'
import PatientForm from './PatientForm.jsx'
import SpecialtyDemoPanel from './SpecialtyDemoPanel.jsx'
import Workday from './Workday.jsx'
import { canRegisterPatient } from './patient-form.js'
import { specialtyActions } from './specialty-demo.js'

export default function ClinicalPage({ service, onBusyChange }) {
  const [appointment,setAppointment]=useState(null)
  const [clinicalTask,setClinicalTask]=useState(null)
  const [workspace,setWorkspace] = useState('operations')
  const [operationTarget, setOperationTarget] = useState(null)
  const [operationResources, setOperationResources] = useState([])
  const [patientArea, setPatientArea] = useState('patients')
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
  const dismissSuccess = useCallback(() => setSuccess(''), [])
  const [tutorPatient, setTutorPatient] = useState(null), [tutorEditor, setTutorEditor] = useState(null)
  const directorySearch = useRef(null)
  const [focusDirectory, setFocusDirectory] = useState(false)

  const handleError = useCallback(failure => {
    if (failure.name === 'AbortError') return
    if (failure.status === 401) {
      setWorkspace('operations'); setClinicalTask(null); setAppointment(null); setUser(null); setPage(null); setHistory(null); setSelected(null)
      setRegistering(false); setSuccess('')
      setTutorPatient(null); setTutorEditor(null)
      setOperationTarget(null); setOperationResources([])
    }
    setError(failure)
  }, [])

  useEffect(() => { onBusyChange?.(busy) }, [busy, onBusyChange])
  useEffect(() => {
    if (focusDirectory && directorySearch.current) {
      directorySearch.current.focus()
      setFocusDirectory(false)
    }
  }, [focusDirectory, workspace])

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
      setOperationTarget(null); setOperationResources([])
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

  function searchPatients(q) {
    setAppointment(null)
    setSelected(null)
    setHistory(null)
    setTutorPatient(null)
    setDraft(q)
    setQuery({ q, offset: 0 })
    setWorkspace('patients')
  }

  function openClinical(task) {
    setWorkspace('patients')
    setPatientArea('patients')
    setClinicalTask(typeof task === 'string' && task !== 'patient' ? task : null)
    if (task === 'patient') {
      setRegistering(true)
      setSuccess('')
      setSelected(null)
      setHistory(null)
      setTutorPatient(null)
      setAppointment(null)
    } else if (!selected) {
      setFocusDirectory(true)
    }
  }

  function selectPatient(patient) {
    setAppointment(null)
    if (user.rol === 'secretaria') { setTutorPatient(patient); setTutorEditor(null) }
    else setSelected(patient.id)
  }

  const canUseSpecialty = !!(service.specialty || (service.mode === 'mock' && service.specialtyDemo))
  const currentPatient = history && history.paciente.id === selected ? history.paciente : page?.results.find(patient => patient.id === selected)
  const patientLabel = currentPatient ? `${currentPatient.nombres} ${currentPatient.apellidos}` : ''
  const followUpTask = clinicalTask?.startsWith('followup:') ? specialtyActions[clinicalTask.slice(9)]?.section : null
  const pendingTask = followUpTask ?? specialtyActions[clinicalTask]?.title ?? (clinicalTask === 'consultation' ? 'Registrar consulta' : 'Continuar atención')
  const workday = () => <Workday user={user} patients={page} loading={loading} busy={busy}
    canUseSpecialty={canUseSpecialty}
    onSearch={q => { setClinicalTask(null); setPatientArea('patients'); searchPatients(q); setFocusDirectory(true) }}
    onPatient={patient => {
      setClinicalTask(null)
      setRegistering(false)
      if (user.rol === 'secretaria') {
        searchPatients(patient.identificacion)
        setTutorPatient(patient); setTutorEditor(null); setPatientArea('patients')
        setFocusDirectory(true)
      } else {
        setWorkspace('patients')
        setPatientArea('patients')
        setAppointment(null)
        setSelected(patient.id)
      }
    }}
    onClinicalTask={task => {
      setRegistering(false)
      searchPatients('')
      openClinical(task)
      if (task !== 'patient') setFocusDirectory(true)
    }} />

  const navigation = user ? workspaceNavigation(user, operationResources, !!service.operations) : []
  const demo = service.mode === 'mock'
  function navigate(item) {
    if (item.id === 'patients' || item.followUp) {
      setWorkspace('patients')
      setPatientArea(item.id)
      setClinicalTask(item.followUp ? `followup:${item.followUp}` : null)
      if (item.followUp && !selected) setFocusDirectory(true)
    } else {
      setWorkspace('operations')
      setOperationTarget({ ...item })
    }
  }

  return <ClinicalShell user={user} navigation={navigation} busy={busy}
    active={workspace === 'patients' ? patientArea : operationTarget?.id ?? 'home'}
    onNavigate={navigate} onLogout={logout}>
    {checking ? <p className="ui-feedback" role="status">Comprobando sesión…</p> : !user ?
      <LoginPage busy={busy} error={error} onLogin={login} demo={demo} /> : <>
      {demo && <p className="demo-indicator">DEMO · Datos ficticios</p>}
      <ErrorBanner error={error}>
        <Button disabled={busy} variant="secondary" type="button" onClick={() => setRevision(value => value + 1)}>Reintentar consulta</Button>
      </ErrorBanner>
      <Toast message={success} onClose={dismissSuccess} />
      {service.operations && <div hidden={workspace!=='operations'}><OperationsWorkspace service={service.operations} user={user} patient={selected} onBusy={setBusy} busy={busy} onSessionExpired={handleError} onOpenClinical={openClinical} renderHome={workday}
        target={operationTarget} onAccess={setOperationResources} clinicalRevision={revision}
        patientLabel={patientLabel} patientStatus={currentPatient?.estado}
        onClearPatient={() => { setSelected(null); setHistory(null); setAppointment(null); setClinicalTask(null) }}
        onAreaChange={group => setOperationTarget({
          ...(navigation.find(item => group === 'Usuarios y permisos' ? item.id === 'admin' : item.group === group && !item.resource) ?? navigation[0]),
          group,
        })}
        onAttend={(patient,id)=>{setClinicalTask(null);setRegistering(false);setSelected(patient);setAppointment(id);setPatientArea('patients');setWorkspace('patients')}} /></div>}
      {(!service.operations || workspace==='patients') && <>
      {!service.operations && !selected && !clinicalTask && !registering && !tutorPatient && workday()}
      {clinicalTask && !selected && <section className="patient-handoff" aria-label="Tarea en curso">
        <div><p className="shell-overline">Tarea en curso</p><h2>{pendingTask}</h2>
          <p>Elige al paciente. Su expediente se abrirá con esta tarea lista para continuar.</p></div>
        <Button type="button" variant="secondary" disabled={busy} onClick={() => setClinicalTask(null)}>Cancelar tarea</Button>
      </section>}
      {canRegisterPatient(user) && !registering && <div className="directory-actions">
        <Button type="button" disabled={busy} onClick={() => { setRegistering(true); setSuccess(''); setSelected(null); setHistory(null); setTutorPatient(null) }}>Nuevo paciente</Button>
      </div>}
      {registering && <PatientForm service={service} pediatric={user.institucion === 'pediatrico'} onBusyChange={setBusy} onSessionExpired={handleError}
        onCancel={() => setRegistering(false)} onCreated={patient => {
          setRegistering(false); setError(null)
          setSuccess(`Paciente ${patient.nombres} ${patient.apellidos} registrado correctamente.`)
          setDraft(patient.identificacion); setQuery({ q: patient.identificacion, offset: 0 })
          setHistory(null); setSelected(user.rol === 'secretaria' ? null : patient.id)
          if (user.rol === 'secretaria') { setTutorPatient(patient); setTutorEditor(null) }
        }} />}
      <div className="clinical-layout">
        <PatientsPage user={user} draft={draft} onDraft={setDraft} onSearch={searchPatients} searchRef={directorySearch}
          page={page} loading={loading} busy={busy} registering={registering} selected={selected}
          choosingPatient={!!clinicalTask && !selected} tutorAccess={canUseSpecialty && user.rol === 'secretaria' && user.institucion === 'pediatrico'}
          demo={demo} onSelect={selectPatient} onTutor={patient => { setClinicalTask(null); setTutorPatient(patient); setTutorEditor('tutor') }}
          offset={query.offset} onOffset={offset => { setSelected(null); setHistory(null); setTutorPatient(null); setQuery({ ...query, offset }) }} />
        <div aria-live="polite" aria-busy={historyLoading}>
          {tutorPatient && user.rol === 'secretaria' && <section className="clinical-panel" aria-label="Ficha administrativa">
            <PatientHeader patient={tutorPatient} />
            {user.institucion === 'pediatrico' && canUseSpecialty && <SpecialtyDemoPanel key={tutorPatient.id} history={{ paciente: tutorPatient }}
              user={user} service={service} busy={busy} editor={tutorEditor} onEdit={setTutorEditor}
              onCreated={message => { setSuccess(message); setRevision(value => value + 1) }}
              onBusyChange={setBusy} onSessionExpired={handleError} />}
          </section>}
          {historyLoading && <p className="ui-feedback" role="status">Cargando historial…</p>}
          {history ? <History key={history.paciente.id} history={history} user={user} service={service} busy={busy || historyLoading}
            requestedTask={clinicalTask} onTaskOpened={()=>setClinicalTask(null)} appointment={appointment} onAppointmentConsumed={()=>setAppointment(null)} onActionCreated={message => { setSuccess(message); setRevision(value => value + 1) }} onRefresh={() => setRevision(value => value + 1)}
            onBusyChange={setBusy} onSessionExpired={handleError} onConsultationCreated={() => {
              setSuccess('Consulta registrada correctamente.'); setRevision(value => value + 1)
            }} /> : !historyLoading && !tutorPatient && <section className="clinical-panel directory-placeholder" aria-label="Historial clínico">
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
