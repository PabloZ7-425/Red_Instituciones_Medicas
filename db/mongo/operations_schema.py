"""Explicit operational provisioning. No legacy collections or existing validators are altered."""
import argparse
import os
from pymongo import MongoClient

COLLECTIONS=('profesionales_operativos','pagos','operaciones_unicidad')

def prepare(db):
    expected={'$jsonSchema':{'bsonType':'object','required':['_id','institucion','schema_version'],
              'properties':{'_id':{'bsonType':'string'},'institucion':{'enum':['laboratorio']},'schema_version':{'enum':[2]}}}}
    names=set(db.list_collection_names())
    for name in COLLECTIONS:
        target='clinico_'+name
        if target in names and db[target].options().get('validator')!=expected:
            raise RuntimeError('Colección operativa incompatible; requiere revisión')
    for name in COLLECTIONS:
        target='clinico_'+name
        if target not in names:db.create_collection(target,validator=expected,validationLevel='strict',validationAction='error')
        db[target].create_index([('institucion',1),('schema_version',1)])
    db.clinico_citas.create_index([('profesional_id',1),('fecha_hora',1)])
    db.clinico_pagos.create_index([('paciente_id',1),('fecha_hora',1)])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true',required=True);p.parse_args()
    with MongoClient(os.environ['MONGO_CLINICAL_SETUP_URI']) as client:prepare(client.get_default_database())
    print('Colecciones operativas listas; sin cambios de datos legados')
