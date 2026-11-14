"""Sugerencias de una lista: `GET /api/lists/{id}/suggestions/?pagina=N`.

Diseño en `openspec/changes/recomendaciones-similares/design.md` §7. El motor
tiene sus propios tests (`catalogo/tests_similares.py`) y el nombre de la lista
también (`catalogo/tests_similares_nombre.py`). Acá se prueba lo que agrega la
vista: quién puede pedirla, qué semillas arma con los ítems de la lista, qué
firma tiene su caché y qué se le saca a cada usuario. TMDB se reemplaza por
`ServicioFalso` y Ollama por un parche sobre `vector_del_nombre`: ningún test
sale de la máquina.
"""

from unittest.mock import patch

from django.core.cache import cache
from rest_framework.test import APIClient

from catalogo.models import EstadoEmbedding, TipoProduccion
from catalogo.services import similares
from catalogo.tests_similares import (
    BaseSimilares,
    ServicioFalso,
    eje,
    item_tmdb,
    vector_a,
)
from listas.factories import ListaFactory
from listas.models import ClaveLista, Tiene
from usuarios.factories import UsuarioFactory


class BaseSugerencias(BaseSimilares):
    """Un usuario con sesión, TMDB y Ollama reemplazados y la caché limpia."""

    def setUp(self):
        super().setUp()
        # El pool se guarda en la caché: sin limpiarla, un test vería el del anterior.
        cache.clear()
        self.addCleanup(cache.clear)
        self.respuestas_tmdb = {}
        self.servicio = ServicioFalso(self.respuestas_tmdb)
        parche = patch("listas.views.get_catalog_service", return_value=self.servicio)
        parche.start()
        self.addCleanup(parche.stop)
        parche = patch(
            "catalogo.services.similares.materializar_listado_en_segundo_plano"
        )
        self.encolar = parche.start()
        self.addCleanup(parche.stop)
        # Por defecto Ollama «no responde»: el nombre se saltea. Los tests del
        # nombre cambian `.return_value`.
        parche = patch("catalogo.services.similares.vector_del_nombre")
        self.vector_nombre = parche.start()
        self.vector_nombre.return_value = None
        self.addCleanup(parche.stop)

        self.usuario = UsuarioFactory()
        self.api = APIClient()
        self.api.force_authenticate(self.usuario)

    def url(self, lista, pagina=None):
        base = f"/api/lists/{lista.pk}/suggestions/"
        return base if pagina is None else f"{base}?pagina={pagina}"

    def lista_con(self, *producciones, nombre="Sci Fi"):
        lista = ListaFactory(usuario=self.usuario, nombre=nombre)
        for produccion in producciones:
            Tiene.objects.create(lista=lista, produccion=produccion)
        return lista

    def vecinas(self, cantidad, **campos):
        """Títulos a un ángulo cada vez mayor de `eje(0)`: todos muy cercanos."""
        return [
            self.produccion(f"Vecina {n}", vector_a(0.01 * (n + 1)), **campos)
            for n in range(cantidad)
        ]

    def ids(self, respuesta):
        return [(item["tipo"], item["id_tmdb"]) for item in respuesta.json()["results"]]


class AccesoTests(BaseSugerencias):
    def test_sin_sesion_es_401(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))

        respuesta = APIClient().get(self.url(lista))

        self.assertEqual(respuesta.status_code, 401)

    def test_la_lista_de_otra_persona_es_404_not_found(self):
        ajena = ListaFactory()

        respuesta = self.api.get(self.url(ajena))

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json()["code"], "not_found")

    def test_una_lista_inactiva_es_404(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        lista.activa = False
        lista.save()

        self.assertEqual(self.api.get(self.url(lista)).status_code, 404)

    def test_pendientes_y_vistas_son_404_not_found(self):
        for clave in (ClaveLista.PENDIENTES, ClaveLista.VISTAS):
            with self.subTest(clave=clave):
                lista = self.usuario.listas.get(clave=clave)

                respuesta = self.api.get(self.url(lista))

                self.assertEqual(respuesta.status_code, 404)
                self.assertEqual(respuesta.json()["code"], "not_found")

    def test_favoritos_si_tiene_sugerencias(self):
        favoritos = self.usuario.listas.get(clave=ClaveLista.FAVORITOS)
        Tiene.objects.create(lista=favoritos, produccion=self.produccion("A", eje(0)))
        self.vecinas(3)

        respuesta = self.api.get(self.url(favoritos))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["results"]), 3)

    def test_usa_el_limite_de_pedidos_del_catalogo(self):
        from listas.views import ListaSugerenciasView

        self.assertEqual(ListaSugerenciasView.throttle_scope, "catalogo")


