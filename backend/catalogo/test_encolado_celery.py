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

    def test_redis_py_tiene_la_version_que_pide_kombu(self):
        # kombu chequea la versión de redis-py recién al abrir el canal, no al
        # importar: con redis-py 5.3.1 y kombu 5.7, todo `.delay()` fallaba con
        # VersionMismatch y el test de arriba seguía en verde (07/11/2026).
        # `_get_client` es ese chequeo; con un `self` mínimo no se conecta.
        from types import SimpleNamespace

        from kombu.transport.redis import Channel

        Channel._get_client(SimpleNamespace(global_keyprefix=None))


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
