"""Cómo se habla con el modelo, sin que el resto del chatbot sepa con cuál.

El orquestador solo conoce `ProveedorLLM`. Cambiar de empresa es sumar una clase a
`_TIPOS` y una entrada a `LLM_PROVEEDORES`.

Lo usa: `orquestador.py`.
Usa: el SDK `openai`, porque DeepSeek habla el mismo formato.
"""

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from typing import Protocol

from django.conf import settings
from openai import AsyncOpenAI

_MAX_TOKENS = 800
# Mayor que el turno a propósito: el tope real, `LLM_TIMEOUT_SECONDS`, es de la vista.
_TIMEOUT_SEGUNDOS = 30
_REINTENTOS = 1


@dataclass(frozen=True)
class LlamadaTool:
    """El modelo pidió una tool. `argumentos` es texto JSON, tal como llegó."""

    id: str
    nombre: str
    argumentos: str


@dataclass(frozen=True)
class Uso:
    """Lo que costó una llamada, tal como lo informa el proveedor.

    `entrada` y `salida` son tokens. `cache_acierto` y `cache_fallo` son los tokens
    de la entrada que el proveedor ya tenía en su caché (más baratos y rápidos) y los
    que no: DeepSeek los manda como `prompt_cache_hit_tokens` y
    `prompt_cache_miss_tokens`. Un proveedor que no los manda los deja en `None`
    (distinto de 0: «no sé» no es «ninguno»).
    """

    entrada: int
    salida: int
    cache_acierto: int | None = None
    cache_fallo: int | None = None


@dataclass(frozen=True)
class Vuelta:
    """Una respuesta completa del modelo. Es lo último que entrega `escribir()`.

    Además del texto y las tools, lleva cómo fue la llamada: `uso` (tokens), `fin`
    (por qué terminó: `stop`, `tool_calls` o `length` si se quedó sin tokens) y
    `segundos` (lo que tardó). Sirven para la línea `Turno:` del log, nunca para
    decidir nada del turno.
    """

    texto: str = ""
    llamadas: list[LlamadaTool] = field(default_factory=list)
    razonamiento: str | None = None
    uso: Uso | None = None
    fin: str | None = None
    segundos: float = 0.0


def _reloj():
    """El reloj de las llamadas. Aparte para poder fijarlo en los tests."""
    return time.perf_counter()


class ProveedorLLM(Protocol):
    """Lo que cumple cualquier proveedor.

    `escribir` entrega el texto de a pedazos (`str`) y termina con una `Vuelta`.
    Va con `def` y no con `async def`: una función async con `yield` devuelve un
    iterador que se recorre con `async for`.
    """

    def escribir(
        self,
        mensajes: list[dict],
        esquemas: list[dict],
        tool_choice: str | None = None,
    ) -> AsyncIterator[str | Vuelta]: ...

    # Con `esquemas` vacío el modelo no recibe tools y solo puede escribir texto.
    # `tool_choice="required"` lo obliga a pedir al menos una tool (la búsqueda
    # forzada del orquestador); `None` lo deja decidir a él. Un `= None` en la firma
    # es un argumento opcional: en Java sería una sobrecarga del método.


async def leer_stream(stream):
    """Convierte los fragmentos del proveedor en texto y una `Vuelta` final.

    El texto llega en `delta.content`. Cada tool llega partida: el primer fragmento
    trae `index`, `id` y `name`, y los siguientes solo `index` y un pedazo de los
    argumentos (verificado contra DeepSeek el 05/11/2026). Algunos fragmentos
    no traen `choices`, como el del uso de tokens.
    """
    texto, razonamiento, partes = [], [], {}
    uso, fin = None, None
    async for fragmento in stream:
        # Con `include_usage`, el último fragmento no trae `choices` y sí `usage`.
        if informado := getattr(fragmento, "usage", None):
            uso = _uso_de(informado)
        if not fragmento.choices:
            continue
        # `finish_reason` llega en el último fragmento con `choices` (en el resto es `None`).
        fin = getattr(fragmento.choices[0], "finish_reason", None) or fin
        delta = fragmento.choices[0].delta
        if delta.content:
            texto.append(delta.content)
            yield delta.content
        # `getattr`: `reasoning_content` no es parte del formato de OpenAI.
        pensado = getattr(delta, "reasoning_content", None)
        if pensado:
            razonamiento.append(pensado)
        for llamada in delta.tool_calls or []:
            parte = partes.setdefault(
                llamada.index, {"id": "", "nombre": "", "argumentos": ""}
            )
            parte["id"] = llamada.id or parte["id"]
            if llamada.function:
                parte["nombre"] = llamada.function.name or parte["nombre"]
                parte["argumentos"] += llamada.function.arguments or ""

    yield Vuelta(
        texto="".join(texto),
        llamadas=[LlamadaTool(**partes[indice]) for indice in sorted(partes)],
        razonamiento="".join(razonamiento) or None,
        uso=uso,
        fin=fin,
    )


