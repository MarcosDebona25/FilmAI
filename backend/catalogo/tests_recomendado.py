"""Pruebas HTTP de «Recomendado para ti» (C-05): `GET /api/catalogo/recommended/`.

El diseño está en `openspec/changes/home-catalogo/design.md` §2. Van en su
propio módulo porque `catalogo/tests.py` ya es muy largo; el runner de Django
descubre cualquier `test*.py`.
"""

import copy
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.models import Calificacion, TipoProduccion
from listas.models import ClaveLista, Tiene
from usuarios.factories import UsuarioFactory

URL = "/api/catalogo/recommended/"

# Recortes de respuestas reales de TMDB del 13/10/2026: `discover` con
# Thriller|Drama|Crime en películas y Drama|Crime en series, por popularidad y
# con 100 votos o más. La sinopsis quedó en su primera oración.
PELICULAS_TMDB = [
    {
        "id": 1291595,
        "title": "Insidious: Out of the Further",
        "overview": "Gemma, a young mother raising her daughter in the house she "
        "grew up in, discovers she can travel into The Further.",
        "poster_path": "/4tTrW9dXCByS5wt2pXVWb58zNjz.jpg",
        "backdrop_path": "/p40lmrdI4blcAPZQMTPaiy5v5Ym.jpg",
        "release_date": "2026-08-19",
        "vote_average": 7.725,
        "vote_count": 694,
        "genre_ids": [27, 53],
    },
    {
        "id": 1101412,
        "title": "Fall 2: Deadpoint",
        "overview": "On a perilous climb across Thailand's Mount Kwan, two "
        "climbers become trapped thousands of feet above the ground.",
        "poster_path": "/fgSm5ylwiXbIHn8UbUXDjk9RRu4.jpg",
        "backdrop_path": "/yBDxqDB29kpH9VojTytjGWBgmdJ.jpg",
        "release_date": "2026-09-01",
        "vote_average": 7.313,
        "vote_count": 509,
        "genre_ids": [53],
    },
    {
        "id": 1339274,
        "title": "Don't Leave the Kids Alone",
        "overview": "A mother moves into a new house with her two children.",
        "poster_path": "/7kaglo9sblVsQrKsUqaVxrfc6ag.jpg",
        "backdrop_path": "/flo7Xmyxz2wDUjr5Ff0VrxaVwlY.jpg",
        "release_date": "2026-05-14",
        "vote_average": 6.81,
        "vote_count": 121,
        "genre_ids": [27, 18, 53],
    },
]
SERIES_TMDB = [
    {
        "id": 108978,
        "name": "Reacher",
        "overview": "Jack Reacher, a veteran military police investigator, has "
        "just recently entered civilian life.",
        "poster_path": "/f1VCQIG2iCyOookdgOzwtUpwWC0.jpg",
        "backdrop_path": "/pF0qkRsrHkdYadPWY9AMeFZfcwk.jpg",
        "first_air_date": "2022-02-03",
        "vote_average": 8.136,
        "vote_count": 3488,
        "genre_ids": [10759, 80],
    },
    {
        "id": 2734,
        "name": "Law & Order: Special Victims Unit",
        "overview": "In the criminal justice system, sexually-based offenses "
        "are considered especially heinous.",
        "poster_path": "/iofokHZoUB4Qhik4PflvJl8TT6a.jpg",
        "backdrop_path": "/xhK9YCxNwnE0OB1SWvCY39heHQI.jpg",
        "first_air_date": "1999-09-20",
        "vote_average": 8.0,
        "vote_count": 4375,
        "genre_ids": [80, 18, 9648],
    },
]
# Nombres reales de `genre/{tipo}/list` el 13/10/2026 (recortados).
GENEROS_TMDB = {
    ("movie", "en-US"): [
        {"id": 18, "name": "Drama"},
        {"id": 53, "name": "Thriller"},
        {"id": 80, "name": "Crime"},
        {"id": 35, "name": "Comedy"},
    ],
    ("movie", "es-MX"): [
        {"id": 18, "name": "Drama"},
        {"id": 53, "name": "Suspense"},
        {"id": 80, "name": "Crimen"},
        {"id": 35, "name": "Comedia"},
    ],
    ("tv", "en-US"): [
        {"id": 18, "name": "Drama"},
        {"id": 80, "name": "Crime"},
        {"id": 9648, "name": "Mystery"},
    ],
    ("tv", "es-MX"): [
        {"id": 18, "name": "Drama"},
        {"id": 80, "name": "Crimen"},
        {"id": 9648, "name": "Misterio"},
    ],
}


class ServicioFalso:
    """Hace de `get_catalog_service(idioma)`: responde con los recortes reales
    y anota cada llamada a `discover` para que el test la inspeccione."""

    def __init__(self, idioma, llamadas):
        self.idioma = idioma
        self.llamadas = llamadas

    def discover(self, tipo, **filtros):
        self.llamadas.append({"tipo": tipo, "idioma": self.idioma, **filtros})
        items = PELICULAS_TMDB if tipo == "movie" else SERIES_TMDB
        # Copia: el respaldo en inglés marca cada item y no debe tocar el original.
        return {"page": 1, "results": copy.deepcopy(items)}

    def get_genres(self, tipo):
        return {"genres": copy.deepcopy(GENEROS_TMDB[(tipo, self.idioma)])}


