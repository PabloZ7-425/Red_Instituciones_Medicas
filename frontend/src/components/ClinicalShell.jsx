import { institutionProfile, institutions } from '../features/institutions.js'
import Button from './ui/Button.jsx'

const iconPaths = {
  brand: 'M4 12h4l2-4 4 8 2-4h4M12 2v3m0 14v3M2 12h3m14 0h3',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  file: 'M6 3h9l4 4v14H6zM14 3v5h5M9 12h7m-7 4h7',
  logout: 'M10 17l5-5-5-5m5 5H3m9-9h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7',
}

function Icon({ name }) {
  return <svg aria-hidden="true" className="shell-icon" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d={iconPaths[name]} />
  </svg>
}

function Brand() {
  return <div className="shell-brand">
    <span className="shell-brand__mark"><Icon name="brand" /></span>
    <span>Red de Instituciones<br />Médicas</span>
  </div>
}

export default function ClinicalShell({ user, hasOperations, workspace, busy, onWorkspaceChange, onLogout, children }) {
  if (!user) {
    return <main className="rim-shell auth-shell">
      <div className="auth-frame">
        <section className="auth-context" aria-label="Red de Instituciones Médicas">
          <Brand />
          <div className="auth-context__body">
            <p className="shell-overline">Plataforma clínica</p>
            <h1>Historiales<br /> clínicos</h1>
            <p>Un espacio de trabajo para la atención y el seguimiento de pacientes en tu institución.</p>
          </div>
          <ul className="auth-institutions">
            {Object.entries(institutions).map(([slug, institution]) => <li key={slug} data-institution={slug}>
              <span aria-hidden="true" className="institution-dot" />{institution.name}
            </li>)}
          </ul>
        </section>
        <div className="auth-content">{children}</div>
      </div>
    </main>
  }

  const institution = institutionProfile(user.institucion)
  const activeWorkspace = hasOperations ? workspace : 'patients'

  return <div className="rim-shell workspace-shell" data-institution={user.institucion}>
    <a className="shell-skip" href="#workspace-main">Ir al contenido</a>
    <aside className="shell-sidebar">
      <Brand />
      <div className="shell-institution">
        <span className="institution-monogram" aria-hidden="true">{institution.initials}</span>
        <div>
          <span className="shell-overline">Institución</span>
          <h2>{institution.name}</h2>
        </div>
      </div>
      <nav className="shell-nav" aria-label="Espacio de trabajo">
        <span className="shell-overline">Área de trabajo</span>
        {hasOperations && <button type="button" disabled={busy}
          aria-current={activeWorkspace === 'operations' ? 'page' : undefined}
          onClick={() => onWorkspaceChange('operations')}><Icon name="grid" />Inicio y operaciones</button>}
        <button type="button" disabled={busy} aria-current={activeWorkspace === 'patients' ? 'page' : undefined}
          onClick={() => onWorkspaceChange('patients')}><Icon name="file" />Pacientes y expedientes</button>
      </nav>
      <div className="shell-session">
        <span className="shell-overline">Sesión institucional</span>
        <p>{user.username} · {user.rol}</p>
        <Button type="button" variant="quiet" onClick={onLogout} disabled={busy}>
          <Icon name="logout" />Cerrar sesión
        </Button>
      </div>
    </aside>
    <main id="workspace-main" className="shell-content" tabIndex={-1}>
      <header className="shell-header">
        <div>
          <p className="shell-overline">Espacio de trabajo</p>
          <h1>{activeWorkspace === 'operations' ? 'Centro de operaciones' : 'Pacientes y expedientes'}</h1>
        </div>
        <span className="shell-header__context"><span aria-hidden="true" className="institution-dot" />{institution.name}</span>
      </header>
      {children}
    </main>
  </div>
}
