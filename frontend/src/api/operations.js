export function createOperationsClient(request) {
  const root = '/operaciones/'
  return {
    accounts: () => request(root+'cuentas/'),
    bindProfessional: (id, profesional_id) => request(root+'cuentas/', {method:'PATCH',body:{id,profesional_id}}),
    createAccount: values => request(root+'cuentas/', {method:'POST',body:values}),
    setAccountActive: (id, activo) => request(root+'cuentas/', {method:'PATCH',body:{id,activo}}),
    manifest: ({ signal } = {}) => request(root, { signal }),
    list(name, { q = '', offset = 0, limit = 20, patient, lookup, signal } = {}) {
      const query = new URLSearchParams({ q, offset, limit })
      if (patient) query.set('patient', patient)
      if (lookup) query.set('lookup', '1')
      return request(`${root}${encodeURIComponent(name)}/?${query}`, { signal })
    },
    create: (name, values) => request(`${root}${encodeURIComponent(name)}/`, { method: 'POST', body: values }),
    update: (name, id, values, version) => request(`${root}${encodeURIComponent(name)}/${encodeURIComponent(id)}/`, { method: 'PATCH', body: { values, version } }),
  }
}
