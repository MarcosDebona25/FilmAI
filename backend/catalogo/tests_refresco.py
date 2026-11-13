"""La tarea nocturna `catalogo.refrescar_vencidos` y la regla del 404 (#180).

Dos grupos de tests, con dos estrategias distintas:

- La orquestación (qué filas elige, qué cuenta, qué pasa si una falla) parchea
  `materializar`: el enriquecimiento ya tiene su suite y acá no importa.
- Lo que pasa con la base tras un 404 y la restauración usan los servicios de
  TMDB falsos de `test_traducciones`, para ver lo que de verdad queda escrito.
"""

import datetime as dt
from datetime import timedelta
from unittest.mock import patch

import httpx
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from catalogo.client import TMDBClient
from catalogo.exceptions import (
    TMDBError,
    TMDBNotFound,
    TMDBRateLimited,
    TMDBServerError,
    TMDBTransportError,
)
from catalogo.models import (
    Calificacion,
    EstadoEmbedding,
    ProduccionAudiovisual,
    ProduccionEmbedding,
    ProduccionTraduccion,
    Resena,
    TipoProduccion,
)
from catalogo.tasks import refrescar_vencidos
from catalogo.test_traducciones import ServiciosPorIdioma
from listas.models import Lista, Tiene
from usuarios.factories import UsuarioFactory

MATERIALIZAR = "catalogo.services.vencimiento.materializar"


def crear(id_tmdb, antiguedad_dias=None, tipo=TipoProduccion.PELICULA, **extra):
    """Producción con contenido; `antiguedad_dias=None` = nunca enriquecida."""
    fecha = (
        None
        if antiguedad_dias is None
        else timezone.now() - timedelta(days=antiguedad_dias)
    )
    return ProduccionAudiovisual.objects.create(
        id_tmdb=id_tmdb,
        tipo=tipo,
        titulo=extra.pop("titulo", f"Título {id_tmdb}"),
        poster="/poster.jpg",
        sinopsis="Una sinopsis de TMDB.",
        fecha_lanzamiento=dt.date(1999, 10, 15),
        reparto=["Actor"],
        directores=["Directora"],
        generos=["Drama"],
        generos_ids=[18],
        keywords=["clave"],
        calificacion_promedio=8.1,
        duracion=139,
        fecha_enriquecimiento=fecha,
        **extra,
    )


