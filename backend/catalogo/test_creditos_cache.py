"""Los créditos se guardan en Redis recortados y una sola vez (13/11/2026).

Redis estaba al 99 % (254 de 256 MB) porque cada título guardaba su respuesta
entera de créditos (hasta 260 KB) y dos veces: la copia normal y la de
respaldo. La ficha usa 50 actores con su personaje y los directores; la
materialización, los nombres de los primeros 10 actores y los directores.
"""

import json
from unittest.mock import patch

import fakeredis
import httpx
from django.test import SimpleTestCase

from catalogo.cache import (
    CREDITOS_FRESCOS_SEGUNDOS,
    ENDPOINT_TTLS,
    RESPALDO_TTL,
    TMDBClientCache,
    _build_key,
)
from catalogo.client import TMDBClient
from catalogo.exceptions import TMDBNotFound, TMDBServerError
from catalogo.services.creditos import creditos
from catalogo.services.materialization import _mapear

CLAVE = _build_key("creditos_ficha", {"id_tmdb": 550, "tipo": "movie"})


def respuesta_de_tmdb(actores=200, equipo=600):
    """Una respuesta de créditos como la real: con cientos de campos de sobra."""
    return {
        "id": 550,
        "cast": [
            {
                "adult": False,
                "gender": 2,
                "id": 1000 + i,
                "known_for_department": "Acting",
                "name": f"Actor {i}",
                "original_name": f"Actor {i}",
                "popularity": 9.5,
                "profile_path": f"/foto{i}.jpg",
                "cast_id": i,
                "character": f"Personaje {i}" if i % 2 == 0 else "",
                "credit_id": f"{i:024d}",
                "order": i,
            }
            for i in range(actores)
        ],
        "crew": [
            {
                "id": 5000 + i,
                "name": f"Equipo {i}",
                "job": "Director" if i < 2 else "Sound Editor",
                "department": "Directing" if i < 2 else "Sound",
                "profile_path": f"/crew{i}.jpg",
                "credit_id": f"{i:024d}",
            }
            for i in range(equipo)
        ],
    }


class CreditosEnRedisTests(SimpleTestCase):
    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        self.pedidos = 0
        self.respuesta = respuesta_de_tmdb()
        self.falla = None  # un `httpx.Response` para simular un error de TMDB

        def handler(request):
            self.pedidos += 1
            return self.falla or httpx.Response(200, json=self.respuesta)

        cliente = TMDBClient(api_key="k", transport=httpx.MockTransport(handler))
        self.cache = TMDBClientCache(cliente, self.redis)

    def _envejecer(self, segundos):
        """Simula que la copia lleva `segundos` guardada (el TTL baja con el tiempo)."""
        self.redis.expire(CLAVE, RESPALDO_TTL - segundos)

    def test_guarda_solo_el_reparto_y_los_directores_que_se_usan(self):
        resultado = self.cache.get_credits(550, "movie")

        self.assertEqual(len(resultado["cast"]), 50)  # lo que muestra la ficha
        self.assertEqual(
            resultado["cast"][0], {"name": "Actor 0", "character": "Personaje 0"}
        )
        self.assertEqual(
            resultado["crew"],
            [
                {"name": "Equipo 0", "job": "Director"},
                {"name": "Equipo 1", "job": "Director"},
            ],
        )
        # Lo que se guardó en Redis es exactamente lo que se devolvió.
        self.assertEqual(json.loads(self.redis.get(CLAVE)), resultado)

    def test_la_copia_guardada_es_mucho_mas_chica_que_la_respuesta_de_tmdb(self):
        entera = len(json.dumps(self.respuesta))

        self.cache.get_credits(550, "movie")
        guardada = len(self.redis.get(CLAVE))

        self.assertGreater(entera, 100_000)
        self.assertLess(guardada, 8_000)
        self.assertLess(guardada * 20, entera)

    def test_se_guarda_una_sola_vez_sin_copia_de_respaldo_aparte(self):
        self.cache.get_credits(550, "movie")

        self.assertEqual(self.redis.keys("tmdb:*"), [CLAVE])
        # Vive 30 días (el respaldo); la frescura de 24 h se mide con ese TTL.
        self.assertEqual(self.redis.ttl(CLAVE), RESPALDO_TTL)
        self.assertEqual(CREDITOS_FRESCOS_SEGUNDOS, ENDPOINT_TTLS["creditos_ficha"])

    def test_dentro_de_las_24_horas_sale_de_redis(self):
        self.cache.get_credits(550, "movie")
        self._envejecer(CREDITOS_FRESCOS_SEGUNDOS - 60)

        self.cache.get_credits(550, "movie")

        self.assertEqual(self.pedidos, 1)

    def test_pasadas_las_24_horas_vuelve_a_pedir_y_renueva_la_copia(self):
        self.cache.get_credits(550, "movie")
        self._envejecer(CREDITOS_FRESCOS_SEGUNDOS + 60)

        self.cache.get_credits(550, "movie")

        self.assertEqual(self.pedidos, 2)
        self.assertEqual(self.redis.ttl(CLAVE), RESPALDO_TTL)

    def test_vencida_y_con_tmdb_caido_sirve_la_ultima_copia(self):
        primera = self.cache.get_credits(550, "movie")
        self._envejecer(CREDITOS_FRESCOS_SEGUNDOS + 60)
        self.falla = httpx.Response(500)

        with patch("catalogo.client.time.sleep"):
            self.assertEqual(self.cache.get_credits(550, "movie"), primera)

    def test_un_no_existe_no_sirve_la_copia_vieja(self):
        self.cache.get_credits(550, "movie")
        self._envejecer(CREDITOS_FRESCOS_SEGUNDOS + 60)
        self.falla = httpx.Response(404)

        with self.assertRaises(TMDBNotFound):
            self.cache.get_credits(550, "movie")

    def test_sin_copia_y_con_tmdb_caido_el_error_sigue(self):
        self.falla = httpx.Response(500)

        with patch("catalogo.client.time.sleep"):
            with self.assertRaises(TMDBServerError):
                self.cache.get_credits(550, "movie")

    def test_ignora_las_entradas_viejas_con_la_forma_anterior(self):
        # Antes la clave era `tmdb:credits:*` y guardaba la respuesta entera.
        vieja = _build_key("credits", {"id_tmdb": 550, "tipo": "movie"})
        self.redis.set(vieja, json.dumps(self.respuesta))

        self.cache.get_credits(550, "movie")

        self.assertEqual(self.pedidos, 1)
        self.assertNotEqual(vieja, CLAVE)

    def test_lo_recortado_alcanza_para_la_ficha_y_la_materializacion(self):
        recortado = self.cache.get_credits(550, "movie")
        entero = self.respuesta

        # Ficha (C-07): mismos directores y mismo reparto con personaje.
        class Servicio:
            def get_credits(self, id_tmdb, tipo):
                return recortado

        class ServicioEntero(Servicio):
            def get_credits(self, id_tmdb, tipo):
                return entero

        self.assertEqual(
            creditos(Servicio(), "movie", 550), creditos(ServicioEntero(), "movie", 550)
        )
        # Materialización (C-04a): mismos directores y los mismos 10 del reparto.
        detalle = {"title": "X", "genres": []}
        con_recorte = _mapear(detalle, recortado, {}, "movie")
        con_todo = _mapear(detalle, entero, {}, "movie")
        self.assertEqual(con_recorte["reparto"], con_todo["reparto"])
        self.assertEqual(con_recorte["directores"], con_todo["directores"])
