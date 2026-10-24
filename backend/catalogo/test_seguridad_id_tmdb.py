"""Auditoría F7: `id_tmdb` inexistente o fuera de rango (24/10/2026).

Dos fallas del alta de reseñas, confirmadas en la auditoría run-2:

- Un id que TMDB no conoce respondía 404 (Not Found), pero dejaba en la base
  una `ProduccionAudiovisual` vacía: `materializar()` crea la fila antes de
  pedirle el detalle a TMDB.
- Un id mayor que el máximo de la columna (`integer` de Postgres) pasaba la
  validación y el INSERT terminaba en 500 (Internal Server Error).

Los tests de integración usan `materializar()` real con TMDB falso, igual que
`CalificarMaterializaTests`: lo que importa es qué queda en la base.
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.exceptions import TMDBNotFound, TMDBServerError
from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.models import Calificacion, ProduccionAudiovisual, TipoProduccion
from catalogo.serializers_reviews import CrearCalificacionSerializer
from catalogo.services.materialization import materializar
from catalogo.tests import _ParchesDeMaterializacion
from usuarios.factories import UsuarioFactory

# El máximo de una columna `integer` de Postgres, escrito a mano a propósito:
# si alguien cambiara la constante del código, este test lo notaría.
MAXIMO_POSTGRES = 2_147_483_647


def _campos_con_error(respuesta):
    return {(error["field"], error["code"]) for error in respuesta.data["errors"]}


class MaterializarIdInexistenteTests(_ParchesDeMaterializacion, TestCase):
    """Qué deja `materializar()` en la base cuando TMDB no tiene el id."""

    def test_un_id_que_tmdb_no_conoce_no_deja_fila(self):
        self.servicio.get_movie_detail.side_effect = TMDBNotFound("HTTP 404")

        with self.assertRaises(TMDBNotFound):
            materializar(999_999_999, "movie")

        self.assertFalse(ProduccionAudiovisual.objects.exists())

    def test_una_fila_que_ya_existia_no_se_borra(self):
        # La sync diaria (C-04b) refresca con `forzar=True`. Si TMDB dio de baja
        # un título que ya teníamos, la fila puede tener calificaciones y listas
        # colgando (CASCADE): borrarla se las llevaría puestas.
        existente = ProduccionAudiovisualFactory(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Fight Club"
        )
        self.servicio.get_movie_detail.side_effect = TMDBNotFound("HTTP 404")

        with self.assertRaises(TMDBNotFound):
            materializar(550, "movie", forzar=True)

        self.assertTrue(ProduccionAudiovisual.objects.filter(pk=existente.pk).exists())

    def test_un_fallo_transitorio_conserva_la_fila_para_reintentar(self):
        # Con TMDB caído el id sí puede existir: la fila queda sin enriquecer y
        # la próxima visita a la ficha la vuelve a encolar (comportamiento de
        # C-04a que este arreglo no cambia).
        self.servicio.get_movie_detail.side_effect = TMDBServerError("HTTP 503")

        with self.assertRaises(TMDBServerError):
            materializar(550, "movie")

        fila = ProduccionAudiovisual.objects.get(id_tmdb=550)
        self.assertIsNone(fila.fecha_enriquecimiento)


class CalificarIdInexistenteTests(_ParchesDeMaterializacion, TestCase):
    """`POST /api/reviews/` con ids que no sirven."""

    def setUp(self):
        super().setUp()
        self.cliente = APIClient()
        self.cliente.force_authenticate(UsuarioFactory())

    def _calificar(self, id_tmdb):
        return self.cliente.post(
            "/api/reviews/",
            {"id_tmdb": id_tmdb, "tipo": "movie", "valor": 8},
            format="json",
        )

    def test_un_id_que_tmdb_no_conoce_es_404_y_no_deja_filas(self):
        self.servicio.get_movie_detail.side_effect = TMDBNotFound("HTTP 404")

        respuesta = self._calificar(999_999_999)

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.data["code"], "upstream_not_found")
        self.assertFalse(ProduccionAudiovisual.objects.exists())
        self.assertFalse(Calificacion.objects.exists())

    def test_un_id_fuera_de_rango_es_400_sin_llamar_a_tmdb(self):
        respuesta = self._calificar(MAXIMO_POSTGRES + 1)

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            {
                "field": "id_tmdb",
                "code": "max_value",
                "params": {"maxValue": MAXIMO_POSTGRES},
            },
            respuesta.data["errors"],
        )
        self.servicio.get_movie_detail.assert_not_called()
        self.assertFalse(ProduccionAudiovisual.objects.exists())

    def test_el_maximo_de_la_columna_todavia_entra(self):
        # El límite es inclusivo: sin este caso, un `<` en vez de `<=` pasaría.
        entrada = CrearCalificacionSerializer(
            data={"id_tmdb": MAXIMO_POSTGRES, "tipo": "movie", "valor": 8}
        )

        self.assertTrue(entrada.is_valid(), entrada.errors)


class LecturasIdFueraDeRangoTests(TestCase):
    """Las lecturas validan el mismo rango: 400 con el campo, no un 404 mudo."""

    def setUp(self):
        self.cliente = APIClient()
        self.cliente.force_authenticate(UsuarioFactory())

    def test_resenas_de_la_comunidad(self):
        respuesta = self.cliente.get(
            "/api/reviews/", {"id_tmdb": MAXIMO_POSTGRES + 1, "tipo": "movie"}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(("id_tmdb", "max_value"), _campos_con_error(respuesta))

    def test_mi_calificacion_en_una_ficha(self):
        respuesta = self.cliente.get(
            "/api/reviews/mias/", {"id_tmdb": MAXIMO_POSTGRES + 1, "tipo": "movie"}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(("id_tmdb", "max_value"), _campos_con_error(respuesta))


class CatalogoIdFueraDeRangoTests(TestCase):
    """Las vistas de TMDB cortan antes de gastar una llamada que da 404 seguro."""

    def setUp(self):
        self.cliente = APIClient()
        # Un error explícito y no un Mock suelto: si la vista llegara a TMDB, DRF
        # intentaría serializar el Mock que devuelve, y cada atributo que consulta
        # es otro Mock. En el RED del 24/10/2026 eso agotó el 1,5 GB del contenedor.
        parche = patch(
            "catalogo.views.get_catalog_service",
            side_effect=AssertionError("La vista no tendría que llegar a TMDB"),
        )
        parche.start()
        self.addCleanup(parche.stop)

    def test_detalle_creditos_y_plataformas(self):
        fuera = MAXIMO_POSTGRES + 1
        for url in (
            f"/api/catalogo/movie/{fuera}/",
            f"/api/catalogo/tv/{fuera}/",
            f"/api/catalogo/movie/{fuera}/credits/",
            f"/api/catalogo/tv/{fuera}/providers/?pais=AR",
            f"/api/catalogo/keywords/?id_tmdb={fuera}&tipo=movie",
        ):
            with self.subTest(url=url):
                respuesta = self.cliente.get(url)

                self.assertEqual(respuesta.status_code, 400)
                self.assertIn(
                    {
                        "field": "id_tmdb",
                        "code": "max_value",
                        "params": {"maxValue": MAXIMO_POSTGRES},
                    },
                    respuesta.data["errors"],
                )
