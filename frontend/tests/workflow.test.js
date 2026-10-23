import test from 'node:test'
import assert from 'node:assert/strict'
import {continuation,clinicalTask} from '../src/operations/workflow.js'
import {createOperationsClient} from '../src/api/operations.js'

test('guided steps preserve opaque parent, patient and ancestor references across differing field names',()=>{
  const invoice={key:'factura',fields:{id_paciente:{type:'reference',resource:'paciente'}}}
  const detail={key:'detalle_factura',fields:{factura_id:{type:'reference',resource:'factura'},precio:{type:'decimal'}}}
  const payment={key:'pago',fields:{id_factura:{type:'reference',resource:'factura'},paciente_id:{type:'reference',resource:'paciente'},total:{type:'decimal',computed:true}}}
  const first=continuation(invoice,{id:'opaque-invoice',values:{id_paciente:'opaque-patient'}},detail)
  assert.deepEqual(first.values,{factura_id:'opaque-invoice'})
  const second=continuation(detail,{id:'opaque-detail',values:{factura_id:'opaque-invoice'}},payment,first.references)
  assert.deepEqual(second.values,{id_factura:'opaque-invoice',paciente_id:'opaque-patient'})
  assert.deepEqual(first.references,{paciente:'opaque-patient',factura:'opaque-invoice'})
})

test('clinical tasks route to the matching editor without promoting read-only roles',()=>{
  assert.equal(clinicalTask({key:'consulta'},{rol:'medico'}),'consultation')
  assert.equal(clinicalTask({key:'tratamiento'},{rol:'medico'}),'treatment')
  assert.equal(clinicalTask({key:'ingreso_hospitalario'},{rol:'admin'}),'admission')
  assert.equal(clinicalTask({key:'consulta'},{rol:'enfermero'}),null)
  assert.equal(clinicalTask({key:'procedimiento'},{rol:'laboratorista'}),null)
})

test('account navigation transmits search, page bounds and cancellation signal',async()=>{
  const calls=[],client=createOperationsClient(async(...args)=>calls.push(args)),signal=new AbortController().signal
  await client.accounts({q:'a+b %',offset:200,limit:20,signal})
  assert.equal(calls[0][0],'/operaciones/cuentas/?q=a%2Bb+%25&offset=200&limit=20')
  assert.equal(calls[0][1].signal,signal)
})
