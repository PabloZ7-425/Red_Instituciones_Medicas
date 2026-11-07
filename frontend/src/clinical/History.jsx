import { useEffect, useRef, useState } from 'react'
import Button from '../components/ui/Button.jsx'
import PatientHeader from '../components/ui/PatientHeader.jsx'
import Tabs from '../components/ui/Tabs.jsx'
import TaskDialog from './TaskDialog.jsx'
import { nextClinicalStep } from '../operations/workflow.js'
import ClinicalActionForm from './ClinicalActionForm.jsx'
import { canPrescribe, canArchive } from './clinical-actions.js'
import ConsultationForm from './ConsultationForm.jsx'
import SpecialtyDemoPanel from './SpecialtyDemoPanel.jsx'
import { canRegisterConsultation } from './consultation-form.js'
import { canWriteSpecialtyDemo } from './specialty-demo.js'
import { institutionTasks } from './Workday.jsx'
import PatientSummary from './PatientSummary.jsx'
import ConsultationTimeline from './ConsultationTimeline.jsx'

export default function History({ history, user, service, busy, onBusyChange, onSessionExpired, onConsultationCreated, onActionCreated, onRefresh, appointment, onAppointmentConsumed, requestedTask, onTaskOpened }) {
  const [tab,setTab]=useState(appointment ? 'clinical' : 'summary')
  const [registering, setRegistering] = useState(!!appointment)
  const consultationTrigger = useRef(null)
  const [editor, setEditor] = useState(null)
  const [nextAction, setNextAction] = useState(null)
  const [specialtySection, setSpecialtySection] = useState(null)
  const [medicines, setMedicines] = useState({}), [catalogError, setCatalogError] = useState(false)
  const [catalogRetry, setCatalogRetry] = useState(0)
  const patient = history.paciente
  const consultations = [...history.consultas].sort((a, b) => b.fecha.localeCompare(a.fecha))
  const canConsult = patient.estado === 'activo' && canRegisterConsultation(user)
  const canViewSpecialty = service.specialty || (service.mode === 'mock' && service.specialtyDemo)
  const followUp = institutionTasks[user.institucion]?.followUp
  useEffect(() => {
    const needed = new Set(history.consultas.flatMap(c => c.diagnosticos.flatMap(d => d.tratamientos.flatMap(t => t.recetas.map(r => r.medicamento_id)))))
    if (!canPrescribe(user) || needed.size === 0) return
    const controller = new AbortController()
    let active = true
    async function load() {
      const names = {}
      let offset = 0
      try {
        while (true) {
          const page = service.operations ? await service.operations.list('medicamento',{limit:100,offset,lookup:true,signal:controller.signal}) : await service.listMedicines({ limit: 100, offset, signal: controller.signal })
          for (const m of page.results) names[m.id] = m.nombre ?? m.label
          offset += page.limit
          if ([...needed].every(id => Object.hasOwn(names, id)) || offset >= page.count || page.results.length === 0) break
        }
        if (active) { setMedicines(names); setCatalogError(false) }
      } catch (error) {
        if (active && error.name !== 'AbortError') {
          if (error.status === 401) onSessionExpired(error)
          else setCatalogError(true)
        }
      }
    }
    load()
    return () => { active = false; controller.abort() }
  }, [service, history, user.rol, catalogRetry, onSessionExpired])
  useEffect(() => {
    if (!appointment) return
    if (canConsult) { setRegistering(true); setTab('clinical') }
    else { setRegistering(false); onAppointmentConsumed?.() }
  }, [appointment, canConsult])
  useEffect(()=>{
    if(!requestedTask||busy)return
    if (requestedTask.startsWith('followup:') && canViewSpecialty) {
      setRegistering(false); setEditor(null); setSpecialtySection(requestedTask.slice(9)); setTab('specialty'); onTaskOpened()
      return
    }
    if(patient.estado!=='activo')return
    if(requestedTask==='consultation'&&canRegisterConsultation(user)){
      setTab('clinical');setEditor(null);setRegistering(true);onTaskOpened()
    }else if(canWriteSpecialtyDemo(user,requestedTask)){
      setTab('specialty');setRegistering(false);setEditor({specialty:requestedTask});onTaskOpened()
    }else setTab('clinical')
  },[requestedTask,busy,patient.estado])
  const edit = (kind, parentId) => {
    setRegistering(false); setEditor({ kind, parentId }); onTaskOpened?.()
    if (kind !== 'archive') setTab('clinical')
  }
  function closeConsultation() {
    setRegistering(false)
    onAppointmentConsumed?.()
  }
  const actionButton = (kind, parentId, title) => patient.estado === 'activo' && canPrescribe(user) && <button type="button" disabled={busy} onClick={() => edit(kind, parentId)}>{title}</button>
  return <section aria-label="Historial clínico" className="clinical-panel history-panel">
    <PatientHeader patient={patient}>
      <div className="history-actions">
        {canConsult && <button ref={consultationTrigger} type="button" disabled={busy} hidden={registering}
          onClick={() => { setTab('clinical'); setEditor(null); setRegistering(true) }}>Nueva consulta</button>}
        <Button type="button" variant="secondary" disabled={busy} onClick={onRefresh}>Actualizar historial</Button>
        {canArchive(user) && patient.estado === 'activo' && <Button type="button" variant="danger" disabled={busy}
          onClick={() => edit('archive', patient.id)}>Archivar paciente</Button>}
      </div>
    </PatientHeader>
    {['diagnosis','treatment','prescription'].includes(requestedTask)&&<p className="notice" role="status">{requestedTask==='diagnosis'?'Selecciona la consulta con Nuevo diagnóstico.':requestedTask==='treatment'?'Selecciona el diagnóstico con Nuevo tratamiento.':'Selecciona el tratamiento con Nueva receta.'} El paciente seleccionado se conserva.</p>}
    {patient.estado !== 'activo' && <p>{requestedTask ? 'Elige un paciente activo para continuar la tarea.' : 'El expediente de este paciente está disponible para consulta.'}</p>}
    {(canConsult || (canViewSpecialty && followUp)) && <section className="patient-next-step" aria-label="Continuar con este paciente">
      <div>
        <h3>Continuar con {patient.nombres}</h3>
        <p>{history.consultas.length ? `${history.consultas.length} ${history.consultas.length === 1 ? 'consulta registrada' : 'consultas registradas'}` : canConsult ? 'Registra la primera consulta para empezar el historial.' : 'Todavía no hay consultas.'}</p>
      </div>
      <div className="workday-actions">
        {canViewSpecialty && followUp && <Button variant="secondary" type="button" disabled={busy}
          onClick={() => setTab('specialty')}>{followUp}</Button>}
      </div>
    </section>}
    {nextAction && patient.estado === 'activo' && canPrescribe(user) && <p className="notice">
      Siguiente paso <Button variant="secondary" type="button" disabled={busy}
        onClick={() => edit(nextAction.kind, nextAction.parentId)}>{nextAction.label}</Button>
    </p>}
    {editor && !editor.specialty && <TaskDialog title="Registro clínico" busy={busy} onCancel={()=>setEditor(null)}><ClinicalActionForm key={`${editor.kind}-${editor.parentId}`} {...editor} service={service} onBusyChange={onBusyChange} onSessionExpired={onSessionExpired}
      onCancel={() => setEditor(null)} onCreated={result => {
        setNextAction(nextClinicalStep(editor.kind, result))
        setEditor(null)
        onActionCreated(editor.kind === 'archive' ? 'Paciente archivado. Se conserva su historial.' : 'Registro clínico guardado correctamente.')
      }} /></TaskDialog>}
    {catalogError && <p role="status">No se pudieron cargar los nombres de medicamentos. <button type="button" disabled={busy} onClick={() => setCatalogRetry(v => v + 1)}>Reintentar nombres</button></p>}
    <Tabs label="Secciones del expediente" busy={busy} active={tab} onChange={id => { setSpecialtySection(null); setTab(id) }}
      items={[
        { id: 'summary', label: 'Resumen' },
        { id: 'clinical', label: 'Consultas y tratamientos' },
        ...(canViewSpecialty ? [{ id: 'specialty', label: 'Seguimiento institucional' }] : []),
      ]} />
    {tab === 'summary' && <PatientSummary consultations={consultations} medicines={medicines}>
      {canViewSpecialty && <SpecialtyDemoPanel history={history} user={user} service={service} summaryOnly onSessionExpired={onSessionExpired} />}
    </PatientSummary>}
    {tab==='clinical' && <>
    {canConsult && registering && <TaskDialog title="Registrar consulta" busy={busy} returnFocusRef={consultationTrigger}
        onCancel={closeConsultation}>
        <p className="task-patient-context">Paciente · {patient.nombres} {patient.apellidos} · {patient.identificacion}</p>
        <ConsultationForm service={service} patientId={patient.id} appointment={appointment} onBusyChange={onBusyChange}
          onSessionExpired={onSessionExpired} onCancel={closeConsultation}
          onCreated={consultation => { closeConsultation(); setNextAction(nextClinicalStep('consultation', consultation)); onConsultationCreated(consultation) }} />
    </TaskDialog>}
    <ConsultationTimeline consultations={consultations} medicines={medicines} actionButton={actionButton} />
    </>}
    {tab==='specialty' && canViewSpecialty && <SpecialtyDemoPanel history={history} user={user} service={service} busy={busy} editor={editor?.specialty} sectionKind={specialtySection}
      onEdit={kind => { setRegistering(false); setEditor(kind ? { specialty: kind } : null) }} onCreated={onActionCreated} onBusyChange={onBusyChange} onSessionExpired={onSessionExpired} />}
  </section>
}
