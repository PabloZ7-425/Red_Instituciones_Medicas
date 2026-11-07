export default function Tabs({ label, items, active, busy, onChange }) {
  return <nav className="section-tabs" aria-label={label}>
    {items.map(item => <button key={item.id} type="button" disabled={busy}
      aria-current={active === item.id ? 'page' : undefined} onClick={() => onChange(item.id)}>{item.label}</button>)}
  </nav>
}
