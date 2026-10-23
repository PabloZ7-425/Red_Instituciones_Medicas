"""Explicit local academic setup. Requires prior verified backups; never seeds patients.

Creates only synthetic reference catalogs/professionals and four clinical DEMO
accounts. Existing records/passwords are never overwritten. Repeating is safe.
"""
import importlib.util
import json
import os
from pathlib import Path
import secrets

import mysql.connector
import psycopg
from pymongo import MongoClient
from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def pg_reference(c, select, insert, params):
    row = c.execute(select, (params[0],)).fetchone()
    return row[0] if row else c.execute(insert, params).fetchone()[0]


def mysql_reference(c, table, column, value, insert, params):
    # Table/column are fixed program constants, not HTTP input.
    c.execute(f"SELECT id FROM {table} WHERE {column}=%s", (value,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute(insert, params)
    return c.lastrowid


def main():
    if os.environ.get("PABLO_LOCAL_SETUP") != "backups-verified":
        raise RuntimeError("Requiere mantenimiento explícito con respaldos verificados")
    references = {}
    with psycopg.connect(host="postgres", dbname="hospital", user=os.environ["PG_USER"], password=os.environ["PG_PASSWORD"]) as conn:
        specialty = pg_reference(conn, "SELECT id_especialidad FROM especialidad WHERE nombre=%s",
                                 "INSERT INTO especialidad(nombre,nivel_complejidad) VALUES(%s,%s) RETURNING id_especialidad", ("DEMO Pablo", 1))
        professional = pg_reference(conn, "SELECT id_medico FROM medico WHERE colegiado=%s",
                                    "INSERT INTO medico(colegiado,id_especialidad,nombre_completo) VALUES(%s,%s,%s) RETURNING id_medico",
                                    ("DEMO-PABLO-LOCAL", specialty, "Profesional DEMO local"))
        if not conn.execute("SELECT habilitado FROM medico WHERE id_medico=%s", (professional,)).fetchone()[0]:
            raise RuntimeError("Profesional DEMO deshabilitado; no se reactiva automáticamente")
        references["hospital"] = str(professional)
        pg_reference(conn, "SELECT id_medicamento FROM medicamento WHERE nombre_comercial=%s",
                     "INSERT INTO medicamento(nombre_comercial,principio_activo) VALUES(%s,%s) RETURNING id_medicamento", ("DEMO Pablo no administrar", "DEMO"))
        wing = pg_reference(conn, "SELECT id_pabellon FROM pabellon_edificio WHERE nombre_pabellon=%s",
                            "INSERT INTO pabellon_edificio(nombre_pabellon) VALUES(%s) RETURNING id_pabellon", ("DEMO Pablo",))
        room = pg_reference(conn, "SELECT id_habitacion FROM habitacion WHERE numero_habitacion=%s",
                            "INSERT INTO habitacion(numero_habitacion,id_pabellon) VALUES(%s,%s) RETURNING id_habitacion", ("DEMO-PABLO", wing))
        pg_reference(conn, "SELECT id_cama FROM cama WHERE codigo_cama=%s",
                     "INSERT INTO cama(codigo_cama,id_habitacion,estado_limpieza) VALUES(%s,%s,%s) RETURNING id_cama", ("DEMO-PABLO-CAMA", room, "limpia"))
    conn = mysql.connector.connect(host="mysql", database="pediatrico", user="root", password=os.environ["MYSQL_ROOT_PASSWORD"])
    try:
        with conn.cursor() as c:
            specialty = mysql_reference(c, "especialidad", "nombre", "DEMO Pablo", "INSERT INTO especialidad(nombre) VALUES(%s)", ("DEMO Pablo",))
            professional = mysql_reference(c, "medico", "colegiado", "DEMO-PABLO-LOCAL",
                                           "INSERT INTO medico(colegiado,nombre,apellido,especialidad_id) VALUES(%s,%s,%s,%s)",
                                           ("DEMO-PABLO-LOCAL", "Profesional", "DEMO local", specialty))
            c.execute("SELECT estado FROM medico WHERE id=%s", (professional,))
            if c.fetchone()[0] != "activo":
                raise RuntimeError("Profesional DEMO inactivo; no se reactiva automáticamente")
            references["pediatrico"] = str(professional)
            mysql_reference(c, "medicamento", "nombre", "DEMO Pablo no administrar", "INSERT INTO medicamento(nombre) VALUES(%s)", ("DEMO Pablo no administrar",))
            mysql_reference(c, "vacuna", "nombre", "DEMO Pablo no aplicar", "INSERT INTO vacuna(nombre) VALUES(%s)", ("DEMO Pablo no aplicar",))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    with MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=3000) as client:
        database = client.get_default_database()
        module("clinical_setup", "/mongo-schema/clinical_schema.py").prepare(database)
        module("specialty_setup", "/mongo-schema/specialty_schema.py").prepare(database)
        for collection, identifier, name in (("clinico_medicamentos", "DEMO-PABLO-M", "DEMO Pablo no administrar"),
                                              ("clinico_tipos_examen", "DEMO-PABLO-E", "DEMO examen Pablo")):
            row = {"_id": identifier, "nombre": name, "schema_version": 2, "institucion": "laboratorio"}
            if collection == "clinico_medicamentos":
                row["presentacion"] = None
            existing = database[collection].find_one({"_id": identifier})
            if existing is None:
                database[collection].insert_one(row)
            elif existing != row:
                raise RuntimeError("Catálogo DEMO Mongo incompatible; no se sobrescribe")
    client = firestore.Client(project=os.environ["FIREBASE_PROJECT_ID"], credentials=AnonymousCredentials())
    try:
        ref = client.collection("medicamentos").document("DEMO-PABLO-M")
        row = {"nombre": "DEMO Pablo no administrar", "presentacion": None, "schema_version": 2, "institucion": "odontologica"}
        current = ref.get()
        if not current.exists:
            ref.create(row)
        elif current.to_dict() != row:
            raise RuntimeError("Catálogo DEMO Firestore incompatible; no se sobrescribe")
    finally:
        client.close()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.contrib.auth.models import User
    from django.db import transaction
    from apps.identidad.models import PerfilInstitucional, Profesional
    directory = Path("/private")
    path = directory / "access.json"
    accounts = json.loads(path.read_text()) if path.exists() else {}
    for institution in ("hospital", "pediatrico", "laboratorio", "odontologica"):
        accounts.setdefault(institution, {"username": "DEMO-PABLO-" + institution, "password": secrets.token_urlsafe(24)})
    path.write_text(json.dumps(accounts, indent=2))
    path.chmod(0o600)
    with transaction.atomic():
        for institution, credentials in accounts.items():
            pro, _ = Profesional.objects.get_or_create(institucion=institution, referencia_externa=references.get(institution, "DEMO-PABLO-PRO"))
            if not pro.habilitado:
                raise RuntimeError("Vínculo DEMO deshabilitado; no se modifica")
            user = User.objects.filter(username=credentials["username"]).first()
            if user is None:
                user = User.objects.create_user(credentials["username"], password=credentials["password"])
                PerfilInstitucional.objects.create(usuario=user, institucion=institution, rol="admin", profesional=pro)
            else:
                profile = PerfilInstitucional.objects.get(usuario=user)
                if not user.check_password(credentials["password"]) or not user.is_active or not profile.activo or profile.institucion != institution or profile.rol != "admin" or profile.profesional_id != pro.id:
                    raise RuntimeError("Cuenta DEMO existente incompatible; no se cambia contraseña/perfil")
    print("Referencias y cuatro cuentas DEMO preparadas; claves solo en .local/bootstrap/access.json. Sin crear pacientes.")


if __name__ == "__main__":
    main()
