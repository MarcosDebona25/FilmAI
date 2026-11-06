"""`POST /api/chat/messages/`: el stream SSE, el candado, el tope por hora y el guardado.

Hasta que el PR 3 estuvo en `develop`, estos tests manejaban la vista con
`OrquestadorFalso`: su `demora` hace de turno lento y `falla_en` de falla del
proveedor. Se quedan así porque son rápidos y no dependen del modelo; un test al
final corre además el orquestador real con un proveedor de mentira.

Son `async def` dentro del `TestCase` de Django (no `IsolatedAsyncioTestCase`): así
el código que la vista corre con `en_hilo` ve la transacción del test. Cortar la
conexión no se puede simular con `AsyncClient`; esos casos están en
`CorteDeConexionTests`, que llama a la aplicación ASGI de verdad.
"""

import asyncio
import json
import time
from unittest.mock import patch

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.test import (
    AsyncClient,
    Client,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from rest_framework_simplejwt.tokens import RefreshToken

from chatbot.eventos import Resultado, Texto
from chatbot.limites import _clave_candado, soltar_candado, tomar_candado
from chatbot.llm import LlamadaTool, ProveedorFalso
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.orquestador_falso import OrquestadorFalso
from chatbot.servicio import guardar_turno
from chatbot.tools import FUNCIONES
from filmai.pruebas_asgi import pedir
from usuarios.factories import UsuarioFactory
from usuarios.models import EstadoCuenta

URL = "/api/chat/messages/"


def eventos_de(cuerpo):
    """`[(nombre, datos)]` a partir del cuerpo de un stream SSE."""
    resultado = []
    texto = cuerpo.decode() if isinstance(cuerpo, bytes) else cuerpo
    for bloque in texto.split("\n\n"):
        if not bloque.strip():
            continue
        lineas = bloque.split("\n")
        assert lineas[0].startswith("event: "), bloque
        assert lineas[1].startswith("data: ") and len(lineas) == 2, bloque
        resultado.append((lineas[0][7:], json.loads(lineas[1][6:])))
    return resultado


def sesion(usuario):
    """Las cookies que tendría el navegador: `access` (JWT) y `csrftoken`."""
    csrf = Client().get("/api/auth/csrf/").cookies["csrftoken"].value
    return str(RefreshToken.for_user(usuario).access_token), csrf


class BaseSSE(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(idioma="en")
        self.chat = Chat.objects.get(usuario=self.usuario)
        self.acceso, self.csrf = sesion(self.usuario)
        self.cliente = AsyncClient(enforce_csrf_checks=True)
        self.cliente.cookies["access"] = self.acceso
        self.cliente.cookies["csrftoken"] = self.csrf

    async def enviar(self, texto="hola", *, csrf=True, cliente=None):
        # `Accept: text/event-stream` es lo que manda el panel.
        encabezados = {"Accept": "text/event-stream"}
        if csrf:
            encabezados["X-CSRFToken"] = self.csrf
        return await (cliente or self.cliente).post(
            URL,
            {"texto": texto},
            content_type="application/json",
            headers=encabezados,
        )

    async def leer(self, respuesta):
        return b"".join([parte async for parte in respuesta.streaming_content])

    async def turno(self, falso=None, texto="hola", **parametros):
        """Manda un mensaje con un orquestador falso y devuelve `(respuesta, eventos)`."""
        falso = falso or OrquestadorFalso(**parametros)
        with patch("chatbot.views.responder", falso.responder):
            respuesta = await self.enviar(texto)
            self.assertEqual(respuesta.status_code, 200)
            cuerpo = await self.leer(respuesta)
        return respuesta, eventos_de(cuerpo)

    def candado_tomado(self):
        return cache.get(_clave_candado(self.chat.pk)) is not None


class RechazosAntesDelStreamTests(BaseSSE):
    async def test_sin_sesion_es_401(self):
        respuesta = await AsyncClient().post(
            URL, {"texto": "hola"}, content_type="application/json"
        )

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["code"], "not_authenticated")
        self.assertEqual(await Mensaje.objects.acount(), 0)

    async def test_sin_csrf_es_403_en_json(self):
        respuesta = await self.enviar(csrf=False)

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertEqual(respuesta.json()["code"], "permission_denied")
        self.assertFalse(self.candado_tomado())

    async def test_cuenta_de_baja_con_la_cookie_viva_se_trata_como_en_el_resto_de_la_api(
        self,
    ):
        # El JWT sigue vigente, pero simplejwt rechaza al usuario inactivo antes de
        # llegar a la vista: 401 `session_revoked`, igual que en `/api/profile/`.
        await self.usuario.__class__.objects.filter(pk=self.usuario.pk).aupdate(
            estado=EstadoCuenta.BAJA
        )

        respuesta = await self.enviar()

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["code"], "session_revoked")

    async def test_texto_invalido_es_400_con_el_campo_texto(self):
        for texto in ("", "   ", "a" * 501):
            with self.subTest(largo=len(texto)):
                respuesta = await self.enviar(texto)

                self.assertEqual(respuesta.status_code, 400)
                cuerpo = respuesta.json()
                self.assertEqual(cuerpo["code"], "validation_error")
                self.assertEqual(cuerpo["errors"][0]["field"], "texto")
                self.assertFalse(self.candado_tomado())

    async def test_500_caracteres_justos_son_validos(self):
        _, eventos = await self.turno(texto="a" * 500)

        self.assertEqual(eventos[-1][0], "fin")

    async def test_un_formulario_es_415(self):
        # El panel manda JSON; el endpoint no acepta otro formato.
        respuesta = await self.cliente.post(
            URL, {"texto": "hola"}, headers={"X-CSRFToken": self.csrf}
        )

        self.assertEqual(respuesta.status_code, 415)
        self.assertEqual(respuesta.json()["code"], "unsupported_media_type")

    async def test_cuerpo_sin_texto_es_400(self):
        respuesta = await self.cliente.post(
            URL,
            {},
            content_type="application/json",
            headers={"X-CSRFToken": self.csrf},
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["errors"][0]["field"], "texto")

    async def test_otra_respuesta_en_curso_es_409(self):
        token = await sync_to_async(tomar_candado)(self.chat.pk)

        respuesta = await self.enviar()

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.json()["code"], "chat_request_in_progress")
        # El candado de la otra respuesta sigue siendo suyo.
        self.assertEqual(cache.get(_clave_candado(self.chat.pk)), token)

    async def test_el_segundo_mensaje_mientras_el_primero_transmite_es_409(self):
        falso = OrquestadorFalso()
        with patch("chatbot.views.responder", falso.responder):
            primera = await self.enviar("uno")
            segunda = await self.enviar("dos")
            cuerpo = await self.leer(primera)

        self.assertEqual(segunda.status_code, 409)
        # La primera sigue como si nada.
        self.assertEqual(eventos_de(cuerpo)[-1][0], "fin")
        self.assertEqual(await Mensaje.objects.acount(), 2)

    @override_settings(CHAT_MENSAJES_POR_HORA=1)
    async def test_pasado_el_tope_por_hora_es_429_con_cuanto_esperar(self):
        await self.turno()

        respuesta = await self.enviar()

        self.assertEqual(respuesta.status_code, 429)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["code"], "throttled")
        self.assertGreater(cuerpo["params"]["retry_after_seconds"], 0)
        self.assertLessEqual(cuerpo["params"]["retry_after_seconds"], 3600)
        self.assertEqual(
            respuesta["Retry-After"], str(cuerpo["params"]["retry_after_seconds"])
        )
        # El 429 devuelve el candado: si no, el chat quedaría trabado un minuto.
        self.assertFalse(self.candado_tomado())

    @override_settings(CHAT_MENSAJES_POR_HORA=1)
    async def test_un_400_y_un_409_no_gastan_cupo(self):
        await self.enviar("")  # 400
        token = await sync_to_async(tomar_candado)(self.chat.pk)
        await self.enviar()  # 409
        await sync_to_async(soltar_candado)(self.chat.pk, token)

        _, eventos = await self.turno()

        self.assertEqual(eventos[-1][0], "fin")

    @override_settings(CHAT_MENSAJES_POR_HORA=1)
    async def test_el_tope_es_por_usuario(self):
        await self.turno()
        otro = await sync_to_async(UsuarioFactory)()
        acceso, csrf = await sync_to_async(sesion)(otro)
        cliente = AsyncClient(enforce_csrf_checks=True)
        cliente.cookies["access"], cliente.cookies["csrftoken"] = acceso, csrf

        with patch("chatbot.views.responder", OrquestadorFalso().responder):
            respuesta = await cliente.post(
                URL,
                {"texto": "hola"},
                content_type="application/json",
                headers={"X-CSRFToken": csrf},
            )

        self.assertEqual(respuesta.status_code, 200)

    async def test_get_sigue_devolviendo_el_historial(self):
        await self.turno()

        respuesta = await self.cliente.get(URL)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["results"]), 2)


