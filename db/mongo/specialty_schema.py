"""Explicit LAB-01 maintenance; no rewriting or migration of A2 legacy data."""
import argparse
import os

from pymongo import MongoClient


def validators():
    shared = {'_id': {'bsonType': 'string', 'minLength': 1}, 'schema_version': {'enum': [2]}, 'institucion': {'enum': ['laboratorio']}}
    catalog = shared | {'nombre': {'bsonType': 'string', 'minLength': 1, 'maxLength': 150}}
    result = shared | {key: {'bsonType': 'string', 'minLength': 1} for key in ('paciente_id', 'profesional_id', 'tipo_examen', 'fecha')}
    result['estado'] = {'enum': ['pendiente', 'en_proceso', 'finalizado', 'anulado']}
    result['campos'] = {'bsonType': 'array', 'minItems': 1, 'maxItems': 50, 'items': {
        'bsonType': 'object', 'required': ['nombre', 'valor'], 'additionalProperties': False,
        'properties': {'nombre': {'bsonType': 'string', 'minLength': 1, 'maxLength': 100},
                       'valor': {'bsonType': ['string', 'int', 'long', 'double', 'bool']},
                       'unidad': {'bsonType': 'string', 'maxLength': 100}, 'rango': {'bsonType': 'string', 'maxLength': 100}}}}
    return {name: {'$jsonSchema': {'bsonType': 'object', 'required': list(props), 'properties': props}}
            for name, props in [('clinico_tipos_examen', catalog), ('clinico_resultados', result)]}


def prepare(db):
    expected = validators()
    present = set(db.list_collection_names())
    # Validate every existing definition before performing any maintenance.
    for name, validator in expected.items():
        if name in present:
            options = db[name].options()
            if (options.get('validator') != validator or options.get('validationAction', 'error') != 'error'
                    or options.get('validationLevel', 'strict') != 'strict'):
                raise RuntimeError('Validador LAB-01 incompatible; requiere revisión explícita')
    for name, validator in expected.items():
        if name not in present:
            db.create_collection(name, validator=validator, validationLevel='strict', validationAction='error')
        db[name].create_index([('institucion', 1), ('schema_version', 1)])
    db.clinico_resultados.create_index([('institucion', 1), ('paciente_id', 1), ('fecha', 1)])
    db.clinico_tipos_examen.create_index([('institucion', 1), ('nombre', 1)], unique=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    with MongoClient(os.environ['MONGO_CLINICAL_SETUP_URI'], serverSelectionTimeoutMS=3000) as client:
        prepare(client.get_default_database())
        print('LAB-01 preparado; legacy y catálogos existentes conservados')
