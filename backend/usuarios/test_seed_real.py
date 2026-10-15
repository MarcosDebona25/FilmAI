"""El seed por defecto arma el catálogo desde TMDB y actividad con sentido."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.models import Calificacion, ProduccionAudiovisual, Resena
from listas.models import ClaveLista, Tiene
from usuarios import seed_real
from usuarios.factories import UsuarioFactory
from usuarios.models import Usuario


class ServicioFalso:
    """Devuelve 4 títulos por género; el id codifica género y posición."""

    def discover(self, tipo, genero, page, sort_by):
        base = (1000 if tipo == "movie" else 5000) + genero * 10
        return {"results": [{"id": base + i} for i in range(4)]}


def materializar_falso(id_tmdb, tipo):
    genero = (id_tmdb % 5000 if id_tmdb >= 5000 else id_tmdb - 1000) // 10
    return ProduccionAudiovisual.objects.get_or_create(
        id_tmdb=id_tmdb,
        tipo="pelicula" if tipo == "movie" else "serie",
        defaults={
            "titulo": f"Real {id_tmdb}",
            "poster": f"/p{id_tmdb}.jpg",
            "generos_ids": [genero],
            "calificacion_promedio": 7.5,
        },
    )[0]


class SeedRealTests(TestCase):
    def correr(self, **opciones):
        with (
            patch.object(seed_real, "PAUSA_TMDB", 0),
            patch.object(seed_real, "get_catalog_service", ServicioFalso),
            patch.object(seed_real, "materializar", materializar_falso),
        ):
            call_command("seed", stdout=StringIO(), **opciones)

    def test_materializa_tmdb_y_arma_actividad_con_sentido(self):
        self.correr()

        self.assertGreaterEqual(seed_real.reales().count(), seed_real.MINIMO_REALES)
        self.assertEqual(Usuario.objects.filter(is_staff=False).count(), 3)
        calificaciones = Calificacion.objects.all()
        self.assertTrue(calificaciones.exists())
        self.assertTrue(Resena.objects.exists())
        for calificacion in calificaciones:
            # calificada ⇒ en Vistas, y todo con póster de TMDB.
            self.assertTrue(calificacion.produccion.poster.startswith("/"))
            self.assertTrue(
                Tiene.objects.filter(
                    lista__usuario=calificacion.usuario,
                    lista__clave=ClaveLista.VISTAS,
                    produccion=calificacion.produccion,
                ).exists()
            )
        for usuario in Usuario.objects.filter(is_staff=False):
            self.assertEqual(usuario.listas.filter(tipo="personalizada").count(), 2)
            vistas = set(
                Tiene.objects.filter(
                    lista__usuario=usuario, lista__clave=ClaveLista.VISTAS
                ).values_list("produccion_id", flat=True)
            )
            pendientes = set(
                Tiene.objects.filter(
                    lista__usuario=usuario, lista__clave=ClaveLista.PENDIENTES
                ).values_list("produccion_id", flat=True)
            )
            self.assertFalse(vistas & pendientes)

    def test_repetirlo_conserva_el_catalogo_real_y_quita_las_sinteticas(self):
        self.correr()
        total = ProduccionAudiovisual.objects.count()
        sintetica = ProduccionAudiovisualFactory(poster="https://picsum.photos/1.jpg")

        self.correr()

        self.assertFalse(ProduccionAudiovisual.objects.filter(pk=sintetica.pk).exists())
        self.assertEqual(ProduccionAudiovisual.objects.count(), total)

    def test_sin_pool_minimo_aborta_sin_borrar(self):
        usuario = UsuarioFactory()
        vacio = type("Vacio", (), {"discover": lambda *a, **k: {"results": []}})
        with (
            patch.object(seed_real, "PAUSA_TMDB", 0),
            patch.object(seed_real, "get_catalog_service", vacio),
            self.assertRaises(CommandError),
        ):
            call_command("seed", stdout=StringIO())
        self.assertTrue(Usuario.objects.filter(pk=usuario.pk).exists())
