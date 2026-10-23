"""Native operational repository. No SQL identifiers ever come from request data.

Patient root locks serialize operational writes with clinical archive. Catalog
locks validate every FK before writes; Firestore reads precede all mutations.
"""
import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from decimal import Decimal

from apps.historiales.application.validation import invalid, normalizar_busqueda
from apps.historiales.domain.errors import AccesoDenegado, Conflicto, RecursoNoEncontrado
from apps.historiales.infrastructure.factory import AdapterFactory
from .catalog import RESOURCES, resource, validate, validate_chronology
from .transitions import validate_transition

KINDS = {'paciente':'P','consulta':'C','diagnostico':'D','diagnostico_ingreso':'D','tratamiento':'T','medicamento':'M','cita':'CITA','ingreso_hospitalario':'I','cama':'CAMA','vacuna':'V','tutor':'TUTOR','receta_prescripcion':'R','detalle_receta':'R'}
# Explicit parent routes avoid ambiguous join inference (e.g. insurer vs patient).
PARENTS = {'ingreso_hospitalario':'id_paciente','movimiento_cama':'id_ingreso','emergencia':'id_ingreso','signos_vitales':'id_ingreso','cirugia':'id_ingreso','equipo_quirurgico':'id_cirugia','consulta':'id_paciente','diagnostico':'id_consulta','tratamiento':'id_diagnostico','receta_prescripcion':'id_tratamiento','despacho_farmacia':'id_receta','aplicacion_enfermeria':'id_despacho','factura':'id_paciente','detalle_factura':'id_factura','pago':'id_factura'}
PED_PARENTS={'paciente_tutor':'paciente_id','cita':'paciente_id','consulta':'paciente_id','consulta_diagnostico':'consulta_id','tratamiento':'consulta_diagnostico_id','receta':'consulta_id','detalle_receta':'receta_id','examen':'consulta_id','resultado_examen':'examen_id','aplicacion_vacuna':'paciente_id','control_de_crecimiento':'paciente_id','antecedente_medico':'paciente_id','signos_vitales':'consulta_id','poliza_paciente':'paciente_id','autorizacion_seguro':'poliza_paciente_id','factura':'paciente_id','detalle_factura':'factura_id','pago':'factura_id','reclamacion_seguro':'factura_id'}


def serialize(value):
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, (datetime,date,time)):
        if isinstance(value,datetime) and value.tzinfo is None: value=value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace('+00:00','Z')
    if hasattr(value, 'total_seconds'): return str(value)
    return value


