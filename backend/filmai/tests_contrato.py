"""Referencia del contrato previo a i18n; cada caso ejecuta código real.

REGENERAR_REFERENCIAS_API=1 permite actualizar los JSON explícitamente.
Los métodos generados son tests independientes (uno por caso del inventario).
"""

import json
import os
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from allauth.account import app_settings
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.socialaccount.models import SocialAccount, SocialApp
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.conf import settings
from django.core import signing
from django.db import IntegrityError
from django.http import Http404, HttpResponseBadRequest
from django.test import TestCase, override_settings
from django.utils.translation import override
from requests.exceptions import RequestException
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
)
from rest_framework.test import APIClient, APIRequestFactory

from catalogo.client import TMDBClient
from catalogo.exceptions import CalificacionDuplicada
from catalogo.serializers_reviews import ActualizarCalificacionSerializer
from catalogo.services.tmdb import get_catalog_service
from filmai.errores.sobre import RESERVADOS
from filmai.exceptions import filmai_exception_handler
from filmai.views import custom_500
from listas.exceptions import (
    CalificacionImpideQuitarDeVistas,
    ItemDuplicado,
    ListaPredeterminadaProtegida,
    NombreListaDuplicado,
)
from listas.models import Lista
from listas.serializers import NombreListaSerializer
from usuarios.exceptions import NombreUsuarioOcupado
from usuarios.factories import UsuarioFactory
from usuarios.perfil import CambiarContrasenaSerializer
from usuarios.serializers import (
    GoogleSocialLoginSerializer,
    UsuarioPerfilSerializer,
)

