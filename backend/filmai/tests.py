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
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import MethodNotAllowed, Throttled

from catalogo.exceptions import TMDBNotFound
from filmai.email_backends import ResendBackend
from filmai.email_validation import validar_configuracion_email
from filmai.exceptions import filmai_exception_handler
from filmai.views import custom_404, custom_500
from usuarios.factories import UsuarioFactory


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
        self.assertEqual(response.data["code"], "upstream_not_found")
        self.assertEqual(response.data["code"], "upstream_not_found")

    def test_404_de_django_devuelve_json_en_espanol(self):
        response = filmai_exception_handler(Http404(), {})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "not_found")

    def test_method_not_allowed_acepta_detail_como_lista(self):
        exception = MethodNotAllowed("GET")
        exception.detail = ["GET"]

        response = filmai_exception_handler(exception, {})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data["code"], "method_not_allowed")

    def test_throttled_devuelve_429_con_mensaje_consistente(self):
        response = filmai_exception_handler(Throttled(wait=10), {})

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["code"], "throttled")
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


class DocumentacionApiTests(TestCase):
    """Swagger y el esquema usan la sesión y el rol del Django Admin."""

    def test_anonimo_y_usuario_comun_no_pueden_leer_documentacion(self):
        for nombre in ("schema", "swagger-ui"):
            with self.subTest(ruta=nombre, usuario="anónimo"):
                self.assertEqual(
                    self.client.get(reverse(nombre)).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

        self.client.force_login(UsuarioFactory())
        for nombre in ("schema", "swagger-ui"):
            with self.subTest(ruta=nombre, usuario="común"):
                self.assertEqual(
                    self.client.get(reverse(nombre)).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_navegador_anonimo_recibe_formulario_de_ingreso(self):
        for nombre, ruta in (("schema", "/api/schema/"), ("swagger-ui", "/api/docs/")):
            with self.subTest(ruta=nombre):
                respuesta = self.client.get(reverse(nombre), HTTP_ACCEPT="text/html")
                self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
                self.assertTrue(respuesta["Content-Type"].startswith("text/html"))
                self.assertContains(respuesta, "Admin access", status_code=403)
                self.assertContains(
                    respuesta, 'action="/api/docs/login/"', status_code=403
                )
                self.assertContains(
                    respuesta, f'name="next" value="{ruta}"', status_code=403
                )
                self.assertContains(respuesta, "csrfmiddlewaretoken", status_code=403)
                self.assertNotContains(respuesta, 'role="alert"', status_code=403)
                self.assertEqual(respuesta["Cache-Control"], "private, no-store")

    def test_navegador_con_sesion_comun_recibe_estado_sin_permisos(self):
        self.client.force_login(UsuarioFactory(nombre_usuario="juanperez"))
        for nombre in ("schema", "swagger-ui"):
            with self.subTest(ruta=nombre):
                respuesta = self.client.get(reverse(nombre), HTTP_ACCEPT="text/html")
                self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
                self.assertContains(
                    respuesta, "Your account has no access", status_code=403
                )
                self.assertContains(respuesta, "juanperez", status_code=403)
                self.assertContains(respuesta, "?cuenta=otra", status_code=403)
                self.assertNotContains(
                    respuesta, "csrfmiddlewaretoken", status_code=403
                )

    def test_cambiar_de_cuenta_vuelve_al_formulario(self):
        self.client.force_login(UsuarioFactory())
        respuesta = self.client.get(
            reverse("swagger-ui"), {"cuenta": "otra"}, HTTP_ACCEPT="text/html"
        )
        self.assertContains(respuesta, "Admin access", status_code=403)
        self.assertContains(respuesta, 'action="/api/docs/login/"', status_code=403)

    def test_idioma_sale_de_accept_language_y_cae_en_ingles(self):
        for encabezado, texto in (
            ("es-AR,es;q=0.9", "Acceso de administración"),
            ("fr-FR", "Admin access"),
        ):
            with self.subTest(encabezado=encabezado):
                respuesta = self.client.get(
                    reverse("swagger-ui"),
                    HTTP_ACCEPT="text/html",
                    HTTP_ACCEPT_LANGUAGE=encabezado,
                )
                self.assertContains(respuesta, texto, status_code=403)

    def test_sin_permisos_usa_el_idioma_de_la_cuenta(self):
        self.client.force_login(UsuarioFactory(idioma="es"))
        respuesta = self.client.get(reverse("swagger-ui"), HTTP_ACCEPT="text/html")
        self.assertContains(respuesta, "Tu cuenta no tiene acceso", status_code=403)

    def test_textos_en_y_es_tienen_las_mismas_claves(self):
        from filmai.documentation import TEXTOS

        self.assertEqual(set(TEXTOS["en"]), set(TEXTOS["es"]))
        self.assertEqual(set(TEXTOS["en"]["resource"]), set(TEXTOS["es"]["resource"]))
        for idioma, textos in TEXTOS.items():
            with self.subTest(idioma=idioma):
                self.assertTrue(all(textos[k] for k in textos))

    def test_cliente_json_recibe_403_explicativo(self):
        respuesta = self.client.get(reverse("schema"), HTTP_ACCEPT="application/json")
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(respuesta.json()["code"], "documentation_staff_required")
        self.assertEqual(respuesta.json()["code"], "documentation_staff_required")

    def test_staff_puede_leer_documentacion_con_cookie_jwt_invalida(self):
        # El navegador conserva la sesión del Admin aunque el JWT de la API
        # haya vencido. Estas vistas autentican solo con SessionAuthentication.
        self.client.force_login(UsuarioFactory(is_staff=True))
        self.client.cookies["access"] = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid"
        for nombre in ("schema", "swagger-ui"):
            with self.subTest(ruta=nombre):
                self.assertEqual(
                    self.client.get(
                        reverse(nombre),
                        HTTP_ACCEPT="text/html,application/xhtml+xml,*/*",
                    ).status_code,
                    status.HTTP_200_OK,
                )


class IngresoDocumentacionTests(TestCase):
    """Formulario propio para abrir la sesión que exige la documentación."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.addCleanup(cache.clear)
        self.url = reverse("docs-login")
        self.staff = UsuarioFactory(
            nombre_usuario="adminfilm", correo="admin@example.com", is_staff=True
        )
        self.staff.set_password("Palomitas24!")
        self.staff.save()
        self.comun = UsuarioFactory(nombre_usuario="juanperez")
        self.comun.set_password("Palomitas24!")
        self.comun.save()

    def _publicar(self, usuario, clave="Palomitas24!", destino="/api/docs/", **extra):
        return self.client.post(
            self.url,
            {"usuario": usuario, "clave": clave, "next": destino},
            HTTP_ACCEPT="text/html",
            **extra,
        )

    def test_staff_ingresa_con_usuario_o_correo_y_vuelve_a_la_ruta(self):
        for identificador in ("adminfilm", "ADMINFILM", "admin@example.com"):
            with self.subTest(identificador=identificador):
                self.client.logout()
                respuesta = self._publicar(identificador, destino="/api/schema/")
                self.assertRedirects(
                    respuesta, "/api/schema/", fetch_redirect_response=False
                )
                self.assertEqual(
                    self.client.get(
                        reverse("schema"), HTTP_ACCEPT="application/json"
                    ).status_code,
                    status.HTTP_200_OK,
                )

    def test_credenciales_incorrectas_y_cuenta_comun_reciben_el_mismo_aviso(self):
        casos = (
            ("adminfilm", "incorrecta"),
            ("inexistente", "Palomitas24!"),
            ("juanperez", "Palomitas24!"),
        )
        for usuario, clave in casos:
            with self.subTest(usuario=usuario):
                respuesta = self._publicar(usuario, clave)
                self.assertContains(
                    respuesta, "Incorrect admin credentials.", status_code=403
                )
                self.assertContains(respuesta, 'aria-invalid="true"', status_code=403)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_cuenta_dada_de_baja_no_ingresa(self):
        from usuarios.models import EstadoCuenta

        self.staff.estado = EstadoCuenta.BAJA
        self.staff.save()
        respuesta = self._publicar("adminfilm")
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_destino_externo_o_desconocido_vuelve_a_swagger(self):
        for destino in ("https://evil.example/", "//evil.example", "/admin/", ""):
            with self.subTest(destino=destino):
                self.client.logout()
                respuesta = self._publicar("adminfilm", destino=destino)
                self.assertRedirects(
                    respuesta, "/api/docs/", fetch_redirect_response=False
                )

    def test_exige_token_csrf(self):
        from django.test import Client

        cliente = Client(enforce_csrf_checks=True)
        respuesta = cliente.post(
            self.url, {"usuario": "adminfilm", "clave": "Palomitas24!"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn("_auth_user_id", cliente.session)

    def test_solo_acepta_post(self):
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_bloquea_tras_demasiados_intentos_fallidos(self):
        from filmai.documentation import INTENTOS_MAXIMOS

        for _ in range(INTENTOS_MAXIMOS):
            self._publicar("adminfilm", "incorrecta")
        respuesta = self._publicar("adminfilm")
        self.assertEqual(respuesta.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertContains(respuesta, "Too many attempts", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_ingreso_correcto_reinicia_el_contador(self):
        for _ in range(3):
            self._publicar("adminfilm", "incorrecta")
        self._publicar("adminfilm")
        self.client.logout()
        from django.core.cache import cache

        self.assertEqual(cache.get("docs-login:127.0.0.1", 0), 0)

    def test_mensajes_en_espanol_segun_el_navegador(self):
        respuesta = self._publicar(
            "adminfilm", "incorrecta", HTTP_ACCEPT_LANGUAGE="es-AR"
        )
        self.assertContains(
            respuesta, "Credenciales de administración incorrectas.", status_code=403
        )


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
