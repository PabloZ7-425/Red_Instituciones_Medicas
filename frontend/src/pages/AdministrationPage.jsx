import { useState } from 'react'
import EmptyState from '../components/ui/EmptyState.jsx'

const themes = {
  'Equipo y atención': /medico|profesional|enfermero|especialidad|tutor/,
  Infraestructura: /cama|habitacion|pabellon|quirofano/,
  'Medicamentos, vacunas y exámenes': /medicamento|vacuna|examen/,
  'Caja y seguros': /seguro|cobertura|pago|servicio/,
}

function textForSearch(value) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

export default function AdministrationPage({ resources, busy, onOpen }) {
  const [search, setSearch] = useState('')
  const visible = resources.filter(resource => textForSearch(resource.label).includes(textForSearch(search.trim())))
  const groups = {}
  for (const resource of visible) {
    const theme = Object.keys(themes).find(name => themes[name].test(resource.key)) ?? 'Otros catálogos'
    groups[theme] ??= []
    groups[theme].push(resource)
  }
  return <section className="resource-panel" aria-labelledby="catalog-title">
    <h2 id="catalog-title">Catálogos de la institución</h2>
    <label htmlFor="catalog-search">Buscar catálogo</label>
    <input id="catalog-search" type="search" maxLength={100} value={search}
      onChange={event => setSearch(event.target.value)} />
    {!visible.length && <EmptyState title="No hay catálogos que coincidan">Prueba con otro nombre.</EmptyState>}
    {Object.entries(groups).map(([theme, items]) => <section className="catalog-theme" key={theme}>
      <h3>{theme}</h3>
      <ul className="operation-list">{items.map(resource => <li key={resource.key}>
        <button className="task-card" type="button" disabled={busy} onClick={() => onOpen(resource)}>
          <strong>{resource.label}</strong><span aria-hidden="true">→</span>
        </button>
      </li>)}</ul>
    </section>)}
  </section>
}
