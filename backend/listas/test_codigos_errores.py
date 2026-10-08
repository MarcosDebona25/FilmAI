"""OT-32: los errores de `listas` llevan código estable y conservan el formato previo."""

from django.test import TestCase
from rest_framework.test import APIClient

from usuarios.factories import UsuarioFactory

from .models import Lista


class CodigosValidacionListasTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)

    def _crear(self, nombre):
        return self.cliente.post("/api/lists/", {"nombre": nombre}, format="json")

    def _hoja(self, respuesta):
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["code"], "validation_error")
        self.assertIn("nombre", respuesta.data)  # clave heredada intacta
        self.assertEqual(len(respuesta.data["errors"]), 1)
        return respuesta.data["errors"][0]

    def test_nombre_vacio_tras_normalizar_es_blank(self):
        hoja = self._hoja(self._crear("   "))
        self.assertEqual(hoja, {"field": "nombre", "code": "blank", "params": {}})

    def test_nombre_largo_informa_el_limite(self):
        hoja = self._hoja(self._crear("a" * 81))
        self.assertEqual(
            hoja,
            {"field": "nombre", "code": "max_length", "params": {"maxLength": 80}},
        )

    def test_nombre_sin_alfanumericos(self):
        hoja = self._hoja(self._crear("---"))
        self.assertEqual(hoja["code"], "list_name_missing_alphanumeric")

    def test_nombre_con_caracteres_no_permitidos(self):
        hoja = self._hoja(self._crear("Sci-Fi"))
        self.assertEqual(hoja["code"], "list_name_invalid_characters")

    def test_nombre_ausente_es_required(self):
        respuesta = self.cliente.post("/api/lists/", {}, format="json")
        self.assertEqual(self._hoja(respuesta)["code"], "required")

    def test_conflictos_conservan_codigo_heredado_y_sobre(self):
        Lista.objects.create(usuario=self.usuario, nombre="Mi lista")
        respuesta = self._crear("mi lista")
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["codigo"], "nombre_lista_duplicado")
        self.assertEqual(respuesta.data["code"], "list_name_duplicated")

    def test_consulta_de_pertenencia_invalida_informa_campo_y_codigo(self):
        respuesta = self.cliente.get("/api/lists/?id_tmdb=0&tipo=person")
        codigos = {(e["field"], e["code"]) for e in respuesta.data["errors"]}
        self.assertIn(("id_tmdb", "min_value"), codigos)
        self.assertIn(("tipo", "invalid_choice"), codigos)
