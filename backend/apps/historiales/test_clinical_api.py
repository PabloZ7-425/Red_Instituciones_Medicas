"""HTTP contract tests with an explicit B1 double; SQL HTTP tests are separate."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.http import Http404

from apps.historiales.domain.context import PERMISOS
from apps.historiales.domain.errors import (
    AccesoDenegado, Conflicto, DatosInvalidos, NoAutenticado, PersistenciaNoDisponible, RecursoNoEncontrado,
)
from apps.historiales.domain.institutions import Institution
from apps.historiales.domain.ports import DatabaseAdapter
from apps.historiales.infrastructure.factory import AdapterFactory
from apps.historiales.testing.memory import MemoryHarness
from apps.historiales.testing.repository_contract import PACIENTE, CONSULTA, DIAGNOSTICO, TRATAMIENTO
from apps.identidad.models import PerfilInstitucional, Profesional

PASSWORD = "DEMO-api-test-clave-619!"
ROUTES = (
    ("GET", "/api/pacientes/", "listar_pacientes", None),
    ("POST", "/api/pacientes/", "registrar_paciente", PACIENTE),
    ("GET", "/api/pacientes/absent/historial/", "obtener_historial", None),
    ("POST", "/api/pacientes/absent/consultas/", "registrar_consulta", CONSULTA),
    ("POST", "/api/consultas/absent/diagnosticos/", "registrar_diagnostico", DIAGNOSTICO),
    ("POST", "/api/diagnosticos/absent/tratamientos/", "registrar_tratamiento", TRATAMIENTO),
    ("POST", "/api/tratamientos/absent/recetas/", "registrar_receta", {"medicamento_id": "DEMO-M-1", "dosis": "D", "frecuencia": "F"}),
    ("PATCH", "/api/pacientes/absent/estado/", "archivar_paciente", {"estado": "archivado", "motivo": "DEMO"}),
    ("GET", "/api/medicamentos/", "listar_medicamentos", None),
)


class APIHelpers:
    def account(self, institution="hospital", role="admin", *, professional=True):
        user = get_user_model().objects.create_user(f"DEMO-{institution}-{role}-{get_user_model().objects.count()}", password=PASSWORD)
        pro = None
        if professional:
            pro, _ = Profesional.objects.get_or_create(institucion=institution, referencia_externa="1")
        PerfilInstitucional.objects.create(usuario=user, institucion=institution, rol=role, profesional=pro)
        return user

    def signin(self, user):
        browser = Client(enforce_csrf_checks=True)
        token = browser.get("/api/auth/csrf/").json()["csrfToken"]
        result = browser.post("/api/auth/login/", {"username": user.username, "password": PASSWORD},
                              content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(result.status_code, 200, result.content)
        token = browser.get("/api/auth/csrf/").json()["csrfToken"]
        return browser, token

    def send(self, method, url, body=None, *, browser=None, token=None):
        browser = browser or self.browser
        token = token or self.token
        kwargs = {"HTTP_X_CSRFTOKEN": token}
        if method == "GET":
            return browser.get(url, **kwargs)
        return getattr(browser, method.lower())(url, body if body is not None else {},
                                               content_type="application/json", **kwargs)

    def successful(self, response, status):
        self.assertEqual(response.status_code, status, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        return response.json()

    def clinical_chain(self, browser=None, token=None):
        kw = {"browser": browser, "token": token}
        p = self.successful(self.send("POST", "/api/pacientes/", PACIENTE, **kw), 201)
        c = self.successful(self.send("POST", f"/api/pacientes/{p['id']}/consultas/", CONSULTA, **kw), 201)
        d = self.successful(self.send("POST", f"/api/consultas/{c['id']}/diagnosticos/", DIAGNOSTICO, **kw), 201)
        t = self.successful(self.send("POST", f"/api/diagnosticos/{d['id']}/tratamientos/", TRATAMIENTO, **kw), 201)
        medicine = self.successful(self.send("GET", "/api/medicamentos/", **kw), 200)["results"][0]
        r = self.successful(self.send("POST", f"/api/tratamientos/{t['id']}/recetas/",
                            {"medicamento_id": medicine["id"], "dosis": "DEMO", "frecuencia": "DEMO"}, **kw), 201)
        return p, c, d, t, r


class ClinicalAPITests(APIHelpers, TestCase):
    def setUp(self):
        self.harness = MemoryHarness()
        self.addCleanup(self.harness.close)
        factory_patch = patch("apps.historiales.presentation.clinical.AdapterFactory.create_clinical", side_effect=self.harness.repo)
        self.factory = factory_patch.start()
        self.addCleanup(factory_patch.stop)
        self.user = self.account()
        self.browser, self.token = self.signin(self.user)

    def test_all_routes_chain_tree_archive_and_json_shapes(self):
        p, c, d, t, r = self.clinical_chain()
        self.assertEqual(self.browser.get("/api/pacientes/?q=demo-&limit=1&offset=0").json(),
                         {"count": 1, "limit": 1, "offset": 0, "results": [p]})
        history = self.successful(self.browser.get(f"/api/pacientes/{p['id']}/historial/"), 200)
        self.assertEqual(history, {"paciente": p, "consultas": [c | {"diagnosticos": [d | {"tratamientos": [t | {"recetas": [r]}]}]}]})
        state_url = f"/api/pacientes/{p['id']}/estado/"
        body = {"estado": "archivado", "motivo": "DEMO archivo"}
        archived = self.successful(self.send("PATCH", state_url, body), 200)
        self.assertEqual(self.send("PATCH", state_url, body).json(), archived)
        self.assertEqual(self.send("PATCH", state_url, body | {"motivo": "Otro"}).status_code, 409)
        self.assertEqual(self.send("POST", f"/api/pacientes/{p['id']}/consultas/", CONSULTA).status_code, 409)
        self.assertEqual(self.browser.get(f"/api/pacientes/{p['id']}/historial/").json()["consultas"], history["consultas"])
        self.assertEqual(self.send("POST", "/api/pacientes/", PACIENTE).status_code, 409)
        self.assertEqual(self.factory.call_args.args[0].institucion, "hospital")

    def test_all_routes_require_session_and_mutations_require_csrf(self):
        anonymous = Client(enforce_csrf_checks=True)
        for method, url, _, body in ROUTES:
            self.factory.reset_mock()
            result = self.send(method, url, body, browser=anonymous)
            self.assertEqual(result.status_code, 401)
            self.assertEqual(result.json()["error"]["code"], "UNAUTHORIZED")
            self.assertIn("WWW-Authenticate", result)
            self.factory.assert_not_called()
            if method != "GET":
                result = getattr(self.browser, method.lower())(url, body, content_type="application/json")
                self.assertEqual(result.status_code, 403)
                self.factory.assert_not_called()

    def test_clinical_session_revocation_and_untrusted_origin(self):
        self.factory.reset_mock()
        response = self.browser.post("/api/pacientes/", PACIENTE, content_type="application/json",
                                     HTTP_X_CSRFTOKEN=self.token, HTTP_ORIGIN="http://untrusted.invalid")
        self.assertEqual(response.status_code, 403)
        self.factory.assert_not_called()
        session_key = self.browser.cookies["sessionid"].value
        self.assertEqual(self.send("POST", "/api/auth/logout/", {}).status_code, 204)
        self.assertEqual(self.browser.get("/api/pacientes/").status_code, 401)
        self.browser.cookies["sessionid"] = session_key
        self.assertEqual(self.browser.get("/api/pacientes/").status_code, 401)
        self.factory.assert_not_called()

    def test_permission_matrix_denies_before_body_lookup_or_factory(self):
        for role in ("admin", "medico", "secretaria", "enfermero", "laboratorista"):
            institution = "laboratorio" if role == "laboratorista" else "hospital"
            user = self.account(institution, role)
            browser, token = self.signin(user)
            for method, url, operation, body in ROUTES:
                with self.subTest(role=role, operation=operation):
                    self.factory.reset_mock()
                    response = self.send(method, url, body, browser=browser, token=token)
                    if role not in PERMISOS[operation]:
                        self.assertEqual(response.status_code, 403)
                        self.factory.assert_not_called()
                    else:
                        self.assertNotEqual(response.status_code, 403, response.content)
                        self.factory.assert_called_once()

    def test_professional_missing_or_revoked_blocks_clinical_mutation(self):
        browser, token = self.signin(self.account(role="medico", professional=False))
        for method, url, operation, body in ROUTES:
            if operation in ("registrar_consulta", "registrar_diagnostico", "registrar_tratamiento", "registrar_receta"):
                self.factory.reset_mock()
                self.assertEqual(self.send(method, url, body, browser=browser, token=token).status_code, 403)
                self.factory.assert_not_called()
        profile = self.user.perfil_institucional
        profile.profesional.habilitado = False
        profile.profesional.save()
        self.assertEqual(self.browser.get("/api/pacientes/").status_code, 200)
        self.factory.reset_mock()
        self.assertEqual(self.send("POST", "/api/pacientes/id/consultas/", CONSULTA).status_code, 403)
        self.factory.assert_not_called()

    def test_validation_before_factory_and_no_engine_or_identity_selection(self):
        cases = [("POST", "/api/pacientes/", PACIENTE | {k: "mysql"}) for k in ("institucion", "engine", "motor", "profesional_id", "id")]
        cases += [("POST", "/api/pacientes/", body) for body in ({}, [], None, "texto", PACIENTE | {"fecha_nacimiento": "2026-02-30"})]
        cases += [("POST", "/api/pacientes/p/consultas/", CONSULTA | {"fecha": "2999-01-01"}),
                  ("GET", "/api/pacientes/%20/historial/", None),
                  ("POST", "/api/consultas/c/diagnosticos/", DIAGNOSTICO | {"descripcion": " "}),
                  ("POST", "/api/diagnosticos/d/tratamientos/", TRATAMIENTO | {"indicaciones_generales": 3}),
                  ("POST", "/api/tratamientos/t/recetas/", {"medicamento_id": 1, "dosis": "D", "frecuencia": "F"}),
                  ("PATCH", "/api/pacientes/p/estado/", {"estado": "activo", "motivo": "DEMO"})]
        for method, url, body in cases:
            self.factory.reset_mock()
            response = self.send(method, url, body)
            self.assertEqual(response.status_code, 400, response.content)
            self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
            self.assertTrue(response.json()["error"]["fields"])
            self.factory.assert_not_called()

    def test_query_repetitions_unknowns_types_and_literal_search(self):
        for base in ("/api/pacientes/", "/api/medicamentos/"):
            for query in ("limit=0", "limit=101", "limit=true", "offset=-1", "offset=1.5", "limit=1&limit=2", "q=a&q=b", "motor=mysql", "q=" + "a"*101):
                self.factory.reset_mock()
                self.assertEqual(self.browser.get(base+"?"+query).status_code, 400)
                self.factory.assert_not_called()
        self.assertEqual(self.send("POST", "/api/pacientes/?q=a", PACIENTE).status_code, 400)
        self.assertEqual(self.browser.get("/api/pacientes/id/historial/?limit=1").status_code, 400)
        self.send("POST", "/api/pacientes/", PACIENTE | {"nombres": "Á%_ DEMO"})
        self.assertEqual(self.browser.get("/api/pacientes/", {"q": "a\u0301%_"}).json()["count"], 1)
        self.assertEqual(self.browser.get("/api/pacientes/?q=%25").json()["count"], 0)

    def test_json_parsing_duplicate_keys_and_media_type(self):
        for data in ('{"nombres":', '{"id":1,"id":2}', '{"valor":NaN}', '{"valor":Infinity}', b'\xff'):
            self.factory.reset_mock()
            result = self.browser.post("/api/pacientes/", data, content_type="application/json", HTTP_X_CSRFTOKEN=self.token)
            self.assertEqual(result.status_code, 400, result.content)
            self.factory.assert_not_called()
        result = self.browser.post("/api/pacientes/", "nombres=DEMO", content_type="text/plain", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(result.status_code, 415)
        self.assertEqual(result.json()["error"]["code"], "UNSUPPORTED_MEDIA_TYPE")

    def test_safe_error_envelopes_cover_domain_driver_boundary_and_unexpected_errors(self):
        errors = ((DatosInvalidos(fields={"q": ["DEMO"]}), 400, "VALIDATION_ERROR"),
                  (NoAutenticado(), 401, "UNAUTHORIZED"), (AccesoDenegado(), 403, "FORBIDDEN"),
                  (RecursoNoEncontrado(), 404, "NOT_FOUND"), (Conflicto(), 409, "CONFLICT"),
                  (PersistenciaNoDisponible(), 503, "SERVICE_UNAVAILABLE"),
                  (Http404("DEMO secreto"), 404, "NOT_FOUND"), (RuntimeError("DEMO secreto SQL password"), 500, "INTERNAL_ERROR"))
        for error, status, code in errors:
            self.factory.side_effect = error
            response = self.browser.get("/api/pacientes/")
            self.assertEqual(response.status_code, status)
            payload = response.json()["error"]
            self.assertEqual(set(payload), {"code", "message", "fields"})
            self.assertEqual(payload["code"], code)
            self.assertIsInstance(payload["fields"], dict)
            self.assertNotIn("secreto", response.content.decode())

    @override_settings(DEBUG=True)
    def test_methods_unknown_paths_head_and_no_cache(self):
        response = self.send("DELETE", "/api/pacientes/", {})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["error"]["code"], "METHOD_NOT_ALLOWED")
        self.assertEqual(self.browser.get("/api/no-existe/").json()["error"]["code"], "NOT_FOUND")
        response = self.browser.head("/api/pacientes/?limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        browser, token = self.signin(self.account(role="secretaria"))
        self.factory.reset_mock()
        self.assertEqual(browser.head("/api/pacientes/id/historial/").status_code, 403)
        self.factory.assert_not_called()

    def test_four_contexts_are_bound_to_session_and_cannot_cross_any_parent(self):
        p, c, d, t, _ = self.clinical_chain()
        for institution in ("pediatrico", "laboratorio", "odontologica"):
            browser, token = self.signin(self.account(institution))
            self.assertEqual(browser.get("/api/pacientes/").json()["count"], 0)
            for method, url, _, body in ROUTES:
                if "absent" not in url:
                    continue
                key = t["id"] if "recetas" in url else d["id"] if "tratamientos" in url else c["id"] if "diagnosticos" in url else p["id"]
                response = self.send(method, url.replace("absent", key), body, browser=browser, token=token)
                missing = self.send(method, url, body, browser=browser, token=token)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), missing.json())
            self.factory.reset_mock()
            result = self.send("POST", "/api/pacientes/", PACIENTE, browser=browser, token=token)
            self.assertEqual(result.status_code, 201)
            self.assertEqual(self.factory.call_args.args[0].institucion, institution)


class MissingProviderAPITests(APIHelpers, TestCase):
    def test_health_only_nosql_is_explicit_503_without_fake_success(self):
        # Explicit test provider: keep this failure-path test valid when A ships
        # real adapters. The management audit reports actual checkout availability.
        class HealthOnly(DatabaseAdapter):
            def health_check(self):
                return True
        with patch.dict(AdapterFactory._adapters, {Institution.LABORATORIO: HealthOnly,
                                                  Institution.ODONTOLOGICA: HealthOnly}):
            self.check_unavailable()

    def check_unavailable(self):
        for institution in ("laboratorio", "odontologica"):
            self.browser, self.token = self.signin(self.account(institution))
            for method, url, _, body in ROUTES:
                response = self.send(method, url, body)
                self.assertEqual(response.status_code, 503, response.content)
                self.assertEqual(response.json()["error"]["code"], "SERVICE_UNAVAILABLE")
            self.assertEqual(self.send("POST", "/api/pacientes/", {}).status_code, 400)
