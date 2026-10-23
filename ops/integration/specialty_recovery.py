"""Additional cold-restore assertions for new LAB-01 / ODONTO-01 collections.

Called only by run.py recovery in dedicated services. No shared destinations.
"""
import importlib.util
import os
from pathlib import Path
import time
from unittest.mock import patch
from uuid import uuid4


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def prepare(root, bins, directory):
    import sys
    sys.path.insert(0, str(root / "backend"))
    from apps.historiales.domain.context import ContextoClinico
    from apps.historiales.infrastructure.adapters.mongo_adapter import MongoAdapter
    from apps.historiales.infrastructure.adapters.firestore_adapter import FirestoreAdapter
    from pymongo import MongoClient
    mongo = module("extra_mongo_recovery", root / "db/mongo/clinical_recovery.py")
    firebase = module("extra_firestore_recovery", root / "db/firebase/clinical_recovery.py")
    suffix = uuid4().hex[:16]
    source = f"mongodb://127.0.0.1:27039/specialty_source_{suffix}?replicaSet=recovery"
    target = f"mongodb://127.0.0.1:27049/specialty_recovery_{uuid4().hex}?replicaSet=recoveryTarget"
    project = "demo-specialty-recovery"
    with MongoClient(source) as client:
        db = client.get_default_database()
        module("extra_schema", root / "db/mongo/clinical_schema.py").prepare(db)
        module("extra_specialty_schema", root / "db/mongo/specialty_schema.py").prepare(db)
        db.clinico_tipos_examen.insert_one({"_id": "DEMO-E", "nombre": "DEMO examen", "institucion": "laboratorio", "schema_version": 2})
    snapshots = {}
    for institution, provider, environment in (
        ("laboratorio", MongoAdapter, {"MONGO_URI": source}),
        ("odontologica", FirestoreAdapter, {"FIRESTORE_EMULATOR_HOST": "127.0.0.1:8093", "FIREBASE_PROJECT_ID": project}),
    ):
        with patch.dict(os.environ, environment):
            repo = provider(contexto=ContextoClinico(institution, "DEMO-recovery", "admin", "1"))
            patient = repo.registrar_paciente({"identificacion": "DEMO-SPECIALTY", "nombres": "DEMO", "apellidos": "Recuperacion", "fecha_nacimiento": "2000-01-01"})
            consult = repo.registrar_consulta(patient["id"], {"fecha": "2020-01-01", "notas_evolucion": "DEMO"})
            diagnosis = repo.registrar_diagnostico(consult["id"], {"codigo_cie10": "DEMO", "descripcion": "DEMO"})
            treatment = repo.registrar_tratamiento(diagnosis["id"], {"indicaciones_generales": "DEMO"})
            if institution == "laboratorio":
                repo.registrar_resultado(patient["id"], {"tipo_examen": "DEMO-E", "fecha": "2020-01-01T00:00:00.125Z", "estado": "finalizado", "campos": [{"nombre": "numero", "valor": 3.5}, {"nombre": "booleano", "valor": False}, {"nombre": "texto", "valor": "DEMO"}]})
                specialized = repo.listar_resultados(patient["id"])
            else:
                repo.registrar_procedimiento(patient["id"], {"tratamiento_id": treatment["id"], "pieza": "16", "descripcion": "DEMO", "estado": "realizado"})
                specialized = repo.listar_procedimientos(patient["id"])
            snapshots[institution] = (patient["id"], repo.obtener_historial(patient["id"]), specialized)
    mongo.backup(source, directory / "specialty-mongo", writers_stopped=True, mongodump=bins / "mongodump")
    with patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "127.0.0.1:8093"}):
        firebase.backup(project, directory / "specialty-firestore", writers_stopped=True)
    return mongo, firebase, target, project, snapshots


def verify(root, bins, directory, prepared, server):
    from apps.historiales.domain.context import ContextoClinico
    from apps.historiales.infrastructure.adapters.mongo_adapter import MongoAdapter
    from apps.historiales.infrastructure.adapters.firestore_adapter import FirestoreAdapter
    mongo, firebase, target, project, snapshots = prepared
    mongo.restore(target, directory / "specialty-mongo", mongorestore=bins / "mongorestore")
    _, metadata = firebase.read_backup(directory / "specialty-firestore")
    process, handle = server(["java", "-jar", "/opt/firestore.jar", "--host=127.0.0.1", "--port=8097", "--project_id=" + project, "--import-data=" + str(metadata)], "specialty-restore")
    try:
        with patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "127.0.0.1:8097"}):
            for _ in range(50):
                try:
                    firebase.verify_restored(project, directory / "specialty-firestore")
                    break
                except Exception:
                    if process.poll() is not None:
                        raise RuntimeError("Specialty restore JVM failed") from None
                    time.sleep(0.2)
            else:
                raise RuntimeError("Specialty restore did not become ready")
        for institution, provider, environment in (
            ("laboratorio", MongoAdapter, {"MONGO_URI": target}),
            ("odontologica", FirestoreAdapter, {"FIRESTORE_EMULATOR_HOST": "127.0.0.1:8097", "FIREBASE_PROJECT_ID": project}),
        ):
            with patch.dict(os.environ, environment):
                repo = provider(contexto=ContextoClinico(institution, "DEMO-recovery", "admin", "1"))
                if snapshots is not None:
                    identifier, history, specialized = snapshots[institution]
                    assert repo.obtener_historial(identifier) == history
                else:
                    # Resume verification after an interrupted runner: native
                    # manifests already compare every document hash to source.
                    patients = repo.listar_pacientes()["results"]
                    assert len(patients) == 1 and patients[0]["identificacion"] == "DEMO-SPECIALTY"
                    identifier = patients[0]["id"]
                actual = repo.listar_resultados(identifier) if institution == "laboratorio" else repo.listar_procedimientos(identifier)
                if institution == "laboratorio":
                    assert actual["resultados"][0]["campos"][1]["valor"] is False
                if snapshots is not None:
                    assert actual == specialized
                elif institution == "laboratorio":
                    assert [v["valor"] for v in actual["resultados"][0]["campos"]] == [3.5, False, "DEMO"]
                    assert len(actual["resultados"]) == 1
                else:
                    assert len(actual["procedimientos"]) == 1 and actual["procedimientos"][0]["pieza"] == "16"
                    treatment = repo.obtener_historial(identifier)["consultas"][0]["diagnosticos"][0]["tratamientos"][0]
                    assert actual["procedimientos"][0]["tratamiento_id"] == treatment["id"]
                repo.registrar_consulta(identifier, {"fecha": "2020-01-02", "notas_evolucion": "DEMO despues de restore"})
                assert len(repo.obtener_historial(identifier)["consultas"]) == 2
        print("Extra cold restore OK: LAB results/types and dental procedures, metadata and continued writes", flush=True)
    finally:
        process.terminate()
        process.wait(timeout=15)
        handle.close()
