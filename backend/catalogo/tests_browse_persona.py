"""Pruebas del filtro por persona de Buscar (13/11/2026): `browse/?persona=&rol=`.

El diseño está en `openspec/changes/busqueda-navbar/design.md` (§5). TMDB se
reemplaza por un servicio falso que responde las filmografías reales de tres
personas capturadas el 14/11/2026 (`test_datos/tmdb_buscar_personas.json`,
clave `personas`): Christopher Nolan (525), Vince Gilligan (66633) y Tom Hanks
(31). `discover` con `with_people` no sirve (TMDB lo ignora en series), así que
se lee `combined_credits` y se filtra en memoria.
"""

import copy
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import fakeredis
import httpx
from django.test import SimpleTestCase

from catalogo.cache import TMDBClientCache
from catalogo.client import TMDBClient
from catalogo.exceptions import TMDBNotFound, TMDBServerError
from catalogo.services.browse import explorar
from catalogo.tests_browse import BrowseBase, TMDBFalso

DATOS = json.loads(
    (Path(__file__).parent / "test_datos" / "tmdb_buscar_personas.json").read_text()
)
PERSONAS = DATOS["personas"]
NOLAN, GILLIGAN, HANKS = 525, 66633, 31


class TMDBFalsoPersonas(TMDBFalso):
    """El de `tests_browse`, más el detalle y los créditos de las 3 personas."""

    def get_person_detail(self, id_persona):
        self.llamadas.append(("person_detail", id_persona))
        return self._persona(id_persona)["detalle"]

    def get_person_credits(self, id_persona):
        self.llamadas.append(("person_credits", id_persona))
        return self._persona(id_persona)["creditos"]

    def _persona(self, id_persona):
        if str(id_persona) not in PERSONAS:
            raise TMDBNotFound("TMDB respondió 404")
        return copy.deepcopy(PERSONAS[str(id_persona)])


class PersonaBase(BrowseBase):
    Falso = TMDBFalsoPersonas

    def titulos(self, datos):
        return [item.get("title") or item.get("name") for item in datos["results"]]


class RolTests(PersonaBase):
    def test_los_creadores_cuentan_como_directores_de_series(self):
        datos = self.ok(persona=GILLIGAN, rol="director", tipo="tv")

        titulos = self.titulos(datos)
        for serie in ("Breaking Bad", "Better Call Saul", "Pluribus", "Battle Creek"):
            self.assertIn(serie, titulos)
        # Dirigió episodios de «The X-Files» pero no la creó: no es «director».
        self.assertNotIn("The X-Files", titulos)
        self.assertTrue(all(item["media_type"] == "tv" for item in datos["results"]))

    def test_en_peliculas_director_es_el_job_director(self):
        datos = self.ok(persona=GILLIGAN, rol="director", tipo="movie")

        self.assertEqual(self.titulos(datos), ["El Camino: A Breaking Bad Movie"])

    def test_un_director_en_todo_junta_peliculas_y_series(self):
        datos = self.ok(persona=GILLIGAN, rol="director")

        tipos = {item["media_type"] for item in datos["results"]}
        self.assertEqual(tipos, {"movie", "tv"})
        self.assertNotIn("The X-Files", self.titulos(datos))

    def test_un_actor_no_trae_los_programas_de_news_o_talk(self):
        datos = self.ok(persona=HANKS, rol="actor")

        titulos = self.titulos(datos)
        # Sus apariciones en shows de entrevistas llenarían la lista.
        for talk in ("This Morning", "The Daily Show", "The Ellen DeGeneres Show"):
            self.assertNotIn(talk, titulos)
        self.assertIn("The Simpsons", titulos)

    def test_sin_rol_son_las_dos_cosas_sin_repetir(self):
        datos = self.ok(persona=GILLIGAN)

        titulos = self.titulos(datos)
        # Breaking Bad está como `Director` (episodios) y como `Creator`.
        self.assertEqual(titulos.count("Breaking Bad"), 1)
        self.assertIn("Community", titulos)  # como actor

    def test_el_actor_no_trae_lo_que_solo_dirigio(self):
        datos = self.ok(persona=NOLAN, rol="actor")

        self.assertNotIn("Oppenheimer", self.titulos(datos))


