"""Run the cold NoSQL suite on NEW dedicated local containers/emulator, then retire them."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', required=True)
    parser.add_argument('--work', type=Path, required=True, help='New directory outside the repository, directly below work/')
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--mongodump', type=Path, required=True)
    parser.add_argument('--mongorestore', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent.parent.parent
    directory = args.work.resolve()
    if directory.parent.name != 'work' or directory.exists() or directory.is_relative_to(repo):
        parser.error('Requiere directorio nuevo directamente bajo work/ y fuera del repositorio')
    for path in (args.jar, args.mongodump, args.mongorestore):
        if not path.resolve().is_file():
            parser.error('JAR/binarios locales ausentes')
    env = os.environ.copy()
    for name in ('DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        env.pop(name, None)
    env['DOCKER_HOST'] = 'unix:///var/run/docker.sock'

    def docker(*argv, check=True):
        return subprocess.run(['docker', *argv], env=env, check=check, capture_output=True, text=True)

    docker('info', '--format', '{{.ServerVersion}}')
    names = ('jennifer-recovery-mongo', 'jennifer-recovery-target')
    for name in names:
        result = docker('inspect', name, check=False)
        if result.returncode == 0:
            parser.error('Nombre de contenedor ocupado; no se modifica ni reemplaza')
        if 'No such object' not in result.stderr and 'No such container' not in result.stderr:
            parser.error('No se pudo verificar ausencia de contenedor')
    for port in (27039, 27049, 8093, 8095):
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                parser.error('Puerto dedicado ocupado; no se modifica el servicio existente')
    directory.mkdir(parents=True, mode=0o700)
    # The test suite generates/cleans its own artifacts here; no backup is versioned.
    (repo.parent / 'work/recovery').mkdir(parents=True, exist_ok=True)
    containers = []
    java = None
    java_log = None
    result = None

    def wait_ready(probe):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            try:
                if probe():
                    return
            except Exception:
                pass
            time.sleep(0.2)
        raise RuntimeError('El servicio dedicado no alcanzó disponibilidad')

    try:
        from pymongo import MongoClient
        import requests
        for name, port, replica in ((names[0], 27039, 'recovery'), (names[1], 27049, 'recoveryTarget')):
            identifier = docker('run', '-d', '--name', name, '--label', 'codex.task=jennifer-recovery',
                                '-p', f'127.0.0.1:{port}:{port}', 'mongo:7', 'mongod', '--replSet', replica,
                                '--bind_ip_all', '--port', str(port)).stdout.strip()
            containers.append(identifier)
            with MongoClient(f'mongodb://127.0.0.1:{port}/?directConnection=true', serverSelectionTimeoutMS=500) as client:
                wait_ready(lambda: client.admin.command('ping')['ok'] == 1)
                client.admin.command('replSetInitiate', {'_id': replica, 'members': [{'_id': 0, 'host': f'127.0.0.1:{port}'}]})
                wait_ready(lambda: client.admin.command('hello').get('isWritablePrimary'))
        java_log = (directory / 'firestore.log').open('w')
        java = subprocess.Popen(['java', '-jar', str(args.jar.resolve()), '--host=127.0.0.1', '--port=8093',
                                 '--project_id=demo-clinical-recovery'], stdout=java_log, stderr=subprocess.STDOUT)
        wait_ready(lambda: java.poll() is None and requests.get('http://127.0.0.1:8093/', timeout=0.5).status_code in {200, 404})
        env.update(RECOVERY_NOSQL_TESTS='1', FIRESTORE_RECOVERY_SOURCE_PID=str(java.pid),
                   FIRESTORE_RECOVERY_JAR=str(args.jar.resolve()), MONGO_DUMP_BIN=str(args.mongodump.resolve()),
                   MONGO_RESTORE_BIN=str(args.mongorestore.resolve()), PYTHONPATH=str(repo / 'backend'))
        with (directory / 'tests.log').open('w') as log:
            result = subprocess.run([sys.executable, '-m', 'unittest', 'apps.historiales.test_recovery_nosql', '-v'],
                                    cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
        source = repo / 'backend/apps/historiales/test_recovery_nosql.py'
        report = {'suite': 'cold-recovery-A3-A4', 'exit_code': result.returncode,
                  'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
                  'test_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    finally:
        if java is not None:
            if java.poll() is None:
                java.terminate()
            java.wait(timeout=15)
        if java_log is not None:
            java_log.close()
        # Validate all owned IDs/mounts before retiring any container. No shared volumes.
        for identifier in containers:
            data = json.loads(docker('inspect', identifier).stdout)[0]
            if data['Config']['Labels'].get('codex.task') != 'jennifer-recovery' or any(
                mount['Type'] != 'volume' or not re.fullmatch('[a-f0-9]{64}', mount.get('Name', '')) for mount in data['Mounts']
            ):
                raise RuntimeError('Limpieza rechazada fuera de recursos desechables propios')
        if containers:
            docker('rm', '--force', '--volumes', *containers)
    print('Recuperación fría: código', result.returncode, '; servicios propios retirados; logs conservados')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
