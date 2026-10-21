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
  return {
    mode: 'http',
    me: ({ signal } = {}) => request('/auth/me/', { signal }),
    async login({ username, password }) {
      const result = await request('/auth/login/', { method: 'POST', body: { username: username.trim(), password } })
      // Django rota CSRF al iniciar sesión. No reutilizar el secreto anónimo.
      csrfToken = undefined
      await csrf()
      return result
    },
    async logout() {
      await request('/auth/logout/', { method: 'POST' })
      csrfToken = undefined
    },
    listPatients({ q = '', limit = 20, offset = 0, signal } = {}) {
      const query = new URLSearchParams({ q, limit: String(limit), offset: String(offset) })
      return request(`/pacientes/?${query}`, { signal })
    },
    createPatient: patient => request('/pacientes/', { method: 'POST', body: patient }),
    createConsultation: (patientId, consultation) => request(`/pacientes/${encodeURIComponent(patientId)}/consultas/`, { method: 'POST', body: consultation }),
    history: (id, { signal } = {}) => request(`/pacientes/${encodeURIComponent(id)}/historial/`, { signal }),
  }
}
