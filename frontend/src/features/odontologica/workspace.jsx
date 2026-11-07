import { useState } from 'react'
import { DentitionControl, ToothChart, ToothPicker } from './ToothChart.jsx'
import './workspace.css'

const flow = [
  { key: 'cita', step: '01', title: 'Agenda de atención', detail: 'Consulta las citas y organiza el turno.' },
  { key: 'paciente', step: '02', title: 'Expedientes', detail: 'Ubica al paciente y revisa su historial.' },
  { key: 'procedimiento', step: '03', title: 'Procedimientos', detail: 'Consulta el trabajo asociado a cada pieza.' },
]

function Overview({ resources, openResource, busy }) {
  const allowed = new Map(resources.map(resource => [resource.key, resource]))
  const visible = flow.filter(item => allowed.has(item.key))

  return <section className="odonto-home" aria-label="Área odontológica">
    <header className="odonto-home__heading">
      <p className="shell-overline">Clínica odontológica · Operaciones</p>
      <h2>¿Qué necesitas hacer?</h2>
      <p>De la cita al expediente y al seguimiento por pieza dental.</p>
    </header>
    {visible.length > 0 && <ol className="odonto-flow">
      {visible.map(item => <li key={item.key}>
        <button type="button" disabled={busy} onClick={() => openResource(allowed.get(item.key))}>
          <span className="odonto-flow__index" aria-hidden="true">{item.step}</span>
          <strong>{item.title}</strong>
          <span>{item.detail}</span>
        </button>
      </li>)}
    </ol>}
  </section>
}

function FollowUpSummary({ rows }) {
  const [dentition, setDentition] = useState('permanent')
  const procedures = rows.procedure ?? []

  return <section className="odonto-summary" aria-label="Odontograma de procedimientos">
    <header className="odonto-summary__heading">
      <div>
        <p className="shell-overline">Seguimiento por pieza</p>
        <h4>Odontograma FDI</h4>
        <p>{procedures.length === 1 ? '1 procedimiento registrado' : `${procedures.length} procedimientos registrados`}</p>
      </div>
      <DentitionControl value={dentition} onChange={setDentition} />
    </header>
    <ToothChart dentition={dentition} procedures={procedures} />
    <ul className="odonto-legend" aria-label="Leyenda">
      <li><span />Sin registro</li>
      <li><span data-tone="recorded" />Con registro</li>
      <li><span data-tone="pending" />Con pendiente</li>
    </ul>
  </section>
}

function RecordDetails({ row }) {
  return row.tratamiento_descripcion && <div>
    <dt>Tratamiento vinculado</dt><dd>{row.tratamiento_descripcion}</dd>
  </div>
}

export default {
  name: 'Clínica Odontológica',
  initials: 'CO',
  description: 'Organiza las citas y documenta tratamientos y procedimientos por pieza dental.',
  priorities: ['paciente', 'cita', 'procedimiento', 'tratamiento'],
  Overview,
  FollowUpSummary,
  fieldControls: { pieza: ToothPicker },
  RecordDetails,
}
