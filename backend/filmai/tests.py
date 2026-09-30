"""Tests del backend de email sobre Resend (filmai.email_backends).

Se instancia `ResendBackend` directamente y se mockea `resend.Emails.send`:
el test runner de Django fuerza locmem como EMAIL_BACKEND, así que estos
tests unitarios no dependen de la configuración global ni de la API real.
"""

from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.http import Http404
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import MethodNotAllowed, Throttled

from catalogo.exceptions import TMDBNotFound
from filmai.email_backends import ResendBackend
from filmai.email_validation import validar_configuracion_email
from filmai.exceptions import filmai_exception_handler
from filmai.views import custom_404, custom_500


@override_settings(RESEND_API_KEY="re_test", RESEND_TEST_RECIPIENT="")
class ResendBackendTests(SimpleTestCase):
    def _mensaje(self):
        return EmailMessage(
            "Asunto de prueba",
            "Cuerpo de prueba",
            "FilmAI <onboarding@resend.dev>",
            ["destinatario@example.com"],
        )

    @patch("resend.Emails.send")
    def test_envia_con_from_to_subject_text(self, mock_send):
        mock_send.return_value = {"id": "abc"}
        enviados = ResendBackend(fail_silently=False).send_messages([self._mensaje()])

        self.assertEqual(enviados, 1)
        params = mock_send.call_args[0][0]
        self.assertEqual(params["from"], "FilmAI <onboarding@resend.dev>")
        self.assertEqual(params["to"], ["destinatario@example.com"])
        self.assertEqual(params["subject"], "Asunto de prueba")
        self.assertEqual(params["text"], "Cuerpo de prueba")
        self.assertNotIn("html", params)

    @patch("resend.Emails.send")
    @override_settings(RESEND_TEST_RECIPIENT="dueno@example.com")
    def test_redirige_todos_los_destinatarios_a_test_recipient(self, mock_send):
        mensaje = EmailMessage(
            "Confirmación",
            "Cuerpo",
            "FilmAI <onboarding@resend.dev>",
            ["usuario999@test.com"],
            cc=["otro@test.com"],
        )
        ResendBackend(fail_silently=False).send_messages([mensaje])

        params = mock_send.call_args[0][0]
        # Sin dominio propio, TODO email sale hacia el dueño de la API key.
        self.assertEqual(params["to"], ["dueno@example.com"])

    @patch("resend.Emails.send")
    def test_extrae_alternativa_html(self, mock_send):
        mock_send.return_value = {"id": "abc"}
        mensaje = EmailMultiAlternatives(
            "Asunto de prueba",
            "Cuerpo de prueba",
            "FilmAI <onboarding@resend.dev>",
            ["destinatario@example.com"],
        )
        mensaje.attach_alternative("<p>Cuerpo</p>", "text/html")

        ResendBackend(fail_silently=False).send_messages([mensaje])

        params = mock_send.call_args[0][0]
        self.assertEqual(params["html"], "<p>Cuerpo</p>")
        self.assertEqual(params["text"], "Cuerpo de prueba")

    @override_settings(RESEND_API_KEY="")
    @patch("resend.Emails.send")
    def test_sin_api_key_no_llama_a_la_api(self, mock_send):
        enviados = ResendBackend(fail_silently=True).send_messages([self._mensaje()])

        self.assertEqual(enviados, 0)
        mock_send.assert_not_called()

    @patch("resend.Emails.send", side_effect=RuntimeError("API caída"))
    def test_error_propaga_cuando_no_es_fail_silent(self, _mock_send):
        with self.assertRaises(RuntimeError):
            ResendBackend(fail_silently=False).send_messages([self._mensaje()])

    @patch("resend.Emails.send")
    def test_separa_cc_y_bcc_en_campos_propios(self, mock_send):
        mock_send.return_value = {"id": "abc"}
        mensaje = EmailMessage(
            "Asunto",
            "Cuerpo",
            "FilmAI <onboarding@resend.dev>",
            ["principal@example.com"],
            cc=["copia@example.com"],
            bcc=["oculto@example.com"],
        )
        ResendBackend(fail_silently=False).send_messages([mensaje])

        params = mock_send.call_args[0][0]
        # Los CC no se fusionan en `to` y los BCC no quedan expuestos.
        self.assertEqual(params["to"], ["principal@example.com"])
        self.assertEqual(params["cc"], ["copia@example.com"])
        self.assertEqual(params["bcc"], ["oculto@example.com"])

    @patch("resend.Emails.send")
    def test_solo_cc_promueve_a_to(self, mock_send):
        mock_send.return_value = {"id": "abc"}
        mensaje = EmailMessage(
            "Asunto",
            "Cuerpo",
            "FilmAI <onboarding@resend.dev>",
            [],
            cc=["copia@example.com"],
        )
        ResendBackend(fail_silently=False).send_messages([mensaje])

        params = mock_send.call_args[0][0]
        # Resend exige un `to` no vacío: el CC se promueve para poder enviar.
        self.assertEqual(params["to"], ["copia@example.com"])
        self.assertNotIn("cc", params)


