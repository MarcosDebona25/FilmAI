"""Lo que el encolado en Celery necesita para funcionar de verdad.

Los demás tests simulan `.delay()`, así que no notan si el broker no se puede usar.
"""

from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from catalogo.models import ProduccionAudiovisual, ProduccionEmbedding, TipoProduccion
from catalogo.services.materialization import _encolar_embedding


class TransporteDeRedisTests(SimpleTestCase):
    def test_se_puede_importar(self):
        # kombu 5.7 lo importa con `packaging` sin declararlo: en una instalación
        # limpia, todo `.delay()` fallaba con ModuleNotFoundError (05/11/2026).
        import kombu.transport.redis  # noqa: F401


class EncoladoDeEmbeddingTests(TestCase):
    def test_si_el_broker_falla_la_operacion_del_usuario_sigue(self):
        # El vector lo recupera el backfill: agregar a una lista no debe dar 500.
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=1, tipo=TipoProduccion.PELICULA, titulo="Moon"
        )

        with (
            patch(
                "catalogo.services.materialization.generar_embedding.delay",
                side_effect=ConnectionError("broker"),
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            _encolar_embedding(produccion)

        self.assertTrue(
            ProduccionEmbedding.objects.filter(produccion=produccion).exists()
        )
