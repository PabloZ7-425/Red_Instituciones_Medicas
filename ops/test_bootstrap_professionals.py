"""The DEMO repair must preserve explicit deactivation and concurrent versions."""
from copy import deepcopy
import unittest

from bootstrap_professionals import ensure_native_professional


class NativeProfessionalTests(unittest.TestCase):
    def provision(self, institution="laboratorio"):
        rows = {}
        writes = []

        def create(identifier, row):
            self.assertNotIn(identifier, rows)
            rows[identifier] = deepcopy(row)
            writes.append(identifier)

        identifier = ensure_native_professional(institution, rows.get, create)
        return rows, writes, create, identifier

    def test_both_stores_create_native_eligibility_and_retry_without_writes(self):
        for institution in ["laboratorio", "odontologica"]:
            with self.subTest(institution=institution):
                rows, writes, create, identifier = self.provision(institution)
                self.assertIs(rows[identifier]["activo"], True)
                self.assertIs(rows[identifier]["habilitado"], True)
                self.assertEqual(rows[identifier]["institucion"], institution)
                self.assertEqual(rows[identifier]["schema_version"], 2)
                self.assertEqual(ensure_native_professional(institution, rows.get, create), identifier)
                self.assertEqual(writes, [identifier])

    def test_clinical_version_is_preserved_on_retry(self):
        rows, writes, create, identifier = self.provision()
        rows[identifier]["version"] = 17
        ensure_native_professional("laboratorio", rows.get, create)
        self.assertEqual(rows[identifier]["version"], 17)
        self.assertEqual(len(writes), 1)

    def test_disabled_missing_or_incompatible_fields_never_get_overwritten(self):
        for key, value in [("activo", False), ("habilitado", False), ("habilitado", 1),
                           ("institucion", "odontologica"), ("schema_version", 1),
                           ("colegiado", "OTRO"), ("nombre", None)]:
            with self.subTest(key=key, value=value):
                rows, writes, create, identifier = self.provision()
                rows[identifier][key] = value
                original = deepcopy(rows)
                with self.assertRaises(RuntimeError):
                    ensure_native_professional("laboratorio", rows.get, create)
                self.assertEqual(rows, original)
                self.assertEqual(len(writes), 1)

    def test_unsupported_institution_does_not_read_or_write(self):
        def fail(*args):
            self.fail("Unsupported setup touched the store")
        with self.assertRaises(ValueError):
            ensure_native_professional("hospital", fail, fail)


if __name__ == "__main__":
    unittest.main()
