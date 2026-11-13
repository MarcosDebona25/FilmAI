"""El orquestador con un modelo de mentira: qué entrega y qué le manda al proveedor.

Son tests `async def` en el `TestCase` de Django, no `IsolatedAsyncioTestCase`: así
el código que corre en `en_hilo` ve la transacción del test.
"""

import json
from datetime import date
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from catalogo.models import Calificacion, ProduccionAudiovisual, TipoProduccion
from catalogo.presupuesto import contar_llamadas, registrar_llamada
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.llm import (
    LlamadaTool,
    ProveedorFalso,
    ProveedorOpenAICompatible,
    Vuelta,
    crear_proveedor,
    leer_stream,
)
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.orquestador import _LARGO_DE_PREAMBULO, responder
from chatbot.prompts import armar_sistema
from chatbot.tools import FUNCIONES, ContextoTurno
from chatbot.tools.turno import publicar, titulo
from listas.models import ClaveLista, Lista, Tiene, TipoLista
from usuarios.factories import UsuarioFactory


def tool(nombre, _id="1", **argumentos):
    return LlamadaTool(_id, nombre, json.dumps(argumentos))


def tarjetas(*ids):
    pedidas = [{"id_tmdb": i, "tipo": "movie"} for i in ids]
    return tool("mostrar_tarjetas", "t", tarjetas=pedidas)


