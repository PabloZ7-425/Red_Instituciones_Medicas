// Match references by resource, never by coincidentally named columns or IDs.
export const nextSteps = { diagnostico_ingreso:'tratamiento', tratamiento:'receta_prescripcion', receta_prescripcion:'despacho_farmacia', especialidad:'medico', pabellon_edificio:'habitacion', habitacion:'cama', aseguradora:'plan_seguro', plan_seguro:'cobertura_servicio', factura:'detalle_factura', detalle_factura:'pago', tipo_examen:'examen', examen:'resultado_examen', cirugia:'equipo_quirurgico', despacho_farmacia:'aplicacion_enfermeria', tutor:'paciente_tutor' }

export function continuation(source, saved, target, previous={}) {
  const references={...previous}
  for(const [key,field] of Object.entries(source.fields)) {
    if(field.type==='reference'&&saved.values[key])references[field.resource]=saved.values[key]
  }
  references[source.key]=saved.id
  const values=Object.fromEntries(Object.entries(target.fields).filter(([,field])=>!field.computed&&field.type==='reference'&&references[field.resource]).map(([key,field])=>[key,references[field.resource]]))
  return {references,values}
}

export function clinicalTask(resource,user) {
  if(resource.key==='paciente')return ['admin','medico','secretaria'].includes(user.rol)||(user.rol==='laboratorista'&&user.institucion==='laboratorio')?'patient':null
  if(!['admin','medico','laboratorista'].includes(user.rol))return null
  const common={consulta:'consultation',diagnostico:'diagnosis',consulta_diagnostico:'diagnosis',tratamiento:'treatment',receta:'prescription',detalle_receta:'prescription',receta_prescripcion:'prescription'}
  const specialty={ingreso_hospitalario:'admission',aplicacion_vacuna:'vaccine',control_de_crecimiento:'growth',resultado:'result',procedimiento:'procedure'}
  if(user.rol==='laboratorista')return resource.key==='resultado'?'result':resource.key==='consulta'?'consultation':null
  return common[resource.key]??specialty[resource.key]??null
}
