"""Native export of the app's flat Firestore models and post-import verification.

Emulator only, local filesystem, stopped writers. Does not seed or overwrite data.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import http.client
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore
from google.api_core.datetime_helpers import DatetimeWithNanoseconds

KIND = 'jennifer-firestore-recovery-1'
REPO = Path(__file__).resolve().parents[2]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def local_client(project):
    endpoint = os.environ.get('FIRESTORE_EMULATOR_HOST', '')
    parsed = urlsplit('//' + endpoint)
    require(parsed.hostname in {'127.0.0.1', 'localhost', '::1'} and parsed.port is not None, 'Se requiere emulador local explícito')
    require(re.fullmatch(r'demo-[a-z0-9-]{1,50}', project) is not None, 'Solo proyectos emulados demo-')
    return firestore.Client(project=project, credentials=AnonymousCredentials())


def tagged(value):
    if value is None: return ['null']
    if isinstance(value, bool): return ['bool', value]
    if isinstance(value, int): return ['int', str(value)]
    if isinstance(value, float): return ['float', value.hex()]
    if isinstance(value, str): return ['str', value]
    if isinstance(value, bytes): return ['bytes', value.hex()]
    if isinstance(value, datetime):
        instant = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return ['time', DatetimeWithNanoseconds.from_rfc3339(instant.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')).rfc3339() if not isinstance(value, DatetimeWithNanoseconds) else value.rfc3339()]
    if isinstance(value, firestore.DocumentReference): return ['reference', value._document_path]
    if isinstance(value, firestore.GeoPoint): return ['point', tagged(value.latitude), tagged(value.longitude)]
    if isinstance(value, dict): return ['map', [[key, tagged(v)] for key, v in sorted(value.items())]]
    if isinstance(value, list): return ['array', [tagged(v) for v in value]]
    raise ValueError('Tipo Firestore no soportado en verificación; no se omite')


def capture(client):
    collections = sorted(c.id for c in client.collections())
    # Current A1/A3 models are flat. Never silently ignore nested/ghost documents.
    refs = {}
    for name in collections:
        refs[name] = list(client.collection(name).list_documents())
        for ref in refs[name]:
            require(next(ref.collections(), None) is None, 'Subcolecciones fuera del modelo; exportación rechazada')
    @firestore.transactional
    def read(tx):
        result = {}
        for name in collections:
            docs = client.collection(name).get(transaction=tx, timeout=15)
            require({d.id for d in docs} == {r.id for r in refs[name]}, 'Padres ausentes o documentos cambiaron durante inventario')
            hashes = [sha256(json.dumps(tagged({'id': d.id, 'data': d.to_dict()}), ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest() for d in docs]
            result[name] = {'count': len(docs), 'documents': sorted(hashes)}
        return result
    result = read(client.transaction(read_only=True))
    require(collections == sorted(c.id for c in client.collections()), 'El inventario cambió durante lectura')
    return result


def digest(path):
    h = sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def backup(project, output, *, writers_stopped=False):
    require(writers_stopped, 'Detener escritores antes de exportar')
    output = Path(output).resolve()
    require(not output.is_relative_to(REPO) and not output.exists() and output.parent.is_dir(), 'Usar directorio nuevo fuera del repo')
    client = local_client(project)
    try:
        before = capture(client)
        output.mkdir(mode=0o700)
        endpoint = urlsplit('//' + os.environ['FIRESTORE_EMULATOR_HOST'])
        connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=30)
        try:
            body = json.dumps({'database': f'projects/{project}/databases/(default)', 'export_directory': str(output), 'export_name': 'firestore_export'})
            connection.request('POST', f'/emulator/v1/projects/{project}:export', body, {'Content-Type': 'application/json'})
            response = connection.getresponse(); response.read()
            require(response.status == 200, 'Exportación nativa falló')
        finally: connection.close()
        require(capture(client) == before, 'Origen cambió; exportación sin manifiesto de aceptación')
        metadata = output / 'firestore_export/firestore_export.overall_export_metadata'
        require(metadata.is_file(), 'Emulador y exportador deben compartir filesystem')
        files = {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}
        manifest = {'format': KIND, 'project': project, 'collections': before, 'files': files}
        path = output / 'manifest.json'; path.write_text(json.dumps(manifest, sort_keys=True), encoding='utf-8'); path.chmod(0o600)
        return metadata
    finally: client.close()


def read_backup(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest.get('format') == KIND and 'firestore_export/firestore_export.overall_export_metadata' in manifest.get('files', {}), 'Formato de respaldo incorrecto')
    for relative, expected in manifest['files'].items():
        raw = directory / relative
        require(not raw.is_symlink() and raw.resolve().is_relative_to(directory), 'Ruta de archivo fuera del respaldo')
        require(digest(raw) == expected, 'Exportación alterada o incompleta')
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    require(actual == set(manifest['files']), 'Archivos inesperados en respaldo')
    return manifest, directory / 'firestore_export/firestore_export.overall_export_metadata'


def verify_restored(project, directory):
    manifest, _ = read_backup(directory)
    require(project == manifest['project'], 'Restaurar el mismo proyecto en un emulador NUEVO')
    client = local_client(project)
    try:
        require(capture(client) == manifest['collections'], 'La recuperación no coincide con el respaldo')
        return {'verified_collections': len(manifest['collections']), 'verified_documents': sum(c['count'] for c in manifest['collections'].values())}
    finally: client.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['backup', 'verify-archive', 'verify-restored'])
    p.add_argument('--project', required=True)
    p.add_argument('--directory', required=True)
    p.add_argument('--writers-stopped', action='store_true')
    a = p.parse_args()
    try:
        if a.action == 'backup':
            print(json.dumps({'metadata': str(backup(a.project, a.directory, writers_stopped=a.writers_stopped))}))
        elif a.action == 'verify-restored': print(json.dumps(verify_restored(a.project, a.directory)))
        else:
            read_backup(a.directory); print('Exportación SHA-256 verificada')
    except Exception as error:
        raise SystemExit('Recuperación no certificada: ' + type(error).__name__) from None