class ElegirYContarTests(TestCase):
    """Tarea 2.3: la tarea refresca lo elegido y cuenta lo que hizo."""

    def setUp(self):
        parche = patch(MATERIALIZAR)
        self.materializar = parche.start()
        self.addCleanup(parche.stop)

    def llamadas(self):
        return [(c.args, c.kwargs) for c in self.materializar.call_args_list]

    def test_refresca_con_forzar_solo_las_filas_de_la_cuota(self):
        sin_fecha = crear(1)
        vencida = crear(2, 200)
        crear(3, 160)
        crear(4, 10)

        # Hay 2 filas para esta noche (k = 1): la cuota es 2.
        estadisticas = refrescar_vencidos()

        self.assertEqual(estadisticas["cuota"], 2)
        self.assertEqual(
            self.llamadas(),
            [
                ((sin_fecha.id_tmdb, "movie"), {"forzar": True}),
                ((vencida.id_tmdb, "movie"), {"forzar": True}),
            ],
        )

    def test_pide_el_tipo_de_tmdb_no_el_del_dominio(self):
        crear(7, 200, tipo=TipoProduccion.SERIE)

        refrescar_vencidos()

        self.assertEqual(self.llamadas(), [((7, "tv"), {"forzar": True})])

    def test_un_error_no_frena_al_resto(self):
        crear(1)
        crear(2)
        crear(3)
        self.materializar.side_effect = [TMDBServerError("500"), None, None]

        estadisticas = refrescar_vencidos()

        self.assertEqual(self.materializar.call_count, 3)
        self.assertEqual(estadisticas["refrescadas"], 2)
        self.assertEqual(estadisticas["fallidas"], 1)

    def test_una_excepcion_cualquiera_tampoco_frena_al_resto(self):
        # Es el borde con TMDB y con la base: se atrapa todo, como en la sync.
        crear(1)
        crear(2)
        self.materializar.side_effect = [RuntimeError("raro"), None]

        estadisticas = refrescar_vencidos()

        self.assertEqual(estadisticas["fallidas"], 1)
        self.assertEqual(estadisticas["refrescadas"], 1)

    def test_el_resumen_cuenta_no_encontradas_y_filas_que_siguen_vencidas(self):
        crear(1, 200)
        crear(2, 400)
        self.materializar.side_effect = [None, TMDBNotFound("404")]

        with self.assertLogs("catalogo.services.vencimiento", "WARNING") as logs:
            estadisticas = refrescar_vencidos()

        self.assertEqual(estadisticas["refrescadas"], 1)
        self.assertEqual(estadisticas["no_encontradas"], 1)
        # `materializar` está parcheada: ninguna fila cambió de fecha, así que
        # las dos siguen pasadas de 180 días.
        self.assertEqual(estadisticas["pasadas_de_180"], 2)
        self.assertIn("2", "".join(logs.output))

    def test_sin_filas_vencidas_no_avisa_nada(self):
        crear(1, 10)

        with self.assertNoLogs("catalogo.services.vencimiento", "WARNING"):
            estadisticas = refrescar_vencidos()

        self.assertEqual(estadisticas["pasadas_de_180"], 0)

    def test_base_vacia_no_llama_a_tmdb(self):
        estadisticas = refrescar_vencidos()

        self.assertEqual(estadisticas["cuota"], 0)
        self.materializar.assert_not_called()

    def test_el_techo_limita_y_el_resumen_lo_avisa(self):
        for i in range(5):
            crear(i + 1, 200)

        with (
            self.settings(CELERY_REFRESCO_TECHO=2),
            self.assertLogs("catalogo.services.vencimiento", "WARNING") as logs,
        ):
            estadisticas = refrescar_vencidos()

        self.assertEqual(self.materializar.call_count, 2)
        self.assertEqual(estadisticas["limitada_por"], "techo")
        self.assertIn("techo", "".join(logs.output).lower())


