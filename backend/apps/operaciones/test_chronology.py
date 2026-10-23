"""AUC-05: partial edits must preserve the complete stored interval."""
from datetime import date, datetime
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.historiales.domain.context import ContextoClinico
from apps.historiales.domain.errors import Conflicto, DatosInvalidos
from apps.operaciones.catalog import RESOURCES, validate, validate_chronology
from apps.operaciones.repository import OperationsRepository, token


class ChronologyTests(SimpleTestCase):
    def test_all_declared_intervals_reject_reversed_dates(self):
        pairs = [('fecha_inicio', 'fecha_fin'), ('fecha_solicitud', 'fecha_respuesta'),
                 ('fecha_envio', 'fecha_resolucion'), ('fecha_hora_inicio', 'fecha_hora_fin')]
        for institution, resources in RESOURCES.items():
            for name, spec in resources.items():
                for start, end in pairs:
                    if start not in spec['fields'] or end not in spec['fields']:
                        continue
                    with self.subTest(institution=institution, resource=name):
                        suffix = 'T12:00:00Z' if spec['fields'][start]['type'] == 'datetime' else ''
                        with self.assertRaises(DatosInvalidos) as caught:
                            validate_chronology(spec, {start: '2026-02-02'+suffix, end: '2026-02-01'+suffix})
                        self.assertIn(end, caught.exception.fields)

    def policy_repository(self):
        repo = object.__new__(OperationsRepository)
        repo.context = ContextoClinico('pediatrico', 'audit', 'admin', '1')
        repo.specs = RESOURCES['pediatrico']
        repo.sql = True
        repo.hospital = False
        old = {'id': 1, 'paciente_id': 2, 'plan_seguro_id': 3, 'numero_poliza': 'DEMO',
               'estado': 'activo', 'fecha_inicio': date(2026, 1, 1), 'fecha_fin': date(2026, 12, 31)}
        cursor = Mock()
        repo.core = Mock()
        repo._run = lambda operation: operation(cursor)
        repo._get = Mock(side_effect=lambda unit, name, number, **kw: old if name == 'poliza_paciente' else {})
        repo._owner = Mock(return_value=None)
        return repo, old, cursor

    def test_patch_one_or_both_ends_rejects_before_any_write(self):
        for changes in [{'fecha_fin': '2025-12-31'}, {'fecha_inicio': '2027-01-01'},
                        {'fecha_inicio': '2027-01-01', 'fecha_fin': '2026-01-01'}]:
            with self.subTest(changes=changes):
                repo, old, cursor = self.policy_repository()
                with self.assertRaises(DatosInvalidos):
                    repo.save('poliza_paciente', changes, identifier='PED-OP_poliza_paciente-1', version=token(old))
                cursor.execute.assert_not_called()
                repo.core._after_write.assert_not_called()

    def test_valid_partial_both_equal_and_optional_null_updates(self):
        for changes in [{'fecha_fin': '2027-01-01'}, {'fecha_inicio': '2026-02-01'},
                        {'fecha_inicio': '2027-01-01', 'fecha_fin': '2027-12-31'},
                        {'fecha_inicio': '2026-12-31'}, {'fecha_fin': None}, {'fecha_inicio': None}]:
            with self.subTest(changes=changes):
                repo, old, cursor = self.policy_repository()
                repo.save('poliza_paciente', changes, identifier='PED-OP_poliza_paciente-1', version=token(old))
                self.assertTrue(cursor.execute.call_args.args[0].startswith('UPDATE poliza_paciente'))
                args = cursor.execute.call_args.args[1]
                self.assertEqual(args[-3:-1], [changes.get('fecha_inicio', '2026-01-01'), changes.get('fecha_fin', '2026-12-31')])
                repo.core._after_write.assert_called_once_with(cursor)

    def test_stale_version_still_rejects_before_writing(self):
        repo, old, cursor = self.policy_repository()
        with self.assertRaises(Conflicto):
            repo.save('poliza_paciente', {'fecha_fin': None}, identifier='PED-OP_poliza_paciente-1', version='stale')
        cursor.execute.assert_not_called()

    def test_datetime_compares_instants_and_stored_sql_precision(self):
        spec = RESOURCES['hospital']['cirugia']
        # Different offsets and fractional precision must compare chronologically.
        validate_chronology(spec, {'fecha_hora_inicio': '2026-01-01T12:00:00Z',
                                   'fecha_hora_fin': '2026-01-01T07:00:00-06:00'})
        validate_chronology(spec, {'fecha_hora_inicio': '2026-01-01T12:00:00Z',
                                   'fecha_hora_fin': '2026-01-01T12:00:00.000001Z'})
        repo, old, cursor = self.policy_repository()
        repo.context = ContextoClinico('hospital', 'audit', 'admin', '1')
        repo.specs = RESOURCES['hospital']
        repo.hospital = True
        old.clear()
        old.update(id_cirugia=1, fecha_hora_inicio=datetime(2026, 1, 2, 12), fecha_hora_fin=datetime(2026, 1, 3, 12))
        repo._get = Mock(return_value=old)
        with self.assertRaises(DatosInvalidos):
            repo.save('cirugia', {'fecha_hora_fin': '2026-01-01T12:00:00Z'}, identifier='H-OP_cirugia-1', version=token(old))
        cursor.execute.assert_not_called()

    def test_create_rejects_reversed_interval_and_keeps_field_validation(self):
        spec = RESOURCES['pediatrico']['poliza_paciente']
        values = {'paciente_id': 'PED-P-1', 'plan_seguro_id': 'PED-OP_plan_seguro-1',
                  'numero_poliza': 'DEMO', 'estado': 'activo',
                  'fecha_inicio': '2026-02-01', 'fecha_fin': '2026-01-01'}
        with self.assertRaises(DatosInvalidos):
            validate(spec, values)
        with self.assertRaises(DatosInvalidos):
            validate(spec, {'fecha_fin': '2026-02-30'}, partial=True)
