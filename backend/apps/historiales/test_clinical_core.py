from datetime import date
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from apps.historiales.application.clinical import HistorialService
from apps.historiales.application.validation import validar_dto, validar_paginacion, validar_query
from apps.historiales.domain.context import ContextoClinico, ROLES, autorizar
from apps.historiales.domain.errors import (
    AccesoDenegado, Conflicto, DatosInvalidos, NoAutenticado,
    PersistenciaNoDisponible, RecursoNoEncontrado,
)
from apps.historiales.domain.institutions import Institution
from apps.historiales.domain.ports import DatabaseAdapter, HistorialRepository, MedicamentoCatalogo
from apps.historiales.infrastructure.factory import AdapterFactory
from apps.historiales.presentation.errors import error_response
from apps.historiales.testing.memory import MemoryHarness
from apps.historiales.testing.repository_contract import PACIENTE, CONSULTA, DIAGNOSTICO, TRATAMIENTO


class ValidationTests(TestCase):
    def test_http_query_preserves_and_rejects_repetitions_unknown_and_non_integers(self):
        for pairs in ([('q', 'x'), ('q', 'y')], [('motor', 'mongo')], [('limit', '1.0')],
                      [('offset', '-1')], [('limit', '0')], [('offset', '9' * 100)]):
            with self.subTest(pairs=pairs), self.assertRaises(DatosInvalidos):
                validar_query(pairs)
        self.assertEqual(validar_query([('q', ' Pac '), ('limit', '2')]), {'q': 'pac', 'limit': 2, 'offset': 0})

    def test_valid_dtos_trim_optional_and_preserve_opaque_ids(self):
        self.assertEqual(validar_dto("paciente", PACIENTE | {"nombres": " Pablo "})["nombres"], "Pablo")
        self.assertNotIn("cita_id", validar_dto("consulta", CONSULTA))
        self.assertEqual(validar_dto("consulta", CONSULTA | {"cita_id": " opaque "})["cita_id"], " opaque ")
        self.assertEqual(validar_dto("archivo", {"estado": "archivado", "motivo": " Baja "})["motivo"], "Baja")

    def test_reject_unknown_generated_and_identity_fields(self):
        for field in ("motor", "institucion", "usuario_id", "medico_id", "id", "estado", "extra"):
            with self.subTest(field=field), self.assertRaises(DatosInvalidos):
                validar_dto("paciente", PACIENTE | {field: "DEMO"})

    def test_reject_non_objects_and_invalid_fields(self):
        for body in (None, [], "text", 1, True, {}, PACIENTE | {"nombres": None},
                     PACIENTE | {"nombres": " "}, PACIENTE | {"identificacion": 123},
                     PACIENTE | {"apellidos": "a" * 101}):
            with self.subTest(body=body), self.assertRaises(DatosInvalidos) as raised:
                validar_dto("paciente", body)
            self.assertTrue(raised.exception.fields)

    def test_dates_are_strict_civil_non_future(self):
        for value in ("2026-02-30", "2026-1-01", "20260101", "2026-01-01T00:00:00Z", "2026-10-22"):
            with self.subTest(value=value), self.assertRaises(DatosInvalidos):
                validar_dto("consulta", CONSULTA | {"fecha": value}, today=date(2026, 10, 21))
        self.assertEqual(validar_dto("consulta", CONSULTA | {"fecha": "2024-02-29"}, today=date(2026, 1, 1))["fecha"], "2024-02-29")

    def test_each_schema_rejects_required_null_and_excess_length(self):
        examples = {"paciente": PACIENTE, "consulta": CONSULTA, "diagnostico": DIAGNOSTICO,
                    "tratamiento": TRATAMIENTO,
                    "receta": {"medicamento_id": "M", "dosis": "D", "frecuencia": "F"},
                    "archivo": {"estado": "archivado", "motivo": "DEMO"}}
        for schema, example in examples.items():
            for field in example:
                for value in (None, "", 1, [], {}):
                    with self.subTest(schema=schema, field=field, value=value), self.assertRaises(DatosInvalidos):
                        validar_dto(schema, example | {field: value})
        for kind, dto, field, maximum in (("paciente", PACIENTE, "identificacion", 20),
                                         ("consulta", CONSULTA, "notas_evolucion", 5000),
                                         ("diagnostico", DIAGNOSTICO, "descripcion", 5000),
                                         ("tratamiento", TRATAMIENTO, "indicaciones_generales", 5000)):
            self.assertEqual(len(validar_dto(kind, dto | {field: "a" * maximum})[field]), maximum)
            with self.assertRaises(DatosInvalidos):
                validar_dto(kind, dto | {field: "a" * (maximum+1)})
        for field in ("cita_id",):
            with self.assertRaises(DatosInvalidos):
                validar_dto("consulta", CONSULTA | {field: None})
        with self.assertRaises(DatosInvalidos):
            validar_dto("archivo", {"estado": "activo", "motivo": "DEMO"})

    def test_pagination_rejects_bool_float_string_and_invalid_bounds(self):
        for field, values in (("limit", (0, 101, True, 1.0, "20", None)),
                              ("offset", (-1, False, 0.0, "0", None)),
                              ("q", (None, 1, "a" * 101))):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(DatosInvalidos):
                    validar_paginacion(**{field: value})
        self.assertEqual(validar_paginacion(q=" A\u0301%_ ", limit=100, offset=0), {"q": "á%_", "limit": 100, "offset": 0})