class BaseOrquestador(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(
            nombre="Juan", apellido="Perez", nombre_usuario="juanp"
        )
        self.chat = Chat.objects.get(usuario=self.usuario)
        # Una tool de búsqueda de mentira: anota un título, como haría la real.
        parche = patch.dict(FUNCIONES, {"descubrir": self.buscar_de_mentira})
        parche.start()
        self.addCleanup(parche.stop)

    @staticmethod
    def buscar_de_mentira(ctx, **argumentos):
        ctx.encontrados[(1, "movie")] = {
            "id_tmdb": 1,
            "tipo": "movie",
            "titulo": "Moon",
            "poster": "/m.jpg",
            "anio": 2009,
        }
        return {"resultados": [{"id_tmdb": 1, "titulo": "Moon"}]}

    async def correr(self, guion, texto="hola", idioma="es", **falso):
        self.proveedor = ProveedorFalso(guion, **falso)
        return [
            evento
            async for evento in responder(
                self.chat, texto, idioma, proveedor=self.proveedor
            )
        ]

    def mensajes_del_primer_pedido(self):
        return self.proveedor.pedidos[0]


class RespuestaSimpleTests(BaseOrquestador):
    async def test_el_texto_sale_de_a_pedazos_y_cierra_con_un_resultado(self):
        eventos = await self.correr([["Hola ", "che"]])

        self.assertEqual(
            eventos, [Texto("Hola "), Texto("che"), Resultado("Hola che", [])]
        )

    async def test_no_guarda_nada(self):
        # Guardar es de la vista: el orquestador solo entrega eventos.
        await self.correr([["Hola"]])

        self.assertEqual(await Mensaje.objects.acount(), 0)

    async def test_una_respuesta_vacia_y_una_ultima_llamada_vacia_es_un_error(self):
        # Sin texto hay una última llamada de rescate; si también vuelve vacía, error.
        with self.assertRaises(ErrorDelTurno):
            await self.correr([[], []])


class VueltaConToolsTests(BaseOrquestador):
    async def test_avisa_que_busca_y_le_devuelve_el_resultado_al_modelo(self):
        eventos = await self.correr([[tool("descubrir")], ["Te recomiendo Moon"]])

        self.assertEqual(eventos[0], Estado("searching"))
        self.assertEqual(eventos[-1], Resultado("Te recomiendo Moon", []))
        asistente, resultado = self.proveedor.pedidos[1][-2:]
        self.assertEqual(asistente["tool_calls"][0]["function"]["name"], "descubrir")
        self.assertEqual(resultado["role"], "tool")
        self.assertEqual(resultado["tool_call_id"], "1")
        self.assertIn("Moon", resultado["content"])

    async def test_las_tarjetas_de_una_vuelta_del_medio_llegan_al_resultado(self):
        eventos = await self.correr([[tool("descubrir")], [tarjetas(1)], ["Mirá esta"]])

        self.assertEqual(eventos[-1].tarjetas[0]["titulo"], "Moon")
        self.assertEqual(sum(isinstance(e, Resultado) for e in eventos), 1)
        self.assertIsInstance(eventos[-2], Texto)

    async def test_texto_con_solo_tarjetas_cierra_sin_otra_llamada(self):
        # Ahorra una llamada entera, y evita que el modelo repita la respuesta.
        eventos = await self.correr([[tool("descubrir")], ["Mirá esta", tarjetas(1)]])

        self.assertEqual(len(self.proveedor.pedidos), 2)
        self.assertEqual(eventos[-1].texto, "Mirá esta")
        self.assertEqual(len(eventos[-1].tarjetas), 1)

    async def test_mostrar_tarjetas_sola_no_avisa_que_busca(self):
        eventos = await self.correr([[tool("descubrir")], ["Esta", tarjetas(1)]])

        self.assertEqual(sum(isinstance(e, Estado) for e in eventos), 1)

    async def test_el_texto_de_dos_vueltas_no_queda_pegado(self):
        # Un texto largo antes de buscar ya salió al front: el que sigue va aparte.
        largo = "x" * (_LARGO_DE_PREAMBULO + 1)
        eventos = await self.correr([[largo, tool("descubrir")], ["Listo."]])

        self.assertEqual(eventos[-1].texto, f"{largo}\n\nListo.")
        pedazos = "".join(e.delta for e in eventos if isinstance(e, Texto))
        self.assertEqual(pedazos, eventos[-1].texto)

    async def test_un_preambulo_antes_de_buscar_no_llega_al_usuario(self):
        # «I'll look that up.» y después la respuesta: el prompt lo prohíbe, pero
        # el modelo a veces lo escribe igual.
        eventos = await self.correr(
            [["I'll look ", "that up.", tool("descubrir")], ["Te recomiendo Moon"]]
        )

        self.assertEqual(eventos[-1].texto, "Te recomiendo Moon")
        pedazos = "".join(e.delta for e in eventos if isinstance(e, Texto))
        self.assertEqual(pedazos, "Te recomiendo Moon")

    async def test_el_preambulo_sigue_en_lo_que_ve_el_modelo(self):
        # El modelo tiene que ver lo que dijo, o la charla que recibe no cierra.
        await self.correr([["Busco.", tool("descubrir")], ["Listo."]])

        self.assertEqual(self.proveedor.pedidos[1][-2]["content"], "Busco.")

    async def test_el_texto_con_tarjetas_no_es_un_preambulo(self):
        eventos = await self.correr([[tool("descubrir")], ["Mirá", tarjetas(1)]])

        self.assertEqual(eventos[-1].texto, "Mirá")

    async def test_el_texto_con_tarjetas_y_otra_busqueda_no_es_un_preambulo(self):
        # Las tarjetas de esta vuelta se muestran: la frase que las acompaña también.
        guion = [[tool("descubrir")], ["Mirá", tool("descubrir", "2"), tarjetas(1)]]
        eventos = await self.correr([*guion, ["Listo"]])

        self.assertTrue(eventos[-1].texto.startswith("Mirá"))

    async def test_el_texto_que_cruza_el_umbral_despues_de_otra_vuelta_no_duplica_el_separador(
        self,
    ):
        # La primera vuelta ya salió al front; en la segunda, dos trozos cruzan el
        # umbral juntos: el separador va una sola vez y no se reenvía lo ya emitido.
        largo = "x" * (_LARGO_DE_PREAMBULO + 1)
        primero, segundo = "y" * 150, "z" * 100
        eventos = await self.correr([[largo, tool("descubrir")], [primero, segundo]])

        esperado = f"{largo}\n\n{primero}{segundo}"
        self.assertEqual(eventos[-1].texto, esperado)
        pedazos = "".join(e.delta for e in eventos if isinstance(e, Texto))
        self.assertEqual(pedazos, esperado)
        self.assertEqual(pedazos.count("\n\n"), 1)

    async def test_varias_tools_en_una_vuelta_responden_en_orden(self):
        await self.correr([[tool("descubrir", "a"), tool("descubrir", "b")], ["Listo"]])

        ids = [m["tool_call_id"] for m in self.proveedor.pedidos[1][-2:]]
        self.assertEqual(ids, ["a", "b"])

    async def test_con_thinking_devuelve_el_razonamiento_al_proveedor(self):
        await self.correr(
            [[tool("descubrir")], ["Listo"]], razonamiento="pensando en Moon"
        )

        asistente = self.proveedor.pedidos[1][-2]
        self.assertEqual(asistente["reasoning_content"], "pensando en Moon")

    async def test_sin_thinking_no_manda_razonamiento(self):
        await self.correr([[tool("descubrir")], ["Listo"]])

        self.assertNotIn("reasoning_content", self.proveedor.pedidos[1][-2])


def pelicula_de_mentira(id_tmdb, nombre, anio=2009, tipo="movie"):
    return titulo(
        id_tmdb=id_tmdb,
        tipo=tipo,
        nombre=nombre,
        anio=anio,
        generos=["Drama"],
        duracion=None,
        nota=7.0,
        sinopsis="",
        poster=f"/{id_tmdb}.jpg",
    )


class RedDeTarjetasTests(BaseOrquestador):
    """Si el modelo recomienda en el texto y no llama a `mostrar_tarjetas`, las
    tarjetas las arma el orquestador con los títulos que nombró.

    En el set dorado del 08/11/2026 solo 3 de 8 recomendaciones tenían tarjetas.
    """

    def setUp(self):
        super().setUp()
        # Búsquedas de mentira que pasan por `publicar()`, como las reales: así
        # queda anotado qué títulos salieron de una búsqueda para recomendar.
        self.peliculas = [
            pelicula_de_mentira(1, "Moon"),
            pelicula_de_mentira(2, "Arrival", 2016),
            pelicula_de_mentira(3, "Her", 2013),
            pelicula_de_mentira(4, "Solaris", 1972),
            pelicula_de_mentira(5, "Interstellar", 2014),
        ]
        parche = patch.dict(
            FUNCIONES,
            {
                "descubrir": lambda ctx, **_: {
                    "resultados": publicar(ctx, self.peliculas)
                },
                "buscar_por_titulo": lambda ctx, **_: {
                    "resultados": publicar(ctx, self.peliculas, sacar_vistas=False)
                },
            },
        )
        parche.start()
        self.addCleanup(parche.stop)

    def ids(self, eventos):
        return [t["id_tmdb"] for t in eventos[-1].tarjetas]

    async def test_nombra_titulos_sin_mostrarlos_y_aparecen_las_tarjetas(self):
        eventos = await self.correr(
            [[tool("descubrir")], ["Te recomiendo **Arrival** y también **Moon**."]]
        )

        self.assertEqual(self.ids(eventos), [2, 1])
        self.assertEqual(eventos[-1].tarjetas[0]["titulo"], "Arrival")

    async def test_la_respuesta_de_la_ultima_llamada_tambien_arma_tarjetas(self):
        guion = [[tool("descubrir")] for _ in range(5)]
        guion += [["Después de buscar, te va a gustar **Arrival**."]]

        eventos = await self.correr(guion)

        self.assertEqual(self.ids(eventos), [2])

    async def test_si_el_modelo_mostro_tarjetas_no_se_agrega_nada(self):
        eventos = await self.correr(
            [[tool("descubrir")], ["Mirá Arrival, Moon y Solaris.", tarjetas(1)]]
        )

        self.assertEqual(self.ids(eventos), [1])

    async def test_un_titulo_de_una_consulta_directa_no_se_vuelve_tarjeta(self):
        # «¿Cuánto dura Interstellar?»: es un dato, no una recomendación.
        eventos = await self.correr(
            [[tool("buscar_por_titulo")], ["Interstellar dura 169 minutos."]]
        )

        self.assertEqual(eventos[-1].tarjetas, [])

    async def test_un_titulo_visto_no_se_vuelve_tarjeta(self):
        produccion = await ProduccionAudiovisual.objects.acreate(
            id_tmdb=1, tipo=TipoProduccion.PELICULA, titulo="Moon"
        )
        vistas, _ = await Lista.objects.aget_or_create(
            usuario=self.usuario,
            clave=ClaveLista.VISTAS,
            defaults={"nombre": "Vistas", "tipo": TipoLista.PREDETERMINADA},
        )
        await Tiene.objects.acreate(lista=vistas, produccion=produccion)

        eventos = await self.correr(
            [[tool("descubrir")], ["Como ya viste Moon, probá **Arrival**."]]
        )

        self.assertEqual(self.ids(eventos), [2])

    async def test_sin_acentos_ni_mayusculas(self):
        self.peliculas = [pelicula_de_mentira(7, "El Laberinto del Fauno", 2006)]

        eventos = await self.correr(
            [[tool("descubrir")], ["Probá **el laberinto del fauno**, es hermosa."]]
        )

        self.assertEqual(self.ids(eventos), [7])

    async def test_el_apostrofo_curvo_vale_como_el_recto(self):
        # TMDB escribe «Ocean's Eleven» con el apóstrofo recto y el modelo a veces con
        # el curvo, U+2019 (PR-Agent en
        # #187). Para el lector es la misma letra, así que tiene que coincidir.
        self.peliculas = [pelicula_de_mentira(8, "Ocean's Eleven", 2001)]

        eventos = await self.correr(
            [[tool("descubrir")], ["Probá **Ocean\u2019s Eleven**, es muy divertida."]]
        )

        self.assertEqual(self.ids(eventos), [8])

    async def test_un_titulo_corto_no_se_confunde_con_una_palabra(self):
        eventos = await self.correr(
            [[tool("descubrir")], ["Show her the way to **Solaris**, the classic."]]
        )

        self.assertEqual(self.ids(eventos), [4])

    async def test_un_titulo_corto_en_negrita_si_cuenta(self):
        eventos = await self.correr([[tool("descubrir")], ["Te va a gustar **Her**."]])

        self.assertEqual(self.ids(eventos), [3])

    async def test_un_titulo_corto_no_cuenta_pegado_a_un_apostrofo_o_un_guion(self):
        # «It's» y «Up-to-date» no nombran a «It» ni a «Up» (PR-Agent en #187).
        self.peliculas = [
            pelicula_de_mentira(8, "It", 2017),
            pelicula_de_mentira(9, "Up", 2009),
        ]

        eventos = await self.correr(
            [
                [tool("descubrir")],
                ["It\u2019s a classic, and it's up-to-date: Up-to-date."],
            ]
        )

        self.assertEqual(eventos[-1].tarjetas, [])

    async def test_un_titulo_corto_sin_negrita_no_cuenta(self):
        # «Her latest film…» o «It is…» al empezar una oración: escrito igual que el
        # título, pero no lo nombra. El modelo pone los títulos en negrita.
        eventos = await self.correr(
            [[tool("descubrir")], ["Her latest film is great. Te va a gustar Her."]]
        )

        self.assertEqual(eventos[-1].tarjetas, [])

    async def test_un_titulo_adentro_de_otro_mas_largo_no_cuenta(self):
        # Gana el más largo: la tarjeta tiene que mostrar lo que dice el texto.
        self.peliculas = [
            pelicula_de_mentira(10, "Dune", 2021),
            pelicula_de_mentira(11, "Dune: Part Two", 2024),
            pelicula_de_mentira(12, "Blade Runner", 1982),
            pelicula_de_mentira(13, "Blade Runner 2049", 2017),
        ]

        eventos = await self.correr(
            [[tool("descubrir")], ["Probá **Dune: Part Two** y **Blade Runner 2049**."]]
        )

        self.assertEqual(self.ids(eventos), [11, 13])

    async def test_un_titulo_largo_sin_negrita_no_cuenta(self):
        # Ahora la negrita vale para todos los títulos, no solo los cortos: un
        # título suelto en la prosa («Probá Arrival…») puede no ser una recomendación.
        eventos = await self.correr(
            [[tool("descubrir")], ["Probá Arrival, o mejor **Moon**."]]
        )

        self.assertEqual(self.ids(eventos), [1])

    async def test_el_titulo_en_negrita_cuenta_aunque_haya_otro_mas_largo_sin_negrita(
        self,
    ):
        self.peliculas = [
            pelicula_de_mentira(10, "Dune", 2021),
            pelicula_de_mentira(11, "Dune: Part Two", 2024),
        ]

        eventos = await self.correr(
            [[tool("descubrir")], ["Empezá por **Dune** y seguí con Dune: Part Two."]]
        )

        self.assertEqual(self.ids(eventos), [10])

    async def test_no_cuenta_dentro_de_otra_palabra(self):
        eventos = await self.correr([[tool("descubrir")], ["Algo lunar: Moonlight."]])

        self.assertEqual(eventos[-1].tarjetas, [])

    async def test_van_en_orden_de_aparicion_y_como_mucho_3(self):
        eventos = await self.correr(
            [
                [tool("descubrir")],
                [
                    "**Interstellar**, **Solaris**, **Moon** y **Arrival**: las cuatro van."
                ],
            ]
        )

        self.assertEqual(self.ids(eventos), [5, 4, 1])

    async def test_las_tarjetas_armadas_son_las_mismas_que_las_del_modelo(self):
        armadas = await self.correr([[tool("descubrir")], ["Probá **Moon**."]])
        self.chat = await Chat.objects.aget(pk=self.chat.pk)
        elegidas = await self.correr(
            [[tool("descubrir")], ["Probá **Moon**.", tarjetas(1)]]
        )

        self.assertEqual(armadas[-1].tarjetas, elegidas[-1].tarjetas)

    # --- Lo que el usuario ya escribió en su pregunta -----------------------

    async def test_un_titulo_que_escribio_el_usuario_no_arma_tarjeta(self):
        # «Algo como Arrival»: el modelo lo nombra de referencia, no lo recomienda.
        eventos = await self.correr(
            [[tool("descubrir")], ["Parecido a **Arrival**: **Moon**."]],
            texto="Quiero algo como arrival",
        )

        self.assertEqual(self.ids(eventos), [1])

    async def test_un_titulo_corto_solo_cuenta_como_escrito_si_es_igual(self):
        # «is it scary?» no nombra a «It»; «Quiero ver It» sí.
        corta = [pelicula_de_mentira(8, "It", 2017)]
        self.peliculas = corta

        como_palabra = await self.correr(
            [[tool("descubrir")], ["Te recomiendo **It**."]], texto="is it scary?"
        )
        self.chat = await Chat.objects.aget(pk=self.chat.pk)
        como_titulo = await self.correr(
            [[tool("descubrir")], ["Te recomiendo **It**."]], texto="Quiero ver It"
        )

        self.assertEqual(self.ids(como_palabra), [8])
        self.assertEqual(como_titulo[-1].tarjetas, [])

    # --- Texto con la tilde suelta (NFD) --------------------------------------

    async def test_un_texto_con_la_tilde_suelta_coincide(self):
        # «é» puede venir como «e» + una tilde aparte (U+0301): se junta antes de
        # comparar.
        self.peliculas = [pelicula_de_mentira(9, "Amélie", 2001)]

        eventos = await self.correr(
            [[tool("descubrir")], ["Probá **Ame\u0301lie**, es hermosa."]]
        )

        self.assertEqual(self.ids(eventos), [9])

    # --- Homónimos: una película y una serie con el mismo nombre -------------

    def homonimos(self, primero="movie"):
        orden = [primero, "tv" if primero == "movie" else "movie"]
        self.peliculas = [
            pelicula_de_mentira(20 + i, "Fargo", 1996 + i, tipo=tipo)
            for i, tipo in enumerate(orden)
        ]

    async def test_homonimos_sin_pistas_gana_el_primero_de_la_busqueda(self):
        for primero in ("movie", "tv"):
            with self.subTest(primero):
                self.homonimos(primero)
                self.chat = await Chat.objects.aget(pk=self.chat.pk)

                eventos = await self.correr([[tool("descubrir")], ["Mirá **Fargo**."]])

                self.assertEqual([t["tipo"] for t in eventos[-1].tarjetas], [primero])

    async def test_homonimos_una_sola_tarjeta_por_mencion(self):
        self.homonimos()

        eventos = await self.correr([[tool("descubrir")], ["Mirá **Fargo**."]])

        self.assertEqual(len(eventos[-1].tarjetas), 1)

    async def test_homonimos_la_pregunta_del_usuario_da_la_pista(self):
        for pregunta, tipo in (
            ("Recomendame una serie", "tv"),
            ("any good tv show?", "tv"),
            ("Quiero una película", "movie"),
            ("a movie please", "movie"),
        ):
            with self.subTest(pregunta):
                self.homonimos("movie" if tipo == "tv" else "tv")
                self.chat = await Chat.objects.aget(pk=self.chat.pk)

                eventos = await self.correr(
                    [[tool("descubrir")], ["Mirá **Fargo**."]], texto=pregunta
                )

                self.assertEqual([t["tipo"] for t in eventos[-1].tarjetas], [tipo])

    async def test_homonimos_el_texto_alrededor_de_la_mencion_da_la_pista(self):
        for texto, tipo in (
            ("Te recomiendo **Fargo**, una serie de crimen.", "tv"),
            ("Try **Fargo**, the 1996 film.", "movie"),
            ("La película **Fargo** es genial.", "movie"),
            ("The **Fargo** show is great.", "tv"),
        ):
            with self.subTest(texto):
                self.homonimos("movie" if tipo == "tv" else "tv")
                self.chat = await Chat.objects.aget(pk=self.chat.pk)

                eventos = await self.correr([[tool("descubrir")], [texto]])

                self.assertEqual([t["tipo"] for t in eventos[-1].tarjetas], [tipo])

    async def test_homonimos_cada_mencion_elige_con_su_propio_contexto(self):
        self.homonimos()

        eventos = await self.correr(
            [
                [tool("descubrir")],
                [
                    "La serie **Fargo** y también la película **Fargo**, que es anterior."
                ],
            ]
        )

        self.assertEqual([t["tipo"] for t in eventos[-1].tarjetas], ["tv", "movie"])

    # --- Log de diagnóstico: una línea por turno (13/11/2026) ---------------------
    # `assertLogs` es como un `Appender` de prueba en Java: captura lo que el logger
    # escribe y falla si no escribió nada. Es un `with` normal aunque el test sea
    # `async`: solo envuelve el código, no depende de `await`.

    def linea_del_turno(self, registros):
        lineas = [m for m in registros.output if "Turno:" in m]
        self.assertEqual(len(lineas), 1, registros.output)
        return lineas[0]

    async def test_el_log_cuenta_tools_vueltas_y_origen_de_las_tarjetas(self):
        with self.assertLogs("chatbot.orquestador", level="INFO") as registros:
            await self.correr(
                [[tool("descubrir")], ["Mirá esta", tarjetas(2)]], texto="algo"
            )

        linea = self.linea_del_turno(registros)
        self.assertIn("tools=descubrir(5),mostrar_tarjetas(1)", linea)
        self.assertIn("vueltas=2", linea)
        self.assertIn("ultima_sin_tools=no", linea)
        self.assertIn("tarjetas=mostrar_tarjetas", linea)

    async def test_el_log_distingue_las_tarjetas_de_la_red(self):
        with self.assertLogs("chatbot.orquestador", level="INFO") as registros:
            await self.correr([[tool("descubrir")], ["Te va bien **Arrival**."]])

        linea = self.linea_del_turno(registros)
        self.assertIn("tools=descubrir(5)", linea)
        self.assertIn("tarjetas=red", linea)

    async def test_el_log_sin_tarjetas_dice_ninguna(self):
        with self.assertLogs("chatbot.orquestador", level="INFO") as registros:
            await self.correr(["Hola, ¿qué querés ver?"])

        linea = self.linea_del_turno(registros)
        self.assertIn("tools=ninguna", linea)
        self.assertIn("vueltas=1", linea)
        self.assertIn("tarjetas=ninguna", linea)

    async def test_el_log_avisa_si_hubo_ultima_llamada_sin_tools(self):
        guion = [[tool("descubrir")] for _ in range(5)] + [["Te va bien **Arrival**."]]

        with self.assertLogs("chatbot.orquestador", level="INFO") as registros:
            await self.correr(guion)

        linea = self.linea_del_turno(registros)
        self.assertIn("ultima_sin_tools=si", linea)
        self.assertIn("vueltas=5", linea)

    async def test_el_log_marca_las_tools_que_fallaron(self):
        with patch.dict(FUNCIONES, {"descubrir": lambda ctx, **_: {"error": "x"}}):
            with self.assertLogs("chatbot.orquestador", level="INFO") as registros:
                await self.correr([[tool("descubrir")], ["No encontré nada."]])

        self.assertIn("tools=descubrir(error)", self.linea_del_turno(registros))

    async def test_el_log_no_lleva_la_pregunta_ni_la_respuesta(self):
        # Son datos personales: el log cuenta cómo fue el turno, no de qué se habló.
        with self.assertLogs("chatbot.orquestador", level="INFO") as registros:
            await self.correr(
                [[tool("descubrir")], ["Te va bien **Arrival**."]],
                texto="algo secretisimo",
            )

        todo = "\n".join(registros.output)
        self.assertNotIn("secretisimo", todo)
        self.assertNotIn("Arrival", todo)


class FallosTests(BaseOrquestador):
    async def test_la_quinta_vuelta_con_tools_pide_una_ultima_llamada_sin_tools(self):
        guion = [[tool("descubrir")] for _ in range(5)] + [["Con lo que hay: Moon."]]

        eventos = await self.correr(guion)

        self.assertEqual(eventos[-1].texto, "Con lo que hay: Moon.")
        self.assertEqual(len(self.proveedor.pedidos), 6)
        # Las 5 primeras llamadas llevan las tools; la última, ninguna.
        self.assertTrue(all(self.proveedor.esquemas[:5]))
        self.assertFalse(self.proveedor.esquemas[5])

    async def test_la_ultima_llamada_lleva_el_aviso_de_que_ya_no_busca(self):
        guion = [[tool("descubrir")] for _ in range(5)] + [["Listo"]]

        await self.correr(guion)

        aviso = self.proveedor.pedidos[5][-1]
        self.assertEqual(aviso["role"], "system")
        self.assertIn("Ya no podés buscar", aviso["content"])
        # Antes del aviso va todo lo que pasó, incluidos los resultados de las tools.
        self.assertEqual(self.proveedor.pedidos[5][-2]["role"], "tool")

    async def test_el_texto_ya_emitido_no_se_repite_en_la_ultima_llamada(self):
        largo = "x" * (_LARGO_DE_PREAMBULO + 1)
        guion = [[largo, tool("descubrir")]]
        guion += [[tool("descubrir")] for _ in range(4)] + [["Final."]]

        eventos = await self.correr(guion)

        textos = [e.delta for e in eventos if isinstance(e, Texto)]
        self.assertEqual("".join(textos), f"{largo}\n\nFinal.")
        self.assertEqual(eventos[-1].texto, f"{largo}\n\nFinal.")

    async def test_las_tarjetas_de_la_vuelta_que_se_paso_llegan_al_resultado(self):
        # La quinta vuelta pidió solo tarjetas, sin texto: se corren y la última
        # llamada escribe la respuesta.
        guion = [[tool("descubrir")] for _ in range(4)]
        guion += [[tarjetas(1)], ["Mirá esta."]]

        eventos = await self.correr(guion)

        self.assertEqual(eventos[-1].texto, "Mirá esta.")
        self.assertEqual(eventos[-1].tarjetas[0]["titulo"], "Moon")

    async def test_un_turno_sin_texto_pide_una_ultima_llamada_sin_tools(self):
        eventos = await self.correr([[tool("descubrir")], [], ["Te recomiendo Moon."]])

        self.assertEqual(eventos[-1].texto, "Te recomiendo Moon.")
        self.assertEqual(len(self.proveedor.pedidos), 3)
        self.assertFalse(self.proveedor.esquemas[2])
        self.assertEqual(self.proveedor.pedidos[2][-1]["role"], "system")

    async def test_si_la_ultima_llamada_falla_es_un_error_del_turno(self):
        guion = [[tool("descubrir")] for _ in range(5)] + [[RuntimeError("503")]]

        with self.assertRaises(ErrorDelTurno):
            await self.correr(guion)

    async def test_si_la_ultima_llamada_vuelve_vacia_es_un_error_del_turno(self):
        guion = [[tool("descubrir")] for _ in range(5)] + [[]]

        with self.assertRaises(ErrorDelTurno):
            await self.correr(guion)

    async def test_la_ultima_llamada_no_cuenta_si_solo_pide_tools(self):
        # Sin esquemas no debería pasar, pero si el modelo igual las pide, se ignoran.
        guion = [[tool("descubrir")] for _ in range(5)] + [[tool("descubrir")]]

        with self.assertRaises(ErrorDelTurno):
            await self.correr(guion)

    async def test_cuatro_vueltas_de_tools_y_una_respuesta_estan_permitidas(self):
        guion = [[tool("descubrir")] for _ in range(4)] + [["Listo"]]

        eventos = await self.correr(guion)

        self.assertEqual(eventos[-1].texto, "Listo")

    async def test_la_ultima_llamada_puede_cerrar_con_texto_y_tarjetas(self):
        # Es lo que pide el prompt: no cuenta como pasarse del tope.
        guion = [[tool("descubrir")] for _ in range(4)] + [["Listo", tarjetas(1)]]

        eventos = await self.correr(guion)

        self.assertEqual(eventos[-1].texto, "Listo")
        self.assertEqual(eventos[-1].tarjetas[0]["titulo"], "Moon")

    async def test_si_el_proveedor_falla_no_hay_resultado(self):
        eventos = []
        self.proveedor = ProveedorFalso([["Hola", RuntimeError("503")]])

        with self.assertRaises(ErrorDelTurno):
            async for evento in responder(
                self.chat, "hola", "es", proveedor=self.proveedor
            ):
                eventos.append(evento)

        self.assertFalse(any(isinstance(e, Resultado) for e in eventos))

    async def test_si_no_se_puede_preparar_el_turno_es_un_error_del_turno(self):
        # Sin `anio`, `armar_sistema` no puede escribir «Ya recomendados».
        self.chat.contexto = {"ya_recomendados": [{"titulo": "Moon"}]}
        await self.chat.asave()

        with self.assertRaises(ErrorDelTurno):
            await self.correr([["Hola"]])

    async def test_una_tool_que_falla_no_termina_el_turno(self):
        with patch.dict(FUNCIONES, {"descubrir": self.explotar}):
            eventos = await self.correr([[tool("descubrir")], ["Sin suerte"]])

        self.assertEqual(eventos[-1].texto, "Sin suerte")
        self.assertIn("tool_failed", self.proveedor.pedidos[1][-1]["content"])

    @staticmethod
    def explotar(ctx, **argumentos):
        raise RuntimeError("TMDB caído")

    async def test_argumentos_que_no_son_json_son_un_error_de_tool(self):
        # Pasa si el modelo se queda sin tokens en medio de los argumentos.
        cortada = LlamadaTool("1", "descubrir", '{"generos": ["Thri')

        eventos = await self.correr([[cortada], ["Reintento"]])

        self.assertEqual(eventos[-1].texto, "Reintento")
        self.assertIn("tool_failed", self.proveedor.pedidos[1][-1]["content"])

    async def test_argumentos_json_que_no_son_un_objeto_son_un_error_de_tool(self):
        await self.correr([[LlamadaTool("1", "descubrir", "[1]")], ["Listo"]])

        self.assertIn("tool_failed", self.proveedor.pedidos[1][-1]["content"])


class LoQueRecibeElModeloTests(BaseOrquestador):
    async def crear_mensaje(self, texto, autor):
        await Mensaje.objects.acreate(chat=self.chat, texto=texto, autor=autor)

    async def test_las_instrucciones_llevan_el_perfil_y_el_idioma(self):
        produccion = await ProduccionAudiovisual.objects.acreate(
            id_tmdb=1, tipo=TipoProduccion.PELICULA, titulo="Arrival"
        )
        await Calificacion.objects.acreate(
            usuario=self.usuario, produccion=produccion, valor=9
        )

        # «Moon» no dice en qué idioma escribió: vale el del turno.
        await self.correr([["Hola"]], texto="Moon", idioma="en")

        sistema = self.mensajes_del_primer_pedido()[0]
        self.assertEqual(sistema["role"], "system")
        self.assertIn("Arrival (9)", sistema["content"])
        self.assertIn("reply in English", sistema["content"])

    async def test_la_prosa_sigue_al_mensaje_y_las_tools_al_turno(self):
        # Interfaz en español, mensaje en inglés: el texto va en inglés, pero las
        # tools (y con ellas las tarjetas) siguen en el idioma del turno.
        with patch(
            "chatbot.orquestador.ContextoTurno.para", wraps=ContextoTurno.para
        ) as para:
            await self.correr(
                [["Hi"]], texto="Something like Arrival, but lighter", idioma="es"
            )

        self.assertIn(
            "reply in English", self.mensajes_del_primer_pedido()[0]["content"]
        )
        self.assertEqual(para.call_args.args[1], "es")

    async def test_el_mensaje_actual_va_anonimizado_y_ultimo(self):
        await self.correr([["Hola"]], texto="soy Juan Perez, mail j@x.com")

        ultimo = self.mensajes_del_primer_pedido()[-1]
        self.assertEqual(ultimo["role"], "user")
        self.assertEqual(ultimo["content"], "soy [usuario], mail [correo]")

    async def test_el_historial_son_los_ultimos_10_en_orden(self):
        for i in range(12):
            autor = TipoAutor.USUARIO if i % 2 == 0 else TipoAutor.CHATBOT
            await self.crear_mensaje(f"m{i}", autor)

        await self.correr([["Hola"]])

        mensajes = self.mensajes_del_primer_pedido()
        historial = mensajes[1:-1]
        self.assertEqual(
            [m["content"] for m in historial], [f"m{i}" for i in range(2, 12)]
        )
        self.assertEqual(historial[0]["role"], "user")
        self.assertEqual(historial[1]["role"], "assistant")

    async def test_el_historial_va_anonimizado(self):
        await self.crear_mensaje("soy juanp, j@x.com", TipoAutor.USUARIO)

        await self.correr([["Hola"]])

        self.assertEqual(
            self.mensajes_del_primer_pedido()[1]["content"], "soy [usuario], [correo]"
        )

    async def test_no_viaja_ningun_dato_personal(self):
        await self.crear_mensaje("hola, soy Juan Perez", TipoAutor.USUARIO)

        await self.correr([["Hola"]], texto="mi usuario es juanp")

        enviado = json.dumps(self.proveedor.pedidos, ensure_ascii=False)
        self.assertNotIn("Juan Perez", enviado)
        self.assertNotIn("juanp", enviado)
        self.assertNotIn(self.usuario.correo, enviado)

    async def test_ya_recomendados_va_con_titulo_y_anio_sin_ids(self):
        self.chat.contexto = {
            "ya_recomendados": [
                {"id_tmdb": 17431, "tipo": "movie", "titulo": "Moon", "anio": 2009}
            ]
        }
        await self.chat.asave()

        await self.correr([["Hola"]])

        sistema = self.mensajes_del_primer_pedido()[0]["content"]
        self.assertIn("Moon (2009)", sistema)
        self.assertNotIn("17431", sistema)


class ReglasDelPromptTests(SimpleTestCase):
    def test_la_parte_fija_va_antes_que_lo_del_usuario(self):
        # Lo fijo adelante es lo que el proveedor puede cachear.
        sistema = armar_sistema("Le gustó: Moon", [], "es")

        self.assertLess(sistema.index("mostrar_tarjetas"), sistema.index("Le gustó"))

    def test_lleva_las_reglas_de_los_titulos_vistos(self):
        sistema = armar_sistema("", [], "es")

        self.assertIn("`vista: true`", sistema)
        self.assertIn("avisale que ya lo vio", sistema)
        self.assertIn("aunque ya lo haya visto", sistema)

    def test_una_secuela_sin_la_anterior_recomienda_la_anterior(self):
        # Va al final de «Títulos vistos»: mover una regla al principio de «Cómo
        # trabajar» cambió la conducta del modelo (12/11/2026).
        sistema = armar_sistema("", [], "es")
        vistos = sistema.split("Títulos vistos:\n", 1)[1].split("\n\n", 1)[0]

        self.assertTrue(
            vistos.rstrip().endswith("Si ya la vio, no hace falta aclararlo.")
        )
        self.assertIn("recomendá la anterior", vistos)

    def test_el_estilo_cambia_con_el_idioma(self):
        self.assertIn("voseo", armar_sistema("", [], "es"))
        self.assertNotIn("voseo", armar_sistema("", [], "en"))

    def test_el_idioma_se_nombra_al_final_del_sistema(self):
        # «Respondé en el idioma del mensaje» perdía contra un perfil y un historial
        # en español. Nombrado y al final, el modelo lo cumple.
        sistema = armar_sistema("Le gustó: Moon", [], "en")

        self.assertTrue(
            sistema.split("\n\n")[-1].startswith("Language: reply in English")
        )

    def test_en_espanol_tambien_se_nombra(self):
        self.assertIn("respondé en español", armar_sistema("", [], "es"))

    def test_la_duracion_va_para_todos_o_para_ninguno(self):
        # Los listados de TMDB no traen `runtime`: sin esta regla, el modelo daba la
        # duración del título que venía de la base y callaba la del otro.
        sistema = armar_sistema("", [], "es")

        self.assertIn("dala para todos los títulos", sistema)
        self.assertIn(
            "consultala con `detalle` para cada título que no la traiga", sistema
        )
        # Las series casi nunca la tienen: callarla sería repetir el problema.
        self.assertIn("decí que de ese título no la tenés", sistema)

    def test_una_tarjeta_sin_anio_no_se_ve_como_titulo_none(self):
        sistema = armar_sistema(
            "",
            [{"titulo": "Moon", "anio": None}, {"titulo": "Her", "anio": 2013}],
            "es",
        )

        self.assertIn("Ya recomendados: Moon, Her (2013)", sistema)
        self.assertNotIn("None", sistema)

    def test_sin_datos_lo_dice_en_vez_de_dejarlo_vacio(self):
        self.assertIn("Todavía no hay datos.", armar_sistema("", [], "es"))

    def test_la_fecha_de_hoy_va_en_la_parte_variable_en_el_idioma_de_la_respuesta(self):
        # Sin la fecha, el modelo no sabe si «Proyecto Fin del Mundo» ya se estrenó.
        # Va después del perfil: lo fijo del comienzo sigue siendo cacheable.
        hoy = date(2026, 11, 13)
        en_es = armar_sistema("Le gustó: Moon", [], "es", hoy=hoy)
        en_en = armar_sistema("Le gustó: Moon", [], "en", hoy=hoy)

        self.assertIn("13 de noviembre de 2026", en_es)
        self.assertIn("November 13, 2026", en_en)
        self.assertGreater(en_es.index("13 de noviembre"), en_es.index("Le gustó"))

    def test_cambiar_la_fecha_no_toca_la_parte_fija(self):
        a = armar_sistema("", [], "es", hoy=date(2026, 11, 13))
        b = armar_sistema("", [], "es", hoy=date(2027, 1, 2))

        fija = a.split("Perfil del usuario:")[0]
        self.assertEqual(fija, b.split("Perfil del usuario:")[0])
        self.assertNotEqual(a, b)

    def test_no_afirma_fechas_de_estreno_de_memoria(self):
        sistema = armar_sistema("", [], "es")

        self.assertIn("puede estar desactualizado", sistema)
        self.assertIn("«ya salió»", sistema)
        self.assertIn("salvo que lo haya devuelto una tool en este turno", sistema)

    def test_no_anuncia_cuantos_titulos_recomienda(self):
        self.assertIn("No anuncies cuántos títulos", armar_sistema("", [], "es"))

    def test_un_criterio_que_no_se_puede_filtrar_se_aclara_en_una_oracion(self):
        sistema = armar_sistema("", [], "es")

        self.assertIn("no pueden filtrar", sistema)
        self.assertIn("sin presentarlo como cumplido", sistema)

    def test_las_reglas_nuevas_no_reordenan_las_existentes(self):
        # Mover reglas cambió la conducta del modelo el 12/11/2026: las nuevas se
        # suman en su propia sección, después de «Títulos vistos».
        sistema = armar_sistema("", [], "es")

        self.assertLess(
            sistema.index("Títulos vistos:"), sistema.index("Al recomendar:")
        )
        self.assertLess(
            sistema.index("Al recomendar:"), sistema.index("Datos no confiables")
        )

    def test_lo_que_el_usuario_nombro_pesa_mas_que_lo_que_dijo_el_asistente(self):
        # Pidió «parecidas a esta serie» queriendo decir Cowboy Bebop (la que había
        # nombrado él) y el bot tomó Serial Experiments Lain, de su respuesta anterior.
        sistema = armar_sistema("", [], "es")

        self.assertIn("«esta serie»", sistema)
        self.assertIn("que él mismo nombró en su mensaje", sistema)
        self.assertIn("antes que uno que apareció en tu respuesta anterior", sistema)

    def test_una_referencia_ambigua_se_resuelve_y_se_aclara_sin_frenar(self):
        sistema = armar_sistema("", [], "es")

        self.assertIn("puede ser de dos títulos", sistema)
        self.assertIn("Tomo X como base; si querías Y, decime", sistema)
        self.assertIn("sin cortar la respuesta ni hacer una pregunta", sistema)

    def test_no_da_opiniones_de_calidad_como_hechos(self):
        sistema = armar_sistema("", [], "es")

        self.assertIn("No des opiniones de calidad como hechos", sistema)
        self.assertIn("un escalón abajo en calidad", sistema)

    def test_los_datos_concretos_salen_solo_de_una_tool_de_este_turno(self):
        # El bot dijo 22 episodios de Texhnolyze y TMDB dice 20.
        sistema = armar_sistema("", [], "es")

        self.assertIn(
            "episodios, temporadas, duración, año, reparto y director", sistema.lower()
        )
        self.assertIn("`temporadas` y `episodios`", sistema)

    def test_las_tarjetas_que_se_piden_son_las_de_la_ultima_respuesta(self):
        # Tras recomendar Log Horizon, Btooom! y SAO Alicization sin tarjetas, el
        # usuario preguntó «¿y las tarjetas?» y el bot mostró tres de «Ya
        # recomendados» (Interestelar, Apolo 13, Pasajeros): esa lista es de toda la
        # sesión, no de la última respuesta.
        sistema = armar_sistema("", [], "es")

        self.assertIn("«¿y las tarjetas?»", sistema)
        self.assertIn("«mostrame esos»", sistema)
        self.assertIn("los títulos de tu última respuesta", sistema)
        self.assertIn("`buscar_por_titulo`", sistema)
        self.assertIn("Nunca tomes los de «Ya recomendados»", sistema)
        # Va dentro de «Referencias y datos», sin mover ninguna regla existente.
        self.assertLess(
            sistema.index("Referencias y datos:"),
            sistema.index("«¿y las tarjetas?»"),
        )
        self.assertLess(
            sistema.index("«¿y las tarjetas?»"), sistema.index("Datos no confiables")
        )

    def test_las_reglas_de_referencias_van_despues_de_al_recomendar(self):
        sistema = armar_sistema("", [], "es")

        self.assertLess(
            sistema.index("Al recomendar:"), sistema.index("Referencias y datos:")
        )
        self.assertLess(
            sistema.index("Referencias y datos:"), sistema.index("Datos no confiables")
        )

    def test_las_malas_palabras_se_prohiben_con_ejemplos_en_los_dos_idiomas(self):
        es = armar_sistema("", [], "es")
        en = armar_sistema("", [], "en")

        for ejemplo in ("carajo", "mierda", "joder", "tampoco las suaves"):
            self.assertIn(ejemplo, es)
        for ejemplo in ("damn", "hell", "not even mild"):
            self.assertIn(ejemplo, en)

    def test_sin_jerga_ni_comentarios_sobre_el_fisico_de_los_actores(self):
        # «Pibardos» para los protagonistas de «Violet & Finch» (13/11/2026).
        es = armar_sistema("", [], "es")
        en = armar_sistema("", [], "en")

        for ejemplo in ("pibe", "pibardo", "está re fuerte", "un caño", "todo público"):
            self.assertIn(ejemplo, es)
        self.assertIn("lo atractivos que son los actores", es)
        self.assertIn("how attractive the actors are", en)
        self.assertIn("voseo", es)


class FechaDeHoyTests(BaseOrquestador):
    async def test_el_orquestador_pasa_la_fecha_de_hoy_al_sistema(self):
        with patch(
            "chatbot.orquestador.timezone.localdate", return_value=date(2026, 11, 13)
        ):
            await self.correr([["Hola"]])

        sistema = self.mensajes_del_primer_pedido()[0]["content"]
        self.assertIn("13 de noviembre de 2026", sistema)


class PresupuestoDeTmdbTests(BaseOrquestador):
    @staticmethod
    def llamar_a_tmdb(ctx, **argumentos):
        registrar_llamada()
        return {"resultados": []}

    async def test_las_tools_de_un_turno_suman_al_mismo_contador(self):
        with patch.dict(FUNCIONES, {"descubrir": self.llamar_a_tmdb}):
            with contar_llamadas() as contador:
                await self.correr([[tool("descubrir")], [tool("descubrir")], ["Listo"]])

        self.assertEqual(contador.total, 2)

    async def test_pasado_el_tope_la_tool_falla_y_el_turno_sigue(self):
        with patch.dict(FUNCIONES, {"descubrir": self.llamar_a_tmdb}):
            with contar_llamadas() as contador:
                contador.total = 30
                eventos = await self.correr([[tool("descubrir")], ["Listo"]])

        self.assertEqual(eventos[-1].texto, "Listo")
        self.assertIn("tool_failed", self.proveedor.pedidos[1][-1]["content"])


class ComandoChatearTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(nombre_usuario="juanp")

    def chatear(self, guion, **opciones):
        salida = StringIO()
        with patch(
            "chatbot.orquestador.crear_proveedor", return_value=ProveedorFalso(guion)
        ):
            call_command(
                "chatear",
                usuario="juanp",
                mensaje="hola",
                stdout=salida,
                stderr=salida,
                **opciones,
            )
        return salida.getvalue()

    def test_imprime_la_respuesta_y_guarda_el_turno(self):
        salida = self.chatear([["Hola, ", "che"]])

        self.assertIn("Hola, che", salida)
        self.assertEqual(
            list(Mensaje.objects.values_list("autor", "texto").order_by("id")),
            [("usuario", "hola"), ("chatbot", "Hola, che")],
        )

    def test_sin_guardar_no_toca_el_historial(self):
        self.chatear([["Hola"]], sin_guardar=True)

        self.assertEqual(Mensaje.objects.count(), 0)

    def test_si_el_turno_falla_lo_avisa_y_no_guarda(self):
        salida = self.chatear([[RuntimeError("503")]])

        self.assertIn("error del turno", salida)
        self.assertEqual(Mensaje.objects.count(), 0)

    def test_un_usuario_que_no_existe_es_un_error_claro(self):
        with self.assertRaises(CommandError):
            call_command("chatear", usuario="nadie", mensaje="hola")


def fragmento(*, contenido=None, llamadas=None, razonamiento=None):
    delta = SimpleNamespace(
        content=contenido, tool_calls=llamadas, reasoning_content=razonamiento
    )
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def parte_de_tool(indice, argumentos, id_=None, nombre=None):
    funcion = SimpleNamespace(name=nombre, arguments=argumentos)
    return SimpleNamespace(index=indice, id=id_, function=funcion)


async def como_stream(*fragmentos):
    for item in fragmentos:
        yield item


class LeerStreamTests(SimpleTestCase):
    """La forma de los fragmentos copia la de DeepSeek, consultada el 05/11/2026."""

    async def leer(self, *fragmentos):
        return [item async for item in leer_stream(como_stream(*fragmentos))]

    async def test_el_texto_sale_de_a_pedazos(self):
        items = await self.leer(fragmento(contenido="Ho"), fragmento(contenido="la"))

        self.assertEqual(items[:2], ["Ho", "la"])
        self.assertEqual(items[-1], Vuelta("Hola", [], None))

    async def test_junta_los_argumentos_partidos_de_una_tool(self):
        items = await self.leer(
            fragmento(llamadas=[parte_de_tool(0, "", "c1", "descubrir")]),
            fragmento(llamadas=[parte_de_tool(0, '{"tipo"')]),
            fragmento(llamadas=[parte_de_tool(0, ': "tv"}')]),
        )

        self.assertEqual(
            items[-1].llamadas, [LlamadaTool("c1", "descubrir", '{"tipo": "tv"}')]
        )

    async def test_separa_tools_en_paralelo_por_su_indice(self):
        items = await self.leer(
            fragmento(llamadas=[parte_de_tool(0, "", "a", "descubrir")]),
            fragmento(llamadas=[parte_de_tool(1, "", "b", "detalle")]),
            fragmento(llamadas=[parte_de_tool(0, "{}")]),
            fragmento(llamadas=[parte_de_tool(1, "[]")]),
        )

        self.assertEqual(
            items[-1].llamadas,
            [LlamadaTool("a", "descubrir", "{}"), LlamadaTool("b", "detalle", "[]")],
        )

    async def test_ignora_los_fragmentos_sin_choices(self):
        items = await self.leer(
            SimpleNamespace(choices=[]), fragmento(contenido="Hola")
        )

        self.assertEqual(items[-1].texto, "Hola")

    async def test_junta_el_razonamiento(self):
        items = await self.leer(
            fragmento(razonamiento="pen"), fragmento(razonamiento="sando")
        )

        self.assertEqual(items[-1].razonamiento, "pensando")


class ParametroToolsTests(SimpleTestCase):
    """Sin esquemas, `tools` no viaja: es lo que hace una llamada «solo texto»."""

    async def pedido_enviado(self, esquemas):
        crear = AsyncMock(return_value=como_stream(fragmento(contenido="Hola")))
        with patch("chatbot.llm.AsyncOpenAI") as cliente:
            cliente.return_value.__aenter__.return_value = MagicMock(
                chat=MagicMock(completions=MagicMock(create=crear))
            )
            proveedor = ProveedorOpenAICompatible(
                base_url="http://x", modelo="m", api_key="k", thinking=False
            )
            [_ async for _ in proveedor.escribir([], esquemas)]
        return crear.call_args.kwargs

    async def test_con_esquemas_los_manda(self):
        enviado = await self.pedido_enviado([{"type": "function"}])

        self.assertEqual(enviado["tools"], [{"type": "function"}])

    async def test_sin_esquemas_no_manda_el_parametro_tools(self):
        enviado = await self.pedido_enviado([])

        self.assertNotIn("tools", enviado)
        self.assertNotIn("tool_choice", enviado)


class CrearProveedorTests(SimpleTestCase):
    @override_settings(
        LLM_PROVEEDORES=[
            {
                "tipo": "openai_compatible",
                "base_url": "http://x",
                "modelo": "m",
                "api_key": "k",
                "thinking": False,
            }
        ]
    )
    def test_arma_el_proveedor_de_la_configuracion(self):
        proveedor = crear_proveedor()

        self.assertIsInstance(proveedor, ProveedorOpenAICompatible)
        self.assertEqual(proveedor.modelo, "m")

    @override_settings(LLM_PROVEEDORES=[{"tipo": "deepseek"}])
    def test_un_tipo_desconocido_falla_enseguida(self):
        with self.assertRaises(KeyError):
            crear_proveedor()

    @override_settings(LLM_PROVEEDORES=[{"tipo": "deepseek"}])
    async def test_mal_configurado_es_un_error_del_turno(self):
        # La vista solo sabe convertir `ErrorDelTurno` en el evento `error`.
        with self.assertRaises(ErrorDelTurno):
            await anext(responder(None, "hola", "es"))
