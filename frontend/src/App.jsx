import { useEffect, useState } from 'react'
import HomePage from './pages/HomePage.jsx'
import ClinicalPage from './clinical/ClinicalPage.jsx'
import { createClinicalClient } from './api/clinical.js'

export default function App() {
  const [view, setView] = useState('clinical')
  const [service, setService] = useState(null)
  useEffect(() => {
    let active = true
    async function configure() {
      // Nunca activar datos ficticios como respuesta a un fallo del backend.
      const client = import.meta.env.DEV && import.meta.env.VITE_CLINICAL_MODE === 'mock'
        ? (await import('./mocks/clinical-service.js')).createDemoClinicalService()
        : createClinicalClient({ baseUrl: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api' })
      if (active) setService(client)
    }
    configure()
    return () => { active = false }
  }, [])
  return <>
    <nav className="app-nav" aria-label="Secciones">
      <button aria-current={view === 'clinical' ? 'page' : undefined} onClick={() => setView('clinical')}>Pacientes</button>
      <button aria-current={view === 'health' ? 'page' : undefined} onClick={() => setView('health')}>Conexiones</button>
    </nav>
    {view === 'health' ? <HomePage /> : service ? <ClinicalPage service={service} /> : <p role="status">Preparando aplicación…</p>}
  </>
}
