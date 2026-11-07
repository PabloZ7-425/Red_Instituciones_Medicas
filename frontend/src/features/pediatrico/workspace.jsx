function RecordDetails({ row }) {
  return <>
    {row.parentesco == null && row.parentesco_legacy && <div>
      <dt>Parentesco histórico sin confirmar</dt><dd>{row.parentesco_legacy}</dd>
    </div>}
    {row.mediciones_legacy && Object.entries(row.mediciones_legacy)
      .filter(([, value]) => value != null)
      .map(([name, value]) => <div key={name}>
        <dt>{name} histórico (unidades sin confirmar)</dt><dd>{String(value)}</dd>
      </div>)}
    {row.vacuna_nombre && <div><dt>Vacuna</dt><dd>{row.vacuna_nombre}</dd></div>}
  </>
}

export default {
  name: 'Clínica Pediátrica',
  initials: 'CP',
  description: 'Acompaña el crecimiento, el registro de vacunas y la atención pediátrica.',
  priorities: ['paciente', 'consulta', 'aplicacion_vacuna', 'control_de_crecimiento', 'cita'],
  RecordDetails,
}
