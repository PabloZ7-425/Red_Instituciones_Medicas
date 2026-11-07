import Badge from '../components/ui/Badge.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'

export default function PatientsPage({ user, draft, onDraft, onSearch, searchRef, page, loading, busy, registering,
  selected, choosingPatient, tutorAccess, demo, onSelect, onTutor, offset, onOffset }) {
  return <section className="clinical-panel directory-panel" aria-label="Pacientes">
    <header className="directory-heading"><p className="shell-overline">Directorio</p><h2>Pacientes</h2></header>
    <form className="search-form" onSubmit={event => { event.preventDefault(); if (!busy) onSearch(draft.trim()) }}>
      <label htmlFor="search">Buscar por inicio de identificación, nombre o apellido</label>
      <input id="search" ref={searchRef} type="search" disabled={busy} maxLength={100} value={draft}
        onChange={event => onDraft(event.target.value)} />
      <button disabled={busy}>Buscar</button>
    </form>
    {loading && <p className="ui-feedback" role="status">Cargando pacientes…</p>}
    {!loading && page?.count === 0 && <EmptyState title="No hay pacientes que coincidan con la búsqueda.">
      Prueba con otro nombre o identificación.
    </EmptyState>}
    {page && <>
      <p className="directory-count" aria-live="polite">{page.count} pacientes encontrados</p>
      <ul className="patient-list">{page.results.map(patient => <li key={patient.id}>
        <strong>{patient.nombres} {patient.apellidos}</strong>
        <div className="patient-list__meta"><span>{patient.identificacion}</span>
          <Badge tone={patient.estado === 'activo' ? 'success' : 'neutral'}>{patient.estado}</Badge>
        </div>
        {user.rol !== 'secretaria' && <button type="button" disabled={busy || registering} aria-pressed={selected === patient.id}
          onClick={() => onSelect(patient)}>{choosingPatient ? 'Elegir paciente' : 'Ver historial'}</button>}
        {user.rol === 'secretaria' && <button type="button" disabled={busy || registering} onClick={() => onSelect(patient)}>Ver ficha</button>}
        {tutorAccess && patient.estado === 'activo' && <button type="button" disabled={busy || registering} onClick={() => onTutor(patient)}>
          Gestionar tutores{demo ? ' · DEMO' : ''}
        </button>}
      </li>)}</ul>
      <nav className="pagination" aria-label="Páginas de pacientes">
        <button disabled={busy || loading || offset === 0} onClick={() => onOffset(Math.max(0, offset - page.limit))}>Anterior</button>
        <button disabled={busy || loading || offset + page.limit >= page.count} onClick={() => onOffset(offset + page.limit)}>Siguiente</button>
      </nav>
    </>}
  </section>
}
