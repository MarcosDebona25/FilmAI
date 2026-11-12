"""Las herramientas del chatbot: qué ve el modelo y qué se le impide.

El catálogo falso copia la forma real de las respuestas de TMDB, consultada el
05/11/2026.
"""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from catalogo.exceptions import TMDBPresupuestoAgotado
from catalogo.models import (
    ProduccionAudiovisual,
    ProduccionTraduccion,
    TipoProduccion,
)
from catalogo.services.embeddings import EmbeddingProviderError
from chatbot.tools import ESQUEMAS, FUNCIONES, ContextoTurno, ejecutar
from listas.models import ClaveLista, Lista, Tiene, TipoLista
from usuarios.factories import UsuarioFactory


def pelicula(id_tmdb, titulo="Moon", **campos):
    return {
        "id": id_tmdb,
        "title": titulo,
        "overview": "Un hombre solo en la Luna.",
        "release_date": "2009-06-12",
        "genre_ids": [18],
        "poster_path": f"/{id_tmdb}.jpg",
        "vote_average": 7.62,
        "vote_count": 100,
        "popularity": 10.0,
        **campos,
    }


def serie(id_tmdb, titulo="Dark", **campos):
    item = pelicula(id_tmdb, **campos)
    item.pop("title")
    item.pop("release_date")
    return {"name": titulo, "first_air_date": "2017-12-01", **item}


class CatalogoFalso:
    """Lo que devuelve `servicio_localizado`, con solo lo que usan las tools."""

    def __init__(self):
        self.llamadas = []
        self.resultados = {"movie": [], "tv": []}
        self.personas = []
        self.creditos = {"cast": [], "crew": []}
        self.detalle = {}

    def get_genres(self, tipo):
        return {
            "genres": [
                {"id": 18, "name": "Drama"},
                {"id": 35, "name": "Comedy"},
                {
                    "movie": {"id": 878, "name": "Science Fiction"},
                    "tv": {"id": 10765, "name": "Sci-Fi & Fantasy"},
                }[tipo],
            ]
        }

    def search(self, titulo, tipo, anio=None):
        self.llamadas.append(("search", titulo, tipo, anio))
        return {"results": self.resultados[tipo]}

    def discover(self, tipo, **filtros):
        self.llamadas.append(("discover", tipo, filtros))
        return {"results": self.resultados[tipo]}

    def get_recommendations(self, id_tmdb, tipo):
        self.llamadas.append(("recomendaciones", id_tmdb, tipo))
        return {"results": self.resultados[tipo]}

    def search_person(self, nombre):
        return {"results": self.personas}

    def get_person_credits(self, id_persona):
        self.llamadas.append(("creditos", id_persona))
        return self.creditos

    def get_movie_detail(self, id_tmdb):
        return self.detalle

    def get_tv_detail(self, id_tmdb):
        return self.detalle