class TurnoCompletoTests(BaseSSE):
    async def test_un_turno_entrega_la_secuencia_de_eventos_y_guarda_el_par(self):
        respuesta, eventos = await self.turno()

        self.assertEqual(respuesta["Content-Type"], "text/event-stream")
        self.assertEqual(respuesta["Cache-Control"], "no-cache")
        self.assertEqual(respuesta["X-Accel-Buffering"], "no")
        self.assertEqual(
            [nombre for nombre, _ in eventos],
            ["estado", "texto", "texto", "texto", "tarjetas", "fin"],
        )
        self.assertEqual(eventos[0][1], {"code": "searching"})
        deltas = "".join(d["delta"] for n, d in eventos if n == "texto")
        pregunta = await Mensaje.objects.aget(autor=TipoAutor.USUARIO)
        respuesta_guardada = await Mensaje.objects.aget(autor=TipoAutor.CHATBOT)
        self.assertEqual(respuesta_guardada.texto, deltas)
        self.assertEqual(pregunta.texto, "hola")
        self.assertEqual(
            eventos[-1][1],
            {"id": respuesta_guardada.pk, "id_pregunta": pregunta.pk},
        )

    async def test_las_tarjetas_salen_despues_del_guardado_y_se_guardan_como_salieron(
        self,
    ):
        _, eventos = await self.turno()

        tarjetas = dict(eventos)["tarjetas"]["tarjetas"]
        guardada = await Mensaje.objects.aget(autor=TipoAutor.CHATBOT)
        self.assertEqual(tarjetas[0]["titulo"], "Moon")
        self.assertEqual(guardada.tarjetas, tarjetas)
        chat = await Chat.objects.aget(pk=self.chat.pk)
        self.assertEqual(chat.contexto["ya_recomendados"][0]["titulo"], "Moon")

    async def test_sin_tarjetas_el_evento_sale_igual_y_vacio(self):
        guion = (Texto("Hola"), Resultado("Hola", []))

        _, eventos = await self.turno(OrquestadorFalso(guion))

        self.assertEqual(eventos[-2], ("tarjetas", {"tarjetas": []}))

    async def test_el_texto_con_saltos_de_linea_no_parte_el_evento(self):
        guion = (Texto("uno\ndos\n\ntres"), Resultado("uno\ndos\n\ntres", []))

        _, eventos = await self.turno(OrquestadorFalso(guion))

        self.assertEqual(eventos[0], ("texto", {"delta": "uno\ndos\n\ntres"}))

    async def test_el_orquestador_recibe_el_chat_el_texto_y_el_idioma_de_la_cuenta(
        self,
    ):
        falso = OrquestadorFalso()

        await self.turno(falso, texto="  algo como Moon  ")

        ((chat, texto, idioma),) = falso.llamadas
        self.assertEqual(chat.pk, self.chat.pk)
        self.assertEqual(texto, "algo como Moon")
        self.assertEqual(idioma, "en")

    async def test_sin_idioma_en_la_cuenta_manda_el_encabezado(self):
        await self.usuario.__class__.objects.filter(pk=self.usuario.pk).aupdate(
            idioma=None
        )
        falso = OrquestadorFalso()
        with patch("chatbot.views.responder", falso.responder):
            respuesta = await self.cliente.post(
                URL,
                {"texto": "hola"},
                content_type="application/json",
                headers={
                    "X-CSRFToken": self.csrf,
                    "Accept-Language": "es-AR,es;q=0.9",
                },
            )
            await self.leer(respuesta)

        self.assertEqual(falso.llamadas[0][2], "es")

    async def test_el_candado_se_suelta_al_terminar(self):
        await self.turno()

        self.assertFalse(self.candado_tomado())


