"""La conexión a TMDB se reutiliza: más tiempo ociosa y compartida entre idiomas.

httpx cierra por defecto las conexiones que pasan 5 s sin usarse, y volver a
abrir TLS contra TMDB cuesta ~300 ms (medido el 13/11/2026). Además, el idioma
de respaldo (inglés) usaba su propio cliente y abría su propia conexión.
"""

from unittest.mock import MagicMock, patch

import httpx
from django.test import SimpleTestCase

from catalogo.client import KEEPALIVE_SEGUNDOS, TMDBClient, crear_http_client
from catalogo.services import tmdb as servicio_tmdb


class ConexionOciosaTests(SimpleTestCase):
    def test_el_cliente_http_conserva_las_conexiones_60_segundos(self):
        # `httpx.Client` se reemplaza por un Mock (en Java sería un mock de
        # Mockito) para mirar con qué argumentos lo arma `crear_http_client`:
        # `Limits` no se puede consultar después de construido el cliente.
        with patch("catalogo.client.httpx.Client") as falso:
            crear_http_client(base_url="https://x.test", timeout=3)

        limites = falso.call_args.kwargs["limits"]
        self.assertEqual(limites, httpx.Limits(keepalive_expiry=60))
        self.assertEqual(KEEPALIVE_SEGUNDOS, 60)

    def test_tmdbclient_sin_cliente_inyectado_usa_la_misma_configuracion(self):
        with patch("catalogo.client.httpx.Client") as falso:
            TMDBClient(api_key="k")

        self.assertEqual(
            falso.call_args.kwargs["limits"], httpx.Limits(keepalive_expiry=60)
        )

    def test_un_cliente_http_inyectado_se_usa_tal_cual(self):
        http = MagicMock()
        http.get.return_value = httpx.Response(200, json={})
        cliente = TMDBClient(api_key="k", http_client=http)

        cliente._get("/movie/1")

        self.assertIs(cliente._client, http)
        http.get.assert_called_once()


class ClienteCompartidoTests(SimpleTestCase):
    def setUp(self):
        servicio_tmdb.get_catalog_service.cache_clear()
        self.addCleanup(servicio_tmdb.get_catalog_service.cache_clear)

    def test_los_dos_idiomas_comparten_el_mismo_cliente_http(self):
        with patch("catalogo.services.tmdb.get_redis", return_value=MagicMock()):
            ingles = servicio_tmdb.get_catalog_service("en-US")
            espanol = servicio_tmdb.get_catalog_service("es-MX")

        self.assertIsNot(ingles.client, espanol.client)  # idiomas distintos
        self.assertEqual(espanol.client.idioma, "es-MX")
        # ...pero un solo pool de conexiones hacia TMDB.
        self.assertIs(ingles.client._client, espanol.client._client)