class BaseTools(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(
            nombre="Juan", apellido="Perez", nombre_usuario="juanp"
        )
        self.catalogo = CatalogoFalso()
        for ruta in ("_servicio", "_servicio_en_ingles"):
            parche = patch(f"chatbot.tools.busqueda.{ruta}", return_value=self.catalogo)
            parche.start()
            self.addCleanup(parche.stop)
        self.proximo_id = 1000

    def contexto(self, idioma="en"):
        return ContextoTurno.para(self.usuario, idioma)

    def produccion(self, titulo="Moon", tipo=TipoProduccion.PELICULA, **campos):
        self.proximo_id += 1
        campos.setdefault("id_tmdb", self.proximo_id)
        return ProduccionAudiovisual.objects.create(titulo=titulo, tipo=tipo, **campos)

    def lista(self, clave=None, nombre="Mi lista", usuario=None):
        return Lista.objects.get_or_create(
            usuario=usuario or self.usuario,
            clave=clave,
            nombre=nombre,
            defaults={
                "tipo": TipoLista.PREDETERMINADA if clave else TipoLista.PERSONALIZADA
            },
        )[0]

    def marcar_vista(self, id_tmdb, tipo=TipoProduccion.PELICULA):
        Tiene.objects.create(
            lista=self.lista(ClaveLista.VISTAS, "Vistas"),
            produccion=self.produccion(id_tmdb=id_tmdb, tipo=tipo),
        )


class FormaDeLosResultadosTests(BaseTools):
    def test_una_pelicula_llega_con_los_campos_acordados(self):
        self.catalogo.resultados["movie"] = [pelicula(1)]

        resultado = ejecutar(
            self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "movie"}
        )

        self.assertEqual(
            resultado["resultados"],
            [
                {
                    "id_tmdb": 1,
                    "tipo": "movie",
                    "titulo": "Moon",
                    "anio": 2009,
                    "generos": ["Drama"],
                    "duracion": None,
                    "nota_tmdb": 7.6,
                    "sinopsis_corta": "Un hombre solo en la Luna.",
                }
            ],
        )

    def test_una_serie_usa_name_y_first_air_date(self):
        self.catalogo.resultados["tv"] = [serie(2)]

        resultado = ejecutar(
            self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "tv"}
        )

        self.assertEqual(resultado["resultados"][0]["titulo"], "Dark")
        self.assertEqual(resultado["resultados"][0]["anio"], 2017)

    def test_la_sinopsis_se_corta_a_300_caracteres(self):
        self.catalogo.resultados["movie"] = [pelicula(1, overview="a" * 400)]

        resultado = ejecutar(
            self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "movie"}
        )

        self.assertEqual(len(resultado["resultados"][0]["sinopsis_corta"]), 300)

    def test_sin_fecha_el_anio_queda_vacio(self):
        self.catalogo.resultados["movie"] = [pelicula(1, release_date="")]

        resultado = ejecutar(
            self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "movie"}
        )

        self.assertIsNone(resultado["resultados"][0]["anio"])

    def test_similares_respeta_el_orden_de_tmdb(self):
        self.catalogo.resultados["movie"] = [
            pelicula(1, popularity=1.0),
            pelicula(2, popularity=99.0),
        ]

        resultado = ejecutar(
            self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "movie"}
        )

        self.assertEqual([r["id_tmdb"] for r in resultado["resultados"]], [1, 2])

    def test_devuelve_como_mucho_10(self):
        self.catalogo.resultados["movie"] = [pelicula(i) for i in range(15)]

        resultado = ejecutar(
            self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "movie"}
        )

        self.assertEqual(len(resultado["resultados"]), 10)


class VistasTests(BaseTools):
    def test_cada_busqueda_saca_las_vistas_antes_de_que_el_modelo_las_vea(self):
        self.marcar_vista(1)
        self.catalogo.resultados["movie"] = [pelicula(1), pelicula(2, "Otra")]
        self.catalogo.personas = [{"id": 103, "name": "Mark Ruffalo"}]
        self.catalogo.creditos["cast"] = [
            {**pelicula(1), "media_type": "movie"},
            {**pelicula(2, "Otra"), "media_type": "movie"},
        ]
        llamadas = (
            ("descubrir", {"tipo": "movie"}),
            ("similares_a", {"id_tmdb": 5, "tipo": "movie"}),
            ("buscar_por_persona", {"nombre": "Mark Ruffalo"}),
        )

        for nombre, argumentos in llamadas:
            with self.subTest(nombre):
                resultado = ejecutar(self.contexto(), nombre, argumentos)

                self.assertEqual([r["id_tmdb"] for r in resultado["resultados"]], [2])

    def test_buscar_por_nombre_encuentra_lo_visto_y_lo_marca(self):
        # «Algo como Moon» necesita encontrar Moon aunque ya la haya visto.
        self.marcar_vista(1)
        self.catalogo.resultados["movie"] = [pelicula(1), pelicula(2, "Otra")]

        resultado = ejecutar(
            self.contexto(), "buscar_por_titulo", {"titulo": "Moon", "tipo": "movie"}
        )

        vista, otra = resultado["resultados"]
        self.assertIs(vista["vista"], True)
        self.assertNotIn("vista", otra)

    def test_lo_que_una_busqueda_de_recomendacion_saco_no_puede_ser_tarjeta(self):
        self.marcar_vista(1)
        self.catalogo.resultados["movie"] = [pelicula(1)]
        contexto = self.contexto()
        ejecutar(contexto, "similares_a", {"id_tmdb": 5, "tipo": "movie"})

        resultado = ejecutar(
            contexto,
            "mostrar_tarjetas",
            {"tarjetas": [{"id_tmdb": 1, "tipo": "movie"}]},
        )

        self.assertEqual(resultado["tarjetas"], [])

    def test_una_serie_con_el_id_de_una_pelicula_vista_no_se_saca(self):
        self.marcar_vista(1, TipoProduccion.PELICULA)
        self.catalogo.resultados["tv"] = [serie(1)]

        resultado = ejecutar(
            self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "tv"}
        )

        self.assertEqual(len(resultado["resultados"]), 1)

    def test_buscar_semantico_le_pasa_las_vistas_como_excluidas(self):
        self.marcar_vista(1)

        with patch(
            "chatbot.tools.busqueda.buscar_semantico", return_value=[]
        ) as buscar:
            ejecutar(self.contexto(), "buscar_semantico", {"consulta": "algo"})

        self.assertEqual(buscar.call_args.kwargs["excluir"], {(1, "movie")})


