"""Explicit A3 collection provisioning; never rewrite A2/legacy collections."""
import argparse
import os

from pymongo import MongoClient

TEXTS = {
    'pacientes': {'identificacion': 20, 'nombres': 100, 'apellidos': 100, 'fecha_nacimiento': 10, 'estado': 9},
    'consultas': {'paciente_id': 1500, 'profesional_id': 1500, 'fecha': 10, 'notas_evolucion': 5000},
    'diagnosticos': {'paciente_id': 1500, 'consulta_id': 1500, 'codigo_cie10': 20, 'descripcion': 5000},
    'tratamientos': {'paciente_id': 1500, 'diagnostico_id': 1500, 'indicaciones_generales': 5000},
    'recetas': {'paciente_id': 1500, 'tratamiento_id': 1500, 'medicamento_id': 1500, 'dosis': 100, 'frecuencia': 100},
    'medicamentos': {'nombre': 150},
    'identificaciones': {'paciente_id': 1500, 'identificacion': 20},
    'citas': {'paciente_id': 1500, 'profesional_id': 1500, 'estado': 12},
}


def validator(collection):
    properties = {'_id': {'bsonType': 'string', 'minLength': 1},
                  'schema_version': {'enum': [2]}, 'institucion': {'enum': ['laboratorio']}}
    properties.update({k: {'bsonType': 'string', 'minLength': 1, 'maxLength': maximum} for k, maximum in TEXTS[collection].items()})
    if collection == 'pacientes':
        properties['estado'] = {'enum': ['activo', 'inactivo', 'archivado']}
        properties['version'] = {'bsonType': ['int', 'long'], 'minimum': 0}
    return {'$jsonSchema': {'bsonType': 'object', 'required': list(properties), 'properties': properties}}


def prepare(db):
    """Maintenance action. Reject differing existing validators; no collMod/data edits."""
    for name in TEXTS:
        collection = 'clinico_' + name
        expected = validator(name)
        if collection in db.list_collection_names():
            if db[collection].options().get('validator') != expected:
                raise RuntimeError('Validador clínico incompatible: requiere revisión explícita')
        else:
            db.create_collection(collection, validator=expected, validationLevel='strict', validationAction='error')
        db[collection].create_index([('institucion', 1), ('schema_version', 1)])
    db.clinico_pacientes.create_index([('institucion', 1), ('identificacion', 1)], unique=True)
    for name in ('consultas', 'diagnosticos', 'tratamientos', 'recetas'):
        db['clinico_' + name].create_index([('institucion', 1), ('paciente_id', 1)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    with MongoClient(os.environ['MONGO_CLINICAL_SETUP_URI'], serverSelectionTimeoutMS=3000) as client:
        prepare(client.get_default_database())
        print('A3: colecciones e índices preparados; ningún dato legacy modificado')
