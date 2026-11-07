import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import { canRegisterPatient } from './patient-form.js'
import { canWriteSpecialtyDemo } from './specialty-demo.js'

export const institutionTasks = {
  hospital: { kind: 'admission', start: 'Iniciar ingreso hospitalario', followUp: 'Ver ingresos y altas' },
  pediatrico: { kind: 'vaccine', start: 'Anotar una vacuna', followUp: 'Ver vacunas y crecimiento' },
  laboratorio: { kind: 'result', start: 'Cargar resultado de examen', followUp: 'Ver resultados de exámenes' },
  odontologica: { kind: 'procedure', start: 'Documentar procedimiento dental', followUp: 'Ver odontograma' },
}

const shiftDate = new Intl.DateTimeFormat('es-GT', {
  timeZone: 'America/Guatemala', weekday: 'long', day: 'numeric', month: 'long',
})

export default function Workday({ user, patients, loading, busy, canUseSpecialty, onSearch, onPatient, onClinicalTask }) {
  const [search, setSearch] = useState('')
  const task = user.institucion === 'pediatrico' && user.rol === 'secretaria'
    ? { kind: 'tutor', start: 'Vincular tutor' } : institutionTasks[user.institucion]
  const canStartTask = canUseSpecialty && canWriteSpecialtyDemo(user, task?.kind)
  const results = patients?.results.slice(0, 3) ?? []

  return <section className="workday" aria-labelledby="workday-title">
    <header className="workday-heading">
      <div>
        <p className="shell-overline workday-date">{shiftDate.format(new Date())}</p>
        <h2 id="workday-title">Pacientes y tareas</h2>
        <p>Abre un expediente o empieza la próxima atención.</p>
      </div>
      <div className="workday-actions">
        {canStartTask && <Button type="button" disabled={busy} onClick={() => onClinicalTask(task.kind)}>
          {task.start}
        </Button>}
      </div>
    </header>
    <div className="workday-body">
      <div className="workday-search">
        <h3>Encuentra a tu paciente</h3>
        <form onSubmit={event => { event.preventDefault(); onSearch(search.trim()) }}>
          <label htmlFor="workday-search">Identificación, nombre o apellido</label>
          <div className="workday-search__field">
            <input id="workday-search" type="search" maxLength={100} value={search}
              disabled={busy} onChange={event => setSearch(event.target.value)} />
            <Button type="submit" disabled={busy}>Buscar paciente</Button>
          </div>
        </form>
        {canRegisterPatient(user) && <button type="button" className="text-button" disabled={busy}
          onClick={() => onClinicalTask('patient')}>Registrar paciente nuevo</button>}
      </div>
      <div className="workday-directory">
        <h3>Directorio de pacientes</h3>
        {loading && <p role="status">Cargando pacientes…</p>}
        {patients?.count === 0 && <p>No hay pacientes que mostrar.</p>}
        {results.length > 0 && <ul>{results.map(patient => <li key={patient.id}>
          <button type="button" disabled={busy} onClick={() => onPatient(patient)}>
            <span><strong>{patient.nombres} {patient.apellidos}</strong><small>{patient.identificacion}</small></span>
            <span aria-hidden="true">→</span>
          </button>
        </li>)}</ul>}
      </div>
    </div>
  </section>
}
