"""Configuración propia de Mongo; no requiere servidor ni base Django."""
import os
import unittest
from unittest.mock import patch

from apps.historiales.infrastructure.adapters.mongo_adapter import MongoAdapter


class MongoConnectionTests(unittest.TestCase):
    def check_uri(self, environment, expected):
        with patch.dict(os.environ, environment, clear=True), patch(
            "apps.historiales.infrastructure.adapters.mongo_adapter.MongoClient"
        ) as client:
            client.return_value.admin.command.return_value = {"ok": 1}
            self.assertTrue(MongoAdapter().health_check())
            client.assert_called_once_with(expected, serverSelectionTimeoutMS=3000)
            client.return_value.close.assert_called_once_with()

    def test_fallback_matches_standalone_compose(self):
        self.check_uri({}, "mongodb://mongo:27017/laboratorio")

    def test_explicit_replica_set_configuration_is_preserved(self):
        uri = "mongodb://mongo:27017/laboratorio?replicaSet=rs0"
        self.check_uri({"MONGO_URI": uri}, uri)

    def test_failed_ping_closes_connection(self):
        with patch("apps.historiales.infrastructure.adapters.mongo_adapter.MongoClient") as client:
            client.return_value.admin.command.side_effect = RuntimeError("DEMO ping fallido")
            with self.assertRaisesRegex(RuntimeError, "DEMO ping fallido"):
                MongoAdapter().health_check()
            client.return_value.close.assert_called_once_with()
