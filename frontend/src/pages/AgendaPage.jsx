import { useEffect, useState } from 'react'
import Badge from '../components/ui/Badge.jsx'
import Button from '../components/ui/Button.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import { todayInGuatemala } from '../clinical/patient-form.js'
import { appointmentsInRange, canAttendAppointment } from '../operations/appointments.js'
import { readOperationPages } from '../operations/read-pages.js'

const statusLabels = { programada: 'Programada', atendida: 'Atendida', cancelada: 'Cancelada' }

export default function AgendaPage({ service, user, busy, revision, onSchedule, onAttend, onOpen, onSessionExpired, blockedPatient, compact = false }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(false)
  const [retry, setRetry] = useState(0)
  const [days, setDays] = useState(1)

  useEffect(() => {
    const controller = new AbortController()
    setRows(null)
    setError(false)
    readOperationPages(service, 'cita', { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) setRows(result)
    }).catch(failure => {
      if (controller.signal.aborted) return
      if (failure.status === 401) onSessionExpired(failure)
      else setError(true)
    })
    return () => controller.abort()
  }, [service, revision, retry, onSessionExpired])

  const shown = rows ? appointmentsInRange(rows, todayInGuatemala(), compact ? 1 : days) : []
  const waiting = shown.filter(item => item.status === 'programada').length
  return <section className="agenda-page" aria-labelledby="agenda-title">
    <header>
      <div>
        <p className="shell-overline">{compact ? 'Atención de hoy' : 'Horario de Guatemala'}</p>
        <h2 id="agenda-title">{compact ? 'Citas de hoy' : 'Calendario de atención'}</h2>
        {rows && <p>{waiting} {waiting === 1 ? 'cita por atender' : 'citas por atender'}</p>}
      </div>
      {onSchedule && <Button type="button" disabled={busy} onClick={onSchedule}>Agendar cita</Button>}
    </header>
    {!compact && <div className="section-tabs" aria-label="Periodo de agenda">
      <Button type="button" variant="secondary" aria-pressed={days === 1} onClick={() => setDays(1)}>Hoy</Button>
      <Button type="button" variant="secondary" aria-pressed={days === 7} onClick={() => setDays(7)}>Próximos 7 días</Button>
    </div>}
    {!rows && !error && <p role="status">Cargando citas…</p>}
    {error && <p role="alert">No se pudo cargar la agenda. <button type="button" className="text-button" onClick={() => setRetry(value => value + 1)}>Reintentar</button></p>}
    {rows && shown.length === 0 && <EmptyState title="No hay citas en este periodo">Usa la agenda para consultar otras fechas o programar una atención.</EmptyState>}
    {shown.length > 0 && <ul className="agenda-list">{(compact ? shown.slice(0, 5) : shown).map(item => <li key={item.id}>
      <time dateTime={`${item.date}T${item.time ?? '00:00'}`}><strong>{item.time ?? '—'}</strong><small>{item.date}</small></time>
      <div><strong>{item.patient}</strong><p>{item.professional}</p></div>
      <Badge tone={item.status === 'atendida' ? 'success' : 'neutral'}>{statusLabels[item.status] ?? 'Registrada'}</Badge>
      {item.patientId !== blockedPatient && canAttendAppointment(user, item) && <Button type="button" variant="secondary" disabled={busy}
        aria-label={`Atender cita de ${item.patient}`} onClick={() => onAttend(item.patientId, item.id)}>Atender</Button>}
    </li>)}</ul>}
    <button className="text-button" type="button" disabled={busy} onClick={onOpen}>{compact ? 'Abrir agenda de la institución' : 'Ver todas las citas'}</button>
  </section>
}