class FallasDelTurnoTests(BaseSSE):
    async def test_si_el_proveedor_falla_sale_error_y_no_se_guarda_nada(self):
        _, eventos = await self.turno(falla_en=2)

        self.assertEqual([n for n, _ in eventos], ["estado", "texto", "error"])
        self.assertEqual(
            eventos[-1][1], {"code": "chat_unavailable", "params": {}, "errors": []}
        )
        self.assertEqual(await Mensaje.objects.acount(), 0)
        self.assertFalse(self.candado_tomado())

    async def test_una_falla_al_empezar_es_solo_un_error(self):
        _, eventos = await self.turno(falla_en=0)

        self.assertEqual([n for n, _ in eventos], ["error"])

    async def test_una_excepcion_inesperada_tambien_es_chat_unavailable(self):
        async def roto(chat, texto, idioma):
            raise RuntimeError("no debería llegar al usuario")
            yield

        with self.assertLogs("chatbot.views", level="ERROR"):
            _, eventos = await self.turno(SimpleOrquestador(roto))

        self.assertEqual(eventos, [("error", eventos[0][1])])
        self.assertEqual(eventos[0][1]["code"], "chat_unavailable")
        self.assertNotIn("debería", json.dumps(eventos))
        self.assertFalse(self.candado_tomado())

    async def test_un_turno_sin_resultado_es_un_error(self):
        _, eventos = await self.turno(OrquestadorFalso((Texto("hola"),)))

        self.assertEqual(eventos[-1][0], "error")
        self.assertEqual(await Mensaje.objects.acount(), 0)

    async def test_si_falla_el_guardado_sale_error_y_nunca_tarjetas(self):
        with patch("chatbot.views.guardar_turno", side_effect=RuntimeError("base")):
            with self.assertLogs("chatbot.views", level="ERROR"):
                _, eventos = await self.turno()

        nombres = [n for n, _ in eventos]
        self.assertEqual(nombres[-1], "error")
        self.assertNotIn("tarjetas", nombres)
        self.assertNotIn("fin", nombres)
        self.assertEqual(await Mensaje.objects.acount(), 0)
        self.assertFalse(self.candado_tomado())


