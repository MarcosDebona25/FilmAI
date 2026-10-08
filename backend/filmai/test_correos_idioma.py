"""OT-52: cada correo existe completo en ambos idiomas y sigue al destinatario."""

import re
from types import SimpleNamespace

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from filmai.correos.servicio import CASOS, enviar_correo
from usuarios.factories import UsuarioFactory

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
# Palabras que solo pueden aparecer en uno de los dos idiomas.
PROPIAS = {
    "es": ("Hola", "El equipo de FilmAI"),
    "en": ("Hi ", "The FilmAI team"),
}
# El texto plano español de esta notificación conserva la copia anterior (sin
# saludo ni enlace) hasta que OT-53 la reemplace por la de la tabla.
PENDIENTE_OT53 = ("contrasena_actualizada", "es")


@override_settings(EMAIL_BACKEND=LOCMEM, FRONTEND_URL="https://filmai.test")
class MatrizDeCorreosTests(SimpleTestCase):
    def _enviar(self, caso, idioma, usuario=None):
        mail.outbox.clear()
        contexto = {
            "user": usuario or SimpleNamespace(nombre="Ana", apellido="Pérez"),
            "activate_url": "https://filmai.test/confirmar-correo/key/",
            "reset_url": "https://filmai.test/restablecer-contrasena/uid/token/",
        }
        enviar_correo(caso, "destino@example.com", contexto, idioma)
        correo = mail.outbox[-1]
        return correo.subject, correo.body, correo.alternatives[0][0]

    def test_cada_caso_tiene_asunto_texto_y_html_en_cada_idioma(self):
        for caso in sorted(CASOS):
            for idioma in settings.IDIOMAS_SOPORTADOS:
                otro = "en" if idioma == "es" else "es"
                with self.subTest(caso=caso, idioma=idioma):
                    asunto, texto, html = self._enviar(caso, idioma)
                    self.assertTrue(asunto.startswith("[FilmAI] "))
                    self.assertNotIn("\n", asunto)
                    self.assertIn(f'<html lang="{idioma}">', html)
                    partes = (texto, html)
                    if (caso, idioma) == PENDIENTE_OT53:
                        partes = (html,)
                    for parte in partes:
                        self.assertIn("Ana Pérez", parte)
                        self.assertIn("https://filmai.test/", parte)
                        self.assertIsNone(re.search(r"\{[{%#]|\{\w+[,}]", parte))
                        for palabra in PROPIAS[idioma]:
                            self.assertIn(palabra, parte)
                        for palabra in PROPIAS[otro]:
                            self.assertNotIn(palabra, parte)

    def test_asuntos_aprobados_en_ingles(self):
        esperado = {
            "confirmacion_registro": "[FilmAI] Confirm your account",
            "confirmacion_correo": "[FilmAI] Confirm your account",
            "restablecer_contrasena": "[FilmAI] Reset your password",
            "contrasena_actualizada": "[FilmAI] Your password was updated",
        }
        for caso, asunto in esperado.items():
            with self.subTest(caso=caso):
                self.assertEqual(self._enviar(caso, "en")[0], asunto)

    def test_saludo_de_reserva_no_mezcla_idiomas(self):
        sin_nombre = SimpleNamespace(nombre="", apellido=None)
        for caso in sorted(CASOS):
            _, texto_es, html_es = self._enviar(caso, "es", sin_nombre)
            _, texto_en, html_en = self._enviar(caso, "en", sin_nombre)
            with self.subTest(caso=caso):
                partes_es = (texto_es, html_es)
                if (caso, "es") == PENDIENTE_OT53:
                    partes_es = (html_es,)
                for parte in partes_es:
                    self.assertIn("Hola usuario,", parte)
                for parte in (texto_en, html_en):
                    self.assertIn("Hi there,", parte)
                    self.assertNotIn("usuario", parte)

    def test_vigencia_en_ingles_usa_singular_y_plural(self):
        self.assertIn(
            "valid for 1 hour.", self._enviar("restablecer_contrasena", "en")[1]
        )
        self.assertIn(
            "valid for 24 hours.", self._enviar("confirmacion_registro", "en")[1]
        )


@override_settings(EMAIL_BACKEND=LOCMEM)
class IdiomaDelDestinatarioTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        mail.outbox.clear()

    def _recuperar(self, usuario, idioma_request):
        cliente = APIClient()
        extra = {"HTTP_ACCEPT_LANGUAGE": idioma_request} if idioma_request else {}
        cliente.post(
            "/api/auth/password/reset/",
            {"email": usuario.correo},
            format="json",
            **extra,
        )
        return mail.outbox[-1].subject

    def test_idioma_guardado_gana_al_del_request(self):
        en = UsuarioFactory(idioma="en")
        es = UsuarioFactory(idioma="es")
        self.assertEqual(self._recuperar(en, "es"), "[FilmAI] Reset your password")
        self.assertEqual(
            self._recuperar(es, "en"), "[FilmAI] Restablecimiento de contraseña"
        )

    def test_sin_idioma_guardado_usa_el_request_y_luego_ingles(self):
        usuario = UsuarioFactory(idioma=None)
        self.assertEqual(
            self._recuperar(usuario, "es"), "[FilmAI] Restablecimiento de contraseña"
        )
        cache.clear()
        self.assertEqual(self._recuperar(usuario, None), "[FilmAI] Reset your password")

    def test_registro_en_ingles_envia_la_confirmacion_en_ingles(self):
        APIClient().post(
            "/api/auth/registration/",
            {
                "correo": "english@example.com",
                "nombre_usuario": "english01",
                "nombre": "Ann",
                "apellido": "Lee",
                "fecha_nacimiento": "1990-01-01",
                "genero": "no_especifica",
                "password1": "NuevaClave456!",
                "password2": "NuevaClave456!",
            },
            format="json",
            HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9",
        )
        correo = mail.outbox[-1]
        self.assertEqual(correo.subject, "[FilmAI] Confirm your account")
        self.assertIn("Hi Ann Lee,", correo.body)

    def test_cambio_de_contrasena_notifica_en_el_idioma_de_la_cuenta(self):
        from rest_framework_simplejwt.tokens import AccessToken

        usuario = UsuarioFactory(idioma="en")
        cliente = APIClient(HTTP_ACCEPT_LANGUAGE="es")
        cliente.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}"
        )
        with self.captureOnCommitCallbacks(execute=True):
            cliente.post(
                "/api/profile/change-password/",
                {
                    "old_password": "Password123!",
                    "password1": "NuevaPassword456!",
                    "password2": "NuevaPassword456!",
                },
                format="json",
            )
        self.assertEqual(mail.outbox[-1].subject, "[FilmAI] Your password was updated")
