"""Native one-database Mongo backup/restore, with independent snapshot verification.

Maintenance only. Writers/DDL must be stopped; never restores over existing data.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

from bson import BSON, json_util
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.uri_parser import parse_uri

KIND = 'jennifer-mongo-recovery-1'
REPO = Path(__file__).resolve().parents[2]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def client_for(uri):
    parsed = parse_uri(uri)
    require(all(host in {'localhost', '127.0.0.1', '::1'} for host, _ in parsed['nodelist']), 'Solo destinos Mongo locales explícitos')
    require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,62}', parsed.get('database') or '') is not None, 'Se requiere base explícita con nombre simple')
    return MongoClient(uri, serverSelectionTimeoutMS=3000, timeoutMS=30000)


def capture(db):
    inventory = {row['name']: row for row in db.list_collections() if not row['name'].startswith('system.')}
    require(all(row['type'] == 'collection' and not row.get('options', {}).get('timeseries') for row in inventory.values()), 'Esta recuperación solo admite colecciones normales')
    result = {}
    with db.client.start_session() as session:
        with session.start_transaction(read_concern=ReadConcern('snapshot')):
            for name, info in sorted(inventory.items()):
                rows = [sha256(BSON.encode(doc)).hexdigest() for doc in db[name].find({}, session=session)]
                result[name] = {'count': len(rows), 'documents': sorted(rows), 'options': info.get('options', {}), 'indexes': db[name].index_information()}
    require(set(inventory) == {n for n in db.list_collection_names() if not n.startswith('system.')}, 'Las colecciones cambiaron durante la lectura')
    # Extended JSON retains BSON metadata types; array order retains compound keys.
    return json.loads(json_util.dumps(result, sort_keys=True))


def digest(path):
    h = sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def tool(program, uri, args, directory):
    # URI (including any credentials) is not put on argv or printed by this script.
    with NamedTemporaryFile(mode='w', encoding='utf-8', prefix='.mongo-tools-', suffix='.json', dir=directory) as config:
        json.dump({'uri': uri}, config)
        config.flush()
        result = subprocess.run([str(program), '--config', config.name, *args], capture_output=True)
        require(result.returncode == 0, 'La herramienta Mongo terminó con error; respaldo/restauración no certificados')


def backup(uri, output, *, writers_stopped=False, mongodump='mongodump'):
    require(writers_stopped, 'Detener escritores y DDL antes de exportar')
    output = Path(output).resolve()
    require(not output.is_relative_to(REPO) and not output.exists() and output.parent.is_dir(), 'Usar directorio nuevo fuera del repo con padre existente')
    with client_for(uri) as client:
        db = client.get_default_database()
        before = capture(db)
        output.mkdir(mode=0o700)
        archive = output / 'database.archive.gz'
        tool(mongodump, uri, ['--archive=' + str(archive), '--gzip'], output)
        require(capture(db) == before, 'El origen cambió; respaldo incompleto sin manifiesto de aceptación')
        manifest = {'format': KIND, 'database': db.name, 'collections': before, 'archive_sha256': digest(archive)}
        path = output / 'manifest.json'
        path.write_text(json.dumps(manifest, sort_keys=True), encoding='utf-8')
        path.chmod(0o600)
    return manifest


def read_backup(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest.get('format') == KIND, 'Formato de respaldo incorrecto')
    require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,62}', manifest.get('database', '')) is not None, 'Namespace de respaldo inválido')
    archive = directory / 'database.archive.gz'
    require(not archive.is_symlink() and digest(archive) == manifest['archive_sha256'], 'Respaldo alterado o incompleto')
    return manifest, archive


def restore(uri, directory, *, mongorestore='mongorestore'):
    manifest, archive = read_backup(directory)
    with client_for(uri) as client:
        db = client.get_default_database()
        require(db.name != manifest['database'] and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*_recovery_[a-f0-9]{32}', db.name) is not None, 'Restaurar únicamente a una base nueva *_recovery_<uuid>')
        require(not db.list_collection_names(), 'El destino contiene datos/colecciones; no se sobrescribe')
        server_uri = urlsplit(uri)._replace(path='/').geturl()
        tool(mongorestore, server_uri, ['--archive=' + str(archive), '--gzip', '--nsInclude=' + manifest['database'] + '.*', '--nsFrom=' + manifest['database'] + '.*', '--nsTo=' + db.name + '.*', '--stopOnError'], archive.parent)
        require(capture(db) == manifest['collections'], 'Documentos/validadores/índices recuperados no coinciden')
        return {'verified_collections': len(manifest['collections']), 'verified_documents': sum(c['count'] for c in manifest['collections'].values())}


if __name__ == '__main__':
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'restore', 'verify-archive'])
    parser.add_argument('--directory', required=True)
    parser.add_argument('--writers-stopped', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'backup':
            result = backup(os.environ['MONGO_RECOVERY_URI'], args.directory, writers_stopped=args.writers_stopped)
            print(json.dumps({'collections': len(result['collections']), 'backup_complete': True}))
        elif args.action == 'restore':
            print(json.dumps(restore(os.environ['MONGO_RECOVERY_URI'], args.directory)))
        else:
            read_backup(args.directory)
            print('Archive SHA-256 verificado')
    except Exception as error:
        raise SystemExit('Recuperación no certificada: ' + type(error).__name__) from None
