"""OT-61: los campos sin traducción se completan con inglés y quedan marcados."""

from unittest.mock import patch

import fakeredis
import httpx
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from catalogo.cache import TMDBClientCache
from catalogo.client import TMDBClient
from catalogo.services.fallback import MARCA, CatalogoConRespaldo

EN = {
    "detalle": {"id": 1, "title": "Cure", "overview": "A detective...", "x": 1},
    "serie": {"id": 2, "name": "The Show", "overview": "About a show"},
    "lista": {
        "page": 1,
        "results": [
            {"id": 1, "media_type": "movie", "title": "Cure", "overview": "EN one"},
            {"id": 1, "media_type": "tv", "name": "Other", "overview": "EN tv"},
            {"id": 3, "media_type": "movie", "title": "Three", "overview": "EN three"},
        ],
    },
}


class Falso:
    """Servicio mínimo que cuenta llamadas y devuelve copias independientes."""

    def __init__(self, datos):
        self.datos = datos
        self.llamadas = []

    def _dar(self, clave, metodo, args):
        import copy

        self.llamadas.append((metodo, args))
        return copy.deepcopy(self.datos[clave])

    def get_movie_detail(self, id_tmdb):
        return self._dar("detalle", "get_movie_detail", (id_tmdb,))

    def get_tv_detail(self, id_tmdb):
        return self._dar("serie", "get_tv_detail", (id_tmdb,))

    def get_trending(self, *args):
        return self._dar("lista", "get_trending", args)

    def search(self, *args):
        return self._dar("lista", "search", args)

    def get_keywords(self, *args):
        return {"keywords": []}


class RespaldoCampoPorCampoTests(SimpleTestCase):
    def _servicio(self, es):
        self.es, self.en = Falso(es), Falso(EN)
        return CatalogoConRespaldo(self.es, self.en)

    def test_sinopsis_vacia_se_completa_y_se_marca(self):
        servicio = self._servicio(
            {"detalle": {"id": 1, "title": "Cura", "overview": "", "x": 9}}
        )
        datos = servicio.get_movie_detail(1)
        self.assertEqual(datos["title"], "Cura")
        self.assertEqual(datos["overview"], "A detective...")
        self.assertEqual(datos[MARCA], ["overview"])
        self.assertEqual(datos["x"], 9)  # nada más se toca

    def test_titulo_vacio_o_nulo_se_completa(self):
        for vacio in ("", "   ", None):
            with self.subTest(vacio=vacio):
                servicio = self._servicio(
                    {"serie": {"id": 2, "name": vacio, "overview": "Sinopsis"}}
                )
                datos = servicio.get_tv_detail(2)
                self.assertEqual(datos["name"], "The Show")
                self.assertEqual(datos["overview"], "Sinopsis")
                self.assertEqual(datos[MARCA], ["name"])

    def test_con_ambos_presentes_no_se_consulta_el_respaldo(self):
        servicio = self._servicio(
            {"detalle": {"id": 1, "title": "Cura", "overview": "Un detective..."}}
        )
        datos = servicio.get_movie_detail(1)
        self.assertEqual(datos[MARCA], [])
        self.assertEqual(self.en.llamadas, [])

    def test_si_el_ingles_tambien_esta_vacio_no_se_marca(self):
        servicio = self._servicio(
            {"detalle": {"id": 1, "title": "Cura", "overview": ""}}
        )
        self.en.datos = {"detalle": {"id": 1, "title": "Cure", "overview": ""}}
        datos = servicio.get_movie_detail(1)
        self.assertEqual(datos["overview"], "")
        self.assertEqual(datos[MARCA], [])

    def test_listado_combina_la_misma_pagina_por_id_y_tipo(self):
        servicio = self._servicio(
            {
                "lista": {
                    "page": 1,
                    "results": [
                        {
                            "id": 1,
                            "media_type": "movie",
                            "title": "Cura",
                            "overview": "",
                        },
                        {"id": 1, "media_type": "tv", "name": "", "overview": "ES tv"},
                        {
                            "id": 3,
                            "media_type": "movie",
                            "title": "Tres",
                            "overview": "ES",
                        },
                        {"id": 9, "media_type": "movie", "title": "", "overview": ""},
                    ],
                }
            }
        )
        datos = servicio.get_trending("all", "week", 2)
        uno, serie, tres, sin_par = datos["results"]
        self.assertEqual((uno["overview"], uno[MARCA]), ("EN one", ["overview"]))
        self.assertEqual((serie["name"], serie[MARCA]), ("Other", ["name"]))
        self.assertEqual((tres["title"], tres[MARCA]), ("Tres", []))
        self.assertEqual((sin_par["title"], sin_par[MARCA]), ("", []))
        # Una sola llamada de respaldo, con los mismos argumentos.
        self.assertEqual(self.en.llamadas, [("get_trending", ("all", "week", 2))])

    def test_listado_completo_no_consulta_el_respaldo(self):
        servicio = self._servicio(
            {"lista": {"results": [{"id": 3, "title": "Tres", "overview": "ES"}]}}
        )
        servicio.search("tres", "movie", 1)
        self.assertEqual(self.en.llamadas, [])

    def test_los_demas_metodos_se_delegan_sin_cambios(self):
        servicio = self._servicio({})
        self.assertEqual(servicio.get_keywords(1, "movie"), {"keywords": []})


class RespaldoPorHTTPTests(SimpleTestCase):
    """De punta a punta con la caché real: claves por idioma y respaldo cacheado."""

    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        self.llamadas = []
        self.clientes = []
        parche = patch("catalogo.views.get_catalog_service", side_effect=self._servicio)
        parche.start()
        self.addCleanup(parche.stop)
        parche = patch("catalogo.views.materializar_en_segundo_plano")
        parche.start()
        self.addCleanup(parche.stop)
        self.addCleanup(lambda: [c._client.close() for c in self.clientes])

    def _servicio(self, idioma=None):
        cliente = TMDBClient(
            api_key="test",
            idioma=idioma,
            transport=httpx.MockTransport(self._respuesta),
        )
        self.clientes.append(cliente)
        return TMDBClientCache(cliente, self.redis)

    def _respuesta(self, request):
        idioma = request.url.params.get("language")
        self.llamadas.append(idioma)
        en = idioma == "en-US"
        return httpx.Response(
            200,
            json={
                "id": 550,
                "title": "Fight Club" if en else "El club de la pelea",
                "overview": "An insomniac..." if en else "",
            },
        )

    def test_espanol_sin_sinopsis_devuelve_la_inglesa_marcada_y_la_cachea(self):
        api = APIClient()
        for _ in range(2):
            datos = api.get(
                "/api/catalogo/movie/550/", HTTP_ACCEPT_LANGUAGE="es"
            ).json()
            self.assertEqual(datos["title"], "El club de la pelea")
            self.assertEqual(datos["overview"], "An insomniac...")
            self.assertEqual(datos[MARCA], ["overview"])
        # Una llamada por idioma: la segunda solicitud sale entera de la caché.
        self.assertEqual(sorted(self.llamadas), ["en-US", "es-MX"])
        self.assertEqual(len(self.redis.keys("tmdb:movie_detail:*")), 2)

    def test_ingles_conserva_el_cuerpo_de_tmdb_sin_marca(self):
        datos = APIClient().get("/api/catalogo/movie/550/").json()
        self.assertNotIn(MARCA, datos)
        self.assertEqual(self.llamadas, ["en-US"])
