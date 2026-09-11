"""Tests de usuarios: disponibilidad de username (A-05) y confirmación de
cuenta por email (CU-002) con sus errores diferenciados."""

import re
from datetime import date
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.core import mail
from django.core.management import call_command
from django.http import HttpRequest
from django.test import Client, TestCase, TransactionTestCase
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from .adapter import UsuarioSocialAccountAdapter
from .factories import UsuarioFactory
from .models import EstadoCuenta, Usuario
from .provisioning import LISTAS_PREDETERMINADAS
from .serializers import GoogleSocialLoginSerializer


class UsernameDisponibleTests(TestCase):
    def setUp(self):
        self.url = "/api/auth/username-available/"
        self.usuario = UsuarioFactory(nombre_usuario="usuario123")

    def test_disponible_cuando_no_existe(self):
        response = self.client.get(self.url, {"username": "nuevousuario"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"disponible": True})

    def test_no_disponible_cuando_existe(self):
        response = self.client.get(self.url, {"username": "usuario123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"disponible": False})

    def test_insensible_a_mayusculas(self):
        response = self.client.get(self.url, {"username": "USUARIO123"})
        self.assertEqual(response.json(), {"disponible": False})

    def test_formato_invalido_reporta_no_disponible(self):
        for username in ("abc", "a" * 26, "con espacio!", ""):
            with self.subTest(username=username):
                response = self.client.get(self.url, {"username": username})
                self.assertEqual(response.json(), {"disponible": False})


class ConfirmarCorreoTests(TestCase):
    """Flujo CU-002 completo sobre el backend real (emails en outbox local).

    El registro envía el correo vía allauth con nuestros templates en español;
    la key se extrae del `activate_url` del cuerpo capturado.
    """

    PAYLOAD: ClassVar[dict] = {
        "correo": "confirmar@filmai.com",
        "nombre_usuario": "usuarioconf",
        "nombre": "Confirmar",
        "apellido": "Correo",
        "fecha_nacimiento": "1995-05-10",
        "genero": "no_especifica",
        "password1": "Password123!",
        "password2": "Password123!",
    }

    def _registrar(self) -> str:
        response = self.client.post(
            "/api/auth/registration/", self.PAYLOAD, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        # El subject sale de nuestro template (prefijo global vacío).
        self.assertEqual(mail.outbox[0].subject, "[FilmAI] Confirmación de cuenta")
        # La key viaja en el enlace .../confirmar-correo/<key>/
        match = re.search(r"/confirmar-correo/([^/\s\"<]+)/", mail.outbox[0].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def _confirmar(self, key: str):
        return self.client.post(
            "/api/auth/registration/verify-email/",
            {"key": key},
            content_type="application/json",
        )

    def _estado_cuenta(self):
        from .models import EstadoCuenta, Usuario

        usuario = Usuario.objects.get(correo=self.PAYLOAD["correo"])
        email_address = EmailAddress.objects.get(email=self.PAYLOAD["correo"])
        return usuario, email_address, EstadoCuenta

    def test_flujo_completo_registro_confirmacion_login(self):
        key = self._registrar()

        usuario, email_address, EstadoCuenta = self._estado_cuenta()
        self.assertEqual(usuario.estado, EstadoCuenta.PENDIENTE)
        self.assertFalse(email_address.verified)

        # Saludo del email de confirmación con nombre + apellido.
        self.assertIn("Hola Confirmar Correo,", mail.outbox[0].body)

        response = self._confirmar(key)
        self.assertEqual(response.status_code, 200)

        usuario, email_address, _ = self._estado_cuenta()
        self.assertEqual(usuario.estado, EstadoCuenta.ACTIVA)
        self.assertTrue(email_address.verified)

        login = self.client.post(
            "/api/auth/login/",
            {"email": self.PAYLOAD["correo"], "password": "Password123!"},
            content_type="application/json",
        )
        self.assertIn("access", login.json())

    def test_key_reusada_reporta_ya_confirmada(self):
        key = self._registrar()
        self.assertEqual(self._confirmar(key).status_code, 200)

        response = self._confirmar(key)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "ya_confirmada"})

    def test_key_corrupta_reporta_invalido(self):
        response = self._confirmar("key-totalmente-falsa")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "invalido"})

    def test_key_expirada_reporta_expirado(self):
        key = self._registrar()

        # Adelantamos el reloj 25 horas: django.core.signing usa time.time()
        # para validar el timestamp firmado.
        import time as time_module

        real_time = time_module.time()
        with patch("django.core.signing.time.time", return_value=real_time + 25 * 3600):
            response = self._confirmar(key)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "expirado"})


