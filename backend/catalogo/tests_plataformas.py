"""Plataformas de la ficha: servicio, vista y caché de `watch/providers`.

La respuesta de TMDB trae todos los países; se cachea por título (12 h) con
respaldo de 7 días, sin pasar por PostgreSQL.
"""

import copy
from unittest.mock import patch

import fakeredis
import httpx
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from catalogo.cache import RESPALDO_TTLS, TMDBClientCache
from catalogo.client import TMDBClient
from catalogo.exceptions import TMDBServerError
from catalogo.services.plataformas import plataformas

NETFLIX = {
    "logo_path": "/netflix.jpg",
    "provider_id": 8,
    "provider_name": "Netflix",
    "display_priority": 0,
}
MAX = {
    "logo_path": "/max.jpg",
    "provider_id": 1899,
    "provider_name": "Max",
    "display_priority": 5,
}
TUBI = {
    "logo_path": "/tubi.jpg",
    "provider_id": 73,
    "provider_name": "Tubi",
    "display_priority": 2,
}
APPLE = {
    "logo_path": "/apple.jpg",
    "provider_id": 2,
    "provider_name": "Apple TV",
    "display_priority": 1,
}

# Recorte con la forma real de `movie/157336/watch/providers`.
RESPUESTA_TMDB = {
    "id": 157336,
    "results": {
        "AR": {
            "link": "https://www.themoviedb.org/movie/157336/watch?locale=AR",
            # Desordenado a propósito: Max (5) viene antes que Netflix (0).
            "flatrate": [MAX, NETFLIX],
            "free": [TUBI],
            # Tubi también está con anuncios: no debe repetirse en `gratis`.
            "ads": [{**TUBI, "display_priority": 9}, APPLE],
            "rent": [APPLE],
            "buy": [APPLE, NETFLIX],
        },
        "BR": {
            "link": "https://www.themoviedb.org/movie/157336/watch?locale=BR",
            "flatrate": [NETFLIX],
        },
        "ES": {"link": "https://www.themoviedb.org/movie/157336/watch?locale=ES"},
    },
}


class ServicioFalso:
    def __init__(self, respuesta=None):
        self.respuesta = RESPUESTA_TMDB if respuesta is None else respuesta
        self.pedidos = []

    def get_watch_providers(self, id_tmdb, tipo):
        self.pedidos.append((id_tmdb, tipo))
        return copy.deepcopy(self.respuesta)


class ServicioPlataformasTests(SimpleTestCase):
    def test_agrupa_ordena_por_prioridad_y_une_free_con_ads(self):
        datos = plataformas(ServicioFalso(), "movie", 157336, "AR")

        self.assertEqual(datos["pais"], "AR")
        self.assertEqual(
            datos["enlace"], "https://www.themoviedb.org/movie/157336/watch?locale=AR"
        )
        self.assertEqual(
            [p["nombre"] for p in datos["suscripcion"]], ["Netflix", "Max"]
        )
        # Free y ads juntos, por prioridad y sin repetir a Tubi.
        self.assertEqual([p["nombre"] for p in datos["gratis"]], ["Apple TV", "Tubi"])
        self.assertEqual([p["nombre"] for p in datos["alquiler"]], ["Apple TV"])
        self.assertEqual(
            [p["nombre"] for p in datos["compra"]], ["Netflix", "Apple TV"]
        )

    def test_cada_item_lleva_id_nombre_y_logo_de_tmdb(self):
        datos = plataformas(ServicioFalso(), "movie", 157336, "BR")

        self.assertEqual(
            datos["suscripcion"],
            [{"id": 8, "nombre": "Netflix", "logo": "/netflix.jpg"}],
        )
        self.assertEqual(datos["gratis"], [])

    def test_pais_sin_datos_devuelve_grupos_vacios_y_enlace_nulo(self):
        vacio = {
            "pais": "CN",
            "enlace": None,
            "suscripcion": [],
            "gratis": [],
            "alquiler": [],
            "compra": [],
        }
        # Un país que TMDB no trae y otro que trae solo el enlace.
        self.assertEqual(plataformas(ServicioFalso(), "movie", 157336, "CN"), vacio)
        self.assertEqual(
            plataformas(ServicioFalso(), "movie", 157336, "ES"), {**vacio, "pais": "ES"}
        )

    def test_respuesta_sin_results_no_falla(self):
        datos = plataformas(ServicioFalso({"id": 1}), "tv", 1, "AR")

        self.assertIsNone(datos["enlace"])
        self.assertEqual(datos["suscripcion"], [])


