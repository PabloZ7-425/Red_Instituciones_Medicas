const errorTitles = {
  0: 'Conexión interrumpida',
  400: 'Revisa los datos',
  401: 'Sesión requerida',
  403: 'Acceso restringido',
  404: 'Registro no disponible',
  409: 'Conflicto al guardar',
  503: 'Servicio no disponible',
}

export default function ErrorBanner({ error, children }) {
  if (!error) return null

  return <div role="alert" className="ui-error">
    <div>
      <strong>{errorTitles[error.status] ?? 'Ocurrió un problema'}</strong>
      <p>{error.message}</p>
      {Object.entries(error.fields ?? {}).map(([field, messages]) =>
        Array.isArray(messages) && <p key={field}>{field}: {messages.join(' ')}</p>
      )}
    </div>
    {children}
  </div>
}
