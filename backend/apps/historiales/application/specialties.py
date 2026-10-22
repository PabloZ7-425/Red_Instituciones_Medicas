"""SPECIALTY-API-01@1.0.0: additive institutional use cases and pure DTO validation."""
import math
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal

from apps.historiales.application.validation import identificador, invalid, texto, validar_dto
from apps.historiales.domain.context import autorizar
from apps.historiales.domain.errors import AccesoDenegado, PersistenciaNoDisponible

# action: institution, core permission, repository method, required fields, optional fields
ACTIONS = {
    'admission': ('hospital', 'registrar_consulta', 'ingresar_paciente', ('cama_id', 'fecha_hora_ingreso', 'tipo_ingreso'), ()),
    'discharge': ('hospital', 'registrar_consulta', 'dar_alta', ('fecha_hora_alta',), ()),
    'tutor': ('pediatrico', 'registrar_paciente', 'registrar_tutor', ('nombres', 'apellidos', 'parentesco'), ('telefono', 'correo', 'dpi')),
    'vaccine': ('pediatrico', 'registrar_consulta', 'registrar_vacuna', ('vacuna_id', 'fecha', 'dosis'), ('lote', 'observaciones')),
    'growth': ('pediatrico', 'registrar_consulta', 'registrar_crecimiento', ('fecha', 'peso_kg', 'talla_cm'), ('observaciones',)),
    'result': ('laboratorio', 'registrar_consulta', 'registrar_resultado', ('tipo_examen', 'fecha', 'estado', 'campos'), ()),
    'procedure': ('odontologica', 'registrar_diagnostico', 'registrar_procedimiento', ('tratamiento_id', 'pieza', 'descripcion', 'estado'), ()),
}
READS = {
    'admissions': ('hospital', 'obtener_historial', 'listar_ingresos'),
    'beds': ('hospital', 'obtener_historial', 'listar_camas'),
    'followup': ('pediatrico', 'obtener_historial', 'obtener_seguimiento'),
    'tutors': ('pediatrico', 'registrar_paciente', 'listar_tutores'),
    'vaccines': ('pediatrico', 'obtener_historial', 'listar_vacunas'),
    'results': ('laboratorio', 'obtener_historial', 'listar_resultados'),
    'exams': ('laboratorio', 'obtener_historial', 'listar_tipos_examen'),
    'procedures': ('odontologica', 'obtener_historial', 'listar_procedimientos'),
}
CATALOGS = {'beds', 'vaccines', 'exams'}


def utc(value, field):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', value):
        invalid(field, 'Se requiere timestamp UTC terminado en Z')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        invalid(field, 'Timestamp inválido')
    if parsed > datetime.now(timezone.utc):
        invalid(field, 'No puede ser futuro')
    return parsed.isoformat().replace('+00:00', 'Z')


def validate_specialty(action, body):
    _, _, _, required, optional = ACTIONS[action]
    if not isinstance(body, Mapping) or not set(required) <= body.keys() or set(body) - set(required) - set(optional):
        invalid('body', 'Faltan campos requeridos o hay campos desconocidos')
    data = {}
    for name, value in body.items():
        if name.endswith('_id') or name == 'tipo_examen':
            data[name] = identificador(value, name)
        elif name == 'fecha' and action != 'result':
            data[name] = validar_dto('consulta', {'fecha': value, 'notas_evolucion': 'Validación'})['fecha']
        elif name.startswith('fecha_hora_') or name == 'fecha':
            data[name] = utc(value, name)
        elif name in {'peso_kg', 'talla_cm'}:
            if not isinstance(value, str) or not re.fullmatch(r'\d{1,4}(?:\.\d{1,2})?', value) or not 0 < Decimal(value) <= Decimal('9999.99'):
                invalid(name, 'Se requiere decimal string positivo, máximo 9999.99')
            data[name] = f'{Decimal(value):.2f}'
        elif name == 'dosis':
            if type(value) is not int or not 1 <= value <= 2147483647:
                invalid(name, 'Se requiere entero positivo')
            data[name] = value
        elif name == 'campos':
            if not isinstance(value, list) or not 1 <= len(value) <= 50:
                invalid(name, 'Se requieren entre 1 y 50 campos')
            converted, names = [], set()
            for row in value:
                if not isinstance(row, Mapping) or not {'nombre', 'valor'} <= row.keys() or set(row) - {'nombre', 'valor', 'unidad', 'rango'}:
                    invalid(name, 'Campo de resultado inválido')
                title = texto(row['nombre'], name, 100)
                if title in names:
                    invalid(name, 'Nombre de campo duplicado')
                names.add(title)
                result = row['valor']
                if type(result) not in {str, int, float, bool}:
                    invalid(name, 'Valor de resultado inválido')
                if type(result) in {int, float} and (abs(result) > 9007199254740991 or not math.isfinite(result)):
                    invalid(name, 'Número fuera del rango interoperable')
                if isinstance(result, str):
                    result = texto(result, name, 5000)
                item = {'nombre': title, 'valor': result}
                for key in ('unidad', 'rango'):
                    if key in row:
                        item[key] = texto(row[key], name, 100)
                converted.append(item)
            data[name] = converted
        else:
            maximum = 5000 if name in {'descripcion', 'observaciones'} else 150 if name == 'correo' else 50 if name == 'tipo_ingreso' else 100
            data[name] = texto(value, name, maximum)
    if action == 'procedure':
        pieces = {str(q * 10 + n) for q in range(1, 9) for n in range(1, 9 if q <= 4 else 6)}
        if data['pieza'] not in pieces or data['estado'] not in {'pendiente', 'realizado'}:
            invalid('pieza' if data['pieza'] not in pieces else 'estado', 'Valor no permitido')
    if action == 'result' and data['estado'] not in {'pendiente', 'en_proceso', 'finalizado', 'anulado'}:
        invalid('estado', 'Estado inválido')
    return data


class SpecialtyService:
    def __init__(self, context, factory):
        self.context, self.factory = context, factory

    def authorize(self, action):
        spec = ACTIONS.get(action) or READS[action]
        autorizar(self.context, spec[1])
        if self.context.institucion != spec[0]:
            raise AccesoDenegado()

    def execute(self, action, identifier=None, body=None, page=None):
        self.authorize(action)
        spec = ACTIONS.get(action) or READS[action]
        if identifier is not None:
            identificador(identifier)
        data = validate_specialty(action, body) if action in ACTIONS else None
        repo = self.factory(self.context)
        method = getattr(repo, spec[2], None)
        if not callable(method):
            raise PersistenciaNoDisponible()
        if action in CATALOGS:
            return method(**page)
        if action == 'discharge':
            return method(identifier, data['fecha_hora_alta'])
        return method(identifier, data) if data is not None else method(identifier)
