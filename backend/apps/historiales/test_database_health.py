from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.historiales.application.database_health import DatabaseHealthService
from apps.historiales.domain.institutions import Institution


class DatabaseHealthServiceTests(SimpleTestCase):
    def ejecutar_con_fallo(self, institucion_afectada, *, error=None):
        adaptadores = {}
        for institucion in Institution:
            adaptador = Mock()
            adaptador.health_check.return_value = institucion != institucion_afectada
            if institucion == institucion_afectada and error is not None:
                adaptador.health_check.side_effect = error
            adaptadores[institucion] = adaptador
        with patch(
            "apps.historiales.application.database_health.AdapterFactory.create",
            side_effect=adaptadores.__getitem__,
        ) as crear:
            resultado = DatabaseHealthService().execute()
        self.assertEqual(crear.call_count, len(Institution))
        for adaptador in adaptadores.values():
            adaptador.health_check.assert_called_once_with()
        return resultado

    def test_resultado_false_se_respeta_en_cualquiera_de_los_motores(self):
        for afectada in Institution:
            with self.subTest(institucion=afectada.value.slug):
                resultado = self.ejecutar_con_fallo(afectada)
                self.assertEqual(len(resultado), len(Institution))
                for institucion in Institution:
                    estado = resultado[institucion.value.slug]
                    self.assertIs(estado["connected"], institucion != afectada)
                    self.assertEqual(estado["institution"], institucion.value.name)
                    self.assertEqual(estado["engine"], institucion.value.engine)

    def test_todos_conectados(self):
        resultado = self.ejecutar_con_fallo(None)
        self.assertTrue(all(estado["connected"] is True for estado in resultado.values()))

    def test_excepcion_no_impide_verificar_los_demas_motores(self):
        resultado = self.ejecutar_con_fallo(
            Institution.PEDIATRICO, error=ConnectionError("Fallo DEMO")
        )
        self.assertIs(resultado["pediatrico"]["connected"], False)
        self.assertEqual(resultado["pediatrico"]["error"], "Fallo DEMO")
        self.assertIs(resultado["hospital"]["connected"], True)
        self.assertIs(resultado["laboratorio"]["connected"], True)
        self.assertIs(resultado["odontologica"]["connected"], True)

    def test_endpoint_no_anuncia_conexion_si_adaptador_devuelve_false(self):
        adaptador = Mock()
        adaptador.health_check.return_value = False
        with patch(
            "apps.historiales.application.database_health.AdapterFactory.create",
            return_value=adaptador,
        ):
            respuesta = self.client.get("/api/health/databases/")
        self.assertEqual(respuesta.status_code, 200)
        estados = respuesta.json()["databases"]
        self.assertEqual(set(estados), {institucion.value.slug for institucion in Institution})
        self.assertTrue(all(estado["connected"] is False for estado in estados.values()))
