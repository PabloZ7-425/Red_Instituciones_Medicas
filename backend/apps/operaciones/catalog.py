"""Versioned operation definitions. Only this trusted allowlist supplies SQL identifiers."""
import json
import re
from copy import deepcopy
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4
from datetime import timedelta

from apps.historiales.application.validation import invalid
from apps.historiales.domain.errors import AccesoDenegado, RecursoNoEncontrado
from apps.historiales.domain.context import autorizar
from .transitions import TRANSITIONS, INITIAL_STATES

RESOURCES = json.loads(Path(__file__).with_name('resources.json').read_text(encoding='utf-8'))


def resource(context, name, *, write=False, edit=False):
    spec = RESOURCES[context.institucion].get(name)
    if spec is None:
        raise RecursoNoEncontrado()
    roles = spec['write_roles'] if write else spec['read_roles']
    if context.rol not in roles:
        raise AccesoDenegado()
    if write and not spec['edit' if edit else 'create']:
        raise AccesoDenegado()
    if write and spec.get('clinical_operation'):autorizar(context,spec['clinical_operation'])
    return spec


def manifest(context):
    items = []
    for key, spec in RESOURCES[context.institucion].items():
        if context.rol not in spec['read_roles']:
            continue
        can_write=context.rol in spec['write_roles'] and (not spec.get('clinical_operation') or context.profesional_id is not None)
        fields = deepcopy(spec['fields'])
        if context.profesional_id:
            for name,field in fields.items():
                if field.get('resource') in {'medico','profesional'} and name in {'id_medico','medico_id','profesional_id'}:
                    prefix='H-OP_medico-' if context.institucion=='hospital' else 'PED-OP_medico-' if context.institucion=='pediatrico' else ''
                    field['default']=prefix+context.profesional_id
        # Public definitions contain labels, not database/column permissions.
        for field in fields.values():
            if field['type'] == 'reference':
                field['reference_label'] = RESOURCES[context.institucion][field['resource']]['label']
        items.append(dict(key=key, label=spec['label'], fields=fields, group=spec['group'],
                          state_transitions=deepcopy(TRANSITIONS.get((context.institucion,key))),
                          initial_states=INITIAL_STATES.get((context.institucion,key)),
                          transition_only_states=['aprobado'] if key in {'autorizacion_seguro','reclamacion_seguro'} else [],
                          create=spec['create'] and can_write,
                          edit=spec['edit'] and can_write, editable_fields=spec.get('editable_fields'), catalog=spec['catalog'],
                          actions=({'factura':['emitir','anular'],'pago':['revertir']}.get(key,[])
                                   if context.institucion in {'hospital','pediatrico'} and context.rol in spec['write_roles'] else [])))
    return {'version': 'OPERACIONES-01@2.0.0', 'institucion': context.institucion, 'resources': items}


def validate_chronology(spec, values):
    """Check intervals on normalized input or the serialized, combined stored row."""
    for start, end in [('fecha_inicio', 'fecha_fin'),
                       ('fecha_solicitud', 'fecha_respuesta'),
                       ('fecha_envio', 'fecha_resolucion'),
                       ('fecha_hora_inicio', 'fecha_hora_fin')]:
        if start not in spec['fields'] or end not in spec['fields']:
            continue
        if values.get(start) is None or values.get(end) is None:
            continue
        kind = spec['fields'][start]['type']
        def parse(value):
            if kind == 'datetime':
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            return date.fromisoformat(value)
        if parse(values[end]) < parse(values[start]):
            invalid(end, 'La fecha final no puede preceder a la inicial')


def validate(spec, data, *, partial=False):
    if not isinstance(data, dict) or set(data) - spec['fields'].keys():
        invalid('body', 'Campos desconocidos o no permitidos')
    result = {}
    for key, field in spec['fields'].items():
        if field.get('computed'):
            if key in data: invalid(key, 'Este valor se calcula automáticamente')
            continue
        if partial and key not in data: continue
        value = data.get(key)
        if key not in data and not partial and 'default' in field:
            default=field['default']
            now=datetime.now(timezone(timedelta(hours=-6)))
            value=(now.date().isoformat() if field['type']=='date' else now.isoformat()) if default=='now' else 'F-'+uuid4().hex[:12].upper() if default=='code' else default
        if value is None or value == '':
            if field['required']: invalid(key, 'Este campo es obligatorio')
            if key in data: result[key] = None
            continue
        kind = field['type']
        if kind == 'boolean':
            if type(value) is not bool: invalid(key, 'Selecciona Sí o No')
        elif kind in {'decimal', 'integer'}:
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                invalid(key, 'Se requiere un número válido')
            try: number = Decimal(str(value))
            except InvalidOperation: invalid(key, 'Número inválido')
            if not number.is_finite() or number < Decimal(str(field.get('min', 0))) or number > Decimal(str(field.get('max_value', 999999999))):
                invalid(key, 'Número fuera de rango')
            scale = field.get('scale', 2)
            if kind == 'integer':
                if number != number.to_integral_value(): invalid(key, 'Se requiere un entero')
                value = int(number)
            else:
                if number != number.quantize(Decimal(10) ** -scale): invalid(key, f'Máximo {scale} decimales')
                value = format(number, f'.{scale}f')
        elif kind in {'date','datetime','time'}:
            if not isinstance(value, str): invalid(key, 'Fecha u hora inválida')
            try:
                if kind == 'datetime':
                    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    if parsed.tzinfo is None: invalid(key, 'La fecha y hora requiere zona horaria')
                    value = parsed.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
                elif kind == 'date':
                    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value): raise ValueError()
                    value = date.fromisoformat(value).isoformat()
                else: value = time.fromisoformat(value).isoformat()
            except ValueError: invalid(key, 'Fecha u hora inválida')
        else:
            if not isinstance(value, str) or not value.strip(): invalid(key,'Se requiere texto')
            if len(value) > (1500 if kind=='reference' else field['max']): invalid(key,'Texto demasiado largo')
            value = value if kind == 'reference' else value.strip()
        if field.get('choices') and value not in field['choices']:invalid(key,'Selecciona una opción válida')
        result[key] = value
    if not result: invalid('body', 'No hay cambios para guardar')
    validate_chronology(spec, result)
    for key in ['oximetria','saturacion_oxigeno','porcentaje_cobertura','percentil']:
        if result.get(key) is not None and Decimal(str(result[key])) > 100: invalid(key, 'Debe estar entre 0 y 100')
    if result.get('correo') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',result['correo']): invalid('correo','Correo inválido')
    return result