class ResultadoTests(PersonaBase):
    def test_nolan_sin_los_titulos_sin_relevancia_y_los_mas_conocidos_arriba(self):
        datos = self.ok(persona=NOLAN, rol="director")

        titulos = self.titulos(datos)
        # 19 como director; «Cinema 16: European Short Films» (1 voto, 0,7) no pasa.
        self.assertEqual(datos["total_results"], 18)
        self.assertNotIn("Cinema 16: European Short Films (U.S. Edition)", titulos)
        # `max(votos, popularidad por 100)`: The Odyssey (popularidad 452) y luego
        # Interstellar (41 876 votos), igual que en una búsqueda con texto.
        self.assertEqual(titulos[:2], ["The Odyssey", "Interstellar"])

    def test_la_respuesta_trae_a_la_persona_con_su_rol(self):
        datos = self.ok(persona=NOLAN, rol="director")

        self.assertEqual(
            datos["persona"],
            {
                "id": NOLAN,
                "name": "Christopher Nolan",
                "rol": "director",
                "gender": 2,
                "profile_path": PERSONAS["525"]["detalle"]["profile_path"],
            },
        )
        self.assertEqual(self.ok(persona=NOLAN)["persona"]["rol"], None)

    def test_las_paginas_siguen_la_regla_de_siempre(self):
        # 45 películas con votos: 20 + 20 + 5, ordenadas por votos.
        creditos = [
            {
                "id": i,
                "media_type": "movie",
                "title": f"Peli {i}",
                "vote_count": 100 + i,
                "popularity": 1,
                "genre_ids": [],
                "job": "Director",
            }
            for i in range(45)
        ]
        self.tmdb._persona = lambda _: {
            "detalle": {"id": 1, "name": "X", "gender": 1, "profile_path": None},
            "creditos": {"cast": [], "crew": creditos},
        }

        paginas = [
            self.ok(persona=1, rol="director", tipo="movie", page=n) for n in (1, 2, 3)
        ]

        self.assertEqual([len(p["results"]) for p in paginas], [20, 20, 5])
        self.assertEqual({p["total_results"] for p in paginas}, {45})
        self.assertEqual({p["total_pages"] for p in paginas}, {3})
        votos = [i["vote_count"] for p in paginas for i in p["results"]]
        self.assertEqual(votos, sorted(votos, reverse=True))

    def test_nolan_y_series_no_tiene_nada_pero_no_es_un_error(self):
        datos = self.ok(persona=NOLAN, rol="director", tipo="tv")

        self.assertEqual(datos["total_results"], 0)
        self.assertEqual(datos["results"], [])
        self.assertEqual(datos["persona"]["id"], NOLAN)

    def test_cada_item_lleva_su_media_type(self):
        datos = self.ok(persona=GILLIGAN)

        self.assertTrue(
            all(item["media_type"] in ("movie", "tv") for item in datos["results"])
        )


class FiltrosEnMemoriaTests(PersonaBase):
    def test_no_llama_a_search_ni_a_discover(self):
        self.ok(persona=NOLAN, rol="director", genero=878, anio=2014)

        self.assertEqual(self.tmdb.de("search"), [])
        self.assertEqual(self.tmdb.de("discover"), [])
        self.assertEqual(
            self.tmdb.llamadas,
            [("person_detail", NOLAN), ("person_credits", NOLAN)],
        )

    def test_genero(self):
        datos = self.ok(persona=NOLAN, rol="director", genero=878)

        self.assertEqual(
            sorted(self.titulos(datos)),
            ["Inception", "Interstellar", "Tenet", "The Prestige"],
        )

    def test_genero_en_todo_se_traduce_para_las_series(self):
        # 878 (ciencia ficción) en series es 10765 (Sci-Fi & Fantasy).
        datos = self.ok(persona=GILLIGAN, rol="director", genero=878)

        self.assertTrue(
            all(
                878 in item["genre_ids"]
                if item["media_type"] == "movie"
                else 10765 in item["genre_ids"]
                for item in datos["results"]
            )
        )
        self.assertIn("Pluribus", self.titulos(datos))

    def test_anio(self):
        datos = self.ok(persona=NOLAN, rol="director", anio=2010)

        self.assertEqual(self.titulos(datos), ["Inception"])

    def test_decada(self):
        datos = self.ok(persona=NOLAN, rol="director", decada=1990)

        self.assertEqual(
            sorted(self.titulos(datos)),
            ["Doodlebug", "Following", "Larceny", "Tarantella"],
        )

    def test_a_estrenar(self):
        with patch("catalogo.services.browse.hoy", return_value=date(2026, 6, 1)):
            datos = self.ok(persona=NOLAN, rol="director", a_estrenar="true")

        self.assertEqual(self.titulos(datos), ["The Odyssey"])

    def test_nota_pide_50_votos(self):
        datos = self.ok(persona=NOLAN, rol="director", nota="8+")

        titulos = self.titulos(datos)
        self.assertIn("Inception", titulos)
        self.assertNotIn(
            "Quay", titulos
        )  # nota alta pero apenas 75 votos? ver más abajo
        self.assertTrue(all(item["vote_count"] >= 50 for item in datos["results"]))
        self.assertTrue(all(item["vote_average"] >= 8 for item in datos["results"]))

    def test_texto_por_contenido_sin_tildes_ni_mayusculas(self):
        for q in ("dark KNIGHT", "  DÁRK  knight ", "knight"):
            with self.subTest(q):
                datos = self.ok(persona=NOLAN, rol="director", q=q)
                self.assertEqual(
                    sorted(self.titulos(datos)),
                    ["The Dark Knight", "The Dark Knight Rises"],
                )

    def test_un_texto_que_no_esta_en_ningun_titulo_no_deja_nada(self):
        datos = self.ok(persona=NOLAN, rol="director", q="zzz")

        self.assertEqual(datos["results"], [])

    def test_el_texto_tambien_busca_en_el_titulo_original(self):
        credito = {
            "id": 1,
            "media_type": "movie",
            "title": "El origen de algo",
            "original_title": "Origin Story",
            "vote_count": 100,
            "popularity": 1,
            "genre_ids": [],
            "job": "Director",
        }
        self.tmdb._persona = lambda i: {
            "detalle": {"id": 1, "name": "X", "gender": 1, "profile_path": None},
            "creditos": {"cast": [], "crew": [credito]},
        }

        datos = self.ok(persona=1, rol="director", q="origin story")

        self.assertEqual(datos["total_results"], 1)

    def test_si_nada_pasa_el_corte_se_muestra_todo(self):
        poco_conocido = [
            {
                "id": i,
                "media_type": "movie",
                "title": f"Corto {i}",
                "vote_count": 0,
                "popularity": 0.1,
                "genre_ids": [],
                "job": "Director",
            }
            for i in (1, 2)
        ]
        self.tmdb._persona = lambda i: {
            "detalle": {"id": 1, "name": "X", "gender": 1, "profile_path": None},
            "creditos": {"cast": [], "crew": poco_conocido},
        }

        datos = self.ok(persona=1, rol="director")

        self.assertEqual(datos["total_results"], 2)


