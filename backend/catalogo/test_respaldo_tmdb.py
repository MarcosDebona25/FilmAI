"""Respaldo de la caché cuando TMDB no responde (CU-008 2.A, CU-019 4.A)."""

from unittest.mock import patch

import fakeredis
import httpx
from django.test import SimpleTestCase

from catalogo.cache import RESPALDO_TTL, TMDBClientCache, _build_key
from catalogo.client import TMDBClient
from catalogo.exceptions import TMDBNotFound, TMDBServerError, TMDBTransportError

TENDENCIAS = {"results": [{"id": 550, "title": "Fight Club", "media_type": "movie"}]}


class RespaldoTMDBTest(SimpleTestCase):
    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        # TMDB responde bien la primera vez; después, lo que diga `self.falla`.
        self.falla = None
        self.pedidos = 0

        def handler(request):
            self.pedidos += 1
            if self.pedidos > 1 and self.falla is not None:
                return self.falla(request)
            return httpx.Response(200, json=TENDENCIAS)

        cliente = TMDBClient(api_key="test-key", transport=httpx.MockTransport(handler))
        self.cache = TMDBClientCache(cliente, self.redis)
        # El cliente reintenta los 5xx con espera: acá no hace falta esperar.
        parche = patch("catalogo.client.time.sleep")
        parche.start()
        self.addCleanup(parche.stop)

    def _vencer_la_copia_normal(self):
        """Simula que pasaron las 6 horas de la caché de tendencias."""
        params = {
            "media_type": "all",
            "time_window": "week",
            "page": 1,
            "language": "en-US",
        }
        self.redis.delete(_build_key("trending", params))

    def test_si_tmdb_devuelve_error_de_servidor_sirve_la_ultima_copia(self):
        self.cache.get_trending()
        self._vencer_la_copia_normal()
        self.falla = lambda request: httpx.Response(
            503, json={"status_message": "caído"}
        )

        self.assertEqual(self.cache.get_trending(), TENDENCIAS)

    def test_si_tmdb_no_responde_sirve_la_ultima_copia(self):
        # Conexión rechazada o tiempo agotado: lo mismo para el usuario.
        self.cache.get_trending()
        self._vencer_la_copia_normal()

        def sin_conexion(request):
            raise httpx.ConnectTimeout("tiempo agotado", request=request)

        self.falla = sin_conexion

        self.assertEqual(self.cache.get_trending(), TENDENCIAS)

    def test_sin_copia_guardada_el_error_sigue_su_camino(self):
        # CU-019 4.A.2: si tampoco hay respaldo, se notifica el error.
        self.falla = lambda request: httpx.Response(500, json={})
        self.pedidos = 1  # que falle desde el primer pedido

        with self.assertRaises(TMDBServerError):
            self.cache.get_trending()

    def test_un_no_existe_no_usa_el_respaldo(self):
        # Un 404 dice algo cierto del pedido: una copia vieja lo escondería.
        self.cache.get_movie_detail(550)
        self.redis.delete(
            _build_key("movie_detail", {"id_tmdb": 550, "language": "en-US"})
        )
        self.falla = lambda request: httpx.Response(404, json={"status_message": "no"})

        with self.assertRaises(TMDBNotFound):
            self.cache.get_movie_detail(550)

    def test_la_copia_de_respaldo_dura_30_dias(self):
        self.cache.get_trending()
        claves = self.redis.keys("tmdb:respaldo:*")

        self.assertEqual(len(claves), 1)
        self.assertGreater(self.redis.ttl(claves[0]), RESPALDO_TTL - 60)

    def test_la_lista_de_cambios_de_la_sync_no_tiene_respaldo(self):
        # La sync nocturna tiene que enterarse si TMDB falla.
        self.cache.get_changes("movie")
        self.assertEqual(self.redis.keys("tmdb:respaldo:*"), [])

        self.redis.flushall()
        self.pedidos = 1

        def sin_conexion(request):
            raise httpx.ConnectError("sin red", request=request)

        self.falla = sin_conexion
        with self.assertRaises(TMDBTransportError):
            self.cache.get_changes("movie")