class DescubrirTests(BaseTools):
    def filtros(self, tipo="movie"):
        return next(
            llamada[2]
            for llamada in self.catalogo.llamadas
            if llamada[0] == "discover" and llamada[1] == tipo
        )

    def test_sin_tipo_busca_peliculas_y_series_y_ordena_por_popularidad(self):
        self.catalogo.resultados["movie"] = [pelicula(1, popularity=1.0)]
        self.catalogo.resultados["tv"] = [serie(2, popularity=9.0)]

        resultado = ejecutar(self.contexto(), "descubrir", {})

        self.assertEqual([r["tipo"] for r in resultado["resultados"]], ["tv", "movie"])

    def test_los_generos_se_traducen_a_ids_y_alcanza_con_uno(self):
        ejecutar(
            self.contexto(),
            "descubrir",
            {"tipo": "movie", "generos": ["Drama", "Comedy"]},
        )

        self.assertEqual(self.filtros()["genero"], "18|35")

    def test_un_genero_de_peliculas_encuentra_su_equivalente_en_series(self):
        # En TMDB la ciencia ficción se llama distinto en cada tipo.
        ejecutar(self.contexto(), "descubrir", {"generos": ["Science Fiction"]})

        self.assertEqual(self.filtros("movie")["genero"], "878")
        self.assertEqual(self.filtros("tv")["genero"], "10765")

    def test_un_genero_que_el_tipo_no_tiene_no_devuelve_cualquier_cosa(self):
        self.catalogo.resultados["tv"] = [serie(2)]

        resultado = ejecutar(
            self.contexto(), "descubrir", {"tipo": "tv", "generos": ["Horror"]}
        )

        self.assertEqual(resultado["resultados"], [])

    def test_la_nota_minima_pide_un_minimo_de_votos(self):
        ejecutar(self.contexto(), "descubrir", {"tipo": "movie", "nota_minima": 7})

        self.assertEqual(self.filtros()["min_rating"], 7)
        self.assertGreater(self.filtros()["min_votos"], 0)

    def test_la_duracion_sin_tipo_solo_busca_peliculas(self):
        # TMDB casi no tiene la duración de las series.
        ejecutar(self.contexto(), "descubrir", {"duracion_max": 120})

        self.assertEqual([llamada[1] for llamada in self.catalogo.llamadas], ["movie"])
        self.assertEqual(self.filtros()["duracion_max"], 120)

    def test_pedir_series_con_duracion_ignora_la_duracion(self):
        ejecutar(self.contexto(), "descubrir", {"tipo": "tv", "duracion_max": 30})

        self.assertIsNone(self.filtros("tv")["duracion_max"])


