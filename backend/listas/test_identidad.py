"""Las identidades de las listas no dependen de sus etiquetas almacenadas."""

from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import ProduccionAudiovisualFactory
from listas.models import ClaveLista, Lista, TipoLista
from usuarios.factories import UsuarioFactory
from usuarios.management.commands.seed import Command
from usuarios.provisioning import provisionar_recursos_por_defecto


class IdentidadListaTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)

    def _renombrar(self):
        nombres = ("ZZ primera", "AA segunda", "Ya vi")
        for clave, nombre in zip(ClaveLista.values, nombres, strict=True):
            self.usuario.listas.filter(clave=clave).update(nombre=nombre)
        return dict(self.usuario.listas.values_list("clave", "nombre"))

    def test_alta_asigna_las_tres_claves_y_personalizadas_exponen_nulo(self):
        self.assertEqual(
            set(self.usuario.listas.values_list("clave", flat=True)),
            set(ClaveLista.values),
        )
        respuesta = self.cliente.post(
            "/api/lists/", {"nombre": "Mi colección"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertIsNone(respuesta.data["clave"])

    def test_resumen_expone_claves_y_ordena_sin_usar_nombres(self):
        nombres = self._renombrar()

        respuesta = self.cliente.get("/api/lists/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            [lista["clave"] for lista in respuesta.data], ClaveLista.values
        )
        self.assertEqual(
            {lista["clave"]: lista["nombre"] for lista in respuesta.data}, nombres
        )

    def test_calificar_bloquea_quitar_y_borrar_nota_quita_de_vistas_renombrada(self):
        self._renombrar()
        produccion = ProduccionAudiovisualFactory()
        vistas = self.usuario.listas.get(clave=ClaveLista.VISTAS)
        with patch("catalogo.reviews.materializar", return_value=produccion):
            respuesta = self.cliente.post(
                "/api/reviews/",
                {"id_tmdb": produccion.id_tmdb, "tipo": "movie", "valor": 8},
                format="json",
            )
        self.assertEqual(respuesta.status_code, 201)
        item = vistas.items.get(produccion=produccion)
        bloqueada = self.cliente.delete(f"/api/lists/{vistas.pk}/items/{item.pk}/")
        self.assertEqual(bloqueada.status_code, 409)

        borrada = self.cliente.delete(f"/api/reviews/{respuesta.data['id']}/")

        self.assertEqual(borrada.status_code, 204)
        self.assertFalse(vistas.items.exists())

    def test_provision_y_auditoria_conservan_listas_renombradas(self):
        nombres = self._renombrar()
        ids = set(self.usuario.listas.values_list("pk", flat=True))
        self.assertEqual(provisionar_recursos_por_defecto(self.usuario), (0, False))
        salida = StringIO()
        call_command("reparar_recursos_usuarios", "--dry-run", stdout=salida)

        self.assertIn("listas 3/3", salida.getvalue())
        self.assertEqual(set(self.usuario.listas.values_list("pk", flat=True)), ids)
        self.assertEqual(
            dict(self.usuario.listas.values_list("clave", "nombre")), nombres
        )

    def test_provision_completa_nulas_heredadas_sin_recrear_filas(self):
        vistas = self.usuario.listas.get(clave=ClaveLista.VISTAS)
        # OT-42 prohíbe predeterminadas sin clave; se quita la restricción solo
        # aquí (el DDL es transaccional y se revierte) para simular datos previos.
        restriccion = next(
            c for c in Lista._meta.constraints if c.name == "ck_lista_tipo_clave"
        )
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        with connection.schema_editor() as editor:
            editor.remove_constraint(Lista, restriccion)
        Lista.objects.filter(pk=vistas.pk).update(clave=None, nombre="VISTAS")

        self.assertEqual(provisionar_recursos_por_defecto(self.usuario), (0, False))

        vistas.refresh_from_db()
        self.assertEqual(vistas.clave, ClaveLista.VISTAS)
        self.assertEqual(vistas.nombre, "VISTAS")
        self.assertEqual(self.usuario.listas.count(), 3)

    def test_semilla_reutiliza_predeterminadas_renombradas_por_clave(self):
        nombres = self._renombrar()
        producciones = ProduccionAudiovisualFactory.create_batch(5)

        Command()._crear_listas([self.usuario], producciones)

        predeterminadas = self.usuario.listas.filter(tipo=TipoLista.PREDETERMINADA)
        self.assertEqual(dict(predeterminadas.values_list("clave", "nombre")), nombres)
        self.assertEqual(
            [
                predeterminadas.get(clave=clave).items.count()
                for clave in ClaveLista.values
            ],
            [4, 5, 3],
        )

    def test_respaldo_no_reasigna_otra_identidad_si_el_nombre_colisiona(self):
        self.usuario.listas.filter(clave=ClaveLista.PENDIENTES).delete()
        self.usuario.listas.filter(clave=ClaveLista.FAVORITOS).update(
            nombre="Pendientes"
        )

        with self.assertRaisesRegex(ValidationError, "otra clave"):
            provisionar_recursos_por_defecto(self.usuario)

        self.assertEqual(self.usuario.listas.count(), 2)
        self.assertEqual(
            self.usuario.listas.get(nombre="Pendientes").clave, ClaveLista.FAVORITOS
        )
