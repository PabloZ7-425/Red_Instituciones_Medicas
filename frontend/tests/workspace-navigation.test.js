import test from 'node:test'
import assert from 'node:assert/strict'
import { workspaceNavigation } from '../src/components/workspace-navigation.js'

test('el menú institucional muestra áreas con permiso y reserva administración al administrador', () => {
  const access = [
    { key: 'cita', group: 'Agenda' },
    { key: 'ingreso_hospitalario', group: 'Hospitalización' },
    { key: 'cirugia', group: 'Hospitalización' },
  ]
  const ids = (rol, resources) => workspaceNavigation({ rol, institucion: 'hospital' }, resources, true).map(item => item.id)
  assert.deepEqual(ids('secretaria', access.slice(0, 1)), ['home', 'patients', 'agenda'])
  assert.deepEqual(ids('admin', access), ['home', 'patients', 'agenda', 'hospitalization', 'surgery', 'admin'])
})

test('laboratorio y pediatría tienen navegación propia sin dependencia del motor de datos', () => {
  const resources = [{ key: 'resultado' }, { key: 'aplicacion_vacuna' }]
  const nav = institucion => workspaceNavigation({ institucion, rol: 'medico' }, resources, true).map(item => item.id)
  assert.deepEqual(nav('laboratorio'), ['home', 'patients', 'results'])
  assert.deepEqual(nav('pediatrico'), ['home', 'patients', 'vaccines'])
})