class RecomendadoAutenticacionTests(TestCase):
    """Recomendado depende de las calificaciones de alguien: sin sesión no hay."""

    def test_sin_sesion_responde_401_con_el_sobre_de_errores(self):
        respuesta = APIClient().get(URL)

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["code"], "not_authenticated")


class RecomendadoSinGustosTests(TestCase):
    """Sin calificaciones de 7 o más no hay géneros de dónde partir."""

    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)

    @patch("catalogo.cache.TMDBClientCache.discover")
    def test_solo_notas_bajas_responde_vacio_sin_llamar_a_tmdb(self, discover):
        # Un 6 no alcanza: la fila parte de lo que le gustó (7 o más).
        produccion = ProduccionAudiovisualFactory(
            tipo=TipoProduccion.PELICULA, generos_ids=[18]
        )
        Calificacion.objects.create(
            usuario=self.usuario, produccion=produccion, valor=6
        )

        respuesta = self.cliente.get(URL)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"generos": [], "results": []})
        discover.assert_not_called()


class _BaseRecomendado(TestCase):
    """Usuario con sesión y TMDB reemplazado por `ServicioFalso`."""

    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.llamadas = []
        parche = patch(
            "catalogo.views.get_catalog_service",
            side_effect=lambda idioma=None: ServicioFalso(
                idioma or "en-US", self.llamadas
            ),
        )
        parche.start()
        self.addCleanup(parche.stop)

    def _calificar(self, generos, *, tipo=TipoProduccion.PELICULA, valor=8, **campos):
        produccion = ProduccionAudiovisualFactory(
            tipo=tipo, generos_ids=generos, **campos
        )
        return Calificacion.objects.create(
            usuario=self.usuario, produccion=produccion, valor=valor
        )

    def _agregar_a(self, clave, id_tmdb, tipo):
        lista = self.usuario.listas.get(clave=clave)
        produccion = ProduccionAudiovisualFactory(id_tmdb=id_tmdb, tipo=tipo)
        Tiene.objects.create(lista=lista, produccion=produccion)

    def _ids(self, respuesta):
        return [
            (item["media_type"], item["id"]) for item in respuesta.json()["results"]
        ]


