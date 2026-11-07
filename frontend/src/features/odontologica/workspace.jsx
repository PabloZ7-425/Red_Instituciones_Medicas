import { useState } from 'react'
import { DentitionControl, ToothChart, ToothPicker } from './ToothChart.jsx'
import './workspace.css'

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
  FollowUpSummary,
  fieldControls: { pieza: ToothPicker },
  RecordDetails,
}
