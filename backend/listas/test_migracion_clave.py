"""Ejecuta el esquema y los datos reales de listas.0005 en ambos sentidos."""

from datetime import date
from unittest.mock import patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigracionClaveListaTests(TransactionTestCase):
    anterior = ("listas", "0004_calificadas_en_vistas")
    nueva = ("listas", "0005_lista_clave")

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.hojas = executor.loader.graph.leaf_nodes()
        # Las otras apps quedan en sus hojas actuales, incluido Usuario.idioma.
        self.otras = [nodo for nodo in self.hojas if nodo[0] != "listas"]
        self.addCleanup(self._restaurar_esquema)
        self.apps = self._migrar(self.anterior)
        Usuario = self.apps.get_model("usuarios", "Usuario")
        self.usuario = Usuario.objects.create(
            nombre_usuario="migracion01",
            correo="migracion01@example.com",
            nombre="Ana",
            apellido="Prueba",
            fecha_nacimiento=date(1990, 1, 1),
            genero="no_especifica",
            idioma="es",
        )
        self.otro = Usuario.objects.create(
            nombre_usuario="migracion02",
            correo="migracion02@example.com",
            nombre="Luis",
            apellido="Prueba",
            fecha_nacimiento=date(1990, 1, 1),
            genero="no_especifica",
        )
        Lista = self.apps.get_model("listas", "Lista")
        self.listas = [
            Lista.objects.create(
                usuario=self.usuario, nombre=nombre, tipo="predeterminada"
            )
            for nombre in ("FAVORITOS", "Pendientes", "vistas")
        ]
        self.personalizada = Lista.objects.create(
            usuario=self.otro, nombre="Vistas", tipo="personalizada"
        )
        Produccion = self.apps.get_model("catalogo", "ProduccionAudiovisual")
        produccion = Produccion.objects.create(
            id_tmdb=123456, tipo="pelicula", titulo="Migración"
        )
        Tiene = self.apps.get_model("listas", "Tiene")
        Tiene.objects.create(lista=self.listas[2], produccion=produccion)
        self.filas_originales = self._filas(self.apps)

    def _restaurar_esquema(self):
        MigrationExecutor(connection).migrate(self.hojas)

    def _migrar(self, destino):
        executor = MigrationExecutor(connection)
        objetivos = [*self.otras, destino]
        executor.migrate(objetivos)
        return executor.loader.project_state(objetivos).apps

    @staticmethod
    def _filas(apps):
        Lista = apps.get_model("listas", "Lista")
        Tiene = apps.get_model("listas", "Tiene")
        Usuario = apps.get_model("usuarios", "Usuario")
        return (
            list(
                Lista.objects.order_by("pk").values_list(
                    "pk", "nombre", "tipo", "usuario_id", "activa"
                )
            ),
            list(
                Tiene.objects.order_by("pk").values_list(
                    "pk", "lista_id", "produccion_id", "fecha_agregado"
                )
            ),
            list(Usuario.objects.order_by("pk").values_list("pk", "idioma")),
        )

    def test_asigna_por_tipo_y_nombre_sin_alterar_listas_ni_items(self):
        apps = self._migrar(self.nueva)
        Lista = apps.get_model("listas", "Lista")

        self.assertEqual(
            list(Lista.objects.order_by("pk").values_list("clave", flat=True)),
            ["favoritos", "pendientes", "vistas", None],
        )
        self.assertEqual(self._filas(apps), self.filas_originales)

    def test_reversion_vacia_claves_y_conserva_filas_al_quitar_columna(self):
        self._migrar(self.nueva)
        executor = MigrationExecutor(connection)
        operacion = executor.loader.get_migration(*self.nueva).operations[1]
        revertir = operacion.reverse_code
        claves_revertidas = []

        def observar_reversion(apps, schema_editor):
            revertir(apps, schema_editor)
            Lista = apps.get_model("listas", "Lista")
            claves_revertidas.extend(
                Lista.objects.order_by("pk").values_list("clave", flat=True)
            )

        # Observamos RunPython antes de que AddField quite la columna.
        with patch.object(operacion, "reverse_code", observar_reversion):
            executor.migrate([*self.otras, self.anterior])
        apps = executor.loader.project_state([*self.otras, self.anterior]).apps

        self.assertEqual(claves_revertidas, [None] * 4)
        self.assertEqual(self._filas(apps), self.filas_originales)
        with connection.cursor() as cursor:
            columnas = connection.introspection.get_table_description(cursor, "lista")
        self.assertNotIn("clave", [columna.name for columna in columnas])

    def test_nombre_desconocido_revierte_la_migracion_completa(self):
        Lista = self.apps.get_model("listas", "Lista")
        desconocida = Lista.objects.create(
            usuario=self.otro, nombre="Renombrada", tipo="predeterminada"
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "Renombrada"):
                self._migrar(self.nueva)

            with connection.cursor() as cursor:
                columnas = connection.introspection.get_table_description(
                    cursor, "lista"
                )
            self.assertNotIn("clave", [columna.name for columna in columnas])
            self.assertFalse(
                MigrationExecutor(connection)
                .recorder.migration_qs.filter(app=self.nueva[0], name=self.nueva[1])
                .exists()
            )
            self.assertEqual(Lista.objects.get(pk=desconocida.pk).nombre, "Renombrada")
        finally:
            desconocida.delete()
        self.assertEqual(self._filas(self.apps), self.filas_originales)
