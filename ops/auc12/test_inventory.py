"""Sanitized diagnoses distinguish preparation failures without exposing secrets."""
import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('desktop_inventory',Path(__file__).with_name('desktop_inventory.py'))
inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)


class InventoryPrivacyTests(unittest.TestCase):
    def observe_error(self,error):
        def fail():raise error
        result=inventory.observe(fail)
        self.assertEqual(result['status'],'unavailable')
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(result))
        return result

    def test_chained_django_error_retains_table_missing_code_without_message(self):
        driver=Exception('PRIVATE_SENTINEL credentials and SQL');driver.sqlstate='42P01'
        wrapper=Exception('PRIVATE_SENTINEL personal record');wrapper.__cause__=driver
        result=self.observe_error(wrapper)
        self.assertEqual(result['sqlstate'],'42P01');self.assertEqual(result['diagnosis'],'table_missing')

    def test_mysql_permission_and_authentication_are_distinguished(self):
        for number,diagnosis in [(1045,'authentication_failed'),(1044,'permission_denied'),(1146,'table_missing')]:
            error=Exception('PRIVATE_SENTINEL');error.errno=number;error.sqlstate='28000' if number==1045 else '42000'
            self.assertEqual(self.observe_error(error)['diagnosis'],diagnosis)

    def test_libpq_auth_without_sqlstate_is_classified_but_not_printed(self):
        result=self.observe_error(Exception('password authentication failed for user PRIVATE_SENTINEL'))
        self.assertEqual(result['diagnosis'],'authentication_failed')

    def test_unknown_error_and_untrusted_codes_are_not_echoed(self):
        error=Exception('PRIVATE_SENTINEL');error.sqlstate='PRIVATE_SENTINEL';error.errno='PRIVATE_SENTINEL'
        result=self.observe_error(error)
        self.assertNotIn('sqlstate',result);self.assertNotIn('errno',result)
        self.assertEqual(result['diagnosis'],'undetermined')

    def test_postgres_schema_and_privilege_failures_are_distinguished(self):
        for state,expected in [('42501','permission_denied'),('42703','column_missing'),('3D000','database_missing')]:
            error=Exception('PRIVATE_SENTINEL');error.sqlstate=state
            self.assertEqual(self.observe_error(error)['diagnosis'],expected)

    def test_cyclic_exception_chain_stops_and_success_payload_is_unchanged(self):
        error=Exception('PRIVATE_SENTINEL');error.__context__=error
        self.assertEqual(self.observe_error(error)['diagnosis'],'undetermined')
        self.assertEqual(inventory.observe(lambda:17),{'status':'ok','data':17})


if __name__=='__main__':unittest.main()
