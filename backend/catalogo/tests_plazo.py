"""El plazo de red: dentro de él, TMDB y Ollama esperan menos (chatbot, H3).

Fuera de un `plazo_de_red` nada cambia: es lo que prueban los tests que terminan
en «fuera del plazo». Lo abre solo el chatbot, alrededor de sus tools.
"""

from unittest.mock import patch

import httpx
from django.test import SimpleTestCase, override_settings

from catalogo.client import TMDBClient
from catalogo.exceptions import TMDBTransportError
from catalogo.plazo import para_tmdb, plazo_de_red, que_queda
from catalogo.services.embeddings import (
    PRESUPUESTO_CARGA,
    PRESUPUESTO_CHAT,
    EmbeddingProviderError,
)
from catalogo.services.semantica import _vector_de


class PlazoDeRedTests(SimpleTestCase):
    def test_fuera_del_plazo_no_hay_limite(self):
        self.assertIsNone(que_queda())
        self.assertIsNone(para_tmdb())

    def test_dentro_del_plazo_tmdb_usa_el_timeout_corto(self):
        with plazo_de_red(10, timeout_tmdb=3, reintentos_tmdb=1):
            limite = para_tmdb()

            self.assertEqual(limite.timeout, 3)
            self.assertEqual(limite.reintentos, 1)
            self.assertAlmostEqual(que_queda(), 10, delta=0.5)

    def test_si_queda_menos_que_el_timeout_corto_se_usa_lo_que_queda(self):
        with plazo_de_red(1, timeout_tmdb=3, reintentos_tmdb=1):
            self.assertLessEqual(para_tmdb().timeout, 1)

    def test_el_tiempo_que_queda_baja_con_el_reloj(self):
        with patch("catalogo.plazo._ahora", side_effect=[100.0, 104.0]):
            with plazo_de_red(10, timeout_tmdb=3, reintentos_tmdb=1):
                self.assertEqual(que_queda(), 6.0)

    def test_al_salir_del_bloque_ya_no_hay_plazo(self):
        with plazo_de_red(10, timeout_tmdb=3, reintentos_tmdb=1):
            pass

        self.assertIsNone(que_queda())


@override_settings(TMDB_API_KEY="test-key", TMDB_TIMEOUT=5.0)
class ClienteTMDBConPlazoTests(SimpleTestCase):
    def cliente(self, handler):
        return TMDBClient(transport=httpx.MockTransport(handler))

    def caido(self, pedidos):
        def handler(request):
            # `extensions["timeout"]` es el timeout con el que httpx hizo el pedido.
            pedidos.append(request.extensions["timeout"]["read"])
            raise httpx.ConnectError("offline", request=request)

        return handler

    def test_fuera_del_plazo_usa_el_timeout_general_y_tres_reintentos(self):
        pedidos = []
        cliente = self.cliente(self.caido(pedidos))

        with patch("catalogo.client.time.sleep"):
            with self.assertRaises(TMDBTransportError):
                cliente.get_movie_detail(550)

        self.assertEqual(pedidos, [5.0, 5.0, 5.0, 5.0])

    def test_dentro_del_plazo_usa_el_timeout_corto_y_un_solo_reintento(self):
        pedidos = []
        cliente = self.cliente(self.caido(pedidos))

        with (
            plazo_de_red(100, timeout_tmdb=3, reintentos_tmdb=1),
            patch("catalogo.client.time.sleep"),
        ):
            with self.assertRaises(TMDBTransportError):
                cliente.get_movie_detail(550)

        self.assertEqual(pedidos, [3, 3])

    def test_sin_tiempo_no_sale_a_la_red(self):
        pedidos = []
        cliente = self.cliente(self.caido(pedidos))

        with plazo_de_red(0, timeout_tmdb=3, reintentos_tmdb=1):
            with self.assertRaises(TMDBTransportError):
                cliente.get_movie_detail(550)

        self.assertEqual(pedidos, [])

    def test_no_reintenta_si_la_espera_no_entra_en_lo_que_queda(self):
        pedidos = []
        cliente = self.cliente(self.caido(pedidos))

        # Queda medio segundo y la espera antes del primer reintento es de 1 s.
        with (
            plazo_de_red(0.5, timeout_tmdb=3, reintentos_tmdb=1),
            patch("catalogo.client.time.sleep") as dormir,
        ):
            with self.assertRaises(TMDBTransportError):
                cliente.get_movie_detail(550)

        self.assertEqual(len(pedidos), 1)
        dormir.assert_not_called()

    def test_una_respuesta_normal_dentro_del_plazo_sale_igual(self):
        cliente = self.cliente(lambda request: httpx.Response(200, json={"id": 550}))

        with plazo_de_red(10, timeout_tmdb=3, reintentos_tmdb=1):
            self.assertEqual(cliente.get_movie_detail(550), {"id": 550})


class OllamaConPlazoTests(SimpleTestCase):
    """`buscar_semantico` espera a Ollama como mucho lo que le queda al turno."""

    def embeber(self, cargado):
        with (
            patch("catalogo.services.semantica.modelo_cargado", return_value=cargado),
            patch(
                "catalogo.services.semantica.generar_vector", return_value=[0.0]
            ) as generar,
            patch("catalogo.services.semantica.pedir_carga_del_modelo"),
        ):
            _vector_de("algo lento")
        return generar

    def test_fuera_del_plazo_la_carga_espera_lo_de_siempre(self):
        generar = self.embeber(cargado=False)

        self.assertEqual(generar.call_args.kwargs, PRESUPUESTO_CARGA)

    def test_dentro_del_plazo_la_carga_espera_solo_lo_que_queda(self):
        with plazo_de_red(4, timeout_tmdb=3, reintentos_tmdb=1):
            generar = self.embeber(cargado=False)

        self.assertLessEqual(generar.call_args.kwargs["timeout"], 4)
        self.assertEqual(generar.call_args.kwargs["reintentos"], 0)

    def test_con_tiempo_de_sobra_el_modelo_cargado_espera_lo_de_siempre(self):
        with plazo_de_red(15, timeout_tmdb=3, reintentos_tmdb=1):
            generar = self.embeber(cargado=True)

        self.assertEqual(generar.call_args.kwargs, PRESUPUESTO_CHAT)

    def test_sin_tiempo_no_llama_a_ollama(self):
        with plazo_de_red(0, timeout_tmdb=3, reintentos_tmdb=1):
            with (
                patch("catalogo.services.semantica.modelo_cargado") as estado,
                patch("catalogo.services.semantica.generar_vector") as generar,
                self.assertRaises(EmbeddingProviderError),
            ):
                _vector_de("algo lento")

        estado.assert_not_called()
        generar.assert_not_called()
