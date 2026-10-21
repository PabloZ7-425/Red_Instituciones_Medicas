"""Exporta solo el dataset DEMO exacto desde un emulador en la misma máquina.

Usa la API de exportación del emulador, también usada por Firebase CLI.
No depende del hub local ni exporta datos distintos del fixture.
"""

import argparse
import http.client
import json
from pathlib import Path
from urllib.parse import urlsplit

import seed_demo


def verify_demo(client):
    expected = {
        (collection, key): seed_demo.stored_document(collection, doc)
        for collection, docs in seed_demo.load_fixture().items()
        for key, doc in docs.items()
    }
    actual = {}
    for collection in client.collections():
        # list_documents incluye padres ausentes con subcolecciones.
        for ref in collection.list_documents():
            snapshot = ref.get(timeout=10)
            seed_demo.require(snapshot.exists, "Documento padre ausente: no exportar")
            seed_demo.require(next(ref.collections(), None) is None, "Subcolección ajena al fixture: no exportar")
            actual[(collection.id, ref.id)] = snapshot.to_dict()
    seed_demo.require(actual == expected, "El emulador no contiene exactamente el fixture DEMO: no exportar")
    return len(expected)


def destination(value):
    output = Path(value).expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    seed_demo.require(not output.is_relative_to(repo), "Exportar fuera del repositorio")
    seed_demo.require(not output.exists(), "El destino ya existe; no se sobrescribe")
    seed_demo.require(output.parent.is_dir(), "El directorio padre debe existir")
    return output


def export_demo(output):
    endpoint = urlsplit("//" + seed_demo.emulator_host())
    seed_demo.require(endpoint.hostname in {"localhost", "127.0.0.1", "::1"}, "Exportación requiere emulador en la misma máquina; no servicio Docker remoto")
    output = destination(output)
    client = seed_demo.client_for_emulator()
    try:
        verify_demo(client)
    finally:
        client.close()
    output.mkdir()
    body = json.dumps({
        "database": f"projects/{seed_demo.PROJECT}/databases/(default)",
        "export_directory": str(output),
        "export_name": "firestore_export",
    })
    # HTTP directo SOLO a loopback, sin autenticación ni conexión a Google Cloud.
    connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=30)
    try:
        connection.request("POST", f"/emulator/v1/projects/{seed_demo.PROJECT}:export", body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        response.read()
        seed_demo.require(response.status == 200, f"Exportación del emulador falló: HTTP {response.status}")
    finally:
        connection.close()
    import_path = output / "firestore_export"
    seed_demo.require((import_path / "firestore_export.overall_export_metadata").is_file(), "El emulador no generó metadatos; comprobar que comparte filesystem con este script")
    return import_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Directorio nuevo fuera del repositorio")
    parser.add_argument("--verify-only", action="store_true", help="Solo comprobar los siete documentos, sin crear ni exportar")
    args = parser.parse_args()
    if args.verify_only:
        client = seed_demo.client_for_emulator()
        try:
            print(json.dumps({"verified": verify_demo(client)}))
        finally:
            client.close()
    else:
        if not args.output:
            parser.error("--output es obligatorio para exportar")
        print(json.dumps({"import_path": str(export_demo(args.output))}))


if __name__ == "__main__":
    main()