class BuscarPorPersonaTests(BaseTools):
    def setUp(self):
        super().setUp()
        self.catalogo.personas = [{"id": 525, "name": "Christopher Nolan"}]
        self.catalogo.creditos = {
            "cast": [
                {**pelicula(1, "Actuada"), "media_type": "movie", "vote_count": 5}
            ],
            "crew": [
                {
                    **pelicula(2, "Interstellar"),
                    "media_type": "movie",
                    "job": "Director",
                    "vote_count": 90,
                },
                {
                    **pelicula(2, "Interstellar"),
                    "media_type": "movie",
                    "job": "Writer",
                    "vote_count": 90,
                },
                {
                    **pelicula(3, "Producida"),
                    "media_type": "movie",
                    "job": "Producer",
                    "vote_count": 80,
                },
                {
                    **serie(4, "Dirigida"),
                    "media_type": "tv",
                    "job": "Director",
                    "vote_count": 10,
                },
            ],
        }

    def titulos(self, **argumentos):
        resultado = ejecutar(
            self.contexto(), "buscar_por_persona", {"nombre": "Nolan", **argumentos}
        )
        return [r["titulo"] for r in resultado["resultados"]]

    def test_sin_rol_trae_actuacion_y_direccion_lo_mas_votado_primero(self):
        self.assertEqual(self.titulos(), ["Interstellar", "Dirigida", "Actuada"])

    def test_rol_actor(self):
        self.assertEqual(self.titulos(rol="actor"), ["Actuada"])

    def test_rol_director_incluye_series(self):
        self.assertEqual(self.titulos(rol="director"), ["Interstellar", "Dirigida"])

    def test_dice_a_que_persona_encontro(self):
        resultado = ejecutar(self.contexto(), "buscar_por_persona", {"nombre": "Nolan"})

        self.assertEqual(resultado["persona"], "Christopher Nolan")

    def test_una_persona_que_no_existe_no_es_un_error(self):
        self.catalogo.personas = []

        resultado = ejecutar(self.contexto(), "buscar_por_persona", {"nombre": "Nadie"})

        self.assertEqual(resultado, {"persona": None, "resultados": []})


class DetalleTests(BaseTools):
    def test_un_titulo_visto_pedido_directamente_se_puede_mostrar(self):
        self.marcar_vista(1)
        self.catalogo.detalle = pelicula(
            1, runtime=97, genres=[{"id": 18, "name": "Drama"}]
        )
        contexto = self.contexto()

        resultado = ejecutar(contexto, "detalle", {"id_tmdb": 1, "tipo": "movie"})
        tarjetas = ejecutar(
            contexto,
            "mostrar_tarjetas",
            {"tarjetas": [{"id_tmdb": 1, "tipo": "movie"}]},
        )

        self.assertEqual(resultado["duracion"], 97)
        self.assertEqual(resultado["generos"], ["Drama"])
        self.assertIs(resultado["vista"], True)
        self.assertEqual([t["id_tmdb"] for t in tarjetas["tarjetas"]], [1])


class BuscarSemanticoTests(BaseTools):
    def buscar(self, contexto, producciones, **argumentos):
        with patch(
            "chatbot.tools.busqueda.buscar_semantico", return_value=producciones
        ) as buscar:
            resultado = ejecutar(
                contexto, "buscar_semantico", {"consulta": "algo", **argumentos}
            )
        return resultado, buscar

    def test_convierte_la_produccion_con_tipo_de_tmdb(self):
        moon = self.produccion(
            "Moon",
            id_tmdb=17431,
            fecha_lanzamiento=date(2009, 6, 12),
            duracion=97,
            calificacion_promedio=7.62,
            generos=["Drama"],
            sinopsis="Un hombre solo.",
        )

        resultado, _ = self.buscar(self.contexto(), [moon])

        self.assertEqual(
            resultado["resultados"],
            [
                {
                    "id_tmdb": 17431,
                    "tipo": "movie",
                    "titulo": "Moon",
                    "anio": 2009,
                    "generos": ["Drama"],
                    "duracion": 97,
                    "nota_tmdb": 7.6,
                    "sinopsis_corta": "Un hombre solo.",
                }
            ],
        )

    def test_usa_el_titulo_en_el_idioma_del_turno(self):
        moon = self.produccion("Moon")
        ProduccionTraduccion.objects.create(
            produccion=moon, idioma="es", titulo="Luna", sinopsis="Sola."
        )

        resultado, _ = self.buscar(self.contexto("es"), [moon])

        self.assertEqual(resultado["resultados"][0]["titulo"], "Luna")
        self.assertEqual(resultado["resultados"][0]["sinopsis_corta"], "Sola.")

    def test_amplia_el_genero_a_su_equivalente_de_series(self):
        _, buscar = self.buscar(self.contexto(), [], generos=["Science Fiction"])

        self.assertCountEqual(
            buscar.call_args.kwargs["generos"], ["Science Fiction", "Sci-Fi & Fantasy"]
        )

    def test_pasa_los_filtros(self):
        _, buscar = self.buscar(
            self.contexto(),
            [],
            tipo="tv",
            anio_desde=2000,
            anio_hasta=2010,
            nota_minima=7,
            duracion_max=60,
        )

        filtros = buscar.call_args.kwargs
        self.assertEqual(filtros["tipo"], "tv")
        self.assertEqual(filtros["anio_desde"], 2000)
        self.assertEqual(filtros["anio_hasta"], 2010)
        self.assertEqual(filtros["nota_minima"], 7)
        self.assertEqual(filtros["duracion_max"], 60)


