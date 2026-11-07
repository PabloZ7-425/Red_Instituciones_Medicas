import DataTable from '../../components/ui/DataTable.jsx'

const columns = [
  { label: 'Fecha', value: row => row.fecha },
  { label: 'Peso (kg)', value: row => row.peso_kg ?? 'Sin dato' },
  { label: 'Talla (cm)', value: row => row.talla_cm ?? 'Sin dato' },
]

function Measurement({ rows, field, title }) {
  const values = rows.filter(row => row[field] != null && Number.isFinite(Number(row[field])))
    .map(row => ({ id: row.id, date: Date.parse(row.fecha), value: Number(row[field]) }))
    .filter(row => Number.isFinite(row.date))
  if (!values.length) return null
  const min = Math.min(...values.map(row => row.value))
  const max = Math.max(...values.map(row => row.value))
  const elapsed = values.at(-1).date - values[0].date
  const points = values.map(row => ({
    id: row.id,
    x: elapsed ? 16 + (row.date - values[0].date) / elapsed * 258 : 145,
    y: max === min ? 48 : 77 - (row.value - min) / (max - min) * 60,
  }))
  return <figure className="growth-chart">
    <figcaption>{title}</figcaption>
    <svg viewBox="0 0 290 96" role="img" aria-label={`Evolución de ${title.toLowerCase()}. Consulta los valores exactos en la tabla.`}>
      <path d="M16 78H274" className="growth-axis" />
      <polyline points={points.map(point => `${point.x},${point.y}`).join(' ')} />
      {points.map(point => <circle key={point.id} cx={point.x} cy={point.y} r="4" />)}
    </svg>
  </figure>
}

export default function GrowthChart({ rows }) {
  const measurements = [...rows].sort((a, b) => a.fecha.localeCompare(b.fecha))
  if (!measurements.length) return null
  return <>
    <div className="growth-charts">
      <Measurement rows={measurements} field="peso_kg" title="Peso (kg)" />
      <Measurement rows={measurements} field="talla_cm" title="Talla (cm)" />
    </div>
    <DataTable caption="Controles registrados" columns={columns} rows={measurements} />
  </>
}
