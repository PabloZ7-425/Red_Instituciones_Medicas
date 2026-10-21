"""Seed sintético de laboratorio; no es un adaptador ni contrato clínico."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from validate_demo import validate_dataset


def fixture():
    from bson import ObjectId
    patient = ObjectId("000000000000000000000001")
    instant = datetime(2026, 10, 20, 15, tzinfo=timezone.utc)
    data = {
        "pacientes": [{"_id": patient, "identificacion": "DEMO-LAB-001", "nombres": "Paciente", "apellidos": "Sintético", "fecha_nacimiento": datetime(2001, 2, 3, tzinfo=timezone.utc), "estado": "activo", "contacto": {"nota": "DEMO sin contacto real"}}],
        "consultas": [{"_id": ObjectId("000000000000000000000002"), "paciente_id": patient, "fecha": instant, "diagnosticos": [{"descripcion": "DEMO: hallazgo ficticio"}], "recetas": []}],
        "medicamentos": [{"_id": ObjectId("000000000000000000000003"), "nombre": "DEMO-MED-001 (no administrar)"}],
        "tipos_examen": [], "resultados_examen": []
    }
    examples = [
        ("DEMO-hematologia", [{"nombre": "DEMO-hemoglobina", "valor": 14.0, "unidad": "g/dL", "rango": "DEMO-12-16"}]),
        ("DEMO-orina", [{"nombre": "DEMO-color", "valor": "amarillo"}, {"nombre": "DEMO-proteinas", "valor": False}]),
        ("DEMO-quimica", [{"nombre": "DEMO-glucosa", "valor": 90, "unidad": "mg/dL", "rango": "DEMO-70-100"}])
    ]
    for index, (kind, fields) in enumerate(examples):
        data["tipos_examen"].append({"_id": ObjectId(f"{10 + index:024x}"), "nombre": kind})
        data["resultados_examen"].append({"_id": ObjectId(f"{20 + index:024x}"), "paciente_id": patient, "tipo_examen": kind, "fecha": instant, "estado": "finalizado", "campos": fields})
    for documents in data.values():
        for doc in documents:
            doc["seed_version"] = "laboratorio-demo-v1"
    return data


def local_uri():
    uri = os.getenv("MONGO_DEMO_URI", "")
    parsed = urlsplit(uri)
    if parsed.scheme != "mongodb" or parsed.hostname not in {"localhost", "127.0.0.1", "::1", "mongo"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("MONGO_DEMO_URI debe señalar a MongoDB local sin credenciales ni opciones")
    if not parsed.port or parsed.path != "/laboratorio_demo":
        raise ValueError("Solo se permite puerto explícito y base laboratorio_demo")
    return uri


def seed(database):
    if database.name != "laboratorio_demo":
        raise ValueError("El seed solo escribe en laboratorio_demo")
    data = fixture()
    validate_dataset(data)
    # Preflight completo: no sobrescribir registros distintos. Standalone NO ofrece
    # atomicidad multidocumento; un error de red puede dejar un subconjunto creado.
    for collection, docs in data.items():
        for doc in docs:
            current = database[collection].find_one({"_id": doc["_id"]})
            if current is not None and current != doc:
                raise ValueError("Conflicto DEMO: no se sobrescribe contenido existente")
            # También revisar claves únicas antes de crear cualquier documento.
            key = {"pacientes": "identificacion", "tipos_examen": "nombre"}.get(collection)
            if key:
                owner = database[collection].find_one({key: doc[key]})
                if owner is not None and owner["_id"] != doc["_id"]:
                    raise ValueError("Conflicto DEMO: clave única ocupada")
    created = 0
    for collection, docs in data.items():
        for doc in docs:
            result = database[collection].update_one({"_id": doc["_id"]}, {"$setOnInsert": doc}, upsert=True)
            created += int(result.upserted_id is not None)
    # Detecta también una modificación concurrente; nunca la sobrescribe.
    for collection, docs in data.items():
        for doc in docs:
            if database[collection].find_one({"_id": doc["_id"]}) != doc:
                raise ValueError("Conflicto concurrente DEMO; revisar documentos, sin sobrescribir")
    total = sum(map(len, data.values()))
    return {"created": created, "unchanged": total - created}


def initialize_demo(database, manifest):
    """Aplica el esquema exportado de init.js únicamente a la base DEMO."""
    expected = {"usuarios", "pacientes", "consultas", "medicamentos", "tipos_examen", "resultados_examen"}
    if database.name != "laboratorio_demo" or set(manifest["schemas"]) != expected:
        raise ValueError("Destino o manifiesto DEMO inválido")
    existing = set(database.list_collection_names())
    for name, options in manifest["schemas"].items():
        if name not in existing:
            database.create_collection(name, **options)
        elif "validator" in options:
            database.command({"collMod": name, "validator": options["validator"], "validationLevel": "strict", "validationAction": "error"})
        for index in manifest["indexes"].get(name, []):
            database[name].create_index(list(index["keys"].items()), **index["options"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Construye BSON DEMO sin conexión; no valida contra servidor")
    parser.add_argument("--schema", type=Path, help="Manifiesto exportado por schema_manifest.js; aplica solo a laboratorio_demo")
    args = parser.parse_args()
    if args.validate_only:
        validate_dataset(fixture())
        print("Fixture BSON construido: " + str(sum(map(len, fixture().values()))) + " documentos; validación servidor pendiente")
        return
    from pymongo import MongoClient
    with MongoClient(local_uri(), serverSelectionTimeoutMS=3000, socketTimeoutMS=5000, tz_aware=True) as client:
        if args.schema:
            initialize_demo(client.laboratorio_demo, json.loads(args.schema.read_text(encoding="utf-8-sig")))
        if not {"pacientes", "consultas", "resultados_examen"}.issubset(client.laboratorio_demo.list_collection_names()):
            raise ValueError("Inicializar esquema DEMO primero con --schema")
        print(json.dumps(seed(client.laboratorio_demo), sort_keys=True))


if __name__ == "__main__":
    main()
