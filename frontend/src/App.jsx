import { useEffect, useState } from 'react'
import HomePage from './pages/HomePage.jsx'
import ClinicalPage from './clinical/ClinicalPage.jsx'
import { createClinicalClient } from './api/clinical.js'

export default function App() {
  const [view, setView] = useState('clinical')
  const [busy, setBusy] = useState(false)
  const [service, setService] = useState(null)
  useEffect(() => {
    let active = true
    async function configure() {
      // Nunca activar datos ficticios como respuesta a un fallo del backend.
      const client = import.meta.env.DEV && import.meta.env.VITE_CLINICAL_MODE === 'mock'
        ? (await import('./mocks/clinical-service.js')).createDemoClinicalService({ role: ['admin', 'medico', 'secretaria', 'enfermero', 'laboratorista'].includes(import.meta.env.VITE_CLINICAL_DEMO_ROLE) ? import.meta.env.VITE_CLINICAL_DEMO_ROLE : 'medico' })
        : createClinicalClient({ baseUrl: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api' })
      if (active) setService(client)
    }
    configure()
    return () => { active = false }
  }, [])
  return <>
    <nav className="app-nav" aria-label="Secciones">
      <button disabled={busy} aria-current={view === 'clinical' ? 'page' : undefined} onClick={() => setView('clinical')}>Pacientes</button>
      <button disabled={busy} aria-current={view === 'health' ? 'page' : undefined} onClick={() => setView('health')}>Conexiones</button>
    </nav>
    {view === 'health' ? <HomePage /> : service ? <ClinicalPage service={service} onBusyChange={setBusy} /> : <p role="status">Preparando aplicación…</p>}
  </>
}
