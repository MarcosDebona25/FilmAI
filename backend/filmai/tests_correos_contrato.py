"""Referencias del correo real anterior a la extracción del servicio i18n."""

import json
import os
import re
from pathlib import Path

from allauth.account.models import EmailAddress
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from usuarios.factories import UsuarioFactory
from usuarios.models import EstadoCuenta


@override_settings(
    DEBUG=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://frontend.filmai.test",
)
class CorreosContratoTests(TestCase):
    """Ejercita cada flujo de envío; no reconstruye las plantillas en el test."""

    idioma = "es"
    sufijo = ""

    def setUp(self):
        # Las referencias de F0 son la variante en español; `.en` las de inglés.
        self.client = APIClient(HTTP_ACCEPT_LANGUAGE=self.idioma)
        mail.outbox.clear()

    def assert_correo(self, caso):
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]

        def normalizar(texto):
            texto = re.sub(
                r"/confirm-email/[^/\s\"<]+/",
                "/confirm-email/<key>/",
                texto,
            )
            texto = re.sub(
                r"/reset-password/[^/\s\"<]+/[^/\s\"<]+/",
                "/reset-password/<uid>/<token>/",
                texto,
            )
            # El año del pie cambia solo; no es parte de la copia.
            return re.sub(r"© \d{4}", "© <year>", texto)

        observado = {
            "asunto": correo.subject,
            "texto": normalizar(correo.body),
            "html": [
                normalizar(contenido)
                for contenido, tipo in getattr(correo, "alternatives", [])
                if tipo == "text/html"
            ],
        }
        archivo = (
            Path(__file__).parent
            / "tests_golden"
            / "correos"
            / f"{caso}{self.sufijo}.json"
        )
        if os.environ.get("FILMAI_ACTUALIZAR_REFERENCIAS") == "1":
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_text(
                json.dumps(observado, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        self.assertTrue(archivo.exists(), f"Falta referencia: {archivo}")
        self.assertEqual(observado, json.loads(archivo.read_text(encoding="utf-8")))
        return observado

    def crear_usuario(self, **extra):
        return UsuarioFactory(
            correo="correos@filmai.test",
            nombre_usuario="correos01",
            nombre="Correo",
            apellido="Referencia",
            **extra,
        )

    def test_confirmacion_registro(self):
        """Registro envía saludo, vigencia y enlace en texto y HTML."""
        respuesta = self.client.post(
            "/api/auth/registration/",
            {
                "correo": "correos@filmai.test",
                "nombre_usuario": "correos01",
                "nombre": "Correo",
                "apellido": "Referencia",
                "fecha_nacimiento": "1990-01-01",
                "genero": "no_especifica",
                "acepta_terminos": True,
                "password1": "Password123!",
                "password2": "Password123!",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(len(self.assert_correo("confirmacion_registro")["html"]), 1)

    def test_reenvio_confirmacion(self):
        """Reenvío usa su plantilla completa y conserva el mismo asunto."""
        usuario = self.crear_usuario(estado=EstadoCuenta.PENDIENTE)
        EmailAddress.objects.create(
            user=usuario, email=usuario.correo, primary=True, verified=False
        )
        respuesta = self.client.post(
            "/api/auth/registration/resend-email/",
            {"email": usuario.correo},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(self.assert_correo("reenvio_confirmacion")["html"]), 1)

    def test_restablecimiento(self):
        """Recuperación produce las dos variantes con enlace normalizado."""
        usuario = self.crear_usuario()
        respuesta = self.client.post(
            "/api/auth/password/reset/", {"email": usuario.correo}, format="json"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(self.assert_correo("restablecimiento")["html"]), 1)

    def test_contrasena_actualizada(self):
        """Cambio ejecuta el envío posterior al commit, hoy solo de texto."""
        usuario = self.crear_usuario()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}"
        )
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(
                "/api/profile/change-password/",
                {
                    "old_password": "Password123!",
                    "password1": "NuevaPassword456!",
                    "password2": "NuevaPassword456!",
                },
                format="json",
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(self.assert_correo("contrasena_actualizada")["html"]), 1)


class CorreosContratoInglesTests(CorreosContratoTests):
    """Las mismas cuatro rutas reales, con el request en inglés (OT-52)."""

    idioma = "en"
    sufijo = ".en"
