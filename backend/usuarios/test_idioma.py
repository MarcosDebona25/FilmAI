"""Preferencia persistida y registro con idioma, sin traducir respuestas todavía."""

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .adapter import UsuarioSocialAccountAdapter
from .factories import UsuarioFactory
from .models import Usuario


class PreferenciasIdiomaTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        token = RefreshToken.for_user(self.usuario).access_token
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    def test_cambio_de_idioma_persiste_y_conserva_otras_preferencias(self):
        """Elegir ES/EN no cambia tema ni preferencias omitidas."""
        for idioma in ("es", "en"):
            with self.subTest(idioma=idioma):
                response = self.client.put(
                    "/api/preferences/",
                    {"idioma": idioma},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.usuario.refresh_from_db()
                self.assertEqual(self.usuario.idioma, idioma)
                self.assertEqual(response.json()["idioma"], idioma)
                self.assertEqual(response.json()["tema"], "oscuro")
                self.assertEqual(
                    self.client.get("/api/preferences/").json()["idioma"], idioma
                )

    def test_valores_invalidos_no_borran_la_preferencia_guardada(self):
        """Nulo es estado previo de cuenta; el selector solo puede guardar idiomas soportados."""
        self.usuario.idioma = "es"
        self.usuario.save(update_fields=["idioma"])
        for valor in ("fr", "es-AR", "", None, ["en"]):
            with self.subTest(valor=valor):
                response = self.client.put(
                    "/api/preferences/",
                    {"idioma": valor},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.usuario.refresh_from_db()
                self.assertEqual(self.usuario.idioma, "es")

    def test_usuario_y_perfil_exponen_idioma_solo_lectura(self):
        """El cambio de idioma tiene su operación de preferencias, no edición de perfil."""
        for ruta in ("/api/auth/user/", "/api/profile/"):
            with self.subTest(ruta=ruta):
                self.assertIsNone(self.client.get(ruta).json()["idioma"])
        response = self.client.put(
            "/api/profile/", {"idioma": "es"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertIsNone(self.usuario.idioma)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistroIdiomaTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_registro_guarda_el_encabezado_o_el_respaldo(self):
        """El idioma activo se guarda antes del correo; un campo extra no lo impone."""
        for indice, (encabezado, esperado) in enumerate(
            (("es-MX,en;q=0.5", "es"), ("en", "en"), (None, "en"))
        ):
            with self.subTest(encabezado=encabezado):
                payload = {
                    "correo": f"idioma{indice}@example.com",
                    "nombre_usuario": f"idioma{indice}",
                    "nombre": "Cuenta",
                    "apellido": "Nueva",
                    "fecha_nacimiento": "1990-01-01",
                    "genero": "no_especifica",
                    "password1": "Password123!",
                    "password2": "Password123!",
                    "idioma": "es" if esperado == "en" else "en",
                }
                headers = (
                    {} if encabezado is None else {"HTTP_ACCEPT_LANGUAGE": encabezado}
                )
                response = self.client.post(
                    "/api/auth/registration/",
                    payload,
                    content_type="application/json",
                    **headers,
                )
                self.assertEqual(response.status_code, 201, response.content)
                self.assertEqual(
                    Usuario.objects.get(correo=payload["correo"]).idioma, esperado
                )

    def test_alta_google_persiste_idioma_del_request(self):
        """La frontera OAuth se aísla; el adaptador y guardado social son reales."""
        for indice, (encabezado, esperado) in enumerate(
            (("es-AR", "es"), (None, "en"))
        ):
            with self.subTest(encabezado=encabezado):
                correo = f"google{indice}@example.com"
                headers = (
                    {} if encabezado is None else {"HTTP_ACCEPT_LANGUAGE": encabezado}
                )
                request = RequestFactory().post("/api/auth/google/", **headers)
                request.session = {}
                request.google_extra = {
                    "nombre_usuario": f"googleidioma{indice}",
                    "fecha_nacimiento": "1990-01-01",
                    "genero": "no_especifica",
                }
                login = SocialLogin(
                    user=Usuario(correo=correo),
                    account=SocialAccount(
                        provider="google", uid=f"idioma-google-{indice}"
                    ),
                    email_addresses=[
                        EmailAddress(email=correo, verified=True, primary=True)
                    ],
                )
                adapter = UsuarioSocialAccountAdapter()
                login.user = adapter.populate_user(request, login, {"email": correo})
                adapter.save_user(request, login)
                self.assertEqual(Usuario.objects.get(correo=correo).idioma, esperado)

    def test_google_existente_conserva_idioma_aunque_cambie_encabezado(self):
        """Iniciar sesión no convierte el idioma del dispositivo en preferencia de cuenta."""
        usuario = UsuarioFactory(idioma="es")
        cuenta = SocialAccount.objects.create(
            user=usuario, provider="google", uid="existente-idioma"
        )
        request = RequestFactory().post("/api/auth/google/", HTTP_ACCEPT_LANGUAGE="en")
        resultado = UsuarioSocialAccountAdapter().populate_user(
            request, SocialLogin(account=cuenta), {"email": usuario.correo}
        )
        self.assertEqual(resultado.pk, usuario.pk)
        self.assertEqual(resultado.idioma, "es")
        usuario.refresh_from_db()
        self.assertEqual(usuario.idioma, "es")
