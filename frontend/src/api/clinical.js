import { createOperationsClient } from './operations.js'
import { createSpecialtyClient } from './specialties.js'

export class ApiError extends Error {
  constructor(status, code, message, fields = {}) {
    super(message)
    this.name = 'ApiError'
    Object.assign(this, { status, code, fields })
  }
}

// La sesión está en cookies HttpOnly; únicamente el CSRF se mantiene en memoria.
export function createClinicalClient({ baseUrl = '/api', fetchImpl = globalThis.fetch } = {}) {
  let csrfToken
  async function request(path, { method = 'GET', body, signal } = {}) {
    const headers = { Accept: 'application/json' }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    if (method !== 'GET') {
      if (!csrfToken) await csrf()
      headers['X-CSRFToken'] = csrfToken
    }
    let response
    try {
      response = await fetchImpl(`${baseUrl.replace(/\/$/, '')}${path}`, {
        method, credentials: 'include', headers, signal,
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      })
    } catch (error) {
      if (error.name === 'AbortError') throw error
      throw new ApiError(0, 'NETWORK_ERROR', 'No se pudo conectar. Comprueba tu conexión e inténtalo de nuevo.')
    }
    let data
    if (response.status !== 204) {
      try { data = await response.json() } catch {
        throw new ApiError(response.status, 'INVALID_RESPONSE', 'El servidor devolvió una respuesta no válida.')
      }
    }
    if (!response.ok) {
      if ([401, 403].includes(response.status)) csrfToken = undefined
      const error = data?.error
      throw new ApiError(response.status, error?.code ?? 'HTTP_ERROR',
        typeof error?.message === 'string' ? error.message : 'No se pudo completar la solicitud.',
        error?.fields && typeof error.fields === 'object' && !Array.isArray(error.fields) ? error.fields : {})
    }
    return data
  }
  async function csrf() {
    const data = await request('/auth/csrf/')
    if (typeof data?.csrfToken !== 'string' || !data.csrfToken) {
      throw new ApiError(200, 'INVALID_RESPONSE', 'No se pudo preparar una solicitud segura.')
    }
    csrfToken = data.csrfToken
  }
  const specialty = createSpecialtyClient(request, ApiError)
  return {
    mode: 'http',
    specialty,
    operations: createOperationsClient(request),
    me: ({ signal } = {}) => request('/auth/me/', { signal }),
    async login({ username, password }) {
      specialty.resumeReads()
      const result = await request('/auth/login/', { method: 'POST', body: { username: username.trim(), password } })
      // Django rota CSRF al iniciar sesión. No reutilizar el secreto anónimo.
      csrfToken = undefined
      await csrf()
      return result
    },
    async logout() {
      specialty.pauseReads()
      try { await request('/auth/logout/', { method: 'POST' }) }
      catch (error) { specialty.resumeReads(); throw error }
      csrfToken = undefined
    },
    listPatients({ q = '', limit = 20, offset = 0, signal } = {}) {
      const query = new URLSearchParams({ q, limit: String(limit), offset: String(offset) })
      return request(`/pacientes/?${query}`, { signal })
    },
    listMedicines({ q = '', limit = 20, offset = 0, signal } = {}) {
      const query = new URLSearchParams({ q, limit: String(limit), offset: String(offset) })
      return request(`/medicamentos/?${query}`, { signal }).then(page => {
        if (!page || !Number.isInteger(page.count) || page.count < 0 || !Number.isInteger(page.limit) || page.limit < 1 || page.limit > 100 || page.offset !== offset || !Array.isArray(page.results) || page.results.length > page.limit || page.results.some(m => !m || typeof m.id !== 'string' || !m.id.trim() || typeof m.nombre !== 'string' || !m.nombre.trim() || !(m.presentacion === null || typeof m.presentacion === 'string'))) {
          throw new ApiError(200, 'INVALID_RESPONSE', 'El catálogo devolvió una respuesta no válida.')
        }
        return page
      })
    },
    createDiagnosis: (id, data) => request(`/consultas/${encodeURIComponent(id)}/diagnosticos/`, { method: 'POST', body: data }),
    createTreatment: (id, data) => request(`/diagnosticos/${encodeURIComponent(id)}/tratamientos/`, { method: 'POST', body: data }),
    createPrescription: (id, data) => request(`/tratamientos/${encodeURIComponent(id)}/recetas/`, { method: 'POST', body: data }),
    archivePatient: (id, { motivo }) => request(`/pacientes/${encodeURIComponent(id)}/estado/`, { method: 'PATCH', body: { estado: 'archivado', motivo } }),
    createPatient: patient => request('/pacientes/', { method: 'POST', body: patient }),
    createConsultation: (patientId, consultation) => request(`/pacientes/${encodeURIComponent(patientId)}/consultas/`, { method: 'POST', body: consultation }),
    history: (id, { signal } = {}) => request(`/pacientes/${encodeURIComponent(id)}/historial/`, { signal }),
  }
}
