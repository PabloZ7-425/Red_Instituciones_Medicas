import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase
from apps.historiales.domain.institutions import Institution
from apps.historiales.domain.ports import DatabaseAdapter
from apps.historiales.infrastructure.factory import AdapterFactory
from apps.historiales.testing.memory import MemoryRepository


class ProviderAuditTests(SimpleTestCase):
    def test_report_distinguishes_sql_ports_from_nosql_connectivity(self):
        class HealthOnly(DatabaseAdapter):
            def health_check(self):
                return True
        output = StringIO()
        with patch.dict(AdapterFactory._adapters, {Institution.LABORATORIO: HealthOnly,
                                                  Institution.ODONTOLOGICA: HealthOnly}):
            call_command("audit_clinical_providers", stdout=output)
            with self.assertRaises(CommandError):
                call_command("audit_clinical_providers", "--require-all", stdout=StringIO())
        report = json.loads(output.getvalue())["providers"]
        self.assertEqual(set(report), {"hospital", "pediatrico", "laboratorio", "odontologica"})
        self.assertTrue(all(report[s]["implements_ports"] for s in ("hospital", "pediatrico")))
        for slug in ("laboratorio", "odontologica"):
            self.assertFalse(report[slug]["implements_ports"])
            self.assertEqual(len(report[slug]["missing_methods"]), 9)

    def test_gate_accepts_declared_complete_ports_using_an_explicit_test_double(self):
        with patch.dict(AdapterFactory._adapters, {i: MemoryRepository for i in Institution}):
            output = StringIO()
            call_command("audit_clinical_providers", "--require-all", stdout=output)
            self.assertTrue(all(p["implements_ports"] for p in json.loads(output.getvalue())["providers"].values()))
