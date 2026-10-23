"""Read-only audit probes. Demonstrate gaps in validators without opening databases.

These are observations of the audited revision, not acceptance tests that bless
its current behavior. A fix is expected to change these observations.
Run from repository root with backend dependencies and PYTHONPATH=backend.
"""
import json
from datetime import datetime

from apps.historiales.domain.errors import DatosInvalidos
from apps.historiales.domain.context import ContextoClinico
from apps.operaciones.catalog import RESOURCES, validate, validate_chronology
from apps.operaciones.repository import OperationsRepository


def repository(institution):
    # Bypass constructor solely to avoid opening/composing any real provider.
    r=object.__new__(OperationsRepository)
    r.context=ContextoClinico(institution,'audit','admin','1')
    r.specs=RESOURCES[institution]
    r.sql=True
    r.hospital=institution=='hospital'
    return r


class CursorObservation:
    def __init__(self, rows=(), aggregate=0):
        self.rows=list(rows);self.aggregate=aggregate;self.statements=[]
    def execute(self,query,args=()):self.statements.append(query)
    def fetchall(self):return self.rows
    def fetchone(self):return {'n':self.aggregate}


def observe():
    results=[]
    r=repository('hospital')
    cursor=CursorObservation([{'id_ingreso':9}])
    admission={'alta_utc':None,'id_cama':1,'fecha_hora_ingreso':datetime(2020,1,1,12)}
    try:
        r._rules(cursor,'movimiento_cama',{'id_cama':2,'fecha_hora_inicio':'2020-01-01T13:00:00Z'}, {'id_ingreso':admission},None)
        observed='accepted'
    except Exception as error:
        observed=type(error).__name__+': '+str(error)
    results.append({'finding':'AUC-01','case':'occupied bed','expected':'Conflicto / HTTP 409','observed':observed,'gap_confirmed':observed=="KeyError: 'id_cirugia'"})

    r=repository('pediatrico')
    patch=validate(r.specs['poliza_paciente'],{'fecha_fin':'2025-12-31'},partial=True)
    merged={'fecha_inicio':'2026-01-01','fecha_fin':'2026-12-31','estado':'activo'}|patch
    try:
        validate_chronology(r.specs['poliza_paciente'], merged)
        r._rules(CursorObservation(),'poliza_paciente',merged,{}, {'fecha_inicio':'2026-01-01'})
        observed='accepted by validation + merged operational rules';gap=True
    except DatosInvalidos:
        observed='DatosInvalidos: combined interval rejected';gap=False
    results.append({'finding':'AUC-05','case':'partial update ends policy before its start','expected':'validation rejection','observed':observed,'gap_confirmed':gap})

    claim={'monto_reclamado':'5.00','poliza_paciente_id':1,'estado':'pendiente'}
    refs={'factura_id':{'total_seguro':'5.00','consulta_id':10,'estado':'pendiente'},'autorizacion_id':{'poliza_paciente_id':1,'estado':'aprobado','monto_autorizado':'5.00','consulta_id':20}}
    try:
        r._rules(CursorObservation(),'reclamacion_seguro',claim,refs,None)
        observed='accepted by operational rules';gap=True
    except DatosInvalidos:
        observed='DatosInvalidos: incompatible consultation rejected';gap=False
    results.append({'finding':'AUC-04','case':'authorization and invoice belong to different consultations of same patient','expected':'reject incompatible consultation','observed':observed,'gap_confirmed':gap})

    r=repository('hospital');cursor=CursorObservation(aggregate=12)
    r._after_sql(cursor,'pago',{'id_factura':1},{'id_factura':{'total':'20.00','estado':'Pendiente'}})
    updated=any('UPDATE factura SET estado' in query for query in cursor.statements)
    results.append({'finding':'AUC-06','case':'partial payment 12 against total 20','expected':'explicit partial-paid state or defined equivalent lifecycle','observed':'invoice state recalculated' if updated else 'no invoice state update','gap_confirmed':not updated})
    return results


if __name__=='__main__':
    observations=observe()
    print(json.dumps({'method':'isolated validators, no databases or application mutations','observations':observations},ensure_ascii=False,indent=2))
    # An observation is not an acceptance assertion. Dedicated regression tests
    # now verify the closed findings; historical output remains preserved.
