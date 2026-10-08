"""Servicio extraído: las cuatro variantes conservan su formato anterior."""

from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase, override_settings

from filmai.correos.servicio import CASOS, enviar_correo


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ServicioCorreosTests(SimpleTestCase):
    def setUp(self):
        mail.outbox.clear()
        self.contexto = {
            "user": SimpleNamespace(nombre="Correo", apellido="Servicio"),
            "activate_url": "https://filmai.test/confirmar-correo/key/",
            "reset_url": "https://filmai.test/restablecer-contrasena/uid/token/",
        }

    def test_cuatro_casos_se_envian_con_formatos_previos(self):
        """La extracción conserva tres multipart y una notificación solo texto."""
        for caso in sorted(CASOS):
            with self.subTest(caso=caso):
                self.assertEqual(
                    enviar_correo(caso, "correo@example.com", self.contexto, "es"), 1
                )
                correo = mail.outbox[-1]
                self.assertEqual(correo.to, ["correo@example.com"])
                self.assertTrue(correo.subject.startswith("[FilmAI]"))
                self.assertNotIn("\n", correo.subject)
                self.assertTrue(correo.body)
                if caso == "contrasena_actualizada":
                    self.assertEqual(correo.alternatives, [])
                else:
                    self.assertEqual(len(correo.alternatives), 1)
                    html, tipo = correo.alternatives[0]
                    self.assertEqual(tipo, "text/html")
                    self.assertIn('lang="es"', html)
                    self.assertIn("Correo Servicio", html)

    def test_caso_o_idioma_desconocido_no_envia(self):
        """Entradas internas inválidas se rechazan antes de usar el transporte."""
        with patch("filmai.correos.servicio.send_mail") as envio:
            for caso, idioma in (("otro", "es"), ("confirmacion_correo", "../")):
                with (
                    self.subTest(caso=caso, idioma=idioma),
                    self.assertRaises(ValueError),
                ):
                    enviar_correo(caso, "correo@example.com", self.contexto, idioma)
            envio.assert_not_called()

    def test_error_de_transporte_se_propaga_al_flujo_que_decide(self):
        """El caller conserva su política: registro falla o cambio confirmado registra."""
        with patch(
            "filmai.correos.servicio.send_mail",
            side_effect=RuntimeError("correo no disponible"),
        ):
            with self.assertRaisesRegex(RuntimeError, "correo no disponible"):
                enviar_correo("contrasena_actualizada", "correo@example.com", {}, "es")
