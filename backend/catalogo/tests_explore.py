"""Pruebas de Buscar (C-06): `GET /api/catalogo/explore/` y `genres/?tipo=all`.

El diseño está en `openspec/changes/search-catalogo/design.md`. TMDB se
reemplaza por un servicio falso que responde páginas reales capturadas el
14/10/2026 (`test_datos/tmdb_buscar.json`): «dune» en películas (56 páginas) y
series (5), «the office» en series (3), la página 1 de `discover` y las listas
de géneros. Están recortadas a los campos que mira la lógica.
"""

import copy
import json
from datetime import date
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
        datos = copy.deepcopy(DATOS[f"discover_{tipo}_1"])
        # Las capturas no traen `poster_path` y sin póster no entra al
        # descubrimiento (21/11/2026): se les pone uno.
        for item in datos["results"]:
            item.setdefault("poster_path", f"/{item['id']}.jpg")
        return datos

    def get_genres(self, tipo):
        return {"genres": copy.deepcopy(DATOS["genres"][tipo])}

    def de(self, metodo, tipo=None):
        return [
            llamada
            for llamada in self.llamadas
            if llamada[0] == metodo and (tipo is None or llamada[1] == tipo)
        ]


class ExploreBase(SimpleTestCase):
    # Qué servicio falso usa cada clase de tests; una subclase puede cambiarlo.
    Falso = TMDBFalso

    def setUp(self):
        # El throttle `catalogo` guarda su contador en la caché compartida.
        dj_cache.clear()
        self.tmdb = self.Falso()
        parche = patch("catalogo.views.get_catalog_service", return_value=self.tmdb)
        parche.start()
        self.addCleanup(parche.stop)
        # Buscar encola lo que muestra (C-04a); eso consulta la base y estos
        # tests no tienen. Tiene su cobertura en `test_materializar_listados`.
        listado = patch("catalogo.views.materializar_listado_en_segundo_plano")
        listado.start()
        self.addCleanup(listado.stop)
        self.api = APIClient()

    def buscar(self, **params):
        return self.api.get("/api/catalogo/explore/", params, HTTP_ACCEPT_LANGUAGE="en")

    def ok(self, **params):
        respuesta = self.buscar(**params)
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        return respuesta.data


class SinTextoTests(ExploreBase):
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
        with patch("catalogo.services.explore.anio_actual", return_value=2026):
            self.ok(tipo="movie", anio=2027)

        [(*_, params)] = self.tmdb.de("discover")
        self.assertIsNone(params["min_votos"])

    def test_el_anio_actual_sigue_pidiendo_el_minimo(self):
        with patch("catalogo.services.explore.anio_actual", return_value=2026):
            self.ok(tipo="movie", anio=2026)

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["min_votos"], 50)

    def test_un_anio_futuro_con_nota_conserva_el_minimo(self):
        # Una nota sin votos no dice nada: filtrar por nota exige el mínimo.
        with patch("catalogo.services.explore.anio_actual", return_value=2026):
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


class AEstrenarTests(ExploreBase):
    """«A estrenar»: lo que estrena después de hoy (pedido del usuario, 14/10/2026)."""

    def setUp(self):
        super().setUp()
        parche = patch("catalogo.services.explore.hoy", return_value=date(2026, 10, 14))
        parche.start()
        self.addCleanup(parche.stop)

    def test_sin_texto_pide_desde_maniana_sin_minimo_de_votos(self):
        self.ok(tipo="movie", a_estrenar="true")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["desde_fecha"], "2026-10-15")
        self.assertIsNone(params["min_votos"])
        self.assertIsNone(params["anio"])

    def test_con_nota_conserva_el_minimo(self):
        self.ok(tipo="movie", a_estrenar="true", nota="7+")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["min_votos"], 50)

    def test_con_texto_filtra_la_ventana_por_fecha(self):
        # En las 100 primeras películas de «dune» hay dos con fecha posterior
        # al 14/10/2026: Dune: Part Three (15/12) y The Diary of a Chambermaid
        # (23/10).
        datos = self.ok(q="dune", tipo="movie", a_estrenar="true")

        self.assertEqual(len(self.tmdb.de("search", "movie")), 5)
        self.assertEqual(
            sorted(item["title"] for item in datos["results"]),
            ["Dune: Part Three", "The Diary of a Chambermaid"],
        )

    def test_un_valor_que_no_es_true_se_rechaza(self):
        respuesta = self.buscar(a_estrenar="quizas")

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["errors"][0]["field"], "a_estrenar")


