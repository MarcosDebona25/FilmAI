"""Comprueba el cambio de esquema sobre una cuenta creada antes del idioma."""

from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigracionIdiomaTests(TransactionTestCase):
    anterior = ("usuarios", "0006_normalizar_nombres")
    nueva = ("usuarios", "0007_usuario_idioma")

    def test_cuenta_anterior_sigue_nula_y_la_migracion_es_reversible(self):
        """Agregar la columna no decide un idioma ni recrea la cuenta anterior."""
        executor = MigrationExecutor(connection)
        actuales = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([self.anterior])
            UsuarioAnterior = executor.loader.project_state(
                [self.anterior]
            ).apps.get_model("usuarios", "Usuario")
            usuario = UsuarioAnterior.objects.create(
                correo="anterior@example.com",
                nombre_usuario="anterior",
                nombre="Cuenta",
                apellido="Anterior",
                fecha_nacimiento=date(1990, 1, 1),
                genero="no_especifica",
            )
            executor = MigrationExecutor(connection)
            executor.migrate([self.nueva])
            UsuarioNuevo = executor.loader.project_state([self.nueva]).apps.get_model(
                "usuarios", "Usuario"
            )
            cuenta = UsuarioNuevo.objects.get(pk=usuario.pk)
            self.assertIsNone(cuenta.idioma)
            self.assertEqual(cuenta.correo, "anterior@example.com")
            self.assertEqual(cuenta.nombre_usuario, "anterior")

            executor = MigrationExecutor(connection)
            executor.migrate([self.anterior])
            CuentaRevertida = executor.loader.project_state(
                [self.anterior]
            ).apps.get_model("usuarios", "Usuario")
            self.assertEqual(
                CuentaRevertida.objects.get(pk=usuario.pk).correo, cuenta.correo
            )
            self.assertNotIn("idioma", {f.name for f in CuentaRevertida._meta.fields})
        finally:
            MigrationExecutor(connection).migrate(actuales)