class ParametroPaginaTests(BaseSugerencias):
    def test_una_pagina_que_no_es_un_entero_positivo_es_400_invalid(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))

        for valor in ("0", "-1", "abc", "1.5", ""):
            with self.subTest(pagina=valor):
                respuesta = self.api.get(self.url(lista, valor))

                self.assertEqual(respuesta.status_code, 400)
                error = respuesta.json()["errors"][0]
                self.assertEqual((error["field"], error["code"]), ("pagina", "invalid"))
        self.assertEqual(self.servicio.pedidos, [])

    def test_sin_pagina_es_la_primera(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        self.vecinas(25)

        respuesta = self.api.get(self.url(lista))

        self.assertEqual(respuesta.json()["pagina"], 1)
        self.assertEqual(len(respuesta.json()["results"]), 10)

    def test_las_paginas_traen_titulos_distintos_y_pasada_la_ultima_viene_vacia(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        self.vecinas(25)

        primera = self.api.get(self.url(lista, 1))
        segunda = self.api.get(self.url(lista, 2))
        tercera = self.api.get(self.url(lista, 3))
        cuarta = self.api.get(self.url(lista, 4))

        self.assertEqual(primera.json()["paginas"], 3)
        self.assertFalse(set(self.ids(primera)) & set(self.ids(segunda)))
        self.assertEqual(len(tercera.json()["results"]), 5)
        self.assertEqual(cuarta.status_code, 200)
        self.assertEqual(cuarta.json()["results"], [])
        self.assertEqual(cuarta.json()["pagina"], 4)


class ContenidoTests(BaseSugerencias):
    def test_la_respuesta_tiene_la_forma_del_diseno(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        self.vecinas(2)

        respuesta = self.api.get(self.url(lista))

        self.assertEqual(
            set(respuesta.json()), {"results", "pagina", "paginas", "nombre_usado"}
        )
        self.assertEqual(
            set(respuesta.json()["results"][0]),
            {
                "id_tmdb",
                "tipo",
                "titulo",
                "poster",
                "anio",
                "calificacion_promedio",
                "campos_en_ingles",
                "origen",
            },
        )

    def test_no_sugiere_lo_que_ya_esta_en_la_lista(self):
        semilla = self.produccion("Semilla", vector_a(0))
        otra = self.produccion("Otra", vector_a(0.02))
        lista = self.lista_con(semilla, otra)
        self.vecinas(3)

        ids = self.ids(self.api.get(self.url(lista)))

        self.assertNotIn(("movie", semilla.id_tmdb), ids)
        self.assertNotIn(("movie", otra.id_tmdb), ids)
        self.assertEqual(len(ids), 3)

    def test_una_lista_vacia_es_200_sin_resultados_y_sin_llamar_a_tmdb(self):
        lista = self.lista_con(nombre="Pelis para llorar")

        respuesta = self.api.get(self.url(lista))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["results"], [])
        self.assertEqual(respuesta.json()["paginas"], 0)
        self.assertEqual(self.servicio.pedidos, [])
        self.vector_nombre.assert_not_called()

    def test_una_lista_solo_de_series_trae_solo_series(self):
        # D-3: la señal de «solo series» es fuerte.
        lista = self.lista_con(
            self.produccion("Serie", vector_a(0), tipo=TipoProduccion.SERIE)
        )
        pelicula = self.produccion("Peli", vector_a(0.01))
        serie = self.produccion("Otra", vector_a(0.02), tipo=TipoProduccion.SERIE)

        ids = self.ids(self.api.get(self.url(lista)))

        self.assertEqual(ids, [("tv", serie.id_tmdb)])
        self.assertNotIn(("movie", pelicula.id_tmdb), ids)

    def test_una_lista_solo_de_peliculas_trae_solo_peliculas(self):
        lista = self.lista_con(self.produccion("Peli", vector_a(0)))
        self.produccion("Serie", vector_a(0.01), tipo=TipoProduccion.SERIE)
        pelicula = self.produccion("Otra", vector_a(0.02))

        self.assertEqual(
            self.ids(self.api.get(self.url(lista))), [("movie", pelicula.id_tmdb)]
        )

    def test_una_lista_mixta_trae_las_dos_clases(self):
        lista = self.lista_con(
            self.produccion("Peli", vector_a(0)),
            self.produccion("Serie", vector_a(0.01), tipo=TipoProduccion.SERIE),
        )
        pelicula = self.produccion("Otra peli", vector_a(0.02))
        serie = self.produccion("Otra serie", vector_a(0.03), tipo=TipoProduccion.SERIE)

        ids = self.ids(self.api.get(self.url(lista)))

        self.assertCountEqual(ids, [("movie", pelicula.id_tmdb), ("tv", serie.id_tmdb)])

    def test_con_pocos_cercanos_completa_con_tmdb_desde_los_tres_ultimos_items(self):
        viejo = self.produccion("Viejo", vector_a(0))
        medio = self.produccion("Medio", vector_a(0.01))
        reciente = self.produccion("Reciente", vector_a(0.02))
        nuevo = self.produccion("Nuevo", vector_a(0.03))
        lista = ListaFactory(usuario=self.usuario, nombre="Sci Fi")
        for produccion in (viejo, medio, reciente, nuevo):
            Tiene.objects.create(lista=lista, produccion=produccion)
        self.respuestas_tmdb[(nuevo.id_tmdb, "movie")] = [item_tmdb(9001)]

        respuesta = self.api.get(self.url(lista))

        # Las semillas de TMDB son los 3 agregados más recientemente.
        self.assertEqual(
            self.servicio.pedidos,
            [
                (nuevo.id_tmdb, "movie"),
                (reciente.id_tmdb, "movie"),
                (medio.id_tmdb, "movie"),
            ],
        )
        self.assertIn(("movie", 9001), self.ids(respuesta))
        self.assertLessEqual(len(self.servicio.pedidos), similares.SEMILLAS_TMDB)

    def test_sin_vector_en_ninguna_semilla_responde_solo_tmdb(self):
        pendiente = self.produccion("Nueva", None, estado=EstadoEmbedding.PENDING)
        lista = self.lista_con(pendiente)
        self.respuestas_tmdb[(pendiente.id_tmdb, "movie")] = [item_tmdb(9001)]

        respuesta = self.api.get(self.url(lista))

        self.assertEqual(self.ids(respuesta), [("movie", 9001)])

    def test_encola_la_materializacion_de_las_tarjetas_de_tmdb_mostradas(self):
        pendiente = self.produccion("Nueva", None, estado=EstadoEmbedding.PENDING)
        lista = self.lista_con(pendiente)
        self.respuestas_tmdb[(pendiente.id_tmdb, "movie")] = [item_tmdb(9001)]

        self.api.get(self.url(lista))

        self.encolar.assert_called_once_with([{"id": 9001, "media_type": "movie"}])


class VistasTests(BaseSugerencias):
    def test_saca_las_vistas_despues_de_la_cache(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        vecinas = self.vecinas(5)
        self.assertEqual(len(self.ids(self.api.get(self.url(lista)))), 5)

        Tiene.objects.create(
            lista=self.usuario.listas.get(clave=ClaveLista.VISTAS),
            produccion=vecinas[0],
        )
        with self.assertLogs("listas.views", "INFO") as registro:
            respuesta = self.api.get(self.url(lista))

        self.assertIn("cache=True", registro.output[0])
        self.assertNotIn(("movie", vecinas[0].id_tmdb), self.ids(respuesta))
        self.assertEqual(len(self.ids(respuesta)), 4)

    def test_tambien_en_favoritos_y_sin_afectar_a_otra_persona(self):
        favoritos = self.usuario.listas.get(clave=ClaveLista.FAVORITOS)
        Tiene.objects.create(lista=favoritos, produccion=self.produccion("A", eje(0)))
        vecinas = self.vecinas(3)
        Tiene.objects.create(
            lista=self.usuario.listas.get(clave=ClaveLista.VISTAS),
            produccion=vecinas[1],
        )

        propia = self.api.get(self.url(favoritos))

        self.assertNotIn(("movie", vecinas[1].id_tmdb), self.ids(propia))
        self.assertEqual(len(self.ids(propia)), 2)
        # Otra persona con los mismos Favoritos sí lo ve: el pool no es de nadie.
        otra = UsuarioFactory()
        favoritos_ajenos = otra.listas.get(clave=ClaveLista.FAVORITOS)
        Tiene.objects.create(
            lista=favoritos_ajenos, produccion=favoritos.items.get().produccion
        )
        cliente = APIClient()
        cliente.force_authenticate(otra)
        ajena = cliente.get(self.url(favoritos_ajenos))
        self.assertIn(("movie", vecinas[1].id_tmdb), self.ids(ajena))


class NombreTests(BaseSugerencias):
    def test_un_nombre_con_tema_se_embebe_y_entra_en_el_vector(self):
        self.vector_nombre.return_value = eje(1)
        lista = self.lista_con(
            self.produccion("Semilla", eje(0)), nombre="Pelis para llorar"
        )
        # Una cerca del título y otra cerca del nombre: el nombre las reordena.
        self.produccion("Cerca del nombre", eje(1))

        respuesta = self.api.get(self.url(lista))

        self.vector_nombre.assert_called_once_with("Pelis para llorar")
        self.assertTrue(respuesta.json()["nombre_usado"])
        self.assertEqual(len(respuesta.json()["results"]), 1)

    def test_un_nombre_generico_no_se_embebe(self):
        lista = self.lista_con(self.produccion("Semilla", eje(0)), nombre="Lista 3")

        respuesta = self.api.get(self.url(lista))

        self.vector_nombre.assert_not_called()
        self.assertFalse(respuesta.json()["nombre_usado"])

    def test_favoritos_nunca_usa_su_nombre(self):
        favoritos = self.usuario.listas.get(clave=ClaveLista.FAVORITOS)
        Tiene.objects.create(lista=favoritos, produccion=self.produccion("A", eje(0)))

        respuesta = self.api.get(self.url(favoritos))

        self.vector_nombre.assert_not_called()
        self.assertFalse(respuesta.json()["nombre_usado"])

    def test_si_no_se_pudo_embeber_el_pool_dura_cinco_minutos(self):
        # `vector_del_nombre` devuelve `None` (Ollama sin cargar o caído).
        lista = self.lista_con(self.produccion("Semilla", eje(0)), nombre="Terror")
        self.vecinas(1)

        with patch.object(similares.cache, "set", wraps=similares.cache.set) as guardar:
            respuesta = self.api.get(self.url(lista))

        self.assertFalse(respuesta.json()["nombre_usado"])
        (clave, _, ttl), _ = guardar.call_args
        self.assertTrue(clave.startswith(f"similares:lista:{lista.pk}:"))
        self.assertEqual(ttl, similares.TTL_POOL_INCOMPLETO)

    def test_con_el_nombre_usado_el_pool_dura_un_dia(self):
        self.vector_nombre.return_value = eje(1)
        lista = self.lista_con(self.produccion("Semilla", eje(0)), nombre="Terror")
        self.vecinas(25)

        with patch.object(similares.cache, "set", wraps=similares.cache.set) as guardar:
            self.api.get(self.url(lista))

        (_, _, ttl), _ = guardar.call_args
        self.assertEqual(ttl, similares.TTL_POOL)

    def test_con_el_pool_en_cache_no_se_vuelve_a_pedir_el_nombre(self):
        self.vector_nombre.return_value = eje(1)
        lista = self.lista_con(self.produccion("Semilla", eje(0)), nombre="Terror")
        self.vecinas(25)

        self.api.get(self.url(lista))
        self.api.get(self.url(lista, 2))

        self.assertEqual(self.vector_nombre.call_count, 1)


class FirmaTests(BaseSugerencias):
    """La clave de caché lleva una firma: cambia con la lista, no con «Vistas»."""

    def pedir(self, lista):
        """`True` si el pedido se respondió con el pool guardado."""
        with self.assertLogs("listas.views", "INFO") as registro:
            self.api.get(self.url(lista))
        return "cache=True" in registro.output[0]

    def test_el_mismo_estado_de_la_lista_reusa_el_pool(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        self.vecinas(3)

        self.assertFalse(self.pedir(lista))
        self.assertTrue(self.pedir(lista))

    def test_agregar_un_titulo_cambia_la_firma(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        self.vecinas(3)
        self.pedir(lista)

        Tiene.objects.create(lista=lista, produccion=self.produccion("Nueva", eje(2)))

        self.assertFalse(self.pedir(lista))

    def test_quitar_un_titulo_cambia_la_firma(self):
        lista = self.lista_con(
            self.produccion("A", vector_a(0)), self.produccion("B", vector_a(0.5))
        )
        self.vecinas(3)
        self.pedir(lista)

        lista.items.first().delete()

        self.assertFalse(self.pedir(lista))

    def test_renombrar_la_lista_cambia_la_firma(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        self.vecinas(3)
        self.pedir(lista)

        lista.nombre = "Terror"
        lista.save()

        self.assertFalse(self.pedir(lista))

    def test_calificar_un_titulo_lo_agrega_a_vistas_y_no_cambia_la_firma(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        vecinas = self.vecinas(3)
        self.pedir(lista)

        Tiene.objects.create(
            lista=self.usuario.listas.get(clave=ClaveLista.VISTAS),
            produccion=vecinas[0],
        )

        self.assertTrue(self.pedir(lista))

    def test_la_clave_lleva_el_id_de_la_lista_y_una_firma_de_64_caracteres(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        self.vecinas(1)

        with patch.object(similares.cache, "set", wraps=similares.cache.set) as guardar:
            self.api.get(self.url(lista))

        (clave, _, _), _ = guardar.call_args
        self.assertRegex(clave, rf"^similares:lista:{lista.pk}:[0-9a-f]{{64}}$")

    def test_el_idioma_cambia_la_firma(self):
        lista = self.lista_con(self.produccion("Semilla", vector_a(0)))
        self.vecinas(3)
        self.api.get(self.url(lista), HTTP_ACCEPT_LANGUAGE="en")

        with self.assertLogs("listas.views", "INFO") as registro:
            self.api.get(self.url(lista), HTTP_ACCEPT_LANGUAGE="es")

        self.assertIn("cache=False", registro.output[0])