class ErroresTests(PersonaBase):
    def test_una_persona_que_tmdb_no_conoce_es_404_person_not_found(self):
        respuesta = self.buscar(persona=999999)

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.data["code"], "person_not_found")

    def test_persona_invalida(self):
        casos = (("abc", "invalid"), ("0", "min_value"), ("-3", "min_value"))
        for valor, codigo in casos:
            with self.subTest(valor):
                respuesta = self.buscar(persona=valor)
                self.assertEqual(respuesta.status_code, 400)
                [error] = respuesta.data["errors"]
                self.assertEqual((error["field"], error["code"]), ("persona", codigo))
        self.assertEqual(self.tmdb.llamadas, [])

    def test_rol_invalido(self):
        respuesta = self.buscar(persona=NOLAN, rol="guionista")

        self.assertEqual(respuesta.status_code, 400)
        [error] = respuesta.data["errors"]
        self.assertEqual((error["field"], error["code"]), ("rol", "invalid_choice"))
        self.assertEqual(error["params"], {"allowedValues": ["director", "actor"]})

    def test_sin_persona_el_rol_no_hace_nada(self):
        datos = self.ok(tipo="movie", rol="actor")

        self.assertNotIn("persona", datos)
        self.assertEqual(len(self.tmdb.de("discover")), 1)

    def test_un_error_de_tmdb_en_los_creditos_no_se_esconde(self):
        def falla(id_persona):
            raise TMDBServerError("TMDB respondió 500")

        self.tmdb.get_person_credits = falla

        respuesta = self.buscar(persona=NOLAN)

        self.assertEqual(respuesta.status_code, 502)


class CostoTests(SimpleTestCase):
    """Con la caché real: 2 llamadas la primera vez y 0 mientras dura (24 h)."""

    def setUp(self):
        self.pedidos = []

        def handler(request):
            self.pedidos.append(request.url.path)
            id_persona = request.url.path.split("/")[
                -2 if request.url.path.endswith("combined_credits") else -1
            ]
            persona = PERSONAS[id_persona]
            cuerpo = (
                persona["creditos"]
                if request.url.path.endswith("combined_credits")
                else persona["detalle"]
            )
            return httpx.Response(200, json=cuerpo)

        cliente = TMDBClient(api_key="k", transport=httpx.MockTransport(handler))
        self.servicio = TMDBClientCache(
            cliente, fakeredis.FakeRedis(decode_responses=True)
        )

    def pedir(self, **kwargs):
        return explorar(
            self.servicio,
            q=None,
            tipo=kwargs.pop("tipo", "all"),
            genero=kwargs.pop("genero", None),
            anio=None,
            nota=None,
            page=kwargs.pop("page", 1),
            persona=NOLAN,
            rol="director",
        )

    def test_la_primera_vez_son_dos_llamadas_y_despues_ninguna(self):
        self.pedir()
        self.assertEqual(
            sorted(p.split("/")[-1] for p in self.pedidos), ["525", "combined_credits"]
        )

        self.pedidos.clear()
        self.pedir(genero=878)
        self.pedir(page=2)
        self.pedir(tipo="movie")
        self.assertEqual(self.pedidos, [])
