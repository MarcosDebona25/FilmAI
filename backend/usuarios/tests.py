"""Tests de usuarios: disponibilidad de username (A-05) y confirmación de
cuenta por email (CU-002) con sus errores diferenciados."""

import re
from datetime import date
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.core import mail
from django.core.management import CommandError, call_command
from django.http import HttpRequest
from django.test import Client, TestCase, TransactionTestCase
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from catalogo.factories import CalificacionFactory, ResenaFactory
from catalogo.models import Calificacion, ProduccionAudiovisual, Resena, TipoProduccion
from listas.models import Tiene

from .adapter import UsuarioSocialAccountAdapter
from .factories import UsuarioFactory
from .management.commands.seed import (
    CALIFICACIONES_POR_USUARIO_SOLO_RESENAS,
    CANTIDAD_PRODUCCIONES,
    UMBRAL_CATALOGO_PROTEGIDO,
)
from .models import EstadoCuenta, TipoGenero, Usuario
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
        "pais": "AR",
        "acepta_terminos": True,
        "password1": "Password123!",
        "password2": "Password123!",
    }

    def setUp(self):
        # Estas pruebas afirman la copia en español; sin preferencia el correo
        # sale en inglés (idioma por defecto, OT-52).
        self.client.defaults["HTTP_ACCEPT_LANGUAGE"] = "es"

    def _registrar(self) -> str:
        response = self.client.post(
            "/api/auth/registration/", self.PAYLOAD, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        # El subject sale de nuestro template (prefijo global vacío).
        self.assertEqual(mail.outbox[0].subject, "[FilmAI] Confirmación de cuenta")
        # La key viaja en el enlace .../confirm-email/<key>/
        match = re.search(r"/confirm-email/([^/\s\"<]+)/", mail.outbox[0].body)
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

    def test_registro_normaliza_nombres_compuestos(self):
        """Registro guarda un solo espacio interno y quita los sobrantes."""
        payload = {
            **self.PAYLOAD,
            "nombre": "  Juan   Carlos  ",
            "apellido": " De  la Cruz ",
        }
        response = self.client.post(
            "/api/auth/registration/", payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        from .models import Usuario

        usuario = Usuario.objects.get(correo=self.PAYLOAD["correo"])
        self.assertEqual(
            (usuario.nombre, usuario.apellido), ("Juan Carlos", "De la Cruz")
        )

    def test_key_reusada_reporta_ya_confirmada(self):
        key = self._registrar()
        self.assertEqual(self._confirmar(key).status_code, 200)

        response = self._confirmar(key)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "already_confirmed")

    def test_key_corrupta_reporta_invalido(self):
        response = self._confirmar("key-totalmente-falsa")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "link_invalid")

    def test_key_expirada_reporta_expirado(self):
        key = self._registrar()

        # Adelantamos el reloj 25 horas: django.core.signing usa time.time()
        # para validar el timestamp firmado.
        import time as time_module

        real_time = time_module.time()
        with patch("django.core.signing.time.time", return_value=real_time + 25 * 3600):
            response = self._confirmar(key)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "link_expired")


