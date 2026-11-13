"""Filtro de contenido adulto en el cliente de TMDB (13/11/2026).

Gonza pidió que nada de lo que la app lista o recomienda traiga títulos para
adultos. El punto más central es `TMDBClient`: todo lo que llega de TMDB (Inicio,
Buscar, el chatbot, el seed, similares) pasa por `_request`, así que filtrar ahí
cubre todos los caminos de una vez.

Cada test arma un `httpx.MockTransport`: un «TMDB falso» que devuelve el JSON que
queramos, sin red. Es el equivalente de un mock de un servicio HTTP en Java.
"""

import httpx
from django.test import SimpleTestCase

from catalogo.client import KEYWORD_SOFTCORE, TMDBClient
from catalogo.exceptions import TMDBNotFound


def cliente(cuerpo, pedidos=None):
    """Un `TMDBClient` cuyo TMDB siempre responde `cuerpo` y anota los pedidos."""

    def handler(request):
        if pedidos is not None:
            pedidos.append(request)
        return httpx.Response(200, json=cuerpo)

    return TMDBClient(api_key="k", transport=httpx.MockTransport(handler))


class ParametrosTests(SimpleTestCase):
    def test_discover_y_search_piden_include_adult_false_explicito(self):
        # TMDB ya lo asume en `false`, pero un default ajeno no es una garantía.
        pedidos = []
        c = cliente({"results": []}, pedidos)

        c.discover("movie")
        c.search("algo", "tv")
        c.search_person("alguien")

        for pedido in pedidos:
            self.assertEqual(pedido.url.params["include_adult"], "false")

    def test_discover_excluye_la_keyword_softcore(self):
        pedidos = []
        cliente({"results": []}, pedidos).discover("movie")

        self.assertEqual(
            pedidos[0].url.params["without_keywords"], str(KEYWORD_SOFTCORE)
        )


class ListasTests(SimpleTestCase):
    def test_saca_de_results_lo_que_tmdb_marca_adult(self):
        cuerpo = {
            "results": [
                {"id": 1, "adult": False},
                {"id": 2, "adult": True},
                {"id": 3},  # sin el campo: se conserva
            ]
        }

        for llamada in (
            lambda c: c.get_trending(),
            lambda c: c.get_now_playing(),
            lambda c: c.discover("tv"),
            lambda c: c.search("x", "movie"),
            lambda c: c.get_recommendations(9, "movie"),
        ):
            ids = [r["id"] for r in llamada(cliente(cuerpo))["results"]]
            self.assertEqual(ids, [1, 3])

    def test_saca_los_creditos_de_una_persona_marcados_adult(self):
        cuerpo = {
            "cast": [{"id": 1, "adult": True}, {"id": 2, "adult": False}],
            "crew": [{"id": 3, "adult": True}],
        }

        creditos = cliente(cuerpo).get_person_credits(7)

        self.assertEqual([x["id"] for x in creditos["cast"]], [2])
        self.assertEqual(creditos["crew"], [])

    def test_la_busqueda_de_personas_no_deja_pasar_known_for_adulto(self):
        cuerpo = {
            "results": [
                {
                    "id": 5,
                    "adult": False,
                    "known_for": [{"id": 1, "adult": True}, {"id": 2}],
                },
                {"id": 6, "adult": True, "known_for": []},
            ]
        }

        personas = cliente(cuerpo).search_person("x")["results"]

        self.assertEqual([p["id"] for p in personas], [5])
        self.assertEqual([k["id"] for k in personas[0]["known_for"]], [2])

    def test_una_respuesta_sin_listas_pasa_igual(self):
        self.assertEqual(cliente({"ok": True}).get_genres("movie"), {"ok": True})


class DetalleTests(SimpleTestCase):
    def test_el_detalle_de_un_titulo_adulto_es_como_si_no_existiera(self):
        # `TMDBNotFound` es lo que ya convierte la vista en 404 (Not Found) y lo
        # que hace que la materialización no guarde la fila.
        c = cliente({"id": 1, "adult": True, "title": "x"})

        with self.assertRaises(TMDBNotFound):
            c.get_movie_detail(1)
        with self.assertRaises(TMDBNotFound):
            c.get_tv_detail(1)

    def test_el_detalle_normal_pasa(self):
        c = cliente({"id": 1, "adult": False, "title": "x"})

        self.assertEqual(c.get_movie_detail(1)["title"], "x")
