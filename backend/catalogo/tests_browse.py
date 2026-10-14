"""Pruebas de Buscar (C-06): `GET /api/catalogo/browse/` y `genres/?tipo=all`.

El diseño está en `openspec/changes/search-catalogo/design.md`. TMDB se
reemplaza por un servicio falso que responde páginas reales capturadas el
14/10/2026 (`test_datos/tmdb_buscar.json`): «dune» en películas (56 páginas) y
series (5), «the office» en series (3), la página 1 de `discover` y las listas
de géneros. Están recortadas a los campos que mira la lógica.
"""

import copy
import json
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache as dj_cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from catalogo.exceptions import TMDBServerError

DATOS = json.loads(
    (Path(__file__).parent / "test_datos" / "tmdb_buscar.json").read_text()
)


class TMDBFalso:
    """Responde las capturas reales y anota cada llamada."""

    def __init__(self):
        self.llamadas = []
        self.falla_en = None

    def _paginas(self, tipo, query):
        if query == "dune":
            return DATOS[tipo]
        if query == "the office" and tipo == "tv":
            return DATOS["tv_the_office"]
        # Una búsqueda sin coincidencias, con la forma que responde TMDB.
        return {"1": {"page": 1, "total_pages": 0, "total_results": 0, "results": []}}

    def search(self, query, tipo, page=1, anio=None):
        self.llamadas.append(("search", tipo, page, {"anio": anio}))
        if self.falla_en == (tipo, page):
            raise TMDBServerError("TMDB respondió 500")
        paginas = self._paginas(tipo, query)
        return copy.deepcopy(
            paginas.get(str(page)) or {**paginas["1"], "page": page, "results": []}
        )

    def discover(self, tipo, genero=None, anio=None, min_rating=None, page=1, **extra):
        self.llamadas.append(
            (
                "discover",
                tipo,
                page,
                {"genero": genero, "anio": anio, "min_rating": min_rating, **extra},
            )
        )
        return copy.deepcopy(DATOS[f"discover_{tipo}_1"])

    def get_genres(self, tipo):
        return {"genres": copy.deepcopy(DATOS["genres"][tipo])}

    def de(self, metodo, tipo=None):
        return [
            llamada
            for llamada in self.llamadas
            if llamada[0] == metodo and (tipo is None or llamada[1] == tipo)
        ]


class BrowseBase(SimpleTestCase):
    def setUp(self):
        # El throttle `catalogo` guarda su contador en la caché compartida.
        dj_cache.clear()
        self.tmdb = TMDBFalso()
        parche = patch("catalogo.views.get_catalog_service", return_value=self.tmdb)
        parche.start()
        self.addCleanup(parche.stop)
        self.api = APIClient()

    def buscar(self, **params):
        return self.api.get("/api/catalogo/browse/", params, HTTP_ACCEPT_LANGUAGE="en")

    def ok(self, **params):
        respuesta = self.buscar(**params)
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        return respuesta.data


