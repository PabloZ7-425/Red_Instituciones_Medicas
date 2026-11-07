import { useState } from 'react'
import { specialtyActions } from '../../clinical/specialty-demo.js'

const validPieces = specialtyActions.procedure.fields.pieza.options
const quadrants = [
  { name: 'Superior derecho', permanent: '1', temporary: '5', reverse: true },
  { name: 'Superior izquierdo', permanent: '2', temporary: '6', reverse: false },
  { name: 'Inferior derecho', permanent: '4', temporary: '8', reverse: true },
  { name: 'Inferior izquierdo', permanent: '3', temporary: '7', reverse: false },
]

export function ToothChart({ dentition, pieces = validPieces, selected, onSelect, disabled, procedures = [] }) {
  const notes = new Map()
  for (const record of procedures) {
    const piece = String(record.pieza)
    const detail = notes.get(piece) ?? { total: 0, pending: 0 }
    detail.total += 1
    if (record.estado === 'pendiente') detail.pending += 1
    notes.set(piece, detail)
  }

  return <div className="odonto-chart" aria-label="Cuadrantes dentales">
    {quadrants.map(quadrant => {
      const items = pieces.filter(piece => piece.startsWith(quadrant[dentition])).sort()
      if (quadrant.reverse) items.reverse()
      if (items.length === 0) return null

      return <section key={quadrant.name} className="odonto-quadrant" aria-label={quadrant.name}>
        <p>{quadrant.name}</p>
        <ul style={{ '--pieces': items.length }}>
          {items.map(piece => {
            const detail = notes.get(piece)
            const tone = detail ? (detail.pending ? 'pending' : 'recorded') : undefined
            return <li key={piece}>
              {onSelect
                ? <button type="button" className="odonto-piece" disabled={disabled}
                  aria-label={`Seleccionar pieza ${piece}`} aria-pressed={selected === piece} onClick={() => onSelect(piece)}>
                  {piece}
                </button>
                : <span className="odonto-piece" data-tone={tone}>
                  {piece}
                  {detail && <span className="odonto-visually-hidden">
                    , {detail.total} {detail.total === 1 ? 'registro' : 'registros'}{detail.pending > 0 ? `, ${detail.pending} pendiente(s)` : ''}
                  </span>}
                </span>}
            </li>
          })}
        </ul>
      </section>
    })}
  </div>
}

export function DentitionControl({ value, onChange, disabled }) {
  return <div className="odonto-dentition" role="group" aria-label="Tipo de dentición">
    <button type="button" aria-pressed={value === 'permanent'} disabled={disabled}
      onClick={() => onChange('permanent')}>Permanente</button>
    <button type="button" aria-pressed={value === 'temporary'} disabled={disabled}
      onClick={() => onChange('temporary')}>Temporal</button>
  </div>
}

export function ToothPicker({ id, name, options, disabled, errorId }) {
  const [value, setValue] = useState('')
  const [dentition, setDentition] = useState('permanent')

  function choose(piece) {
    setValue(piece)
    if (piece) setDentition(Number(piece[0]) > 4 ? 'temporary' : 'permanent')
  }

  return <div className="odonto-picker">
    <select id={id} name={name} value={value} onChange={event => choose(event.target.value)}
      disabled={disabled} aria-invalid={!!errorId} aria-describedby={errorId}>
      <option value="">Selecciona</option>
      {options.map(piece => <option key={piece} value={piece}>{piece}</option>)}
    </select>
    <div className="odonto-picker__heading">
      <p>Selecciona por código FDI o desde el gráfico.</p>
      <DentitionControl value={dentition} onChange={setDentition} disabled={disabled} />
    </div>
    <ToothChart dentition={dentition} pieces={options} selected={value} onSelect={choose} disabled={disabled} />
  </div>
}
