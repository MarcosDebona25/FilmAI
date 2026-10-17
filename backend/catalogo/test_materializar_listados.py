"""Los listados guardan en el catálogo lo que muestran (C-04a, 16/10/2026)."""

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache as dj_cache
from django.test import TestCase
from django.utils import timezone

from catalogo.models import ProduccionAudiovisual, TipoProduccion
from catalogo.services.materialization import materializar_listado_en_segundo_plano

TENDENCIAS = {
    "results": [
        {"id": 550, "media_type": "movie", "title": "Fight Club"},
        {"id": 1396, "media_type": "tv", "name": "Breaking Bad"},
        {"id": 287, "media_type": "person", "name": "Brad Pitt"},
    ]
}


class MaterializarListadoTests(TestCase):
    def setUp(self):
        # La ventana de 10 minutos vive en la caché: cada test arranca limpio.
        dj_cache.clear()
        parche = patch("catalogo.services.materialization.materializar_produccion")
        self.tarea = parche.start()
        self.addCleanup(parche.stop)

    def encolados(self):
        return [llamada.args for llamada in self.tarea.delay.call_args_list]

    def test_encola_peliculas_y_series_y_descarta_personas(self):
        materializar_listado_en_segundo_plano(TENDENCIAS["results"])

        self.assertEqual(self.encolados(), [(550, "movie"), (1396, "tv")])

    def test_en_un_listado_de_un_solo_tipo_usa_ese_tipo(self):
        # `discover/` y `search/` no traen `media_type` en cada ítem.
        materializar_listado_en_segundo_plano([{"id": 550}, {"id": 13}], "movie")

        self.assertEqual(self.encolados(), [(13, "movie"), (550, "movie")])

    def test_lo_que_ya_esta_fresco_no_se_encola(self):
        ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="Fight Club",
            fecha_enriquecimiento=timezone.now(),
        )
        # Misma id que una serie: la clave es (id, tipo), no solo la id.
        materializar_listado_en_segundo_plano(
            [{"id": 550, "media_type": "movie"}, {"id": 550, "media_type": "tv"}]
        )

        self.assertEqual(self.encolados(), [(550, "tv")])

    def test_lo_vencido_o_sin_enriquecer_se_vuelve_a_encolar(self):
        ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="Fight Club",
            fecha_enriquecimiento=timezone.now() - timedelta(days=91),
        )
        ProduccionAudiovisual.objects.create(
            id_tmdb=13, tipo=TipoProduccion.PELICULA, titulo="Forrest Gump"
        )

        materializar_listado_en_segundo_plano([{"id": 550}, {"id": 13}], "movie")

        self.assertEqual(self.encolados(), [(13, "movie"), (550, "movie")])

    def test_el_mismo_titulo_se_encola_una_vez_cada_10_minutos(self):
        # Muchas visitas al Home seguidas, con el worker todavía sin terminar.
        for _ in range(5):
            materializar_listado_en_segundo_plano(TENDENCIAS["results"])

        self.assertEqual(self.encolados(), [(550, "movie"), (1396, "tv")])

    def test_si_no_se_pudo_encolar_el_proximo_listado_lo_reintenta(self):
        # La marca de 10 minutos no puede quedar puesta si la tarea no salió.
        self.tarea.delay.side_effect = [RuntimeError("broker caído"), None]

        with self.assertRaises(RuntimeError):
            materializar_listado_en_segundo_plano([{"id": 550}], "movie")
        materializar_listado_en_segundo_plano([{"id": 550}], "movie")

        self.assertEqual(self.encolados(), [(550, "movie"), (550, "movie")])

    def test_un_listado_vacio_o_raro_no_encola_nada(self):
        materializar_listado_en_segundo_plano(None)
        materializar_listado_en_segundo_plano([{"id": "x", "media_type": "movie"}])

        self.tarea.delay.assert_not_called()


class VistasDeListadosMaterializanTests(TestCase):
    """Las vistas responden lo de TMDB y encolan; un fallo al encolar no se nota."""

    def setUp(self):
        dj_cache.clear()
        servicio = patch("catalogo.views.get_catalog_service").start()
        self.addCleanup(patch.stopall)
        servicio.return_value.get_trending.return_value = TENDENCIAS
        servicio.return_value.discover.return_value = {"results": [{"id": 13}]}
        self.listado = patch(
            "catalogo.views.materializar_listado_en_segundo_plano"
        ).start()
        from rest_framework.test import APIClient

        self.api = APIClient()

    def test_tendencias_encola_su_listado(self):
        respuesta = self.api.get("/api/catalogo/trending/?media_type=all")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data, TENDENCIAS)
        self.listado.assert_called_once_with(TENDENCIAS["results"], None)

    def test_discover_encola_con_su_tipo(self):
        self.api.get("/api/catalogo/discover/?tipo=tv")

        self.listado.assert_called_once_with([{"id": 13}], "tv")

    def test_si_encolar_falla_el_listado_se_responde_igual(self):
        # La base o el broker caídos no pueden dejar el Home sin tendencias.
        self.listado.side_effect = RuntimeError("broker caído")

        with self.assertLogs("catalogo.views", level="ERROR"):
            respuesta = self.api.get("/api/catalogo/trending/?media_type=all")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data, TENDENCIAS)