class MostrarTarjetasTests(BaseTools):
    def contexto_con_resultados(self, cantidad=5):
        self.catalogo.resultados["movie"] = [
            pelicula(i, f"T{i}") for i in range(1, cantidad + 1)
        ]
        contexto = self.contexto()
        ejecutar(contexto, "similares_a", {"id_tmdb": 99, "tipo": "movie"})
        return contexto

    def mostrar(self, contexto, *ids, tipo="movie"):
        return ejecutar(
            contexto,
            "mostrar_tarjetas",
            {"tarjetas": [{"id_tmdb": i, "tipo": tipo} for i in ids]},
        )

    def test_arma_la_tarjeta_del_contrato(self):
        contexto = self.contexto_con_resultados()

        self.mostrar(contexto, 1)

        self.assertEqual(
            contexto.tarjetas,
            [
                {
                    "id_tmdb": 1,
                    "tipo": "movie",
                    "titulo": "T1",
                    "poster": "/1.jpg",
                    "anio": 2009,
                    "nota_tmdb": 7.6,
                }
            ],
        )

    def test_descarta_lo_que_ninguna_tool_devolvio(self):
        contexto = self.contexto_con_resultados()

        resultado = self.mostrar(contexto, 1, 777)

        self.assertEqual([t["id_tmdb"] for t in resultado["tarjetas"]], [1])

    def test_el_mismo_id_de_otro_tipo_no_cuenta_como_visto_en_el_turno(self):
        contexto = self.contexto_con_resultados()

        resultado = self.mostrar(contexto, 1, tipo="tv")

        self.assertEqual(resultado["tarjetas"], [])

    def test_descarta_duplicados(self):
        contexto = self.contexto_con_resultados()

        resultado = self.mostrar(contexto, 1, 1)

        self.assertEqual(len(resultado["tarjetas"]), 1)

    def test_el_tope_de_3_vale_entre_varias_llamadas(self):
        contexto = self.contexto_con_resultados()

        self.mostrar(contexto, 1, 2)
        resultado = self.mostrar(contexto, 2, 3, 4)

        self.assertEqual([t["id_tmdb"] for t in resultado["tarjetas"]], [1, 2, 3])

    def test_una_tarjeta_mal_armada_es_un_error_y_no_suma_ninguna(self):
        # Antes se descartaba solo la mala. Ahora `ejecutar()` rechaza el pedido
        # entero y el modelo lo corrige; si era la última vuelta, la red del
        # orquestador arma las tarjetas desde el texto.
        contexto = self.contexto_con_resultados()

        resultado = ejecutar(
            contexto,
            "mostrar_tarjetas",
            {
                "tarjetas": [
                    {"id_tmdb": "x", "tipo": "movie"},
                    {"id_tmdb": 1, "tipo": "movie"},
                ]
            },
        )

        self.assertEqual(resultado["error"], "invalid_arguments")
        self.assertEqual(contexto.tarjetas, [])


