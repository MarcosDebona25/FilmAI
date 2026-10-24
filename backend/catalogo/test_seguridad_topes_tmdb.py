"""Auditoría F6: parámetros de `trending` y topes de llamadas a TMDB (24/10/2026).

Tres cosas, cada una con su clase:

- `media_type` y `time_window` de `trending` iban sin validar al path de TMDB:
  `media_type=../movie/550` llevaba el pedido a otro endpoint.
- Un pedido podía encadenar muchas llamadas: Buscar con texto en «Todo» hace
  hasta 10 (20 si hay que completar en inglés) y cada una se reintenta 3 veces.
  Tope por pedido: 30 llamadas, reintentos incluidos.
- El límite del catálogo (60 por minuto) cuenta pedidos, no llamadas a TMDB:
  textos distintos, que no pegan en la caché, multiplicaban por 10 lo que un
  cliente le podía costar a nuestra clave. Tope por IP: llamadas por minuto,
  contadas en el momento de cada una; lo que sale de la caché no cuenta.

Los dobles de TMDB que no deberían usarse lanzan un error explícito: un Mock
suelto devuelto como respuesta hace que DRF intente serializarlo sin fin.
"""

import threading
from unittest.mock import Mock, patch

import fakeredis
import httpx
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import Throttled
from rest_framework.test import APIClient

from catalogo.cache import TMDBClientCache
from catalogo.client import TMDBClient
from catalogo.exceptions import TMDBPresupuestoAgotado
from catalogo.presupuesto import (
    MAX_LLAMADAS_POR_PEDIDO,
    contar_llamadas,
    registrar_llamada,
)
from catalogo.services.browse import explorar

_PAGINA_VACIA = {"page": 1, "total_pages": 0, "total_results": 0, "results": []}


def _sin_tmdb(*args, **kwargs):
    raise AssertionError("La vista no tendría que llegar a TMDB")


def _servicio_que_llama(veces):
    """Doble de TMDB: cada listado cuesta `veces` llamadas, como el cliente real."""

    def listado(*args, **kwargs):
        for _ in range(veces):
            registrar_llamada()
        return _PAGINA_VACIA

    return Mock(get_now_playing=Mock(side_effect=listado))


class TrendingParametrosTests(TestCase):
    """`media_type` y `time_window` son listas cerradas, no texto libre."""

    def test_un_media_type_fuera_de_la_lista_es_400_sin_llamar_a_tmdb(self):
        with patch("catalogo.views.CatalogoBaseView._service", side_effect=_sin_tmdb):
            for valor in ("person", "../movie/550", "movie/550/account_states"):
                with self.subTest(media_type=valor):
                    respuesta = APIClient().get(
                        "/api/catalogo/trending/", {"media_type": valor}
                    )

                    self.assertEqual(respuesta.status_code, 400)
                    self.assertIn(
                        {
                            "field": "media_type",
                            "code": "invalid_choice",
                            "params": {"allowedValues": ["all", "movie", "tv"]},
                        },
                        respuesta.data["errors"],
                    )

    def test_un_time_window_fuera_de_la_lista_es_400_sin_llamar_a_tmdb(self):
        with patch("catalogo.views.CatalogoBaseView._service", side_effect=_sin_tmdb):
            for valor in ("month", "week/../../configuration"):
                with self.subTest(time_window=valor):
                    respuesta = APIClient().get(
                        "/api/catalogo/trending/", {"time_window": valor}
                    )

                    self.assertEqual(respuesta.status_code, 400)
                    self.assertIn(
                        {
                            "field": "time_window",
                            "code": "invalid_choice",
                            "params": {"allowedValues": ["day", "week"]},
                        },
                        respuesta.data["errors"],
                    )

    def test_los_valores_validos_llegan_a_tmdb(self):
        servicio = Mock(get_trending=Mock(return_value=_PAGINA_VACIA))
        with patch("catalogo.views.CatalogoBaseView._service", return_value=servicio):
            respuesta = APIClient().get(
                "/api/catalogo/trending/", {"media_type": "tv", "time_window": "day"}
            )

        self.assertEqual(respuesta.status_code, 200)
        servicio.get_trending.assert_called_once_with("tv", "day", 1)


