"""Tests del contrato de `responder()` (PR 0) a través de `OrquestadorFalso`.

No tocan la base: el falso no la usa, así que alcanza `SimpleTestCase`. Los
métodos son `async def`: Django los corre dentro de un event loop.
"""

import asyncio
from typing import get_type_hints

from django.test import SimpleTestCase

from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Tarjeta, Texto
from chatbot.orquestador_falso import GUION_BASICO, OrquestadorFalso

CHAT = object()  # El falso no mira el chat; cualquier objeto sirve.


async def recolectar(responder):
    return [evento async for evento in responder]


class ContratoTests(SimpleTestCase):
    async def test_el_guion_sale_en_orden_y_termina_en_un_unico_resultado(self):
        eventos = await recolectar(OrquestadorFalso().responder(CHAT, "hola", "es"))

        self.assertEqual(eventos, list(GUION_BASICO))
        self.assertIsInstance(eventos[-1], Resultado)
        self.assertEqual(sum(isinstance(e, Resultado) for e in eventos), 1)
        self.assertTrue(all(isinstance(e, Estado | Texto) for e in eventos[:-1]))

    async def test_falla_en_entrega_lo_anterior_y_lanza_error_sin_resultado(self):
        recibidos = []
        falso = OrquestadorFalso(falla_en=2)

        with self.assertRaises(ErrorDelTurno):
            async for evento in falso.responder(CHAT, "hola", "es"):
                recibidos.append(evento)

        self.assertEqual(recibidos, list(GUION_BASICO[:2]))
        self.assertFalse(any(isinstance(e, Resultado) for e in recibidos))

    async def test_cancelar_durante_una_demora_corta_el_turno(self):
        # Sin depender del reloj: se pide el segundo evento en una tarea, la
        # tarea queda dormida en la demora (60 s) y ahí se la cancela.
        lento = OrquestadorFalso(demora=60).responder(CHAT, "hola", "es")
        tarea = asyncio.create_task(anext(lento))
        await asyncio.sleep(0)  # La tarea arranca y queda esperando la demora.
        tarea.cancel()

        with self.assertRaises(asyncio.CancelledError):
            await tarea
        # El turno cancelado quedó cerrado: no entrega nada más.
        with self.assertRaises(StopAsyncIteration):
            await anext(lento)

    async def test_registra_los_argumentos_de_cada_llamada(self):
        falso = OrquestadorFalso()

        await recolectar(falso.responder(CHAT, "algo para ver", "en"))

        self.assertEqual(falso.llamadas, [(CHAT, "algo para ver", "en")])

    def test_las_tarjetas_del_resultado_tienen_la_forma_de_tarjeta(self):
        claves = set(get_type_hints(Tarjeta))
        resultado = GUION_BASICO[-1]

        self.assertEqual(
            claves, {"id_tmdb", "tipo", "titulo", "poster", "anio", "nota_tmdb"}
        )
        for tarjeta in resultado.tarjetas:
            self.assertEqual(set(tarjeta), claves)
            self.assertIn(tarjeta["tipo"], ("movie", "tv"))

    def test_nota_tmdb_es_la_unica_clave_opcional(self):
        # Las tarjetas guardadas antes del 07/11/2026 no la traen: el contrato
        # no puede exigirla. Las demás claves siguen siendo obligatorias.
        self.assertEqual(Tarjeta.__optional_keys__, {"nota_tmdb"})
        self.assertEqual(
            Tarjeta.__required_keys__, {"id_tmdb", "tipo", "titulo", "poster", "anio"}
        )
