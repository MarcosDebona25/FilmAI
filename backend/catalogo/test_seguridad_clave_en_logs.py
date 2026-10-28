"""La clave de TMDB no debe quedar en ningún log ni mensaje de error.

TMDB v3 recibe la clave en la query (`?api_key=...`). httpx registra en INFO
cada URL que pide y, ante un fallo de red, su mensaje de error puede traer la
URL entera: la clave terminaba en los logs, que suelen viajar a herramientas de
terceros. Se cubren los dos caminos: el logger de httpx y la excepción propia.
"""

import logging
import traceback
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase

from catalogo.client import TMDBClient, _redactar_clave
from catalogo.exceptions import TMDBTransportError

CLAVE = "clave-secreta-de-tmdb-123"


class RegistroEnLista(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.mensajes = []

    def emit(self, registro):
        self.mensajes.append(registro.getMessage())


class ClaveDeTMDBEnLogsTests(SimpleTestCase):
    def cliente(self, handler):
        return TMDBClient(api_key=CLAVE, transport=httpx.MockTransport(handler))

    def raiz_en_info(self):
        """Como un worker de Celery con `-l info`, que sube el logger raíz a INFO."""
        raiz = logging.getLogger()
        nivel = raiz.level
        raiz.setLevel(logging.INFO)
        self.addCleanup(raiz.setLevel, nivel)
        return raiz

    def test_httpx_y_httpcore_no_registran_en_info_ni_con_la_raiz_en_info(self):
        # Es la configuración de LOGGING de settings.py, no un nivel puesto aquí.
        self.raiz_en_info()
        for nombre in ("httpx", "httpcore"):
            with self.subTest(logger=nombre):
                self.assertFalse(logging.getLogger(nombre).isEnabledFor(logging.INFO))

    def test_un_pedido_exitoso_no_deja_la_clave_en_ningun_log(self):
        registro = RegistroEnLista()
        raiz = self.raiz_en_info()
        raiz.addHandler(registro)
        self.addCleanup(raiz.removeHandler, registro)

        self.cliente(lambda request: httpx.Response(200, json={})).get_trending()

        for mensaje in registro.mensajes:
            self.assertNotIn(CLAVE, mensaje)

    def test_el_error_de_transporte_no_lleva_la_clave_ni_en_el_mensaje_ni_en_la_causa(
        self,
    ):
        def handler(request):
            raise httpx.ConnectError(f"no se pudo abrir {request.url}", request=request)

        with patch("catalogo.client.time.sleep"):
            with self.assertRaises(TMDBTransportError) as contexto:
                self.cliente(handler).get_trending()

        error = contexto.exception
        self.assertNotIn(CLAVE, str(error))
        self.assertIn("api_key=***", str(error))
        # Lo que `logger.exception` imprimiría: el traceback con la cadena de causas.
        self.assertNotIn(CLAVE, "".join(traceback.format_exception(error)))

    def test_el_error_de_transporte_registrado_con_logger_exception_no_filtra_la_clave(
        self,
    ):
        def handler(request):
            raise httpx.ReadTimeout(f"timeout en {request.url}", request=request)

        propio = logging.getLogger("catalogo.test_clave")
        with patch("catalogo.client.time.sleep"):
            with self.assertLogs(propio, level="ERROR") as capturado:
                try:
                    self.cliente(handler).get_trending()
                except TMDBTransportError:
                    propio.exception("falló TMDB")

        salida = "\n".join(
            [registro.getMessage() for registro in capturado.records] + capturado.output
        )
        self.assertNotIn(CLAVE, salida)


class RedactarClaveTests(SimpleTestCase):
    def test_tapa_api_key_en_cualquier_posicion_de_la_query(self):
        casos = (
            "GET https://api.themoviedb.org/3/x?api_key=abc123&page=1",
            "GET https://api.themoviedb.org/3/x?page=1&api_key=abc123",
            'GET "https://api.themoviedb.org/3/x?API_KEY=abc123"',
        )
        for texto in casos:
            with self.subTest(texto=texto):
                self.assertNotIn("abc123", _redactar_clave(texto))
                self.assertIn("***", _redactar_clave(texto))

    def test_conserva_el_resto_del_texto(self):
        self.assertEqual(
            _redactar_clave("fallo en x?api_key=abc&page=1"),
            "fallo en x?api_key=***&page=1",
        )

    def test_tapa_la_clave_suelta_si_se_la_pasa(self):
        self.assertEqual(_redactar_clave("usó abc123 mal", "abc123"), "usó *** mal")

    def test_un_texto_sin_clave_queda_igual(self):
        self.assertEqual(_redactar_clave("offline"), "offline")
