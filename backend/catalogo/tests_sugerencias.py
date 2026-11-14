"""Pruebas del endpoint de sugerencias `GET /api/catalogo/suggest/` (13/11/2026).

El diseño está en `openspec/changes/busqueda-navbar/design.md` (§1). TMDB se
reemplaza por un servicio falso que responde páginas reales de `search/multi`
capturadas el 14/11/2026 (`test_datos/tmdb_buscar_personas.json`, clave
`multi`): «nolan», «dune», «tom» y «chihiro».
"""

import copy
import json
from pathlib import Path
from unittest.mock import patch

import fakeredis
import httpx
from django.core.cache import cache as dj_cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from catalogo.cache import ENDPOINT_TTLS, TMDBClientCache
from catalogo.client import TMDBClient
from catalogo.services.browse import es_relevante

DATOS = json.loads(
    (Path(__file__).parent / "test_datos" / "tmdb_buscar_personas.json").read_text()
)


class TMDBFalso:
    """Responde las capturas reales de `search/multi` y anota cada llamada."""

    def __init__(self, respuestas=None):
        self.llamadas = []
        # `respuestas` permite armar una búsqueda a medida (casos de borde).
        self.respuestas = respuestas or DATOS["multi"]

    def search_multi(self, query, page=1):
        self.llamadas.append(("search_multi", query, page))
        vacia = {"page": 1, "total_pages": 0, "total_results": 0, "results": []}
        return copy.deepcopy(self.respuestas.get(query, vacia))


class SugerenciasBase(SimpleTestCase):
    def setUp(self):
        # El throttle `sugerencias` guarda su contador en la caché compartida.
        dj_cache.clear()
        # `tmdb` es el servicio en inglés (el de la app y el respaldo del
        # español); `es` es el de español, que solo se usa con `idioma="es"`.
        self.tmdb = TMDBFalso()
        self.es = TMDBFalso()
        servicios = {"en-US": self.tmdb, "es-MX": self.es}
        parche = patch(
            "catalogo.views.get_catalog_service",
            side_effect=lambda idioma=None: servicios[idioma or "en-US"],
        )
        parche.start()
        self.addCleanup(parche.stop)
        # Las sugerencias NO materializan: si algo lo encola, estos fallan.
        self.materializar = [
            patch("catalogo.views.materializar_listado_en_segundo_plano"),
            patch("catalogo.views.materializar_en_segundo_plano"),
        ]
        self.encolados = [p.start() for p in self.materializar]
        for p in self.materializar:
            self.addCleanup(p.stop)
        self.api = APIClient()

    def sugerir(self, idioma="en", **params):
        return self.api.get(
            "/api/catalogo/suggest/", params, HTTP_ACCEPT_LANGUAGE=idioma
        )

    def ok(self, **params):
        respuesta = self.sugerir(**params)
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        return respuesta.data["results"]