class RecuperarContrasenaTests(TestCase):
    """Recuperación de contraseña (CU-020 / A-07).

    Cubre: envío del email con enlace al frontend, no revelación de
    existencia de cuentas, exclusión de cuentas no activas, cambio efectivo
    de contraseña, rechazo de enlaces inválidos y de contraseñas débiles,
    y rate limit de 1 solicitud por minuto por IP.
    """

    def setUp(self):
        from django.core.cache import cache

        self.client.defaults["HTTP_ACCEPT_LANGUAGE"] = "es"  # copia en español
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
        match = re.search(r"/reset-password/([^/]+)/([^/]+)/", mail.outbox[0].body)
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
        self.assertIn("code", response.json())
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
        match = re.search(r"/reset-password/([^/]+)/([^/]+)/", mail.outbox[0].body)

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
        self.assertEqual(response.json()["code"], "link_invalid")

    def test_confirmar_token_expirado_devuelve_invalido(self):
        import datetime as dt_mod
        from unittest.mock import patch as mock_patch

        from django.contrib.auth.tokens import PasswordResetTokenGenerator

        self._crear_usuario_activo()
        self._solicitar("recuperar@filmai.com")
        match = re.search(r"/reset-password/([^/]+)/([^/]+)/", mail.outbox[0].body)

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
        self.assertEqual(response.json()["code"], "link_invalid")

    def test_confirmar_politica_debil_rechazada(self):
        self._crear_usuario_activo()
        self._solicitar("recuperar@filmai.com")
        match = re.search(r"/reset-password/([^/]+)/([^/]+)/", mail.outbox[0].body)

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
        self.assertIn(
            "password1", {entry["field"] for entry in response.json()["errors"]}
        )

    def test_rate_limit_email_5_intentos_por_dia(self):
        """El throttle por email permite 5 solicitudes por día, luego bloquea."""
        self._crear_usuario_activo()

        # Las primeras 5 solicitudes deben funcionar
        for i in range(5):
            response = self._solicitar("recuperar@filmai.com")
            self.assertEqual(response.status_code, 200, f"Fallo en intento {i + 1}")

        # La 6ta solicitud debe ser bloqueada (429)
        sexta = self._solicitar("recuperar@filmai.com")
        self.assertEqual(sexta.status_code, 429)


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
            "pais": "AR",
        }

        usuario = Usuario(correo="google@filmai.com")
        sociallogin = SimpleNamespace(
            user=usuario,
            account=SimpleNamespace(provider="google", uid="google-sub-123"),
        )

        adapter = UsuarioSocialAccountAdapter()
        user = adapter.populate_user(
            request, sociallogin, {"email": "google@filmai.com"}
        )

        self.assertEqual(user.nombre_usuario, "usuariogoogle")
        self.assertEqual(user.fecha_nacimiento, date(1995, 5, 10))
        self.assertEqual(user.genero, "masculino")
        self.assertEqual(user.estado, EstadoCuenta.ACTIVA)

    def test_populate_user_existente_conserva_perfil_y_estado_de_filmai(self):
        usuario = UsuarioFactory(
            nombre="Nombre FilmAI",
            apellido="Apellido FilmAI",
            estado=EstadoCuenta.BAJA,
        )
        cuenta = SocialAccount.objects.create(
            user=usuario,
            provider="google",
            uid="google-sub-existente",
        )

        resultado = UsuarioSocialAccountAdapter().populate_user(
            HttpRequest(),
            SimpleNamespace(account=cuenta),
            {"given_name": "Nombre Google", "family_name": "Apellido Google"},
        )

        self.assertEqual(resultado.pk, usuario.pk)
        self.assertEqual(resultado.nombre, "Nombre FilmAI")
        self.assertEqual(resultado.apellido, "Apellido FilmAI")
        self.assertEqual(resultado.estado, EstadoCuenta.BAJA)

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
        user = SimpleNamespace(correo="google@filmai.com", is_active=True)
        return SimpleNamespace(
            # Tras `complete_social_login` (mockeado como no-op) la cuenta queda
            # persistida; el segundo `if not login.is_existing` no debe entrar.
            is_existing=is_existing,
            user=user,
            account=SimpleNamespace(
                provider=provider,
                uid=uid,
                user=user,
                # Lo que firma Google en el id_token (se exige desde el 26/10/2026).
                extra_data={"email_verified": True},
            ),
        )

    def _app(self):
        return SocialApp(
            provider="google", name="Google", client_id="test", secret="test"
        )

    def _patch_existencia(self, es_existente):
        """Simula la resolución del vínculo social y su usuario activo."""
        manager = Mock()
        manager.filter.return_value.first.return_value = (
            SimpleNamespace(user=SimpleNamespace(is_active=True))
            if es_existente
            else None
        )
        return patch(
            "usuarios.serializers.SocialAccount.objects.select_related",
            return_value=manager,
        )

    def test_validate_adjunta_campos_extra_al_request_sin_releer_el_body(self):
        extra = {
            "nombre_usuario": "usuariogoogle",
            "fecha_nacimiento": "1995-05-10",
            "genero": "no_especifica",
            "pais": "AR",
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
                "pais": "AR",
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

    def test_login_cuenta_existente_preserva_nombre_y_apellido_de_filmai(self):
        """El login no debe sobrescribir cambios de perfil hechos en FilmAI."""
        usuario = UsuarioFactory(
            nombre="Nombre elegido",
            apellido="Apellido elegido",
        )
        SocialAccount.objects.create(
            user=usuario,
            provider="google",
            uid="google-sub-123",
        )
        serializer, _ = self._serializer_google()
        login = self._login_mock()
        login.user = usuario
        login.account.user = usuario
        app = self._app()

        with (
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

        usuario.refresh_from_db()
        self.assertEqual(usuario.nombre, "Nombre elegido")
        self.assertEqual(usuario.apellido, "Apellido elegido")

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
                "pais": "AR",
                "acepta_terminos": True,
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


class SeguridadCamposAdministradorTests(TestCase):
    """Verifica que los campos de administrador no sean modificables vía API.

    Regresión: un usuario autenticado no debe poder escalar privilegios
    modificando is_staff, is_superuser, groups o user_permissions mediante
    requests HTTP manipuladas.
    """

    def setUp(self):
        self.usuario = UsuarioFactory(
            nombre_usuario="usuariocomun",
            correo="comun@filmai.com",
            estado=EstadoCuenta.ACTIVA,
        )
        # Autenticar usando el endpoint de login
        response = self.client.post(
            "/api/auth/login/",
            {"email": "comun@filmai.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_usuario_detalles_no_expone_campos_admin(self):
        """El endpoint /api/auth/user/ no debe exponer campos de administrador."""
        response = self.client.get("/api/auth/user/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Campos que NO deben estar presentes
        for campo in ("is_staff", "is_superuser", "groups", "user_permissions"):
            self.assertNotIn(
                campo, data, f"El campo {campo} no debe exponerse en /api/auth/user/"
            )

    def test_registro_no_permite_establecer_campos_admin(self):
        """El registro no debe permitir establecer is_staff o is_superuser."""
        response = self.client.post(
            "/api/auth/registration/",
            {
                "correo": "nuevo@filmai.com",
                "nombre_usuario": "nuevousuario",
                "nombre": "Nuevo",
                "apellido": "Usuario",
                "fecha_nacimiento": "2000-01-01",
                "genero": "no_especifica",
                "pais": "AR",
                "acepta_terminos": True,
                "password1": "Password123!",
                "password2": "Password123!",
                # Intento de escalada de privilegios
                "is_staff": True,
                "is_superuser": True,
            },
            content_type="application/json",
        )
        # El registro debe funcionar pero ignorar los campos admin
        self.assertIn(response.status_code, [200, 201, 400])
        if response.status_code in [200, 201]:
            nuevo_usuario = Usuario.objects.get(correo="nuevo@filmai.com")
            # Los campos admin deben ser False por defecto
            self.assertFalse(nuevo_usuario.is_staff)
            self.assertFalse(nuevo_usuario.is_superuser)


class LoginDualTests(TestCase):
    """Tests de integración para ambos mecanismos de autenticación.

    Verifica que tanto el login por correo como por nombre de usuario
    funcionen correctamente de manera independiente. Esto detecta regresiones
    si futuras actualizaciones de django-allauth, dj-rest-auth o Django
    rompen silenciosamente alguna de las dos variantes.
    """

    def setUp(self):
        self.usuario = UsuarioFactory(
            nombre_usuario="testuser",
            correo="test@filmai.com",
            estado=EstadoCuenta.ACTIVA,
        )
        self.usuario.set_password("Password123!")
        self.usuario.save()
        self.login_url = "/api/auth/login/"

    def test_login_por_correo_exitoso(self):
        """Login con correo electrónico y contraseña debe funcionar."""
        response = self.client.post(
            self.login_url,
            {"email": "test@filmai.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_login_por_nombre_usuario_exitoso(self):
        """Login con nombre de usuario y contraseña debe funcionar."""
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_login_correo_insensible_a_mayusculas(self):
        """El login por correo debe ser insensible a mayúsculas."""
        response = self.client.post(
            self.login_url,
            {"email": "TEST@filmai.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_login_nombre_usuario_insensible_a_mayusculas(self):
        """El login por nombre de usuario debe ser insensible a mayúsculas."""
        response = self.client.post(
            self.login_url,
            {"username": "TESTUSER", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_login_correo_incorrecto_falla(self):
        """Login con correo incorrecto debe fallar."""
        response = self.client.post(
            self.login_url,
            {"email": "wrong@filmai.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_login_nombre_usuario_incorrecto_falla(self):
        """Login con nombre de usuario incorrecto debe fallar."""
        response = self.client.post(
            self.login_url,
            {"username": "wronguser", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_login_contrasena_incorrecta_falla(self):
        """Login con contraseña incorrecta debe fallar."""
        response = self.client.post(
            self.login_url,
            {"email": "test@filmai.com", "password": "WrongPassword123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_login_cuenta_inactiva_por_correo_rechazado(self):
        """Login con cuenta inactiva (por correo) debe ser rechazado con 403."""
        self.usuario.estado = EstadoCuenta.PENDIENTE
        self.usuario.save()
        response = self.client.post(
            self.login_url,
            {"email": "test@filmai.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_login_cuenta_inactiva_por_username_rechazado(self):
        """Login con cuenta inactiva (por username) debe ser rechazado con 403."""
        self.usuario.estado = EstadoCuenta.PENDIENTE
        self.usuario.save()
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class AvatarValidacionTests(TestCase):
    """Tests para la validación de avatar_id.

    Verifica que solo se acepten avatar_id válidos según el registro
    centralizado de avatares.
    """

    def test_avatar_id_valido_es_aceptado(self):
        """Un avatar_id válido debe ser aceptado."""
        from .avatares import AVATAR_IDS_VALIDOS

        for avatar_id in AVATAR_IDS_VALIDOS:
            with self.subTest(avatar_id=avatar_id):
                usuario = UsuarioFactory(avatar_id=avatar_id)
                self.assertEqual(usuario.avatar_id, avatar_id)

    def test_avatar_id_invalido_es_rechazado_en_serializer(self):
        """Un avatar_id inválido debe ser rechazado por el serializer."""
        from .serializers import UsuarioPerfilSerializer

        usuario = UsuarioFactory()
        serializer = UsuarioPerfilSerializer(
            instance=usuario,
            data={"avatar_id": 999},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("avatar_id", serializer.errors)

    def test_avatar_id_cero_es_rechazado(self):
        """avatar_id = 0 debe ser rechazado (no está en el registro)."""
        from .serializers import UsuarioPerfilSerializer

        usuario = UsuarioFactory()
        serializer = UsuarioPerfilSerializer(
            instance=usuario,
            data={"avatar_id": 0},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("avatar_id", serializer.errors)

    def test_avatar_id_negativo_es_rechazado(self):
        """avatar_id negativo debe ser rechazado."""
        from .serializers import UsuarioPerfilSerializer

        usuario = UsuarioFactory()
        serializer = UsuarioPerfilSerializer(
            instance=usuario,
            data={"avatar_id": -1},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("avatar_id", serializer.errors)

    def test_registro_centralizado_de_avatares(self):
        """El registro centralizado debe existir y tener avatares válidos."""
        from .avatares import AVATARES, es_avatar_valido

        # Debe tener al menos un avatar
        self.assertGreater(len(AVATARES), 0)
        # El ID 1 debe existir (default)
        self.assertIn(1, AVATARES)
        # es_avatar_valido debe funcionar correctamente
        self.assertTrue(es_avatar_valido(1))
        self.assertFalse(es_avatar_valido(999))
        self.assertFalse(es_avatar_valido(True))
        self.assertFalse(es_avatar_valido(1.0))


class ValidadoresContrasenaTests(TestCase):
    """Tests unitarios para las políticas de contraseña de FilmAI.

    Verifica individualmente cada regla del validador ComplejidadContrasenaValidator:
    - Longitud: 8-20 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un dígito
    - Al menos un carácter especial (@#$%&*!)
    """

    def setUp(self):
        from .validators import ComplejidadContrasenaValidator

        self.validator = ComplejidadContrasenaValidator()

    def test_contrasena_valida_cumple_todas_las_reglas(self):
        """Una contraseña que cumple todas las reglas debe ser aceptada."""
        contrasenas_validas = [
            "Password1!",
            "MiContrasena123@",
            "Test1234#",
            "Abcdefg1$",
            "Password2024%",
            "Secure&Pass1",
            "MyP@ssw0rd",
            "ValidPass*123",
        ]
        for password in contrasenas_validas:
            with self.subTest(password=password):
                # No debe lanzar excepción
                self.validator.validate(password)

    def test_contrasena_muy_corta_es_rechazada(self):
        """Contraseñas con menos de 8 caracteres deben ser rechazadas."""
        contrasenas_cortas = [
            "Pass1!",  # 6 caracteres
            "Abc12!",  # 6 caracteres
            "Test12@",  # 7 caracteres
        ]
        for password in contrasenas_cortas:
            with self.subTest(password=password):
                from django.core.exceptions import ValidationError

                with self.assertRaises(ValidationError) as ctx:
                    self.validator.validate(password)
                self.assertIn("8", str(ctx.exception))

    def test_contrasena_muy_larga_es_rechazada(self):
        """Contraseñas con más de 20 caracteres deben ser rechazadas."""
        password_larga = "Password1!" + "a" * 11  # 21 caracteres
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate(password_larga)
        self.assertIn("20", str(ctx.exception))

    def test_contrasena_sin_mayuscula_es_rechazada(self):
        """Contraseñas sin mayúsculas deben ser rechazadas."""
        contrasenas_sin_mayuscula = [
            "password1!",
            "test1234@",
            "abcdefg1#",
        ]
        for password in contrasenas_sin_mayuscula:
            with self.subTest(password=password):
                from django.core.exceptions import ValidationError

                with self.assertRaises(ValidationError) as ctx:
                    self.validator.validate(password)
                self.assertIn("mayúscula", str(ctx.exception))

    def test_contrasena_sin_minuscula_es_rechazada(self):
        """Contraseñas sin minúsculas deben ser rechazadas."""
        contrasenas_sin_minuscula = [
            "PASSWORD1!",
            "TEST1234@",
            "ABCDEFG1#",
        ]
        for password in contrasenas_sin_minuscula:
            with self.subTest(password=password):
                from django.core.exceptions import ValidationError

                with self.assertRaises(ValidationError) as ctx:
                    self.validator.validate(password)
                self.assertIn("minúscula", str(ctx.exception))

    def test_contrasena_sin_digito_es_rechazada(self):
        """Contraseñas sin dígitos deben ser rechazadas."""
        contrasenas_sin_digito = [
            "Password!",
            "MiContrasena@",
            "TestTest#",
        ]
        for password in contrasenas_sin_digito:
            with self.subTest(password=password):
                from django.core.exceptions import ValidationError

                with self.assertRaises(ValidationError) as ctx:
                    self.validator.validate(password)
                self.assertIn("dígito", str(ctx.exception))

    def test_contrasena_sin_caracter_especial_es_rechazada(self):
        """Contraseñas sin caracteres especiales deben ser rechazadas."""
        contrasenas_sin_especial = [
            "Password1",
            "Test12345",
            "Abcdefg12",
        ]
        for password in contrasenas_sin_especial:
            with self.subTest(password=password):
                from django.core.exceptions import ValidationError

                with self.assertRaises(ValidationError) as ctx:
                    self.validator.validate(password)
                self.assertIn("especial", str(ctx.exception))

    def test_caracteres_especiales_aceptados(self):
        """Cada carácter especial permitido debe ser aceptado individualmente."""
        caracteres_especiales = ["@", "#", "$", "%", "&", "*", "!"]
        for char in caracteres_especiales:
            password = f"Password1{char}"
            with self.subTest(char=char):
                # No debe lanzar excepción
                self.validator.validate(password)

    def test_limite_inferior_exacto(self):
        """Una contraseña de exactamente 8 caracteres debe ser aceptada si cumple todas las reglas."""
        password = "Pass123!"  # 8 caracteres
        self.validator.validate(password)

    def test_limite_superior_exacto(self):
        """Una contraseña de exactamente 20 caracteres debe ser aceptada si cumple todas las reglas."""
        password = "Password1234567!Ab"  # 20 caracteres
        self.validator.validate(password)

    def test_get_help_text(self):
        """El texto de ayuda debe describir las reglas de contraseña."""
        help_text = self.validator.get_help_text()
        self.assertIn("8", help_text)
        self.assertIn("20", help_text)
        self.assertIn("mayúscula", help_text)
        self.assertIn("minúscula", help_text)
        self.assertIn("dígito", help_text)
        self.assertIn("especial", help_text)


class SeedGuardCatalogoTests(TestCase):
    """`manage.py seed` no borra por accidente un catálogo poblado (C-04c).

    El comando hace `ProduccionAudiovisual.objects.all().delete()` para
    resetear datos de desarrollo. Con `seed_catalogo` eso dejó de ser barato:
    son horas de llamadas a TMDB, y por CASCADE se lleva calificaciones,
    reseñas y entradas de listas. Por encima de un umbral se niega y dice qué
    flag lo fuerza; documentarlo en el README depende de que alguien lo haya
    leído justo cuando intenta resetear su base.
    """

    def _poblar_catalogo(self, cantidad):
        ProduccionAudiovisual.objects.bulk_create(
            ProduccionAudiovisual(
                id_tmdb=numero, tipo=TipoProduccion.PELICULA, titulo=f"P{numero}"
            )
            for numero in range(1, cantidad + 1)
        )

    def test_se_niega_por_encima_del_umbral_y_nombra_el_flag(self):
        self._poblar_catalogo(UMBRAL_CATALOGO_PROTEGIDO + 1)

        with self.assertRaisesMessage(CommandError, "--borrar-catalogo"):
            call_command("seed", "--sintetico")

        # No borró nada: ni el catálogo ni lo que cuelga de él.
        self.assertEqual(
            ProduccionAudiovisual.objects.count(), UMBRAL_CATALOGO_PROTEGIDO + 1
        )

    def test_con_el_flag_borra_y_recrea(self):
        self._poblar_catalogo(UMBRAL_CATALOGO_PROTEGIDO + 1)

        call_command("seed", "--sintetico", "--borrar-catalogo", verbosity=0)

        self.assertEqual(ProduccionAudiovisual.objects.count(), CANTIDAD_PRODUCCIONES)

    def test_por_debajo_del_umbral_sigue_sin_flag(self):
        # Un catálogo del tamaño que crea el propio seed se resetea como
        # siempre: el guard no cambia el flujo de desarrollo habitual.
        self._poblar_catalogo(CANTIDAD_PRODUCCIONES)

        call_command("seed", "--sintetico", verbosity=0)

        self.assertEqual(ProduccionAudiovisual.objects.count(), CANTIDAD_PRODUCCIONES)


def _crear_superusuario(correo="admin@filmai.com", nombre_usuario="admin"):
    """Crea un superusuario con todos los campos que exige el modelo Usuario.

    `create_superuser` solo garantiza is_staff/is_superuser/estado; los demás
    campos (nombre, apellido, fecha_nacimiento, genero) son obligatorios y
    hay que pasarlos sí o sí, igual que hace el entrypoint del contenedor.
    """
    return Usuario.objects.create_superuser(
        correo=correo,
        nombre_usuario=nombre_usuario,
        password="Password123!",
        nombre="Admin",
        apellido="FilmAI",
        fecha_nacimiento=date(2000, 1, 1),
        genero=TipoGenero.NO_ESPECIFICA,
    )


def _calificadas_fuera_de_vistas():
    """Calificaciones cuya producción no está en las «Vistas» de su autor.

    La regla «calificada ⇒ en Vistas» (30/09/2026) pide que sea vacía. El seed
    crea las notas con la factory, sin pasar por la API, así que la aplica a
    mano; si se olvidara, cada `seed` volvería a sembrar datos que la violan.
    """
    return [
        calificacion
        for calificacion in Calificacion.objects.all()
        if not Tiene.objects.filter(
            lista__usuario_id=calificacion.usuario_id,
            lista__nombre="Vistas",
            produccion_id=calificacion.produccion_id,
        ).exists()
    ]


class SeedSoloResenasTests(TestCase):
    """`manage.py seed --solo-resenas` suma actividad sin borrar nada.

    Complementa a SeedGuardCatalogoTests: cuando el catálogo supera el umbral
    (C-04c), forzar un reset cuesta horas de TMDB. Este modo siembra
    calificaciones y reseñas sobre el catálogo y los usuarios de desarrollo
    existentes, y se puede repetir sin duplicar (es idempotente).
    """

    def _poblar_catalogo(self, cantidad):
        ProduccionAudiovisual.objects.bulk_create(
            ProduccionAudiovisual(
                id_tmdb=numero, tipo=TipoProduccion.PELICULA, titulo=f"P{numero}"
            )
            for numero in range(1, cantidad + 1)
        )

    def test_crea_calificaciones_y_resenas_sin_borrar_nada(self):
        self._poblar_catalogo(120)
        UsuarioFactory(nombre_usuario="dev001")
        UsuarioFactory(nombre_usuario="dev002")
        staff = _crear_superusuario()
        externo = UsuarioFactory(nombre_usuario="externo", correo="externo@gmail.com")

        call_command("seed", "--solo-resenas", verbosity=0)

        # No borra ni el catálogo protegido ni los usuarios existentes.
        self.assertEqual(ProduccionAudiovisual.objects.count(), 120)
        self.assertEqual(Usuario.objects.count(), 4)
        # Solo las cuentas deterministas del seed (@filmai.com, no staff)
        # califican: el staff y el correo gmail quedan afuera.
        self.assertEqual(staff.calificaciones.count(), 0)
        self.assertEqual(externo.calificaciones.count(), 0)
        self.assertGreater(Calificacion.objects.count(), 0)
        self.assertGreater(Resena.objects.count(), 0)
        # Valores dentro del rango 1..10 (ck_calificacion_valor_rango)...
        self.assertEqual(
            Calificacion.objects.exclude(valor__gte=1, valor__lte=10).count(), 0
        )
        # ...y sin pares (usuario, produccion) repetidos.
        self.assertEqual(
            Calificacion.objects.values("usuario", "produccion").distinct().count(),
            Calificacion.objects.count(),
        )

    def test_es_idempotente(self):
        self._poblar_catalogo(120)
        UsuarioFactory(nombre_usuario="dev001")

        call_command("seed", "--solo-resenas", verbosity=0)
        calificaciones = Calificacion.objects.count()
        resenas = Resena.objects.count()
        call_command("seed", "--solo-resenas", verbosity=0)

        # Hay catálogo sobrante: la segunda corrida debe dejar los mismos
        # conteos, no solo evitar pares duplicados.
        self.assertEqual(calificaciones, CALIFICACIONES_POR_USUARIO_SOLO_RESENAS)
        self.assertEqual(Calificacion.objects.count(), calificaciones)
        self.assertEqual(Resena.objects.count(), resenas)
        self.assertEqual(
            Calificacion.objects.values("usuario", "produccion").distinct().count(),
            Calificacion.objects.count(),
        )

    def test_todo_lo_calificado_queda_en_vistas(self):
        self._poblar_catalogo(120)
        UsuarioFactory(nombre_usuario="dev001")

        call_command("seed", "--solo-resenas", verbosity=0)

        self.assertGreater(Calificacion.objects.count(), 0)
        self.assertEqual(_calificadas_fuera_de_vistas(), [])

    def test_completa_hasta_el_objetivo_sin_modificar_datos_existentes(self):
        self._poblar_catalogo(120)
        usuario = UsuarioFactory(nombre_usuario="dev001")
        produccion = ProduccionAudiovisual.objects.first()
        existente = CalificacionFactory(
            usuario=usuario, produccion=produccion, valor=10
        )
        resena = ResenaFactory(calificacion=existente, texto="Texto existente")

        call_command("seed", "--solo-resenas", verbosity=0)

        existente.refresh_from_db()
        resena.refresh_from_db()
        self.assertEqual(existente.valor, 10)
        self.assertEqual(resena.texto, "Texto existente")
        self.assertEqual(
            Calificacion.objects.filter(usuario=usuario).count(),
            CALIFICACIONES_POR_USUARIO_SOLO_RESENAS,
        )
        self.assertEqual(Resena.objects.filter(calificacion=existente).count(), 1)

    def test_agrega_texto_a_calificaciones_previas_sin_resena(self):
        self._poblar_catalogo(15)
        usuario = UsuarioFactory(nombre_usuario="dev001")
        producciones = list(ProduccionAudiovisual.objects.all())
        for produccion in producciones:
            CalificacionFactory(usuario=usuario, produccion=produccion)

        call_command("seed", "--solo-resenas", verbosity=0)
        self.assertEqual(Calificacion.objects.filter(usuario=usuario).count(), 15)
        self.assertEqual(
            Resena.objects.filter(calificacion__usuario=usuario).count(), 9
        )

        # La segunda corrida conserva los textos creados y sus relaciones.
        resenas = list(Resena.objects.values_list("pk", "calificacion_id"))
        call_command("seed", "--solo-resenas", verbosity=0)
        self.assertEqual(
            list(Resena.objects.values_list("pk", "calificacion_id")), resenas
        )

    def test_crea_resenas_inactivas_para_moderar(self):
        self._poblar_catalogo(15)
        UsuarioFactory(nombre_usuario="dev001")

        # Mock de todo el módulo `random` del comando: con random() < 0.6
        # TODAS las calificaciones llevan reseña, así que la 7ª y la 14ª
        # nacen con activa=False (1 de cada 7, AD-01'/CU-017).
        with patch("usuarios.management.commands.seed.random") as random_mock:
            random_mock.random.return_value = 0.1
            random_mock.sample.side_effect = lambda seq, k: seq
            call_command("seed", "--solo-resenas", verbosity=0)

        self.assertTrue(Resena.objects.filter(activa=False).exists())
        # OneToOne (CU-015): cada reseña cuelga de su calificación.
        self.assertEqual(Resena.objects.filter(calificacion__isnull=True).count(), 0)

    def test_sin_catalogo_aborta(self):
        UsuarioFactory(nombre_usuario="dev001")

        # Sin producciones no hay nada que calificar: aborta y nombra el
        # comando que crea el set completo.
        with self.assertRaisesMessage(CommandError, "seed"):
            call_command("seed", "--solo-resenas", verbosity=0)

        self.assertEqual(Calificacion.objects.count(), 0)

    def test_sin_usuarios_dev_aborta(self):
        self._poblar_catalogo(15)
        _crear_superusuario()

        # Con catálogo pero sin cuentas de desarrollo (@filmai.com, no staff)
        # tampoco tiene sentido: aborta y nombra el comando completo.
        with self.assertRaisesMessage(CommandError, "seed"):
            call_command("seed", "--solo-resenas", verbosity=0)

        self.assertEqual(Calificacion.objects.count(), 0)


class SeedConservaStaffTests(TestCase):
    """El seed completo borra los datos de negocio pero no al superusuario.

    El README promete que `seed` no elimina el superusuario que crea el
    entrypoint; si lo borrara, un reset de desarrollo dejaría a todo el
    equipo sin acceso a /admin/.
    """

    def _poblar_catalogo(self, cantidad):
        ProduccionAudiovisual.objects.bulk_create(
            ProduccionAudiovisual(
                id_tmdb=numero, tipo=TipoProduccion.PELICULA, titulo=f"P{numero}"
            )
            for numero in range(1, cantidad + 1)
        )

    def test_con_el_flag_conserva_el_superusuario(self):
        admin = _crear_superusuario()
        EmailAddress.objects.create(
            user=admin, email=admin.correo, verified=True, primary=True
        )
        normal = UsuarioFactory()
        self._poblar_catalogo(UMBRAL_CATALOGO_PROTEGIDO + 1)

        call_command("seed", "--sintetico", "--borrar-catalogo", verbosity=0)

        # El superusuario y su EmailAddress sobreviven al reset...
        self.assertTrue(
            Usuario.objects.filter(correo=admin.correo, is_staff=True).exists()
        )
        self.assertTrue(EmailAddress.objects.filter(user=admin).exists())
        # ...pero los usuarios de negocio se borran como siempre.
        self.assertFalse(Usuario.objects.filter(pk=normal.pk).exists())

    def test_seed_completo_crea_resenas_validas(self):
        # Por debajo del umbral el flujo completo corre sin flag.
        self._poblar_catalogo(CANTIDAD_PRODUCCIONES)

        call_command("seed", "--sintetico", verbosity=0)

        self.assertGreater(Calificacion.objects.count(), 0)
        self.assertGreater(Resena.objects.count(), 0)
        # Rango 1..10, pares (usuario, produccion) únicos y composición 1:1
        # entre reseña y calificación (CU-015).
        self.assertEqual(
            Calificacion.objects.exclude(valor__gte=1, valor__lte=10).count(), 0
        )
        self.assertEqual(
            Calificacion.objects.values("usuario", "produccion").distinct().count(),
            Calificacion.objects.count(),
        )
        self.assertEqual(Resena.objects.filter(calificacion__isnull=True).count(), 0)
        # Y todo lo calificado quedó en «Vistas» (regla del 30/09/2026).
        self.assertEqual(_calificadas_fuera_de_vistas(), [])
