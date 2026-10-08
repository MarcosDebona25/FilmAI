"""Emisión doble en la frontera real del manejador, sin modificar endpoints."""

from types import SimpleNamespace

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.test import APIClient
from rest_framework.views import exception_handler as drf_exception_handler

from catalogo.exceptions import TMDBNotFound
from filmai.errores.base import ExcepcionAPI
from filmai.errores.catalogo import CATALOGO
from filmai.errores.validacion import ErrorValidacion
from filmai.exceptions import filmai_exception_handler
from listas.exceptions import NombreListaDuplicado


@override_settings(DEBUG=False)
class ManejadorSobreTests(SimpleTestCase):
    def test_excepciones_generales_conservan_http_detail_y_codigos_tipados(self):
        """Cada clase pública conocida agrega el sobre con errores vacíos."""
        for excepcion, estado, codigo in (
            (NotAuthenticated(), 401, "not_authenticated"),
            (AuthenticationFailed(), 401, "invalid_credentials"),
            (PermissionDenied(), 403, "permission_denied"),
            (Http404(), 404, "not_found"),
            (MethodNotAllowed("GET"), 405, "method_not_allowed"),
            (Throttled(wait=42), 429, "throttled"),
            (NombreListaDuplicado(), 409, "list_name_duplicated"),
        ):
            with self.subTest(codigo=codigo):
                response = filmai_exception_handler(excepcion, {})
                self.assertEqual(response.status_code, estado)
                self.assertIn("detail", response.data)
                self.assertEqual(response.data["code"], codigo)
                self.assertEqual(response.data["errors"], [])
                self.assertNotIn("debug", response.data)
        response = filmai_exception_handler(NombreListaDuplicado(), {})
        self.assertEqual(response.data["codigo"], "nombre_lista_duplicado")
        response = filmai_exception_handler(Throttled(wait=42), {})
        self.assertEqual(response["Retry-After"], "42")

    def test_validacion_conserva_formas_legacy_y_parametros_por_hoja(self):
        """El serializer conserva sus listas y el portador final agrega límites."""
        error = ErrorValidacion(
            {"nombre": ["Largo"]},
            "max_length",
            parametros_por_ruta={("nombre", 0): {"maxLength": 25}},
        )
        response = filmai_exception_handler(error, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["nombre"], ["Largo"])
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [{"field": "nombre", "code": "max_length", "params": {"maxLength": 25}}],
        )
        response = filmai_exception_handler(ValidationError(["General"]), {})
        self.assertEqual(response.data["non_field_errors"], ["General"])
        self.assertIsNone(response.data["errors"][0]["field"])

    def test_excepcion_base_y_metodo_reciben_parametros_sin_parsear_texto(self):
        """Los parámetros salen del error tipado o request, nunca de detail."""
        error = ExcepcionAPI("throttled", parametros={"retry_after_seconds": 0})
        response = filmai_exception_handler(error, {})
        self.assertEqual(response.data["params"], {"retry_after_seconds": 0})
        response = filmai_exception_handler(
            MethodNotAllowed("GET"), {"request": SimpleNamespace(method="GET")}
        )
        self.assertEqual(response.data["params"], {"method": "GET"})
        response = filmai_exception_handler(
            UnsupportedMediaType("application/xml"),
            {"request": SimpleNamespace(content_type="application/xml")},
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.data["params"], {"mediaType": "application/xml"})

    def test_fallo_inesperado_no_expone_diagnostico_y_debug_es_condicional(self):
        """Un fallo real entrega server_error, ocultando diagnóstico fuera de DEBUG."""
        with self.assertLogs("filmai.exceptions", level="ERROR"):
            publico = filmai_exception_handler(RuntimeError("diagnóstico interno"), {})
        self.assertEqual(publico.status_code, 500)
        self.assertEqual(publico.data["detail"], "Error interno del servidor.")
        self.assertEqual(publico.data["code"], "server_error")
        self.assertNotIn("debug", publico.data)
        with (
            override_settings(DEBUG=True),
            self.assertLogs("filmai.exceptions", level="ERROR"),
        ):
            interno = filmai_exception_handler(RuntimeError("diagnóstico interno"), {})
        self.assertEqual(interno.data["debug"], {"message": "diagnóstico interno"})
        self.assertEqual(interno.data["code"], publico.data["code"])

    def test_permission_denied_django_conserva_403_y_detail_en_ambos_modos(self):
        """El permiso Django que DRF reconoce no se transforma en fallo inesperado."""
        for debug in (False, True):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                error = DjangoPermissionDenied("Restricción interna")
                heredada = drf_exception_handler(error, {})
                response = filmai_exception_handler(error, {})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.data["detail"], heredada.data["detail"])
                self.assertEqual(response.data["code"], "permission_denied")
                self.assertEqual(response.data["errors"], [])
                self.assertEqual("debug" in response.data, debug)

    def test_tmdb_conserva_retorno_heredado_hasta_su_orden(self):
        """OT-30 preserva el alcance TMDB y la regresión anterior al plan."""
        response = filmai_exception_handler(TMDBNotFound("No encontrada"), {})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"detail": "No encontrada"})


@override_settings(DEBUG=False)
class EndpointSobreTests(TestCase):
    def test_login_inactivo_agrega_sobre_sin_cambiar_el_estado_de_f0(self):
        """El HTTP real de F0 tiene sobre; el resguardo de estados llegará en OT-33."""
        from usuarios.factories import UsuarioFactory
        from usuarios.models import EstadoCuenta

        usuario = UsuarioFactory(estado=EstadoCuenta.BAJA)
        response = APIClient().post(
            "/api/auth/login/",
            {"email": usuario.correo, "password": "Password123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(response.json()["code"], CATALOGO)
        self.assertEqual(response.json()["params"], {})
        self.assertEqual(response.json()["errors"], [])
        self.assertNotIn("debug", response.json())