class ProvidersViewTests(SimpleTestCase):
    def _get(self, url, servicio=None):
        servicio = servicio or ServicioFalso()
        with patch(
            "catalogo.views.get_catalog_service",
            side_effect=lambda idioma=None: servicio,
        ):
            return APIClient().get(url), servicio

    def test_pelicula_y_serie_son_publicas_y_usan_su_tipo(self):
        for tipo in ("movie", "tv"):
            with self.subTest(tipo=tipo):
                respuesta, servicio = self._get(
                    f"/api/catalogo/{tipo}/157336/providers/?pais=AR"
                )

                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(servicio.pedidos, [(157336, tipo)])
                self.assertEqual(respuesta.json()["pais"], "AR")
                self.assertEqual(respuesta.json()["suscripcion"][0]["id"], 8)

    def test_sin_pais_o_con_pais_invalido_responde_400_con_su_codigo(self):
        for query in ("", "?pais=", "?pais=ZZ", "?pais=ar", "?pais=ARG"):
            with self.subTest(query=query):
                respuesta, servicio = self._get(
                    f"/api/catalogo/movie/157336/providers/{query}"
                )

                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(
                    respuesta.json()["errors"],
                    [{"field": "pais", "code": "country_invalid", "params": {}}],
                )
                self.assertEqual(servicio.pedidos, [])

    def test_id_invalido_responde_400(self):
        respuesta, _ = self._get("/api/catalogo/movie/abc/providers/?pais=AR")

        self.assertEqual(respuesta.status_code, 400)


class CachePlataformasTests(SimpleTestCase):
    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        self.pedidos = 0
        self.falla = False

        def handler(request):
            self.pedidos += 1
            if self.falla:
                return httpx.Response(503, json={})
            return httpx.Response(200, json=RESPUESTA_TMDB)

        cliente = TMDBClient(api_key="test-key", transport=httpx.MockTransport(handler))
        self.cache = TMDBClientCache(cliente, self.redis)
        parche = patch("catalogo.client.time.sleep")
        parche.start()
        self.addCleanup(parche.stop)

    def test_un_solo_llamado_a_tmdb_sirve_a_dos_paises(self):
        ar = plataformas(self.cache, "movie", 157336, "AR")
        br = plataformas(self.cache, "movie", 157336, "BR")

        self.assertEqual(self.pedidos, 1)
        self.assertEqual(len(ar["suscripcion"]), 2)
        self.assertEqual(len(br["suscripcion"]), 1)

    def test_no_localiza_la_clave_por_idioma(self):
        self.cache.get_watch_providers(157336, "movie")

        claves = self.redis.keys("tmdb:watch_providers:*")
        self.assertEqual(len(claves), 1)
        self.assertLessEqual(self.redis.ttl(claves[0]), 12 * 3600)
        self.assertGreater(self.redis.ttl(claves[0]), 12 * 3600 - 60)

    def test_respaldo_de_7_dias_y_error_pasado_ese_tiempo(self):
        self.cache.get_watch_providers(157336, "movie")
        (respaldo,) = self.redis.keys("tmdb:respaldo:watch_providers:*")
        self.assertGreater(
            self.redis.ttl(respaldo), RESPALDO_TTLS["watch_providers"] - 60
        )
        self.assertEqual(RESPALDO_TTLS["watch_providers"], 7 * 24 * 3600)

        # Vence la copia de 12 h con TMDB caído: dentro de los 7 días se sirve.
        self.redis.delete(*self.redis.keys("tmdb:watch_providers:*"))
        self.falla = True
        self.assertEqual(
            self.cache.get_watch_providers(157336, "movie"), RESPUESTA_TMDB
        )

        # Pasados los 7 días el respaldo ya no está y el error llega a la vista.
        self.redis.delete(respaldo)
        with self.assertRaises(TMDBServerError):
            self.cache.get_watch_providers(157336, "movie")
