import Timeline from '../components/ui/Timeline.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'

export default function ConsultationTimeline({ consultations, medicines, actionButton }) {
  if (!consultations.length) return <EmptyState title="No hay consultas registradas." />
  return <Timeline items={consultations} renderItem={(consultation, index) => <details className="consultation" open={index === 0}>
    <summary><strong>Consulta · {consultation.fecha}</strong></summary>
    <p className="preserve-lines">{consultation.notas_evolucion}</p>
    {actionButton('diagnosis', consultation.id, 'Nuevo diagnóstico')}
    {consultation.diagnosticos.length === 0 && <p>Sin diagnósticos registrados.</p>}
    {consultation.diagnosticos.map(diagnosis => <section className="timeline-diagnosis" key={diagnosis.id}>
      <h4>{diagnosis.codigo_cie10} · {diagnosis.descripcion}</h4>
      {actionButton('treatment', diagnosis.id, 'Nuevo tratamiento')}
      {diagnosis.tratamientos.length === 0 && <p>Sin tratamientos registrados.</p>}
      {diagnosis.tratamientos.map(treatment => <div className="timeline-treatment" key={treatment.id}>
        <p className="preserve-lines">{treatment.indicaciones_generales}</p>
        {actionButton('prescription', treatment.id, 'Nueva receta')}
        {treatment.recetas.length === 0 && <p>Sin recetas registradas.</p>}
        <ul>{treatment.recetas.map(prescription => <li key={prescription.id}>
          <strong>{medicines[prescription.medicamento_id] ?? 'Nombre de medicamento no disponible'}</strong> · {prescription.dosis} · {prescription.frecuencia}
          {prescription.via_administracion && ` · ${prescription.via_administracion}`}
        </li>)}</ul>
      </div>)}
    </section>)}
  </details>} />
}