class RecomendadoConsultaATMDBTests(_BaseRecomendado):
    """Qué se le pide a TMDB a partir de lo que el usuario calificó."""

    def test_pide_los_tres_generos_mas_repetidos_con_or_por_popularidad(self):
        # Drama (18) 3 veces, Thriller (53) 2, Crimen (80) 2, Comedia (35) 1.
        self._calificar([18, 53])
        self._calificar([18, 80])
        self._calificar([18, 53, 80])
        self._calificar([35])

        respuesta = self.cliente.get(URL, {"tipo": "movie"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(self.llamadas), 1)
        llamada = self.llamadas[0]
        self.assertEqual(llamada["tipo"], "movie")
        self.assertEqual(set(llamada["genero"].split("|")), {"18", "53", "80"})
        self.assertEqual(llamada["sort_by"], "popularity.desc")
        self.assertEqual(llamada["min_votos"], 100)

    def test_un_empate_lo_gana_el_genero_de_la_calificacion_mas_reciente(self):
        # Todos aparecen una vez. `fecha` es la del día, así que el orden lo da
        # el id: la última calificación creada es la más reciente.
        self._calificar([35])
        self._calificar([80])
        self._calificar([53])
        self._calificar([18])

        self.cliente.get(URL, {"tipo": "movie"})

        self.assertEqual(self.llamadas[0]["genero"], "18|53|80")

    def test_una_calificacion_inactiva_no_cuenta(self):
        calificacion = self._calificar([35])
        calificacion.activa = False
        calificacion.save()

        respuesta = self.cliente.get(URL, {"tipo": "movie"})

        self.assertEqual(respuesta.json(), {"generos": [], "results": []})
        self.assertEqual(self.llamadas, [])

    def test_cada_tipo_usa_solo_las_calificaciones_de_ese_tipo(self):
        self._calificar([53], tipo=TipoProduccion.PELICULA)
        self._calificar([9648], tipo=TipoProduccion.SERIE)

        self.cliente.get(URL, {"tipo": "movie"})
        self.cliente.get(URL, {"tipo": "tv"})

        self.assertEqual(
            [(llamada["tipo"], llamada["genero"]) for llamada in self.llamadas],
            [("movie", "53"), ("tv", "9648")],
        )


class RecomendadoResultadosTests(_BaseRecomendado):
    """Qué vuelve: forma de cada item, exclusiones, mezcla y tope."""

    def test_cada_item_conserva_la_forma_de_tmdb_y_suma_media_type(self):
        self._calificar([53])

        respuesta = self.cliente.get(URL, {"tipo": "movie"})

        primero = respuesta.json()["results"][0]
        self.assertEqual(primero["media_type"], "movie")
        self.assertEqual(primero["title"], "Insidious: Out of the Further")
        self.assertEqual(primero["poster_path"], "/4tTrW9dXCByS5wt2pXVWb58zNjz.jpg")

    def test_saca_lo_que_esta_en_vistas_pero_no_lo_que_esta_en_pendientes(self):
        self._calificar([53])
        self._agregar_a(ClaveLista.VISTAS, 1291595, TipoProduccion.PELICULA)
        self._agregar_a(ClaveLista.PENDIENTES, 1101412, TipoProduccion.PELICULA)

        respuesta = self.cliente.get(URL, {"tipo": "movie"})

        self.assertEqual(self._ids(respuesta), [("movie", 1101412), ("movie", 1339274)])

    def test_excluye_por_par_id_y_tipo_no_solo_por_id(self):
        # TMDB numera películas y series por separado: una película vista con
        # el id 108978 no es la serie Reacher, que tiene el mismo número.
        self._calificar([80], tipo=TipoProduccion.SERIE)
        self._agregar_a(ClaveLista.VISTAS, 108978, TipoProduccion.PELICULA)

        respuesta = self.cliente.get(URL, {"tipo": "tv"})

        self.assertIn(("tv", 108978), self._ids(respuesta))

    def test_en_all_alterna_pelicula_y_serie_y_completa_con_el_que_sobra(self):
        self._calificar([53], tipo=TipoProduccion.PELICULA)
        self._calificar([80], tipo=TipoProduccion.SERIE)

        respuesta = self.cliente.get(URL)

        self.assertEqual(
            self._ids(respuesta),
            [
                ("movie", 1291595),
                ("tv", 108978),
                ("movie", 1101412),
                ("tv", 2734),
                ("movie", 1339274),
            ],
        )

    def test_all_con_un_solo_tipo_calificado_pide_solo_ese_tipo(self):
        self._calificar([80], tipo=TipoProduccion.SERIE)

        respuesta = self.cliente.get(URL)

        self.assertEqual([llamada["tipo"] for llamada in self.llamadas], ["tv"])
        self.assertEqual(self._ids(respuesta), [("tv", 108978), ("tv", 2734)])

    def test_devuelve_como_mucho_15(self):
        self._calificar([53])
        muchas = [
            {**PELICULAS_TMDB[0], "id": 9_000_000 + indice} for indice in range(20)
        ]
        with patch.object(
            ServicioFalso,
            "discover",
            lambda servicio, tipo, **filtros: {"page": 1, "results": muchas},
        ):
            respuesta = self.cliente.get(URL, {"tipo": "movie"})

        self.assertEqual(len(respuesta.json()["results"]), 15)


class RecomendadoGenerosTests(_BaseRecomendado):
    """Los nombres de los géneros usados, para el subtítulo de la fila."""

    def test_devuelve_los_nombres_en_orden_de_cantidad(self):
        self._calificar([18, 53])
        self._calificar([18, 80])
        self._calificar([18, 53])

        respuesta = self.cliente.get(URL, {"tipo": "movie"})

        self.assertEqual(respuesta.json()["generos"], ["Drama", "Thriller", "Crime"])

    def test_los_nombres_salen_en_el_idioma_del_pedido(self):
        self._calificar([53])
        self._calificar([53, 80])

        respuesta = self.cliente.get(URL, {"tipo": "movie"}, HTTP_ACCEPT_LANGUAGE="es")

        self.assertEqual(respuesta.json()["generos"], ["Suspense", "Crimen"])
        self.assertEqual(self.llamadas[0]["idioma"], "es-MX")

    def test_en_all_suma_las_cuentas_de_los_dos_tipos(self):
        # Crimen (80) aparece en las dos: 1 + 2 = 3, más que Drama (2).
        self._calificar([18, 80], tipo=TipoProduccion.PELICULA)
        self._calificar([18], tipo=TipoProduccion.PELICULA)
        self._calificar([80], tipo=TipoProduccion.SERIE)
        self._calificar([80, 9648], tipo=TipoProduccion.SERIE)

        respuesta = self.cliente.get(URL)

        self.assertEqual(respuesta.json()["generos"], ["Crime", "Drama", "Mystery"])


class RecomendadoValidacionTests(_BaseRecomendado):
    def test_un_tipo_desconocido_responde_400_sin_llamar_a_tmdb(self):
        respuesta = self.cliente.get(URL, {"tipo": "book"})

        self.assertEqual(respuesta.status_code, 400)
        error = respuesta.json()["errors"][0]
        self.assertEqual(error["field"], "tipo")
        self.assertEqual(error["code"], "invalid_choice")
        self.assertEqual(error["params"]["allowedValues"], ["all", "movie", "tv"])
        self.assertEqual(self.llamadas, [])
