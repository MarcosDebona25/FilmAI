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
from chatbot.tools.turno import titulo
from usuarios.factories import UsuarioFactory


def tool(nombre, _id="1", **argumentos):
    return LlamadaTool(_id, nombre, json.dumps(argumentos))


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

        # El filtro de marcadores retiene un espacio final por si lo que sigue es un
        # `[[n]]` inválido (que se borra junto con su espacio): los cortes se
        # corren, pero el texto es el mismo.
        self.assertEqual(
            eventos, [Texto("Hola"), Texto(" che"), Resultado("Hola che", [])]
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

        self.assertLess(sistema.index("Cómo trabajar"), sistema.index("Le gustó"))

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

    def test_un_pedido_de_filmografia_es_una_recomendacion_no_un_rechazo(self):
        # «¿Cómo puedo empezar a ver la filmografía de Nolan?» se rechazó dos de dos
        # veces por la regla de alcance, sin buscar nada.
        sistema = armar_sistema("", [], "es")

        self.assertIn("filmografía", sistema)
        self.assertIn("«por dónde arranco con X»", sistema)
        self.assertIn("es un pedido de recomendación, no de instrucciones", sistema)
        self.assertIn("`buscar_por_persona`", sistema)
        self.assertIn("ante la duda entre rechazar y recomendar, recomendá", sistema)
        # La regla de alcance no se mueve: sigue siendo lo primero que se lee.
        self.assertLess(
            sistema.index("lo rechazás con amabilidad"), sistema.index("Cómo trabajar:")
        )
        self.assertLess(
            sistema.index("ante la duda entre rechazar"),
            sistema.index("Cómo trabajar:"),
        )
        self.assertGreater(
            sistema.index("es un pedido de recomendación"),
            sistema.index("Al recomendar:"),
        )

    def test_nunca_ofrece_mostrar_los_titulos_y_los_muestra_en_la_misma_respuesta(self):
        # El bot recomendó sin tarjetas y cerró con «¿Te armo las tarjetas?».
        sistema = armar_sistema("", [], "es")

        self.assertIn("Nunca ofrezcas ni preguntes si querés verlos", sistema)
        self.assertIn("«¿te armo las tarjetas?»", sistema)
        self.assertIn("en esa misma respuesta", sistema)

    def test_no_le_nombra_al_usuario_las_palabras_internas(self):
        sistema = armar_sistema("", [], "es")

        self.assertIn("Al usuario no le nombres palabras internas", sistema)
        for palabra in ("«tarjeta»", "«tool»", "«herramienta»"):
            self.assertIn(palabra, sistema)
        self.assertIn("«los títulos»", sistema)
        # La regla de «¿y las tarjetas?» sigue: sirve para entender al usuario.
        self.assertIn("«¿y las tarjetas?»", sistema)
        self.assertLess(
            sistema.index("Al recomendar:"),
            sistema.index("Al usuario no le nombres palabras internas"),
        )
        self.assertLess(
            sistema.index("Al usuario no le nombres palabras internas"),
            sistema.index("Referencias y datos:"),
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
