export default function DatabaseCard({ database }) {
  return (
    <article className="database-card">
      <div>
        <p className="database-engine">{database.engine}</p>
        <h2>{database.institution}</h2>
      </div>
      <span className={database.connected ? 'status connected' : 'status disconnected'}>
        {database.connected ? 'Conectada' : 'Sin conexión'}
      </span>
    </article>
  )
}
