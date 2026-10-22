import json
import time
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import CommonPasswordValidator, validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import include, path
from rest_framework.response import Response

from apps.historiales.application.clinical import HistorialService
from apps.identidad.models import PerfilInstitucional, Profesional
from apps.identidad.principal import MAX_SESSION_SECONDS, SESSION_STARTED, contexto_usuario
from apps.identidad.transfer import fingerprint, identity_payload
from apps.identidad.views import IdentityView

User = get_user_model()
PASSWORD = "  DEMO-clave-sintetica-509!  "


class ClinicalProbe(IdentityView):
    """Test-only endpoint. Confirms B2->B1 binding without exposing a production route."""
    def post(self, request):
        repository = self.repository_factory(request.contexto_clinico)
        service = HistorialService(request.contexto_clinico, repository)
        return Response(service.obtener_historial(request.data["id"]))


urlpatterns = [path("api/auth/", include("apps.identidad.urls")), path("probe/", ClinicalProbe.as_view())]


class IdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("DEMO-medico", password=PASSWORD)
        cls.professional = Profesional.objects.create(institucion="hospital", referencia_externa="DEMO-PRO")
        cls.profile = PerfilInstitucional.objects.create(usuario=cls.user, institucion="hospital", rol="medico", profesional=cls.professional)

    def setUp(self):
        self.browser = Client(enforce_csrf_checks=True)

    def csrf(self):
        response = self.browser.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        return response.json()["csrfToken"]

    def login(self, username="DEMO-medico", password=PASSWORD):
        return self.browser.post("/api/auth/login/", {"username": username, "password": password},
                                 content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())

    def test_anonymous_csrf_cookie_and_no_cache(self):
        response = self.browser.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["csrfToken"])
        self.assertIn("csrftoken", response.cookies)
        self.assertIn("no-store", response["Cache-Control"])

    def test_login_me_and_no_password_in_response(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"usuario": {"id": str(self.user.pk), "username": self.user.username,
                                                       "rol": "medico", "institucion": "hospital"}})
        me = self.browser.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json(), response.json())
        self.assertNotIn("password", str(me.json()))
        self.assertTrue(response.cookies["sessionid"]["httponly"])
        self.assertEqual(response.cookies["sessionid"]["max-age"], "")
        self.assertEqual(response.cookies["sessionid"]["expires"], "")
        self.assertEqual(response.cookies["sessionid"]["samesite"], "Lax")

    def test_password_whitespace_preserved_and_username_trimmed(self):
        self.assertEqual(self.login(password=PASSWORD.strip()).status_code, 401)
        self.assertEqual(self.login(username=" DEMO-medico ").status_code, 200)

    def test_login_requires_csrf_even_when_anonymous(self):
        response = self.browser.post("/api/auth/login/", {"username": self.user.username, "password": PASSWORD}, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")
        self.assertNotIn("sessionid", response.cookies)

    def test_login_always_rotates_session_and_csrf(self):
        old_csrf = self.csrf()
        old_secret = self.browser.cookies["csrftoken"].value
        session = self.browser.session
        session["untrusted"] = "DEMO"
        session.save()
        # Ensure this client presents the existing anonymous session.
        self.browser.cookies["sessionid"] = session.session_key
        anonymous_key = session.session_key
        self.assertEqual(self.browser.post("/api/auth/login/", {"username": self.user.username, "password": PASSWORD},
                         content_type="application/json", HTTP_X_CSRFTOKEN=old_csrf).status_code, 200)
        first_key = self.browser.cookies["sessionid"].value
        self.assertNotEqual(first_key, anonymous_key)
        self.assertFalse(Session.objects.filter(session_key=anonymous_key).exists())
        self.assertNotIn("untrusted", self.browser.session)
        self.assertNotEqual(old_secret, self.browser.cookies["csrftoken"].value)
        self.assertEqual(self.browser.post("/api/auth/logout/", {}, content_type="application/json", HTTP_X_CSRFTOKEN=old_csrf).status_code, 403)
        self.assertEqual(self.login().status_code, 200)
        self.assertNotEqual(first_key, self.browser.cookies["sessionid"].value)

    def test_logout_invalidates_database_session_and_replay(self):
        self.assertEqual(self.login().status_code, 200)
        key = self.browser.cookies["sessionid"].value
        response = self.browser.post("/api/auth/logout/", {}, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(Session.objects.filter(session_key=key).exists())
        self.browser.cookies["sessionid"] = key
        self.assertEqual(self.browser.get("/api/auth/me/").status_code, 401)

    def test_authenticated_logout_requires_csrf_and_rejects_extra_body(self):
        self.login()
        self.assertEqual(self.browser.post("/api/auth/logout/", {}, content_type="application/json").status_code, 403)
        response = self.browser.post("/api/auth/logout/", {"institucion": "hospital"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.browser.get("/api/auth/me/").status_code, 200)

    def test_password_change_revokes_existing_session(self):
        self.login()
        self.user.set_password("DEMO-clave-nueva-573!")
        self.user.save()
        self.assertEqual(self.browser.get("/api/auth/me/").status_code, 401)

    def test_anonymous_protected_endpoints_return_401_deliberately(self):
        for method, path_name in (("get", "/api/auth/me/"), ("post", "/api/auth/logout/")):
            response = getattr(self.browser, method)(path_name)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")
            self.assertIn("WWW-Authenticate", response)

    def test_absolute_expiry_missing_and_future_timestamp(self):
        for timestamp in (time.time() - MAX_SESSION_SECONDS - 1, time.time() + 100, None, "invalid", float("inf")):
            self.login()
            session = self.browser.session
            session[SESSION_STARTED] = timestamp
            session.save()
            key = session.session_key
            with self.subTest(timestamp=timestamp):
                self.assertEqual(self.browser.get("/api/auth/me/").status_code, 401)
                self.assertFalse(Session.objects.filter(session_key=key).exists())

    def test_activity_does_not_extend_absolute_session(self):
        self.login()
        session = self.browser.session
        original = time.time() - 100
        session[SESSION_STARTED] = original
        session.save()
        for _ in range(3):
            self.assertEqual(self.browser.get("/api/auth/me/").status_code, 200)
        self.assertEqual(self.browser.session[SESSION_STARTED], original)

    def test_credentials_and_inactive_account_have_uniform_401(self):
        responses = [self.login(username="DEMO-no-existe"), self.login(password="wrong")]
        self.user.is_active = False
        self.user.save()
        responses.append(self.login())
        for response in responses:
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), responses[0].json())

    def test_missing_profile_and_technical_superuser_have_no_bypass(self):
        User.objects.create_superuser("DEMO-root", "synthetic@example.invalid", PASSWORD)
        self.assertEqual(self.login(username="DEMO-root").status_code, 401)
        self.profile.delete()
        self.assertEqual(self.login().status_code, 401)

    def test_profile_revocation_and_account_deactivation_are_immediate(self):
        self.login()
        self.profile.activo = False
        self.profile.save()
        self.assertEqual(self.browser.get("/api/auth/me/").status_code, 403)
        self.profile.activo = True
        self.profile.save()
        self.login()
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.browser.get("/api/auth/me/").status_code, 401)

    def test_current_profile_is_read_each_request_and_institution_not_from_query(self):
        self.login()
        self.profile.rol = "enfermero"
        self.profile.save()
        self.assertEqual(self.browser.get("/api/auth/me/").json()["usuario"]["rol"], "enfermero")
        self.assertEqual(self.browser.get("/api/auth/me/?institucion=laboratorio").status_code, 400)

    def test_professional_of_other_institution_is_rejected_at_login_and_session(self):
        self.login()
        Profesional.objects.filter(pk=self.professional.pk).update(institucion="pediatrico")
        self.assertEqual(self.browser.get("/api/auth/me/").status_code, 403)
        self.assertEqual(self.login().status_code, 401)

    def test_disabled_professional_cannot_write_but_can_read_identity(self):
        from apps.historiales.domain.errors import AccesoDenegado
        self.professional.habilitado = False
        self.professional.save()
        context = contexto_usuario(self.user)
        self.assertIsNone(context.profesional_id)
        with self.assertRaises(AccesoDenegado):
            HistorialService(context, object()).registrar_consulta("missing", {})
        self.assertEqual(self.login().status_code, 200)

    def test_profiles_route_the_four_institutions(self):
        for slug in ("hospital", "pediatrico", "laboratorio", "odontologica"):
            self.profile.profesional = None
            self.profile.institucion = slug
            self.profile.save()
            response = self.login()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.browser.get("/api/auth/me/").json()["usuario"]["institucion"], slug)

    @override_settings(ROOT_URLCONF="apps.identidad.tests")
    def test_authenticated_context_isolates_clinical_resource_and_permissions(self):
        from unittest.mock import Mock
        from apps.historiales.domain.context import ContextoClinico
        from apps.historiales.testing.memory import MemoryHarness
        from apps.historiales.testing.repository_contract import PACIENTE
        harness = MemoryHarness()
        patient = harness.repo(ContextoClinico("hospital", "DEMO", "admin")).registrar_paciente(PACIENTE)
        factory = Mock(side_effect=harness.repo)
        with patch.object(ClinicalProbe, "repository_factory", factory, create=True):
            self.login()
            response = self.browser.post("/probe/", {"id": patient["id"]}, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(factory.call_args.args[0].institucion, "hospital")
            self.profile.profesional = None
            self.profile.institucion = "laboratorio"
            self.profile.save()
            foreign = self.browser.post("/probe/", {"id": patient["id"]}, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())
            missing = self.browser.post("/probe/", {"id": "DEMO-no-existe"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())
            self.assertEqual(foreign.status_code, 404)
            self.assertEqual(foreign.json(), missing.json())
            self.assertEqual(factory.call_args.args[0].institucion, "laboratorio")
            self.profile.rol = "secretaria"
            self.profile.save()
            response = self.browser.post("/probe/", {"id": "DEMO-no-existe"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())
            self.assertEqual(response.status_code, 403)

    def test_login_rejects_invalid_json_fields_and_types(self):
        for data in ([], None, "text", {}, {"username": self.user.username, "password": PASSWORD, "institucion": "hospital"},
                     {"username": 123, "password": PASSWORD}, {"username": self.user.username, "password": ""}):
            response = self.browser.post("/api/auth/login/", json.dumps(data), content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
        response = self.browser.post("/api/auth/login/", '{"bad":', content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 400)

    def test_method_media_type_and_query_errors_have_contract_envelope(self):
        response = self.browser.get("/api/auth/login/")
        self.assertEqual((response.status_code, response.json()["error"]["code"]), (405, "METHOD_NOT_ALLOWED"))
        response = self.browser.post("/api/auth/login/", "username=x", content_type="text/plain", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual((response.status_code, response.json()["error"]["code"]), (415, "UNSUPPORTED_MEDIA_TYPE"))
        self.assertEqual(self.browser.get("/api/auth/csrf/?q=x&q=y").status_code, 400)

    def test_credentialed_cors_allows_only_localhost_frontend(self):
        response = self.browser.get("/api/auth/csrf/", HTTP_ORIGIN="http://localhost:5173")
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")
        for origin in ("http://evil.example", "http://127.0.0.1:5173"):
            self.assertNotIn("Access-Control-Allow-Origin", self.browser.get("/api/auth/csrf/", HTTP_ORIGIN=origin))
            response = self.browser.post("/api/auth/login/", {"username": self.user.username, "password": PASSWORD},
                                         content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf(), HTTP_ORIGIN=origin)
            self.assertEqual(response.status_code, 403)

    @override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_secure_cookie_flags_when_https_enabled(self):
        response = self.login()
        self.assertTrue(response.cookies["sessionid"]["secure"])
        self.assertTrue(response.cookies["csrftoken"]["secure"])

    def test_login_database_failure_is_503_without_raw_error(self):
        from django.db import OperationalError
        with patch("apps.identidad.views.authenticate", side_effect=OperationalError("password=SECRET")):
            response = self.login()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SECRET", response.content.decode())


class ModelAndProvisioningTests(TestCase):
    def test_database_rejects_unknown_roles_and_laboratorista_outside_lab(self):
        for role, institution in (("root", "hospital"), ("laboratorista", "hospital"), ("admin", "otro")):
            user = User.objects.create_user(f"DEMO-{role}-{institution}", password=PASSWORD)
            with self.subTest(role=role, institution=institution), self.assertRaises(IntegrityError), transaction.atomic():
                PerfilInstitucional.objects.create(usuario=user, rol=role, institucion=institution)

    def test_model_rejects_cross_institution_professional(self):
        user = User.objects.create_user("DEMO-cross", password=PASSWORD)
        professional = Profesional.objects.create(institucion="hospital", referencia_externa="DEMO-PRO")
        with self.assertRaises(ValidationError):
            PerfilInstitucional(usuario=user, institucion="pediatrico", rol="medico", profesional=professional).full_clean()

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"])
    def test_production_django_hashing(self):
        user = User.objects.create_user("DEMO-hash", password=PASSWORD)
        self.assertEqual(identify_hasher(user.password).algorithm, "pbkdf2_sha256")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_password_validators(self):
        for password in ("short", "1234567890123456", "DEMO-similitud-DEMO-similitud"):
            with self.subTest(password=password), self.assertRaises(ValidationError):
                validate_password(password, User(username="DEMO-similitud-DEMO-similitud"))
        validate_password(PASSWORD, User(username="unrelated"))
        with self.assertRaises(ValidationError):
            CommonPasswordValidator().validate("password")

    def test_demo_command_hashes_and_never_prints_password(self):
        output = StringIO()
        with patch("apps.identidad.management.commands.create_demo_identity.getpass", return_value=PASSWORD):
            call_command("create_demo_identity", username="DEMO-local", institucion="odontologica", rol="medico", professional_id="DEMO-ODONTO", database="default", stdout=output)
        user = User.objects.get(username="DEMO-local")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_superuser)
        self.assertEqual(contexto_usuario(user).institucion, "odontologica")
        self.assertNotIn(PASSWORD, output.getvalue())
        with self.assertRaises(CommandError):
            call_command("create_demo_identity", username="DEMO-local", institucion="hospital", rol="admin", database="default")

    def test_demo_command_rejects_weak_password_and_rolls_back_invalid_profile(self):
        with patch("apps.identidad.management.commands.create_demo_identity.getpass", return_value="short"), self.assertRaises(CommandError):
            call_command("create_demo_identity", username="DEMO-weak", institucion="hospital", rol="medico", database="default")
        self.assertFalse(User.objects.filter(username="DEMO-weak").exists())
        with patch("apps.identidad.management.commands.create_demo_identity.getpass", return_value=PASSWORD), self.assertRaises(CommandError):
            call_command("create_demo_identity", username="DEMO-invalid", institucion="hospital", rol="laboratorista", database="default")
        self.assertFalse(User.objects.filter(username="DEMO-invalid").exists())

    def test_payload_preserves_hashes_permissions_groups_and_identifies_invalid_hash(self):
        user = User.objects.create_user("DEMO-transfer", password=PASSWORD)
        group = Group.objects.create(name="DEMO-equipo")
        group.permissions.add(Permission.objects.first())
        user.groups.add(group)
        user.user_permissions.add(Permission.objects.last())
        payload = identity_payload("default")
        records = json.loads(payload)
        self.assertEqual(len(records), 2)
        saved_user = next(r for r in records if r["model"] == "auth.user")
        self.assertEqual(saved_user["fields"]["password"], user.password)
        self.assertTrue(saved_user["fields"]["groups"])
        self.assertTrue(saved_user["fields"]["user_permissions"])
        self.assertEqual(fingerprint(payload), fingerprint(payload))
        user.password = "unknown-not-a-django-hash"
        user.save()
        with self.assertRaises(CommandError):
            identity_payload("default")
