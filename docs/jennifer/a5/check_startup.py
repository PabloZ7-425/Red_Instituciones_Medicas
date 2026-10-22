"""Read-only clinical startup checks; no migrations, seeds, login or clinical writes."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, help='Optional prepared disposable A5 copy')
    parser.add_argument('--backend-root', type=Path, help='Backend source directory when mounted separately')
    parser.add_argument('--mongo-schema', type=Path, help='Read-only clinical_schema.py source when mounted separately')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent.parent.parent
    if args.runtime:
        root = args.runtime.resolve()
        if root.name != 'a5-runtime' or root.parent.name != 'work':
            parser.error('Solo copia dedicada work/a5-runtime')
        os.environ.update(json.loads((root / 'server.json').read_text()))
        sys.path[:0] = [str(root), str(root / 'backend')]
    else:
        sys.path.insert(0, str(args.backend_root or repo / 'backend'))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.conf import settings
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor
    from apps.historiales.domain.context import ContextoClinico
    from apps.historiales.infrastructure.factory import AdapterFactory
    from apps.identidad.models import PerfilInstitucional

    results = []

    def check(name, action):
        try:
            ok = bool(action())
        except Exception:
            # Driver/SDK messages can contain hosts, credentials or clinical data.
            ok = False
        results.append({'check': name, 'ok': ok})

    check('identidad_postgres', lambda: settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql')

    def migrated():
        executor = MigrationExecutor(connections['default'])
        return not executor.migration_plan(executor.loader.graph.leaf_nodes())

    check('identidad_migraciones_aplicadas', migrated)
    for institution in ('hospital', 'pediatrico', 'laboratorio', 'odontologica'):
        # A synthetic read-only context probes the native repositories, not HTTP auth.
        adapter = None
        try:
            adapter = AdapterFactory.create_clinical(ContextoClinico(institution, 'startup-read-only', 'admin'))
        except Exception:
            pass
        check(institution + '_lectura_clinica', lambda: adapter is not None and isinstance(adapter.listar_pacientes(limit=1)['count'], int))
        check(institution + '_catalogo_no_vacio', lambda: adapter is not None and adapter.listar_medicamentos(limit=1)['count'] > 0)
        check(institution + '_cuenta_clinica_habilitada', lambda: PerfilInstitucional.objects.filter(
            institucion=institution, activo=True, usuario__is_active=True,
            rol__in=['admin', 'medico'], profesional__institucion=institution,
            profesional__habilitado=True,
        ).exclude(profesional__referencia_externa='').exists())

    def mongo_schema():
        import importlib.util
        from pymongo import MongoClient
        spec = importlib.util.spec_from_file_location('startup_schema', args.mongo_schema or repo / 'db/mongo/clinical_schema.py')
        schema = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema)
        with MongoClient(os.environ['MONGO_URI'], serverSelectionTimeoutMS=3000) as client:
            hello = client.admin.command('hello')
            if not hello.get('setName') or not hello.get('isWritablePrimary'):
                return False
            db = client.get_default_database()
            for name in schema.TEXTS:
                collection = db['clinico_' + name]
                options = collection.options()
                if (options.get('validator') != schema.validator(name)
                        or options.get('validationLevel', 'strict') != 'strict'
                        or options.get('validationAction', 'error') != 'error'):
                    return False
                expected = [[('institucion', 1), ('schema_version', 1)]]
                if name in ('consultas', 'diagnosticos', 'tratamientos', 'recetas'):
                    expected.append([('institucion', 1), ('paciente_id', 1)])
                indexes = list(collection.list_indexes())
                if any(not any(list(index['key'].items()) == key for index in indexes) for key in expected):
                    return False
                if name == 'pacientes' and not any(
                    list(index['key'].items()) == [('institucion', 1), ('identificacion', 1)]
                    and index.get('unique') and not index.get('partialFilterExpression')
                    and not index.get('sparse') for index in indexes
                ):
                    return False
            return True

    check('mongo_replica_validadores_indices_v2', mongo_schema)
    connections.close_all()
    print(json.dumps({'ready': all(row['ok'] for row in results), 'checks': results}, indent=2))
    return 0 if all(row['ok'] for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