REFERENCIAS = Path(__file__).with_name("tests_golden") / "api"


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class ContratoErroresAPITests(TestCase):
    """Congela HTTP y JSON; no depende de tokens, fechas ni servicios externos."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = UsuarioFactory(
            nombre_usuario="referencia01",
            correo="referencia@filmai.com",
            nombre="Ana",
            apellido="Perez",
            fecha_nacimiento=date(1990, 1, 1),
        )

    def setUp(self):
        # Las vistas pueden resolver el singleton antes de validar parámetros.
        # addCleanup también se ejecuta si un escenario falla.
        get_catalog_service.cache_clear()
        self.addCleanup(get_catalog_service.cache_clear)
        self.client = APIClient()
        self.registro = {
            "correo": "nuevo@filmai.com",
            "nombre_usuario": "referencia02",
            "nombre": "Ana",
            "apellido": "Perez",
            "fecha_nacimiento": "1990-01-01",
            "genero": "no_especifica",
            "pais": "AR",
            "acepta_terminos": True,
            "password1": "Password123!",
            "password2": "Password123!",
        }

    def nombre_lista_duplicado(self):
        """OT-41 conserva el duplicado personalizado, separado del reservado."""
        Lista.objects.create(usuario=self.usuario, nombre="Cine de autor")
        return self.serializar(
            NombreListaSerializer(
                data={"nombre": "Cine de autor"},
                context={"request": SimpleNamespace(user=self.usuario)},
            )
        )

    def referencia(self, nombre, ejecutar):
        with override("es-ar"):
            respuesta = ejecutar(self)
        self.assertFalse(settings.DEBUG)
        if nombre not in {"servidor", "servidor_django"} and not nombre.startswith(
            "tmdb_"
        ):
            self.assertLess(
                respuesta.status_code,
                500,
                "El escenario falló antes de la validación buscada",
            )
        cuerpo = (
            respuesta.data
            if hasattr(respuesta, "data")
            else json.loads(respuesta.content)
        )
        archivo = REFERENCIAS / f"{nombre}.json"
        # OT-82: oráculo por código mientras todavía se emiten ambas formas.
        if isinstance(cuerpo, dict):
            if respuesta.status_code >= 400:
                cuerpo = {
                    clave: valor
                    for clave, valor in cuerpo.items()
                    if clave in RESERVADOS
                }
            else:
                cuerpo = {
                    clave: valor for clave, valor in cuerpo.items() if clave != "detail"
                }
        # Roundtrip elimina ErrorDetail y fuerza la forma JSON que ve el cliente.
        actual = json.loads(
            json.dumps({"status": respuesta.status_code, "body": cuerpo})
        )
        if os.environ.get("REGENERAR_REFERENCIAS_API") == "1":
            REFERENCIAS.mkdir(parents=True, exist_ok=True)
            archivo.write_text(json.dumps(actual, ensure_ascii=False, indent=2) + "\n")
        self.assertTrue(archivo.exists(), f"Falta referencia {archivo.name}")
        self.assertEqual(actual, json.loads(archivo.read_text()))

    def registro_error(self, campo, valor):
        return self.client.post(
            "/api/auth/registration/", {**self.registro, campo: valor}, format="json"
        )

    def serializar(self, serializer):
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            return filmai_exception_handler(exc, {})
        self.fail("El caso debía producir una excepción real")

    def validar_metodo(self, serializer, metodo, valor):
        try:
            getattr(serializer, metodo)(valor)
        except Exception as exc:
            return filmai_exception_handler(exc, {})
        self.fail("La rama defensiva debía rechazar el valor")

    def google(self, caso):
        request = APIRequestFactory().post("/api/auth/google/", {}, format="json")
        view = SimpleNamespace(adapter_class=GoogleOAuth2Adapter)
        datos = {
            "id_token": "token-de-prueba",
            "nombre_usuario": "nuevogoogle",
            "fecha_nacimiento": "1990-01-01",
            "genero": "no_especifica",
            "pais": "AR",
            "acepta_terminos": caso != "sin_terminos",
        }
        if caso == "adapter":
            view = SimpleNamespace()
        if caso == "token":
            datos.pop("id_token")
        if caso == "faltantes":
            datos = {"id_token": "token-de-prueba"}
        usuario = UsuarioFactory(correo="google-nuevo@filmai.com")
        if caso in ("baja", "baja_final"):
            usuario.estado = "baja"
            usuario.save(update_fields=["estado"])
        if caso == "baja":
            SocialAccount.objects.create(user=usuario, provider="google", uid="sub")
        login = Mock()
        login.account = SimpleNamespace(
            provider="google",
            uid="sub",
            user=usuario,
            extra_data={"email_verified": True},
        )
        login.user = SimpleNamespace(correo="google-sin-registrar@filmai.com")
        login.is_existing = caso == "baja_final"
        if caso == "correo":
            login.user = self.usuario
        if caso == "carrera":
            login.save.side_effect = IntegrityError()
        serializer = GoogleSocialLoginSerializer(
            data=datos, context={"request": request, "view": view}
        )
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    GoogleOAuth2Adapter,
                    "get_provider",
                    return_value=SimpleNamespace(
                        app=SocialApp(
                            provider="google",
                            name="Google",
                            client_id="test",
                            secret="test",
                        )
                    ),
                )
            )
            stack.enter_context(
                patch.object(
                    serializer,
                    "get_social_login",
                    side_effect=RequestException() if caso == "verificar" else None,
                    return_value=login,
                )
            )
            stack.enter_context(
                patch(
                    "usuarios.serializers.complete_social_login",
                    side_effect=RequestException() if caso == "completar" else None,
                    return_value=HttpResponseBadRequest(b"Bad Request")
                    if caso == "respuesta"
                    else None,
                )
            )
            return self.serializar(serializer)

    def tmdb(self, caso):
        def transportar(request):
            if caso == "transporte":
                raise httpx.ConnectError("conexion de prueba", request=request)
            if caso == "json":
                return httpx.Response(200, content=b"no-json")
            return httpx.Response(int(caso))

        cliente = TMDBClient(
            api_key="prueba",
            base_url="https://tmdb.invalid",
            transport=httpx.MockTransport(transportar),
        )
        with patch("catalogo.client.time.sleep"), ExitStack() as stack:
            if caso == "presupuesto":
                stack.enter_context(patch("catalogo.client.MAX_RETRIES", -1))
            try:
                cliente.get_movie_detail(1)
            except Exception as exc:
                return filmai_exception_handler(exc, {})
            finally:
                cliente._client.close()
        self.fail("TMDB debía fallar")

    def confirmar(self, caso):
        email = EmailAddress.objects.create(
            user=self.usuario, email=self.usuario.correo, verified=caso == "confirmada"
        )
        key = EmailConfirmationHMAC(email).key
        if caso == "invalida":
            key = "invalida"
        if caso == "inexistente":
            key = signing.dumps(999999, salt=app_settings.SALT)
        if caso == "expirada":
            with patch("django.core.signing.time.time", return_value=0):
                key = signing.dumps(email.pk, salt=app_settings.SALT)
        return self.client.post(
            "/api/auth/registration/verify-email/", {"key": key}, format="json"
        )


# Cada entrada explica qué rama cubre; se ejecuta como test independiente.
CASOS = {}


def caso(nombre, descripcion, ejecutar):
    CASOS[nombre] = descripcion

    def test(self):
        self.referencia(nombre, ejecutar)

    test.__doc__ = descripcion
    setattr(ContratoErroresAPITests, f"test_{nombre}", test)


for nombre, exc in [
    ("autenticacion_requerida", NotAuthenticated()),
    ("credenciales_invalidas", AuthenticationFailed()),
    ("permisos", PermissionDenied()),
    ("recurso_inexistente", Http404()),
    ("metodo", MethodNotAllowed("GET")),
    ("limite_solicitudes", Throttled(wait=42)),
    ("servidor", RuntimeError("detalle interno que no debe exponerse")),
    ("usuario_ocupado", NombreUsuarioOcupado()),
    ("lista_duplicada", NombreListaDuplicado()),
    ("item_duplicado", ItemDuplicado()),
    ("lista_protegida", ListaPredeterminadaProtegida()),
    ("calificacion_bloquea_quitar", CalificacionImpideQuitarDeVistas()),
    ("calificacion_duplicada", CalificacionDuplicada()),
]:
    caso(
        nombre,
        f"Manejador real: {nombre}; conserva estado y cuerpo de la excepción de producción.",
        lambda self, exc=exc: filmai_exception_handler(exc, {}),
    )

caso(
    "ruta_inexistente",
    "El 404 de Django usa un texto distinto al 404 de DRF.",
    lambda self: self.client.get("/api/no-existe/"),
)
caso(
    "servidor_django",
    "El handler500 de Django también evita exponer detalles internos.",
    lambda self: custom_500(APIRequestFactory().get("/")),
)
caso(
    "documentacion_staff",
    "Acceso anónimo al esquema ofrece indicaciones para entrar al Admin.",
    lambda self: self.client.get("/api/schema/"),
)

for campo, valores in {
    "correo": [
        ("ocupado", "referencia@filmai.com"),
        ("invalido", "mal"),
        ("vacio", ""),
    ],
    "nombre_usuario": [
        ("ocupado", "referencia01"),
        ("formato", "a!"),
        ("largo", "a" * 26),
    ],
    "nombre": [("formato", "Ana1")],
    "apellido": [("formato", "Perez1")],
    "fecha_nacimiento": [
        ("futura", "2999-01-01"),
        ("menor", "2025-01-01"),
        ("formato", "mal"),
    ],
    "genero": [("invalido", "otro")],
    "pais": [("invalido", "ZZ")],
    "password1": [
        ("largo", "Aa1!"),
        ("mayuscula", "password1!"),
        ("minuscula", "PASSWORD1!"),
        ("digito", "Password!"),
        ("especial", "Password1"),
    ],
    "password2": [("no_coincide", "Different123!")],
}.items():
    for etiqueta, valor in valores:
        caso(
            f"registro_{campo}_{etiqueta}",
            f"Registro: {campo} {etiqueta}; valida el campo mediante HTTP.",
            lambda self, campo=campo, valor=valor: self.registro_error(campo, valor),
        )
caso(
    "registro_obligatorios",
    "DRF identifica los campos requeridos cuando el registro está vacío.",
    lambda self: self.client.post("/api/auth/registration/", {}, format="json"),
)

for nombre, path in {
    "catalogo_entero": "/api/catalogo/trending/?page=abc",
    "catalogo_positivo": "/api/catalogo/trending/?page=0",
    "catalogo_numero": "/api/catalogo/discover/?min_rating=abc",
    "catalogo_finito": "/api/catalogo/discover/?min_rating=nan",
    "catalogo_tipo": "/api/catalogo/discover/?tipo=person",
    "catalogo_query": "/api/catalogo/search/",
    "catalogo_requerido": "/api/catalogo/keywords/",
    "catalogo_id": "/api/catalogo/movie/abc/",
}.items():
    caso(
        nombre,
        f"Parámetro inválido del catálogo: {nombre}; retiene el cuerpo irregular de cadenas.",
        lambda self, path=path: self.client.get(path),
    )
for estado in ["400", "404", "429", "500", "302", "json", "transporte", "presupuesto"]:
    caso(
        f"tmdb_{estado}",
        f"Cliente HTTP real con transporte aislado: {estado}; prueba el mensaje producido por TMDBClient.",
        lambda self, estado=estado: self.tmdb(estado),
    )

for nombre, valor in [
    ("vacio", ""),
    ("largo", "a" * 81),
    ("sin_letras", "!!!"),
    ("caracteres", "Lista!"),
]:
    caso(
        f"lista_nombre_{nombre}",
        f"Validación de nombre {nombre}; invoca la rama del serializer, incluso si DRF la filtra antes.",
        lambda self, valor=valor: self.validar_metodo(
            NombreListaSerializer(), "validate_nombre", valor
        ),
    )
caso(
    "lista_nombre_duplicado",
    "Serializer conserva la regresión de nombres personalizados duplicados.",
    lambda self: self.nombre_lista_duplicado(),
)
caso(
    "resena_actualizacion_vacia",
    "Una actualización vacía produce non_field_errors.",
    lambda self: self.serializar(ActualizarCalificacionSerializer(data={})),
)

for clase in [GoogleSocialLoginSerializer, UsuarioPerfilSerializer]:
    for metodo, etiqueta, valor in [
        ("validate_nombre_usuario", "ocupado", "referencia01"),
        ("validate_fecha_nacimiento", "futura", date(2999, 1, 1)),
        ("validate_fecha_nacimiento", "menor", date(2025, 1, 1)),
    ]:
        caso(
            f"{clase.__name__}_{etiqueta}",
            f"{clase.__name__}: {metodo} {etiqueta}; caracteriza también validadores de campos de solo lectura.",
            lambda self, clase=clase, metodo=metodo, valor=valor: self.validar_metodo(
                clase(
                    instance=UsuarioFactory()
                    if clase is UsuarioPerfilSerializer
                    else self.usuario
                ),
                metodo,
                valor,
            ),
        )
caso(
    "perfil_nombre",
    "Perfil rechaza nombres con números.",
    lambda self: self.validar_metodo(
        UsuarioPerfilSerializer(), "validate_nombre", "Ana1"
    ),
)
caso(
    "perfil_avatar",
    "Avatar fuera del catálogo produce el listado real de IDs permitidos.",
    lambda self: self.validar_metodo(
        UsuarioPerfilSerializer(), "validate_avatar_id", -1
    ),
)
caso(
    "google_nombre_formato",
    "Google usa la misma regla alfanumérica que el registro.",
    lambda self: self.validar_metodo(
        GoogleSocialLoginSerializer(), "validate_nombre_usuario", "a!"
    ),
)
for nombre in [
    "adapter",
    "token",
    "verificar",
    "faltantes",
    "correo",
    "completar",
    "respuesta",
    "carrera",
    "baja",
    "baja_final",
]:
    caso(
        f"google_{nombre}",
        f"Google: {nombre}; sustituye la infraestructura OAuth, conserva la validación y el mensaje reales.",
        lambda self, nombre=nombre: self.google(nombre),
    )

for nombre in ["invalida", "inexistente", "confirmada", "expirada"]:
    caso(
        f"confirmacion_{nombre}",
        f"Confirmación {nombre}: el endpoint devuelve solo codigo.",
        lambda self, nombre=nombre: self.confirmar(nombre),
    )
caso(
    "restablecimiento_enlace",
    "Restablecimiento con uid inválido devuelve codigo sin texto.",
    lambda self: self.client.post(
        "/api/auth/password/reset/confirm/",
        {
            "uid": "mal",
            "token": "mal",
            "password1": "Password123!",
            "password2": "Password123!",
        },
        format="json",
    ),
)
caso(
    "restablecimiento_no_coincide",
    "Las contraseñas se comparan antes de comprobar el enlace.",
    lambda self: self.client.post(
        "/api/auth/password/reset/confirm/",
        {
            "uid": "mal",
            "token": "mal",
            "password1": "Password123!",
            "password2": "Different123!",
        },
        format="json",
    ),
)
caso(
    "login_incorrecto",
    "dj-rest-auth devuelve su validación de credenciales, distinta del 401 global.",
    lambda self: self.client.post(
        "/api/auth/login/",
        {"email": "no-existe@filmai.com", "password": "Password123!"},
        format="json",
    ),
)

for nombre in ["sin_local", "actual_incorrecta", "no_coincide", "complejidad"]:

    def cambiar(self, nombre=nombre):
        usuario = self.usuario
        if nombre == "sin_local":
            usuario.set_unusable_password()
        datos = {
            "old_password": "Password123!",
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        }
        if nombre == "actual_incorrecta":
            datos["old_password"] = "incorrecta"
        if nombre == "no_coincide":
            datos["password2"] = "Different123!"
        if nombre == "complejidad":
            datos["password1"] = datos["password2"] = "password1!"
        return self.serializar(
            CambiarContrasenaSerializer(data=datos, context={"usuario": usuario})
        )

    caso(
        f"cambio_{nombre}",
        f"Cambio autenticado {nombre}; conserva errores de campo como cadena o lista.",
        cambiar,
    )

caso(
    "recuperacion_respuesta",
    "Recuperación conserva texto en respuesta exitosa sin revelar si existe el correo.",
    lambda self: self.client.post(
        "/api/auth/password/reset/", {"email": "no-existe@filmai.com"}, format="json"
    ),
)


def sesion_y_accion(self, accion):
    login = self.client.post(
        "/api/auth/login/",
        {"email": self.usuario.correo, "password": "Password123!"},
        format="json",
    )
    self.assertEqual(login.status_code, 200)
    if accion == "baja":
        return self.client.post("/api/account/deactivate/", {}, format="json")
    return self.client.post(
        "/api/profile/change-password/",
        {
            "old_password": "Password123!",
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        format="json",
    )


for accion in ["baja", "contrasena"]:
    caso(
        f"exito_{accion}",
        f"Texto exitoso {accion}: usa una sesión JWT real y captura la respuesta final.",
        lambda self, accion=accion: sesion_y_accion(self, accion),
    )


def restablecer_exito(self):
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import user_pk_to_url_str

    return self.client.post(
        "/api/auth/password/reset/confirm/",
        {
            "uid": user_pk_to_url_str(self.usuario),
            "token": default_token_generator.make_token(self.usuario),
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        format="json",
    )


caso(
    "restablecimiento_exito",
    "Restablecimiento válido captura el texto exitoso y no los tokens variables del enlace.",
    restablecer_exito,
)
