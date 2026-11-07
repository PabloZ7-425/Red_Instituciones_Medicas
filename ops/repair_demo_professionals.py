"""Inspect or create only a missing native professional for an existing DEMO account."""
import argparse
import os

from bootstrap_professionals import ensure_native_professional


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--institution', choices=['laboratorio', 'odontologica'], required=True)
    parser.add_argument('--apply', action='store_true', help='Create the missing native DEMO record')
    args = parser.parse_args()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from apps.identidad.models import PerfilInstitucional

    profile = PerfilInstitucional.objects.select_related('usuario', 'profesional').get(
        usuario__username='DEMO-PABLO-' + args.institution,
    )
    if (profile.institucion != args.institution or profile.rol != 'admin' or not profile.activo
            or not profile.usuario.is_active or profile.usuario.is_staff or profile.usuario.is_superuser
            or profile.profesional is None or not profile.profesional.habilitado
            or profile.profesional.institucion != args.institution
            or profile.profesional.referencia_externa != 'DEMO-PABLO-PRO'):
        raise RuntimeError('El perfil DEMO no cumple los requisitos; no se modifica')

    def verify(read, create):
        missing = False

        def create_if_requested(identifier, row):
            nonlocal missing
            missing = True
            if args.apply:
                create(identifier, row)

        ensure_native_professional(args.institution, read, create_if_requested)
        result = ('created' if args.apply else 'missing; rerun with --apply') if missing else 'valid; unchanged'
        print(args.institution + ': ' + result)

    if args.institution == 'laboratorio':
        from pymongo import MongoClient
        with MongoClient(os.environ['MONGO_URI'], serverSelectionTimeoutMS=3000) as client:
            database = client.get_default_database()
            if 'clinico_profesionales_operativos' not in database.list_collection_names():
                raise RuntimeError('Prepara primero el esquema operativo de Mongo; no se crea una colección sin validar')
            collection = database.clinico_profesionales_operativos
            verify(lambda key: collection.find_one({'_id': key}),
                   lambda key, row: collection.insert_one({'_id': key, **row}))
    else:
        if os.getenv('FIRESTORE_MODE', 'emulator') != 'emulator' or not os.getenv('FIRESTORE_EMULATOR_HOST'):
            raise RuntimeError('La reparación DEMO requiere el emulador local de Firestore')
        from apps.historiales.infrastructure.adapters.firestore_adapter import FirestoreAdapter
        client = FirestoreAdapter()._client()
        try:
            def read(key):
                snapshot = client.collection('profesionales_operativos').document(key).get(timeout=10)
                return snapshot.to_dict() if snapshot.exists else None
            verify(read, lambda key, row: client.collection('profesionales_operativos').document(key).create(row))
        finally:
            client.close()


if __name__ == '__main__':
    main()