class RecuperarContrasenaTests(TestCase):
    """Recuperación de contraseña (CU-020 / A-07).

    Cubre: envío del email con enlace al frontend, no revelación de
    existencia de cuentas, exclusión de cuentas no activas, cambio efectivo
    de contraseña, rechazo de enlaces inválidos y de contraseñas débiles,
    y rate limit de 1 solicitud por minuto por IP.
    """

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def _crear_usuario_activo(self, correo: str = "recuperar@filmai.com"):
        usuario = UsuarioFactory(
            nombre_usuario="usuarioreset",
            correo=correo,
            nombre="Recuperar",
            apellido="Contrasena",
        )  # el factory ya crea la cuenta ACTIVA
        usuario.set_password("ViejaPass1!")
        usuario.save()
        return usuario

    def _solicitar(self, email: str):
        return self.client.post(
            "/api/auth/password/reset/",
            {"email": email},
            content_type="application/json",
        )

    def test_solicitud_envia_email_con_enlace_al_frontend(self):
        self._crear_usuario_activo()

        response = self._solicitar("recuperar@filmai.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject, "[FilmAI] Restablecimiento de contraseña"
        )
        match = re.search(
            r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body
        )
        self.assertIsNotNone(match)
        self.assertIn("válido durante 1 hora", mail.outbox[0].body)
        # El saludo muestra nombre + apellido (docs/decisiones.md 24/08/2026).
        self.assertIn("Hola Recuperar Contrasena,", mail.outbox[0].body)

    def test_saludo_fallback_sin_nombre(self):
        """Sin nombre ni apellido, el saludo es "Hola usuario"."""
        UsuarioFactory(
            nombre_usuario="usuariosenombre",
            correo="sinnombre@filmai.com",
            nombre="",
            apellido="",
        )

        self._solicitar("sinnombre@filmai.com")

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Hola usuario,", mail.outbox[0].body)

    def test_solicitud_email_inexistente_no_revela_y_no_envia(self):
        response = self._solicitar("fantasma@filmai.com")

        self.assertEqual(response.status_code, 200)
        # Misma respuesta que para un correo existente (docs/02 CU-020 obs.).
        self.assertIn("detail", response.json())
        self.assertEqual(len(mail.outbox), 0)

    def test_solicitud_cuenta_pendiente_o_baja_no_envia_email(self):
        pendiente = UsuarioFactory(
            nombre_usuario="usuariopend",
            correo="pendiente@filmai.com",
            estado=EstadoCuenta.PENDIENTE,
        )
        assert pendiente.estado == EstadoCuenta.PENDIENTE

        response = self._solicitar("pendiente@filmai.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmar_actualiza_contraseña_y_permite_login(self):
        self._crear_usuario_activo()
        self._solicitar("recuperar@filmai.com")
        match = re.search(
            r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body
        )

        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": match.group(1),
                "token": match.group(2),
                "password1": "NuevaPass456!",
                "password2": "NuevaPass456!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        viejo = self.client.post(
            "/api/auth/login/",
            {"email": "recuperar@filmai.com", "password": "ViejaPass1!"},
            content_type="application/json",
        )
        nuevo = self.client.post(
            "/api/auth/login/",
            {"email": "recuperar@filmai.com", "password": "NuevaPass456!"},
            content_type="application/json",
        )
        self.assertEqual(viejo.status_code, 400)
        self.assertEqual(nuevo.status_code, 200)
        self.assertIn("access", nuevo.json())

    def test_confirmar_enlace_invalido_devuelve_codigo(self):
        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": "AAAA",
                "token": "token-falso",
                "password1": "NuevaPass456!",
                "password2": "NuevaPass456!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "invalido"})

    def test_confirmar_token_expirado_devuelve_invalido(self):
        import datetime as dt_mod
        from unittest.mock import patch as mock_patch

        from django.contrib.auth.tokens import PasswordResetTokenGenerator

        self._crear_usuario_activo()
        self._solicitar("recuperar@filmai.com")
        match = re.search(
            r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body
        )

        futuro = dt_mod.datetime.now() + dt_mod.timedelta(hours=2)
        with mock_patch.object(
            PasswordResetTokenGenerator, "_now", return_value=futuro
        ):
            response = self.client.post(
                "/api/auth/password/reset/confirm/",
                {
                    "uid": match.group(1),
                    "token": match.group(2),
                    "password1": "NuevaPass456!",
                    "password2": "NuevaPass456!",
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "invalido"})

    def test_confirmar_politica_debil_rechazada(self):
        self._crear_usuario_activo()
        self._solicitar("recuperar@filmai.com")
        match = re.search(
            r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body
        )

        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": match.group(1),
                "token": match.group(2),
                "password1": "abc123",
                "password2": "abc123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password1", response.json())

    def test_rate_limit_segunda_solicitud_429(self):
        self._crear_usuario_activo()

        primera = self._solicitar("recuperar@filmai.com")
        segunda = self._solicitar("recuperar@filmai.com")

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 429)


