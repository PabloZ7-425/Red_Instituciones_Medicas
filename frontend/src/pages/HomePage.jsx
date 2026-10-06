import { useEffect, useState } from 'react'

import { getDatabaseHealth } from '../api/health.js'
import DatabaseCard from '../components/DatabaseCard.jsx'


export default function HomePage() {
  const [databases, setDatabases] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadHealth() {
    setLoading(true)
    setError('')

    try {
      const data = await getDatabaseHealth()
      setDatabases(Object.values(data.databases))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHealth()
  }, [])

  return (
    <main className="page-shell">
      <header className="hero">
        <p className="eyebrow">Bases de Datos II</p>
        <h1>Plataforma de historiales clínicos</h1>
        <p className="hero-copy">
          Una interfaz para cuatro instituciones y cuatro motores de bases de datos.
        </p>
      </header>

      <section className="section-heading">
        <div>
          <p className="eyebrow">Estado del entorno</p>
          <h2>Conexiones disponibles</h2>
        </div>
        <button type="button" onClick={loadHealth} disabled={loading}>
          {loading ? 'Verificando…' : 'Verificar de nuevo'}
        </button>
      </section>

      {error && <p className="error-message">{error}</p>}

      <section className="database-grid">
        {databases.map((database) => (
          <DatabaseCard key={database.institution} database={database} />
        ))}
      </section>

      {!loading && !error && databases.length === 0 && (
        <p className="empty-message">Todavía no hay resultados de conexión.</p>
      )}
    </main>
  )
}
