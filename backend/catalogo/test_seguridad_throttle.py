"""F3 de la auditoría: el límite del catálogo se eludía con `X-Forwarded-For`.

Sin `NUM_PROXIES`, DRF toma el header como identidad del cliente: quien lo cambia
en cada pedido obtiene un contador nuevo cada vez y el límite de 60 por minuto
nunca se alcanza.
"""

from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.settings import api_settings
from rest_framework.test import APIClient

from catalogo.services.tmdb import get_catalog_service

RUTA = "/api/catalogo/now-playing/"


class CatalogoThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        get_catalog_service.cache_clear()
        patcher = patch(
            "catalogo.views.CatalogoBaseView._service",
            return_value=type(
                "Servicio",
                (),
                {"get_now_playing": lambda self, page: {"results": []}},
            )(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = APIClient()

    def test_rotar_x_forwarded_for_no_evita_el_limite(self):
        estados = [
            self.client.get(
                RUTA, HTTP_X_FORWARDED_FOR=f"10.9.{i // 250}.{i % 250}"
            ).status_code
            for i in range(70)
        ]
        self.assertEqual(estados.count(429), 10)
        self.assertEqual(estados[60], 429)

    def test_num_proxies_por_defecto_es_cero(self):
        self.assertEqual(api_settings.NUM_PROXIES, 0)

    def test_con_un_proxy_se_toma_la_ip_que_anadio_el_proxy_propio(self):
        """Con NUM_PROXIES=1 cuenta la última IP del header, no la que escribe el cliente."""
        with override_settings(
            REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
        ):
            estados = [
                self.client.get(
                    RUTA, HTTP_X_FORWARDED_FOR=f"6.6.6.{i % 250}, 203.0.113.9"
                ).status_code
                for i in range(65)
            ]
        self.assertEqual(estados[60], 429)


class PaginaMaximaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_una_pagina_enorme_se_rechaza_antes_de_llamar_a_tmdb(self):
        with patch("catalogo.views.CatalogoBaseView._service") as servicio:
            respuesta = APIClient().get(RUTA, {"page": 501})
        self.assertEqual(respuesta.status_code, 400)
        servicio.return_value.get_now_playing.assert_not_called()

    def test_la_pagina_500_sigue_permitida(self):
        with patch("catalogo.views.CatalogoBaseView._service") as servicio:
            servicio.return_value.get_now_playing.return_value = {"results": []}
            respuesta = APIClient().get(RUTA, {"page": 500})
        self.assertEqual(respuesta.status_code, 200)
