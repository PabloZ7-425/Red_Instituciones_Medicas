import test from 'node:test'
import assert from 'node:assert/strict'
import { localNow, localToUtc, initialValues, serializeFields, age, financialActionsFor, canEditRecord, operationEditorFields } from '../src/operations/helpers.js'
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

test('state editor offers permitted steps and terminal records open as details',()=>{
  const resource={edit:true,state_transitions:{pendiente:['en_proceso','anulado'],en_proceso:['finalizado','anulado'],finalizado:[],anulado:[]},
    initial_states:['pendiente'],fields:{estado:{choices:['pendiente','en_proceso','finalizado','anulado']}}}
  assert.equal(canEditRecord(resource,{values:{estado:'pendiente'}}),true)
  assert.equal(canEditRecord(resource,{values:{estado:'finalizado'}}),false)
  assert.equal(canEditRecord(resource,{values:{estado:'anulado'}}),false)
  assert.deepEqual(operationEditorFields(resource,{values:{estado:'pendiente'}}).estado.choices,['pendiente','en_proceso','anulado'])
  assert.deepEqual(operationEditorFields(resource).estado.choices,['pendiente'])
  assert.equal(resource.fields.estado.choices.length,4)
})

test('approved decisions expose only cancellation and preserve their approved data',()=>{
  const resource={edit:true,editable_fields:['estado','monto_aprobado'],transition_only_states:['aprobado'],
    state_transitions:{aprobado:['anulado']},fields:{estado:{type:'text'},monto_aprobado:{type:'decimal'},factura_id:{type:'reference'}}}
  const record={values:{estado:'aprobado',monto_aprobado:'10.00',factura_id:'opaque'}}
  const fields=operationEditorFields(resource,record)
  assert.equal(fields.monto_aprobado.computed,true)
  assert.equal(fields.factura_id.computed,true)
  assert.deepEqual(serializeFields(fields,{...record.values,estado:'anulado'}),{estado:'anulado'})
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
