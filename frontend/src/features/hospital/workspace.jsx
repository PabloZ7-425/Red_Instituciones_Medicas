import Badge from '../../components/ui/Badge.jsx'
import { localNow } from '../../operations/helpers.js'
import './workspace.css'

const routes = [
  { name: 'Hospitalización', description: 'Ingresos, camas y traslados.', keys: ['ingreso_hospitalario', 'cama', 'movimiento_cama'] },
  { name: 'Atención y cirugía', description: 'Agenda, triaje y registro quirúrgico.', keys: ['cita', 'emergencia', 'cirugia'] },
  { name: 'Farmacia', description: 'Entrega y administración de medicamentos.', keys: ['despacho_farmacia', 'aplicacion_enfermeria'] },
  { name: 'Caja', description: 'Facturas, conceptos y pagos.', keys: ['factura', 'detalle_factura', 'pago'] },
]

function Overview({ resources, openResource, busy }) {
  const allowed = new Map(resources.map(resource => [resource.key, resource]))
  const visible = routes.map(route => ({
    ...route,
    items: route.keys.map(key => allowed.get(key)).filter(Boolean),
  })).filter(route => route.items.length > 0)

  return <section className="hospital-home" aria-label="Área hospitalaria">
    <header className="hospital-home__heading">
      <p className="shell-overline">Hospital general · Operaciones</p>
      <h2>¿Qué necesitas hacer?</h2>
      <p>Accede a las áreas de atención disponibles para tu cuenta.</p>
    </header>
    {visible.length > 0 && <div className="hospital-routes">
      {visible.map(route => <section className="hospital-route" key={route.name}>
        <h3>{route.name}</h3>
        <p>{route.description}</p>
        <ul>
          {route.items.map(resource => <li key={resource.key}>
            <button type="button" disabled={busy} onClick={() => openResource(resource)}>
              <span>{resource.label}</span><span aria-hidden="true">↗</span>
            </button>
          </li>)}
        </ul>
      </section>)}
    </div>}
  </section>
}

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
  description: 'Organiza la atención, la hospitalización y el seguimiento de tus pacientes.',
  priorities: ['paciente', 'ingreso_hospitalario', 'cita', 'movimiento_cama'],
  Overview,
  FollowUpSummary,
  RecordDetails,
}
