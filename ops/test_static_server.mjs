import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, mkdir, writeFile, symlink, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { once } from 'node:events'
import { staticServer } from './serve_frontend.mjs'

test('compiled UI serves assets but rejects traversal, links outside root and dev endpoints', async t => {
  const folder = await mkdtemp(join(tmpdir(), 'rim-static-'))
  const root = join(folder, 'dist')
  await mkdir(root)
  await writeFile(join(root, 'index.html'), '<main>DEMO</main>')
  await writeFile(join(root, 'app.js'), 'export const demo = true')
  await writeFile(join(folder, 'private.txt'), 'private-fixture')
  await symlink(join(folder, 'private.txt'), join(root, 'outside.txt'))
  const server = staticServer(root).listen(0, '127.0.0.1')
  await once(server, 'listening')
  t.after(async () => { await new Promise(resolve => server.close(resolve)); await rm(folder, { recursive: true, force: true }) })
  const url = 'http://127.0.0.1:' + server.address().port
  assert.equal(await (await fetch(url)).text(), '<main>DEMO</main>')
  assert.match((await fetch(url + '/app.js')).headers.get('content-type'), /javascript/)
  assert.equal((await fetch(url, { method: 'HEAD' })).status, 200)
  for (const path of ['/..%2fprivate.txt', '/outside.txt', '/@fs/etc/passwd', '/__open-in-editor?file=private.txt']) assert.equal((await fetch(url + path)).status, 404)
  assert.equal((await fetch(url + '/%xx')).status, 400)
  assert.equal((await fetch(url, { method: 'POST' })).status, 405)
})
