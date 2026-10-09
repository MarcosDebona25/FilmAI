"""OT-34: el contrato exportado es la fuente que consume el frontend."""

import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase

from filmai.errores.catalogo import CATALOGO
from filmai.errores.contrato import contrato_errores, serializar_contrato

ARCHIVO = Path(settings.BASE_DIR).parent / "contracts" / "error-codes.json"


class ContratoCodigosTests(SimpleTestCase):
    def test_archivo_versionado_coincide_con_el_catalogo(self):
        """Compara el contenido completo; se regenera con `exportar_contrato`."""
        self.assertTrue(ARCHIVO.exists(), f"Falta el contrato: {ARCHIVO}")
        self.assertEqual(
            ARCHIVO.read_text(encoding="utf-8"),
            serializar_contrato(),
            "Ejecutá `python manage.py exportar_contrato` y revisá el diff.",
        )

    def test_incluye_cada_codigo_con_categoria_contextos_y_parametros(self):
        contrato = contrato_errores()
        self.assertEqual(set(contrato["codes"]), set(CATALOGO))
        for codigo, entrada in contrato["codes"].items():
            with self.subTest(codigo=codigo):
                self.assertIn(entrada["category"], {"error", "success"})
                self.assertTrue(entrada["contexts"])
                self.assertEqual(entrada["params"], CATALOGO[codigo].parametros)

    def test_no_publica_mensajes_internos(self):
        valores = set()

        def reunir(nodo):
            if isinstance(nodo, dict):
                for clave, valor in nodo.items():
                    valores.add(clave)
                    reunir(valor)
            elif isinstance(nodo, str):
                valores.add(nodo)

        reunir(contrato_errores())
        for definicion in CATALOGO.values():
            self.assertNotIn(definicion.mensaje, valores)

    def test_comando_escribe_el_mismo_contenido(self):
        with TemporaryDirectory() as carpeta:
            salida = Path(carpeta) / "codigos.json"
            call_command("exportar_contrato", salida=salida, stdout=StringIO())
            self.assertEqual(
                json.loads(salida.read_text(encoding="utf-8")), contrato_errores()
            )