class ReglaDelCuatrocientosCuatroTests(TestCase):
    """Tareas 2.5, 2.5b y 2.6: dos 404 en noches distintas y, según el uso, se
    borra o queda como lápida."""

    def setUp(self):
        parche = patch(MATERIALIZAR, side_effect=TMDBNotFound("404"))
        self.materializar = parche.start()
        self.addCleanup(parche.stop)

    def recargar(self, produccion):
        return ProduccionAudiovisual.objects.get(pk=produccion.pk)

    def test_el_primer_404_solo_anota_la_fecha_y_deja_la_fila_vencida(self):
        produccion = crear(1, 200)
        fecha_vieja = produccion.fecha_enriquecimiento

        refrescar_vencidos()

        produccion = self.recargar(produccion)
        self.assertEqual(produccion.fecha_404, timezone.localdate())
        self.assertTrue(produccion.disponible_en_tmdb)
        self.assertEqual(produccion.titulo, "Título 1")
        # Sigue vencida: mañana se vuelve a intentar.
        self.assertEqual(produccion.fecha_enriquecimiento, fecha_vieja)

    def test_dos_404_la_misma_noche_no_cuentan_como_dos(self):
        produccion = crear(1, 200)

        refrescar_vencidos()  # anota la fecha de hoy
        refrescar_vencidos()  # reintento a mano la misma noche

        produccion = self.recargar(produccion)
        self.assertTrue(produccion.disponible_en_tmdb)
        self.assertEqual(produccion.titulo, "Título 1")

    def test_el_segundo_404_en_otra_noche_borra_la_fila_que_nadie_usa(self):
        produccion = crear(1, 200, fecha_404=timezone.localdate() - timedelta(days=1))
        ProduccionTraduccion.objects.create(
            produccion=produccion, idioma="es", titulo="Título"
        )
        ProduccionEmbedding.objects.create(produccion=produccion)

        estadisticas = refrescar_vencidos()

        self.assertFalse(
            ProduccionAudiovisual.objects.filter(pk=produccion.pk).exists()
        )
        # Las traducciones y el embedding se van por CASCADE.
        self.assertFalse(ProduccionTraduccion.objects.exists())
        self.assertFalse(ProduccionEmbedding.objects.exists())
        self.assertEqual(estadisticas["borradas"], 1)

    def test_con_una_calificacion_queda_lapida_y_la_calificacion_sigue(self):
        produccion = crear(1, 200, fecha_404=timezone.localdate() - timedelta(days=1))
        calificacion = Calificacion.objects.create(
            usuario=UsuarioFactory(), produccion=produccion, valor=9
        )
        Resena.objects.create(calificacion=calificacion, texto="Una obra maestra")
        ProduccionTraduccion.objects.create(
            produccion=produccion, idioma="es", titulo="Título", sinopsis="Sinopsis"
        )
        ProduccionEmbedding.objects.create(produccion=produccion)

        estadisticas = refrescar_vencidos()

        lapida = self.recargar(produccion)
        self.assertFalse(lapida.disponible_en_tmdb)
        self.assertEqual((lapida.id_tmdb, lapida.tipo), (1, TipoProduccion.PELICULA))
        self.assertGreater(
            lapida.fecha_enriquecimiento, timezone.now() - timedelta(minutes=1)
        )
        # La nota y la reseña del usuario siguen intactas.
        self.assertEqual(Calificacion.objects.get(pk=calificacion.pk).valor, 9)
        self.assertEqual(Resena.objects.get().texto, "Una obra maestra")
        # Nada de TMDB queda: ni traducciones ni vector.
        self.assertFalse(ProduccionTraduccion.objects.exists())
        self.assertFalse(ProduccionEmbedding.objects.exists())
        self.assertEqual(estadisticas["lapidas"], 1)

    def test_la_lapida_no_conserva_ningun_campo_de_contenido(self):
        produccion = crear(1, 200, fecha_404=timezone.localdate() - timedelta(days=1))
        Calificacion.objects.create(
            usuario=UsuarioFactory(), produccion=produccion, valor=5
        )

        refrescar_vencidos()

        lapida = self.recargar(produccion)
        conservados = {
            "id",
            "id_tmdb",
            "tipo",
            "fecha_enriquecimiento",
            "fecha_404",
            "disponible_en_tmdb",
        }
        # Recorre todos los campos del modelo, así un campo nuevo con contenido
        # de TMDB que se agregue mañana hace fallar este test.
        for campo in ProduccionAudiovisual._meta.concrete_fields:
            if campo.name in conservados:
                continue
            with self.subTest(campo=campo.name):
                self.assertEqual(getattr(lapida, campo.name), campo.get_default())

    def test_un_item_de_lista_tambien_cuenta_como_uso(self):
        produccion = crear(1, 200, fecha_404=timezone.localdate() - timedelta(days=1))
        lista = Lista.objects.create(nombre="Para ver", usuario=UsuarioFactory())
        Tiene.objects.create(lista=lista, produccion=produccion)

        refrescar_vencidos()

        self.assertFalse(self.recargar(produccion).disponible_en_tmdb)
        self.assertEqual(Tiene.objects.count(), 1)

    def test_si_el_borrado_falla_por_una_calificacion_nueva_queda_lapida(self):
        # La carrera de la tarea 2.6b: la fila no tenía referencias cuando se
        # decidió borrarla y una calificación llega antes del DELETE. En
        # producción la calificación entra desde otra conexión, ya confirmada;
        # acá ya existe de antemano y lo que se simula es cómo falla el DELETE:
        # Django lo detecta antes (`ProtectedError`) o, si llegó entre su lectura
        # y el DELETE, la clave foránea de Postgres lo frena (`IntegrityError`).
        errores = {
            "django": ProtectedError("protegida", []),
            "postgres": IntegrityError("viola la clave foránea"),
        }
        for nombre, error in errores.items():
            with self.subTest(detecta=nombre):
                produccion = crear(
                    1, 200, fecha_404=timezone.localdate() - timedelta(days=1)
                )
                Calificacion.objects.create(
                    usuario=UsuarioFactory(), produccion=produccion, valor=7
                )

                with patch.object(ProduccionAudiovisual, "delete", side_effect=error):
                    estadisticas = refrescar_vencidos()

                self.assertFalse(self.recargar(produccion).disponible_en_tmdb)
                self.assertEqual(Calificacion.objects.count(), 1)
                self.assertEqual(estadisticas["lapidas"], 1)
                self.assertEqual(estadisticas["borradas"], 0)
                Calificacion.objects.all().delete()
                produccion.delete()

    def test_una_lapida_que_sigue_dando_404_se_conserva_y_rota(self):
        produccion = crear(1, 200, fecha_404=timezone.localdate() - timedelta(days=1))
        Calificacion.objects.create(
            usuario=UsuarioFactory(), produccion=produccion, valor=5
        )
        refrescar_vencidos()  # pasa a lápida
        ProduccionAudiovisual.objects.filter(pk=produccion.pk).update(
            fecha_enriquecimiento=timezone.now() - timedelta(days=151)
        )

        refrescar_vencidos()

        lapida = self.recargar(produccion)
        self.assertFalse(lapida.disponible_en_tmdb)
        # Volvió a la cola 150 días después: no vuelve a estar vencida esta noche.
        self.assertGreater(
            lapida.fecha_enriquecimiento, timezone.now() - timedelta(minutes=1)
        )

    def test_una_lapida_que_ya_nadie_usa_se_borra_con_el_siguiente_404(self):
        produccion = crear(1, 200, fecha_404=timezone.localdate() - timedelta(days=1))
        calificacion = Calificacion.objects.create(
            usuario=UsuarioFactory(), produccion=produccion, valor=5
        )
        refrescar_vencidos()  # lápida
        calificacion.delete()  # el usuario borra su calificación
        ProduccionAudiovisual.objects.filter(pk=produccion.pk).update(
            fecha_enriquecimiento=timezone.now() - timedelta(days=151),
            fecha_404=timezone.localdate() - timedelta(days=1),
        )

        refrescar_vencidos()

        self.assertFalse(
            ProduccionAudiovisual.objects.filter(pk=produccion.pk).exists()
        )