class ResultadosTests(SugerenciasBase):
    def test_una_sola_llamada_a_search_multi(self):
        self.ok(q="nolan")

        self.assertEqual(self.tmdb.llamadas, [("search_multi", "nolan", 1)])

    def test_el_texto_llega_sin_espacios_de_mas(self):
        self.ok(q="  nolan ")

        self.assertEqual(self.tmdb.llamadas, [("search_multi", "nolan", 1)])

    def test_una_persona_va_primero_con_su_rol_y_se_ignoran_los_de_poca_fama(self):
        resultados = self.ok(q="nolan")

        primero = resultados[0]
        self.assertEqual(
            primero,
            {
                "media_type": "person",
                "id": 525,
                "name": "Christopher Nolan",
                "rol": "director",
                "gender": 2,
                "profile_path": primero["profile_path"],
            },
        )
        self.assertTrue(primero["profile_path"].endswith(".jpg"))
        nombres = [item.get("name") or item.get("title") for item in resultados]
        # Jonathan Nolan es de Writing (fuera de v1) y «Finding Nolan», sin votos
        # ni popularidad, no pasa el corte.
        self.assertNotIn("Jonathan Nolan", nombres)
        self.assertNotIn("Finding Nolan", nombres)
        # Nolan North (Acting, 2.2) sí: es actor y tiene popularidad.
        self.assertIn("Nolan North", nombres)

    def test_como_mucho_5_resultados_en_el_orden_de_tmdb(self):
        resultados = self.ok(q="tom")

        # TMDB pone 3 series antes que a Tom Holland: el corte a 5 respeta ese
        # orden (no se reserva lugar para las personas).
        self.assertEqual(
            [r.get("name") for r in resultados],
            [
                "Tom & Jerry Kids Show",
                "The Tom and Jerry Show",
                "Talking Tom and Friends",
                "Tom Holland",
                "Tom Turbo",
            ],
        )
        self.assertEqual(resultados[3]["rol"], "actor")

    def test_como_mucho_2_personas(self):
        resultados = self.ok(q="chihiro")

        # Hay 3 personas con popularidad de 1 o más (Yamamoto, Suzuki,
        # Hashimoto): entran las 2 primeras de TMDB.
        personas = [r["name"] for r in resultados if r["media_type"] == "person"]
        self.assertEqual(personas, ["Chihiro Yamamoto", "Chihiro Suzuki"])

    def test_los_titulos_sin_relevancia_no_se_sugieren(self):
        resultados = self.ok(q="dune")

        por_id = {i["id"]: i for i in DATOS["multi"]["dune"]["results"]}
        titulos = [r for r in resultados if r["media_type"] != "person"]
        self.assertTrue(titulos)
        self.assertTrue(all(es_relevante(por_id[r["id"]], "dune") for r in titulos))
        # Dune: Part Three no tiene votos pero sí popularidad (25): pasa.
        self.assertIn("Dune: Part Three", [r.get("title") for r in titulos])
        self.assertLessEqual(len(resultados), 5)

    def test_un_titulo_con_poca_fama_se_descarta_pero_la_persona_se_queda(self):
        resultados = self.ok(q="chihiro")

        nombres = [item.get("name") or item.get("title") for item in resultados]
        self.assertIn("Call Me Chihiro", nombres)
        self.assertNotIn("Chihiro | Akemi", nombres)  # 0 votos, 0.5 de popularidad
        self.assertNotIn("Sato no Chihiro", nombres)  # 1 voto
        # Chihiro Yoshioka (0.4) queda fuera; entre las personas entran 2.
        self.assertNotIn("Chihiro Yoshioka", nombres)

    def test_si_ningun_titulo_pasa_van_los_titulos_como_vienen(self):
        irrelevante = {
            "media_type": "movie",
            "release_date": "2020-01-01",
            "vote_count": 0,
            "popularity": 0.1,
            "poster_path": None,
            "vote_average": 0,
        }
        self.tmdb.respuestas = {
            "raro": {
                "results": [
                    {**irrelevante, "id": i, "title": f"Raro {i}"} for i in range(1, 4)
                ]
            }
        }

        resultados = self.ok(q="raro")

        self.assertEqual(
            [r["title"] for r in resultados], ["Raro 1", "Raro 2", "Raro 3"]
        )

    def test_el_titulo_exacto_pasa_aunque_no_tenga_votos(self):
        resultados = self.ok(q="sato no chihiro")
        self.assertEqual(resultados, [])  # el falso no conoce ese texto

        self.tmdb.respuestas = {
            "sato no chihiro": {
                "results": [
                    {
                        "id": 1,
                        "media_type": "movie",
                        "title": "Sato no Chihiro",
                        "vote_count": 1,
                        "popularity": 0.07,
                    },
                    {
                        "id": 2,
                        "media_type": "movie",
                        "title": "Otra cosa",
                        "vote_count": 0,
                        "popularity": 0.1,
                    },
                ]
            }
        }
        resultados = self.ok(q="sato no chihiro")
        self.assertEqual([r["title"] for r in resultados], ["Sato no Chihiro"])

    def test_los_titulos_llevan_los_campos_de_tmdb_que_usa_el_frontend(self):
        resultados = self.ok(q="dune")

        pelicula = next(r for r in resultados if r["media_type"] == "movie")
        self.assertEqual(
            set(pelicula),
            {
                "media_type",
                "id",
                "title",
                "release_date",
                "poster_path",
                "vote_average",
            },
        )
        serie = next(r for r in resultados if r["media_type"] == "tv")
        self.assertEqual(
            set(serie),
            {
                "media_type",
                "id",
                "name",
                "first_air_date",
                "poster_path",
                "vote_average",
            },
        )

    def test_tipo_person_devuelve_solo_personas_hasta_5(self):
        resultados = self.ok(q="tom", tipo="person")

        self.assertTrue(resultados)
        self.assertTrue(all(r["media_type"] == "person" for r in resultados))
        self.assertLessEqual(len(resultados), 5)
        # Sin el tope de 2 de la lista mezclada: acá sí entran más.
        self.assertGreater(len(resultados), 2)

    def test_otros_departamentos_y_poca_popularidad_quedan_fuera(self):
        self.tmdb.respuestas = {
            "ana": {
                "results": [
                    {
                        "id": 1,
                        "media_type": "person",
                        "name": "Guionista",
                        "known_for_department": "Writing",
                        "popularity": 9,
                    },
                    {
                        "id": 2,
                        "media_type": "person",
                        "name": "Don Nadie",
                        "known_for_department": "Acting",
                        "popularity": 0.99,
                    },
                    {
                        "id": 3,
                        "media_type": "person",
                        "name": "Directora",
                        "known_for_department": "Directing",
                        "popularity": 1,
                        "gender": 1,
                        "profile_path": None,
                    },
                ]
            }
        }

        resultados = self.ok(q="ana")

        self.assertEqual([r["name"] for r in resultados], ["Directora"])
        self.assertEqual(resultados[0]["rol"], "director")

    def test_sin_coincidencias_la_lista_va_vacia(self):
        self.assertEqual(self.ok(q="zzzzzz"), [])

    def test_no_encola_materializacion(self):
        self.ok(q="dune")

        for encolado in self.encolados:
            encolado.assert_not_called()


