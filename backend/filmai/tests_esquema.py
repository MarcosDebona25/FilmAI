"""El contrato OpenAPI versionado debe reflejar el generador de Django."""

import os
from io import StringIO
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase


class EsquemaContratoTests(SimpleTestCase):
    def test_esquema_coincide_con_contrato_versionado(self):
        """Detecta cambios semánticos, sin depender del formato del YAML."""
        salida = StringIO()
        call_command("spectacular", stdout=salida, stderr=StringIO())
        archivo = Path(settings.BASE_DIR).parent / "contracts" / "openapi.yaml"
        if os.environ.get("FILMAI_ACTUALIZAR_REFERENCIAS") == "1":
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_text(salida.getvalue(), encoding="utf-8")
        self.assertTrue(archivo.exists(), f"Falta el contrato: {archivo}")
        self.assertEqual(
            yaml.safe_load(salida.getvalue()),
            yaml.safe_load(archivo.read_text(encoding="utf-8")),
        )
