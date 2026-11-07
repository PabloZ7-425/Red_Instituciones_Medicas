export default function ResultFields({ value, onChange, disabled, errorId }) {
  const change = (index, key, next) => onChange(value.map((row, i) => i === index ? { ...row, [key]: next } : row))
  return <fieldset className="lab-result-fields" disabled={disabled} aria-invalid={!!errorId} aria-describedby={errorId}><legend>Campos del resultado</legend>
    {value.map((row, index) => <fieldset key={row.key}><legend>Campo {index + 1}</legend>
      <label>Nombre del campo<input value={row.nombre} maxLength={100} onChange={e => change(index, 'nombre', e.target.value)} /></label>
      <label>Tipo de valor<select value={row.tipo} onChange={e => onChange(value.map((r, i) => i === index ? { ...r, tipo: e.target.value, valor: '' } : r))}>
        <option value="texto">Texto</option><option value="numero">Número</option><option value="booleano">Sí / No</option>
      </select></label>
      <label>Valor{row.tipo === 'booleano' ? <select value={row.valor} onChange={e => change(index, 'valor', e.target.value)}><option value="">Selecciona</option><option value="true">Sí</option><option value="false">No</option></select>
        : <input value={row.valor} maxLength={5000} inputMode={row.tipo === 'numero' ? 'decimal' : 'text'} onChange={e => change(index, 'valor', e.target.value)} />}</label>
      <label>Unidad (opcional)<input value={row.unidad} maxLength={100} onChange={e => change(index, 'unidad', e.target.value)} /></label>
      <label>Referencia (opcional)<input value={row.rango} maxLength={100} onChange={e => change(index, 'rango', e.target.value)} /></label>
      <button type="button" disabled={value.length === 1} onClick={() => onChange(value.filter((_, i) => i !== index))}>Quitar campo {index + 1}</button>
    </fieldset>)}
    <button type="button" disabled={value.length >= 50} onClick={() => onChange([...value, { key: crypto.randomUUID(), nombre: '', tipo: 'texto', valor: '', unidad: '', rango: '' }])}>Añadir campo</button>
  </fieldset>
}
