import test from 'node:test'
import assert from 'node:assert/strict'
import { outsideReference, resultTemplate } from '../src/features/laboratorio/result-format.js'

test('las plantillas proponen campos editables y los avisos requieren una referencia explícita', () => {
  assert.equal(resultTemplate('Uroanálisis')[1].nombre, 'pH')
  assert.ok(resultTemplate('Hemograma').every(field => field.valor === '' && field.rango === ''))
  assert.equal(resultTemplate('Examen personalizado'), undefined)
  assert.equal(outsideReference(14, '10,5 – 12,2'), true)
  assert.equal(outsideReference(12, '10 a 12'), false)
  assert.equal(outsideReference(5, 'Según el laboratorio'), false)
  assert.equal(outsideReference('14', '10–12'), false)
})
