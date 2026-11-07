import { useEffect, useState } from 'react'
import Button from '../../components/ui/Button.jsx'
import StatCard from '../../components/ui/StatCard.jsx'
import { readOperationPages } from '../../operations/read-pages.js'

export default function HospitalOverview({ service, patient, busy, revision, onOpen, onSessionExpired }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(false)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setRows(null); setError(false)
    readOperationPages(service, 'ingreso_hospitalario', { signal: controller.signal, patient }).then(result => {
      if (!controller.signal.aborted) setRows(result)
    }).catch(failure => {
      if (controller.signal.aborted) return
      if (failure.status === 401) onSessionExpired(failure)
      else setError(true)
    })
    return () => controller.abort()
  }, [service, patient, revision, retry, onSessionExpired])
  const active = rows?.filter(row => row.values.fecha_hora_alta == null).length
  return <section className="agenda-page" aria-labelledby="hospital-focus-title">
    <header><div><p className="shell-overline">Seguimiento hospitalario</p><h2 id="hospital-focus-title">Ingresos y altas</h2></div>
      <Button type="button" variant="secondary" disabled={busy} onClick={onOpen}>Consultar ingresos</Button></header>
    {!rows && !error && <p role="status">Cargando ingresos…</p>}
    {error && <p role="alert">No se pudieron consultar los ingresos. <button type="button" className="text-button"
      onClick={() => setRetry(value => value + 1)}>Reintentar</button></p>}
    {rows && <div className="stats-list">
      <StatCard label="Ingresos sin alta" value={active} />
      <StatCard label="Ingresos con alta registrada" value={rows.length - active} />
    </div>}
  </section>
}
