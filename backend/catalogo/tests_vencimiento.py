"""Cuánto refrescar cada noche y qué filas (#180, tarea 2.2).

Los tests de `cuota_nocturna` son de aritmética pura: no tocan la base. Los de
`contar_plazos` y `a_refrescar` sí, porque lo que verifican es el SQL.
"""

import datetime as dt
from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from catalogo.models import ProduccionAudiovisual, TipoProduccion
from catalogo.services.vencimiento import (
    a_refrescar,
    contar_plazos,
    cuota_nocturna,
    detalle_cuota,
    filas_pasadas_de_180,
)

TECHO = 1000


class CuotaNocturnaTests(SimpleTestCase):
    """`cuota_nocturna(total, por_dia, techo)`: `por_dia[k]` son las filas que
    llegan a los 180 días dentro de `k` noches (k = 1 es esta misma noche)."""

    def test_base_vacia_no_refresca_nada(self):
        self.assertEqual(cuota_nocturna(0, {}, TECHO), 0)

    def test_catalogo_parejo_sigue_la_rotacion(self):
        # 10 000 filas repartidas en los últimos 150 días: ninguna vence en los
        # próximos 30, así que manda la rotación: ceil(10 000 / 150) = 67.
        self.assertEqual(cuota_nocturna(10_000, {}, TECHO), 67)

    def test_carga_masiva_de_150_dias_obliga_a_334_por_noche(self):
        # Todas vencen dentro de 30 noches: ceil(10 000 / 30) = 334, más que la
        # rotación (67). Es el caso que motivó el diseño.
        self.assertEqual(cuota_nocturna(10_000, {30: 10_000}, TECHO), 334)

    def test_lo_vencido_y_lo_sin_fecha_cuentan_para_esta_noche(self):
        # Están en k = 1: hay que refrescarlas todas esta noche.
        self.assertEqual(cuota_nocturna(500, {1: 500}, TECHO), 500)

    def test_los_plazos_se_acumulan_y_manda_el_peor(self):
        # k=1: 10 filas → 10/noche. k=2: 20 acumuladas → 10/noche.
        # k=3: 120 acumuladas → 40/noche. El máximo es 40.
        self.assertEqual(cuota_nocturna(120, {1: 10, 2: 10, 3: 100}, TECHO), 40)

    def test_el_techo_manda_aunque_los_plazos_pidan_mas(self):
        self.assertEqual(cuota_nocturna(40_000, {1: 40_000}, TECHO), TECHO)

    def test_la_rotacion_redondea_hacia_arriba(self):
        self.assertEqual(cuota_nocturna(150, {}, TECHO), 1)
        self.assertEqual(cuota_nocturna(151, {}, TECHO), 2)

    def test_plazos_mas_alla_de_30_noches_no_se_cuentan(self):
        # Esa ventana la cubre la rotación: no pueden inflar la cuota de hoy.
        self.assertEqual(cuota_nocturna(1_000, {31: 1_000}, TECHO), 7)

    def test_el_detalle_dice_cual_de_los_tres_numeros_mando(self):
        self.assertEqual(detalle_cuota(10_000, {}, TECHO)["limitada_por"], "rotacion")
        self.assertEqual(
            detalle_cuota(10_000, {30: 10_000}, TECHO)["limitada_por"], "plazos"
        )
        self.assertEqual(
            detalle_cuota(40_000, {1: 40_000}, TECHO)["limitada_por"], "techo"
        )


AHORA = dt.datetime(2026, 11, 14, 3, 30, tzinfo=timezone.get_current_timezone())


def crear(id_tmdb, antiguedad_dias):
    """Una producción enriquecida hace `antiguedad_dias`; `None` = sin fecha."""
    fecha = None if antiguedad_dias is None else AHORA - timedelta(days=antiguedad_dias)
    return ProduccionAudiovisual.objects.create(
        id_tmdb=id_tmdb,
        tipo=TipoProduccion.PELICULA,
        titulo=f"Título {id_tmdb}",
        fecha_enriquecimiento=fecha,
    )


class ContarPlazosTests(TestCase):
    def test_agrupa_las_filas_por_noches_que_faltan_para_los_180_dias(self):
        crear(1, None)  # nunca enriquecida: k = 1
        crear(2, 200)  # ya vencida: k = 1
        crear(3, 170)  # cumple 180 en ~10 días: k = 10
        crear(4, 150)  # k = 30
        crear(5, 150)
        crear(6, 150)
        crear(7, 10)  # reciente: cuenta en el total, en ningún plazo

        total, por_dia = contar_plazos(AHORA)

        self.assertEqual(total, 7)
        self.assertEqual(por_dia, {1: 2, 10: 1, 30: 3})

    def test_agrupar_cuesta_dos_consultas_sin_importar_cuantas_filas_hay(self):
        for i in range(40):
            crear(100 + i, 150 + i % 25)

        with self.assertNumQueries(2):  # un COUNT y un GROUP BY
            contar_plazos(AHORA)

    def test_base_vacia(self):
        self.assertEqual(contar_plazos(AHORA), (0, {}))


class ALRefrescarTests(TestCase):
    def test_primero_las_sin_fecha_despues_las_mas_viejas_y_solo_cuota(self):
        reciente = crear(1, 10)
        vieja = crear(2, 160)
        sin_fecha = crear(3, None)
        media = crear(4, 100)

        elegidas = a_refrescar(3)

        self.assertEqual(elegidas, [sin_fecha, vieja, media])
        self.assertNotIn(reciente, elegidas)

    def test_cuota_cero_no_elige_nada(self):
        crear(1, None)
        self.assertEqual(a_refrescar(0), [])

    def test_la_cuota_puede_alcanzar_filas_menores_de_150_dias(self):
        # Es la rotación funcionando, no un error (design, paso 2).
        crear(1, 10)
        self.assertEqual(len(a_refrescar(5)), 1)


class FilasPasadasDe180Tests(TestCase):
    def test_cuenta_solo_las_que_ya_pasaron_los_180_dias(self):
        crear(1, 181)
        crear(2, 400)
        crear(3, 179)
        crear(4, None)  # sin fecha: se informa aparte, no entra acá

        self.assertEqual(filas_pasadas_de_180(AHORA), 2)
