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


class EsquemaDelChatTests(SimpleTestCase):
    """La ruta `messages/` tiene dos métodos; que el POST no haga perder al GET."""

    def esquema(self):
        salida = StringIO()
        call_command("spectacular", stdout=salida, stderr=StringIO())
        return yaml.safe_load(salida.getvalue())["paths"]["/api/chat/messages/"]

    def test_tiene_el_historial_y_el_envio(self):
        ruta = self.esquema()

        self.assertEqual(set(ruta), {"get", "post"})
        # El GET sigue paginado por cursor.
        self.assertIn("cursor", [p["name"] for p in ruta["get"]["parameters"]])

    def test_el_post_declara_el_stream_y_los_rechazos_previos(self):
        post = self.esquema()["post"]

        self.assertEqual(
            list(post["responses"]["200"]["content"]), ["text/event-stream"]
        )
        for codigo in ("400", "401", "403", "409", "429"):
            with self.subTest(codigo=codigo):
                contenido = post["responses"][codigo]["content"]["application/json"]
                self.assertEqual(
                    contenido["schema"], {"$ref": "#/components/schemas/ErrorEnvelope"}
                )
        self.assertEqual(list(post["requestBody"]["content"]), ["application/json"])
