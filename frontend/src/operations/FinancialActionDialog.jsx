import { useRef, useState } from 'react'
import ConfirmDialog from '../components/ui/ConfirmDialog.jsx'

export const actionLabels = {emitir:'Emitir factura',anular:'Anular factura',revertir:'Revertir pago'}
const descriptions = {
  emitir:'La factura quedará lista para cobrar. Sus conceptos y totales ya no podrán modificarse.',
  anular:'La factura conservará sus conceptos y quedará anulada. Primero deben revertirse sus pagos y cancelarse las reclamaciones activas.',
  revertir:'El pago conservará su importe y referencia, quedará anulado y su saldo volverá a estar pendiente en la factura.',
}
export default function FinancialActionDialog({action,resource,record,service,onClose,onSaved,onBusy,onSessionExpired}) {
  const inFlight=useRef(false)
  const [saving,setSaving]=useState(false),[error,setError]=useState(null)
  async function submit(e) {
    e.preventDefault();if(inFlight.current)return
    inFlight.current=true;setSaving(true);onBusy(true);setError(null)
    try {await service.financialAction(resource.key,record.id,action,record.version);onSaved()}
    catch(e){setError(e);if(e.status===401)onSessionExpired(e)}
    finally{inFlight.current=false;setSaving(false);onBusy(false)}
  }
  return <ConfirmDialog title={actionLabels[action]} busy={saving} onCancel={onClose} onConfirm={submit}>
    <p>{record.values.numero_factura??record.values.numero??record.values.referencia_pago??record.values.referencia}</p>
    <p>{descriptions[action]}</p>
    {error&&<div role="alert"><p>{error.status===409?'El registro cambió o su estado no permite esta acción. Actualiza la lista antes de repetir.':error.message}</p>{Object.values(error.fields??{}).flat().map((message,i)=><p key={i}>{message}</p>)}</div>}
  </ConfirmDialog>
}

export function FinancialSummary({record}) {
  if(!record.financial)return null
  const f=record.financial
  return <p>Estado: {record.values.estado} · Cobrado paciente: Q {f.cobrado_paciente} · Saldo paciente: Q {f.saldo_paciente} · Cobrado seguro: Q {f.cobrado_seguro} · Saldo seguro: Q {f.saldo_seguro}</p>
}