class GoogleOAuthTests(TestCase):
    """Regresión del 500 en `/api/auth/google/` (RawPostDataException) y del
    flujo login vs registro con Google.

    En un view de DRF, `request.data` consume el stream del body. El adapter
    releía `request.body` dentro de `populate_user` para obtener los campos que
    Google no provee, lo que lanzaba `RawPostDataException` → 500. Ahora esos
    campos viajan pegados al request (`request.google_extra`) y el adapter no
    toca el body. Además se cubre que una cuenta de Google existente inicia
    sesión sin los campos extra, y una nueva los exige. Ver docs/decisiones.md
    (26/08/2026).
    """

    def test_populate_user_lee_campos_extra_sin_releer_el_body(self):
        # Estado exacto que deja DRF tras parsear el body: `_read_started=True`
        # hace que cualquier acceso a `request.body` lance RawPostDataException.
        request = HttpRequest()
        request._read_started = True
        request.google_extra = {
            "nombre_usuario": "usuariogoogle",
            "fecha_nacimiento": "1995-05-10",
            "genero": "masculino",
        }

        usuario = Usuario(correo="google@filmai.com")
        sociallogin = SimpleNamespace(user=usuario)

        adapter = UsuarioSocialAccountAdapter()
        user = adapter.populate_user(
            request, sociallogin, {"email": "google@filmai.com"}
        )

        self.assertEqual(user.nombre_usuario, "usuariogoogle")
        self.assertEqual(user.fecha_nacimiento, date(1995, 5, 10))
        self.assertEqual(user.genero, "masculino")
        self.assertEqual(user.estado, EstadoCuenta.ACTIVA)

    def _serializer_google(self, extra=None):
        """Construye el serializer con el request en el estado post-parseo de DRF.

        Deja `_read_started=True` para que cualquier acceso a `request.body`
        lance `RawPostDataException` (regresión del 500).
        """
        factory = APIRequestFactory()
        django_request = factory.post(
            "/api/auth/google/",
            {"id_token": "fake-id-token", **(extra or {})},
            format="json",
        )
        drf_request = Request(django_request, parsers=[JSONParser()])
        _ = drf_request.data  # fuerza el parseo de DRF (consume el body)
        django_request._read_started = True

        view = SimpleNamespace(adapter_class=GoogleOAuth2Adapter)
        serializer = GoogleSocialLoginSerializer(
            data=drf_request.data,
            context={"request": drf_request, "view": view},
        )
        return serializer, django_request

    def _login_mock(self, provider="google", uid="google-sub-123", is_existing=False):
        user = SimpleNamespace(correo="google@filmai.com")
        return SimpleNamespace(
            # Tras `complete_social_login` (mockeado como no-op) la cuenta queda
            # persistida; el segundo `if not login.is_existing` no debe entrar.
            is_existing=is_existing,
            user=user,
            account=SimpleNamespace(
                provider=provider,
                uid=uid,
                user=user,
            ),
        )

    def _app(self):
        return SocialApp(
            provider="google", name="Google", client_id="test", secret="test"
        )

    def _patch_existencia(self, es_existente):
        """Fija `SocialAccount.objects.filter(...).exists()` al valor deseado."""
        return patch(
            "usuarios.serializers.SocialAccount.objects.filter",
            return_value=SimpleNamespace(exists=lambda: es_existente),
        )

    def test_validate_adjunta_campos_extra_al_request_sin_releer_el_body(self):
        extra = {
            "nombre_usuario": "usuariogoogle",
            "fecha_nacimiento": "1995-05-10",
            "genero": "no_especifica",
        }
        serializer, django_request = self._serializer_google(extra=extra)
        login = self._login_mock(is_existing=False)
        app = self._app()
        with (
            self._patch_existencia(True),
            patch.object(serializer, "get_social_login", return_value=login),
            patch(
                "usuarios.serializers.complete_social_login",
                side_effect=lambda _request, social_login: setattr(
                    social_login, "is_existing", True
                ),
            ),
            patch.object(
                GoogleOAuth2Adapter,
                "get_provider",
                return_value=SimpleNamespace(app=app),
            ),
        ):
            self.assertTrue(serializer.is_valid())
            attrs = serializer.validated_data

        self.assertEqual(
            django_request.google_extra,
            {
                "nombre_usuario": "usuariogoogle",
                "fecha_nacimiento": date(1995, 5, 10),
                "genero": "no_especifica",
            },
        )
        self.assertIs(attrs["user"], login.account.user)

    def test_login_cuenta_existente_no_exige_campos(self):
        """Regresión: una cuenta de Google ya vinculada inicia sesión SIN los
        campos extra (antes caía en la rama de "campos faltantes" y el frontend
        la mandaba a /completar-google)."""
        serializer, _ = self._serializer_google()  # solo id_token
        login = self._login_mock()
        app = self._app()
        with (
            self._patch_existencia(True),
            patch.object(serializer, "get_social_login", return_value=login),
            patch(
                "usuarios.serializers.complete_social_login",
                side_effect=lambda _request, social_login: setattr(
                    social_login, "is_existing", True
                ),
            ),
            patch.object(
                GoogleOAuth2Adapter,
                "get_provider",
                return_value=SimpleNamespace(app=app),
            ),
        ):
            self.assertTrue(serializer.is_valid())

    def test_registro_cuenta_nueva_sin_campos_devuelve_error(self):
        """Una cuenta de Google NUEVA (sin SocialAccount) exige los campos que
        Google no provee: `nombre_usuario`, `fecha_nacimiento`, `genero`."""
        serializer, _ = self._serializer_google()  # solo id_token
        login = self._login_mock()
        app = self._app()
        with (
            self._patch_existencia(False),
            patch.object(serializer, "get_social_login", return_value=login),
            patch("usuarios.serializers.complete_social_login", return_value=None),
            patch.object(
                GoogleOAuth2Adapter,
                "get_provider",
                return_value=SimpleNamespace(app=app),
            ),
        ):
            self.assertFalse(serializer.is_valid())
            errores = serializer.errors
            for campo in ("nombre_usuario", "fecha_nacimiento", "genero"):
                self.assertIn(campo, errores)

    def test_registro_cuenta_nueva_correo_duplicado_rechaza_antes_de_persistir(self):
        """Regresión: el chequeo de email duplicado case-insensitive corre ANTES
        de `complete_social_login`.

        Con `SOCIALACCOUNT_AUTO_SIGNUP=True`, allauth puede crear el usuario
        dentro de esa llamada cuando el usuario existente no tiene
        `EmailAddress` (p.ej. los del seed); entonces un chequeo a posteriori
        llega tarde y queda una segunda fila `Usuario` pese a responderse 400.
        """
        UsuarioFactory(
            nombre_usuario="mariaregistrada",
            correo="maria@filmai.com",
            estado=EstadoCuenta.ACTIVA,
        )
        serializer, _ = self._serializer_google(
            extra={
                "nombre_usuario": "usuariogoogle",
                "fecha_nacimiento": "1995-05-10",
                "genero": "masculino",
            }
        )
        login = self._login_mock()
        # El perfil de Google trae el mismo correo con otras mayúsculas.
        login.user = SimpleNamespace(correo="MARIA@filmai.com")
        app = self._app()
        with (
            self._patch_existencia(False),
            patch.object(serializer, "get_social_login", return_value=login),
            patch(
                "usuarios.serializers.complete_social_login", return_value=None
            ) as complete_mock,
            patch.object(
                GoogleOAuth2Adapter,
                "get_provider",
                return_value=SimpleNamespace(app=app),
            ),
        ):
            self.assertFalse(serializer.is_valid())
            self.assertIn(
                "Ya existe una cuenta registrada con este correo.",
                str(serializer.errors),
            )
            complete_mock.assert_not_called()

        self.assertEqual(Usuario.objects.count(), 1)


