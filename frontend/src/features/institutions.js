import hospital from './hospital/workspace.jsx'
import pediatrico from './pediatrico/workspace.jsx'
import laboratorio from './laboratorio/workspace.jsx'
import odontologica from './odontologica/workspace.jsx'

export const institutions = { hospital, pediatrico, laboratorio, odontologica }

export function institutionProfile(slug) {
  return Object.hasOwn(institutions, slug) ? institutions[slug] : {
    name: 'Institución',
    initials: 'RI',
  }
}