class MisListasTests(BaseTools):
    def test_sin_argumentos_devuelve_las_listas_del_usuario(self):
        lista = self.lista(nombre="Para el finde")
        self.lista(nombre="Ajena", usuario=UsuarioFactory())

        resultado = ejecutar(self.contexto(), "mis_listas", {})

        self.assertIn({"id": lista.pk, "nombre": "Para el finde"}, resultado["listas"])
        self.assertNotIn("Ajena", str(resultado))

    def test_el_nombre_de_la_lista_llega_anonimizado(self):
        self.lista(nombre="Cumple de Juan Perez")

        resultado = ejecutar(self.contexto(), "mis_listas", {})

        self.assertIn("Cumple de [usuario]", str(resultado))
        self.assertNotIn("Juan", str(resultado))

    def test_lee_una_predeterminada_por_clave(self):
        lista = self.lista(ClaveLista.PENDIENTES, "Pendientes")
        Tiene.objects.create(lista=lista, produccion=self.produccion("Moon"))

        resultado = ejecutar(self.contexto(), "mis_listas", {"lista": "pendientes"})

        self.assertEqual(resultado["resultados"][0]["titulo"], "Moon")

    def test_lee_una_personalizada_por_id(self):
        lista = self.lista(nombre="Cumple de Juan")
        Tiene.objects.create(lista=lista, produccion=self.produccion("Moon"))

        resultado = ejecutar(self.contexto(), "mis_listas", {"lista": str(lista.pk)})

        self.assertEqual(resultado["lista"], "Cumple de [usuario]")
        self.assertEqual(resultado["resultados"][0]["titulo"], "Moon")

    def test_el_id_de_una_lista_ajena_no_se_encuentra(self):
        ajena = self.lista(nombre="Ajena", usuario=UsuarioFactory())

        resultado = ejecutar(self.contexto(), "mis_listas", {"lista": str(ajena.pk)})

        self.assertEqual(resultado, {"error": "not_found"})

    def test_la_clave_de_otro_usuario_no_se_confunde(self):
        otra = self.lista(ClaveLista.FAVORITOS, "Favoritos", usuario=UsuarioFactory())
        Tiene.objects.create(lista=otra, produccion=self.produccion("Ajena"))

        resultado = ejecutar(self.contexto(), "mis_listas", {"lista": "favoritos"})

        self.assertEqual(resultado["resultados"], [])

    def test_un_titulo_de_una_lista_se_puede_mostrar_como_tarjeta(self):
        lista = self.lista(ClaveLista.PENDIENTES, "Pendientes")
        moon = self.produccion("Moon", poster="/m.jpg")
        Tiene.objects.create(lista=lista, produccion=moon)
        contexto = self.contexto()

        ejecutar(contexto, "mis_listas", {"lista": "pendientes"})
        resultado = ejecutar(
            contexto,
            "mostrar_tarjetas",
            {"tarjetas": [{"id_tmdb": moon.id_tmdb, "tipo": "movie"}]},
        )

        self.assertEqual(resultado["tarjetas"][0]["poster"], "/m.jpg")


class FallosTests(BaseTools):
    def test_una_tool_que_explota_no_termina_el_turno(self):
        with patch.object(
            self.catalogo, "get_recommendations", side_effect=RuntimeError("x")
        ):
            resultado = ejecutar(
                self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "movie"}
            )

        self.assertEqual(resultado, {"error": "tool_failed"})

    def test_el_tope_de_llamadas_a_tmdb_es_un_error_de_tool(self):
        with patch.object(
            self.catalogo,
            "get_recommendations",
            side_effect=TMDBPresupuestoAgotado("tope"),
        ):
            resultado = ejecutar(
                self.contexto(), "similares_a", {"id_tmdb": 5, "tipo": "movie"}
            )

        self.assertEqual(resultado, {"error": "tool_failed"})

    def test_ollama_caido_es_un_error_de_tool(self):
        with patch(
            "chatbot.tools.busqueda.buscar_semantico",
            side_effect=EmbeddingProviderError("caído"),
        ):
            resultado = ejecutar(self.contexto(), "buscar_semantico", {"consulta": "a"})

        self.assertEqual(resultado, {"error": "tool_failed"})

    def test_una_tool_que_no_existe_no_rompe_nada(self):
        self.assertEqual(
            ejecutar(self.contexto(), "borrar_todo", {}), {"error": "tool_failed"}
        )

    def test_argumentos_que_la_tool_no_conoce_no_rompen_nada(self):
        resultado = ejecutar(self.contexto(), "detalle", {"usuario": 1})

        self.assertEqual(resultado["error"], "invalid_arguments")


