"""Pruebas HTTP de perfil y contraseñas, sin omitir la autenticación JWT."""

import re
from datetime import datetime, timedelta
from unittest.mock import patch

from allauth.account.forms import default_token_generator
from allauth.account.utils import user_pk_to_url_str
from allauth.socialaccount.models import SocialAccount
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import UsuarioFactory
from .models import EstadoCuenta, Usuario
from .serializers import EnlaceRestablecimientoInvalido, RestablecerContrasenaSerializer


class PerfilTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = UsuarioFactory(nombre="María", apellido="Pérez")
        self.refresh = RefreshToken.for_user(self.usuario)
        self.client.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {self.refresh.access_token}"
        )

    def test_get_requiere_sesion_y_devuelve_solo_perfil_propio(self):
        """401 anónimo y representación propia sin credenciales ni permisos."""
        self.assertEqual(Client().get("/api/profile/").status_code, 401)
        otro = UsuarioFactory()
        response = self.client.get("/api/profile/", {"pk": otro.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pk"], self.usuario.pk)
        self.assertTrue(response.json()["tiene_contrasena_local"])
        for campo in ("password", "google_id", "is_staff", "is_superuser", "groups"):
            self.assertNotIn(campo, response.json())

    def test_put_parcial_actualiza_los_cuatro_campos_editables(self):
        """Cada campo se puede cambiar sin reenviar ni perder los otros."""
        for campo, valor in {
            "nombre": "José",
            "apellido": "López",
            "nombre_usuario": "nuevo123",
            "avatar_id": 1,
        }.items():
            with self.subTest(campo=campo):
                response = self.client.put(
                    "/api/profile/", {campo: valor}, content_type="application/json"
                )
                self.assertEqual(response.status_code, 200, response.content)
                self.usuario.refresh_from_db()
                self.assertEqual(getattr(self.usuario, campo), valor)
        self.assertEqual(self.usuario.nombre, "José")
        self.assertEqual(self.usuario.apellido, "López")

    def test_campos_manipulados_no_modifican_identidad_permisos_ni_preferencias(self):
        """La lista de campos permitidos impide escalada y escritura entre módulos."""
        antes = Usuario.objects.values().get(pk=self.usuario.pk)
        response = self.client.put(
            "/api/profile/",
            {
                "pk": 999,
                "correo": "otro@example.com",
                "password": "Robada123!",
                "estado": "baja",
                "google_id": "otro-sub",
                "is_staff": True,
                "is_superuser": True,
                "groups": [1],
                "user_permissions": [1],
                "fecha_nacimiento": "2020-01-01",
                "genero": "masculino",
                "tema": "claro",
                "perfil_publico": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Usuario.objects.values().get(pk=self.usuario.pk), antes)

    def test_validaciones_no_dejan_guardado_parcial(self):
        """Errores de CU-001 y avatar invalidan toda la petición."""
        for campo, valor in (
            ("nombre", "Ana2"),
            ("apellido", "Pérez!"),
            ("nombre", ""),
            ("nombre", "a" * 51),
            ("nombre_usuario", "abc"),
            ("nombre_usuario", "con espacio"),
            ("avatar_id", 999),
        ):
            with self.subTest(campo=campo, valor=valor):
                response = self.client.put(
                    "/api/profile/",
                    {"apellido": "Cambio", campo: valor},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(campo, response.json())
                self.usuario.refresh_from_db()
                self.assertEqual(self.usuario.apellido, "Pérez")

    def test_username_duplicado_409_y_mismo_usuario_permitido(self):
        """La unicidad ignora mayúsculas, pero permite conservar el username propio."""
        UsuarioFactory(nombre_usuario="Ocupado123")
        response = self.client.put(
            "/api/profile/",
            {"nombre_usuario": "OCUPADO123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        response = self.client.put(
            "/api/profile/",
            {"nombre_usuario": self.usuario.nombre_usuario.upper()},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_unicidad_en_bd_cubre_escrituras_concurrentes(self):
        """La BD, no solo el serializer, rechaza variantes del mismo nombre."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            UsuarioFactory(nombre_usuario=self.usuario.nombre_usuario.upper())

    def test_error_integridad_devuelve_conflicto_sin_guardar(self):
        """Una colisión posterior a la validación devuelve 409 y revierte cambios."""
        with patch(
            "usuarios.serializers.UsuarioPerfilSerializer.update",
            side_effect=IntegrityError,
        ):
            response = self.client.put(
                "/api/profile/", {"nombre": "Cambio"}, content_type="application/json"
            )
        self.assertEqual(response.status_code, 409)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.nombre, "María")

    def test_cookie_exige_csrf_y_header_bearer_no(self):
        """La autenticación real aplica CSRF a cookies en PUT."""
        cliente = Client(enforce_csrf_checks=True)
        cliente.cookies["access"] = str(self.refresh.access_token)
        self.assertEqual(
            cliente.put(
                "/api/profile/", {"nombre": "Ana"}, content_type="application/json"
            ).status_code,
            403,
        )
        cliente.get("/api/auth/csrf/")
        csrf = cliente.cookies["csrftoken"].value
        self.assertEqual(
            cliente.put(
                "/api/profile/",
                {"nombre": "Ana"},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=csrf,
            ).status_code,
            200,
        )


class ContrasenaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = UsuarioFactory()
        self.refresh = RefreshToken.for_user(self.usuario)
        self.client.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {self.refresh.access_token}"
        )
        self.payload = {
            "old_password": "Password123!",
            "password1": "NuevaClave456!",
            "password2": "NuevaClave456!",
        }

    def cambiar(self, payload=None, cliente=None, url="/api/profile/change-password/"):
        return (cliente or self.client).post(
            url, payload or self.payload, content_type="application/json"
        )

    def assert_revocado(self, refresh):
        cliente = Client()
        self.assertEqual(
            cliente.get(
                "/api/profile/", HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
            ).status_code,
            401,
        )
        self.assertEqual(
            cliente.post(
                "/api/auth/token/refresh/",
                {"refresh": str(refresh)},
                content_type="application/json",
            ).status_code,
            401,
        )

    def test_cambio_requiere_sesion(self):
        """Conocer los campos del formulario no basta para cambiar contraseñas."""
        self.assertEqual(self.cambiar(cliente=Client()).status_code, 401)

    def test_errores_no_cambian_contrasena_ni_revocan_sesion(self):
        """Contraseña actual, confirmación y política son verificadas por separado."""
        casos = [
            ({"old_password": "Incorrecta1!"}, "old_password"),
            ({"password2": "Distinta123!"}, "password2"),
        ]
        casos.extend(
            ({"password1": pwd, "password2": pwd}, "password1")
            for pwd in (
                "Pass1!",
                "A" * 21 + "a1!",
                "sinmayuscula1!",
                "SINMINUSCULA1!",
                "SinDigitos!",
                "SinEspecial123",
            )
        )
        for cambios, campo in casos:
            with self.subTest(cambios=cambios):
                cache.clear()
                response = self.cambiar({**self.payload, **cambios})
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(campo, response.json())
                self.usuario.refresh_from_db()
                self.assertTrue(self.usuario.check_password("Password123!"))
                self.assertEqual(self.client.get("/api/profile/").status_code, 200)

    def test_cambio_revoca_todos_los_dispositivos_y_notifica_sin_login(self):
        """Todos los JWT viejos fallan y la respuesta limpia ambas cookies."""
        otro_dispositivo = RefreshToken.for_user(self.usuario)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.cambiar()
        self.assertEqual(response.status_code, 200)
        for cookie in ("access", "refresh"):
            self.assertEqual(response.cookies[cookie]["max-age"], 0)
        self.assertNotIn("access", response.json())
        self.assert_revocado(self.refresh)
        self.assert_revocado(otro_dispositivo)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(self.payload["password1"], mail.outbox[0].body)
        for campo, valor in (
            ("email", self.usuario.correo),
            ("username", self.usuario.nombre_usuario),
        ):
            response = Client().post(
                "/api/auth/login/",
                {campo: valor, "password": self.payload["password1"]},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Client()
            .post(
                "/api/auth/login/",
                {"email": self.usuario.correo, "password": "Password123!"},
                content_type="application/json",
            )
            .status_code,
            400,
        )

    def test_tokens_sin_claim_previo_al_despliegue_se_rechazan(self):
        """La activación de revocación exige volver a autenticar sesiones antiguas."""
        del self.refresh[api_settings.REVOKE_TOKEN_CLAIM]
        self.assert_revocado(self.refresh)

    def test_refresh_valido_rota_y_cookie_exige_csrf(self):
        """Renovar sigue funcionando; un sitio externo no puede renovar por cookie."""
        cliente = Client(enforce_csrf_checks=True)
        cliente.cookies["refresh"] = str(self.refresh)
        self.assertEqual(cliente.post("/api/auth/token/refresh/").status_code, 403)
        cliente.get("/api/auth/csrf/")
        response = cliente.post(
            "/api/auth/token/refresh/",
            HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access", response.cookies)
        self.assertIn("refresh", response.cookies)
        self.assertNotEqual(response.cookies["refresh"].value, str(self.refresh))
        self.assertEqual(
            Client()
            .post(
                "/api/auth/token/refresh/",
                {"refresh": str(self.refresh)},
                content_type="application/json",
            )
            .status_code,
            401,
        )

    def test_cambio_por_cookie_rechaza_csrf_ausente_o_invalido(self):
        """El cambio de contraseña no se ejecuta sin protección CSRF."""
        cliente = Client(enforce_csrf_checks=True)
        cliente.cookies["access"] = str(self.refresh.access_token)
        for headers in ({}, {"HTTP_X_CSRFTOKEN": "invalido"}):
            self.assertEqual(
                cliente.post(
                    "/api/profile/change-password/",
                    self.payload,
                    content_type="application/json",
                    **headers,
                ).status_code,
                403,
            )
        cliente.get("/api/auth/csrf/")
        self.assertEqual(
            cliente.post(
                "/api/profile/change-password/",
                self.payload,
                content_type="application/json",
                HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value,
            ).status_code,
            200,
        )

    def test_alias_de_auth_no_evade_contrasena_actual(self):
        """El endpoint heredado no ofrece una ruta de cambio menos segura."""
        response = self.cambiar(
            {**self.payload, "old_password": "Incorrecta1!"},
            url="/api/auth/password/change/",
        )
        self.assertEqual(response.status_code, 400)

    def test_google_sin_password_indica_recuperacion(self):
        """Una contraseña inutilizable no se puede sustituir sin demostrar acceso al correo."""
        self.usuario.set_unusable_password()
        self.usuario.save(update_fields=["password"])
        self.client.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {RefreshToken.for_user(self.usuario).access_token}"
        )
        response = self.cambiar()
        self.assertEqual(response.status_code, 400)
        self.assertIn("recuperación por correo", str(response.json()))
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.has_usable_password())

    def test_fallo_persistencia_no_cambia_password_ni_notifica(self):
        """El rollback mantiene el hash original y no ejecuta el correo on_commit."""
        original = Usuario.save

        def falla_despues_de_guardar(usuario, *args, **kwargs):
            original(usuario, *args, **kwargs)
            raise RuntimeError("fallo simulado")

        with (
            self.captureOnCommitCallbacks(execute=True),
            patch.object(Usuario, "save", falla_despues_de_guardar),
        ):
            response = self.cambiar()
        self.assertEqual(response.status_code, 500)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Password123!"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.client.get("/api/profile/").status_code, 200)

    def test_fallo_notificacion_no_revierte_password(self):
        """Una caída del correo posterior al commit no devuelve falso fracaso."""
        with (
            self.captureOnCommitCallbacks(execute=True),
            patch(
                "usuarios.passwords.send_mail",
                side_effect=RuntimeError("correo no disponible"),
            ),
        ):
            response = self.cambiar()
        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.payload["password1"]))


class RecuperacionSesionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = UsuarioFactory()
        self.refresh = RefreshToken.for_user(self.usuario)
        self.payload = {
            "uid": user_pk_to_url_str(self.usuario),
            "token": default_token_generator.make_token(self.usuario),
            "password1": "Restablecida123!",
            "password2": "Restablecida123!",
        }

    def confirmar(self, data=None):
        return self.client.post(
            "/api/auth/password/reset/confirm/",
            data or self.payload,
            content_type="application/json",
        )

    def test_recuperacion_revoca_access_refresh_y_token_reutilizado(self):
        """Restablecer cierra todos los dispositivos y consume el enlace."""
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.confirmar().status_code, 200)
        self.assertEqual(self.confirmar().status_code, 400)
        self.assertEqual(
            self.client.get(
                "/api/profile/",
                HTTP_AUTHORIZATION=f"Bearer {self.refresh.access_token}",
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/token/refresh/",
                {"refresh": str(self.refresh)},
                content_type="application/json",
            ).status_code,
            401,
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_enlace_vencido_y_confirmaciones_distintas_no_cambian_password(self):
        """Los rechazos conservan tanto el hash como la sesión original."""
        with patch.object(
            default_token_generator,
            "_now",
            return_value=datetime.now() + timedelta(hours=2),
        ):
            self.assertEqual(self.confirmar().json(), {"codigo": "invalido"})
        response = self.confirmar({**self.payload, "password2": "Diferente123!"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("password2", response.json())
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Password123!"))

    def test_dos_validaciones_previas_no_permiten_dos_consumos(self):
        """La segunda escritura revalida el token bajo bloqueo, incluso si ya validó."""
        primero = RestablecerContrasenaSerializer(data=self.payload)
        segundo = RestablecerContrasenaSerializer(data=self.payload)
        self.assertTrue(primero.is_valid())
        self.assertTrue(segundo.is_valid())
        primero.save()
        with self.assertRaises(EnlaceRestablecimientoInvalido):
            segundo.save()

    def test_enlace_emitido_antes_de_baja_o_pendiente_se_rechaza(self):
        """Un enlace previo no permite cambiar la cuenta ni reactivarla."""
        for estado in (EstadoCuenta.BAJA, EstadoCuenta.PENDIENTE):
            self.usuario.estado = estado
            self.usuario.save(update_fields=["estado"])
            response = self.confirmar()
            self.assertEqual(response.status_code, 400)
            self.usuario.refresh_from_db()
            self.assertEqual(self.usuario.estado, estado)
            self.assertTrue(self.usuario.check_password("Password123!"))

    def test_google_agrega_password_por_email_sin_perder_vinculo(self):
        """El alta local por recuperación conserva el PK y el sub de Google."""
        self.usuario.set_unusable_password()
        self.usuario.google_id = "google-sub-perfil"
        self.usuario.save(update_fields=["password", "google_id"])
        social = SocialAccount.objects.create(
            user=self.usuario, provider="google", uid=self.usuario.google_id
        )
        response = self.client.post(
            "/api/auth/password/reset/",
            {"email": self.usuario.correo},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        enlace = re.search(
            r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body
        )
        self.assertIsNotNone(enlace)
        self.assertEqual(
            self.confirmar(
                {**self.payload, "uid": enlace[1], "token": enlace[2]}
            ).status_code,
            200,
        )
        self.usuario.refresh_from_db()
        social.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.payload["password1"]))
        self.assertEqual(social.user_id, self.usuario.pk)
        self.assertEqual(social.uid, self.usuario.google_id)
        for campo, valor in (
            ("email", self.usuario.correo),
            ("username", self.usuario.nombre_usuario),
        ):
            self.assertEqual(
                Client()
                .post(
                    "/api/auth/login/",
                    {campo: valor, "password": self.payload["password1"]},
                    content_type="application/json",
                )
                .status_code,
                200,
            )
        # Solo se simula la frontera criptográfica de Google, no el flujo de allauth.
        with patch(
            "allauth.socialaccount.providers.google.views._verify_and_decode",
            return_value={
                "sub": social.uid,
                "email": self.usuario.correo,
                "email_verified": True,
                "given_name": "Google",
                "family_name": "Nombre",
                "picture": "https://example.com/avatar.png",
            },
        ):
            response = Client().post(
                "/api/auth/google/",
                {"id_token": "token-google-verificado"},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["user"]["pk"], self.usuario.pk)
        self.assertEqual(Usuario.objects.count(), 1)
