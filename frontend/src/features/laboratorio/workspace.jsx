import Badge from '../../components/ui/Badge.jsx'
import ResultFields from './ResultFields.jsx'
import { outsideReference, resultTemplate } from './result-format.js'
import './workspace.css'

function SpecialtySection({ action, rows, children }) {
  return <section className="lab-followup">
    <header className="lab-followup__heading"><h4>{action.section}</h4><Badge>{rows.length} {rows.length === 1 ? 'resultado' : 'resultados'}</Badge></header>
    <p className="lab-followup__help">Revisa el examen, su estado y los valores registrados. Las referencias corresponden a cada resultado.</p>
    {children}
  </section>
}

function RecordDetails({ row }) {
  return <>
    {row.tipo_examen_nombre && <div><dt>Examen</dt><dd>{row.tipo_examen_nombre}</dd></div>}
    {!!row.campos?.length && <div className="lab-result-values"><dt>Valores del examen</dt><dd>
      <div className="lab-result-scroll" role="region" aria-label={`Valores de ${row.tipo_examen_nombre ?? 'examen'}`} tabIndex={0}>
        <table><caption>Valores registrados · {row.tipo_examen_nombre ?? 'Examen'}</caption>
          <thead><tr><th scope="col">Campo</th><th scope="col">Resultado</th><th scope="col">Unidad</th><th scope="col">Referencia</th></tr></thead>
          <tbody>{row.campos.map(field => <tr key={field.nombre}>
            <th scope="row">{field.nombre}</th>
            <td className="preserve-lines">{typeof field.valor === 'boolean' ? field.valor ? 'Sí' : 'No' : String(field.valor)}
              {outsideReference(field.valor, field.rango) && <span className="result-outside">Fuera de referencia</span>}</td>
            <td>{field.unidad || 'Sin unidad'}</td><td>{field.rango || 'Sin referencia'}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </dd></div>}
  </>
}

export default {
  name: 'Laboratorio Clínico',
  initials: 'LC',
  SpecialtySection,
  ResultFields,
  resultTemplate,
  RecordDetails,
}
