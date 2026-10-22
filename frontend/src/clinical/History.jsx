import { useEffect, useState } from 'react'
import ClinicalActionForm from './ClinicalActionForm.jsx'
import { canPrescribe, canArchive } from './clinical-actions.js'
import ConsultationForm from './ConsultationForm.jsx'
import SpecialtyDemoPanel from './SpecialtyDemoPanel.jsx'
import { canRegisterConsultation } from './consultation-form.js'

export default function History({ history, user, service, busy, onBusyChange, onSessionExpired, onConsultationCreated, onActionCreated, onRefresh }) {
  const [registering, setRegistering] = useState(false)
  const [editor, setEditor] = useState(null)
  const [medicines, setMedicines] = useState({}), [catalogError, setCatalogError] = useState(false)
  const [catalogRetry, setCatalogRetry] = useState(0)
  const patient = history.paciente
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
          const page = await service.listMedicines({ limit: 100, offset, signal: controller.signal })
          for (const m of page.results) names[m.id] = m.nombre
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
  const edit = (kind, parentId) => { setRegistering(false); setEditor({ kind, parentId }) }
  const actionButton = (kind, parentId, title) => patient.estado === 'activo' && canPrescribe(user) && <button type="button" disabled={busy} onClick={() => edit(kind, parentId)}>{title}</button>
  return <section aria-label="Historial clínico" className="clinical-panel">
    <h2>{patient.nombres} {patient.apellidos}</h2>
    <dl className="patient-details">
      <div><dt>Identificación</dt><dd>{patient.identificacion}</dd></div>
      <div><dt>Nacimiento</dt><dd>{patient.fecha_nacimiento}</dd></div>
      <div><dt>Estado</dt><dd>{patient.estado}</dd></div>
    </dl>
    {patient.estado === 'archivado' && <p className="notice">Archivado el {patient.fecha_archivo ?? 'fecha no disponible'}: {patient.motivo_archivo ?? 'motivo no disponible'}. El historial se conserva.</p>}
    {patient.estado !== 'activo' && <p>El paciente no está activo; no se permiten nuevas escrituras clínicas.</p>}
    <button type="button" disabled={busy} onClick={onRefresh}>Actualizar historial</button>
    {canArchive(user) && patient.estado !== 'archivado' && <button type="button" disabled={busy} onClick={() => edit('archive', patient.id)}>Archivar paciente</button>}
    {editor && !editor.specialty && <ClinicalActionForm key={`${editor.kind}-${editor.parentId}`} {...editor} service={service} onBusyChange={onBusyChange} onSessionExpired={onSessionExpired}
      onCancel={() => setEditor(null)} onCreated={() => { setEditor(null); onActionCreated(editor.kind === 'archive' ? 'Paciente archivado; el historial se conserva.' : 'Registro clínico guardado correctamente.') }} />}
    {catalogError && <p role="status">No se pudieron cargar los nombres de medicamentos. <button type="button" disabled={busy} onClick={() => setCatalogRetry(v => v + 1)}>Reintentar nombres</button></p>}
    {patient.estado === 'activo' && canRegisterConsultation(user) && (registering
      ? <ConsultationForm service={service} patientId={patient.id} onBusyChange={onBusyChange} onSessionExpired={onSessionExpired}
          onCancel={() => setRegistering(false)} onCreated={consultation => { setRegistering(false); onConsultationCreated(consultation) }} />
      : <button type="button" disabled={busy} onClick={() => { setEditor(null); setRegistering(true) }}>Nueva consulta</button>)}
    {history.consultas.length === 0 && <p>No hay consultas registradas.</p>}
    {history.consultas.map(consultation => <article key={consultation.id} className="consultation">
      <h3>Consulta · {consultation.fecha}</h3>
      <p className="preserve-lines">{consultation.notas_evolucion}</p>
      {actionButton('diagnosis', consultation.id, 'Nuevo diagnóstico')}
      {consultation.diagnosticos.length === 0 && <p>Sin diagnósticos registrados.</p>}
      {consultation.diagnosticos.map(diagnosis => <section key={diagnosis.id}>
        <h4>{diagnosis.codigo_cie10} · {diagnosis.descripcion}</h4>
        {actionButton('treatment', diagnosis.id, 'Nuevo tratamiento')}
        {diagnosis.tratamientos.length === 0 && <p>Sin tratamientos registrados.</p>}
        {diagnosis.tratamientos.map(treatment => <div key={treatment.id}>
          <p className="preserve-lines">{treatment.indicaciones_generales}</p>
          {actionButton('prescription', treatment.id, 'Nueva receta')}
          {treatment.recetas.length === 0 && <p>Sin recetas registradas.</p>}
          <ul>{treatment.recetas.map(prescription => <li key={prescription.id}>
            <strong>{medicines[prescription.medicamento_id] ?? 'Nombre de medicamento no disponible'}</strong> · {prescription.dosis} · {prescription.frecuencia}
            {prescription.via_administracion && ` · ${prescription.via_administracion}`}
          </li>)}</ul>
        </div>)}
      </section>)}
    </article>)}
    {(service.specialty || (service.mode === 'mock' && service.specialtyDemo)) && <SpecialtyDemoPanel history={history} user={user} service={service} busy={busy} editor={editor?.specialty}
      onEdit={kind => { setRegistering(false); setEditor(kind ? { specialty: kind } : null) }} onCreated={onActionCreated} onBusyChange={onBusyChange} onSessionExpired={onSessionExpired} />}
  </section>
}