class ContextAndServiceTests(TestCase):
    def test_invalid_context(self):
        for fields, error in (({"usuario_id": ""}, NoAutenticado), ({"usuario_id": 12}, NoAutenticado),
                              ({"institucion": "mysql"}, AccesoDenegado), ({"institucion": []}, AccesoDenegado),
                              ({"rol": "root"}, AccesoDenegado), ({"profesional_id": " "}, AccesoDenegado),
                              ({"rol": "laboratorista"}, AccesoDenegado)):
            with self.subTest(fields=fields), self.assertRaises(error):
                ContextoClinico(**({"institucion": "hospital", "usuario_id": "U", "rol": "admin"} | fields))
        with self.assertRaises(NoAutenticado):
            HistorialService(None, Mock())

    def test_entire_role_matrix_before_resource_lookup(self):
        allowed = {"listar_pacientes": ROLES, "registrar_paciente": {"admin", "medico", "secretaria", "laboratorista"},
                   "obtener_historial": {"admin", "medico", "enfermero", "laboratorista"},
                   "registrar_consulta": {"admin", "medico", "laboratorista"},
                   "registrar_diagnostico": {"admin", "medico"}, "registrar_tratamiento": {"admin", "medico"},
                   "registrar_receta": {"admin", "medico"}, "archivar_paciente": {"admin"},
                   "listar_medicamentos": {"admin", "medico"}}
        arguments = {"listar_pacientes": (), "registrar_paciente": (PACIENTE,), "obtener_historial": ("missing",),
                     "registrar_consulta": ("missing", CONSULTA), "registrar_diagnostico": ("missing", DIAGNOSTICO),
                     "registrar_tratamiento": ("missing", TRATAMIENTO),
                     "registrar_receta": ("missing", {"medicamento_id": "M", "dosis": "D", "frecuencia": "F"}),
                     "archivar_paciente": ("missing", "DEMO"), "listar_medicamentos": ()}
        for role in ROLES:
            ctx = ContextoClinico("laboratorio" if role == "laboratorista" else "hospital", "U", role, "PRO")
            for operation in allowed:
                repo = Mock()
                service = HistorialService(ctx, repo, repo)
                with self.subTest(role=role, operation=operation):
                    if role in allowed[operation]:
                        getattr(service, operation)(*arguments[operation])
                        self.assertEqual(len(repo.mock_calls), 1)
                    else:
                        with self.assertRaises(AccesoDenegado):
                            getattr(service, operation)(*arguments[operation])
                        self.assertEqual(repo.mock_calls, [])

    def test_professional_required_for_all_clinical_writes_including_admin(self):
        for role in ("admin", "medico", "laboratorista"):
            ctx = ContextoClinico("laboratorio", "U", role)
            for operation in ("registrar_consulta", "registrar_diagnostico", "registrar_tratamiento", "registrar_receta"):
                with self.subTest(role=role, operation=operation), self.assertRaises(AccesoDenegado):
                    autorizar(ctx, operation)

    def test_invalid_input_does_not_call_repository(self):
        repo = Mock()
        service = HistorialService(ContextoClinico("hospital", "U", "admin", "P"), repo)
        with self.assertRaises(DatosInvalidos):
            service.registrar_consulta("P", CONSULTA | {"medico_id": "arbitrary"})
        with self.assertRaises(DatosInvalidos):
            service.obtener_historial(123)
        self.assertEqual(repo.mock_calls, [])

    def test_missing_catalog_is_unavailable(self):
        with self.assertRaises(PersistenciaNoDisponible):
            HistorialService(ContextoClinico("hospital", "U", "medico"), Mock()).listar_medicamentos()

    def test_error_mapping_never_exposes_unexpected_exception(self):
        for error, status, code in ((DatosInvalidos, 400, "VALIDATION_ERROR"), (NoAutenticado, 401, "UNAUTHORIZED"),
                                    (AccesoDenegado, 403, "FORBIDDEN"), (RecursoNoEncontrado, 404, "NOT_FOUND"),
                                    (Conflicto, 409, "CONFLICT"), (PersistenciaNoDisponible, 503, "SERVICE_UNAVAILABLE")):
            number, body = error_response(error())
            self.assertEqual((number, body["error"]["code"]), (status, code))
            self.assertEqual(body["error"]["fields"], {})
        status, body = error_response(RuntimeError("SQL password=SECRET"))
        self.assertEqual(status, 500)
        self.assertNotIn("SECRET", str(body))


