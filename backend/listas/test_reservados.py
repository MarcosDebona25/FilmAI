"""Reservas por idioma y contrato exportado, sin traducir nombres del usuario."""

import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from filmai.errores.catalogo import obtener_codigo
from listas.identidades import NOMBRES_RESERVADOS, contrato_enums
from listas.models import ClaveLista, Lista
from usuarios.factories import UsuarioFactory


class NombresReservadosTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)

    def test_creacion_y_renombrado_reservan_ambos_idiomas_con_el_mismo_codigo(self):
        personalizada = Lista.objects.create(
            usuario=self.usuario, nombre="Mi colección"
        )
        for idioma in ("en", "es"):
            for nombres in NOMBRES_RESERVADOS.values():
                for nombre in nombres:
                    with self.subTest(idioma=idioma, nombre=nombre):
                        datos = {"nombre": f"  {nombre.upper()}  "}
                        for respuesta in (
                            self.cliente.post(
                                "/api/lists/",
                                datos,
                                format="json",
                                HTTP_ACCEPT_LANGUAGE=idioma,
                            ),
                            self.cliente.put(
                                f"/api/lists/{personalizada.pk}/",
                                datos,
                                format="json",
                                HTTP_ACCEPT_LANGUAGE=idioma,
                            ),
                        ):
                            self.assertEqual(respuesta.status_code, 409)
                            self.assertEqual(
                                respuesta.data["code"], "list_name_reserved"
                            )
                            self.assertEqual(respuesta.data["params"], {})
                            self.assertEqual(respuesta.data["errors"], [])
        personalizada.refresh_from_db()
        self.assertEqual(personalizada.nombre, "Mi colección")

    def test_reserva_persiste_aunque_la_predeterminada_haya_sido_renombrada(self):
        self.usuario.listas.filter(clave=ClaveLista.FAVORITOS).update(
            nombre="Otra favorita"
        )

        respuesta = self.cliente.post(
            "/api/lists/", {"nombre": "Favoritos"}, format="json"
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["code"], "list_name_reserved")

    def test_listado_conserva_nombre_personalizado_anterior_sin_traducirlo(self):
        personalizada = Lista.objects.create(usuario=self.usuario, nombre="Watchlist")

        respuesta = self.cliente.get("/api/lists/")

        fila = next(
            lista for lista in respuesta.data if lista["id"] == personalizada.pk
        )
        self.assertEqual(fila["nombre"], "Watchlist")
        self.assertIsNone(fila["clave"])


class ContratoEnumsTests(SimpleTestCase):
    def test_exportacion_reproducible_coincide_con_el_contrato_versionado(self):
        esperado = contrato_enums()
        versionado = Path(settings.BASE_DIR).parent / "contracts" / "enums.json"
        self.assertEqual(json.loads(versionado.read_text()), esperado)
        with TemporaryDirectory() as carpeta:
            salida = Path(carpeta) / "enums.json"
            call_command("exportar_enums", "--salida", str(salida))
            self.assertEqual(json.loads(salida.read_text()), esperado)

    def test_reservas_coinciden_con_las_etiquetas_editoriales_aprobadas(self):
        archivo = Path(settings.BASE_DIR).parent / "traducciones" / "claves.csv"
        with archivo.open(newline="") as filas:
            etiquetas = {
                fila["clave"]: fila
                for fila in csv.DictReader(filas)
                if fila["clave"].startswith("enums.defaultList.")
            }
        for idioma in ("en", "es"):
            self.assertEqual(
                list(NOMBRES_RESERVADOS[idioma]),
                [
                    etiquetas[f"enums.defaultList.{clave}"][f"{idioma}_curado"]
                    for clave in ClaveLista.values
                ],
            )

    def test_codigo_reservado_tiene_solo_http_409_y_copia_aprobada(self):
        definicion = obtener_codigo("list_name_reserved")
        self.assertEqual(definicion.contextos, {"listas": 409})
        self.assertEqual(definicion.parametros, {})
        archivo = Path(settings.BASE_DIR).parent / "traducciones" / "claves-extra.csv"
        with archivo.open(newline="") as filas:
            fila = next(
                fila
                for fila in csv.DictReader(filas)
                if fila["codigo"] == "list_name_reserved"
            )
        self.assertEqual(fila["estado"], "aprobado")
        self.assertEqual(fila["es"], definicion.mensaje)
        self.assertEqual(fila["en"], "This name is reserved for a default list.")
