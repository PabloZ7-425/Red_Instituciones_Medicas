"""Repeatable demo catalogs through application validation; never updates existing rows."""
import os


def load_catalogs(repo):
    counts = {'created': 0, 'preserved': 0}

    def ensure(name, values, keys):
        matches = []
        offset = 0
        while True:
            page = repo.page(name, limit=100, offset=offset)
            matches.extend(row for row in page['results']
                           if all(row['values'].get(key) == values[key] for key in keys))
            offset += 100
            if offset >= page['count']:
                break
        if len(matches) > 1:
            raise RuntimeError('Duplicate demo catalog: ' + name)
        if matches:
            counts['preserved'] += 1
            return matches[0]['id']
        identifier = repo.save(name, values)['id']
        counts['created'] += 1
        return identifier

    def named(name, values, key='nombre'):
        return ensure(name, values, [key])

    if repo.hospital:
        named('especialidad', {'nombre': 'PRUEBA Medicina general', 'nivel_complejidad': 1, 'activo_operativo': True})
        named('enfermero', {'nombre_completo': 'PRUEBA Enfermeria', 'licencia_enfermeria': 'PRUEBA-AUC12-ENF', 'activo_operativo': True}, 'licencia_enfermeria')
        pavilion = named('pabellon_edificio', {'nombre_pabellon': 'PRUEBA Pabellon', 'activo_operativo': True}, 'nombre_pabellon')
        room = ensure('habitacion', {'id_pabellon': pavilion, 'numero_habitacion': 'PRUEBA-101', 'tipo_atencion': 'Demostracion', 'activo_operativo': True}, ['id_pabellon', 'numero_habitacion'])
        for number in (1, 2):
            named('cama', {'id_habitacion': room, 'codigo_cama': 'PRUEBA-CAMA-' + str(number), 'estado_limpieza': 'limpia', 'activo_operativo': True}, 'codigo_cama')
        named('quirofano', {'id_pabellon': pavilion, 'nombre_sala': 'PRUEBA Quirofano', 'activo_operativo': True}, 'nombre_sala')
        for number in (1, 2):
            named('medicamento', {'nombre_comercial': 'PRUEBA Medicamento ' + str(number), 'principio_activo': 'Simulado, sin uso clinico', 'presentacion': 'Demostracion', 'stock_farmacia': 100, 'activo_operativo': True}, 'nombre_comercial')
    elif repo.context.institucion == 'pediatrico':
        named('especialidad', {'nombre': 'PRUEBA Pediatria', 'activo_operativo': True})
        named('vacuna', {'nombre': 'PRUEBA Vacuna simulada', 'descripcion': 'Solo demostracion; sin uso clinico', 'numero_dosis': 2, 'activo_operativo': True})
        for number in (1, 2):
            named('medicamento', {'nombre': 'PRUEBA Medicamento ' + str(number), 'presentacion': 'Demostracion', 'concentracion': 'Simulada', 'estado': 'activo'})
        named('tipo_examen', {'nombre': 'PRUEBA Examen simulado', 'area': 'Demostracion', 'activo_operativo': True})
        service = named('servicio_medico', {'codigo': 'PRUEBA-CONSULTA', 'nombre': 'PRUEBA Consulta', 'precio_base': '100.00', 'tipo_servicio': 'consulta', 'estado': 'activo'}, 'codigo')
        insurer = named('aseguradora', {'nombre': 'PRUEBA Aseguradora', 'estado': 'activo'})
        plan = ensure('plan_seguro', {'aseguradora_id': insurer, 'nombre': 'PRUEBA Plan', 'deducible': '0.00', 'limite_anual': '10000.00', 'estado': 'activo'}, ['aseguradora_id', 'nombre'])
        ensure('cobertura_servicio', {'plan_seguro_id': plan, 'servicio_id': service, 'porcentaje_cobertura': '80.00', 'copago': '20.00', 'limite_eventos': 10, 'requiere_autorizacion': False, 'estado': 'activo'}, ['plan_seguro_id', 'servicio_id'])
        named('metodo_pago', {'nombre': 'PRUEBA Efectivo', 'estado': 'activo'})
    else:
        for number in (1, 2):
            named('medicamento', {'nombre': 'PRUEBA Medicamento ' + str(number), 'presentacion': 'Simulado, sin uso clinico', 'activo': True})
        if repo.context.institucion == 'laboratorio':
            named('tipo_examen', {'nombre': 'PRUEBA Examen simulado', 'activo': True})
    return counts


def main():
    if os.getenv('AUC12_SETUP') != 'seed-demo-catalogs':
        raise RuntimeError('Set AUC12_SETUP=seed-demo-catalogs explicitly')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from apps.historiales.domain.context import ContextoClinico
    from apps.operaciones.repository import OperationsRepository
    for institution in ('hospital', 'pediatrico', 'laboratorio', 'odontologica'):
        repo = OperationsRepository(ContextoClinico(institution, 'auc12-demo-catalogs', 'admin'))
        counts = load_catalogs(repo)
        print('OK ' + institution + ': ' + str(counts), flush=True)
    print('Demo catalogs ready. No patients, accounts or clinical events created. Existing rows preserved.')


if __name__ == '__main__':
    main()
