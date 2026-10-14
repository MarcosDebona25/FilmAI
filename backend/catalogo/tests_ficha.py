"""Pruebas de los créditos de la ficha (C-07): `GET /api/catalogo/{tipo}/{id}/credits/`.

El diseño está en `openspec/changes/title-page/design.md` §2.1. TMDB se
reemplaza por un servicio falso que responde recortes reales del 13-14/10/2026.
"""

import copy
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient

# `movie/157336/credits`: tres del reparto y dos del equipo, uno de ellos no
# director, para probar que solo pasan los directores.
CREDITOS_INTERSTELLAR = {
    "id": 157336,
    "cast": [
        {"id": 10297, "name": "Matthew McConaughey", "character": "Cooper"},
        {"id": 1813, "name": "Anne Hathaway", "character": "Brand"},
        {"id": 3895, "name": "Michael Caine", "character": "Professor Brand"},
    ],
    "crew": [
        {"id": 527, "name": "Jonathan Nolan", "job": "Writer"},
        {"id": 525, "name": "Christopher Nolan", "job": "Director"},
    ],
}
# `tv/1396/credits`: en series no hay director a nivel serie; el equipo trae
# productores, que no deben aparecer como directores.
CREDITOS_BREAKING_BAD = {
    "id": 1396,
    "cast": [
        {"id": 17419, "name": "Bryan Cranston", "character": "Walter White"},
        {"id": 84497, "name": "Aaron Paul", "character": "Jesse Pinkman"},
    ],
    "crew": [
        {"id": 24951, "name": "Peter Gould", "job": "Co-Executive Producer"},
    ],
}
# `tv/1396`: los creadores, que hacen de «directores» de la serie.
DETALLE_BREAKING_BAD = {
    "id": 1396,
    "name": "Breaking Bad",
    "created_by": [{"id": 66633, "name": "Vince Gilligan"}],
}


class ServicioFalso:
    def __init__(self, creditos=None):
        self.creditos = creditos

    def get_credits(self, id_tmdb, tipo):
        datos = self.creditos or (
            CREDITOS_INTERSTELLAR if tipo == "movie" else CREDITOS_BREAKING_BAD
        )
        return copy.deepcopy(datos)

    def get_tv_detail(self, id_tmdb):
        return copy.deepcopy(DETALLE_BREAKING_BAD)


class CreditosTests(SimpleTestCase):
    def _get(self, url, servicio=None):
        with patch(
            "catalogo.views.get_catalog_service",
            side_effect=lambda idioma=None: servicio or ServicioFalso(),
        ):
            return APIClient().get(url)

    def test_pelicula_directores_del_equipo_y_reparto_con_personaje(self):
        respuesta = self._get("/api/catalogo/movie/157336/credits/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json(),
            {
                "directores": ["Christopher Nolan"],
                "reparto": [
                    {"nombre": "Matthew McConaughey", "personaje": "Cooper"},
                    {"nombre": "Anne Hathaway", "personaje": "Brand"},
                    {"nombre": "Michael Caine", "personaje": "Professor Brand"},
                ],
            },
        )

    def test_serie_usa_los_creadores_y_no_el_equipo(self):
        respuesta = self._get("/api/catalogo/tv/1396/credits/")

        self.assertEqual(respuesta.json()["directores"], ["Vince Gilligan"])
        self.assertEqual(
            respuesta.json()["reparto"][0],
            {"nombre": "Bryan Cranston", "personaje": "Walter White"},
        )

    def test_el_reparto_llega_hasta_50(self):
        muchos = copy.deepcopy(CREDITOS_INTERSTELLAR)
        muchos["cast"] = [
            {**muchos["cast"][0], "id": indice, "name": f"Actor {indice}"}
            for indice in range(60)
        ]

        respuesta = self._get(
            "/api/catalogo/movie/157336/credits/", ServicioFalso(creditos=muchos)
        )

        self.assertEqual(len(respuesta.json()["reparto"]), 50)
        self.assertEqual(respuesta.json()["reparto"][0]["nombre"], "Actor 0")

    def test_es_publico_y_un_id_invalido_responde_400(self):
        self.assertEqual(
            self._get("/api/catalogo/movie/157336/credits/").status_code, 200
        )
        self.assertEqual(self._get("/api/catalogo/movie/abc/credits/").status_code, 400)
