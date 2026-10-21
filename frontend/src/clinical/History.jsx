import { useState } from 'react'
import ConsultationForm from './ConsultationForm.jsx'
import { canRegisterConsultation } from './consultation-form.js'

export default function History({ history, user, service, busy, onBusyChange, onSessionExpired, onConsultationCreated, onRefresh }) {
  const [registering, setRegistering] = useState(false)
  const patient = history.paciente
  return <section aria-label="Historial clínico" className="clinical-panel">
    <h2>{patient.nombres} {patient.apellidos}</h2>
    <dl className="patient-details">
      <div><dt>Identificación</dt><dd>{patient.identificacion}</dd></div>
      <div><dt>Nacimiento</dt><dd>{patient.fecha_nacimiento}</dd></div>
      <div><dt>Estado</dt><dd>{patient.estado}</dd></div>
    </dl>
    {patient.estado === 'archivado' && <p className="notice">Archivado el {patient.fecha_archivo ?? 'fecha no disponible'}: {patient.motivo_archivo ?? 'motivo no disponible'}. El historial se conserva.</p>}
    {patient.estado !== 'activo' && <p>El paciente no está activo; no se pueden registrar consultas.</p>}
    <button type="button" disabled={busy} onClick={onRefresh}>Actualizar historial</button>
    {patient.estado === 'activo' && canRegisterConsultation(user) && (registering
      ? <ConsultationForm service={service} patientId={patient.id} onBusyChange={onBusyChange} onSessionExpired={onSessionExpired}
          onCancel={() => setRegistering(false)} onCreated={consultation => { setRegistering(false); onConsultationCreated(consultation) }} />
      : <button type="button" disabled={busy} onClick={() => setRegistering(true)}>Nueva consulta</button>)}
    {history.consultas.length === 0 && <p>No hay consultas registradas.</p>}
    {history.consultas.map(consultation => <article key={consultation.id} className="consultation">
      <h3>Consulta · {consultation.fecha}</h3>
      <p className="preserve-lines">{consultation.notas_evolucion}</p>
      {consultation.diagnosticos.length === 0 && <p>Sin diagnósticos registrados.</p>}
      {consultation.diagnosticos.map(diagnosis => <section key={diagnosis.id}>
        <h4>{diagnosis.codigo_cie10} · {diagnosis.descripcion}</h4>
        {diagnosis.tratamientos.length === 0 && <p>Sin tratamientos registrados.</p>}
        {diagnosis.tratamientos.map(treatment => <div key={treatment.id}>
          <p className="preserve-lines">{treatment.indicaciones_generales}</p>
          {treatment.recetas.length === 0 && <p>Sin recetas registradas.</p>}
          <ul>{treatment.recetas.map(prescription => <li key={prescription.id}>
            {prescription.dosis} · {prescription.frecuencia}
            {prescription.via_administracion && ` · ${prescription.via_administracion}`}
          </li>)}</ul>
        </div>)}
      </section>)}
    </article>)}
  </section>
}
