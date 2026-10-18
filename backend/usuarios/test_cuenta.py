"""Preferencias, conservación de datos y acceso según el estado de cuenta."""

from unittest.mock import patch

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.socialaccount.models import SocialAccount
from django.core.cache import cache
from django.test import Client, TestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from catalogo.factories import CalificacionFactory, ResenaFactory
from chatbot.models import Mensaje
from listas.models import Lista, Tiene

from .factories import UsuarioFactory
from .models import EstadoCuenta, Usuario


class PreferenciasTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        self.refresh = RefreshToken.for_user(self.usuario)
        self.client.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {self.refresh.access_token}"
        )

    def test_get_defaults_y_put_parcial_conservan_campos_omitidos(self):
        """Los defaults se devuelven y cada preferencia es independiente."""
        esperado = {
            "idioma": None,
            "perfil_publico": True,
            "notif_recomendaciones": True,
            "notif_resenas": True,
            "notif_novedades": True,
        }
        self.assertEqual(self.client.get("/api/preferences/").json(), esperado)
        for campo, valor in (
            ("perfil_publico", False),
            ("notif_recomendaciones", False),
            ("notif_resenas", False),
            ("notif_novedades", False),
        ):
            with self.subTest(campo=campo):
                esperado[campo] = valor
                response = self.client.put(
                    "/api/preferences/", {campo: valor}, content_type="application/json"
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), esperado)
                self.assertEqual(self.client.get("/api/preferences/").json(), esperado)
        self.assertEqual(
            self.client.put(
                "/api/preferences/", {}, content_type="application/json"
            ).json(),
            esperado,
        )

    def test_no_autenticado_no_lee_ni_escribe(self):
        """Preferencias privadas: tanto leer como modificar exige JWT."""
        cliente = Client()
        self.assertEqual(cliente.get("/api/preferences/").status_code, 401)
        self.assertEqual(
            cliente.put(
                "/api/preferences/", {}, content_type="application/json"
            ).status_code,
            401,
        )

    def test_campos_manipulados_no_afectan_usuario_ajeno_ni_perfil(self):
        """El usuario se toma de la sesión, nunca del cuerpo del request."""
        otro = UsuarioFactory()
        antes = Usuario.objects.values().get(pk=self.usuario.pk)
        response = self.client.put(
            "/api/preferences/",
            {
                "pk": otro.pk,
                "usuario": otro.pk,
                "correo": "cambio@example.com",
                "nombre": "Otro",
                "estado": "baja",
                "password": "OtraClave123!",
                "is_staff": True,
                "is_superuser": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Usuario.objects.values().get(pk=self.usuario.pk), antes)
        otro.refresh_from_db()
        self.assertEqual(otro.perfil_publico, True)

    def test_valores_invalidos_rechazan_todo_el_cambio(self):
        """Idioma desconocido y booleanos inválidos no dejan actualizaciones parciales."""
        for campo, valor in (
            ("idioma", "fr"),
            ("perfil_publico", "quizas"),
            ("notif_resenas", None),
            ("notif_novedades", []),
        ):
            with self.subTest(campo=campo):
                response = self.client.put(
                    "/api/preferences/",
                    {"notif_recomendaciones": False, campo: valor},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(
                    campo, {entry["field"] for entry in response.json()["errors"]}
                )
                self.usuario.refresh_from_db()
                self.assertTrue(self.usuario.notif_recomendaciones)

    def test_put_cookie_exige_csrf(self):
        """El navegador necesita CSRF para cambiar preferencias."""
        cliente = Client(enforce_csrf_checks=True)
        cliente.cookies["access"] = str(self.refresh.access_token)
        self.assertEqual(
            cliente.put(
                "/api/preferences/",
                {"perfil_publico": False},
                content_type="application/json",
            ).status_code,
            403,
        )
        cliente.get("/api/auth/csrf/")
        self.assertEqual(
            cliente.put(
                "/api/preferences/",
                {"perfil_publico": False},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value,
            ).status_code,
            200,
        )


class EstadoCuentaTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_matriz_estado_correo_username_google_access_refresh(self):
        """Solo activa permite cualquiera de los cinco caminos de autenticación."""
        for estado in EstadoCuenta.values:
            with self.subTest(estado=estado):
                usuario = UsuarioFactory(estado=EstadoCuenta.ACTIVA)
                social = SocialAccount.objects.create(
                    user=usuario, provider="google", uid=f"google-{usuario.pk}"
                )
                refresh = RefreshToken.for_user(usuario)
                usuario.estado = estado
                usuario.save(update_fields=["estado"])
                activa = estado == EstadoCuenta.ACTIVA
                for campo, valor in (
                    ("email", usuario.correo),
                    ("username", usuario.nombre_usuario),
                ):
                    response = Client().post(
                        "/api/auth/login/",
                        {campo: valor, "password": "Password123!"},
                        content_type="application/json",
                    )
                    self.assertEqual(
                        response.status_code, 200 if activa else 403, response.content
                    )
                with patch(
                    "allauth.socialaccount.providers.google.views._verify_and_decode",
                    return_value={
                        "sub": social.uid,
                        "email": usuario.correo,
                        "email_verified": True,
                        "picture": "https://example.com/avatar.png",
                    },
                ):
                    response = Client().post(
                        "/api/auth/google/",
                        {"id_token": "google-verificado"},
                        content_type="application/json",
                    )
                self.assertEqual(
                    response.status_code, 200 if activa else 403, response.content
                )
                for url in ("/api/profile/", "/api/preferences/", "/api/lists/"):
                    response = Client().get(
                        url, HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
                    )
                    self.assertEqual(
                        response.status_code, 200 if activa else 401, response.content
                    )
                response = Client().post(
                    "/api/auth/token/refresh/",
                    {"refresh": str(refresh)},
                    content_type="application/json",
                )
                self.assertEqual(
                    response.status_code, 200 if activa else 401, response.content
                )
                usuario.refresh_from_db()
                self.assertEqual(usuario.estado, estado)

    def test_google_usa_sub_aunque_cambie_el_correo_y_preserva_perfil(self):
        """Cambiar el correo en Google no crea otro usuario ni sobrescribe el perfil."""
        usuario = UsuarioFactory(nombre="Nombrelocal", apellido="Apellidolocal")
        SocialAccount.objects.create(user=usuario, provider="google", uid="sub-estable")
        with patch(
            "allauth.socialaccount.providers.google.views._verify_and_decode",
            return_value={
                "sub": "sub-estable",
                "email": "correo-nuevo@example.com",
                "email_verified": True,
                "given_name": "NombreGoogle",
                "family_name": "ApellidoGoogle",
                "picture": "https://example.com/avatar.png",
            },
        ):
            response = self.client.post(
                "/api/auth/google/",
                {"id_token": "google-verificado"},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["user"]["pk"], usuario.pk)
        self.assertEqual(Usuario.objects.count(), 1)
        usuario.refresh_from_db()
        self.assertEqual(usuario.nombre, "Nombrelocal")
        self.assertNotEqual(usuario.correo, "correo-nuevo@example.com")

    def test_confirmacion_email_no_reactiva_cuenta_baja(self):
        """Un enlace de activación todavía válido no puede revertir una baja."""
        usuario = UsuarioFactory(estado=EstadoCuenta.BAJA)
        email = EmailAddress.objects.create(
            user=usuario, email=usuario.correo, primary=True, verified=False
        )
        key = EmailConfirmationHMAC(email).key
        response = self.client.post(
            "/api/auth/registration/verify-email/",
            {"key": key},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        usuario.refresh_from_db()
        self.assertEqual(usuario.estado, EstadoCuenta.BAJA)
        email.refresh_from_db()
        self.assertFalse(email.verified)


class BajaCuentaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = UsuarioFactory()
        self.refresh = RefreshToken.for_user(self.usuario)
        self.otro_refresh = RefreshToken.for_user(self.usuario)
        self.client.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {self.refresh.access_token}"
        )

    def desactivar(self, cliente=None, payload=None):
        return (cliente or self.client).post(
            "/api/account/deactivate/", payload or {}, content_type="application/json"
        )

    def test_baja_conserva_datos_y_relaciones_y_cierra_todas_las_sesiones(self):
        """No hay cascadas: todos los datos de dominio conservan PK, contenido y FK."""
        self.client.force_login(self.usuario)
        calificacion = CalificacionFactory(usuario=self.usuario)
        resena = ResenaFactory(calificacion=calificacion)
        lista = Lista.objects.create(usuario=self.usuario, nombre="Mi lista")
        item = Tiene.objects.create(lista=lista, produccion=calificacion.produccion)
        chat = self.usuario.chats.get()
        mensaje = Mensaje.objects.create(chat=chat, texto="Mi mensaje", autor="usuario")
        social = SocialAccount.objects.create(
            user=self.usuario, provider="google", uid="google-baja"
        )
        email = EmailAddress.objects.create(
            user=self.usuario, email=self.usuario.correo, verified=True
        )
        relaciones = [
            calificacion,
            resena,
            lista,
            item,
            chat,
            mensaje,
            social,
            email,
            *self.usuario.listas.exclude(pk=lista.pk),
        ]
        antes = [
            (type(objeto), objeto.pk, type(objeto).objects.values().get(pk=objeto.pk))
            for objeto in relaciones
        ]
        usuario_antes = Usuario.objects.values().get(pk=self.usuario.pk)
        response = self.desactivar()
        self.assertEqual(response.status_code, 200, response.content)
        usuario_antes["estado"] = EstadoCuenta.BAJA
        self.assertEqual(
            Usuario.objects.values().get(pk=self.usuario.pk), usuario_antes
        )
        for modelo, pk, datos in antes:
            self.assertEqual(modelo.objects.values().get(pk=pk), datos)
        for cookie in ("access", "refresh"):
            self.assertEqual(response.cookies[cookie]["max-age"], 0)
        self.assertNotIn("_auth_user_id", self.client.session)
        for refresh in (self.refresh, self.otro_refresh):
            self.assertTrue(
                BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
            )
            self.assertEqual(
                Client()
                .get(
                    "/api/profile/", HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
                )
                .status_code,
                401,
            )
            self.assertEqual(
                Client()
                .post(
                    "/api/auth/token/refresh/",
                    {"refresh": str(refresh)},
                    content_type="application/json",
                )
                .status_code,
                401,
            )
        self.assertEqual(self.desactivar().status_code, 401)

    def test_baja_solo_afecta_usuario_de_la_sesion(self):
        """Un cuerpo manipulado no permite dar de baja a otro usuario."""
        otro = UsuarioFactory()
        response = self.desactivar(
            payload={
                "pk": otro.pk,
                "usuario": otro.pk,
                "estado": "activa",
                "is_staff": True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        otro.refresh_from_db()
        self.assertEqual(self.usuario.estado, EstadoCuenta.BAJA)
        self.assertFalse(self.usuario.is_staff)
        self.assertEqual(otro.estado, EstadoCuenta.ACTIVA)

    def test_sin_sesion_o_cuenta_pendiente_no_puede_dar_baja(self):
        """POST requiere una sesión de cuenta activa, no solo un JWT firmado."""
        self.assertEqual(self.desactivar(cliente=Client()).status_code, 401)
        self.usuario.estado = EstadoCuenta.PENDIENTE
        self.usuario.save(update_fields=["estado"])
        self.assertEqual(self.desactivar().status_code, 401)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.estado, EstadoCuenta.PENDIENTE)

    def test_baja_por_cookie_exige_csrf(self):
        """Sin CSRF válido se rechaza antes de modificar el estado."""
        cliente = Client(enforce_csrf_checks=True)
        cliente.cookies["access"] = str(self.refresh.access_token)
        self.assertEqual(self.desactivar(cliente=cliente).status_code, 403)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.estado, EstadoCuenta.ACTIVA)
        cliente.get("/api/auth/csrf/")
        response = cliente.post(
            "/api/account/deactivate/",
            HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 200)

    def test_fallo_al_revocar_segundo_token_revierte_estado_y_blacklist(self):
        """Un fallo intermedio revierte incluso la primera revocación ya persistida."""
        original = BlacklistedToken.objects.get_or_create
        llamadas = 0

        def falla_segunda(*args, **kwargs):
            nonlocal llamadas
            llamadas += 1
            if llamadas == 2:
                raise RuntimeError("fallo de blacklist")
            return original(*args, **kwargs)

        with patch(
            "usuarios.cuenta.BlacklistedToken.objects.get_or_create",
            side_effect=falla_segunda,
        ):
            response = self.desactivar()
        self.assertEqual(response.status_code, 500)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.estado, EstadoCuenta.ACTIVA)
        self.assertEqual(BlacklistedToken.objects.count(), 0)
        self.assertEqual(self.client.get("/api/profile/").status_code, 200)
        self.assertEqual(
            Client()
            .post(
                "/api/auth/token/refresh/",
                {"refresh": str(self.otro_refresh)},
                content_type="application/json",
            )
            .status_code,
            200,
        )

    def test_fallo_cierre_sesion_revierte_baja(self):
        """Cerrar sesión también forma parte de la unidad atómica de baja."""
        with patch(
            "usuarios.cuenta.cerrar_sesion", side_effect=RuntimeError("fallo de sesión")
        ):
            self.assertEqual(self.desactivar().status_code, 500)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.estado, EstadoCuenta.ACTIVA)
        self.assertEqual(BlacklistedToken.objects.count(), 0)
