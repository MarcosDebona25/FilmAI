"""Pruebas HTTP de «Parecidos a {título}»: `GET /api/catalogo/{movie|tv}/{id}/similar/`.

Diseño en `openspec/changes/recomendaciones-similares/design.md` §7. El motor
tiene sus propios tests (`tests_similares.py`); acá se prueba lo que agrega la
vista: quién puede pedirla, qué se cachea, qué se le saca a cada usuario y qué
cabeceras lleva la respuesta. TMDB se reemplaza por `ServicioFalso`.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from catalogo.exceptions import TMDBServerError
from catalogo.models import EstadoEmbedding, ProduccionTraduccion, TipoProduccion
from catalogo.services import similares
from catalogo.services.embeddings import MODEL_VERSION
from catalogo.tests_similares import (
    BaseSimilares,
    ServicioFalso,
    item_tmdb,
    serie_tmdb,
    vector_a,
)
from catalogo.views import CACHE_NAVEGADOR_SEGUNDOS, SimilaresView
from listas.models import ClaveLista, Tiene
from usuarios.factories import UsuarioFactory


class BaseSimilaresAPI(BaseSimilares):
    """Una semilla con 25 vecinas cercanas y TMDB reemplazado."""

    def setUp(self):
        super().setUp()
        # El pool se guarda en la caché: sin limpiarla, un test vería el del anterior.
        cache.clear()
        self.addCleanup(cache.clear)
        self.respuestas_tmdb = {}
        self.servicio = ServicioFalso(self.respuestas_tmdb)
        parche = patch("catalogo.views.get_catalog_service", return_value=self.servicio)
        parche.start()
        self.addCleanup(parche.stop)
        parche = patch(
            "catalogo.services.similares.materializar_listado_en_segundo_plano"
        )
        self.encolar = parche.start()
        self.addCleanup(parche.stop)
        self.cliente = APIClient()

    def poblar(self, vecinas=25):
        self.semilla = self.produccion("Semilla", vector_a(0))
        self.vecinas = [
            self.produccion(f"Vecina {numero}", vector_a(0.01 * (numero + 1)))
            for numero in range(vecinas)
        ]
        return f"/api/catalogo/movie/{self.semilla.id_tmdb}/similar/"

    def con_sesion(self, usuario=None):
        usuario = usuario or UsuarioFactory()
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        return usuario, cliente

    def marcar_vista(self, usuario, produccion):
        Tiene.objects.create(
            lista=usuario.listas.get(clave=ClaveLista.VISTAS), produccion=produccion
        )

    def ids(self, respuesta):
        return [(item["tipo"], item["id_tmdb"]) for item in respuesta.json()["results"]]


class SimilaresSinSesionTests(BaseSimilaresAPI):
    def test_devuelve_veinte_tarjetas_sin_la_semilla(self):
        url = self.poblar()

        respuesta = self.cliente.get(url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(list(respuesta.json()), ["results"])
        resultados = respuesta.json()["results"]
        self.assertEqual(len(resultados), 20)
        self.assertNotIn(("movie", self.semilla.id_tmdb), self.ids(respuesta))
        self.assertEqual(
            set(resultados[0]),
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

    def test_la_respuesta_se_puede_cachear_y_varia_con_el_idioma(self):
        respuesta = self.cliente.get(self.poblar())

        self.assertIn("public", respuesta["Cache-Control"])
        self.assertIn(f"max-age={CACHE_NAVEGADOR_SEGUNDOS}", respuesta["Cache-Control"])
        self.assertIn("Accept-Language", respuesta["Vary"])

    def test_mezcla_peliculas_y_series(self):
        url = self.poblar(vecinas=3)
        serie = self.produccion("Serie", vector_a(0.02), tipo=TipoProduccion.SERIE)

        respuesta = self.cliente.get(url)

        self.assertIn(("tv", serie.id_tmdb), self.ids(respuesta))
        self.assertIn(("movie", self.vecinas[0].id_tmdb), self.ids(respuesta))

    def test_la_ruta_de_series_busca_la_semilla_entre_las_series(self):
        # La película 1 y la serie 1 son títulos distintos en TMDB.
        self.poblar(vecinas=3)
        self.respuestas_tmdb[(self.semilla.id_tmdb, "tv")] = [serie_tmdb(900)]

        respuesta = self.cliente.get(
            f"/api/catalogo/tv/{self.semilla.id_tmdb}/similar/"
        )

        # Esa serie no está en el catálogo: solo responde TMDB.
        self.assertEqual(self.ids(respuesta), [("tv", 900)])

    def test_un_id_invalido_es_400_como_en_la_ficha(self):
        for valor, codigo in (
            ("abc", "invalid"),
            ("0", "min_value"),
            ("99999999999", "max_value"),
        ):
            with self.subTest(id_tmdb=valor):
                respuesta = self.cliente.get(f"/api/catalogo/movie/{valor}/similar/")

                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.json()["errors"][0]["code"], codigo)
                self.assertFalse(respuesta.has_header("Cache-Control"))
        self.assertEqual(self.servicio.pedidos, [])

    def test_usa_el_limite_de_pedidos_del_catalogo(self):
        self.assertEqual(SimilaresView.throttle_scope, "catalogo")
        url = self.poblar(vecinas=1)

        estados = [self.cliente.get(url).status_code for _ in range(62)]

        self.assertEqual(estados[59], 200)
        self.assertEqual(estados[60], 429)

    def test_registra_una_linea_por_pedido(self):
        url = self.poblar()

        with self.assertLogs("catalogo.views", "INFO") as registro:
            self.cliente.get(url)
            self.cliente.get(url)

        self.assertRegex(
            registro.output[0],
            r"similares: titulo=movie/\d+ semillas=1 cercanos=25 tmdb=0 "
            r"cache=False resultados=20 ms=\d+",
        )
        self.assertIn("cache=True", registro.output[1])

    def test_en_espanol_localiza_los_titulos_del_catalogo(self):
        url = self.poblar(vecinas=1)
        ProduccionTraduccion.objects.create(
            produccion=self.vecinas[0], idioma="es", titulo="La vecina"
        )

        en_espanol = self.cliente.get(url, HTTP_ACCEPT_LANGUAGE="es")
        en_ingles = self.cliente.get(url, HTTP_ACCEPT_LANGUAGE="en")

        self.assertEqual(en_espanol.json()["results"][0]["titulo"], "La vecina")
        self.assertEqual(
            en_espanol.json()["results"][0]["campos_en_ingles"], ["poster"]
        )
        # Cada idioma tiene su pool: el inglés no recibe el título en español.
        self.assertEqual(en_ingles.json()["results"][0]["titulo"], "Vecina 0")


class SimilaresCacheTests(BaseSimilaresAPI):
    """El pool se guarda por título, idioma y modelo; nunca por usuario."""

    def ttl_guardado(self, url, **cabeceras):
        with patch.object(similares.cache, "set", wraps=similares.cache.set) as guardar:
            respuesta = self.cliente.get(url, **cabeceras)
        self.assertEqual(respuesta.status_code, 200)
        (clave, _pool, ttl), _ = guardar.call_args
        return clave, ttl, respuesta

    def test_un_pool_completo_dura_24_horas_bajo_la_clave_del_titulo(self):
        url = self.poblar()

        clave, ttl, _ = self.ttl_guardado(url)

        self.assertEqual(
            clave, f"similares:titulo:movie:{self.semilla.id_tmdb}:en:{MODEL_VERSION}"
        )
        self.assertEqual(ttl, 24 * 3600)

    def test_el_segundo_pedido_no_recalcula(self):
        url = self.poblar()

        with patch.object(similares, "armar_pool", wraps=similares.armar_pool) as armar:
            primera = self.cliente.get(url)
            segunda = self.cliente.get(url)

        self.assertEqual(armar.call_count, 1)
        self.assertEqual(primera.json(), segunda.json())

    def test_un_titulo_que_no_esta_en_el_catalogo_responde_con_tmdb_por_10_minutos(
        self,
    ):
        self.respuestas_tmdb[(27205, "movie")] = [item_tmdb(900), item_tmdb(901)]

        _, ttl, respuesta = self.ttl_guardado("/api/catalogo/movie/27205/similar/")

        # El pool se mezcla: importa qué trae, no en qué orden.
        self.assertCountEqual(
            [(item["origen"], item["id_tmdb"]) for item in respuesta.json()["results"]],
            [("tmdb", 900), ("tmdb", 901)],
        )
        self.assertEqual(ttl, 10 * 60)

    def test_un_titulo_sin_vector_responde_con_tmdb_por_10_minutos(self):
        pendiente = self.produccion("Pendiente", None, EstadoEmbedding.PENDING)
        self.produccion("Vecina", vector_a(0.1))
        self.respuestas_tmdb[(pendiente.id_tmdb, "movie")] = [item_tmdb(900)]

        _, ttl, respuesta = self.ttl_guardado(
            f"/api/catalogo/movie/{pendiente.id_tmdb}/similar/"
        )

        self.assertEqual(self.ids(respuesta), [("movie", 900)])
        self.assertEqual(ttl, 10 * 60)

    def test_si_tmdb_falla_responde_200_con_lo_local_y_guarda_5_minutos(self):
        url = self.poblar(vecinas=4)
        self.respuestas_tmdb[(self.semilla.id_tmdb, "movie")] = TMDBServerError("x")

        _, ttl, respuesta = self.ttl_guardado(url)

        self.assertEqual(len(respuesta.json()["results"]), 4)
        self.assertEqual(ttl, 5 * 60)

    def test_con_pocos_cercanos_tmdb_completa_y_lo_mostrado_se_materializa(self):
        url = self.poblar(vecinas=4)
        self.respuestas_tmdb[(self.semilla.id_tmdb, "movie")] = [item_tmdb(900)]

        respuesta = self.cliente.get(url)

        self.assertEqual(len(respuesta.json()["results"]), 5)
        self.assertIn(("movie", 900), self.ids(respuesta))
        self.encolar.assert_called_once_with([{"id": 900, "media_type": "movie"}])

    def test_un_titulo_que_tmdb_no_conoce_responde_vacio(self):
        respuesta = self.cliente.get("/api/catalogo/movie/27205/similar/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"results": []})


class SimilaresConSesionTests(BaseSimilaresAPI):
    def test_saca_las_vistas_y_la_respuesta_es_privada(self):
        url = self.poblar()
        usuario, cliente = self.con_sesion()
        self.marcar_vista(usuario, self.vecinas[0])

        respuesta = cliente.get(url)

        self.assertEqual(len(respuesta.json()["results"]), 20)
        self.assertNotIn(("movie", self.vecinas[0].id_tmdb), self.ids(respuesta))
        self.assertIn("private", respuesta["Cache-Control"])
        self.assertNotIn("public", respuesta["Cache-Control"])
        self.assertNotIn("max-age", respuesta["Cache-Control"])

    def test_dos_usuarios_comparten_el_pool_y_cada_uno_pierde_solo_sus_vistas(self):
        url = self.poblar(vecinas=5)
        ana, cliente_ana = self.con_sesion()
        _, cliente_beto = self.con_sesion()
        self.marcar_vista(ana, self.vecinas[0])
        vista = ("movie", self.vecinas[0].id_tmdb)

        with patch.object(similares, "armar_pool", wraps=similares.armar_pool) as armar:
            de_ana = cliente_ana.get(url)
            de_beto = cliente_beto.get(url)
            sin_sesion = self.cliente.get(url)

        self.assertEqual(armar.call_count, 1)
        self.assertNotIn(vista, self.ids(de_ana))
        self.assertIn(vista, self.ids(de_beto))
        self.assertIn(vista, self.ids(sin_sesion))

    def test_una_vista_de_otro_tipo_con_el_mismo_id_no_saca_nada(self):
        url = self.poblar(vecinas=3)
        usuario, cliente = self.con_sesion()
        # Una serie con el mismo número de TMDB que la primera vecina.
        serie = self.produccion("Serie", None, EstadoEmbedding.PENDING)
        serie.id_tmdb, serie.tipo = self.vecinas[0].id_tmdb, TipoProduccion.SERIE
        serie.save()
        self.marcar_vista(usuario, serie)

        self.assertIn(("movie", self.vecinas[0].id_tmdb), self.ids(cliente.get(url)))


class SimilaresCookieTests(BaseSimilaresAPI):
    """La sesión es opcional: una cookie que no sirve no puede esconder la fila."""

    def pedir_con_cookie(self, url, valor):
        cliente = APIClient()
        cliente.cookies["access"] = valor
        return cliente.get(url)

    def test_una_cookie_valida_cuenta_como_sesion(self):
        url = self.poblar(vecinas=5)
        usuario = UsuarioFactory()
        self.marcar_vista(usuario, self.vecinas[0])

        respuesta = self.pedir_con_cookie(url, str(AccessToken.for_user(usuario)))

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn(("movie", self.vecinas[0].id_tmdb), self.ids(respuesta))
        self.assertIn("private", respuesta["Cache-Control"])

    def test_una_cookie_vencida_se_trata_como_sin_sesion(self):
        url = self.poblar(vecinas=5)
        usuario = UsuarioFactory()
        self.marcar_vista(usuario, self.vecinas[0])
        vencido = AccessToken.for_user(usuario)
        vencido.set_exp(lifetime=-timedelta(minutes=5))

        respuesta = self.pedir_con_cookie(url, str(vencido))

        # Ni 401 (Unauthorized) ni «Vistas»: es un visitante más.
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(("movie", self.vecinas[0].id_tmdb), self.ids(respuesta))
        self.assertIn("public", respuesta["Cache-Control"])

    def test_una_cookie_invalida_se_trata_como_sin_sesion(self):
        url = self.poblar(vecinas=5)

        respuesta = self.pedir_con_cookie(url, "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.x")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["results"]), 5)
        self.assertIn("public", respuesta["Cache-Control"])

    def test_la_cookie_de_un_usuario_borrado_se_trata_como_sin_sesion(self):
        url = self.poblar(vecinas=5)
        usuario = UsuarioFactory()
        token = str(AccessToken.for_user(usuario))
        usuario.delete()

        self.assertEqual(self.pedir_con_cookie(url, token).status_code, 200)

    @override_settings(DEBUG=False)
    def test_las_demas_rutas_del_catalogo_siguen_sin_mirar_la_cookie(self):
        # La ficha no autentica (`authentication_classes = []`): este cambio no
        # la toca.
        self.servicio.get_movie_detail = lambda id_tmdb: {"id": id_tmdb}
        with patch("catalogo.views.materializar_en_segundo_plano"):
            respuesta = self.pedir_con_cookie("/api/catalogo/movie/550/", "rota")

        self.assertEqual(respuesta.status_code, 200)