class SinTextoTests(BrowseBase):
    """Sin texto: `discover`, que admite todos los filtros."""

    def test_un_tipo_usa_discover_por_popularidad_con_los_filtros(self):
        datos = self.ok(tipo="movie", genero=878, anio=2021)

        [(_, tipo, page, params)] = self.tmdb.de("discover")
        self.assertEqual((tipo, page), ("movie", 1))
        self.assertEqual(params["genero"], 878)
        self.assertEqual(params["anio"], 2021)
        self.assertEqual(params["sort_by"], "popularity.desc")
        # Sin un mínimo, los primeros puestos se llenan de títulos sin votos.
        self.assertEqual(params["min_votos"], 50)
        self.assertTrue(all(item["media_type"] == "movie" for item in datos["results"]))
        self.assertEqual(len(datos["results"]), 20)

    def test_las_series_populares_dejan_afuera_news_y_talk(self):
        # Sin ellos, la grilla por defecto arranca con programas diarios
        # (Barbara Karlich - Talk, Watch What Happens Live…; 14/10/2026).
        self.ok(tipo="tv")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["sin_generos"], "10763,10767")

    def test_eligiendo_un_genero_no_se_excluye_nada(self):
        self.ok(tipo="tv", genero=10767)

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["genero"], 10767)
        self.assertIsNone(params["sin_generos"])

    def test_las_peliculas_no_excluyen_generos(self):
        self.ok(tipo="movie")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertIsNone(params["sin_generos"])

    def test_un_anio_futuro_no_pide_minimo_de_votos(self):
        # Lo anunciado no tiene votos: 2027 tiene 946 películas en TMDB y
        # ninguna con 50 (verificado el 14/10/2026).
        with patch("catalogo.services.browse.anio_actual", return_value=2026):
            self.ok(tipo="movie", anio=2027)

        [(*_, params)] = self.tmdb.de("discover")
        self.assertIsNone(params["min_votos"])

    def test_el_anio_actual_sigue_pidiendo_el_minimo(self):
        with patch("catalogo.services.browse.anio_actual", return_value=2026):
            self.ok(tipo="movie", anio=2026)

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["min_votos"], 50)

    def test_un_anio_futuro_con_nota_conserva_el_minimo(self):
        # Una nota sin votos no dice nada: filtrar por nota exige el mínimo.
        with patch("catalogo.services.browse.anio_actual", return_value=2026):
            self.ok(tipo="movie", anio=2027, nota="7+")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["min_votos"], 50)

    def test_las_paginas_se_topean_en_500(self):
        # TMDB informa 1001 páginas de `discover` (capturado), pero rechaza
        # pedir más allá de la 500.
        datos = self.ok(tipo="tv")

        self.assertEqual(datos["total_pages"], 500)

    def test_nota_minima_con_al_menos_50_votos(self):
        self.ok(tipo="movie", nota="8+")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["min_rating"], 8)
        self.assertEqual(params["min_votos"], 50)
        self.assertIsNone(params["max_rating"])

    def test_menos_de_5_es_un_techo(self):
        self.ok(tipo="movie", nota="m5")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertIsNone(params["min_rating"])
        self.assertEqual(params["max_rating"], 4.99)
        self.assertEqual(params["min_votos"], 50)

    def test_todo_alterna_peliculas_y_series_y_suma_los_totales(self):
        datos = self.ok()

        tipos = [item["media_type"] for item in datos["results"]]
        self.assertEqual(tipos[:4], ["movie", "tv", "movie", "tv"])
        self.assertEqual(len(tipos), 40)
        pelis, series = DATOS["discover_movie_1"], DATOS["discover_tv_1"]
        self.assertEqual(
            datos["total_results"], pelis["total_results"] + series["total_results"]
        )

    def test_en_todo_el_genero_se_traduce_para_las_series(self):
        # Science Fiction es 878 en películas y Sci-Fi & Fantasy 10765 en series.
        self.ok(genero=878)

        self.assertEqual(self.tmdb.de("discover", "movie")[0][3]["genero"], 878)
        self.assertEqual(self.tmdb.de("discover", "tv")[0][3]["genero"], 10765)

    def test_un_texto_vacio_es_sin_texto(self):
        self.ok(q="   ", tipo="movie")

        self.assertEqual(len(self.tmdb.de("discover")), 1)
        self.assertEqual(self.tmdb.de("search"), [])


class TextoSinFiltrosTests(BrowseBase):
    """Texto sin género ni nota: una búsqueda de TMDB por tipo."""

    def test_un_tipo_es_una_sola_llamada_con_el_anio(self):
        datos = self.ok(q="dune", tipo="movie", anio=2021, page=2)

        self.assertEqual(
            self.tmdb.de("search"), [("search", "movie", 2, {"anio": 2021})]
        )
        self.assertEqual(datos["total_results"], 1115)
        self.assertEqual(datos["total_pages"], 56)
        self.assertEqual(datos["page"], 2)

    def test_el_texto_llega_sin_espacios_de_mas(self):
        self.ok(q="  dune ", tipo="tv")

        self.assertEqual(len(self.tmdb.de("search", "tv")), 1)

    def test_todo_alterna_y_suma(self):
        datos = self.ok(q="dune")

        tipos = [item["media_type"] for item in datos["results"]]
        self.assertEqual(tipos[:4], ["movie", "tv", "movie", "tv"])
        self.assertEqual(datos["total_results"], 1115 + 96)
        self.assertEqual(datos["total_pages"], 56)


