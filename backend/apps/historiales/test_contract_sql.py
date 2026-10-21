"""Consistencia de ejemplos C0; no acredita endpoints ni persistencia SQL."""

import json
from datetime import date
from pathlib import Path

from django.test import SimpleTestCase

from apps.historiales.domain.institutions import Institution


class EjemplosContratoTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ruta = Path(__file__).parent / "fixtures" / "contrato_v1.json"
        cls.contrato = json.loads(ruta.read_text(encoding="utf-8"))
        cls.casos = {caso["id"]: caso for caso in cls.contrato["cases"]}

    def cuerpo(self, operacion):
        return self.casos[operacion]["response"]["body"]

    def test_ejemplos_preservan_textos_utf8(self):
        self.assertEqual(
            self.casos["API-04"]["invalid"]["response"]["body"]["error"]["message"],
            "Datos inválidos",
        )
        self.assertEqual(self.cuerpo("API-09")["via_administracion"], "Vía DEMO")
        self.assertNotIn("?", json.dumps(self.contrato, ensure_ascii=False))
        self.assertNotIn("\ufffd", json.dumps(self.contrato, ensure_ascii=False))

    def test_cubre_diez_operaciones_del_plan_sin_duplicados(self):
        self.assertEqual(len(self.contrato["cases"]), 10)
        self.assertEqual(set(self.casos), {f"API-{n:02}" for n in range(1, 11)})
        self.assertEqual(self.contrato["status"], "propuesto-no-ratificado")
        esperadas = [
            ("POST", "/api/auth/login/"),
            ("GET", "/api/auth/me/"),
            ("GET", "/api/pacientes/"),
            ("POST", "/api/pacientes/"),
            ("GET", "/api/pacientes/DEMO-P-1/historial/"),
            ("POST", "/api/pacientes/DEMO-P-1/consultas/"),
            ("POST", "/api/consultas/DEMO-C-1/diagnosticos/"),
            ("POST", "/api/diagnosticos/DEMO-D-1/tratamientos/"),
            ("POST", "/api/tratamientos/DEMO-T-1/recetas/"),
            ("PATCH", "/api/pacientes/DEMO-P-1/estado/"),
        ]
        for numero, (metodo, ruta) in enumerate(esperadas, 1):
            with self.subTest(operacion=numero):
                caso = self.casos[f"API-{numero:02}"]
                self.assertEqual((caso["method"], caso["path"]), (metodo, ruta))
                self.assertEqual(caso["response"]["status"], 201 if numero in (4, 6, 7, 8, 9) else 200)

    def test_historial_preserva_relaciones_y_dtos_de_escritura(self):
        historial = self.cuerpo("API-05")
        self.assertEqual(historial["paciente"], self.cuerpo("API-04"))
        consulta = historial["consultas"][0]
        diagnostico = consulta["diagnosticos"][0]
        tratamiento = diagnostico["tratamientos"][0]
        receta = tratamiento["recetas"][0]
        for objeto, operacion, coleccion in (
            (consulta, "API-06", "diagnosticos"),
            (diagnostico, "API-07", "tratamientos"),
            (tratamiento, "API-08", "recetas"),
            (receta, "API-09", None),
        ):
            self.assertEqual({k: v for k, v in objeto.items() if k != coleccion}, self.cuerpo(operacion))
        self.assertEqual(consulta["paciente_id"], historial["paciente"]["id"])
        self.assertEqual(diagnostico["consulta_id"], consulta["id"])
        self.assertEqual(tratamiento["diagnostico_id"], diagnostico["id"])
        self.assertEqual(receta["tratamiento_id"], tratamiento["id"])

    def test_respuestas_no_exponen_secretos_y_usan_ids_string(self):
        def comprobar(valor, *, campos_error=False):
            if isinstance(valor, dict):
                for clave, contenido in valor.items():
                    self.assertNotIn(clave, {"password", "contrasena", "contrasena_hash", "motor", "engine"})
                    if clave == "id" or clave.endswith("_id"):
                        if contenido is not None:
                            self.assertIsInstance(contenido, str)
                            self.assertTrue(contenido)
                    if (
                        not campos_error
                        and clave in {"fecha", "fecha_nacimiento", "fecha_archivo"}
                        and contenido is not None
                    ):
                        self.assertEqual(date.fromisoformat(contenido).isoformat(), contenido)
                    comprobar(contenido, campos_error=campos_error or clave == "fields")
            elif isinstance(valor, list):
                for elemento in valor:
                    comprobar(elemento, campos_error=campos_error)

        for caso in self.casos.values():
            comprobar(caso["response"]["body"])
            comprobar(caso["invalid"]["response"]["body"])

    def test_casos_negativos_y_errores_tienen_formato_comun(self):
        for operacion, caso in self.casos.items():
            with self.subTest(operacion=operacion):
                negativo = caso["invalid"]
                respuesta = negativo["response"]
                error = respuesta["body"]["error"]
                self.assertEqual(set(error), {"code", "message", "fields"})
                self.assertIsInstance(error["fields"], dict)
                if operacion in {"API-01", "API-02"}:
                    self.assertEqual((respuesta["status"], error["code"]), (401, "UNAUTHORIZED"))
                elif operacion == "API-05":
                    self.assertEqual((respuesta["status"], error["code"]), (404, "NOT_FOUND"))
                    self.assertNotEqual(negativo["path"], caso["path"])
                else:
                    self.assertEqual((respuesta["status"], error["code"]), (400, "VALIDATION_ERROR"))
                    self.assertTrue(error["fields"])
                    self.assertNotEqual(negativo["request"], caso["request"])
                    for campo, mensajes in error["fields"].items():
                        self.assertIn(campo, negativo["request"])
                        self.assertIsInstance(mensajes, list)
                        self.assertTrue(all(isinstance(m, str) and m for m in mensajes))

    def test_listado_paginacion_y_archivo_preservan_paciente(self):
        pagina = self.cuerpo("API-03")
        paciente = self.cuerpo("API-04")
        self.assertEqual(pagina, {"count": 1, "limit": 20, "offset": 0, "results": [paciente]})
        archivado = self.cuerpo("API-10")
        for campo in ("id", "identificacion", "nombres", "apellidos", "fecha_nacimiento"):
            self.assertEqual(archivado[campo], paciente[campo])
        self.assertEqual(archivado["estado"], "archivado")
        self.assertEqual(archivado["motivo_archivo"], self.casos["API-10"]["request"]["motivo"])
        self.assertIsNotNone(archivado["fecha_archivo"])

    def test_institucion_existente_y_sin_selector_en_escrituras(self):
        usuario = self.cuerpo("API-01")["usuario"]
        self.assertEqual(usuario, self.cuerpo("API-02")["usuario"])
        self.assertEqual(Institution.from_slug(usuario["institucion"]), Institution.HOSPITAL)
        for caso in self.casos.values():
            for campo in ("motor", "institucion", "usuario_id", "medico_id"):
                self.assertNotIn(campo, caso["request"])
