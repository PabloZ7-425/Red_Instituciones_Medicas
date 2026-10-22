"""Real session -> DRF -> use case -> factory -> limited native SQL provider."""
import os
from unittest import skipUnless
from unittest.mock import patch

from django.test import TestCase

from apps.historiales.domain.context import ContextoClinico
from apps.historiales.testing.repository_contract import PACIENTE, CONSULTA
from apps.historiales.test_clinical_api import APIHelpers, ROUTES

ENABLED = os.getenv("TEST_HOSPITAL_POSTGRES") == "1" and os.getenv("TEST_PEDIATRIA_MYSQL") == "1"


@skipUnless(ENABLED, "B5 HTTP real requiere ambos destinos SQL aislados")
class ClinicalSQLHTTPTests(APIHelpers, TestCase):
    def setUp(self):
        from apps.historiales.testing.postgres import PostgreSQLHarness
        from apps.historiales.testing.mysql import MySQLHarness
        from apps.historiales.infrastructure.adapters.postgres_adapter import PostgreSQLAdapter
        from apps.historiales.infrastructure.adapters.mysql_adapter import MySQLAdapter
        self.harnesses = {}
        self.clients = {}
        for institution, constructor, provider in (("hospital", PostgreSQLHarness, PostgreSQLAdapter),
                                                   ("pediatrico", MySQLHarness, MySQLAdapter)):
            h = constructor()
            self.harnesses[institution] = h
            self.addCleanup(h.close)
            instrument = h.repo(ContextoClinico(institution, "DEMO-U", "admin", "1"))
            # Patch connection destination only; production routing/class/service
            # remain real and no factory double can disguise a wrong provider.
            target = patch.object(provider, "_connect", side_effect=instrument._connect)
            target.start()
            self.addCleanup(target.stop)
            self.clients[institution] = self.signin(self.account(institution))

    def test_complete_persisted_http_flow_and_archive_for_both_sql_institutions(self):
        for institution, (browser, token) in self.clients.items():
            with self.subTest(institution=institution):
                p, c, d, t, r = self.clinical_chain(browser, token)
                history = browser.get(f"/api/pacientes/{p['id']}/historial/").json()
                self.assertEqual(history["consultas"][0]["diagnosticos"][0]["tratamientos"][0]["recetas"], [r])
                # A new repository instance/connection observes committed HTTP writes.
                repo = self.harnesses[institution].repo(ContextoClinico(institution, "U", "admin", "1"))
                self.assertEqual(repo.obtener_historial(p["id"]), history)
                self.assertEqual(self.send("POST", "/api/pacientes/", PACIENTE, browser=browser, token=token).status_code, 409)
                state_url = f"/api/pacientes/{p['id']}/estado/"
                body = {"estado": "archivado", "motivo": "DEMO baja HTTP"}
                archived = self.successful(self.send("PATCH", state_url, body, browser=browser, token=token), 200)
                self.assertEqual(self.send("PATCH", state_url, body, browser=browser, token=token).json(), archived)
                self.assertEqual(self.send("POST", f"/api/pacientes/{p['id']}/consultas/", CONSULTA, browser=browser, token=token).status_code, 409)
                self.assertEqual(browser.get(f"/api/pacientes/{p['id']}/historial/").json()["consultas"], history["consultas"])

    def test_all_foreign_parents_are_indistinguishable_from_missing_and_identification_is_institutional(self):
        chains = {name: self.clinical_chain(*client) for name, client in self.clients.items()}
        for own, foreign in (("hospital", "pediatrico"), ("pediatrico", "hospital")):
            browser, token = self.clients[own]
            p, c, d, t, _ = chains[foreign]
            for method, url, _, body in ROUTES:
                if "absent" not in url:
                    continue
                key = t["id"] if "recetas" in url else d["id"] if "tratamientos" in url else c["id"] if "diagnosticos" in url else p["id"]
                foreign_response = self.send(method, url.replace("absent", key), body, browser=browser, token=token)
                missing_response = self.send(method, url, body, browser=browser, token=token)
                self.assertEqual(foreign_response.status_code, 404)
                self.assertEqual(foreign_response.json(), missing_response.json())
            self.assertEqual(browser.get("/api/pacientes/").json()["count"], 1)

    def test_provider_failure_after_native_insert_is_503_and_leaves_no_patient(self):
        from apps.historiales.infrastructure.adapters.postgres_adapter import PostgreSQLAdapter
        from apps.historiales.infrastructure.adapters.mysql_adapter import MySQLAdapter
        def fail(cursor):
            cursor.execute("SELECT b5_injected_sql_failure_after_insert")
        for institution, provider in (("hospital", PostgreSQLAdapter), ("pediatrico", MySQLAdapter)):
            browser, token = self.clients[institution]
            with patch.object(provider, "_after_write", side_effect=fail):
                response = self.send("POST", "/api/pacientes/", PACIENTE, browser=browser, token=token)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("b5_injected", response.content.decode())
            self.assertEqual(browser.get("/api/pacientes/").json()["count"], 0)

    def test_connection_failure_is_safe_503_not_success_or_duplicate(self):
        from apps.historiales.infrastructure.adapters.postgres_adapter import PostgreSQLAdapter
        from apps.historiales.infrastructure.adapters.mysql_adapter import MySQLAdapter
        import psycopg
        import mysql.connector
        for institution, provider, error in (("hospital", PostgreSQLAdapter, psycopg.OperationalError("DEMO password SQL")),
                                             ("pediatrico", MySQLAdapter, mysql.connector.InterfaceError("DEMO password SQL"))):
            browser, token = self.clients[institution]
            with patch.object(provider, "_connect", side_effect=error):
                response = browser.get("/api/pacientes/")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "SERVICE_UNAVAILABLE")
            self.assertNotIn("password", response.content.decode())
