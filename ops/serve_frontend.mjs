// Serve only the compiled application. No Vite dev/editor/filesystem middleware.
import { createServer } from 'node:http'
import { readFile, realpath, stat } from 'node:fs/promises'
import { resolve, sep, extname } from 'node:path'
import { pathToFileURL } from 'node:url'

export function staticServer(directory) {
  const base = resolve(directory)
  const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.woff2': 'font/woff2' }
  return createServer(async (request, response) => {
    const fail = status => { response.writeHead(status, { 'Content-Type': 'text/plain', 'Cache-Control': 'no-store' }); response.end() }
    if (!['GET', 'HEAD'].includes(request.method)) { response.setHeader('Allow', 'GET, HEAD'); return fail(405) }
    let pathname
    try { pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname) } catch { return fail(400) }
    if (pathname.includes('\0')) return fail(400)
    const candidate = resolve(base, '.' + (pathname === '/' ? '/index.html' : pathname))
    if (!candidate.startsWith(base + sep)) return fail(404)
    try {
      const actual = await realpath(candidate)
      if (!actual.startsWith(base + sep) || !(await stat(actual)).isFile()) return fail(404)
      const data = await readFile(actual)
      response.writeHead(200, { 'Content-Type': types[extname(actual)] ?? 'application/octet-stream', 'Content-Length': data.length, 'Cache-Control': 'no-cache', 'X-Content-Type-Options': 'nosniff' })
      response.end(request.method === 'HEAD' ? undefined : data)
    } catch (error) { fail(error.code === 'ENOENT' || error.code === 'ENOTDIR' ? 404 : 500) }
  })
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  staticServer(process.env.FRONTEND_BUILD_DIR ?? '/tmp/rim-frontend-dist').listen(5173, '0.0.0.0')
}