class ValidacionDeArgumentosTests(BaseTools):
    """`ejecutar()` revisa los argumentos contra el esquema antes de correr la tool.

    El modelo puede mandar cualquier cosa: un género en español, un `tipo` que no
    existe o un id que no es número. Sin esta revisión, la tool fallaba en silencio
    o, peor, buscaba sin el filtro que el usuario pidió.
    """

    def correr(self, nombre, argumentos):
        llamada = patch.dict(FUNCIONES, {nombre: self.tool_espia})
        self.llamadas = []
        with llamada:
            return ejecutar(self.contexto(), nombre, argumentos)

    def tool_espia(self, ctx, **argumentos):
        self.llamadas.append(argumentos)
        return {"resultados": []}

    def test_un_genero_en_espanol_en_semantico_es_un_error(self):
        resultado = self.correr(
            "buscar_semantico", {"consulta": "naves", "generos": ["Ciencia ficción"]}
        )

        self.assertEqual(resultado["error"], "invalid_arguments")
        self.assertIn("generos", resultado["detalle"])
        self.assertEqual(self.llamadas, [])

    def test_un_genero_en_espanol_en_descubrir_es_un_error(self):
        # Antes se descartaba en silencio y la búsqueda salía sin filtro.
        resultado = self.correr("descubrir", {"generos": ["Comedia"]})

        self.assertEqual(resultado["error"], "invalid_arguments")
        self.assertEqual(self.llamadas, [])

    def test_el_error_le_dice_al_modelo_los_valores_validos(self):
        resultado = self.correr("descubrir", {"generos": ["Comedia"]})

        self.assertIn("Comedy", resultado["detalle"])

    def test_un_tipo_que_no_existe_es_un_error(self):
        resultado = self.correr("detalle", {"id_tmdb": 5, "tipo": "person"})

        self.assertEqual(resultado["error"], "invalid_arguments")
        self.assertIn("tipo", resultado["detalle"])

    def test_un_id_que_no_es_numero_es_un_error(self):
        resultado = self.correr("detalle", {"id_tmdb": "abc", "tipo": "movie"})

        self.assertEqual(resultado["error"], "invalid_arguments")
        self.assertIn("id_tmdb", resultado["detalle"])

    def test_falta_un_argumento_obligatorio(self):
        resultado = self.correr("similares_a", {"id_tmdb": 5})

        self.assertEqual(resultado["error"], "invalid_arguments")
        self.assertIn("tipo", resultado["detalle"])

    def test_un_null_cuenta_como_no_mandado(self):
        # Algunos modelos mandan `null` en los opcionales: la tool recibe lo mismo
        # que si no hubieran venido.
        resultado = self.correr("descubrir", {"tipo": None, "generos": ["Drama"]})

        self.assertEqual(resultado, {"resultados": []})
        self.assertEqual(self.llamadas, [{"generos": ["Drama"]}])

    def test_un_llamado_valido_llega_a_la_tool(self):
        argumentos = {"consulta": "algo tranquilo", "generos": ["Drama"], "tipo": "tv"}

        resultado = self.correr("buscar_semantico", argumentos)

        self.assertEqual(resultado, {"resultados": []})
        self.assertEqual(self.llamadas, [argumentos])


class EsquemasTests(BaseTools):
    def test_cada_esquema_tiene_su_funcion_y_al_reves(self):
        nombres = {esquema["function"]["name"] for esquema in ESQUEMAS}

        self.assertEqual(nombres, set(FUNCIONES))

    def test_ninguna_tool_recibe_un_usuario(self):
        # `mis_listas` lee del contexto: el modelo no puede pedir datos de otro.
        for esquema in ESQUEMAS:
            propiedades = esquema["function"]["parameters"]["properties"]
            self.assertNotIn("usuario", propiedades)
            self.assertNotIn("usuario_id", propiedades)