class ValidacionTests(SugerenciasBase):
    def test_menos_de_2_caracteres(self):
        for q in ("a", " a ", ""):
            with self.subTest(q=q):
                respuesta = self.sugerir(q=q)
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(
                    respuesta.data["errors"],
                    [{"field": "q", "code": "min_length", "params": {"minLength": 2}}],
                )
        self.assertEqual(self.tmdb.llamadas, [])

    def test_sin_el_parametro_tambien_es_min_length(self):
        respuesta = self.api.get("/api/catalogo/suggest/", HTTP_ACCEPT_LANGUAGE="en")

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["errors"][0]["code"], "min_length")

    def test_mas_de_50_caracteres(self):
        respuesta = self.sugerir(q="x" * 51)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["errors"],
            [{"field": "q", "code": "max_length", "params": {"maxLength": 50}}],
        )
        self.assertEqual(self.tmdb.llamadas, [])

    def test_el_largo_se_mide_sin_los_espacios_de_alrededor(self):
        respuesta = self.sugerir(q=f"  {'x' * 50}  ")

        self.assertEqual(respuesta.status_code, 200)

    def test_tipo_invalido(self):
        respuesta = self.sugerir(q="dune", tipo="movie")

        self.assertEqual(respuesta.status_code, 400)
        [error] = respuesta.data["errors"]
        self.assertEqual((error["field"], error["code"]), ("tipo", "invalid_choice"))