class DecadasTests(ExploreBase):
    """Antes de 1990, el año se elige por década (pedido del usuario, 14/10/2026)."""

    def test_sin_texto_pide_la_decada_entera_con_minimo_de_votos(self):
        # Con 50 votos aparecen los clásicos: The Terminator, Back to the Future
        # (1980s, verificado el 14/10/2026).
        self.ok(tipo="movie", decada=1980)

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["desde_fecha"], "1980-01-01")
        self.assertEqual(params["hasta_fecha"], "1989-12-31")
        self.assertIsNone(params["anio"])
        self.assertEqual(params["min_votos"], 50)

    def test_con_texto_filtra_la_ventana_por_el_rango(self):
        # De las 100 primeras películas de «dune», 9 son de los 80 (entre ellas
        # la de David Lynch, 1984) y 5 pasan el corte de relevancia.
        datos = self.ok(q="dune", tipo="movie", decada=1980)

        fechas = [item["release_date"] for item in datos["results"]]
        self.assertEqual(datos["total_results"], 5)
        self.assertTrue(all("1980-01-01" <= fecha <= "1989-12-31" for fecha in fechas))
        self.assertIn("Dune", [item["title"] for item in datos["results"]])

    def test_una_decada_invalida_se_rechaza(self):
        for valor in ("1985", "1890", "3000"):
            with self.subTest(valor):
                respuesta = self.buscar(decada=valor)
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.data["errors"][0]["field"], "decada")


def _puntaje(item):
    return max(item["vote_count"], item.get("popularity", 0) * 100)


class TextoTests(ExploreBase):
    """Con texto: los primeros 100 por tipo, ordenados por votos y popularidad.

    El orden de TMDB es de relevancia y deja arriba títulos con 0 votos
    (pedido del usuario, 14/10/2026: lo desconocido, al fondo).
    """

    def test_siempre_lee_los_primeros_100_con_el_anio(self):
        datos = self.ok(q="dune", tipo="movie", anio=2021)

        llamadas = self.tmdb.de("search", "movie")
        self.assertEqual(sorted(llamada[2] for llamada in llamadas), [1, 2, 3, 4, 5])
        self.assertTrue(all(llamada[3] == {"anio": 2021} for llamada in llamadas))
        # 100 en la ventana, 48 pasan el corte de relevancia.
        self.assertEqual((datos["total_results"], datos["total_pages"]), (48, 3))

    def test_el_texto_llega_sin_espacios_de_mas(self):
        datos = self.ok(q="  dune ", tipo="tv")

        # 96 series en la ventana; 56 pasan el corte de relevancia.
        self.assertEqual(datos["total_results"], 56)

    def test_lo_conocido_o_muy_esperado_arriba(self):
        datos = self.ok(q="dune", tipo="movie")

        titulos = [item["title"] for item in datos["results"]]
        # Dune: Part Three no tiene votos, pero su popularidad (32) la deja 5.ª
        # entre 100, delante de títulos con cientos de votos.
        self.assertEqual(
            titulos[:5],
            ["Dune", "Dune: Part Two", "Dune", "Anatomy of a Fall", "Dune: Part Three"],
        )
        puntajes = [_puntaje(item) for item in datos["results"]]
        self.assertEqual(puntajes, sorted(puntajes, reverse=True))

    def test_todo_mezcla_peliculas_y_series_por_puntaje(self):
        primera = self.ok(q="dune")
        segunda = self.ok(q="dune", page=2)

        # 100 películas + 96 series en la ventana; con el corte quedan 104, de
        # a 40 (20 por tipo).
        self.assertEqual((primera["total_results"], primera["total_pages"]), (104, 3))
        self.assertEqual(len(primera["results"]), 40)
        puntajes = [_puntaje(item) for item in primera["results"] + segunda["results"]]
        self.assertEqual(puntajes, sorted(puntajes, reverse=True))
        self.assertEqual(
            {item["media_type"] for item in primera["results"]}, {"movie", "tv"}
        )


