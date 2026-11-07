function RecordDetails({ row }) {
  return row.tratamiento_descripcion && <div>
    <dt>Tratamiento</dt><dd>{row.tratamiento_descripcion}</dd>
  </div>
}

export default {
  name: 'Clínica Odontológica',
  initials: 'CO',
  description: 'Organiza las citas y documenta tratamientos y procedimientos por pieza dental.',
  priorities: ['paciente', 'cita', 'procedimiento', 'tratamiento'],
  RecordDetails,
}