class SimpleOrquestador:
    """Envuelve una función `async def` con `yield` como si fuera un orquestador."""

    def __init__(self, funcion):
        self.responder = funcion


@override_settings(LLM_TIMEOUT_SECONDS=0.3)
class TiempoYCandadoTests(BaseSSE):
    async def test_un_turno_que_se_pasa_del_presupuesto_termina_en_error(self):
        # Cada evento tarda más que el presupuesto entero.
        _, eventos = await self.turno(demora=0.5)

        self.assertEqual([n for n, _ in eventos], ["error"])
        self.assertEqual(eventos[0][1]["code"], "chat_unavailable")
        self.assertEqual(await Mensaje.objects.acount(), 0)
        self.assertFalse(self.candado_tomado())

    async def test_un_guardado_en_curso_cuando_vence_el_presupuesto_no_se_interrumpe(
        self,
    ):
        def guardado_lento(*args):
            time.sleep(0.6)  # más que el presupuesto de 0,3 s
            return guardar_turno(*args)

        with patch("chatbot.views.guardar_turno", guardado_lento):
            _, eventos = await self.turno()

        self.assertEqual(eventos[-1][0], "fin")
        self.assertEqual(await Mensaje.objects.acount(), 2)

    async def test_la_liberacion_tardia_no_borra_el_candado_del_pedido_siguiente(self):
        clave = _clave_candado(self.chat.pk)

        async def lento_que_pierde_el_candado(chat, texto, idioma):
            # Mientras el turno corre, el candado vence y lo toma otro pedido.
            cache.set(clave, "token-de-otro-pedido", 60)
            yield Resultado("ok", [])

        _, eventos = await self.turno(SimpleOrquestador(lento_que_pierde_el_candado))

        self.assertEqual(eventos[-1][0], "fin")
        self.assertEqual(cache.get(clave), "token-de-otro-pedido")
        respuesta = await self.enviar()
        self.assertEqual(respuesta.status_code, 409)


