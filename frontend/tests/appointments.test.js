import test from 'node:test'
import assert from 'node:assert/strict'
import { appointmentsInRange, canAttendAppointment } from '../src/operations/appointments.js'

test('la agenda respeta el día de Guatemala y las fechas civiles de Pediatría', () => {
  const rows = [
    { id: 'a', values: { fecha_hora: '2026-11-08T03:30:00Z', id_paciente: 'hospital-1', estado: 'programada' } },
    { id: 'b', values: { fecha: '2026-11-07', hora: '09:30:00', paciente_id: 'ped-1', estado: 'atendida' } },
    { id: 'c', values: { fecha_hora: '2026-11-08T06:00:00Z' } },
  ]
  const day = appointmentsInRange(rows, '2026-11-07', 1)
  assert.deepEqual(day.map(row => [row.id, row.time]), [['b', '09:30'], ['a', '21:30']])
  assert.equal(canAttendAppointment({ rol: 'secretaria' }, day[1]), false)
  assert.equal(canAttendAppointment({ rol: 'medico' }, day[0]), false)
  assert.equal(canAttendAppointment({ rol: 'medico' }, day[1]), true)
  assert.deepEqual(appointmentsInRange(rows, '2026-11-07', 7).map(row => row.id), ['b', 'a', 'c'])
})
