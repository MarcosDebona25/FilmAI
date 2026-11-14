"""Pruebas del corte de relevancia de Buscar (C-06, 13/11/2026).

Con texto, Buscar deja afuera los títulos de la cola larga de TMDB: los que
tienen menos de 5 votos y popularidad menor a 5, salvo que se llamen justo como
el texto. El diseño está en `openspec/changes/busqueda-navbar/design.md` (§4).

Los datos son una respuesta real de TMDB capturada el 14/11/2026
(`test_datos/tmdb_buscar_personas.json`, clave `buscar`): «chihiro» en
películas devuelve 13 títulos y solo 3 pasan el corte.
"""

import copy
import json
from pathlib import Path

from django.test import SimpleTestCase

from catalogo.services.browse import es_relevante, normalizar
from catalogo.tests_browse import BrowseBase, TMDBFalso

DATOS = json.loads(
    (Path(__file__).parent / "test_datos" / "tmdb_buscar_personas.json").read_text()
)


class TMDBFalsoChihiro(TMDBFalso):
    """El de `tests_browse`, pero «chihiro» sale de la captura nueva."""

    def _paginas(self, tipo, query):
        captura = DATOS["buscar"].get(f"chihiro_{tipo}") if "chihiro" in query else None
        if captura is not None:
            return {"1": copy.deepcopy(captura)}
        return super()._paginas(tipo, query)


class EsRelevanteTests(SimpleTestCase):
    """`es_relevante` en los bordes: 4 y 5 votos, 4,9 y 5 de popularidad."""

    def test_5_votos_pasan_y_4_no(self):
        self.assertTrue(es_relevante({"vote_count": 5, "popularity": 0}))
        self.assertFalse(es_relevante({"vote_count": 4, "popularity": 0}))

    def test_popularidad_5_pasa_y_4_9_no(self):
        self.assertTrue(es_relevante({"vote_count": 0, "popularity": 5}))
        self.assertFalse(es_relevante({"vote_count": 0, "popularity": 4.9}))

    def test_sin_los_campos_no_pasa(self):
        # TMDB a veces manda `null`: cuenta como 0, no rompe.
        self.assertFalse(es_relevante({"vote_count": None, "popularity": None}))
        self.assertFalse(es_relevante({}))

    def test_el_titulo_exacto_pasa_aunque_no_tenga_votos(self):
        item = {"title": "Sato no Chihiro", "vote_count": 1, "popularity": 0.07}
        self.assertTrue(es_relevante(item, "sato no chihiro"))
        # Sin texto, o con otro, no hay excepción.
        self.assertFalse(es_relevante(item))
        self.assertFalse(es_relevante(item, "chihiro"))

    def test_el_titulo_exacto_sirve_traducido_u_original(self):
        item = {"title": "El viaje", "original_title": "Sen to Chihiro"}
        self.assertTrue(es_relevante(item, "El viaje"))
        self.assertTrue(es_relevante(item, "sen to chihiro"))
        serie = {"name": "La casa", "original_name": "Das Haus"}
        self.assertTrue(es_relevante(serie, "das haus"))
        self.assertTrue(es_relevante(serie, "la casa"))

    def test_el_titulo_exacto_ignora_tildes_mayusculas_y_espacios(self):
        item = {"title": "Chihiró", "vote_count": 0, "popularity": 0}
        self.assertTrue(es_relevante(item, "  CHIHIRO "))
        self.assertTrue(es_relevante(item, "chihiro"))


class NormalizarTests(SimpleTestCase):
    def test_minusculas_sin_tildes_y_con_espacios_colapsados(self):
        self.assertEqual(
            normalizar("  El   Señor\tde los Anillos "), "el senor de los anillos"
        )
        self.assertEqual(normalizar("CHIHIRÓ"), "chihiro")

    def test_none_es_texto_vacio(self):
        self.assertEqual(normalizar(None), "")


class CorteEnBuscarTests(BrowseBase):
    """`browse/` con texto saca lo irrelevante antes de contar y paginar."""

    # El mismo reemplazo de TMDB, con la captura de «chihiro».
    Falso = TMDBFalsoChihiro

    def titulos(self, datos):
        return [item["title"] for item in datos["results"]]

    def test_chihiro_muestra_3_de_13(self):
        datos = self.ok(q="chihiro", tipo="movie")

        self.assertEqual(datos["total_results"], 3)
        self.assertEqual(datos["total_pages"], 1)
        self.assertEqual(
            sorted(self.titulos(datos)),
            ["Call Me Chihiro", "Spirited Away", "Spirited Away: Live on Stage"],
        )
        self.assertNotIn("La arquitectura de El Viaje de Chihiro", self.titulos(datos))

    def test_el_titulo_exacto_se_muestra_aunque_tenga_1_voto(self):
        datos = self.ok(q="sato no chihiro", tipo="movie")

        # TMDB devolvió los mismos 13 (la captura es una sola): pasan 3 más
        # el que se llama como el texto.
        self.assertIn("Sato no Chihiro", self.titulos(datos))
        self.assertEqual(datos["total_results"], 4)

    def test_en_todo_el_total_cuenta_solo_lo_que_se_muestra(self):
        # En «Todo» las series de «chihiro» no traen nada: el total es el de películas.
        datos = self.ok(q="chihiro")

        self.assertEqual(datos["total_results"], 3)

    def test_si_nada_pasa_se_muestra_todo(self):
        # Los 10 que no pasan el corte, sin ninguno que pase: se ven todos.
        irrelevantes = [
            item
            for item in DATOS["buscar"]["chihiro_movie"]["results"]
            if item["vote_count"] < 5 and item["popularity"] < 5
        ]
        self.assertEqual(len(irrelevantes), 10)
        captura = copy.deepcopy(DATOS["buscar"]["chihiro_movie"])
        captura["results"] = irrelevantes
        captura["total_results"] = len(irrelevantes)
        self.tmdb._paginas = lambda tipo, query: {
            "1": copy.deepcopy(captura)
            if tipo == "movie"
            else {"page": 1, "total_pages": 0, "total_results": 0, "results": []}
        }

        datos = self.ok(q="chihiro", tipo="movie")

        self.assertEqual(datos["total_results"], 10)

    def test_no_pide_nada_de_mas_a_tmdb(self):
        self.ok(q="chihiro", tipo="movie")

        # El corte trabaja sobre lo que ya se leyó: solo la página 1 (TMDB dice
        # que hay 1) y ninguna llamada nueva.
        self.assertEqual(len(self.tmdb.de("search", "movie")), 1)
        self.assertEqual(self.tmdb.de("discover"), [])

    def test_sin_texto_no_hay_corte(self):
        # `discover` ya pide 50 votos; lo anunciado sin votos es el punto de «A estrenar».
        datos = self.ok(tipo="movie")

        self.assertEqual(len(datos["results"]), 20)
