"""Copy identity into hospital.identidad; preserve source and verify complete fixture.

Stop the backend before running. Requires pre-existing verified source backups and
an empty migrated destination. Private checkpoint includes hashes and sessions.
"""
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4


def main():
    if os.getenv('AUC12_SETUP') != 'consolidate-identity':
        raise RuntimeError('Explicit consolidation flag required')
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    from django.conf import settings
    from django.core import serializers
    from django.core.management import call_command
    from django.db import connections, transaction
    from django.apps import apps
    target_alias = 'identity_migration'
    target = connections[target_alias]
    if settings.IDENTITY_DB_MODE != 'postgres' or os.getenv('IDENTITY_DB_SCHEMA') != 'identidad':
        raise RuntimeError('Destination must use PostgreSQL identity schema')
    source_config = dict(connections['default'].settings_dict)
    source_config.update(HOST=os.getenv('IDENTITY_SOURCE_HOST', 'identidad'),
                         PORT=os.getenv('IDENTITY_SOURCE_PORT', '5432'),
                         NAME=os.getenv('IDENTITY_SOURCE_NAME', 'identidad'),
                         OPTIONS={'connect_timeout': 3, 'options': '-c search_path=public'})
    if (source_config['HOST'], source_config['PORT'], source_config['NAME']) == (
            target.settings_dict['HOST'], target.settings_dict['PORT'], target.settings_dict['NAME']):
        raise RuntimeError('Source and destination must be separate databases')
    connections.databases['identity_source'] = source_config
    models = [apps.get_model(label) for label in (
        'auth.Group', 'auth.User', 'identidad.Profesional',
        'identidad.PerfilInstitucional', 'sessions.Session', 'admin.LogEntry')]

    def snapshot(alias):
        objects = (obj for model in models for obj in model.objects.using(alias).order_by('pk'))
        return serializers.serialize('json', objects, use_natural_foreign_keys=True)

    def digest(payload):
        return hashlib.sha256(json.dumps(json.loads(payload), sort_keys=True).encode()).hexdigest()

    with transaction.atomic(using='identity_source'):
        with connections['identity_source'].cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        payload = snapshot('identity_source')
        directory = Path(os.getenv('AUC12_BACKUP_DIR', '/backups')) / ('consolidation-' + uuid4().hex)
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        fixture = directory / 'identity-private.json'
        with open(fixture, 'x', opener=lambda p, f: os.open(p, f, 0o600)) as handle:
            handle.write(payload)
        with transaction.atomic(using=target_alias):
            with target.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(120012, 4)')
                cursor.execute('LOCK TABLE auth_group,auth_user,identidad_profesional,identidad_perfilinstitucional,django_session,django_admin_log IN ACCESS EXCLUSIVE MODE')
            current = snapshot(target_alias)
            if json.loads(current):
                if digest(current) != digest(payload):
                    raise RuntimeError('Destination contains different identities; nothing overwritten')
                print('OK identity already matches; no rows changed')
            else:
                call_command('loaddata', str(fixture), database=target_alias, verbosity=0)
                if digest(snapshot(target_alias)) != digest(payload):
                    raise RuntimeError('Identity verification failed; destination rolled back')
            # Source stays untouched. No generated accounts or password resets.
            count = len(json.loads(payload))
        report = {'source_preserved': True, 'verified': True, 'records': count,
                  'sha256': digest(payload), 'destination': 'hospital.identidad'}
        (directory / 'report.json').write_text(json.dumps(report, indent=2))
    print('OK identity copied and reconciled: ' + str(count) + ' records; source preserved')
    print('Private checkpoint stored under /backups; do not share identity-private.json')


if __name__ == '__main__':
    main()
