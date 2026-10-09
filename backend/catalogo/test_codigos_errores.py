"""OT-32: parámetros, reseñas y errores de TMDB del catálogo llevan código estable."""

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from catalogo.exceptions import (
    TMDBBadRequest,
    TMDBNotFound,
    TMDBRateLimited,
    TMDBServerError,
    TMDBTransportError,
)
from catalogo.factories import CalificacionFactory
from filmai.exceptions import filmai_exception_handler
from usuarios.factories import UsuarioFactory


class CodigosTMDBTests(SimpleTestCase):
    def test_cada_error_de_tmdb_tiene_codigo_y_conserva_estado_y_detail(self):
        casos = (
            (TMDBBadRequest("x"), 400, "upstream_bad_request"),
            (TMDBNotFound("x"), 404, "upstream_not_found"),
            (TMDBRateLimited("x"), 429, "throttled"),
            (TMDBServerError("x"), 502, "upstream_error"),
            (TMDBTransportError("x"), 503, "upstream_unavailable"),
        )
        for exc, estado, codigo in casos:
            with self.subTest(codigo=codigo):
                respuesta = filmai_exception_handler(exc, {})
                self.assertEqual(respuesta.status_code, estado)
                self.assertIn("code", respuesta.data)
                self.assertEqual(respuesta.data["code"], codigo)
                self.assertEqual(respuesta.data["params"], {})
                self.assertEqual(respuesta.data["errors"], [])

    @override_settings(DEBUG=False)
    def test_sin_debug_no_hay_mensaje_interno(self):
        respuesta = filmai_exception_handler(TMDBNotFound("x"), {})
        self.assertNotIn("debug", respuesta.data)


class CodigosParametrosCatalogoTests(TestCase):
    def setUp(self):
        self.cliente = APIClient()

    def _hoja(self, url):
        respuesta = self.cliente.get(url)
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["code"], "validation_error")
        self.assertEqual(len(respuesta.data["errors"]), 1)
        return respuesta.data, respuesta.data["errors"][0]

    def test_id_ausente_es_required_y_conserva_el_texto_heredado(self):
        _cuerpo, hoja = self._hoja("/api/catalogo/keywords/")
        self.assertEqual(hoja["code"], "required")

    def test_busqueda_sin_query(self):
        cuerpo, hoja = self._hoja("/api/catalogo/search/?tipo=movie")
        self.assertNotIn("query", cuerpo)
        self.assertEqual(hoja, {"field": "query", "code": "required", "params": {}})

    def test_tipo_invalido_informa_valores_permitidos(self):
        cuerpo, hoja = self._hoja("/api/catalogo/search/?query=a&tipo=person")
        self.assertNotIn("tipo", cuerpo)
        self.assertEqual(hoja["code"], "invalid_choice")
        self.assertEqual(hoja["params"], {"allowedValues": ["movie", "tv"]})


class CodigosResenasTests(TestCase):
    def test_actualizacion_vacia_informa_los_campos_posibles(self):
        cliente = APIClient()
        usuario = UsuarioFactory()
        cliente.force_authenticate(usuario)
        calificacion = CalificacionFactory(usuario=usuario)
        respuesta = cliente.put(f"/api/reviews/{calificacion.pk}/", {}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["errors"],
            [
                {
                    "field": None,
                    "code": "review_update_empty",
                    "params": {"fieldNames": ["valor", "texto"]},
                }
            ],
        )