class VentanaTests(ExploreBase):
    """Texto con género o nota: los primeros 100 de cada tipo, filtrados acá."""

    def test_pide_hasta_5_paginas_y_filtra_por_genero(self):
        datos = self.ok(q="dune", tipo="movie", genero=878)

        paginas = sorted(llamada[2] for llamada in self.tmdb.de("search", "movie"))
        # TMDB tiene 56 páginas: la ventana se corta en 5.
        self.assertEqual(paginas, [1, 2, 3, 4, 5])
        # Eran 10 de ciencia ficción; uno no pasa el corte de relevancia.
        self.assertEqual(datos["total_results"], 9)
        self.assertEqual(datos["total_pages"], 1)
        self.assertTrue(all(878 in item["genre_ids"] for item in datos["results"]))

    def test_no_pide_paginas_que_tmdb_no_tiene(self):
        self.ok(q="the office", tipo="tv", genero=35)

        paginas = sorted(llamada[2] for llamada in self.tmdb.de("search", "tv"))
        self.assertEqual(paginas, [1, 2, 3])

    def test_pagina_de_a_20_dentro_de_la_ventana(self):
        # Drama en las 100 primeras películas de «dune»: 34, y 21 pasan el corte.
        primera = self.ok(q="dune", tipo="movie", genero=18)
        segunda = self.ok(q="dune", tipo="movie", genero=18, page=2)

        self.assertEqual((primera["total_results"], primera["total_pages"]), (21, 2))
        self.assertEqual(len(primera["results"]), 20)
        self.assertEqual(len(segunda["results"]), 1)
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

        # 9 películas de Science Fiction y 6 series de Sci-Fi & Fantasy, ya sin
        # lo que no pasa el corte de relevancia.
        self.assertEqual(datos["total_results"], 15)
        puntajes = [_puntaje(item) for item in datos["results"]]
        self.assertEqual(puntajes, sorted(puntajes, reverse=True))
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


class ValidacionTests(ExploreBase):
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


class GenerosTodoTests(ExploreBase):
    def test_suma_a_los_de_peliculas_los_cinco_solo_de_series(self):
        respuesta = self.api.get(
            "/api/catalogo/genres/", {"tipo": "all"}, HTTP_ACCEPT_LANGUAGE="en"
        )

        self.assertEqual(respuesta.status_code, 200)
        ids = [genero["id"] for genero in respuesta.data["genres"]]
        peliculas = [genero["id"] for genero in DATOS["genres"]["movie"]]
        self.assertEqual(ids[: len(peliculas)], peliculas)
        self.assertEqual(ids[len(peliculas) :], [10762, 10763, 10764, 10766, 10767])


class TMDBFalsoPaginado(TMDBFalso):
    """`discover` con páginas distintas: 20 títulos por página y 8 páginas.

    Las capturas devuelven siempre la misma página; para probar la ventana de
    «Todo» con un orden hacen falta títulos distintos en cada una. Fechas, notas
    y votos salen de una fórmula fija, mezclados a propósito.
    """

    def discover(self, tipo, genero=None, anio=None, min_rating=None, page=1, **extra):
        self.llamadas.append(("discover", tipo, page, {"genero": genero, **extra}))
        base = (0 if tipo == "movie" else 10_000) + (page - 1) * 20
        results = []
        for i in range(20):
            n = base + i
            results.append(
                {
                    "id": n,
                    "title": f"T{n}",
                    "poster_path": f"/{n}.jpg",
                    "release_date": f"{2000 + (n * 7) % 25}-{1 + n % 12:02d}-15",
                    "vote_average": (n * 13 % 50) / 5,
                    "vote_count": 300 + (n * 31) % 1000,
                    "popularity": 1,
                }
            )
        return {
            "page": page,
            "total_pages": 8,
            "total_results": 160,
            "results": results,
        }


