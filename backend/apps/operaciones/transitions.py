"""Explicit operational state machines; terminal clinical records are immutable."""
from datetime import datetime, timezone
from decimal import Decimal

from apps.historiales.application.validation import hoy_guatemala, invalid
from apps.historiales.domain.errors import Conflicto

EXAM = {'pendiente':['en_proceso','anulado'], 'en_proceso':['finalizado','anulado'],
        'finalizado':[], 'anulado':[]}
DECISION = {'pendiente':['aprobado','rechazado','anulado'], 'aprobado':['anulado'],
            'rechazado':[], 'anulado':[]}
TOGGLE = {'activo':['inactivo'], 'inactivo':['activo']}
TRANSITIONS = {
    ('hospital','cirugia'):{'pendiente':['realizado','cancelado'], 'realizado':[], 'cancelado':[]},
    ('pediatrico','examen'):EXAM,
    ('pediatrico','resultado_examen'):EXAM,
    ('pediatrico','autorizacion_seguro'):DECISION,
    ('pediatrico','reclamacion_seguro'):DECISION,
    ('pediatrico','plan_seguro'):TOGGLE,
    ('pediatrico','cobertura_servicio'):TOGGLE,
    ('laboratorio','resultado'):EXAM,
    ('odontologica','procedimiento'):{'pendiente':['realizado','anulado'], 'realizado':[], 'anulado':[]},
}
INITIAL_STATES = {
    ('hospital','cirugia'):['pendiente'], ('pediatrico','examen'):['pendiente'],
    ('pediatrico','autorizacion_seguro'):['pendiente'],
    ('pediatrico','reclamacion_seguro'):['pendiente'],
    ('pediatrico','resultado_examen'):['pendiente','en_proceso','finalizado'],
}


def validate_transition(institution,name,row,old):
    machine=TRANSITIONS.get((institution,name))
    if machine is None:return
    state=row.get('estado')
    if state not in machine:invalid('estado','Estado no permitido para esta tarea')
    if old is None:
        if state not in INITIAL_STATES.get((institution,name),list(machine)):
            invalid('estado','El registro debe comenzar en un estado inicial permitido')
    else:
        previous=old.get('estado')
        if previous not in machine or not machine[previous]:raise Conflicto()
        if state!=previous and state not in machine[previous]:raise Conflicto()
        if previous=='aprobado' and state==previous:raise Conflicto()
    if name in {'autorizacion_seguro','reclamacion_seguro'}:
        datefield='fecha_respuesta' if name=='autorizacion_seguro' else 'fecha_resolucion'
        amount='monto_autorizado' if name=='autorizacion_seguro' else 'monto_aprobado'
        if state=='pendiente':
            if row.get(datefield):invalid(datefield,'Una tarea pendiente no tiene resolución')
            if name=='reclamacion_seguro' and Decimal(str(row.get(amount) or 0))!=0:
                invalid(amount,'La aprobación se registra al resolver la reclamación')
        else:
            if not row.get(datefield):row[datefield]=hoy_guatemala().isoformat()
            if state=='aprobado' and Decimal(str(row.get(amount) or 0))<=0:
                invalid(amount,'La aprobación requiere un importe mayor que cero')
            if row[datefield]>hoy_guatemala().isoformat():invalid(datefield,'La resolución no puede ser futura')
    if name=='cirugia' and state=='realizado':
        end=row.get('fecha_hora_fin')
        if not end or datetime.fromisoformat(end.replace('Z','+00:00'))>datetime.now(timezone.utc):
            invalid('fecha_hora_fin','La cirugía realizada requiere una fecha final transcurrida')
