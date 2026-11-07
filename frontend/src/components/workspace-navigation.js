const home = { id: 'home', label: 'Inicio', title: 'Mi jornada', icon: 'grid', group: 'Inicio' }
const patients = { id: 'patients', label: 'Pacientes', title: 'Pacientes y expedientes', icon: 'file' }
const agenda = { id: 'agenda', label: 'Agenda', icon: 'calendar', group: 'Agenda', requires: 'cita' }

const modules = {
  hospital: [
    { id: 'hospitalization', label: 'Hospitalización', icon: 'bed', group: 'Hospitalización' },
    { id: 'surgery', label: 'Cirugía', icon: 'clinical', group: 'Hospitalización', resource: 'cirugia' },
    { id: 'pharmacy', label: 'Farmacia', icon: 'clinical', group: 'Farmacia' },
    { id: 'billing', label: 'Caja', icon: 'billing', group: 'Caja y seguros' },
  ],
  odontologica: [{ id: 'dentistry', label: 'Odontograma', icon: 'clinical', resource: 'procedimiento', followUp: 'procedure' }],
  laboratorio: [{ id: 'results', label: 'Resultados', icon: 'clinical', group: 'Atención y seguimiento', resource: 'resultado' }],
  pediatrico: [
    { id: 'growth', label: 'Crecimiento', icon: 'clinical', resource: 'control_de_crecimiento', followUp: 'growth' },
    { id: 'vaccines', label: 'Vacunación', icon: 'clinical', resource: 'aplicacion_vacuna', followUp: 'vaccine' },
  ],
}

export const roleLabels = {
  admin: 'Administración', medico: 'Profesional médico', secretaria: 'Secretaría',
  enfermero: 'Enfermería', laboratorista: 'Laboratorio',
}

export function workspaceNavigation(user, resources, hasOperations) {
  if (!hasOperations) return [patients]
  const visible = [home, patients]
  if (resources.some(resource => resource.key === agenda.requires)) visible.push(agenda)
  for (const item of modules[user.institucion] ?? []) {
    if (item.followUp && user.rol === 'secretaria') continue
    if (resources.some(resource => item.resource ? resource.key === item.resource : resource.group === item.group)) visible.push(item)
  }
  if (user.rol === 'admin') visible.push({
    id: 'admin', label: 'Administración', icon: 'settings',
    group: resources.some(resource => resource.group === 'Catálogos') ? 'Catálogos' : 'Usuarios y permisos',
  })
  return visible
}
