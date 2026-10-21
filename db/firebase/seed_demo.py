"""Modelo DEMO provisional de odontología; no implementa CONTRACT-REPO-01."""

import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

PROJECT = "demo-historiales"
FIXTURE = Path(__file__).with_name("demo.json")
COLLECTIONS = {
    "pacientes": {"identificacion", "nombres", "apellidos", "fecha_nacimiento", "estado", "contacto"},
    "citas": {"paciente_id", "fecha", "motivo", "estado"},
    "consultas": {"paciente_id", "cita_id", "fecha", "motivo", "diagnosticos"},
    "procedimientos": {"paciente_id", "consulta_id", "pieza", "descripcion", "estado"},
    "recetas": {"paciente_id", "consulta_id", "fecha", "indicaciones"},
    "pagos": {"paciente_id", "procedimiento_id", "fecha", "monto_centavos", "moneda", "estado"},
}
STATES = {
    "pacientes": {"activo", "archivado"},
    "citas": {"programada", "atendida", "cancelada"},
    "procedimientos": {"pendiente", "realizado"},
    "pagos": {"registrado", "anulado"},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 500


def validate(data):
    """Valida todo antes de conectar o escribir. Campos exclusivos de la demo."""
    require(isinstance(data, dict) and set(data) == set(COLLECTIONS), "Se requieren las seis colecciones DEMO")
    for collection, fields in COLLECTIONS.items():
        require(isinstance(data[collection], dict) and bool(data[collection]), "Colección DEMO vacía o inválida")
        for doc_id, doc in data[collection].items():
            require(text(doc_id) and doc_id.startswith("DEMO-") and "/" not in doc_id, "ID DEMO inválido")
            require(isinstance(doc, dict) and set(doc) == fields, "Campos DEMO inesperados o ausentes")
            for key, value in doc.items():
                if key not in {"contacto", "diagnosticos", "indicaciones", "monto_centavos"}:
                    require(text(value), "Campo textual inválido: " + key)
            if collection in STATES:
                require(doc["estado"] in STATES[collection], "Estado inválido")
            if "fecha" in doc:
                require(doc["fecha"].endswith("Z"), "Timestamp debe estar en UTC Z")
                parsed = datetime.fromisoformat(doc["fecha"].replace("Z", "+00:00"))
                require(parsed.utcoffset().total_seconds() == 0, "Timestamp debe estar en UTC")
                require(parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z") == doc["fecha"], "Timestamp DEMO debe usar formato ISO con milisegundos")
            if collection == "pacientes":
                require(date.fromisoformat(doc["fecha_nacimiento"]).isoformat() == doc["fecha_nacimiento"], "Fecha civil inválida")
                require(doc["identificacion"].startswith("DEMO-"), "Identificación debe ser ficticia")
                contact = doc["contacto"]
                require(isinstance(contact, dict) and set(contact) == {"nota"} and text(contact["nota"]), "Contacto DEMO inválido")
            if collection == "consultas":
                require(isinstance(doc["diagnosticos"], list) and 1 <= len(doc["diagnosticos"]) <= 10, "Diagnósticos DEMO inválidos")
                ids = []
                for diagnosis in doc["diagnosticos"]:
                    require(isinstance(diagnosis, dict) and set(diagnosis) == {"id", "descripcion"}, "Diagnóstico inválido")
                    require(text(diagnosis["id"]) and diagnosis["id"].startswith("DEMO-") and text(diagnosis["descripcion"]), "Diagnóstico DEMO inválido")
                    ids.append(diagnosis["id"])
                require(len(ids) == len(set(ids)), "Diagnóstico duplicado")
            if collection == "recetas":
                require(isinstance(doc["indicaciones"], list) and 1 <= len(doc["indicaciones"]) <= 10, "Indicaciones DEMO inválidas")
                for item in doc["indicaciones"]:
                    require(isinstance(item, dict) and set(item) == {"medicamento", "dosis", "via", "frecuencia", "duracion"}, "Renglón de receta DEMO inválido")
                    require(all(text(value) for value in item.values()) and item["medicamento"].startswith("DEMO-"), "Indicación debe ser ficticia y completa")
            if collection == "procedimientos":
                require(doc["pieza"] in {str(q * 10 + p) for q in range(1, 5) for p in range(1, 9)}, "Pieza permanente FDI inválida")
            if collection == "pagos":
                require(type(doc["monto_centavos"]) is int and doc["monto_centavos"] > 0, "Importe debe ser entero positivo en centavos")
                require(doc["moneda"] == "GTQ", "Moneda DEMO inválida")
    identifications = [d["identificacion"] for d in data["pacientes"].values()]
    require(len(identifications) == len(set(identifications)), "Identificación DEMO duplicada")
    for collection, documents in data.items():
        for doc in documents.values():
            for field, target in {"paciente_id": "pacientes", "cita_id": "citas", "consulta_id": "consultas", "procedimiento_id": "procedimientos"}.items():
                if field in doc:
                    require(doc[field] in data[target], "Referencia inexistente: " + field)
                    if field != "paciente_id":
                        require(data[target][doc[field]]["paciente_id"] == doc["paciente_id"], "Referencia a otro paciente")
    return data


def load_fixture():
    return validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


def emulator_host():
    host = os.getenv("FIRESTORE_EMULATOR_HOST", "")
    parsed = urlsplit("//" + host)
    require(parsed.hostname in {"localhost", "127.0.0.1", "::1", "firestore"}, "Solo se permite emulador local o servicio firestore")
    require(parsed.port is not None and 0 < parsed.port < 65536 and not parsed.username and not parsed.password and not parsed.path and not parsed.query and not parsed.fragment, "Destino de emulador inválido")
    require(os.getenv("FIREBASE_PROJECT_ID", PROJECT) == PROJECT, "Proyecto DEMO no autorizado")
    require(os.getenv("GOOGLE_CLOUD_PROJECT", PROJECT) == PROJECT, "Proyecto Google Cloud no autorizado")
    return host


def client_for_emulator():
    emulator_host()
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore
    return firestore.Client(project=PROJECT, credentials=AnonymousCredentials())


def stored_document(collection, doc):
    result = dict(doc, seed_version="odontologia-demo-v1")
    if "fecha" in result:
        result["fecha"] = datetime.fromisoformat(result["fecha"].replace("Z", "+00:00"))
    return result


def seed(client, data):
    """Crea solo documentos ausentes; aborta todo ante contenido diferente."""
    validate(data)
    emulator_host()
    require(client.project == PROJECT, "Cliente fuera del proyecto DEMO")
    from google.cloud import firestore
    entries = [(client.collection(c).document(i), stored_document(c, d)) for c, docs in data.items() for i, d in docs.items()]
    require(len(entries) <= 100, "Dataset DEMO demasiado grande")

    @firestore.transactional
    def apply(transaction):
        # Todas las lecturas preceden a las escrituras, también durante reintentos.
        snapshots = [ref.get(transaction=transaction, timeout=10) for ref, _ in entries]
        for snapshot, (_, expected) in zip(snapshots, entries):
            require(not snapshot.exists or snapshot.to_dict() == expected, "Conflicto DEMO: documento existente diferente; no se sobrescribe")
        created = 0
        for snapshot, (ref, expected) in zip(snapshots, entries):
            if not snapshot.exists:
                transaction.create(ref, expected)
                created += 1
        return {"created": created, "unchanged": len(entries) - created}

    return apply(client.transaction(max_attempts=3))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Valida sin SDK, conexión ni escrituras")
    args = parser.parse_args()
    data = load_fixture()
    if args.validate_only:
        print("Dataset DEMO válido: " + str(sum(map(len, data.values()))) + " documentos")
        return
    client = client_for_emulator()
    try:
        print(json.dumps(seed(client, data), sort_keys=True))
    finally:
        client.close()


if __name__ == "__main__":
    main()