class PresupuestoPorPedidoTests(SimpleTestCase):
    """El tope de llamadas por pedido, sin pasar por HTTP."""

    def test_fuera_de_un_pedido_no_hay_tope(self):
        # Celery, la sync diaria y el seed llaman a TMDB sin pedido HTTP de por
        # medio: el seed hace miles de llamadas y no tiene que cortarse.
        for _ in range(MAX_LLAMADAS_POR_PEDIDO * 3):
            registrar_llamada()

    def test_la_llamada_que_pasa_el_tope_corta(self):
        with contar_llamadas():
            for _ in range(MAX_LLAMADAS_POR_PEDIDO):
                registrar_llamada()
            with self.assertRaises(TMDBPresupuestoAgotado):
                registrar_llamada()

    def test_los_reintentos_cuentan(self):
        # TMDB responde 503 siempre: sin tope, el cliente hace 4 intentos.
        intentos = []

        def tmdb_caido(request):
            intentos.append(request)
            return httpx.Response(503)

        cliente = TMDBClient(api_key="x", transport=httpx.MockTransport(tmdb_caido))
        with (
            patch("catalogo.client.time.sleep"),
            patch("catalogo.presupuesto.MAX_LLAMADAS_POR_PEDIDO", 2),
            contar_llamadas(),
            self.assertRaises(TMDBPresupuestoAgotado),
        ):
            cliente.get_now_playing()

        self.assertEqual(len(intentos), 2)

    def test_las_llamadas_desde_hilos_cuentan_para_el_mismo_pedido(self):
        # Buscar con texto en «Todo» pide 5 páginas de películas y 5 de series
        # en hilos aparte. Los hilos no heredan el contexto solos: sin pasarlo,
        # esas 10 llamadas no se contarían.
        def search(q, tipo, page, anio=None):
            registrar_llamada()
            return {"total_pages": 5, "results": []}

        with contar_llamadas() as contador:
            explorar(Mock(search=Mock(side_effect=search)), q="dune", tipo="all")

        self.assertEqual(contador.total, 10)


class PresupuestoEnLaVistaTests(TestCase):
    def test_un_pedido_que_pasa_el_tope_responde_503(self):
        servicio = _servicio_que_llama(MAX_LLAMADAS_POR_PEDIDO + 1)
        with patch("catalogo.views.CatalogoBaseView._service", return_value=servicio):
            respuesta = APIClient().get("/api/catalogo/now-playing/")

        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.data["code"], "upstream_unavailable")


@override_settings(TMDB_LLAMADAS_POR_IP_POR_MINUTO=10)
class LimitePorIPTests(TestCase):
    """El límite por IP cuenta llamadas a TMDB en el momento, no pedidos."""

    def setUp(self):
        # El ejecutor del proyecto ya vacía la caché antes de cada test; acá se
        # hace explícito porque los contadores viven ahí.
        cache.clear()

    def test_cuenta_llamadas_y_no_pedidos(self):
        servicio = _servicio_que_llama(4)
        with patch("catalogo.views.CatalogoBaseView._service", return_value=servicio):
            respuestas = [
                APIClient().get("/api/catalogo/now-playing/") for _ in range(4)
            ]

        # Llamadas 1-4 y 5-8 entran; el tercer pedido corta en la 11.
        self.assertEqual([r.status_code for r in respuestas], [200, 200, 429, 429])
        self.assertEqual(respuestas[2].data["code"], "throttled")
        self.assertLessEqual(int(respuestas[2]["Retry-After"]), 60)

    def test_pedidos_en_paralelo_no_esquivan_el_limite(self):
        # 10 pedidos a la vez desde la misma IP, 4 llamadas cada uno. Cobrar al
        # terminar el pedido dejaba pasar las 40 (sugerencia de PR-Agent en #129):
        # contando en el momento, entran exactamente 10.
        entraron = []

        def pedido():
            with contar_llamadas(ident="203.0.113.7"):
                for _ in range(4):
                    try:
                        registrar_llamada()
                    except Throttled:
                        return
                    entraron.append(1)

        hilos = [threading.Thread(target=pedido) for _ in range(10)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(len(entraron), 10)

    def test_cada_ip_tiene_su_propio_limite(self):
        with contar_llamadas(ident="203.0.113.7"):
            for _ in range(10):
                registrar_llamada()
        with contar_llamadas(ident="198.51.100.2"):
            registrar_llamada()

    def test_si_el_contador_desaparece_se_vuelve_a_sembrar(self):
        # Redis puede desalojar la clave a mitad de minuto: no tiene que dar 500.
        with contar_llamadas(ident="203.0.113.7"):
            registrar_llamada()
            cache.clear()
            registrar_llamada()

    def test_lo_que_sale_de_la_cache_no_cuenta(self):
        llamadas_http = []

        def tmdb(request):
            llamadas_http.append(request)
            return httpx.Response(200, json=_PAGINA_VACIA)

        servicio = TMDBClientCache(
            TMDBClient(api_key="x", transport=httpx.MockTransport(tmdb)),
            fakeredis.FakeRedis(),
        )
        with patch("catalogo.views.CatalogoBaseView._service", return_value=servicio):
            estados = [
                APIClient().get("/api/catalogo/now-playing/").status_code
                for _ in range(15)
            ]

        # Una sola llamada real: las otras 14 salen de la caché y no se cobran.
        self.assertEqual(len(llamadas_http), 1)
        self.assertNotIn(429, estados)

    def test_recomendado_tambien_tiene_los_topes(self):
        from catalogo.views import RecommendedView, _TopesTMDBMixin

        self.assertTrue(issubclass(RecommendedView, _TopesTMDBMixin))