class VentanaTests(BrowseBase):
    """Texto con género o nota: los primeros 100 de cada tipo, filtrados acá."""

    def test_pide_hasta_5_paginas_y_filtra_por_genero(self):
        datos = self.ok(q="dune", tipo="movie", genero=878)

        paginas = sorted(llamada[2] for llamada in self.tmdb.de("search", "movie"))
        # TMDB tiene 56 páginas: la ventana se corta en 5.
        self.assertEqual(paginas, [1, 2, 3, 4, 5])
        self.assertEqual(datos["total_results"], 10)
        self.assertEqual(datos["total_pages"], 1)
        self.assertTrue(all(878 in item["genre_ids"] for item in datos["results"]))

    def test_no_pide_paginas_que_tmdb_no_tiene(self):
        self.ok(q="the office", tipo="tv", genero=35)

        paginas = sorted(llamada[2] for llamada in self.tmdb.de("search", "tv"))
        self.assertEqual(paginas, [1, 2, 3])

    def test_pagina_de_a_20_dentro_de_la_ventana(self):
        # Drama en las 100 primeras películas de «dune»: 34.
        primera = self.ok(q="dune", tipo="movie", genero=18)
        segunda = self.ok(q="dune", tipo="movie", genero=18, page=2)

        self.assertEqual((primera["total_results"], primera["total_pages"]), (34, 2))
        self.assertEqual(len(primera["results"]), 20)
        self.assertEqual(len(segunda["results"]), 14)
        ids = {item["id"] for item in primera["results"]}
        self.assertFalse(ids & {item["id"] for item in segunda["results"]})

    def test_la_nota_exige_50_votos(self):
        datos = self.ok(q="dune", tipo="movie", nota="8+")

        self.assertEqual(
            [item["title"] for item in datos["results"]], ["Dune: Part Two"]
        )

    def test_menos_de_5(self):
        datos = self.ok(q="dune", tipo="movie", nota="m5")

        self.assertEqual(datos["total_results"], 2)
        self.assertTrue(all(item["vote_average"] < 5 for item in datos["results"]))
        self.assertTrue(all(item["vote_count"] >= 50 for item in datos["results"]))

    def test_el_anio_sigue_yendo_a_tmdb(self):
        self.ok(q="dune", tipo="movie", genero=878, anio=2021)

        self.assertTrue(
            all(llamada[3] == {"anio": 2021} for llamada in self.tmdb.de("search"))
        )

    def test_todo_con_genero_suma_cada_tipo_con_su_id(self):
        datos = self.ok(q="dune", genero=878)

        # 10 películas de Science Fiction y 6 series de Sci-Fi & Fantasy.
        self.assertEqual(datos["total_results"], 16)
        tipos = [item["media_type"] for item in datos["results"]]
        self.assertEqual(tipos[:4], ["movie", "tv", "movie", "tv"])
        series = [item for item in datos["results"] if item["media_type"] == "tv"]
        self.assertTrue(all(10765 in item["genre_ids"] for item in series))

    def test_un_genero_sin_par_en_series_no_las_pide(self):
        # Horror solo existe en películas.
        datos = self.ok(q="dune", genero=27)

        self.assertEqual(self.tmdb.de("search", "tv"), [])
        self.assertEqual(datos["total_results"], 2)

    def test_un_genero_solo_de_series_no_pide_peliculas(self):
        self.ok(q="dune", genero=10762)

        self.assertEqual(self.tmdb.de("search", "movie"), [])

    def test_un_error_de_tmdb_en_una_pagina_no_se_esconde(self):
        # Una página caída no puede dar un conteo parcial como si fuera real.
        self.tmdb.falla_en = ("movie", 3)

        respuesta = self.buscar(q="dune", tipo="movie", genero=878)

        self.assertEqual(respuesta.status_code, 502)


class ValidacionTests(BrowseBase):
    def test_texto_de_mas_de_50(self):
        respuesta = self.buscar(q="x" * 51)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["errors"],
            [{"field": "q", "code": "max_length", "params": {"maxLength": 50}}],
        )
        self.assertEqual(self.tmdb.llamadas, [])

    def test_el_largo_se_mide_sin_los_espacios_de_alrededor(self):
        # 50 caracteres más espacios: entra, porque se recorta antes de medir.
        respuesta = self.buscar(q=f"  {'x' * 50}  ", tipo="movie")

        self.assertNotEqual(respuesta.status_code, 400)

    def test_tipo_y_nota_invalidos(self):
        for params in ({"tipo": "person"}, {"nota": "10+"}):
            with self.subTest(params):
                respuesta = self.buscar(**params)
                self.assertEqual(respuesta.status_code, 400)
                [error] = respuesta.data["errors"]
                self.assertEqual(error["field"], next(iter(params)))
                self.assertEqual(error["code"], "invalid_choice")

    def test_pagina_mayor_a_500(self):
        respuesta = self.buscar(page=501)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["errors"],
            [{"field": "page", "code": "max_value", "params": {"maxValue": 500}}],
        )


class GenerosTodoTests(BrowseBase):
    def test_suma_a_los_de_peliculas_los_cinco_solo_de_series(self):
        respuesta = self.api.get(
            "/api/catalogo/genres/", {"tipo": "all"}, HTTP_ACCEPT_LANGUAGE="en"
        )

        self.assertEqual(respuesta.status_code, 200)
        ids = [genero["id"] for genero in respuesta.data["genres"]]
        peliculas = [genero["id"] for genero in DATOS["genres"]["movie"]]
        self.assertEqual(ids[: len(peliculas)], peliculas)
        self.assertEqual(ids[len(peliculas) :], [10762, 10763, 10764, 10766, 10767])