class IdiomaTests(SugerenciasBase):
    """En español, el título vacío se completa con el inglés (solo `title`/`name`)."""

    def respuesta_es(self, titulo):
        return {
            "results": [
                {
                    "id": 7,
                    "media_type": "movie",
                    "title": titulo,
                    "overview": "",
                    "release_date": "2024-01-01",
                    "vote_count": 100,
                    "popularity": 10,
                    "poster_path": None,
                    "vote_average": 7,
                }
            ]
        }

    def test_completa_el_titulo_vacio_con_el_ingles(self):
        self.es.respuestas = {"viaje": self.respuesta_es("")}
        self.tmdb.respuestas = {"viaje": self.respuesta_es("The Journey")}

        resultados = self.ok(q="viaje", idioma="es")

        self.assertEqual(resultados[0]["title"], "The Journey")
        self.assertEqual(resultados[0]["campos_en_ingles"], ["title"])
        self.assertEqual(self.tmdb.llamadas, [("search_multi", "viaje", 1)])

    def test_sin_titulos_vacios_no_hay_llamada_extra(self):
        self.es.respuestas = {"viaje": self.respuesta_es("El viaje")}
        self.tmdb.respuestas = {"viaje": self.respuesta_es("The Journey")}

        resultados = self.ok(q="viaje", idioma="es")

        self.assertEqual(resultados[0]["title"], "El viaje")
        # La sinopsis vacía no cuenta: acá solo importa el título.
        self.assertNotIn("campos_en_ingles", resultados[0])
        self.assertEqual(self.tmdb.llamadas, [])


class ThrottleTests(SugerenciasBase):
    def test_tiene_su_propio_limite_de_120_por_minuto(self):
        from django.conf import settings

        from catalogo.views import SuggestView

        self.assertEqual(SuggestView.throttle_scope, "sugerencias")
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["sugerencias"], "120/min"
        )

    def test_el_pedido_121_recibe_429(self):
        estados = [self.sugerir(q="dune").status_code for _ in range(121)]

        self.assertEqual(estados.count(429), 1)
        self.assertEqual(estados[-1], 429)

    def test_no_gasta_el_limite_de_las_demas_vistas_del_catalogo(self):
        for _ in range(61):
            self.sugerir(q="dune")

        # `catalogo` (60/min) sigue vacío: otra vista del catálogo responde.
        otra = self.api.get(
            "/api/catalogo/genres/?tipo=movie", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertNotEqual(otra.status_code, 429)


class CacheTests(SimpleTestCase):
    """`search_multi` en el cliente y en la caché de Redis (1 h, copia de respaldo)."""

    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        self.pedidos = []

        def handler(request):
            self.pedidos.append(request.url)
            return httpx.Response(
                200, json={"page": 1, "results": [{"id": 1, "adult": True}, {"id": 2}]}
            )

        cliente = TMDBClient(api_key="k", transport=httpx.MockTransport(handler))
        self.cache = TMDBClientCache(cliente, self.redis)

    def test_pide_search_multi_sin_adultos_y_en_el_idioma(self):
        datos = self.cache.search_multi("nolan")

        [url] = self.pedidos
        self.assertTrue(url.path.endswith("/search/multi"), url.path)
        params = dict(url.params)
        self.assertEqual(params["query"], "nolan")
        self.assertEqual(params["include_adult"], "false")
        self.assertEqual(params["language"], "en-US")
        self.assertEqual(params["page"], "1")
        # El cliente saca lo que TMDB marca `adult`.
        self.assertEqual(datos["results"], [{"id": 2}])

    def test_la_segunda_vez_sale_de_redis(self):
        self.cache.search_multi("nolan")
        self.cache.search_multi("nolan")

        self.assertEqual(len(self.pedidos), 1)

    def test_vive_una_hora_y_tiene_copia_de_respaldo(self):
        self.cache.search_multi("nolan")

        self.assertEqual(ENDPOINT_TTLS["search_multi"], 3600)
        self.assertEqual(len(self.redis.keys("tmdb:*")), 2)  # copia normal + respaldo

    def test_otro_texto_es_otra_llamada(self):
        self.cache.search_multi("nolan")
        self.cache.search_multi("dune")

        self.assertEqual(len(self.pedidos), 2)
