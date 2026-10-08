"""Rutas de validación, metadatos y compatibilidad independientes del manejador."""

from django.test import SimpleTestCase
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ValidationError

from filmai.errores.sobre import conservar_legacy, construir_sobre, entradas_validacion
from filmai.errores.validacion import ErrorValidacion


class SobreErroresTests(SimpleTestCase):
    def test_validacion_anidada_conserva_hojas_orden_campos_y_parametros(self):
        """Los errores generales anidados pertenecen al elemento y los de nombre al campo."""
        error = ErrorValidacion(
            {
                "items": [
                    {
                        "nombre": [
                            ErrorDetail("Largo", "max_length"),
                            ErrorDetail("Vacío", "blank"),
                        ],
                        "non_field_errors": [
                            ErrorDetail("Faltan cambios", "review_update_empty")
                        ],
                    }
                ],
                "non_field_errors": [ErrorDetail("General", "invalid")],
            },
            parametros_por_ruta={("items", 0, "nombre", 0): {"maxLength": 25}},
        )
        self.assertEqual(
            entradas_validacion(error),
            [
                {
                    "field": "items.0.nombre",
                    "code": "max_length",
                    "params": {"maxLength": 25},
                },
                {"field": "items.0.nombre", "code": "blank", "params": {}},
                {"field": "items.0", "code": "review_update_empty", "params": {}},
                {"field": None, "code": "invalid", "params": {}},
            ],
        )

    def test_lista_raiz_preserva_contenido_y_usa_campos_nulos(self):
        """Los mensajes generales en una lista sobreviven como non_field_errors."""
        error = ValidationError(["Primero", "Segundo"])
        entradas = entradas_validacion(error)
        self.assertEqual([entrada["field"] for entrada in entradas], [None, None])
        sobre = construir_sobre("validation_error", 400, errores=entradas)
        cuerpo = conservar_legacy(error.detail, sobre)
        self.assertEqual(cuerpo["non_field_errors"], ["Primero", "Segundo"])
        self.assertEqual(len(cuerpo["errors"]), 2)

    def test_debug_solo_aparece_cuando_se_habilita_y_no_modifica_el_contrato(self):
        """El mismo error conserva código, estado esperado y parámetros sin debug público."""
        publico = construir_sobre("server_error", 500)
        interno = construir_sobre(
            "server_error", 500, debug=True, mensaje="Diagnóstico"
        )
        self.assertNotIn("debug", publico)
        self.assertEqual(interno.pop("debug"), {"message": "Diagnóstico"})
        self.assertEqual(interno, publico)

    def test_legacy_no_pierde_claves_y_rechaza_nombres_reservados(self):
        """detail/codigo se conservan; code no puede sobrescribir un campo del request."""
        anterior = {"codigo": "nombre_lista_duplicado", "detail": "Duplicada"}
        sobre = construir_sobre("list_name_duplicated", 409)
        nuevo = conservar_legacy(anterior, sobre)
        self.assertEqual({clave: nuevo[clave] for clave in anterior}, anterior)
        self.assertEqual(
            anterior, {"codigo": "nombre_lista_duplicado", "detail": "Duplicada"}
        )
        for reservado in ("code", "params", "errors", "debug"):
            with self.subTest(campo=reservado), self.assertRaises(ValueError):
                conservar_legacy({reservado: "texto"}, sobre)

    def test_codigos_y_estados_invalidos_no_forman_un_sobre(self):
        """La validación pura rechaza unknown, HTTP ajeno y hojas en errores generales."""
        for codigo, estado, errores in (
            ("inventado", 400, []),
            ("server_error", 400, []),
            ("not_found", 404, [{"field": None, "code": "invalid", "params": {}}]),
            (
                "validation_error",
                400,
                [{"field": None, "code": "server_error", "params": {}}],
            ),
        ):
            with self.subTest(codigo=codigo), self.assertRaises(ValueError):
                construir_sobre(codigo, estado, errores=errores)
        with self.assertRaises(ValueError):
            entradas_validacion(ValidationError("Texto", code="inventado"))
        self.assertEqual(
            entradas_validacion(
                ValidationError("Texto", code="inventado"), estricto=False
            )[0]["code"],
            "invalid",
        )

    def test_normalizacion_de_aliases_drf_depende_del_codigo_y_no_del_mensaje(self):
        """Mensajes arbitrarios producen el mismo código público para aliases registrados."""
        for alias in ("max_string_length", "overflow", "datetime"):
            with self.subTest(alias=alias):
                error = ValidationError("Texto arbitrario", code=alias)
                self.assertEqual(entradas_validacion(error)[0]["code"], "invalid")

    def test_metadata_se_adjunta_despues_de_la_frontera_real_del_serializer(self):
        """El límite se recupera de configuración al crear la excepción final, no de texto."""

        class Datos(serializers.Serializer):
            nombre = serializers.CharField(max_length=3)

        serializer = Datos(data={"nombre": "Demasiado"})
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
        error = ErrorValidacion(
            serializer.errors,
            parametros_por_ruta={
                ("nombre", 0): {"maxLength": serializer.fields["nombre"].max_length}
            },
        )
        self.assertEqual(
            entradas_validacion(error),
            [{"field": "nombre", "code": "max_length", "params": {"maxLength": 3}}],
        )
