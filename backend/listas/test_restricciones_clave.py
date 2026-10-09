"""OT-42: la base impide claves repetidas o incoherentes con el tipo de lista."""

from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from usuarios.factories import UsuarioFactory

from .models import ClaveLista, Lista, TipoLista


class RestriccionesClaveTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()  # la señal crea las tres predeterminadas

    def _rechaza(self, **datos):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Lista.objects.create(usuario=self.usuario, **datos)

    def test_cada_usuario_tiene_tres_claves_distintas(self):
        self.assertCountEqual(
            self.usuario.listas.values_list("clave", flat=True), ClaveLista.values
        )

    def test_no_admite_dos_listas_con_la_misma_clave_por_usuario(self):
        self._rechaza(
            nombre="Otra",
            tipo=TipoLista.PREDETERMINADA,
            clave=ClaveLista.VISTAS,
        )

    def test_la_misma_clave_puede_existir_en_otro_usuario(self):
        otro = UsuarioFactory()
        self.assertEqual(otro.listas.filter(clave=ClaveLista.VISTAS).count(), 1)

    def test_predeterminada_exige_clave(self):
        self._rechaza(nombre="Sin clave", tipo=TipoLista.PREDETERMINADA)

    def test_personalizada_no_admite_clave(self):
        self._rechaza(
            nombre="Con clave", tipo=TipoLista.PERSONALIZADA, clave=ClaveLista.VISTAS
        )

    def test_renombrar_no_toca_la_identidad(self):
        vistas = self.usuario.listas.get(clave=ClaveLista.VISTAS)
        vistas.nombre = "Mis vistas"
        vistas.save()
        vistas.refresh_from_db()
        self.assertEqual(vistas.clave, ClaveLista.VISTAS)


class MigracionRestriccionesTests(TransactionTestCase):
    anterior = ("listas", "0005_lista_clave")
    nueva = ("listas", "0006_lista_restricciones_clave")

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.hojas = executor.loader.graph.leaf_nodes()
        self.otras = [nodo for nodo in self.hojas if nodo[0] != "listas"]
        self.apps = self._migrar(self.anterior)
        self.addCleanup(self._restaurar_esquema)
        Usuario = self.apps.get_model("usuarios", "Usuario")
        self.usuario = Usuario.objects.create(
            nombre_usuario="restr01",
            correo="restr01@example.com",
            nombre="Ana",
            apellido="Prueba",
            fecha_nacimiento=date(1990, 1, 1),
            genero="no_especifica",
        )
        self.Lista = self.apps.get_model("listas", "Lista")

    def _restaurar_esquema(self):
        # Una migración fallida deja datos que impedirían volver a las hojas.
        self.apps.get_model("listas", "Lista").objects.all().delete()
        MigrationExecutor(connection).migrate(self.hojas)

    def _migrar(self, destino):
        executor = MigrationExecutor(connection)
        objetivos = [*self.otras, destino]
        executor.migrate(objetivos)
        return executor.loader.project_state(objetivos).apps

    @staticmethod
    def _restricciones():
        with connection.cursor() as cursor:
            return set(connection.introspection.get_constraints(cursor, "lista"))

    def test_datos_correctos_agregan_ambas_restricciones_y_se_pueden_revertir(self):
        for clave in ClaveLista.values:
            self.Lista.objects.create(
                usuario=self.usuario, nombre=clave, tipo="predeterminada", clave=clave
            )
        self.Lista.objects.create(usuario=self.usuario, nombre="Mía")
        self._migrar(self.nueva)
        self.assertLessEqual(
            {"uq_lista_usuario_clave", "ck_lista_tipo_clave"}, self._restricciones()
        )
        apps = self._migrar(self.anterior)
        self.assertEqual(apps.get_model("listas", "Lista").objects.count(), 4)
        self.assertFalse(
            {"uq_lista_usuario_clave", "ck_lista_tipo_clave"} & self._restricciones()
        )

    def test_predeterminada_sin_clave_detiene_la_migracion_con_su_identificador(self):
        lista = self.Lista.objects.create(
            usuario=self.usuario, nombre="Vistas", tipo="predeterminada"
        )
        with self.assertRaisesRegex(
            RuntimeError, rf"\({lista.pk}, {self.usuario.pk}\)"
        ):
            self._migrar(self.nueva)
        self.assertFalse(
            {"uq_lista_usuario_clave", "ck_lista_tipo_clave"} & self._restricciones()
        )

    def test_claves_repetidas_detienen_la_migracion(self):
        for nombre in ("Vistas", "Vistas 2"):
            self.Lista.objects.create(
                usuario=self.usuario,
                nombre=nombre,
                tipo="predeterminada",
                clave="vistas",
            )
        with self.assertRaisesRegex(RuntimeError, "claves repetidas"):
            self._migrar(self.nueva)

    def test_personalizada_con_clave_detiene_la_migracion(self):
        self.Lista.objects.create(usuario=self.usuario, nombre="X", clave="vistas")
        with self.assertRaisesRegex(RuntimeError, "personalizadas con clave"):
            self._migrar(self.nueva)
