"""Consistencia del dataset DEMO, sin conexión ni dependencias clínicas de B1.

Mongo valida documentos, no claves foráneas: estas comprobaciones se realizan
antes de escribir. No sustituyen transacciones ni autorización en el adaptador.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import math

from bson import BSON, ObjectId
from bson.errors import InvalidDocument
from bson.decimal128 import Decimal128


def validate_dataset(data):
    expected = {"pacientes", "consultas", "medicamentos", "tipos_examen", "resultados_examen"}
    if set(data) != expected:
        raise ValueError("Colecciones DEMO inesperadas")
    for docs in data.values():
        ids = [doc.get("_id") for doc in docs]
        if any(not isinstance(value, ObjectId) for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("IDs internos inválidos o duplicados")
        for doc in docs:
            try:
                BSON.encode(doc)
            except (InvalidDocument, OverflowError) as error:
                raise ValueError("Documento DEMO no representable como BSON") from error
    for collection, field in (("pacientes", "identificacion"), ("tipos_examen", "nombre")):
        values = [doc.get(field) for doc in data[collection]]
        if any(not isinstance(value, str) or not value.strip() for value in values) or len(set(values)) != len(values):
            raise ValueError("Clave única DEMO inválida o duplicada")
    patients = {doc["_id"] for doc in data["pacientes"]}
    kinds = {doc["nombre"] for doc in data["tipos_examen"]}
    for collection in ("consultas", "resultados_examen"):
        for doc in data[collection]:
            if doc.get("paciente_id") not in patients:
                raise ValueError("Referencia a paciente DEMO inexistente")
    for collection, field in (("pacientes", "fecha_nacimiento"), ("consultas", "fecha"), ("resultados_examen", "fecha")):
        for doc in data[collection]:
            value = doc.get(field)
            if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
                raise ValueError("El fixture BSON requiere fechas UTC conscientes de zona")
    for doc in data["pacientes"]:
        if doc.get("estado") not in {"activo", "inactivo", "archivado"}:
            raise ValueError("Estado de paciente inválido")
    for doc in data["resultados_examen"]:
        if doc.get("tipo_examen") not in kinds:
            raise ValueError("Tipo de examen DEMO inexistente")
        if doc.get("estado") not in {"pendiente", "en_proceso", "finalizado", "anulado"}:
            raise ValueError("Estado de resultado inválido")
        fields = doc.get("campos")
        if not isinstance(fields, list) or not fields:
            raise ValueError("Resultado sin campos")
        names = set()
        for field in fields:
            name = field.get("nombre") if isinstance(field, dict) else None
            if not isinstance(name, str) or not name.strip() or name in names:
                raise ValueError("Nombre de campo vacío o repetido")
            names.add(name)
            value = field.get("valor")
            if isinstance(value, Decimal128):
                value = value.to_decimal()
            if not isinstance(value, (str, int, float, bool, Decimal)):
                raise ValueError("Valor de examen inválido")
            if (isinstance(value, Decimal) and not value.is_finite()) or (isinstance(value, float) and not math.isfinite(value)):
                raise ValueError("Valor numérico no finito")
            for optional in ("unidad", "rango"):
                if optional in field and not isinstance(field[optional], str):
                    raise ValueError("Unidad/rango deben ser cadenas si están presentes")
    return data
