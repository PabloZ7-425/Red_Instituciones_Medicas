import Dialog from './Dialog.jsx'

export default function ConfirmDialog({ title, busy, onCancel, onConfirm, children }) {
  return <Dialog title={title} busy={busy} onCancel={onCancel}>
    <h2>{title}</h2>
    {children}
    <form onSubmit={onConfirm}>
      <button disabled={busy}>{busy ? 'Guardando…' : title}</button>
      <button type="button" className="secondary" disabled={busy} onClick={onCancel}>Cancelar</button>
    </form>
  </Dialog>
}