def _uso_de(usage):
    """El `Uso` a partir del `usage` del SDK. Los campos de caché son de DeepSeek."""
    return Uso(
        entrada=usage.prompt_tokens,
        salida=usage.completion_tokens,
        cache_acierto=getattr(usage, "prompt_cache_hit_tokens", None),
        cache_fallo=getattr(usage, "prompt_cache_miss_tokens", None),
    )


class ProveedorOpenAICompatible:
    """Cualquier API con el formato de OpenAI: hoy, DeepSeek."""

    def __init__(self, *, base_url, modelo, api_key, thinking):
        self.base_url = base_url
        self.modelo = modelo
        self.api_key = api_key
        self.thinking = thinking

    async def escribir(self, mensajes, esquemas, tool_choice=None):
        # Un cliente por llamada: compartido entre event loops falla con
        # `Event loop is closed`, y crearlo cuesta menos de un milisegundo.
        async with AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=_TIMEOUT_SEGUNDOS,
            max_retries=_REINTENTOS,
        ) as cliente:
            # Sin esquemas, el parámetro `tools` ni se manda: la API rechaza una lista
            # vacía, y sin él el modelo no tiene cómo pedir una tool. `**{...}` abre el
            # diccionario como argumentos con nombre, igual que en `ejecutar()`.
            con_tools = {"tools": esquemas} if esquemas else {}
            if esquemas and tool_choice:
                con_tools["tool_choice"] = tool_choice
            inicio = _reloj()
            stream = await cliente.chat.completions.create(
                model=self.modelo,
                messages=mensajes,
                **con_tools,
                max_tokens=_MAX_TOKENS,
                stream=True,
                # Pide el consumo de tokens en un último fragmento del stream.
                stream_options={"include_usage": True},
                # En DeepSeek viene prendido por defecto, y hace la respuesta más lenta.
                extra_body={
                    "thinking": {"type": "enabled" if self.thinking else "disabled"}
                },
            )
            async for item in leer_stream(stream):
                if isinstance(item, Vuelta):
                    # `replace` copia la `Vuelta` (es inmutable) con un campo cambiado.
                    item = replace(item, segundos=_reloj() - inicio)
                yield item


class ProveedorFalso:
    """Reproduce un guion, para probar el orquestador sin red ni costo.

    Cada elemento de `guion` es una vuelta: una lista de `str`, `LlamadaTool` o una
    excepción, que se lanza en ese punto. Guarda en `pedidos` los mensajes que recibió,
    en `esquemas` las tools que se le ofrecieron en cada llamada y en `tool_choices`
    el `tool_choice` de cada una. `entregados` cuenta los trozos de texto entregados.
    """

    def __init__(self, guion, razonamiento=None, usos=None, fines=None, segundos=None):
        self.guion = list(guion)
        self.razonamiento = razonamiento
        # Opcionales, uno por llamada y en orden: el consumo, el motivo de fin y los
        # segundos que informa cada `Vuelta`. Sin ellos, la `Vuelta` sale sin datos.
        self.usos = list(usos or [])
        self.fines = list(fines or [])
        self.segundos = list(segundos or [])
        self.pedidos = []
        self.esquemas = []
        self.tool_choices = []
        self.entregados = 0

    async def escribir(self, mensajes, esquemas, tool_choice=None):
        # Copia: el orquestador sigue agregando mensajes a la misma lista.
        numero = len(self.pedidos)
        self.pedidos.append(list(mensajes))
        self.esquemas.append(esquemas)
        self.tool_choices.append(tool_choice)
        texto, llamadas = [], []
        for item in self.guion.pop(0):
            if isinstance(item, Exception):
                raise item
            if isinstance(item, LlamadaTool):
                llamadas.append(item)
            else:
                texto.append(item)
                self.entregados += 1
                yield item

        def de_la_llamada(lista, por_defecto=None):
            return lista[numero] if numero < len(lista) else por_defecto

        yield Vuelta(
            "".join(texto),
            llamadas,
            self.razonamiento,
            de_la_llamada(self.usos),
            de_la_llamada(self.fines),
            de_la_llamada(self.segundos, 0.0),
        )


_TIPOS = {"openai_compatible": ProveedorOpenAICompatible}


def crear_proveedor():
    """El proveedor configurado en `LLM_PROVEEDORES`."""
    configuracion = dict(settings.LLM_PROVEEDORES[0])
    return _TIPOS[configuracion.pop("tipo")](**configuracion)
