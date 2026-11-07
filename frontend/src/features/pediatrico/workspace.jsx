import Badge from '../../components/ui/Badge.jsx'
import './workspace.css'

const guidance = {
  tutor: 'Personas de contacto y vínculo registrado con el paciente.',
  vaccine: 'Aplicaciones registradas con fecha, dosis y vacuna del catálogo institucional.',
  growth: 'Peso en kilogramos y talla en centímetros, junto con la fecha y las observaciones de cada control.',
}

function SpecialtySection({ kind, action, rows, children }) {
  return <section className={`pediatric-followup pediatric-followup--${kind}`}>
    <header className="pediatric-followup__heading"><h4>{action.section}</h4><Badge>{rows.length} {rows.length === 1 ? 'registro' : 'registros'}</Badge></header>
    <p className="pediatric-followup__help">{guidance[kind]}</p>
    {children}
  </section>
}

function RecordDetails({ row }) {
  return <>
    {row.parentesco == null && row.parentesco_legacy && <div>
      <dt>Parentesco histórico sin confirmar</dt><dd>{row.parentesco_legacy}</dd>
    </div>}
    {row.mediciones_legacy && Object.entries(row.mediciones_legacy)
      .filter(([, value]) => value != null)
      .map(([name, value]) => <div key={name}>
        <dt>{name} histórico (unidades sin confirmar)</dt><dd>{String(value)}</dd>
      </div>)}
    {row.vacuna_nombre && <div><dt>Vacuna</dt><dd>{row.vacuna_nombre}</dd></div>}
  </>
}

export default {
  name: 'Clínica Pediátrica',
  initials: 'CP',
  description: 'Acompaña el crecimiento, el registro de vacunas y la atención pediátrica.',
  priorities: ['paciente', 'consulta', 'aplicacion_vacuna', 'control_de_crecimiento', 'cita'],
  SpecialtySection,
  RecordDetails,
}
