"""`manage.py chatear --golden` con un modelo de mentira: qué muestra y qué no guarda.

El set dorado real se corre a mano contra DeepSeek. Acá se prueba el recorrido con
`ProveedorFalso`, que reproduce un guion de vueltas sin red ni costo.
"""

import itertools
import json
import re
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from chatbot.llm import LlamadaTool, ProveedorFalso
from chatbot.management.commands.chatear import GOLDEN, cargar_golden
from chatbot.models import Mensaje
from chatbot.tools import FUNCIONES
from usuarios.factories import UsuarioFactory

DOS_PREGUNTAS = """
- id: saludo
  mensaje: hola
  rnf6: simple
  espera: Saluda sin tools.
- id: terror
  mensaje: Quiero ver algo de terror
  idioma: en
  rnf6: agregacion
  espera: Solo el género, sin nota_minima.
"""


class ConArchivos:
    def archivo(self, contenido):
        """Escribe `contenido` en un .yaml temporal, que se borra al terminar el test."""
        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta)
        ruta = Path(carpeta) / "golden.yaml"
        ruta.write_text(contenido, encoding="utf-8")
        return ruta


class CargarGoldenTests(ConArchivos, SimpleTestCase):
    def test_el_set_del_repo_es_valido_y_tiene_entre_10_y_20_preguntas(self):
        preguntas = cargar_golden(GOLDEN)

        self.assertGreaterEqual(len(preguntas), 10)
        self.assertLessEqual(len(preguntas), 20)

    def test_el_set_del_repo_cubre_los_casos_pedidos(self):
        ids = {p["id"] for p in cargar_golden(GOLDEN)}

        for caso in (
            "saludo",
            "fuera_de_tema",
            "portugues",
            "inyeccion",
            "para_chicos",
            "como_arrival_mas_liviano",
            "sin_filtros_de_mas",
        ):
            self.assertIn(caso, ids)

    def test_el_idioma_por_defecto_es_espanol(self):
        preguntas = cargar_golden(self.archivo(DOS_PREGUNTAS))

        self.assertEqual([p["idioma"] for p in preguntas], ["es", "en"])

    def test_un_archivo_mal_armado_es_un_error_claro(self):
        casos = {
            "no es lista": "id: saludo",
            "falta espera": "- {id: a, mensaje: hola, rnf6: simple}",
            "rnf6 inválido": "- {id: a, mensaje: hola, rnf6: rapido, espera: x}",
            "idioma inválido": "- {id: a, mensaje: oi, idioma: pt, rnf6: simple, "
            "espera: x}",
            "campo de más": "- {id: a, mensaje: hola, rnf6: simple, espera: x, "
            "tools: []}",
            "id repetido": "- {id: a, mensaje: hola, rnf6: simple, espera: x}\n"
            "- {id: a, mensaje: chau, rnf6: simple, espera: y}",
            "YAML roto": "- [sin cerrar",
        }
        for nombre, contenido in casos.items():
            with self.subTest(nombre), self.assertRaises(CommandError):
                cargar_golden(self.archivo(contenido))

    def test_un_archivo_que_no_existe_es_un_error_claro(self):
        with self.assertRaises(CommandError):
            cargar_golden(self.archivo("x").with_name("no-existe.yaml"))


class ComandoGoldenTests(ConArchivos, TestCase):
    def setUp(self):
        UsuarioFactory(nombre_usuario="juanp")
        # La tool real llamaría a TMDB: la reemplaza una que no busca nada.
        parche = patch.dict(FUNCIONES, {"descubrir": lambda ctx, **_: {}})
        parche.start()
        self.addCleanup(parche.stop)

    def golden(self, guion, contenido=DOS_PREGUNTAS):
        """Corre `--golden` con `guion` y devuelve (stdout, stderr)."""
        salida, errores = StringIO(), StringIO()
        with patch(
            "chatbot.management.commands.chatear.crear_proveedor",
            return_value=ProveedorFalso(guion),
        ):
            call_command(
                "chatear",
                usuario="juanp",
                golden=self.archivo(contenido),
                stdout=salida,
                stderr=errores,
            )
        return salida.getvalue(), errores.getvalue()

    def test_muestra_cada_pregunta_con_su_expectativa_y_su_respuesta(self):
        salida, _ = self.golden([["Hola, che"], ["Probá con Hereditary"]])

        self.assertIn("=== saludo (es, simple)", salida)
        self.assertIn("vos> hola", salida)
        self.assertIn("espera: Saluda sin tools.", salida)
        self.assertIn("Hola, che", salida)
        self.assertIn("=== terror (en, agregacion)", salida)
        self.assertIn("Probá con Hereditary", salida)

    def test_muestra_las_tools_que_pide_el_modelo_con_sus_argumentos(self):
        # Es lo que deja ver si el modelo agrega `nota_minima` sin que se la pidan.
        argumentos = json.dumps({"generos": ["Horror"], "nota_minima": 7})
        guion = [
            ["Hola"],
            [LlamadaTool("1", "descubrir", argumentos)],
            ["No encontré nada"],
        ]

        salida, _ = self.golden(guion)

        self.assertIn(f"[tool: descubrir {argumentos}]", salida)
        self.assertIn("[buscando…]", salida)

    def test_mide_el_primer_texto_y_el_total_de_cada_pregunta(self):
        salida, _ = self.golden([["Hola"], ["Algo"]])

        tiempos = re.findall(r"\[primer texto \d+\.\d s, total \d+\.\d s\]", salida)
        self.assertEqual(len(tiempos), 2)

    def test_cierra_con_un_resumen_contra_rnf6(self):
        salida, _ = self.golden([["Hola"], ["Algo"]])

        resumen = salida.split("Resumen")[1]
        self.assertRegex(resumen, r"saludo\s+\d+\.\d s\s+\d+\.\d s\s+cumple")
        self.assertRegex(resumen, r"terror\s+\d+\.\d s\s+\d+\.\d s\s+cumple")

    def test_un_turno_que_excede_el_limite_figura_en_el_resumen(self):
        # Cada llamada a `perf_counter` avanza 10 s: el saludo tarda más de 5.
        with patch(
            "chatbot.management.commands.chatear.time.perf_counter",
            side_effect=itertools.count(0, 10),
        ):
            salida, _ = self.golden([["Hola"], ["Algo"]])

        resumen = salida.split("Resumen")[1]
        self.assertRegex(resumen, r"saludo\s+.*excede 5 s")

    def test_si_una_pregunta_falla_sigue_con_las_demas(self):
        salida, errores = self.golden([[RuntimeError("503")], ["Algo"]])

        self.assertIn("error del turno", errores)
        self.assertIn("Algo", salida)
        resumen = salida.split("Resumen")[1]
        self.assertRegex(resumen, r"saludo\s+—\s+—\s+error")
        self.assertRegex(resumen, r"terror\s+.*cumple")

    def test_no_guarda_ningun_turno(self):
        self.golden([["Hola"], ["Algo"]])

        self.assertEqual(Mensaje.objects.count(), 0)

    def test_no_se_combina_con_mensaje(self):
        with self.assertRaises(CommandError):
            call_command(
                "chatear",
                usuario="juanp",
                golden=self.archivo(DOS_PREGUNTAS),
                mensaje="x",
            )
