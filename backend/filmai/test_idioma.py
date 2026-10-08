"""La resolución es por operación; no cambia el locale global de Django."""

from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase
from django.utils import translation

from filmai.idioma import idioma_efectivo


class IdiomaEfectivoTests(SimpleTestCase):
    def test_encabezados_con_pesos_regiones_y_respaldo(self):
        """Los navegadores regionales negocian solo idiomas soportados con peso positivo."""
        for encabezado, esperado in (
            (None, "en"),
            ("", "en"),
            ("es", "es"),
            ("ES-ar", "es"),
            ("en-US", "en"),
            ("fr;q=1, es-MX;q=0.8, en;q=0.5", "es"),
            ("es;q=0.2, en;q=0.9", "en"),
            ("es;q=0.8, en;q=0.8", "es"),
            ("es;q=0, en;q=0.5", "en"),
            ("es;q=0, fr;q=1", "en"),
            ("fr, de", "en"),
            ("*", "en"),
            ("*;q=1, es;q=0.5", "es"),
            ("es;q=2", "en"),
            ("es;q=incorrecto, en", "en"),
            ("es_AR", "en"),
            ("x" * 1000, "en"),
        ):
            with self.subTest(encabezado=encabezado):
                headers = (
                    {} if encabezado is None else {"HTTP_ACCEPT_LANGUAGE": encabezado}
                )
                request = RequestFactory().get("/", **headers)
                request.user = AnonymousUser()
                self.assertEqual(idioma_efectivo(request), esperado)

    def test_cuenta_guardada_y_usuario_explicito_tienen_prioridad(self):
        """La cuenta destinataria explícita puede diferir de quien hizo el request."""
        request = RequestFactory().get("/", HTTP_ACCEPT_LANGUAGE="en")
        for guardado, esperado in (
            ("es", "es"),
            ("en", "en"),
            (None, "en"),
            ("fr", "en"),
        ):
            with self.subTest(guardado=guardado):
                request.user = SimpleNamespace(idioma=guardado)
                self.assertEqual(idioma_efectivo(request), esperado)
        request.user = SimpleNamespace(idioma="en")
        self.assertEqual(idioma_efectivo(request, SimpleNamespace(idioma="es")), "es")
        self.assertEqual(idioma_efectivo(None), "en")

    def test_resolucion_no_modifica_el_idioma_global(self):
        """Resolver ES/EN no cambia los mensajes heredados que Django sigue emitiendo."""
        with translation.override("es-ar"):
            self.assertEqual(idioma_efectivo(None), "en")
            self.assertEqual(translation.get_language(), "es-ar")
