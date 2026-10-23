// Civil dates stay in Guatemala; timestamps are stored as UTC instants.
export function localNow(now = new Date()) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Guatemala', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).formatToParts(now).map(p => [p.type, p.value]))
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}`
}
export function localToUtc(value) { return new Date(`${value}-06:00`).toISOString() }
export function initialValues(fields, values = {}, patient) {
  const now = localNow()
  return Object.fromEntries(Object.entries(fields).filter(([,f]) => !f.computed).map(([key,f]) => {
    let value = values[key]
    if (value == null) value = f.context === 'patient' && patient ? patient : f.default === 'now' ? f.type === 'date' ? now.slice(0,10) : now : f.default === 'code' ? `F-${crypto.randomUUID().slice(0,8).toUpperCase()}` : f.default ?? ''
    else if (f.type === 'datetime') value = localNow(new Date(value))
    return [key,value]
  }))
}
export function age(birth, today = localNow().slice(0,10)) {
  const [y,m,d]=birth.split('-').map(Number),[ty,tm,td]=today.split('-').map(Number)
  return ty-y-(tm<m || tm===m && td<d ? 1 : 0)
}
export function serializeFields(fields, values) {
  return Object.fromEntries(Object.entries(values).filter(([k,v]) => !fields[k].computed && v !== '' && v != null).map(([k,v]) => [k,fields[k].type==='datetime' ? localToUtc(v) : v]))
}
export function labelFor(row) {
  if (row.label) return row.label
  const values = row.values ?? {}
  return ['nombre','nombre_completo','nombre_comercial','nombres','apellidos','codigo_cama','numero','numero_factura'].filter(k=>values[k]).map(k=>values[k]).join(' · ') || row.id
}

export function financialActionsFor(resource,record) {
  const state=String(record.values.estado??'').toLowerCase()
  return (resource.actions??[]).filter(action=>action==='emitir'?state==='borrador':action==='anular'?['borrador','pendiente','parcial','pagada'].includes(state):action==='revertir'&&state==='procesado')
}

export function canEditRecord(resource,record) {
  return resource.edit && (!resource.state_transitions || (resource.state_transitions[record.values.estado]?.length??0)>0)
}

export function operationEditorFields(resource,record) {
  return Object.fromEntries(Object.entries(resource.fields).map(([key,field])=>{
    const transitionOnly=record&&resource.transition_only_states?.includes(record.values.estado)
    const computed=field.computed||!!(record&&resource.editable_fields&&!resource.editable_fields.includes(key))||!!(transitionOnly&&key!=='estado')
    let choices=field.choices
    if(key==='estado') {
      if(record&&resource.state_transitions)choices=[record.values.estado,...(resource.state_transitions[record.values.estado]??[])]
      else if(!record&&resource.initial_states)choices=resource.initial_states
    }
    return [key,{...field,computed,choices}]
  }))
}