class SoloElCuatrocientosCuatroCuentaTests(TestCase):
    """Tarea 2.5: un timeout, 500, 429 o 401 es un refresco fallido, no un 404."""

    def test_otros_errores_no_anotan_ni_borran_nada(self):
        errores = {
            "timeout": TMDBTransportError("timeout"),
            "500": TMDBServerError("500"),
            "429": TMDBRateLimited("429"),
            "401": TMDBError("401"),
        }
        for nombre, error in errores.items():
            with self.subTest(error=nombre):
                produccion = crear(10, 200)
                # Aunque ya tuviera un 404 anotado de otra noche.
                produccion.fecha_404 = timezone.localdate() - timedelta(days=1)
                produccion.save()

                with patch(MATERIALIZAR, side_effect=error):
                    estadisticas = refrescar_vencidos()

                produccion.refresh_from_db()
                self.assertTrue(produccion.disponible_en_tmdb)
                self.assertEqual(produccion.titulo, "Título 10")
                self.assertEqual(
                    produccion.fecha_404, timezone.localdate() - timedelta(days=1)
                )
                self.assertEqual(estadisticas["fallidas"], 1)
                produccion.delete()


class RefrescoRealTests(TestCase):
    """Con `materializar` de verdad: lo que un refresco exitoso deja escrito."""

    def setUp(self):
        self.fabrica = ServiciosPorIdioma()
        for destino in (
            patch(
                "catalogo.services.materialization.get_catalog_service",
                side_effect=self.fabrica,
            ),
            patch("catalogo.services.materialization.generar_embedding"),
        ):
            mock = destino.start()
            self.addCleanup(destino.stop)
        self.generar_embedding = mock

    def test_un_refresco_exitoso_borra_la_marca_de_404(self):
        # Tarea 2.5: «a successful refresh clears fecha_404».
        produccion = crear(550, 200, fecha_404=timezone.localdate() - timedelta(days=3))

        refrescar_vencidos()

        produccion.refresh_from_db()
        self.assertIsNone(produccion.fecha_404)
        self.assertEqual(produccion.titulo, "Fight Club")

    def test_una_lapida_que_tmdb_devuelve_se_restaura(self):
        # Tarea 2.6c. Una lápida: sin contenido, sin embedding, no disponible.
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="",
            disponible_en_tmdb=False,
            fecha_404=timezone.localdate() - timedelta(days=200),
            fecha_enriquecimiento=timezone.now() - timedelta(days=151),
        )

        with self.captureOnCommitCallbacks(execute=True):
            refrescar_vencidos()

        produccion.refresh_from_db()
        self.assertTrue(produccion.disponible_en_tmdb)
        self.assertIsNone(produccion.fecha_404)
        self.assertEqual(produccion.titulo, "Fight Club")
        self.assertEqual(produccion.generos, ["Drama", "Thriller"])
        # El embedding vuelve a encolarse: la fila lo había perdido.
        embedding = ProduccionEmbedding.objects.get(produccion=produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.PENDING)
        self.generar_embedding.delay.assert_called_once_with(produccion.pk)

    def test_el_refresco_reescribe_las_traducciones_no_solo_rellena_huecos(self):
        # Tarea 2.4. Esto ya pasaba antes del cambio (`update_or_create`): no es
        # un RED, es la prueba que fija ese comportamiento.
        produccion = crear(550, 200)
        ProduccionTraduccion.objects.create(
            produccion=produccion,
            idioma="es",
            titulo="Título viejo",
            sinopsis="Sinopsis vieja",
            poster="/vieja.jpg",
        )

        refrescar_vencidos()

        traduccion = ProduccionTraduccion.objects.get(produccion=produccion)
        self.assertEqual(traduccion.titulo, "El club de la pelea")
        self.assertEqual(traduccion.sinopsis, "Un oficinista insomne...")
        self.assertEqual(traduccion.poster, "/es.jpg")


