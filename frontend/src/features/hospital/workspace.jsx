import { localNow } from '../../operations/helpers.js'

function RecordDetails({ row, kind }) {
  return <>
    {row.cama_nombre && <div><dt>Cama</dt><dd>{row.cama_nombre}</dd></div>}
    {row.ingreso_descripcion && <div><dt>Ingreso</dt><dd>{row.ingreso_descripcion}</dd></div>}
    {row.fecha_hora_alta && kind === 'admission' && <div>
      <dt>Alta (hora de Guatemala)</dt>
      <dd>{localNow(new Date(row.fecha_hora_alta)).replace('T', ' ')}</dd>
    </div>}
  </>
}

export default {
  name: 'Hospital',
  initials: 'HG',
  description: 'Organiza la atención, la hospitalización y el seguimiento de tus pacientes.',
  priorities: ['paciente', 'ingreso_hospitalario', 'cita', 'movimiento_cama'],
  RecordDetails,
}
