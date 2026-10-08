"""El idioma viaja al proveedor y separa caché sin afectar datos globales."""

from unittest.mock import patch

import fakeredis
import httpx
from django.test import SimpleTestCase

from catalogo.cache import TMDBClientCache
from catalogo.client import TMDBClient
from catalogo.services.tmdb import get_catalog_service


class ClienteIdiomaTests(SimpleTestCase):
    def test_metodos_localizables_envian_idioma_explicito(self):
        """Detalle, listas, búsquedas y géneros no dependen del default remoto."""
        for idioma in (None, "es-MX"):
            llamadas = []
            cliente = TMDBClient(
                api_key="test",
                idioma=idioma,
                transport=httpx.MockTransport(
                    lambda r, capturadas=llamadas: (
                        capturadas.append(r) or httpx.Response(200, json={})
                    )
                ),
            )
            try:
                cliente.get_trending()
                cliente.get_now_playing()
                cliente.discover("movie")
                cliente.search("Cure", "movie")
                cliente.get_movie_detail(550)
                cliente.get_tv_detail(1396)
                cliente.get_genres("tv")
                for llamada in llamadas:
                    self.assertEqual(llamada.url.params["language"], idioma or "en-US")
            finally:
                cliente._client.close()

    def test_endpoints_globales_no_reciben_language(self):
        """Keywords, reparto y cambios mantienen el contrato no localizado."""
        llamadas = []
        cliente = TMDBClient(
            api_key="test",
            idioma="es-MX",
            transport=httpx.MockTransport(
                lambda r, capturadas=llamadas: (
                    capturadas.append(r) or httpx.Response(200, json={})
                )
            ),
        )
        try:
            cliente.get_keywords(550, "movie")
            cliente.get_credits(550, "movie")
            cliente.get_changes("movie")
            for llamada in llamadas:
                self.assertNotIn("language", llamada.url.params)
        finally:
            cliente._client.close()

    def test_cache_separa_en_es_y_reutiliza_cada_idioma(self):
        """Una respuesta ES nunca ocupa la entrada EN del mismo título."""
        redis = fakeredis.FakeRedis(decode_responses=True)
        llamadas = []
        clientes = []
        try:
            for idioma in ("en-US", "es-MX"):
                cliente = TMDBClient(
                    api_key="test",
                    idioma=idioma,
                    transport=httpx.MockTransport(
                        lambda r: (
                            llamadas.append(r)
                            or httpx.Response(
                                200, json={"title": r.url.params["language"]}
                            )
                        )
                    ),
                )
                clientes.append(cliente)
                cache = TMDBClientCache(cliente, redis)
                for _ in range(2):
                    self.assertEqual(cache.get_movie_detail(550)["title"], idioma)
            self.assertEqual(len(llamadas), 2)
            self.assertEqual(len(redis.keys("tmdb:movie_detail:*")), 2)
        finally:
            for cliente in clientes:
                cliente._client.close()

    def test_servicios_en_es_son_independientes_y_canonico_comparte_en(self):
        """El cliente público ES no cambia el cliente EN de materialización."""
        get_catalog_service.cache_clear()
        try:
            with patch("catalogo.services.tmdb.get_redis", return_value=object()):
                en = get_catalog_service()
                es = get_catalog_service("es-MX")
                self.assertIs(en, get_catalog_service("en-US"))
                self.assertIs(es, get_catalog_service("es-MX"))
                self.assertIsNot(en, es)
                self.assertEqual(en.client.idioma, "en-US")
                self.assertEqual(es.client.idioma, "es-MX")
                en.client._client.close()
                es.client._client.close()
        finally:
            get_catalog_service.cache_clear()

    def test_idioma_no_soportado_falla_antes_de_hacer_http(self):
        """Solo se admiten las variantes configuradas para la aplicación."""
        with self.assertRaises(ValueError):
            TMDBClient(api_key="test", idioma="es-ES")
