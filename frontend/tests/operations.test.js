import test from 'node:test'
import assert from 'node:assert/strict'
import { localNow, localToUtc, initialValues, serializeFields, age, financialActionsFor } from '../src/operations/helpers.js'
import { createOperationsClient } from '../src/api/operations.js'

test('civil defaults and age use Guatemala even across UTC midnight',()=>{
  assert.equal(localNow(new Date('2026-10-23T02:30:00Z')),'2026-10-22T20:30:00')
  assert.equal(localToUtc('2026-10-22T20:30:00'),'2026-10-23T02:30:00.000Z')
  assert.equal(age('2000-10-23','2026-10-22'),25)
  assert.equal(age('2000-10-23','2026-10-23'),26)
})

test('financial actions follow invoice/payment lifecycle and permission manifest',()=>{
  const invoice={actions:['emitir','anular']},payment={actions:['revertir']}
  assert.deepEqual(financialActionsFor(invoice,{values:{estado:'Borrador'}}),['emitir','anular'])
  for(const estado of ['Pendiente','Parcial','Pagada','pendiente','parcial','pagada'])assert.deepEqual(financialActionsFor(invoice,{values:{estado}}),['anular'])
  assert.deepEqual(financialActionsFor(invoice,{values:{estado:'Anulada'}}),[])
  assert.deepEqual(financialActionsFor(payment,{values:{estado:'Procesado'}}),['revertir'])
  assert.deepEqual(financialActionsFor(payment,{values:{estado:'Anulado'}}),[])
  assert.deepEqual(financialActionsFor({}, {values:{estado:'Borrador'}}),[])
})

test('financial transport preserves optimistic version and explicit action',async()=>{
  const calls=[],client=createOperationsClient(async(...args)=>calls.push(args))
  await client.financialAction('factura','opaque/id','emitir','version-1')
  assert.deepEqual(calls,[['/operaciones/factura/opaque%2Fid/',{method:'POST',body:{accion:'emitir',version:'version-1'}}]])
})
test('forms prefill context, preserve decimals, omit derived totals and convert timestamps',()=>{
  const fields={paciente:{type:'reference',context:'patient'},fecha:{type:'date',default:'now'},hora:{type:'datetime',default:'now'},total:{type:'decimal',computed:true},precio:{type:'decimal'}}
  const values=initialValues(fields,{precio:'12.30'},'H-P-1')
  assert.equal(values.paciente,'H-P-1');assert.match(values.fecha,/^\d{4}-\d{2}-\d{2}$/);assert.equal(values.precio,'12.30');assert.equal('total' in values,false)
  const dto=serializeFields(fields,{...values,hora:'2026-10-22T20:30:00',total:'100'})
  assert.equal(dto.hora,'2026-10-23T02:30:00.000Z');assert.equal(dto.precio,'12.30');assert.equal('total' in dto,false)
})
test('operation transport uses encoded routes, explicit query scope and optimistic version',async()=>{
  const calls=[];const client=createOperationsClient(async(...args)=>{calls.push(args);return {}})
  await client.list('cita',{q:'Ana %',patient:'H-P-1',lookup:true,offset:20})
  assert.match(calls[0][0],/q=Ana\+%25/);assert.match(calls[0][0],/patient=H-P-1/);assert.match(calls[0][0],/lookup=1/)
  await client.update('medicamento','opaque/id',{nombre:'DEMO'},'v1')
  assert.equal(calls[1][0],'/operaciones/medicamento/opaque%2Fid/');assert.deepEqual(calls[1][1],{method:'PATCH',body:{values:{nombre:'DEMO'},version:'v1'}})
})
