"""OT-62: traducciones y `generos_ids` al materializar y en el relleno."""

from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalogo.exceptions import TMDBServerError
from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.management.commands.rellenar_traducciones import pendientes, rellenar
from catalogo.models import ProduccionAudiovisual, ProduccionTraduccion
from catalogo.services.embeddings import calcular_source_hash, construir_texto_canonico
from catalogo.services.materialization import materializar

DETALLES = {
    "en-US": {
        "id": 550,
        "title": "Fight Club",
        "name": "Fight Club",
        "overview": "An insomniac office worker...",
        "poster_path": "/en.jpg",
        "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
    },
    "es-MX": {
        "id": 550,
        "title": "El club de la pelea",
        "name": "El club de la pelea",
        "overview": "Un oficinista insomne...",
        "poster_path": "/es.jpg",
        "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Suspenso"}],
    },
}


class ServiciosPorIdioma:
    """Sustituye `get_catalog_service`: un servicio falso por variante de TMDB."""

    def __init__(self):
        self.servicios = {}
        self.falla = set()

    def __call__(self, idioma=None):
        idioma = idioma or "en-US"
        if idioma not in self.servicios:
            servicio = Mock()

            def detalle(id_tmdb, idioma=idioma):
                if (idioma, id_tmdb) in self.falla or idioma in self.falla:
                    raise TMDBServerError("TMDB returned HTTP 500")
                return {**DETALLES[idioma], "id": id_tmdb}

            servicio.get_movie_detail.side_effect = detalle
            servicio.get_tv_detail.side_effect = detalle
            servicio.get_credits.return_value = {"cast": [], "crew": []}
            servicio.get_keywords.return_value = {"keywords": [], "results": []}
            self.servicios[idioma] = servicio
        return self.servicios[idioma]


class ConServiciosPorIdioma(TestCase):
    def setUp(self):
        self.fabrica = ServiciosPorIdioma()
        for destino in (
            "catalogo.services.materialization.get_catalog_service",
            "catalogo.management.commands.rellenar_traducciones.get_catalog_service",
        ):
            parche = patch(destino, side_effect=self.fabrica)
            parche.start()
            self.addCleanup(parche.stop)
        parche = patch("catalogo.services.materialization.generar_embedding")
        parche.start()
        self.addCleanup(parche.stop)


class MaterializacionConTraduccionesTests(ConServiciosPorIdioma):
    def test_guarda_canonico_en_ingles_ids_de_genero_y_traduccion_al_espanol(self):
        produccion = materializar(550, "movie")
        self.assertEqual(produccion.titulo, "Fight Club")
        self.assertEqual(produccion.generos, ["Drama", "Thriller"])
        self.assertEqual(produccion.generos_ids, [18, 53])
        traduccion = produccion.traducciones.get()
        self.assertEqual(
            (
                traduccion.idioma,
                traduccion.titulo,
                traduccion.sinopsis,
                traduccion.poster,
            ),
            ("es", "El club de la pelea", "Un oficinista insomne...", "/es.jpg"),
        )

    def test_el_texto_de_embeddings_y_su_hash_no_cambian(self):
        produccion = materializar(550, "movie")
        texto = construir_texto_canonico(produccion)
        self.assertIn("Title: Fight Club", texto)
        self.assertIn("Genres: Drama, Thriller", texto)
        self.assertNotIn("pelea", texto)
        self.assertNotIn("18", texto)
        sin_ids = ProduccionAudiovisual(
            titulo=produccion.titulo,
            generos=produccion.generos,
            directores=produccion.directores,
            reparto=produccion.reparto,
            keywords=produccion.keywords,
            sinopsis=produccion.sinopsis,
        )
        self.assertEqual(
            calcular_source_hash(texto),
            calcular_source_hash(construir_texto_canonico(sin_ids)),
        )

    def test_forzar_actualiza_la_traduccion_sin_duplicarla(self):
        produccion = materializar(550, "movie")
        DETALLES["es-MX"]["title"] = "El club de la lucha"
        self.addCleanup(DETALLES["es-MX"].__setitem__, "title", "El club de la pelea")
        materializar(550, "movie", forzar=True)
        self.assertEqual(produccion.traducciones.get().titulo, "El club de la lucha")
        self.assertEqual(ProduccionTraduccion.objects.count(), 1)

    def test_fallo_de_la_traduccion_no_invalida_el_enriquecimiento(self):
        self.fabrica.falla.add("es-MX")
        with self.assertLogs("catalogo.services.materialization", "ERROR"):
            produccion = materializar(550, "movie")
        self.assertEqual(produccion.titulo, "Fight Club")
        self.assertIsNotNone(produccion.fecha_enriquecimiento)
        self.assertFalse(produccion.traducciones.exists())

    def test_serie_usa_name_como_titulo_traducido(self):
        produccion = materializar(1396, "tv")
        self.assertEqual(produccion.traducciones.get().titulo, "El club de la pelea")


class RellenoDeTraduccionesTests(ConServiciosPorIdioma):
    def _enriquecida(self, **extra):
        return ProduccionAudiovisualFactory(
            fecha_enriquecimiento=timezone.now(),
            generos=["Drama"],
            generos_ids=[],
            **extra,
        )

    def test_completa_ids_y_traducciones_y_es_idempotente(self):
        a, b = self._enriquecida(), self._enriquecida()
        nunca = ProduccionAudiovisualFactory(fecha_enriquecimiento=None)
        titulos = {a.pk: a.titulo, b.pk: b.titulo}
        self.assertEqual(rellenar(), {"procesadas": 2, "fallidas": 0, "pendientes": 0})
        for produccion in (a, b):
            produccion.refresh_from_db()
            self.assertEqual(produccion.generos_ids, [18, 53])
            self.assertEqual(
                produccion.titulo, titulos[produccion.pk]
            )  # canónico intacto
            self.assertEqual(produccion.traducciones.get().idioma, "es")
        self.assertFalse(nunca.traducciones.exists())
        self.assertEqual(rellenar(), {"procesadas": 0, "fallidas": 0, "pendientes": 0})
        self.assertEqual(ProduccionTraduccion.objects.count(), 2)

    def test_un_item_fallido_no_corta_el_resto(self):
        mala, buena = self._enriquecida(), self._enriquecida()
        self.fabrica.falla.add(("en-US", mala.id_tmdb))
        resultado = rellenar()
        self.assertEqual((resultado["procesadas"], resultado["fallidas"]), (1, 1))
        self.assertTrue(buena.traducciones.exists())
        self.assertEqual(list(pendientes()), [mala])

    def test_limite_y_comando(self):
        for _ in range(3):
            self._enriquecida()
        self.assertEqual(rellenar(limite=2, lote=1)["pendientes"], 1)
        salida = StringIO()
        call_command("rellenar_traducciones", stdout=salida)
        self.assertIn("1 procesadas, 0 con error, 0 pendientes", salida.getvalue())
