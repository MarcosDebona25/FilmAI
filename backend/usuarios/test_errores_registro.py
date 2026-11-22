"""Ejercita el registro real, incluidas sus dos etapas de validación."""

from datetime import date, timedelta
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.core.cache import cache
from django.core.exceptions import ValidationError as ErrorDjango
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from filmai.email_backends import ErrorDeProveedor, ProveedorBrevo, ProveedorResend

from .adapter import UsuarioAccountAdapter
from .avatares import AVATAR_ID_DEFAULT, AVATAR_IDS_VALIDOS
from .factories import UsuarioFactory
from .models import Usuario


@override_settings(
    DEBUG=False, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
class ErroresRegistroTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()
        self.payload = {
            "correo": "nueva@example.com",
            "nombre_usuario": "nueva123",
            "nombre": "María",
            "apellido": "Pérez",
            "fecha_nacimiento": "1990-01-01",
            "genero": "no_especifica",
            "pais": "AR",
            "acepta_terminos": True,
            "password1": "NuevaClave456!",
            "password2": "NuevaClave456!",
        }

    def registrar(self, cambios):
        cache.clear()
        return self.client.post(
            "/api/auth/registration/", {**self.payload, **cambios}, format="json"
        )

    def test_registro_exige_aceptar_los_terminos(self):
        """Sin el campo es `required`; en `false` es `terms_not_accepted`."""
        sin_campo = {k: v for k, v in self.payload.items() if k != "acepta_terminos"}
        cache.clear()
        response = self.client.post("/api/auth/registration/", sin_campo, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"],
            [{"field": "acepta_terminos", "code": "required", "params": {}}],
        )
        response = self.registrar({"acepta_terminos": False})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"],
            [{"field": "acepta_terminos", "code": "terms_not_accepted", "params": {}}],
        )
        self.assertFalse(Usuario.objects.filter(correo=self.payload["correo"]).exists())

    def test_registro_guarda_la_fecha_de_aceptacion(self):
        antes = timezone.now()
        response = self.registrar({})
        self.assertEqual(response.status_code, 201)
        usuario = Usuario.objects.get(correo=self.payload["correo"])
        self.assertIsNotNone(usuario.fecha_aceptacion_terminos)
        self.assertGreaterEqual(usuario.fecha_aceptacion_terminos, antes)

    def test_registro_guarda_el_avatar_elegido(self):
        """El avatar que viaja en el alta queda en el usuario creado."""
        response = self.registrar({"avatar_id": 7})
        self.assertEqual(response.status_code, 201)
        usuario = Usuario.objects.get(correo=self.payload["correo"])
        self.assertEqual(usuario.avatar_id, 7)

    def test_registro_sin_avatar_asigna_el_de_siempre(self):
        """El campo es opcional: sin él se mantiene el avatar por defecto."""
        response = self.registrar({})
        self.assertEqual(response.status_code, 201)
        usuario = Usuario.objects.get(correo=self.payload["correo"])
        self.assertEqual(usuario.avatar_id, AVATAR_ID_DEFAULT)

    def test_registro_rechaza_un_avatar_fuera_del_catalogo(self):
        """Mismo código y parámetros que el perfil, y no se crea la cuenta."""
        for invalido in (999, 0, -1):
            with self.subTest(avatar_id=invalido):
                response = self.registrar({"avatar_id": invalido})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["errors"],
                    [
                        {
                            "field": "avatar_id",
                            "code": "avatar_invalid",
                            "params": {"allowedIds": sorted(AVATAR_IDS_VALIDOS)},
                        }
                    ],
                )
        self.assertFalse(Usuario.objects.filter(correo=self.payload["correo"]).exists())

    def test_duplicados_mantienen_campos_y_http_de_registro(self):
        """A diferencia del perfil, el duplicado detectado en registro sigue siendo 400."""
        usuario = UsuarioFactory()
        for campo, valor, codigo, _mensaje in (
            (
                "correo",
                usuario.correo,
                "email_already_used",
                "El correo ya está registrado.",
            ),
            (
                "nombre_usuario",
                usuario.nombre_usuario,
                "username_already_used",
                "El nombre de usuario ya está registrado.",
            ),
        ):
            with self.subTest(campo=campo):
                response = self.registrar({campo: valor})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["code"], "validation_error")
                self.assertEqual(
                    response.data["errors"],
                    [{"field": campo, "code": codigo, "params": {}}],
                )

    def test_reglas_personales_conservan_codigo_y_limites_en_la_frontera_real(self):
        """Cada regla mantiene su identidad y la configuración que se aplicó."""
        for campo, valor, codigo, parametros in (
            (
                "nombre_usuario",
                "abc",
                "username_invalid",
                {"minLength": 5, "maxLength": 25},
            ),
            ("apellido", "Perez123", "person_name_invalid", {"maxLength": 50}),
            (
                "fecha_nacimiento",
                (date.today() + timedelta(days=1)).isoformat(),
                "birth_date_in_future",
                {},
            ),
            (
                "fecha_nacimiento",
                date.today().isoformat(),
                "minimum_age",
                {"minAge": 13},
            ),
        ):
            with self.subTest(codigo=codigo):
                response = self.registrar({campo: valor})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["errors"],
                    [{"field": campo, "code": codigo, "params": parametros}],
                )
                self.assertIn(
                    campo, {entry["field"] for entry in response.data["errors"]}
                )

    def test_mismatch_heredado_conserva_traduccion_y_non_field_errors(self):
        """El código se asigna por la condición, sin interpretar texto traducido."""
        response = self.registrar({"password2": "OtraClave456!"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [{"field": None, "code": "passwords_do_not_match", "params": {}}],
        )

    def test_password_django_no_pierde_codigo_ni_caracteres_especiales(self):
        """La validación heredada de password1 conserva metadata de la regla propia."""
        response = self.registrar(
            {"password1": "ZxCvbnm987", "password2": "ZxCvbnm987"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"],
            [
                {
                    "field": "password1",
                    "code": "password_no_special",
                    "params": {"specialCharacters": "@#$%&*!"},
                }
            ],
        )

    def test_segunda_validacion_durante_save_conserva_metadata_y_no_persiste(self):
        """Un fallo que depende del usuario ocurre en save, después de is_valid."""
        original = UsuarioAccountAdapter.clean_password

        def validar(adapter, password, user=None):
            if user is not None:
                raise ErrorDjango(
                    "Rechazo posterior de contraseña.", code="password_no_special"
                )
            return original(adapter, password, user=user)

        with patch.object(UsuarioAccountAdapter, "clean_password", validar):
            response = self.registrar({})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [
                {
                    "field": None,
                    "code": "password_no_special",
                    "params": {"specialCharacters": "@#$%&*!"},
                }
            ],
        )
        self.assertFalse(Usuario.objects.filter(correo=self.payload["correo"]).exists())


@override_settings(
    DEBUG=False,
    EMAIL_BACKEND="filmai.email_backends.RespaldoBackend",
    RESEND_API_KEY="re_de_prueba",
    BREVO_API_KEY="xkeysib-de-prueba",
    RESEND_TEST_RECIPIENT="",
    BREVO_TEST_RECIPIENT="",
)
class CorreoNoDisponibleTests(TestCase):
    """Con Resend y Brevo caídos (D-4 de brevo-respaldo): `email_unavailable`.

    Se usa el `RespaldoBackend` de verdad y se simula la caída en el borde, en
    `enviar` de cada proveedor, así que el 503 (Service Unavailable) sale de la
    cadena completa: proveedor, backend, `enviar_correo`, adaptador y vista.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()
        self.payload = {
            "correo": "nueva@example.com",
            "nombre_usuario": "nueva123",
            "nombre": "María",
            "apellido": "Pérez",
            "fecha_nacimiento": "1990-01-01",
            "genero": "no_especifica",
            "pais": "AR",
            "acepta_terminos": True,
            "password1": "NuevaClave456!",
            "password2": "NuevaClave456!",
        }

    @staticmethod
    def _caida(proveedor, estado):
        def enviar(self, message):
            raise ErrorDeProveedor(proveedor, transitorio=True, estado=estado)

        return enviar

    def ambos_caidos(self):
        """Resend 503 (Service Unavailable) y Brevo 402 (Payment Required)."""
        return (
            patch.object(ProveedorResend, "enviar", self._caida("Resend", 503)),
            patch.object(ProveedorBrevo, "enviar", self._caida("Brevo", 402)),
        )

    def registrar(self):
        return self.client.post("/api/auth/registration/", self.payload, format="json")

    def test_registro_sin_proveedor_responde_503_y_no_deja_cuenta(self):
        """`transaction.atomic()` deshace el INSERT del usuario y del EmailAddress."""
        resend, brevo = self.ambos_caidos()
        with resend, brevo, self.assertLogs("filmai.email_backends", "ERROR"):
            response = self.registrar()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "email_unavailable")
        self.assertFalse(Usuario.objects.filter(correo="nueva@example.com").exists())
        self.assertFalse(
            EmailAddress.objects.filter(email="nueva@example.com").exists()
        )

    def test_la_respuesta_503_no_lleva_texto_del_proveedor_ni_direcciones(self):
        resend, brevo = self.ambos_caidos()
        with resend, brevo, self.assertLogs("filmai.email_backends", "ERROR"):
            response = self.registrar()
        self.assertNotIn(b"nueva@example.com", response.content)
        self.assertNotIn(b"Resend", response.content)
        self.assertNotIn(b"Brevo", response.content)

    def test_reintento_con_los_proveedores_recuperados_crea_la_cuenta(self):
        resend, brevo = self.ambos_caidos()
        with resend, brevo, self.assertLogs("filmai.email_backends", "ERROR"):
            self.assertEqual(self.registrar().status_code, 503)
        cache.clear()
        with patch.object(ProveedorResend, "enviar", return_value="id-1"):
            response = self.registrar()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Usuario.objects.filter(correo="nueva@example.com").exists())

    def test_datos_invalidos_del_mensaje_no_se_informan_como_correo_no_disponible(self):
        """Un 422 (Unprocessable Entity) no es `EnvioFallido`: sigue siendo un error."""

        def invalido(self, message):
            raise ErrorDeProveedor("Resend", transitorio=False, estado=422)

        with (
            patch.object(ProveedorResend, "enviar", invalido),
            patch.object(ProveedorBrevo, "enviar") as brevo,
            self.assertLogs("filmai.email_backends", "ERROR"),
        ):
            response = self.registrar()
        brevo.assert_not_called()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["code"], "server_error")
        self.assertFalse(Usuario.objects.filter(correo="nueva@example.com").exists())

    def test_reenvio_sin_proveedor_responde_503(self):
        with patch.object(ProveedorResend, "enviar", return_value="id-1"):
            self.assertEqual(self.registrar().status_code, 201)
        cache.clear()
        resend, brevo = self.ambos_caidos()
        with resend, brevo, self.assertLogs("filmai.email_backends", "ERROR"):
            response = self.client.post(
                "/api/auth/registration/resend-email/",
                {"email": "nueva@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "email_unavailable")

    def test_reset_sigue_respondiendo_el_200_generico(self):
        """No revela nada: la respuesta es idéntica exista o no la cuenta."""
        usuario = UsuarioFactory()
        resend, brevo = self.ambos_caidos()
        with resend, brevo, self.assertLogs("filmai.email_backends", "ERROR"):
            con_cuenta = self.client.post(
                "/api/auth/password/reset/", {"email": usuario.correo}, format="json"
            )
        cache.clear()
        sin_cuenta = self.client.post(
            "/api/auth/password/reset/", {"email": "nadie@example.com"}, format="json"
        )
        self.assertEqual(con_cuenta.status_code, 200)
        self.assertEqual(sin_cuenta.status_code, 200)
        # Mismo cuerpo salvo el contador de intentos, que es por correo.
        cuerpos = [r.json() for r in (con_cuenta, sin_cuenta)]
        for cuerpo in cuerpos:
            cuerpo.pop("intentos_restantes", None)
        self.assertEqual(cuerpos[0], cuerpos[1])

    def test_cambio_de_contrasena_se_confirma_aunque_el_aviso_no_salga(self):
        usuario = UsuarioFactory()
        # La vista lee el JWT del pedido (`request.auth`): hace falta uno real.
        self.client.force_authenticate(
            usuario, token=RefreshToken.for_user(usuario).access_token
        )
        resend, brevo = self.ambos_caidos()
        with (
            resend,
            brevo,
            self.assertLogs("filmai.email_backends", "ERROR"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                "/api/auth/password/change/",
                {
                    "old_password": "Password123!",
                    "password1": "OtraClave789!",
                    "password2": "OtraClave789!",
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password("OtraClave789!"))
