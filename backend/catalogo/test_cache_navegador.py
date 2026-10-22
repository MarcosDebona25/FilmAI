"""Caché del navegador y compresión de las respuestas públicas del catálogo."""

import gzip
import json
from unittest.mock import patch

from django.test import TestCase

from catalogo.views import CACHE_NAVEGADOR_SEGUNDOS

# Suficiente texto para superar el mínimo de 200 bytes de `gzip_page`.
LISTADO = {"results": [{"id": i, "title": f"Película {i}"} for i in range(30)]}


@patch("catalogo.views.materializar_listado_en_segundo_plano")
@patch("catalogo.views.get_catalog_service")
class CacheNavegadorCatalogoTests(TestCase):
    url = "/api/catalogo/discover/?tipo=movie"

    def test_un_200_se_puede_cachear_y_varia_con_el_idioma(self, get_service, _encolar):
        get_service.return_value.discover.return_value = LISTADO

        respuesta = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE="es")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("public", respuesta["Cache-Control"])
        self.assertIn(f"max-age={CACHE_NAVEGADOR_SEGUNDOS}", respuesta["Cache-Control"])
        # El mismo URL en otro idioma es otra respuesta: sin este `Vary`, el
        # navegador serviría los títulos en español a quien cambió a inglés.
        self.assertIn("Accept-Language", respuesta["Vary"])

    def test_un_error_no_se_cachea(self, get_service, _encolar):
        respuesta = self.client.get("/api/catalogo/discover/?tipo=book")

        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.has_header("Cache-Control"))

    def test_se_comprime_si_el_cliente_acepta_gzip(self, get_service, _encolar):
        get_service.return_value.discover.return_value = LISTADO

        respuesta = self.client.get(self.url, HTTP_ACCEPT_ENCODING="gzip")

        self.assertEqual(respuesta["Content-Encoding"], "gzip")
        self.assertEqual(json.loads(gzip.decompress(respuesta.content)), LISTADO)

    def test_sin_gzip_en_el_pedido_va_sin_comprimir(self, get_service, _encolar):
        get_service.return_value.discover.return_value = LISTADO

        respuesta = self.client.get(self.url)

        self.assertFalse(respuesta.has_header("Content-Encoding"))
        self.assertEqual(respuesta.json(), LISTADO)