class OrdenTests(ExploreBase):
    """El orden de los resultados (24/11/2026): `orden=` en `explore/`."""

    def setUp(self):
        super().setUp()
        parche = patch("catalogo.services.explore.hoy", return_value=date(2026, 11, 24))
        parche.start()
        self.addCleanup(parche.stop)

    def test_un_orden_invalido_es_400_con_los_valores_permitidos(self):
        respuesta = self.buscar(orden="titulo")

        self.assertEqual(respuesta.status_code, 400)
        [error] = respuesta.data["errors"]
        self.assertEqual((error["field"], error["code"]), ("orden", "invalid_choice"))
        self.assertEqual(
            error["params"]["allowedValues"],
            [
                "popular",
                "fecha-desc",
                "fecha-asc",
                "nota-desc",
                "nota-asc",
                "votos-desc",
            ],
        )
        self.assertEqual(self.tmdb.llamadas, [])

    def test_sin_orden_es_popular(self):
        self.ok(tipo="movie")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["sort_by"], "popularity.desc")

    def test_un_tipo_manda_a_tmdb_el_sort_by_de_cada_tipo(self):
        esperado = {
            "popular": ("popularity.desc", "popularity.desc"),
            "fecha-desc": ("primary_release_date.desc", "first_air_date.desc"),
            "fecha-asc": ("primary_release_date.asc", "first_air_date.asc"),
            "nota-desc": ("vote_average.desc", "vote_average.desc"),
            "nota-asc": ("vote_average.asc", "vote_average.asc"),
            "votos-desc": ("vote_count.desc", "vote_count.desc"),
        }
        for orden, (pelicula, serie) in esperado.items():
            for tipo, sort_by in (("movie", pelicula), ("tv", serie)):
                with self.subTest(orden=orden, tipo=tipo):
                    self.tmdb.llamadas.clear()
                    datos = self.ok(tipo=tipo, orden=orden)

                    [(*_, params)] = self.tmdb.de("discover")
                    self.assertEqual(params["sort_by"], sort_by)
                    # Con un solo tipo lo ordena TMDB: no hay tope de 200.
                    self.assertEqual(len(datos["results"]), 20)

    def test_ordenar_por_nota_exige_200_votos(self):
        for orden in ("nota-desc", "nota-asc"):
            with self.subTest(orden=orden):
                self.tmdb.llamadas.clear()
                self.ok(tipo="movie", orden=orden)

                [(*_, params)] = self.tmdb.de("discover")
                self.assertEqual(params["min_votos"], 200)

    def test_los_otros_ordenes_conservan_el_minimo_de_50(self):
        for orden in ("fecha-desc", "fecha-asc", "votos-desc"):
            with self.subTest(orden=orden):
                self.tmdb.llamadas.clear()
                self.ok(tipo="movie", orden=orden)

                [(*_, params)] = self.tmdb.de("discover")
                self.assertEqual(params["min_votos"], 50)

    def test_ordenar_por_nota_sin_minimo_si_es_lo_que_aun_no_estreno(self):
        self.ok(tipo="movie", orden="nota-desc", a_estrenar="true")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertIsNone(params["min_votos"])

    def test_mas_nuevos_no_pide_lo_que_estrena_despues_de_hoy(self):
        self.ok(tipo="movie", orden="fecha-desc")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["hasta_fecha"], "2026-11-24")

    def test_mas_nuevos_con_a_estrenar_no_pone_tope(self):
        self.ok(tipo="movie", orden="fecha-desc", a_estrenar="true")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["desde_fecha"], "2026-11-25")
        self.assertIsNone(params["hasta_fecha"])

    def test_mas_nuevos_con_un_anio_futuro_no_pone_tope(self):
        self.ok(tipo="movie", orden="fecha-desc", anio=2027)

        [(*_, params)] = self.tmdb.de("discover")
        self.assertIsNone(params["hasta_fecha"])

    def test_mas_nuevos_con_una_decada_conserva_el_fin_de_la_decada(self):
        self.ok(tipo="movie", orden="fecha-desc", decada=1980)

        [(*_, params)] = self.tmdb.de("discover")
        self.assertEqual(params["hasta_fecha"], "1989-12-31")

    def test_popular_no_pone_tope_de_fecha(self):
        self.ok(tipo="movie")

        [(*_, params)] = self.tmdb.de("discover")
        self.assertIsNone(params["hasta_fecha"])