class FactoryTests(TestCase):
    def test_lazy_loading_resolves_each_driver_without_importing_the_others(self):
        for institution, entry in AdapterFactory._adapters.items():
            module, name = entry.rsplit(".", 1)
            fake_module = Mock()
            with patch("apps.historiales.infrastructure.factory.import_module", return_value=fake_module) as load:
                self.assertIs(AdapterFactory._adapter_class(institution), getattr(fake_module, name))
            load.assert_called_once_with(f"apps.historiales.infrastructure.adapters.{module}")

    def test_exact_ports_and_separate_catalog(self):
        self.assertEqual(HistorialRepository.__abstractmethods__, {
            "registrar_paciente", "listar_pacientes", "obtener_historial", "registrar_consulta",
            "registrar_diagnostico", "registrar_tratamiento", "registrar_receta", "archivar_paciente"})
        self.assertEqual(MedicamentoCatalogo.__abstractmethods__, {"listar_medicamentos"})

    def test_health_still_has_four_registrations_without_clinical_context(self):
        self.assertEqual(set(AdapterFactory._adapters), set(Institution))
        for institution in Institution:
            constructor = Mock()
            with patch.object(AdapterFactory, "_adapter_class", return_value=constructor) as load:
                self.assertIs(AdapterFactory.create(institution), constructor.return_value)
            constructor.assert_called_once_with()
            load.assert_called_once_with(institution)

    def test_clinical_factory_passes_context_to_both_ports(self):
        harness = MemoryHarness()
        ctx = ContextoClinico("hospital", "U", "admin", "PRO")
        real_type = type(harness.repo(ctx))

        class DemoAdapter(real_type):
            def __init__(self, *, contexto):
                super().__init__(contexto=contexto, harness=harness)

        with patch.dict(AdapterFactory._adapters, {Institution.HOSPITAL: DemoAdapter}):
            repo = AdapterFactory.create_clinical(ctx)
        self.assertIs(repo.contexto, ctx)
        self.assertIsInstance(repo, MedicamentoCatalogo)

    def test_health_only_adapter_fails_closed_and_invalid_context_is_rejected(self):
        class HealthOnly(DatabaseAdapter):
            def health_check(self):
                return True

        with patch.dict(AdapterFactory._adapters, {Institution.HOSPITAL: HealthOnly}):
            self.assertTrue(AdapterFactory.create(Institution.HOSPITAL).health_check())
            with self.assertRaises(PersistenciaNoDisponible):
                AdapterFactory.create_clinical(ContextoClinico("hospital", "U", "admin"))
        for invalid in (None, {}, "hospital"):
            with self.assertRaises(NoAutenticado):
                AdapterFactory.create_clinical(invalid)


class RuntimeFixturesTests(TestCase):
    def test_normative_fixture_and_extensions(self):
        path = Path(__file__).parent / "fixtures"
        historical = json.loads((path / "contrato_v1.json").read_text(encoding="utf-8"))
        runtime = json.loads((path / "contrato_v1_runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(runtime["version"], "1.0.0")
        self.assertEqual(runtime["status"], "vigente")
        self.assertEqual(runtime["cases"][:10], historical["cases"])
        cases = {case["id"]: case for case in runtime["cases"]}
        self.assertEqual(len(cases), 13)
        self.assertEqual(cases["AUTH-CSRF"]["response"]["status"], 200)
        self.assertIsNone(cases["AUTH-LOGOUT"]["response"]["body"])
        self.assertEqual(cases["AUTH-LOGOUT"]["response"]["status"], 204)
        error = cases["CAT-01"]["invalid"]["response"]
        self.assertEqual(error["status"], 400)
        self.assertIn("limit", error["body"]["error"]["fields"])
