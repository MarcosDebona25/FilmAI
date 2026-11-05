"""Cómo se habla con el modelo, sin que el resto del chatbot sepa con cuál.

El orquestador solo conoce `ProveedorLLM`. Cambiar de empresa es sumar una clase a
`_TIPOS` y una entrada a `LLM_PROVEEDORES`.

Lo usa: `orquestador.py`.
Usa: el SDK `openai`, porque DeepSeek habla el mismo formato.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
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
class Vuelta:
    """Una respuesta completa del modelo. Es lo último que entrega `escribir()`."""

    texto: str = ""
    llamadas: list[LlamadaTool] = field(default_factory=list)
    razonamiento: str | None = None


class ProveedorLLM(Protocol):
    """Lo que cumple cualquier proveedor.

    `escribir` entrega el texto de a pedazos (`str`) y termina con una `Vuelta`.
    Va con `def` y no con `async def`: una función async con `yield` devuelve un
    iterador que se recorre con `async for`.
    """

    def escribir(
        self, mensajes: list[dict], esquemas: list[dict]
    ) -> AsyncIterator[str | Vuelta]: ...


async def leer_stream(stream):
    """Convierte los fragmentos del proveedor en texto y una `Vuelta` final.

    El texto llega en `delta.content`. Cada tool llega partida: el primer fragmento
    trae `index`, `id` y `name`, y los siguientes solo `index` y un pedazo de los
    argumentos (verificado contra DeepSeek el 05/11/2026). Algunos fragmentos
    no traen `choices`, como el del uso de tokens.
    """
    texto, razonamiento, partes = [], [], {}
    async for fragmento in stream:
        if not fragmento.choices:
            continue
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
    )


class ProveedorOpenAICompatible:
    """Cualquier API con el formato de OpenAI: hoy, DeepSeek."""

    def __init__(self, *, base_url, modelo, api_key, thinking):
        self.base_url = base_url
        self.modelo = modelo
        self.api_key = api_key
        self.thinking = thinking

    async def escribir(self, mensajes, esquemas):
        # Un cliente por llamada: compartido entre event loops falla con
        # `Event loop is closed`, y crearlo cuesta menos de un milisegundo.
        async with AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=_TIMEOUT_SEGUNDOS,
            max_retries=_REINTENTOS,
        ) as cliente:
            stream = await cliente.chat.completions.create(
                model=self.modelo,
                messages=mensajes,
                tools=esquemas,
                max_tokens=_MAX_TOKENS,
                stream=True,
                # En DeepSeek viene prendido por defecto, y hace la respuesta más lenta.
                extra_body={
                    "thinking": {"type": "enabled" if self.thinking else "disabled"}
                },
            )
            async for item in leer_stream(stream):
                yield item


class ProveedorFalso:
    """Reproduce un guion, para probar el orquestador sin red ni costo.

    Cada elemento de `guion` es una vuelta: una lista de `str`, `LlamadaTool` o una
    excepción, que se lanza en ese punto. Guarda en `pedidos` lo que recibió.
    """

    def __init__(self, guion, razonamiento=None):
        self.guion = list(guion)
        self.razonamiento = razonamiento
        self.pedidos = []

    async def escribir(self, mensajes, esquemas):
        # Copia: el orquestador sigue agregando mensajes a la misma lista.
        self.pedidos.append(list(mensajes))
        texto, llamadas = [], []
        for item in self.guion.pop(0):
            if isinstance(item, Exception):
                raise item
            if isinstance(item, LlamadaTool):
                llamadas.append(item)
            else:
                texto.append(item)
                yield item
        yield Vuelta("".join(texto), llamadas, self.razonamiento)


_TIPOS = {"openai_compatible": ProveedorOpenAICompatible}


def crear_proveedor():
    """El proveedor configurado en `LLM_PROVEEDORES`."""
    configuracion = dict(settings.LLM_PROVEEDORES[0])
    return _TIPOS[configuracion.pop("tipo")](**configuracion)
