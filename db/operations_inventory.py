"""Read-only preflight for operations upgrades. Uses the selected maintenance account.

No .env loading, credentials in output, DDL, grants or application mutations.
"""
import argparse
import json
import os
from pathlib import Path

FLAGS={
    'hospital':['especialidad','enfermero','pabellon_edificio','habitacion','cama','quirofano','medicamento'],
    'pediatrico':['especialidad','tutor','vacuna','tipo_examen'],
}


def inspect(connection,institution):
    postgres=institution=='hospital'
    with connection.cursor() as cursor:
        cursor.execute('SELECT version FROM '+('hospital_schema_version' if postgres else 'pediatria_schema_version'))
        versions=sorted(str(row[0]) for row in cursor.fetchall())
        if versions != (['B3-1.0.0'] if postgres else ['1']):
            raise RuntimeError('Unsupported clinical schema version; review before upgrade')
        cursor.execute("SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE "+
                       ("table_schema='public'" if postgres else 'table_schema=DATABASE()'))
        columns={(row[0],row[1]):row[2:] for row in cursor.fetchall()}
    definitions=json.loads((Path(__file__).parents[1]/'backend/apps/operaciones/resources.json').read_text())[institution]
    expected={(spec['table'],key) for spec in definitions.values() for key in spec['fields']}
    allowed={(table,'activo_operativo') for table in FLAGS[institution]}
    missing=expected-columns.keys()-allowed
    if missing:raise RuntimeError('Missing clinical columns; a flags-only upgrade is insufficient: '+str(sorted(missing)))
    flags={}
    for table in FLAGS[institution]:
        column=columns.get((table,'activo_operativo'))
        if column is None:flags[table]='missing';continue
        datatype,nullable,default=column
        if datatype!=('boolean' if postgres else 'tinyint') or nullable!='NO' or str(default).lower() not in {'true','1'}:
            raise RuntimeError('Incompatible operational flag on '+table+'; refusing a blind upgrade')
        flags[table]='compatible'
    return {'institution':institution,'clinical_versions':versions,'operations_flags':flags,'read_only':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--institution',required=True,choices=FLAGS)
    args=parser.parse_args()
    if args.institution=='hospital':
        import psycopg
        connection=psycopg.connect(host=os.environ['POSTGRES_HOST'],port=int(os.getenv('POSTGRES_PORT','5432')),dbname=os.environ['POSTGRES_DB'],user=os.environ['PG_USER'],password=os.environ['PG_PASSWORD'])
    else:
        import mysql.connector
        connection=mysql.connector.connect(host=os.environ['MYSQL_HOST'],port=int(os.getenv('MYSQL_PORT','3306')),database=os.environ['MYSQL_DB'],user=os.environ['MYSQL_USER'],password=os.environ['MYSQL_PASSWORD'])
    try:print(json.dumps(inspect(connection,args.institution),indent=2))
    finally:connection.close()
