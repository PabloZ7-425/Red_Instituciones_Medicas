import { useEffect, useState } from 'react'
import ClinicalPage from './clinical/ClinicalPage.jsx'
import { createClinicalClient } from './api/clinical.js'

export default function App() {
  const [service, setService] = useState(null)
  useEffect(() => {
    let active = true
    async function configure() {
      // Demo is explicit and development-only; production never falls back to mocks.
      const client = import.meta.env.DEV && import.meta.env.VITE_CLINICAL_MODE === 'mock'
        ? (await import('./mocks/clinical-service.js')).createDemoClinicalService({ role: ['admin', 'medico', 'secretaria', 'enfermero', 'laboratorista'].includes(import.meta.env.VITE_CLINICAL_DEMO_ROLE) ? import.meta.env.VITE_CLINICAL_DEMO_ROLE : 'medico' })
        : createClinicalClient({ baseUrl: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api' })
      if (active) setService(client)
    }
    configure()
    return () => { active = false }
  }, [])
  return service ? <ClinicalPage service={service} /> : <p role="status">Preparando aplicación…</p>
}
