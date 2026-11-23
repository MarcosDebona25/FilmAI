"""Los títulos sin póster no salen en el descubrimiento (21/11/2026).

Sin texto (Home, Buscar sin texto, recomendados) se descartan; con texto (la
búsqueda por nombre) se encuentran igual. Los listados salen de TMDB, así que
estos tests usan un servicio falso con un ítem con póster y otro sin.
"""

from unittest.mock import patch

from django.core.cache import cache as dj_cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from catalogo.services.explore import con_poster, tiene_poster

CON = {
    "id": 1,
    "title": "Con póster",
    "poster_path": "/a.jpg",
    "vote_count": 900,
    "popularity": 50,
    "genre_ids": [],
}
SIN = {**CON, "id": 2, "title": "Sin póster", "poster_path": None}
VACIO = {**CON, "id": 3, "title": "Póster vacío", "poster_path": ""}


def pagina(*items):
    # Copias: las vistas anotan `media_type` sobre los ítems.
    return {
        "page": 1,
        "total_pages": 7,
        "total_results": 130,
        "results": [dict(i) for i in items],
    }


class TMDBFalso:
    def __init__(self):
        self.catalogo = pagina(CON, SIN, VACIO)

    def discover(self, *args, **kwargs):
        return pagina(CON, SIN, VACIO)

    def search(self, query, tipo, page=1, anio=None):
        return pagina(CON, SIN, VACIO)

    def get_trending(self, *args, **kwargs):
        return pagina(CON, SIN, VACIO)

    def get_now_playing(self, *args, **kwargs):
        return pagina(CON, SIN, VACIO)


class Base(SimpleTestCase):
    def setUp(self):
        dj_cache.clear()
        for destino in (
            "catalogo.views.get_catalog_service",
            "catalogo.views.materializar_listado_en_segundo_plano",
        ):
            parche = patch(destino, return_value=TMDBFalso())
            parche.start()
            self.addCleanup(parche.stop)
        self.api = APIClient()

    def ids(self, url, **params):
        respuesta = self.api.get(url, params, HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(respuesta.status_code, 200)
        return sorted(item["id"] for item in respuesta.data["results"]), respuesta.data


class FuncionTests(SimpleTestCase):
    def test_none_y_vacio_cuentan_como_sin_poster(self):
        self.assertTrue(tiene_poster(CON))
        self.assertFalse(tiene_poster(SIN))
        self.assertFalse(tiene_poster(VACIO))
        self.assertFalse(tiene_poster({"id": 9}))

    def test_con_poster_no_muta_el_original_ni_toca_los_totales(self):
        original = pagina(CON, SIN)

        filtrado = con_poster(original)

        self.assertEqual([i["id"] for i in filtrado["results"]], [1])
        self.assertEqual(len(original["results"]), 2)
        # Páginas cortas: los totales siguen siendo los de TMDB (ver decisiones.md).
        self.assertEqual((filtrado["total_pages"], filtrado["total_results"]), (7, 130))


class DescubrimientoTests(Base):
    def test_buscar_sin_texto_descarta_los_sin_poster(self):
        for tipo in ("movie", "tv", "all"):
            with self.subTest(tipo=tipo):
                ids, _ = self.ids("/api/catalogo/explore/", tipo=tipo)
                self.assertTrue(ids)
                self.assertEqual(set(ids), {1})

    def test_buscar_con_texto_los_encuentra(self):
        ids, _ = self.ids("/api/catalogo/explore/", q="poster", tipo="movie")

        # La ventana pide 5 páginas iguales: se comparan los ids distintos.
        self.assertEqual(set(ids), {1, 2, 3})

    def test_la_busqueda_por_nombre_no_filtra(self):
        ids, _ = self.ids("/api/catalogo/search/", query="poster", tipo="movie")

        self.assertEqual(ids, [1, 2, 3])

    def test_discover_trending_y_en_cartelera_los_descartan(self):
        for url, params in (
            ("/api/catalogo/discover/", {"tipo": "movie"}),
            ("/api/catalogo/trending/", {}),
            ("/api/catalogo/now-playing/", {}),
        ):
            with self.subTest(url=url):
                ids, datos = self.ids(url, **params)
                self.assertEqual(ids, [1])
                # Los totales de TMDB se conservan (páginas cortas, no huecos).
                self.assertEqual(datos["total_pages"], 7)


class RecomendadoTests(SimpleTestCase):
    def test_la_fila_recomendado_descarta_los_sin_poster(self):
        from catalogo.services.recomendado import _de_un_tipo

        resultados = _de_un_tipo(TMDBFalso(), "movie", [(18, 1)], set())

        self.assertEqual([i["id"] for i in resultados], [1])