class ConfiguracionEmailTests(SimpleTestCase):
    def test_rechaza_test_recipient_en_produccion(self):
        with self.assertRaises(ImproperlyConfigured):
            validar_configuracion_email(
                debug=False,
                email_backend="filmai.email_backends.ResendBackend",
                resend_api_key="re_key",
                resend_test_recipient="dueno@example.com",
            )

    def test_rechaza_falta_de_api_key_en_produccion(self):
        with self.assertRaises(ImproperlyConfigured):
            validar_configuracion_email(
                debug=False,
                email_backend="filmai.email_backends.ResendBackend",
                resend_api_key="",
                resend_test_recipient="",
            )

    def test_permite_test_recipient_en_desarrollo(self):
        validar_configuracion_email(
            debug=True,
            email_backend="filmai.email_backends.ResendBackend",
            resend_api_key="re_key",
            resend_test_recipient="dueno@example.com",
        )

    def test_no_aplica_a_backend_no_resend(self):
        validar_configuracion_email(
            debug=False,
            email_backend="django.core.mail.backends.console.EmailBackend",
            resend_api_key="",
            resend_test_recipient="dueno@example.com",
        )


class ExceptionHandlerTests(SimpleTestCase):
    def test_handler_global_conserva_el_mapeo_de_tmdb(self):
        response = filmai_exception_handler(TMDBNotFound("No encontrada"), {})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"detail": "No encontrada"})

    def test_404_de_django_devuelve_json_en_espanol(self):
        response = filmai_exception_handler(Http404(), {})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "El recurso solicitado no existe.")

    def test_method_not_allowed_acepta_detail_como_lista(self):
        exception = MethodNotAllowed("GET")
        exception.detail = ["GET"]

        response = filmai_exception_handler(exception, {})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            response.data["detail"], "Método HTTP GET no permitido para este endpoint."
        )

    def test_throttled_devuelve_429_con_mensaje_consistente(self):
        response = filmai_exception_handler(Throttled(wait=10), {})

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(
            response.data["detail"],
            "Demasiadas solicitudes. Intentá de nuevo más tarde.",
        )
        self.assertEqual(response["Retry-After"], "10")

    def test_handlers_de_django_devuelven_json(self):
        self.assertEqual(custom_404(None).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            custom_500(None).status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def test_openapi_y_swagger_estan_configurados(self):
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"],
            "drf_spectacular.openapi.AutoSchema",
        )
        self.assertEqual(reverse("schema"), "/api/schema/")
        self.assertEqual(reverse("swagger-ui"), "/api/docs/")

    def test_schema_y_swagger_no_devuelven_401_con_cookie_jwt_invalida(self):
        # Las vistas de la documentación son públicas: una cookie `access`
        # vieja o corrupta en el navegador no debe convertirlas en 401.
        # Sin `authentication_classes=[]`, JWTCookieAuthentication rechaza el
        # token ANTES de evaluar permisos, aunque la vista no exija sesión.
        cookie = "access=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid"
        for url in (reverse("schema"), reverse("swagger-ui")):
            with self.subTest(url=url):
                respuesta = self.client.get(url, HTTP_COOKIE=cookie)
                self.assertEqual(respuesta.status_code, status.HTTP_200_OK)


class CeleryAppTests(SimpleTestCase):
    """Wiring de Celery con Django (C-04a).

    Se verifica configuración, no ejecución: no hace falta un worker ni un
    Redis real para saber que la app quedó bien conectada.
    """

    def test_app_es_una_instancia_celery_llamada_filmai(self):
        from celery import Celery

        from filmai.celery import app

        self.assertIsInstance(app, Celery)
        self.assertEqual(app.main, "filmai")

    def test_celery_app_se_expone_en_el_paquete(self):
        # Django debe cargar la app al importar `filmai`, para que las tareas
        # queden registradas con `shared_task`.
        import filmai
        from filmai.celery import app

        self.assertIs(filmai.celery_app, app)

    def test_broker_y_backend_usan_db_de_redis_distinta_del_cache(self):
        from filmai.celery import app

        # La DB 0 la usa el caché de TMDB (`REDIS_URL`): si la cola compartiera
        # esa DB, las claves de Celery se mezclarían con las `tmdb:*`.
        self.assertEqual(app.conf.broker_url, settings.CELERY_BROKER_URL)
        self.assertNotEqual(app.conf.broker_url, settings.REDIS_URL)
        self.assertNotEqual(settings.CELERY_RESULT_BACKEND, settings.REDIS_URL)

    def test_solo_acepta_serializacion_json(self):
        from filmai.celery import app

        self.assertEqual(app.conf.task_serializer, "json")
        self.assertEqual(list(app.conf.accept_content), ["json"])
