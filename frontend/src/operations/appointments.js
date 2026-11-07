import { localNow } from './helpers.js'

export function appointmentDetails(row) {
  const { values, display = {} } = row
  const date = values.fecha_hora ? new Date(values.fecha_hora) : null
  const local = date && !Number.isNaN(date.getTime()) ? localNow(date) : ''
  return {
    patientId: values.id_paciente ?? values.paciente_id,
    patient: display.id_paciente ?? display.paciente_id ?? 'Paciente de la cita',
    professional: display.id_medico ?? display.medico_id ?? display.profesional_id ?? 'Profesional de la cita',
    date: local.slice(0, 10) || values.fecha,
    time: local.slice(11, 16) || values.hora?.slice(0, 5),
    status: values.estado,
  }
}

export function appointmentsInRange(rows, today, days) {
  const end = new Date(`${today}T00:00:00Z`)
  end.setUTCDate(end.getUTCDate() + days)
  const until = end.toISOString().slice(0, 10)
  return rows.map(row => ({ id: row.id, ...appointmentDetails(row) }))
    .filter(row => row.date >= today && row.date < until)
    .sort((a, b) => a.date.localeCompare(b.date) || (a.time ?? '').localeCompare(b.time ?? ''))
}

export function canAttendAppointment(user, item) {
  return item.status === 'programada' && !!item.patientId && ['admin', 'medico', 'laboratorista'].includes(user.rol)
}
