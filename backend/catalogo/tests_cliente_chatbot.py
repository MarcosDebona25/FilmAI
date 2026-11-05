"""Lo que el chatbot le pide a TMDB y el catálogo no usaba: similares y personas.

Las respuestas de ejemplo copian la forma real de la API, consultada el
05/11/2026. TMDB no se llama de verdad: `httpx.MockTransport` reemplaza la red.
"""

from unittest.mock import MagicMock

import fakeredis
import httpx
from django.test import SimpleTestCase

from catalogo.cache import TMDBClientCache
from catalogo.client import TMDBClient
from catalogo.services.fallback import CatalogoConRespaldo


def cliente(cuerpo, idioma="en-US"):
    pedidos = []

    def responder(request):
        pedidos.append(request)
        return httpx.Response(200, json=cuerpo)

    transporte = httpx.MockTransport(responder)
    return TMDBClient(api_key="k", transport=transporte, idioma=idioma), pedidos


class ClienteTests(SimpleTestCase):
    def test_similares_de_una_pelicula(self):
        tmdb, pedidos = cliente({"results": [{"id": 1, "title": "Moon"}]})

        datos = tmdb.get_similar(157336, "movie")

        self.assertEqual(pedidos[0].url.path, "/3/movie/157336/similar")
        self.assertEqual(datos["results"][0]["title"], "Moon")

    def test_similares_de_una_serie(self):
        tmdb, pedidos = cliente({"results": []})

        tmdb.get_similar(1399, "tv")

        self.assertEqual(pedidos[0].url.path, "/3/tv/1399/similar")

    def test_buscar_persona_manda_el_nombre(self):
        tmdb, pedidos = cliente({"results": [{"id": 103, "name": "Mark Ruffalo"}]})

        tmdb.search_person("Mark Ruffalo")

        self.assertEqual(pedidos[0].url.path, "/3/search/person")
        self.assertEqual(pedidos[0].url.params["query"], "Mark Ruffalo")

    def test_creditos_de_una_persona_van_en_el_idioma_del_cliente(self):
        # `discover` con `with_people` no sirve: en series TMDB ignora el filtro
        # sin avisar y devuelve cualquier cosa (verificado el 05/11/2026).
        tmdb, pedidos = cliente({"cast": [], "crew": []}, idioma="es-MX")

        tmdb.get_person_credits(103)

        self.assertEqual(pedidos[0].url.path, "/3/person/103/combined_credits")
        self.assertEqual(pedidos[0].url.params["language"], "es-MX")


class CacheTests(SimpleTestCase):
    def setUp(self):
        self.tmdb = MagicMock()
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        self.cache = TMDBClientCache(self.tmdb, self.redis)

    def test_los_tres_metodos_pasan_por_la_cache(self):
        self.tmdb.get_similar.return_value = {"results": []}
        self.tmdb.search_person.return_value = {"results": []}
        self.tmdb.get_person_credits.return_value = {"cast": [], "crew": []}

        for _ in range(2):
            self.cache.get_similar(157336, "movie")
            self.cache.search_person("Mark Ruffalo")
            self.cache.get_person_credits(103)

        self.tmdb.get_similar.assert_called_once()
        self.tmdb.search_person.assert_called_once()
        self.tmdb.get_person_credits.assert_called_once()

    def test_peliculas_y_series_con_el_mismo_id_no_comparten_cache(self):
        self.tmdb.get_similar.side_effect = [{"results": [1]}, {"results": [2]}]

        pelicula = self.cache.get_similar(100, "movie")
        serie = self.cache.get_similar(100, "tv")

        self.assertNotEqual(pelicula, serie)

    def test_cada_idioma_tiene_su_cache(self):
        # Sin esto, quien pregunta en inglés recibiría títulos guardados en español.
        for metodo, argumentos in (
            ("get_similar", (5, "movie")),
            ("search_person", ("Mark",)),
            ("get_person_credits", (103,)),
        ):
            with self.subTest(metodo):
                espanol, ingles = MagicMock(idioma="es-MX"), MagicMock(idioma="en-US")
                getattr(espanol, metodo).return_value = {"titulo": "Luna"}
                getattr(ingles, metodo).return_value = {"titulo": "Moon"}

                getattr(TMDBClientCache(espanol, self.redis), metodo)(*argumentos)
                datos = getattr(TMDBClientCache(ingles, self.redis), metodo)(
                    *argumentos
                )

                self.assertEqual(datos, {"titulo": "Moon"})


class RespaldoTests(SimpleTestCase):
    def test_similares_completa_la_sinopsis_vacia_en_ingles(self):
        servicio, respaldo = MagicMock(), MagicMock()
        servicio.get_similar.return_value = {
            "results": [{"id": 1, "title": "Luna", "overview": ""}]
        }
        respaldo.get_similar.return_value = {
            "results": [{"id": 1, "title": "Moon", "overview": "A man alone."}]
        }

        datos = CatalogoConRespaldo(servicio, respaldo).get_similar(5, "movie")

        self.assertEqual(datos["results"][0]["overview"], "A man alone.")
        self.assertEqual(datos["results"][0]["title"], "Luna")
