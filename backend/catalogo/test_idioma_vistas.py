"""Pruebas HTTP de selección de idioma, caché y materialización pública."""

from unittest.mock import patch

import fakeredis
import httpx
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from catalogo.cache import TMDBClientCache
from catalogo.client import TMDBClient


class VistasIdiomaTests(SimpleTestCase):
    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        self.llamadas = []
        self.clientes = []
        parche = patch("catalogo.views.get_catalog_service", side_effect=self._servicio)
        parche.start()
        self.addCleanup(parche.stop)
        parche_materializar = patch("catalogo.views.materializar")
        self.materializar = parche_materializar.start()
        self.addCleanup(parche_materializar.stop)
        self.addCleanup(self._cerrar_clientes)
        self.api = APIClient()

    def _servicio(self, idioma=None):
        cliente = TMDBClient(
            api_key="test",
            idioma=idioma,
            transport=httpx.MockTransport(self._respuesta),
        )
        self.clientes.append(cliente)
        return TMDBClientCache(cliente, self.redis)

    def _respuesta(self, request):
        self.llamadas.append(request)
        return httpx.Response(
            200,
            json={
                "id": 550,
                "title": request.url.params.get("language", "global"),
                "results": [],
            },
        )

    def _cerrar_clientes(self):
        for cliente in self.clientes:
            cliente._client.close()

    def test_vistas_localizables_respetan_encabezado_y_default(self):
        """Las seis rutas públicas seleccionan idioma con pesos y regiones."""
        urls = (
            "/api/catalogo/trending/",
            "/api/catalogo/now-playing/",
            "/api/catalogo/discover/?tipo=movie",
            "/api/catalogo/search/?query=Cure&tipo=movie",
            "/api/catalogo/movie/550/",
            "/api/catalogo/tv/1396/",
        )
        for encabezado, esperado in (
            ("", "en-US"),
            ("es-AR", "es-MX"),
            ("es;q=0.2,en-US;q=0.8", "en-US"),
            ("fr;q=1,es-MX;q=0.9", "es-MX"),
            ("es;q=0", "en-US"),
            ("es;q=incorrecto", "en-US"),
        ):
            for url in urls:
                with self.subTest(encabezado=encabezado, url=url):
                    respuesta = self.api.get(url, HTTP_ACCEPT_LANGUAGE=encabezado)
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertEqual(respuesta.data["title"], esperado)
        self.assertEqual(
            {r.url.params["language"] for r in self.llamadas}, {"en-US", "es-MX"}
        )

    def test_mismo_url_separa_idiomas_y_reutiliza_cache(self):
        """Dos clientes HTTP ven su idioma sin repetir llamadas al proveedor."""
        for encabezado, esperado in (("en", "en-US"), ("es", "es-MX")):
            for _ in range(2):
                respuesta = self.api.get(
                    "/api/catalogo/movie/550/", HTTP_ACCEPT_LANGUAGE=encabezado
                )
                self.assertEqual(respuesta.data["title"], esperado)
        self.assertEqual(len(self.llamadas), 2)
        self.assertEqual(len(self.redis.keys("tmdb:movie_detail:*")), 2)
        self.assertEqual(self.materializar.call_count, 4)
        self.materializar.assert_called_with(550, "movie")

    def test_keywords_conserva_contrato_global(self):
        """El encabezado ES no introduce traducción en las keywords canónicas."""
        respuesta = self.api.get(
            "/api/catalogo/keywords/?id_tmdb=550&tipo=movie", HTTP_ACCEPT_LANGUAGE="es"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("language", self.llamadas[0].url.params)
        self.materializar.assert_not_called()
