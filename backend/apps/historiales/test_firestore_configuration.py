"""Cloud selection never falls back silently or uses anonymous credentials."""
import os
from unittest.mock import patch
from django.test import SimpleTestCase
from google.auth.credentials import AnonymousCredentials
from google.auth.exceptions import DefaultCredentialsError
from apps.historiales.domain.errors import PersistenciaNoDisponible
from apps.historiales.infrastructure.adapters.firestore_adapter import FirestoreAdapter


class FirestoreConfigurationTests(SimpleTestCase):
    def test_emulator_uses_anonymous_credentials_only_locally(self):
        with patch.dict(os.environ, {'FIRESTORE_EMULATOR_HOST': 'localhost:8080'}, clear=True), patch('apps.historiales.infrastructure.adapters.firestore_adapter.firestore.Client') as client:
            FirestoreAdapter()._client()
            self.assertIsInstance(client.call_args.kwargs['credentials'], AnonymousCredentials)
            self.assertEqual(client.call_args.kwargs['project'], 'demo-historiales')

    def test_cloud_uses_explicit_project_and_adc(self):
        with patch.dict(os.environ, {'FIRESTORE_MODE': 'cloud', 'FIREBASE_PROJECT_ID': 'delivery-real-project'}, clear=True), patch('apps.historiales.infrastructure.adapters.firestore_adapter.firestore.Client') as client:
            FirestoreAdapter()._client()
            client.assert_called_once_with(project='delivery-real-project')

    def test_ambiguous_or_missing_configuration_does_not_open_client(self):
        cases = [{}, {'FIRESTORE_MODE': 'cloud'},
                 {'FIRESTORE_MODE': 'cloud', 'FIREBASE_PROJECT_ID': 'demo-project'},
                 {'FIRESTORE_MODE': 'cloud', 'FIREBASE_PROJECT_ID': 'real-project', 'FIRESTORE_EMULATOR_HOST': 'localhost:8080'},
                 {'FIRESTORE_MODE': 'invalid'}]
        for environment in cases:
            with self.subTest(environment=environment), patch.dict(os.environ, environment, clear=True), patch('apps.historiales.infrastructure.adapters.firestore_adapter.firestore.Client') as client:
                with self.assertRaises(RuntimeError):
                    FirestoreAdapter()._client()
                client.assert_not_called()

    def test_credentials_failure_returns_safe_domain_error(self):
        with patch.dict(os.environ, {'FIRESTORE_MODE': 'cloud', 'FIREBASE_PROJECT_ID': 'real-project'}, clear=True), patch('apps.historiales.infrastructure.adapters.firestore_adapter.firestore.Client', side_effect=DefaultCredentialsError('private diagnostic')):
            with self.assertRaises(PersistenciaNoDisponible) as caught:
                FirestoreAdapter()._transaction(lambda unit: None)
            self.assertNotIn('private', str(caught.exception))