class CandadoTests(TestCase):
    def test_solo_uno_toma_el_candado(self):
        self.assertIsNotNone(tomar_candado(7))
        self.assertIsNone(tomar_candado(7))
        self.assertIsNotNone(tomar_candado(8))

    def test_soltar_con_otro_token_no_lo_suelta(self):
        token = tomar_candado(7)

        soltar_candado(7, "no-es-mio")
        self.assertIsNone(tomar_candado(7))

        soltar_candado(7, token)
        self.assertIsNotNone(tomar_candado(7))

    @override_settings(LLM_TIMEOUT_SECONDS=25)
    def test_vence_a_los_60_segundos_con_el_tiempo_por_defecto(self):
        with patch("chatbot.limites.cache") as cache_falsa:
            cache_falsa.add.return_value = True
            tomar_candado(7)

        self.assertEqual(cache_falsa.add.call_args.args[2], 60)

    @override_settings(LLM_TIMEOUT_SECONDS=40)
    def test_el_vencimiento_acompana_al_tiempo_del_turno(self):
        with patch("chatbot.limites.cache") as cache_falsa:
            cache_falsa.add.return_value = True
            tomar_candado(7)

        self.assertEqual(cache_falsa.add.call_args.args[2], 75)


class CorteDeConexionTests(TransactionTestCase):
    """El navegador aborta el `fetch` (CU-014). Pasa por la aplicación ASGI real."""

    def setUp(self):
        self.usuario = UsuarioFactory(idioma="en")
        self.chat = Chat.objects.get(usuario=self.usuario)
        acceso, self.csrf = sesion(self.usuario)
        self.encabezados = {
            "content-type": "application/json",
            "cookie": f"access={acceso}; csrftoken={self.csrf}",
            "x-csrftoken": self.csrf,
        }

    def candado_tomado(self):
        return cache.get(_clave_candado(self.chat.pk)) is not None

    async def enviar(self, **opciones):
        return await pedir(
            "POST",
            URL,
            cuerpo=json.dumps({"texto": "hola"}).encode(),
            encabezados=self.encabezados,
            **opciones,
        )

    async def test_un_turno_completo_funciona_bajo_asgi(self):
        falso = OrquestadorFalso()
        with patch("chatbot.views.responder", falso.responder):
            respuesta = await self.enviar()

        self.assertEqual(respuesta.estado, 200)
        self.assertEqual(respuesta.encabezados["content-type"], "text/event-stream")
        self.assertEqual(eventos_de(respuesta.cuerpo)[-1][0], "fin")
        self.assertEqual(await Mensaje.objects.acount(), 2)

    async def test_cortar_a_mitad_de_la_respuesta_no_guarda_nada_y_suelta_el_candado(
        self,
    ):
        falso = OrquestadorFalso(demora=0.05)
        with patch("chatbot.views.responder", falso.responder):
            respuesta = await self.enviar(
                desconectar_si=lambda trozo, _: b"event: texto" in trozo
            )

        nombres = [n for n, _ in eventos_de(respuesta.cuerpo)]
        self.assertNotIn("fin", nombres)
        self.assertEqual(await Mensaje.objects.acount(), 0)
        self.assertFalse(self.candado_tomado())

    async def test_cortar_durante_el_guardado_mantiene_el_candado_hasta_que_termina(
        self,
    ):
        desconexion = asyncio.Event()
        bucle = asyncio.get_running_loop()
        visto = {}

        def guardado_lento(*args):
            bucle.call_soon_threadsafe(desconexion.set)  # el navegador corta ahora
            time.sleep(0.4)
            visto["candado_durante"] = cache.get(_clave_candado(self.chat.pk))
            return guardar_turno(*args)

        with patch("chatbot.views.guardar_turno", guardado_lento):
            with patch("chatbot.views.responder", OrquestadorFalso().responder):
                await self.enviar(desconexion=desconexion)
            # El pedido ya terminó para el cliente; el guardado sigue en su hilo.
            for _ in range(50):
                if not self.candado_tomado():
                    break
                await asyncio.sleep(0.05)

        self.assertIsNotNone(visto["candado_durante"])
        self.assertEqual(await Mensaje.objects.acount(), 2)
        self.assertFalse(self.candado_tomado())

    async def test_sin_cortar_pero_con_otro_pedido_en_curso_es_409_bajo_asgi(self):
        await sync_to_async(tomar_candado)(self.chat.pk)

        respuesta = await self.enviar()

        self.assertEqual(respuesta.estado, 409)
        self.assertEqual(respuesta.json()["code"], "chat_request_in_progress")


