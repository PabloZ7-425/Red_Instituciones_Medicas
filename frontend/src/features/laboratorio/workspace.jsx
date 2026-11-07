function RecordDetails({ row }) {
  return <>
    {row.tipo_examen_nombre && <div><dt>Examen</dt><dd>{row.tipo_examen_nombre}</dd></div>}
    {row.campos?.map(field => <div key={field.nombre}>
      <dt>{field.nombre}</dt>
      <dd>
        {typeof field.valor === 'boolean' ? field.valor ? 'Sí' : 'No' : String(field.valor)}
        {' '}{field.unidad ?? ''}{field.rango ? ` · Referencia: ${field.rango}` : ''}
      </dd>
    </div>)}
  </>
}

export default {
  name: 'Laboratorio Clínico',
  initials: 'LC',
  description: 'Consulta expedientes, registra resultados y organiza los tipos de examen.',
  priorities: ['paciente', 'resultado', 'tipo_examen', 'cita'],
  RecordDetails,
}