class OrdenTodoTests(ExploreBase):
    """«Todo» sin texto con un orden: los primeros 100 de cada tipo, juntos."""

    Falso = TMDBFalsoPaginado

    def setUp(self):
        super().setUp()
        parche = patch("catalogo.services.explore.hoy", return_value=date(2026, 11, 24))
        parche.start()
        self.addCleanup(parche.stop)

    def todas(self, **params):
        """Las páginas 1 a `total_pages`, una detrás de otra."""
        primera = self.ok(**params)
        paginas = [primera]
        for n in range(2, primera["total_pages"] + 1):
            paginas.append(self.ok(page=n, **params))
        return primera, [item for pagina in paginas for item in pagina["results"]]

    def test_pide_5_paginas_por_tipo_y_nada_mas(self):
        self.ok(orden="nota-desc")

        for tipo in ("movie", "tv"):
            paginas = sorted(llamada[2] for llamada in self.tmdb.de("discover", tipo))
            self.assertEqual(paginas, [1, 2, 3, 4, 5])

    def test_mezcla_peliculas_y_series_en_orden_y_pagina_de_a_40(self):
        primera, todos = self.todas(orden="nota-desc")

        self.assertEqual((primera["total_results"], primera["total_pages"]), (200, 5))
        self.assertEqual(len(primera["results"]), 40)
        self.assertEqual(len(todos), 200)
        notas = [item["vote_average"] for item in todos]
        self.assertEqual(notas, sorted(notas, reverse=True))
        self.assertEqual({item["media_type"] for item in todos}, {"movie", "tv"})

    def test_mas_nuevos_baja_las_fechas_sin_saltos_hasta_el_final(self):
        _, todos = self.todas(orden="fecha-desc")

        fechas = [item["release_date"] for item in todos]
        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_mas_viejos_sube_las_fechas(self):
        _, todos = self.todas(orden="fecha-asc")

        fechas = [item["release_date"] for item in todos]
        self.assertEqual(fechas, sorted(fechas))

    def test_mas_votados(self):
        _, todos = self.todas(orden="votos-desc")

        votos = [item["vote_count"] for item in todos]
        self.assertEqual(votos, sorted(votos, reverse=True))

    def test_la_pagina_2_sigue_el_orden_de_la_1(self):
        primera = self.ok(orden="nota-desc")
        segunda = self.ok(orden="nota-desc", page=2)

        self.assertLessEqual(
            segunda["results"][0]["vote_average"],
            primera["results"][-1]["vote_average"],
        )

    def test_cada_tipo_pide_el_sort_by_que_le_toca(self):
        self.ok(orden="fecha-desc")

        [(*_, pelis)] = self.tmdb.de("discover", "movie")[:1]
        [(*_, series)] = self.tmdb.de("discover", "tv")[:1]
        self.assertEqual(pelis["sort_by"], "primary_release_date.desc")
        self.assertEqual(series["sort_by"], "first_air_date.desc")

    def test_popular_sigue_alternando_por_pagina(self):
        self.ok()

        # Sin orden no hay ventana: una página por tipo, como siempre.
        self.assertEqual(len(self.tmdb.de("discover")), 2)

    def test_un_genero_solo_de_peliculas_no_pide_series(self):
        self.ok(orden="nota-desc", genero=27)

        self.assertEqual(self.tmdb.de("discover", "tv"), [])
        self.assertEqual(len(self.tmdb.de("discover", "movie")), 5)

    def test_no_pide_paginas_que_tmdb_no_tiene(self):
        class DosPaginas(TMDBFalsoPaginado):
            def discover(self, *args, **kwargs):
                datos = super().discover(*args, **kwargs)
                datos["total_pages"] = 2
                return datos

        self.tmdb.__class__ = DosPaginas
        self.ok(orden="nota-desc")

        self.assertEqual(len(self.tmdb.de("discover", "movie")), 2)


class OrdenEnMemoriaTests(ExploreBase):
    """Con texto, el orden se aplica en memoria sobre la ventana de 100."""

    def setUp(self):
        super().setUp()
        parche = patch("catalogo.services.explore.hoy", return_value=date(2026, 11, 24))
        parche.start()
        self.addCleanup(parche.stop)

    def fechas(self, datos):
        return [
            item.get("release_date") or item.get("first_air_date") or ""
            for item in datos["results"]
        ]

    def test_por_fecha_lo_que_no_tiene_fecha_va_al_final(self):
        for orden, inverso in (("fecha-desc", True), ("fecha-asc", False)):
            with self.subTest(orden=orden):
                datos = self.ok(q="dune", tipo="movie", orden=orden)

                fechas = self.fechas(datos)
                con_fecha = [f for f in fechas if f]
                self.assertEqual(con_fecha, sorted(con_fecha, reverse=inverso))
                self.assertEqual(
                    fechas, con_fecha + [""] * (len(fechas) - len(con_fecha))
                )

    def test_mas_nuevos_deja_al_final_lo_que_estrena_despues_de_hoy(self):
        datos = self.ok(q="dune", tipo="movie", orden="fecha-desc")

        fechas = [f for f in self.fechas(datos) if f]
        hasta_hoy = [f for f in fechas if f <= "2026-11-24"]
        self.assertEqual(fechas[: len(hasta_hoy)], hasta_hoy)

    def test_por_nota_lo_que_tiene_pocos_votos_va_al_final(self):
        datos = self.ok(q="dune", orden="nota-desc")

        resultados = datos["results"]
        for n in range(2, datos["total_pages"] + 1):
            resultados += self.ok(q="dune", orden="nota-desc", page=n)["results"]
        votos = [i.get("vote_count") or 0 for i in resultados]
        firmes = sum(1 for v in votos if v >= 200)
        self.assertTrue(0 < firmes < len(votos))
        # Primero los de 200 votos o más, de mayor a menor nota; después el resto.
        self.assertTrue(all(v >= 200 for v in votos[:firmes]))
        self.assertTrue(all(v < 200 for v in votos[firmes:]))
        notas = [i["vote_average"] for i in resultados[:firmes]]
        self.assertEqual(notas, sorted(notas, reverse=True))

    def test_mas_votados(self):
        datos = self.ok(q="dune", tipo="movie", orden="votos-desc")

        votos = [item["vote_count"] for item in datos["results"]]
        self.assertEqual(votos, sorted(votos, reverse=True))