class OrquestadorRealTests(BaseSSE):
    """Punto de sincronización 2: la vista con `orquestador.responder` de verdad."""

    async def test_un_turno_con_busqueda_y_tarjetas_de_punta_a_punta(self):
        def buscar(ctx, **_):
            ctx.encontrados[(1, "movie")] = {
                "id_tmdb": 1,
                "tipo": "movie",
                "titulo": "Moon",
                "poster": None,
                "anio": 2009,
            }
            return {"resultados": [{"id_tmdb": 1, "titulo": "Moon"}]}

        proveedor = ProveedorFalso(
            [
                [LlamadaTool("1", "descubrir", "{}")],
                [
                    "Te recomiendo Moon",
                    LlamadaTool(
                        "2",
                        "mostrar_tarjetas",
                        json.dumps({"tarjetas": [{"id_tmdb": 1, "tipo": "movie"}]}),
                    ),
                ],
            ]
        )
        with (
            patch.dict(FUNCIONES, {"descubrir": buscar}),
            patch("chatbot.orquestador.crear_proveedor", return_value=proveedor),
        ):
            respuesta = await self.enviar("algo como Moon")
            eventos = eventos_de(await self.leer(respuesta))

        self.assertEqual(
            [n for n, _ in eventos], ["estado", "texto", "tarjetas", "fin"]
        )
        self.assertEqual(dict(eventos)["tarjetas"]["tarjetas"][0]["titulo"], "Moon")
        guardada = await Mensaje.objects.aget(autor=TipoAutor.CHATBOT)
        self.assertEqual(guardada.texto, "Te recomiendo Moon")

    async def test_un_proveedor_que_falla_es_chat_unavailable(self):
        proveedor = ProveedorFalso([[ConnectionError("503")]])
        with patch("chatbot.orquestador.crear_proveedor", return_value=proveedor):
            with self.assertLogs("chatbot.orquestador", level="ERROR"):
                respuesta = await self.enviar()
                eventos = eventos_de(await self.leer(respuesta))

        self.assertEqual(eventos[-1][1]["code"], "chat_unavailable")
        self.assertEqual(await Mensaje.objects.acount(), 0)
