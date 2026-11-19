"""`listas.0009`: crea «Viendo» y deja a cada título en un solo estado (PR 4).

Como en `MigracionCalificadasEnVistasTests`, las funciones se prueban con los
modelos actuales (`django.apps.apps`) y no migrando la base de ida y vuelta: es
la misma consulta y mucho más rápida. Lo que importa es el efecto sobre los datos.
"""

from datetime import timedelta
from importlib import import_module

from django.apps import apps
from django.test import TestCase
from django.utils import timezone

from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.models import Calificacion
from listas.factories import ListaFactory
from listas.models import Lista, Tiene
from usuarios.factories import UsuarioFactory

# El nombre empieza con un dígito: no se puede importar con `import` normal.
_MIGRACION = import_module("listas.migrations.0009_lista_viendo")


class _Base(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        self.produccion = ProduccionAudiovisualFactory()

    def lista(self, clave, usuario=None):
        return (usuario or self.usuario).listas.get(clave=clave)

    def en(self, clave, produccion=None, usuario=None):
        return Tiene.objects.filter(
            lista=self.lista(clave, usuario), produccion=produccion or self.produccion
        ).exists()

    def agregar(self, clave, produccion=None, hace_dias=0):
        item = Tiene.objects.create(
            lista=self.lista(clave), produccion=produccion or self.produccion
        )
        # `fecha_agregado` es `auto_now_add`: se fija después con un update.
        Tiene.objects.filter(pk=item.pk).update(
            fecha_agregado=timezone.now() - timedelta(days=hace_dias)
        )
        return item


class CrearListaViendoTests(_Base):
    def test_la_crea_en_las_cuentas_que_no_la_tienen(self):
        Lista.objects.filter(clave="viendo").delete()

        _MIGRACION.crear_listas_viendo(apps, None)

        viendo = self.lista("viendo")
        self.assertEqual(viendo.nombre, "Viendo")
        self.assertEqual(viendo.tipo, "predeterminada")
        self.assertTrue(viendo.activa)

    def test_no_duplica_ni_toca_la_que_ya_existe(self):
        antes = self.lista("viendo")
        Tiene.objects.create(lista=antes, produccion=self.produccion)

        _MIGRACION.crear_listas_viendo(apps, None)

        self.assertEqual(self.usuario.listas.filter(clave="viendo").count(), 1)
        self.assertEqual(self.lista("viendo").pk, antes.pk)
        self.assertTrue(self.en("viendo"))

    def test_lo_hace_para_todas_las_cuentas(self):
        otro = UsuarioFactory()
        Lista.objects.filter(clave="viendo").delete()

        _MIGRACION.crear_listas_viendo(apps, None)

        self.assertTrue(otro.listas.filter(clave="viendo").exists())
        self.assertTrue(self.usuario.listas.filter(clave="viendo").exists())

    def test_una_personalizada_que_se_llama_viendo_se_renombra_y_conserva_sus_items(
        self,
    ):
        # `uq_lista_usuario_nombre` no distingue mayúsculas: sin renombrarla, la
        # migración chocaría con quien ya tenía una lista «viendo» o «Viendo».
        Lista.objects.filter(clave="viendo").delete()
        propia = ListaFactory(usuario=self.usuario, nombre="viendo")
        Tiene.objects.create(lista=propia, produccion=self.produccion)
        ListaFactory(usuario=self.usuario, nombre="Viendo 2")

        _MIGRACION.crear_listas_viendo(apps, None)

        propia.refresh_from_db()
        self.assertEqual(propia.nombre, "Viendo 3")
        self.assertEqual(propia.tipo, "personalizada")
        self.assertTrue(propia.items.filter(produccion=self.produccion).exists())
        self.assertEqual(self.lista("viendo").nombre, "Viendo")

    def test_una_personalizada_que_se_llama_watching_tambien_se_renombra(self):
        # «Watching» es el nombre reservado en inglés: una propia que ya lo usaba
        # quedaría duplicada con la predeterminada «Viendo» traducida.
        Lista.objects.filter(clave="viendo").delete()
        propia = ListaFactory(usuario=self.usuario, nombre="watching")
        Tiene.objects.create(lista=propia, produccion=self.produccion)

        _MIGRACION.crear_listas_viendo(apps, None)

        propia.refresh_from_db()
        self.assertEqual(propia.nombre, "Watching 2")
        self.assertEqual(propia.tipo, "personalizada")
        self.assertTrue(propia.items.filter(produccion=self.produccion).exists())
        self.assertEqual(self.lista("viendo").nombre, "Viendo")

    def test_con_viendo_y_watching_propias_renombra_las_dos(self):
        Lista.objects.filter(clave="viendo").delete()
        en_espanol = ListaFactory(usuario=self.usuario, nombre="Viendo")
        en_ingles = ListaFactory(usuario=self.usuario, nombre="Watching")
        ListaFactory(usuario=self.usuario, nombre="Watching 2")

        _MIGRACION.crear_listas_viendo(apps, None)

        en_espanol.refresh_from_db()
        en_ingles.refresh_from_db()
        self.assertEqual(en_espanol.nombre, "Viendo 2")
        self.assertEqual(en_ingles.nombre, "Watching 3")

    def test_no_toca_las_listas_con_otro_nombre(self):
        Lista.objects.filter(clave="viendo").delete()
        otra = ListaFactory(usuario=self.usuario, nombre="Watching later")

        _MIGRACION.crear_listas_viendo(apps, None)

        otra.refresh_from_db()
        self.assertEqual(otra.nombre, "Watching later")


class CalificadasEnVistasTests(_Base):
    def calificar(self, produccion=None, usuario=None, activa=True):
        return Calificacion.objects.create(
            usuario=usuario or self.usuario,
            produccion=produccion or self.produccion,
            valor=8,
            activa=activa,
        )

    def test_una_calificada_sin_estado_pasa_a_vistas(self):
        self.calificar()

        _MIGRACION.calificadas_a_vistas(apps, None)

        self.assertTrue(self.en("vistas"))

    def test_una_calificada_con_estado_no_se_mueve(self):
        self.calificar()
        for clave in ("pendientes", "viendo"):
            with self.subTest(clave=clave):
                Tiene.objects.all().delete()
                self.agregar(clave)

                _MIGRACION.calificadas_a_vistas(apps, None)

                self.assertTrue(self.en(clave))
                self.assertFalse(self.en("vistas"))

    def test_una_calificacion_inactiva_no_cuenta(self):
        self.calificar(activa=False)

        _MIGRACION.calificadas_a_vistas(apps, None)

        self.assertFalse(self.en("vistas"))

    def test_lo_sin_calificar_queda_como_estaba_y_favoritos_no_cuenta_como_estado(self):
        otra = ProduccionAudiovisualFactory()
        self.agregar("favoritos", otra)
        self.calificar(otra)

        _MIGRACION.calificadas_a_vistas(apps, None)

        # Favoritos no es un estado: la calificada pasa a Vistas igual.
        self.assertTrue(self.en("vistas", otra))
        self.assertTrue(self.en("favoritos", otra))
        self.assertFalse(self.en("vistas"))

    def test_es_por_usuario(self):
        otro = UsuarioFactory()
        self.calificar(usuario=otro)

        _MIGRACION.calificadas_a_vistas(apps, None)

        self.assertTrue(self.en("vistas", usuario=otro))
        self.assertFalse(self.en("vistas"))

    def test_correrla_dos_veces_no_duplica(self):
        self.calificar()

        _MIGRACION.calificadas_a_vistas(apps, None)
        _MIGRACION.calificadas_a_vistas(apps, None)

        self.assertEqual(self.lista("vistas").items.count(), 1)


class PendienteYVistaTests(_Base):
    def test_queda_solo_en_la_lista_donde_se_agrego_ultimo(self):
        for ultima, perdedora in (("vistas", "pendientes"), ("pendientes", "vistas")):
            with self.subTest(ultima=ultima):
                Tiene.objects.all().delete()
                self.agregar(perdedora, hace_dias=5)
                self.agregar(ultima, hace_dias=1)

                _MIGRACION.una_sola_lista_de_estado(apps, None)

                self.assertTrue(self.en(ultima))
                self.assertFalse(self.en(perdedora))

    def test_con_la_misma_fecha_gana_vistas(self):
        ahora = timezone.now()
        for clave in ("pendientes", "vistas"):
            item = self.agregar(clave)
            Tiene.objects.filter(pk=item.pk).update(fecha_agregado=ahora)

        _MIGRACION.una_sola_lista_de_estado(apps, None)

        self.assertTrue(self.en("vistas"))
        self.assertFalse(self.en("pendientes"))

    def test_no_toca_lo_que_esta_en_una_sola_lista_ni_otros_usuarios(self):
        sola = ProduccionAudiovisualFactory()
        self.agregar("pendientes", sola)
        otro = UsuarioFactory()
        for clave in ("pendientes", "vistas"):
            Tiene.objects.create(
                lista=self.lista(clave, otro), produccion=self.produccion
            )
        self.agregar("vistas", hace_dias=1)
        self.agregar("pendientes", hace_dias=3)

        _MIGRACION.una_sola_lista_de_estado(apps, None)

        self.assertTrue(self.en("pendientes", sola))
        # Cada usuario se resuelve por separado.
        self.assertEqual(
            Tiene.objects.filter(
                lista__usuario=otro, produccion=self.produccion
            ).count(),
            1,
        )

    def test_favoritos_y_personalizadas_no_se_tocan(self):
        propia = ListaFactory(usuario=self.usuario, nombre="Mi colección")
        Tiene.objects.create(lista=propia, produccion=self.produccion)
        self.agregar("favoritos")
        self.agregar("pendientes", hace_dias=3)
        self.agregar("vistas", hace_dias=1)

        _MIGRACION.una_sola_lista_de_estado(apps, None)

        self.assertTrue(propia.items.exists())
        self.assertTrue(self.en("favoritos"))


class OrdenDeLosPasosTests(_Base):
    def test_el_conjunto_deja_a_cada_titulo_en_un_solo_estado(self):
        """Los tres pasos juntos, en el orden de la migración."""
        calificada = ProduccionAudiovisualFactory()
        doble = ProduccionAudiovisualFactory()
        Lista.objects.filter(clave="viendo").delete()
        Calificacion.objects.create(
            usuario=self.usuario, produccion=calificada, valor=9, activa=True
        )
        self.agregar("pendientes", doble, hace_dias=4)
        self.agregar("vistas", doble, hace_dias=2)

        _MIGRACION.aplicar(apps, None)

        self.assertTrue(self.lista("viendo"))
        self.assertTrue(self.en("vistas", calificada))
        self.assertTrue(self.en("vistas", doble))
        self.assertFalse(self.en("pendientes", doble))

    def test_la_reversa_no_hace_nada(self):
        self.agregar("vistas")
        antes = Tiene.objects.count(), Lista.objects.count()

        _MIGRACION.revertir(apps, None)

        self.assertEqual((Tiene.objects.count(), Lista.objects.count()), antes)