class RefrescoRespetaElLimiteDeTMDBTests(TestCase):
    """Tarea 2.9: el refresco pasa por el cliente de siempre, que espera lo que
    TMDB pide con `Retry-After` antes de reintentar un 429."""

    def test_un_429_con_retry_after_espera_y_la_fila_se_refresca(self):
        pedidos = []

        def responder(request):
            pedidos.append(request.url.path)
            if len(pedidos) == 1:
                return httpx.Response(429, headers={"Retry-After": "2"})
            if request.url.path.endswith("/credits"):
                return httpx.Response(200, json={"cast": [], "crew": []})
            if request.url.path.endswith("/keywords"):
                return httpx.Response(200, json={"keywords": []})
            return httpx.Response(200, json={"id": 550, "title": "Fight Club"})

        cliente = TMDBClient(api_key="clave", transport=httpx.MockTransport(responder))
        produccion = crear(550, 200)

        with (
            patch(
                "catalogo.services.materialization.get_catalog_service",
                return_value=cliente,
            ),
            patch("catalogo.services.materialization.generar_embedding"),
            patch("catalogo.client.time.sleep") as dormir,
        ):
            estadisticas = refrescar_vencidos()

        # Esperó lo que pidió TMDB (2 s) y recién después reintentó.
        dormir.assert_any_call(2.0)
        self.assertEqual(estadisticas["refrescadas"], 1)
        self.assertEqual(estadisticas["fallidas"], 0)
        produccion.refresh_from_db()
        self.assertEqual(produccion.titulo, "Fight Club")
