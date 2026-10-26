"""Comprobaciones ejecutables de los supuestos de la sección 2.6."""

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from catalogo.factories import ResenaFactory
from usuarios.factories import UsuarioFactory
from usuarios.models import EstadoCuenta
from usuarios.serializers import LoginSerializer


@override_settings(DEBUG=False)
class EstadoCuentaCaracterizacionTests(TestCase):
    def test_mensaje_inactivo_del_serializer_se_oculta_en_la_respuesta(self):
        """El diagnóstico queda interno; el HTTP público identifica el estado solo con credenciales correctas."""
        client = APIClient()
        for estado, mensaje in (
            (EstadoCuenta.BAJA, "Tu cuenta fue dada de baja."),
            (
                EstadoCuenta.PENDIENTE,
                "Tu cuenta aún no está activa. Revisá tu correo para confirmarla.",
            ),
        ):
            usuario = UsuarioFactory(estado=estado)
            for campo, identificador in (
                ("email", usuario.correo),
                ("username", usuario.nombre_usuario),
            ):
                with self.subTest(estado=estado, campo=campo, password="correcta"):
                    datos = {campo: identificador, "password": "Password123!"}
                    serializer = LoginSerializer(data=datos)
                    with self.assertRaises(PermissionDenied) as error:
                        serializer.is_valid(raise_exception=True)
                    self.assertEqual(str(error.exception.detail), mensaje)
                    respuesta = client.post("/api/auth/login/", datos, format="json")
                    self.assertEqual(respuesta.status_code, 403)
                    self.assertEqual(
                        respuesta.json()["code"],
                        "account_deactivated"
                        if estado == EstadoCuenta.BAJA
                        else "account_pending_confirmation",
                    )
                    self.assertNotIn("detail", respuesta.json())
                # OT-33: con credencial incorrecta el estado ya no se revela.
                with self.subTest(estado=estado, campo=campo, password="incorrecta"):
                    datos = {campo: identificador, "password": "WrongPassword123!"}
                    respuesta = client.post("/api/auth/login/", datos, format="json")
                    self.assertEqual(respuesta.status_code, 400)
                    self.assertEqual(respuesta.json()["code"], "invalid_credentials")
                    self.assertNotIn(mensaje, str(respuesta.json()))

    def test_resena_y_calificacion_siguen_publicas_tras_baja(self):
        """La baja conserva los datos: la comunidad ve texto y nota, sin el autor.

        Hasta el 26/10/2026 también se veía el nombre de usuario; desde entonces
        la reseña sale anónima (decisión registrada en docs/decisiones.md).
        """
        resena = ResenaFactory(texto="Reseña pública de referencia")
        usuario = resena.calificacion.usuario
        produccion = resena.calificacion.produccion
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}")
        respuesta = client.post("/api/account/deactivate/", {}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        usuario.refresh_from_db()
        self.assertEqual(usuario.estado, EstadoCuenta.BAJA)
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(UsuarioFactory())}"
        )
        tipo = "movie" if produccion.tipo == "pelicula" else "tv"
        respuesta = client.get(
            "/api/reviews/", {"id_tmdb": produccion.id_tmdb, "tipo": tipo}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["results"]), 1)
        publicado = respuesta.json()["results"][0]
        self.assertEqual(publicado["texto"], resena.texto)
        self.assertEqual(publicado["valor"], resena.calificacion.valor)
        self.assertIsNone(publicado["nombre_usuario"])
        self.assertTrue(publicado["autor_dado_de_baja"])