class CsrfCookieTests(TestCase):
    """Protección CSRF del access token en cookie httpOnly (JWT_AUTH_COOKIE_USE_CSRF).

    Al autenticar por cookie (sin header Bearer), `JWTCookieAuthentication`
    exige el header `X-CSRFToken` en las mutaciones. El frontend obtiene la
    cookie `csrftoken` vía `GET /api/auth/csrf/` y la reenvía.
    """

    def _crear_usuario_activo(self):
        usuario = UsuarioFactory(
            nombre_usuario="usuariocsrf",
            correo="csrf@filmai.com",
            nombre="Csrf",
            apellido="Test",
        )
        usuario.set_password("Password123!")
        usuario.save()
        return usuario

    def test_csrf_endpoint_setea_cookie(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_mutacion_autenticada_exige_header_csrf(self):
        self._crear_usuario_activo()

        # El test client desactiva CSRF por defecto; acá lo activamos.
        cliente = Client(enforce_csrf_checks=True)

        # 1. Obtener la cookie csrftoken.
        cliente.get("/api/auth/csrf/")

        # 2. Login (sin cookie `access` previa no hay enforcement) → setea cookies.
        #    OJO: dj-rest-auth con SESSION_LOGIN=True (default) hace `django_login`,
        #    que ROTA el token CSRF (rotate_token). Hay que releerlo después.
        login = cliente.post(
            "/api/auth/login/",
            {"email": "csrf@filmai.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", cliente.cookies)
        csrf = cliente.cookies["csrftoken"].value  # valor vigente tras el login

        # 3. Mutación autenticada SIN header CSRF → rechazada (403).
        sin_header = cliente.post("/api/auth/logout/")
        self.assertEqual(sin_header.status_code, 403)

        # 4. Con el header CSRF (valor actual) → aceptada.
        con_header = cliente.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(con_header.status_code, 200)


class RecursosPredeterminadosTests(TestCase):
    def _crear_usuario(self, correo="recursos@filmai.com"):
        return Usuario.objects.create_user(
            correo=correo,
            password="Password123!",
            nombre_usuario="recursos123",
            nombre="Recursos",
            apellido="Predeterminados",
            fecha_nacimiento="2000-01-01",
            genero="no_especifica",
        )

    def test_usuario_nuevo_recibe_listas_y_chat_del_mvp(self):
        usuario = self._crear_usuario()

        self.assertEqual(usuario.listas.count(), 3)
        self.assertEqual(
            set(usuario.listas.values_list("nombre", flat=True)),
            set(LISTAS_PREDETERMINADAS),
        )
        self.assertEqual(usuario.chats.count(), 1)

    def test_comando_repara_recursos_faltantes_sin_duplicarlos(self):
        usuario = self._crear_usuario()
        usuario.listas.all().delete()
        usuario.chats.all().delete()

        call_command("reparar_recursos_usuarios", "--usuario-id", usuario.pk)
        call_command("reparar_recursos_usuarios", "--usuario-id", usuario.pk)

        self.assertEqual(usuario.listas.count(), 3)
        self.assertEqual(usuario.chats.count(), 1)


class RecursosPredeterminadosRollbackTests(TransactionTestCase):
    def test_fallo_al_crear_chat_revierte_usuario_y_listas(self):
        with (
            patch(
                "chatbot.models.Chat.objects.get_or_create",
                side_effect=RuntimeError("fallo simulado"),
            ),
            self.assertRaisesMessage(RuntimeError, "fallo simulado"),
        ):
            Usuario.objects.create_user(
                correo="rollback@filmai.com",
                password="Password123!",
                nombre_usuario="rollback123",
                nombre="Rollback",
                apellido="Prueba",
                fecha_nacimiento="2000-01-01",
                genero="no_especifica",
            )

        self.assertFalse(Usuario.objects.filter(correo="rollback@filmai.com").exists())
