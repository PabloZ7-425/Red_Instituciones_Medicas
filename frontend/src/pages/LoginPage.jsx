import Button from '../components/ui/Button.jsx'
import ErrorBanner from '../components/ui/ErrorBanner.jsx'

export default function LoginPage({ busy, error, onLogin, demo }) {
  return <section className="login-panel" aria-labelledby="login-title">
    <p className="shell-overline">Acceso institucional</p>
    <h2 id="login-title">Iniciar sesión</h2>
    <p className="login-copy">Ingresa con la cuenta de tu institución para abrir tu espacio de trabajo.</p>
    <ErrorBanner error={error} />
    <form onSubmit={onLogin}>
      <label htmlFor="username">Usuario</label>
      <input id="username" name="username" required autoComplete="username" disabled={busy} />
      <label htmlFor="password">Contraseña</label>
      <input id="password" name="password" type="password" required autoComplete="current-password" disabled={busy} />
      <Button disabled={busy}>{busy ? 'Ingresando…' : 'Ingresar'}</Button>
    </form>
    {demo && <details className="demo-access">
      <summary>DEMO · Datos ficticios</summary>
      <p>Usa DEMO-medico-hospital, DEMO-medico-pediatrico, DEMO-medico-laboratorio o DEMO-medico-odontologica. Contraseña: DEMO-no-utilizar.</p>
    </details>}
  </section>
}