def token(row):
    return hashlib.sha256(json.dumps(row,sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()


class OperationsRepository:
    def __init__(self, context):
        self.context=context
        self.specs=RESOURCES[context.institucion]
        self.sql=context.institucion in {'hospital','pediatrico'}
        self.hospital=context.institucion=='hospital'
        self.core=AdapterFactory.create_clinical(context)

    def public_id(self,name,number):
        if not self.sql: return str(number)
        if isinstance(number,tuple): return 'OP-'+name+'-'+'~'.join(map(str,number))
        return ('H' if self.hospital else 'PED')+'-'+KINDS.get(name,'OP_'+name)+'-'+str(number)

    def internal(self,name,value):
        if not self.sql:
            if not isinstance(value,str) or not value or '/' in value or len(value)>1500: raise RecursoNoEncontrado()
            return value
        if isinstance(self.specs[name]['pk'],list):
            match=re.fullmatch(r'OP-'+re.escape(name)+r'-([1-9]\d{0,9})~([1-9]\d{0,9})',value or '')
            if not match: raise RecursoNoEncontrado()
            return tuple(map(int,match.groups()))
        prefix=('H' if self.hospital else 'PED')+'-'+KINDS.get(name,'OP_'+name)+'-'
        match=re.fullmatch(re.escape(prefix)+r'([1-9]\d{0,9})',value or '')
        if not match or int(match[1])>2147483647: raise RecursoNoEncontrado()
        return int(match[1])

    def dto(self,name,row):
        spec=self.specs[name]
        pk=spec['pk']
        number=tuple(row[k] for k in pk) if isinstance(pk,list) else row[pk]
        values={}
        for key,field in spec['fields'].items():
            value=row.get(key)
            if value is not None and field['type']=='reference': value=self.public_id(field['resource'],value)
            values[key]=bool(value) if field['type']=='boolean' and value is not None else serialize(value)
        return {'id':self.public_id(name,number),'values':values,'version':token(row)}

    def _get(self,u,name,identifier,*,lock=False):
        spec=self.specs[name]
        if not self.sql:
            row=u.get(spec['table'],identifier)
        else:
            pk=spec['pk'];keys=pk if isinstance(pk,list) else [pk]
            args=identifier if isinstance(identifier,tuple) else (identifier,)
            where=' AND '.join(k+'=%s' for k in keys)
            u.execute('SELECT * FROM '+spec['table']+' WHERE '+where+(' FOR UPDATE' if lock else ''),args)
            row=u.fetchone()
        if row is None: raise RecursoNoEncontrado()
        return row

    def _owner(self,u,name,row,*,depth=0):
        if depth>10: raise Conflicto()
        if name=='paciente': return row
        if not self.sql:
            if row.get('paciente_id'): return self._get(u,'paciente',row['paciente_id'])
            return None
        parents=PARENTS if self.hospital else PED_PARENTS
        field=parents.get(name)
        if name=='diagnostico_ingreso' or name=='diagnostico' and self.hospital and not row.get('id_consulta'): field='id_ingreso'
        if name=='cita' and self.hospital: field='id_paciente'
        if not field or not row.get(field): return None
        ref=self.specs[name]['fields'][field]['resource']
        return self._owner(u,ref,self._get(u,ref,row[field]),depth=depth+1)

    def _run(self,callback,*,read=False):
        if not self.sql: return self.core._transaction(callback,read=read)
        with self.core._session(read=read) as cursor: return callback(cursor)

    def page(self,name,*,q='',offset=0,limit=20,patient=None,lookup=False):
        spec=self.specs.get(name) if lookup else resource(self.context,name)
        if spec is None: raise RecursoNoEncontrado()
        patient_number=self.internal('paciente',patient) if patient else None
        def read(u):
            if self.sql:
                # Use paged SQL; patient filters follow the explicitly declared parent chain.
                conditions=[];args=[]
                if patient_number is not None:
                    expr=self._patient_expression(name,'r')
                    if expr: conditions.append(expr+'=%s');args.append(patient_number)
                    elif name=='paciente': conditions.append('r.'+spec['pk']+'=%s');args.append(patient_number)
                searchable=[k for k,f in spec['fields'].items() if f['type']=='text']
                if q and searchable:
                    conditions.append('('+' OR '.join('LOWER(r.'+k+') LIKE %s' for k in searchable)+')')
                    args.extend(['%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%']*len(searchable))
                where=' WHERE '+' AND '.join(conditions) if conditions else ''
                u.execute('SELECT COUNT(*) AS n FROM '+spec['table']+' r'+where,args); count=u.fetchone()['n']
                pk=spec['pk'];order=','.join('r.'+k for k in (pk if isinstance(pk,list) else [pk]))
                u.execute('SELECT r.* FROM '+spec['table']+' r'+where+' ORDER BY '+order+' LIMIT %s OFFSET %s',(*args,limit,offset));rows=u.fetchall()
            else:
                rows=u.rows(spec['table'])
                if patient_number and name=='paciente': rows=[r for r in rows if r['id']==patient_number]
                elif patient_number and any(f.get('resource')=='paciente' for f in spec['fields'].values()): rows=[r for r in rows if r.get('paciente_id')==patient_number]
                rows=[r for r in rows if not q or any(normalizar_busqueda(str(r.get(k,''))).find(q)>=0 for k in spec['fields'])]
                rows.sort(key=lambda r:r['id']);count=len(rows);rows=rows[offset:offset+limit]
            dtos=[]
            for row in rows:
                dto=self.lookup_dto(name,row) if lookup else self.dto(name,row)
                if name=='factura' and self.sql:
                    summary=self._financial_summary(u,row)
                    if lookup: dto['defaults']={'monto':summary['saldo_paciente']}
                    else: dto['financial']=summary
                if not lookup:
                    dto['display']={}
                    for key,f in spec['fields'].items():
                        if f['type']=='reference' and row.get(key) is not None:
                            ref=self._get(u,f['resource'],row[key])
                            dto['display'][key]=self.lookup_dto(f['resource'],ref)['label']
                dtos.append(dto)
            return {'count':count,'limit':limit,'offset':offset,'results':dtos}
        return self._run(read,read=True)

    def lookup_dto(self,name,row):
        dto=self.dto(name,row)
        names=[str(row[k]) for k in ['nombre','nombre_completo','nombres','apellidos','nombre_comercial','codigo_cama','numero_habitacion','nombre_pabellon','nombre_sala','numero_factura','numero','numero_poliza','fecha','fecha_hora'] if row.get(k) is not None]
        if self.context.rol in {'admin','medico','enfermero','laboratorista'} and not names:
            names=[str(row[k])[:100] for k in ['descripcion','indicaciones_generales'] if row.get(k)]
        # Only identification labels, never notes, diagnosis or insurance details.
        result={'id':dto['id'],'label':' · '.join(names[:3]) or self.specs[name]['label']+' '+dto['id']}
        if name=='servicio_medico' and row.get('precio_base') is not None:result['defaults']={'precio_unitario':str(row['precio_base'])}
        return result

    def _patient_expression(self,name,alias,depth=0):
        if depth>10: return None
        if name=='paciente': return alias+'.'+self.specs[name]['pk']
        if name=='diagnostico' and self.hospital:
            return 'COALESCE((SELECT id_paciente FROM consulta dco WHERE dco.id_consulta='+alias+'.id_consulta),(SELECT id_paciente FROM ingreso_hospitalario din WHERE din.id_ingreso='+alias+'.id_ingreso))'
        field=(PARENTS if self.hospital else PED_PARENTS).get(name)
        if name=='diagnostico_ingreso':field='id_ingreso'
        if name=='cita' and self.hospital: field='id_paciente'
        if not field: return None
        target=self.specs[name]['fields'][field]['resource']; target_spec=self.specs[target]
        nested='p'+str(depth)
        expression=self._patient_expression(target,nested,depth+1)
        if not expression:return None
        return '(SELECT '+expression+' FROM '+target_spec['table']+' '+nested+' WHERE '+nested+'.'+target_spec['pk']+'='+alias+'.'+field+')'

    def save(self,name,data,*,identifier=None,version=None):
        spec=resource(self.context,name,write=True,edit=identifier is not None)
        if identifier and spec.get('editable_fields') and (not isinstance(data,dict) or set(data)-set(spec['editable_fields'])):invalid('body','Solo se permite actualizar los campos de seguimiento')
        data=validate(spec,data,partial=identifier is not None)
        if self.hospital and name=='receta_prescripcion' and identifier is None:
            # Use the clinical port for both inpatient and outpatient prescriptions.
            # This preserves role/professional, root lock and medicine validation.
            prescription=self.core.registrar_receta(data['id_tratamiento'],{
                'medicamento_id':data['id_medicamento'],'dosis':data['dosis'],
                'frecuencia':data['frecuencia'],
                **({'via_administracion':data['via_administracion']} if data.get('via_administracion') else {}),
            })
            row={'id_receta':self.internal(name,prescription['id']),
                 'id_tratamiento':self.internal('tratamiento',prescription['tratamiento_id']),
                 'id_medicamento':self.internal('medicamento',prescription['medicamento_id']),
                 'dosis':prescription['dosis'],'frecuencia':prescription['frecuencia'],
                 'via_administracion':prescription['via_administracion']}
            return self.dto(name,row)
        number=self.internal(name,identifier) if identifier else None
        # Convert all references using the referenced resource's exact identifier format.
        for key,field in spec['fields'].items():
            if field['type']=='reference' and data.get(key) is not None: data[key]=self.internal(field['resource'],data[key])
        def apply(u):
            old=self._get(u,name,number,lock=self.sql) if identifier else None
            if old is not None and (not version or token(old)!=version): raise Conflicto()
            if old and name in {'autorizacion_seguro','reclamacion_seguro'} and old.get('estado')=='aprobado' and set(data)!={'estado'}:
                invalid('body','Una aprobación solo permite su anulación; sus importes y datos se conservan')
            merged={k:serialize(v) for k,v in (old or {}).items()} | data
            validate_chronology(spec, merged)
            owners=[]
            # Read all parents before writes; catalog references are locked against concurrent edits.
            references={}
            for key,field in spec['fields'].items():
                if field['type']=='reference' and merged.get(key) is not None:
                    ref=self._get(u,field['resource'],merged[key],lock=self.sql)
                    references[key]=ref
                    owner=self._owner(u,field['resource'],ref)
                    if owner: owners.append(owner)
            owner=self._owner(u,name,merged)
            if owner: owners.append(owner)
            patient_pk=self.specs['paciente']['pk']
            ids={r[patient_pk] for r in owners}
            if len(ids)>1: invalid('body','Las referencias deben pertenecer al mismo paciente')
            patient=None
            if ids:
                patient=self._get(u,'paciente',next(iter(ids)),lock=self.sql)
                if spec['group'] not in {'Caja y seguros'} and patient.get('estado')!='activo': raise Conflicto()
            for key,ref in references.items():
                cancelling=old is not None and merged.get('estado') in {'anulado','cancelado','rechazado','inactivo'}
                if not cancelling and (any(ref.get(k) is False or ref.get(k)==0 for k in ['activo','activo_operativo','habilitado']) or ref.get('estado')=='inactivo'):
                    invalid(key,'La opción seleccionada está desactivada')
            claim=None
            if spec['catalog'] or name=='pago' and not self.sql:
                unique='referencia' if name=='pago' else next((k for k in ['colegiado','licencia_enfermeria','codigo_cama','numero_habitacion','codigo','dpi','nombre','nombre_comercial','nombre_pabellon','nombre_sala'] if merged.get(k)),None)
                if unique:
                    normalized=normalizar_busqueda(str(merged[unique]))
                    if self.sql:
                        if self.hospital:u.execute('LOCK TABLE '+spec['table']+' IN SHARE ROW EXCLUSIVE MODE')
                        else:
                            u.execute('SELECT GET_LOCK(%s,5) AS acquired',('ops-'+name,))
                            if u.fetchone()['acquired']!=1:raise Conflicto()
                        u.execute('SELECT * FROM '+spec['table'])
                        if any(normalizar_busqueda(str(r.get(unique) or ''))==normalized and (old is None or r[spec['pk']]!=old[spec['pk']]) for r in u.fetchall()):raise Conflicto()
                    else:
                        if any(normalizar_busqueda(str(r.get(unique) or ''))==normalized and r['id']!=number for r in u.rows(spec['table'])):raise Conflicto()
                        claim=hashlib.sha256((name+':'+normalized).encode()).hexdigest()
                        claim_row=u.get('operaciones_unicidad',claim)
                        if claim_row and claim_row['registro_id']!=number:raise Conflicto()
                        if claim_row:claim=None
            self._rules(u,name,merged,references,old)
            validate_chronology(spec,merged)
            if self.sql:
                values={k:self._sql_value(spec['fields'][k],v) for k,v in merged.items() if k in spec['fields']}
                if old:
                    keys=[spec['pk']] if isinstance(spec['pk'],str) else spec['pk']
                    args=[values[k] for k in values]+[old[k] for k in keys]
                    u.execute('UPDATE '+spec['table']+' SET '+','.join(k+'=%s' for k in values)+' WHERE '+' AND '.join(k+'=%s' for k in keys),args)
                    result=self._get(u,name,number)
                else:
                    columns=list(values)
                    sql='INSERT INTO '+spec['table']+' ('+','.join(columns)+') VALUES ('+','.join(['%s']*len(columns))+')'
                    if self.hospital and isinstance(spec['pk'],str): sql+=' RETURNING '+spec['pk']
                    u.execute(sql,[values[k] for k in columns])
                    if isinstance(spec['pk'],list): number_new=tuple(values[k] for k in spec['pk'])
                    else: number_new=u.fetchone()[spec['pk']] if self.hospital else u.lastrowid
                    result=self._get(u,name,number_new)
                self._after_sql(u,name,result,references)
            else:
                new_id=number or self.core._id()
                stored=self.core._stored(**{k:v for k,v in merged.items() if k in spec['fields']})
                if name=='cita':
                    pro=references['profesional_id'];u.update('profesionales_operativos',pro['id'],{'version':pro.get('version',0)+1})
                if claim:u.create('operaciones_unicidad',claim,self.core._stored(registro_id=new_id))
                if patient:u.touch(patient)
                if old:u.update(spec['table'],new_id,stored)
                else:u.create(spec['table'],new_id,stored)
                result=dict(old or {},**stored,id=new_id)
            self.core._after_write(u)
            return self.dto(name,result)
        return self._run(apply)

    @staticmethod
    def _sql_value(field,value):
        if value is not None and field['type']=='datetime':
            parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
            return parsed if field.get('timezone') else parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def _rules(self,u,name,row,refs,old):
        validate_transition(self.context.institucion,name,row,old)
        # Sane, explicit initial states. No arbitrary status edits of clinical records.
        if name=='cita':
            if old and old.get('estado')=='atendida':raise Conflicto()
            if row.get('estado') not in {'programada','cancelada'}: invalid('estado','Use programada o cancelada')
            if self.sql:
                doctor='id_medico' if self.hospital else 'medico_id'
                datefield='fecha_hora' if self.hospital else 'fecha'
                condition=doctor+'=%s AND '+datefield+'=%s'
                args=[row[doctor],self._sql_value(self.specs[name]['fields'][datefield],row[datefield])]
                if not self.hospital:condition+=' AND hora=%s';args.append(row.get('hora'))
                # Doctor row already locked, serializing appointments for this professional.
                u.execute('SELECT '+self.specs[name]['pk']+' FROM cita WHERE '+condition+" AND estado='programada'",args)
                existing=u.fetchall()
                if any(r[self.specs[name]['pk']] != (old or {}).get(self.specs[name]['pk']) for r in existing) and row['estado']=='programada':raise Conflicto()
            else:
                candidates=u.rows('citas')
                if any(r.get('profesional_id')==row['profesional_id'] and serialize(r.get('fecha_hora'))==row['fecha_hora'] and r.get('estado')=='programada' and r['id']!=(old or {}).get('id') for r in candidates):raise Conflicto()
        for key in ['cantidad','cantidad_entregada','monto','precio_unitario','monto_centavos']:
            if row.get(key) is not None and Decimal(str(row[key]))<=0:invalid(key,'Debe ser mayor que cero')
        if name=='pago' and not self.sql and row['moneda']!='GTQ':invalid('moneda','Moneda admitida: GTQ')
        if name=='detalle_factura':
            if row.get('precio_unitario') is None:
                base=refs.get('servicio_id',{}).get('precio_base')
                if base is None:invalid('precio_unitario','Indica el precio del concepto')
                row['precio_unitario']=str(base)
            quantity=Decimal(str(row.get('cantidad') or 1));price=Decimal(str(row['precio_unitario']));discount=Decimal(str(row.get('descuento') or 0))
            subtotal=quantity*price-discount
            covered=Decimal(str(row.get('monto_cubierto') or 0))
            if subtotal<0 or covered>subtotal:invalid('descuento','El descuento o cobertura excede el importe')
            row['subtotal']=str(subtotal.quantize(Decimal('.01')))
            if not self.hospital:row['monto_paciente']=str(subtotal-covered)
            parent=refs['id_factura' if self.hospital else 'factura_id']
            if str(parent.get('estado')).lower()!='borrador':raise Conflicto()
        if name=='factura':
            if self.hospital:
                if bool(row.get('id_ingreso'))==bool(row.get('id_consulta')):invalid('id_consulta','Selecciona un ingreso o una consulta')
                row.update(subtotal='0.00',total='0.00',estado='Borrador')
            else:row.update(subtotal='0.00',total='0.00',total_seguro='0.00',total_paciente='0.00',estado='borrador')
        if name=='pago' and self.sql:
            parent=refs['id_factura' if self.hospital else 'factura_id'];pk=self.specs['factura']['pk']
            if str(parent['estado']).lower() not in {'pendiente','parcial','pagada'}:raise Conflicto()
            summary=self._financial_summary(u,parent)
            payer='paciente' if self.hospital else row['tipo_pagador']
            if payer not in {'paciente','aseguradora'}:invalid('tipo_pagador','Pagador inválido')
            if Decimal(str(row['monto']))>Decimal(summary['saldo_'+('seguro' if payer=='aseguradora' else 'paciente')]):invalid('monto','El pago supera el saldo pendiente del pagador')
            if payer=='aseguradora':
                u.execute("SELECT COALESCE(SUM(monto_aprobado),0) AS n FROM reclamacion_seguro WHERE factura_id=%s AND estado='aprobado'",(parent[pk],))
                if Decimal(summary['cobrado_seguro'])+Decimal(str(row['monto']))>Decimal(str(u.fetchone()['n'])):
                    invalid('monto','El cobro supera las reclamaciones aprobadas')
            row['estado']='Procesado' if self.hospital else 'procesado'
        if name=='despacho_farmacia':
            prescription=refs['id_receta'];med=self._get(u,'medicamento',prescription['id_medicamento'],lock=True)
            if med['stock_farmacia']<row['cantidad_entregada']:invalid('cantidad_entregada','Stock insuficiente')
        if name=='movimiento_cama':
            admission=refs['id_ingreso']
            if admission['alta_utc'] is not None:raise Conflicto()
            if self._sql_value(self.specs[name]['fields']['fecha_hora_inicio'],row['fecha_hora_inicio']) < admission['fecha_hora_ingreso']:invalid('fecha_hora_inicio','El traslado no puede preceder al ingreso')
            if admission['id_cama']==row['id_cama']:invalid('id_cama','El paciente ya ocupa esta cama')
            u.execute('SELECT id_ingreso FROM ingreso_hospitalario WHERE id_cama=%s AND alta_utc IS NULL',(row['id_cama'],))
            occupied=u.fetchall()
            if occupied:raise Conflicto()
        if name=='cirugia':
            start=self._sql_value(self.specs[name]['fields']['fecha_hora_inicio'],row['fecha_hora_inicio'])
            end=self._sql_value(self.specs[name]['fields']['fecha_hora_inicio'],row.get('fecha_hora_fin') or row['fecha_hora_inicio'])
            if row.get('fecha_hora_fin') is None:invalid('fecha_hora_fin','Indica la hora final prevista para reservar el quirófano')
            if row['estado']!='cancelado':
                if refs['id_ingreso'].get('alta_utc') is not None:raise Conflicto()
                u.execute("SELECT id_cirugia FROM cirugia WHERE id_quirofano=%s AND estado<>'cancelado' AND fecha_hora_inicio<%s AND fecha_hora_fin>%s",(row['id_quirofano'],end,start))
                occupied=u.fetchall()
                if any(r['id_cirugia']!=(old or {}).get('id_cirugia') for r in occupied):raise Conflicto()
            if row['estado']=='realizado':
                u.execute('SELECT COUNT(*) AS n FROM equipo_quirurgico WHERE id_cirugia=%s',(old['id_cirugia'],))
                if not u.fetchone()['n']:invalid('estado','Registra el equipo quirúrgico antes de completar la cirugía')
        if name=='cirugia' and row.get('fecha_hora_fin') and row['fecha_hora_fin']<row['fecha_hora_inicio']:invalid('fecha_hora_fin','Fin anterior al inicio')
        if name=='aplicacion_enfermeria':
            dispatch=refs['id_despacho']
            u.execute('SELECT id_aplicacion FROM aplicacion_enfermeria WHERE id_despacho=%s',(dispatch['id_despacho'],))
            if u.fetchone():raise Conflicto()  # a dispatch is accounted for once; additional delivery needs another dispatch.
        if name=='resultado_examen':
            if refs['examen_id'].get('estado') in {'finalizado','anulado'}:raise Conflicto()
            if row['estado']=='finalizado':
                from apps.historiales.application.validation import hoy_guatemala
                if not row.get('fecha_resultado') or row['fecha_resultado']>hoy_guatemala().isoformat():
                    invalid('fecha_resultado','El resultado final requiere una fecha transcurrida')
            u.execute("SELECT COUNT(*) AS n FROM resultado_examen WHERE examen_id=%s AND COALESCE(estado,'pendiente')<>'anulado' AND id<>%s",(row['examen_id'],(old or {}).get('id',0)))
            if u.fetchone()['n']:invalid('examen_id','Continúa el resultado existente antes de registrar otro')
        if name=='examen' and row['estado'] in {'finalizado','anulado'}:
            u.execute('SELECT estado FROM resultado_examen WHERE examen_id=%s',(old['id'],))
            states=[r['estado'] for r in u.fetchall()]
            if row['estado']=='finalizado' and 'finalizado' not in states:invalid('estado','Finaliza el resultado antes de cerrar el examen')
            if row['estado']=='anulado' and any(s!='anulado' for s in states):invalid('estado','Anula los resultados pendientes antes de cancelar el examen')
        if name=='equipo_quirurgico' and refs['id_cirugia'].get('estado')!='pendiente':raise Conflicto()
        if name=='autorizacion_seguro' and old and old.get('estado')=='aprobado' and row['estado']=='anulado':
            u.execute("SELECT COUNT(*) AS n FROM reclamacion_seguro WHERE autorizacion_id=%s AND COALESCE(estado,'pendiente') NOT IN ('anulado','rechazado')",(old['id'],))
            if u.fetchone()['n']:invalid('estado','Anula las reclamaciones activas antes de revocar la autorización')
        if name=='resultado' and row['estado']=='finalizado':
            from apps.historiales.application.specialties import validate_specialty
            validate_specialty('result',{key:row.get(key) for key in ['tipo_examen','fecha','estado','campos']})
        if name=='procedimiento' and row['estado']=='anulado':
            if any(p.get('procedimiento_id')==row['id'] and p.get('estado')!='anulado' for p in u.rows('pagos')):
                invalid('estado','El procedimiento tiene pagos vigentes')
        if name=='procedimiento' and row['estado']=='realizado':
            from apps.historiales.application.specialties import validate_specialty
            validate_specialty('procedure',{key:row.get(key) for key in ['tratamiento_id','pieza','descripcion','estado']})
        if name=='pago' and not self.sql and refs.get('procedimiento_id',{}).get('estado') not in {None,'realizado'}:
            invalid('procedimiento_id','El procedimiento debe estar realizado para registrar su pago')
        if name=='autorizacion_seguro':
            policy=refs['poliza_paciente_id']
            if row['estado'] not in {'anulado','rechazado'} and policy.get('estado')!='activo':invalid('poliza_paciente_id','La póliza no está activa')
            if row.get('monto_autorizado') is not None and Decimal(str(row['monto_autorizado']))<0:invalid('monto_autorizado','Importe inválido')
        if name=='reclamacion_seguro':
            if row.get('monto_aprobado') is not None and Decimal(str(row['monto_aprobado']))>Decimal(str(row.get('monto_reclamado') or 0)):invalid('monto_aprobado','El importe aprobado supera lo reclamado')
            bill=refs['factura_id']
            if str(bill.get('estado')).lower() not in {'pendiente','parcial','pagada'}:raise Conflicto()
            amount=Decimal(str(row.get('monto_reclamado') or 0))
            if amount<=0 or amount>Decimal(str(bill.get('total_seguro') or 0)):invalid('monto_reclamado','El reclamo debe corresponder al importe del seguro')
            authorization=refs.get('autorizacion_id')
            if authorization and (authorization.get('poliza_paciente_id')!=row['poliza_paciente_id'] or authorization.get('estado')!='aprobado'):invalid('autorizacion_id','La autorización debe estar aprobada y corresponder a la póliza')
            if authorization and authorization.get('consulta_id')!=bill.get('consulta_id'):
                invalid('autorizacion_id','La autorización y la factura deben corresponder a la misma consulta')
            if authorization and amount>Decimal(str(authorization.get('monto_autorizado') or 0)):invalid('monto_reclamado','El reclamo supera la autorización')
            if old:
                u.execute("SELECT COALESCE(SUM(monto_aprobado),0) AS n FROM reclamacion_seguro WHERE factura_id=%s AND estado='aprobado' AND id<>%s",(bill['id'],old['id']))
                approved=Decimal(str(u.fetchone()['n']))+(Decimal(str(row.get('monto_aprobado') or 0)) if row.get('estado')=='aprobado' else Decimal('0'))
                if approved<Decimal(self._financial_summary(u,bill)['cobrado_seguro']):
                    invalid('monto_aprobado','Revierte los cobros del seguro antes de reducir su aprobación')
            # Both invoice and authorization have already been locked by save().
            # Rejected/void claims release their reservation; edits exclude themselves.
            if row.get('estado') not in {'anulado','rechazado'}:
                exclude=(old or {}).get('id',0)
                active="COALESCE(estado,'pendiente') NOT IN ('anulado','rechazado') AND id<>%s"
                u.execute('SELECT COALESCE(SUM(monto_reclamado),0) AS n FROM reclamacion_seguro WHERE factura_id=%s AND '+active,(bill['id'],exclude))
                if Decimal(str(u.fetchone()['n']))+amount>Decimal(str(bill.get('total_seguro') or 0)):
                    invalid('monto_reclamado','El reclamo supera el saldo reclamable de la factura')
                if authorization:
                    u.execute('SELECT COALESCE(SUM(monto_reclamado),0) AS n FROM reclamacion_seguro WHERE autorizacion_id=%s AND '+active,(authorization['id'],exclude))
                    if Decimal(str(u.fetchone()['n']))+amount>Decimal(str(authorization.get('monto_autorizado') or 0)):
                        invalid('monto_reclamado','El reclamo supera el saldo disponible de la autorización')
        if name=='pago' and self.sql:
            ref_key='referencia_pago' if self.hospital else 'referencia'
            if row.get(ref_key):
                u.execute('SELECT 1 AS n FROM pago WHERE '+ref_key+'=%s',(row[ref_key],))
                if u.fetchone():raise Conflicto()
        if self.sql and name=='paciente_tutor':
            u.execute('SELECT id FROM paciente_tutor WHERE paciente_id=%s AND tutor_id=%s',(row['paciente_id'],row['tutor_id']))
            if u.fetchone():raise Conflicto()

    def _after_sql(self,u,name,row,refs):
        if name=='resultado_examen':u.execute('UPDATE examen SET estado=%s WHERE id=%s',('finalizado' if row['estado']=='finalizado' else 'en_proceso',row['examen_id']))
        if name=='despacho_farmacia':u.execute('UPDATE medicamento SET stock_farmacia=stock_farmacia-%s WHERE id_medicamento=%s',(row['cantidad_entregada'],refs['id_receta']['id_medicamento']))
        if name=='movimiento_cama':
            admission=refs['id_ingreso']
            u.execute('SELECT COUNT(*) AS n FROM movimiento_cama WHERE id_ingreso=%s AND id_movimiento<>%s',(row['id_ingreso'],row['id_movimiento']))
            if u.fetchone()['n']==0:
                u.execute('INSERT INTO movimiento_cama(id_ingreso,id_cama,fecha_hora_inicio,fecha_hora_fin,motivo_traslado) VALUES(%s,%s,%s,%s,%s)',(row['id_ingreso'],admission['id_cama'],admission['fecha_hora_ingreso'],row['fecha_hora_inicio'],'Ingreso inicial'))
            u.execute('UPDATE movimiento_cama SET fecha_hora_fin=%s WHERE id_ingreso=%s AND fecha_hora_fin IS NULL AND id_movimiento<>%s',(row['fecha_hora_inicio'],row['id_ingreso'],row['id_movimiento']))
            u.execute('UPDATE ingreso_hospitalario SET id_cama=%s WHERE id_ingreso=%s',(row['id_cama'],row['id_ingreso']))
        if name=='detalle_factura':
            fk='id_factura' if self.hospital else 'factura_id';pk=self.specs['factura']['pk'];number=row[fk]
            u.execute('SELECT COALESCE(SUM(subtotal),0) AS n'+('' if self.hospital else ',COALESCE(SUM(monto_cubierto),0) AS covered')+' FROM detalle_factura WHERE '+fk+'=%s',(number,));sums=u.fetchone()
            parent=refs[fk];subtotal=Decimal(str(sums['n']));tax=Decimal(str(parent.get('impuestos') or 0));discount=Decimal(str(parent.get('descuento') or 0));total=subtotal+tax-discount
            if total<0:invalid('descuento','El descuento excede la factura')
            if self.hospital:u.execute('UPDATE factura SET subtotal=%s,total=%s WHERE '+pk+'=%s',(subtotal,total,number))
            else:
                covered=Decimal(str(sums['covered']))
                if covered>total:invalid('monto_cubierto','Cobertura excede total')
                u.execute('UPDATE factura SET subtotal=%s,total=%s,total_seguro=%s,total_paciente=%s WHERE '+pk+'=%s',(subtotal,total,covered,total-covered,number))
        if name=='pago':
            self._refresh_invoice(u,refs['id_factura' if self.hospital else 'factura_id'])

    def _financial_summary(self,u,bill):
        fk='id_factura' if self.hospital else 'factura_id'
        number=bill[self.specs['factura']['pk']]
        u.execute("SELECT COALESCE(SUM(monto),0) AS n FROM pago WHERE "+fk+"=%s AND LOWER(estado)='procesado'"+
                  ('' if self.hospital else " AND tipo_pagador='paciente'"),(number,))
        patient_paid=Decimal(str(u.fetchone()['n']))
        insurance_paid=Decimal('0')
        if not self.hospital:
            u.execute("SELECT COALESCE(SUM(monto),0) AS n FROM pago WHERE factura_id=%s AND LOWER(estado)='procesado' AND tipo_pagador='aseguradora'",(number,))
            insurance_paid=Decimal(str(u.fetchone()['n']))
        patient_total=Decimal(str(bill.get('total' if self.hospital else 'total_paciente') or 0))
        insurance_total=Decimal(str(bill.get('total_seguro') or 0)) if not self.hospital else Decimal('0')
        annulled=str(bill.get('estado')).lower()=='anulada'
        return {key:format(value,'.2f') for key,value in {
            'cobrado_paciente':patient_paid,'cobrado_seguro':insurance_paid,
            'saldo_paciente':Decimal('0') if annulled else patient_total-patient_paid,
            'saldo_seguro':Decimal('0') if annulled else insurance_total-insurance_paid}.items()}

    def _refresh_invoice(self,u,bill):
        summary=self._financial_summary(u,bill)
        paid=Decimal(summary['cobrado_paciente'])+Decimal(summary['cobrado_seguro'])
        remaining=Decimal(summary['saldo_paciente'])+Decimal(summary['saldo_seguro'])
        state='pagada' if remaining==0 else 'parcial' if paid>0 else 'pendiente'
        u.execute('UPDATE factura SET estado=%s WHERE '+self.specs['factura']['pk']+'=%s',
                  (state.capitalize() if self.hospital else state,bill[self.specs['factura']['pk']]))

    def financial_action(self,name,identifier,action,version):
        resource(self.context,name,write=True)
        if not self.sql or name not in {'factura','pago'} or not isinstance(action,str) or action not in ({'emitir','anular'} if name=='factura' else {'revertir'}):
            invalid('accion','Acción no disponible')
        number=self.internal(name,identifier)
        fk='id_factura' if self.hospital else 'factura_id'
        # The payment's invoice is immutable. Read its identifier in a separate
        # transaction so MySQL's write transaction establishes no stale snapshot
        # before acquiring the invoice lock and reading the current balances.
        invoice_number=self._run(lambda u:self._get(u,name,number)[fk],read=True) if name=='pago' else number
        def apply(u):
            # Always lock invoice before payment, matching payment creation.
            bill=self._get(u,'factura',invoice_number,lock=True)
            if name=='pago':
                current=self._get(u,name,number,lock=True)
            else:
                current=bill
            if not isinstance(version,str) or token(current)!=version:raise Conflicto()
            state=str(current.get('estado')).lower()
            if action=='emitir':
                if state!='borrador':raise Conflicto()
                u.execute('SELECT COUNT(*) AS n FROM detalle_factura WHERE '+fk+'=%s',(number,))
                if not u.fetchone()['n'] or Decimal(str(bill.get('total') or 0))<=0:
                    invalid('total','Agrega conceptos con un total mayor que cero antes de emitir')
                u.execute('UPDATE factura SET estado=%s,fecha_emision=%s WHERE '+self.specs[name]['pk']+'=%s',
                          ('Pendiente' if self.hospital else 'pendiente',datetime.now(timezone.utc).replace(tzinfo=None),number))
            elif action=='anular':
                if state not in {'borrador','pendiente','parcial','pagada'}:raise Conflicto()
                u.execute("SELECT COUNT(*) AS n FROM pago WHERE "+fk+"=%s AND LOWER(COALESCE(estado,''))<>'anulado'",(number,))
                if u.fetchone()['n']:invalid('estado','Revierte los pagos antes de anular la factura')
                if not self.hospital:
                    u.execute("SELECT COUNT(*) AS n FROM reclamacion_seguro WHERE factura_id=%s AND COALESCE(estado,'pendiente') NOT IN ('anulado','rechazado')",(number,))
                    if u.fetchone()['n']:invalid('estado','Anula las reclamaciones activas antes de anular la factura')
                u.execute('UPDATE factura SET estado=%s WHERE '+self.specs[name]['pk']+'=%s',('Anulada' if self.hospital else 'anulada',number))
            else:
                if state!='procesado' or str(bill.get('estado')).lower() not in {'pendiente','parcial','pagada'}:raise Conflicto()
                u.execute('UPDATE pago SET estado=%s WHERE '+self.specs[name]['pk']+'=%s',('Anulado' if self.hospital else 'anulado',number))
                self._refresh_invoice(u,bill)
            self.core._after_write(u)
            return self.dto(name,self._get(u,name,number))
        return self._run(apply)
