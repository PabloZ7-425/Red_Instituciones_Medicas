import Badge from '../../components/ui/Badge.jsx'
import { localNow } from '../../operations/helpers.js'
import './workspace.css'

function FollowUpSummary({ rows }) {
  const admissions = rows.admission ?? []
  const open = admissions.filter(row => row.fecha_hora_alta === null).length

  return <section className="hospital-summary" aria-label="Resumen de hospitalización">
    <p className="shell-overline">Seguimiento hospitalario</p>
    <h4>Ingresos del paciente</h4>
    <dl>
      <div><dt>Ingresos registrados</dt><dd>{admissions.length}</dd></div>
      <div><dt>Sin alta registrada</dt><dd>{open}</dd></div>
      <div><dt>Con alta registrada</dt><dd>{admissions.length - open}</dd></div>
    </dl>
  </section>
}

function RecordDetails({ row, kind }) {
  const admission = kind === 'admission'
  return <>
    {admission && <div><dt>Situación del ingreso</dt><dd>
      <Badge tone={row.fecha_hora_alta === null ? 'success' : 'neutral'}>
        {row.fecha_hora_alta === null ? 'Sin alta registrada' : 'Con alta registrada'}
      </Badge>
    </dd></div>}
    {row.cama_nombre && <div><dt>Cama</dt><dd>{row.cama_nombre}</dd></div>}
    {row.ingreso_descripcion && <div><dt>Ingreso</dt><dd>{row.ingreso_descripcion}</dd></div>}
    {row.fecha_hora_alta && admission && <div>
      <dt>Alta (hora de Guatemala)</dt>
      <dd>{localNow(new Date(row.fecha_hora_alta)).replace('T', ' ')}</dd>
    </div>}
  </>
}

export default {
  name: 'Hospital',
  initials: 'HG',
  FollowUpSummary,
  RecordDetails,
}
