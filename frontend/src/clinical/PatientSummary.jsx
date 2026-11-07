import EmptyState from '../components/ui/EmptyState.jsx'

export default function PatientSummary({ consultations, medicines, children }) {
  const last = consultations[0]
  if (!last) return <><EmptyState title="No hay consultas registradas.">La primera consulta aparecerá en este resumen.</EmptyState>{children}</>
  const prescriptions = consultations.flatMap(consultation => consultation.diagnosticos.flatMap(diagnosis =>
    diagnosis.tratamientos.flatMap(treatment => treatment.recetas))).slice(0, 5)
  return <div className="patient-summary">
    <section><h3>Última consulta</h3><time>{last.fecha}</time><p className="preserve-lines">{last.notas_evolucion}</p></section>
    <section><h3>Diagnósticos de la última consulta</h3>
      {last.diagnosticos.length ? <ul>{last.diagnosticos.map(item => <li key={item.id}>{item.codigo_cie10} · {item.descripcion}</li>)}</ul>
        : <p>Sin diagnósticos registrados.</p>}
    </section>
    <section><h3>Últimas recetas registradas</h3>
      {prescriptions.length ? <ul>{prescriptions.map(item => <li key={item.id}>
        {medicines[item.medicamento_id] ?? 'Medicamento registrado'} · {item.dosis} · {item.frecuencia}
      </li>)}</ul> : <p>Sin recetas registradas.</p>}
    </section>
    {children}
  </div>
}
