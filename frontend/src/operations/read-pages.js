export async function readOperationPages(service, key, { signal, patient } = {}) {
  const rows = []
  let offset = 0
  while (!signal?.aborted) {
    const page = await service.list(key, { patient, limit: 100, offset, signal })
    rows.push(...page.results)
    offset += page.results.length
    if (!page.results.length || offset >= page.count) break
  }
  return rows
}
