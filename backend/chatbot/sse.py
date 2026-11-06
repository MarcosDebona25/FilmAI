"""El formato de los eventos del stream (server-sent events).

Cada evento es un bloque de texto que termina en una línea en blanco:

    event: texto
    data: {"delta": "Hola"}

El navegador (`frontend/lib/chat.ts`) corta por esa línea en blanco. Por eso el
`data` va en **una** sola línea: `json.dumps` sin `indent` escapa los saltos de
línea del texto como `\\n`, así que un mensaje con varios renglones no parte el
bloque. El contrato completo está en `contracts/sse-chat.md`.
"""

import json

from filmai.errores.sobre import construir_sobre

# Una única causa visible por fallo (design.md, «Error codes»): la real va al log.
CODIGO_NO_DISPONIBLE = "chat_unavailable"
ESTADO_NO_DISPONIBLE = 503


def frame(nombre, datos):
    """Un evento listo para escribir en el stream."""
    cuerpo = json.dumps(datos, ensure_ascii=False)
    return f"event: {nombre}\ndata: {cuerpo}\n\n".encode()


def frame_error(codigo=CODIGO_NO_DISPONIBLE, estado=ESTADO_NO_DISPONIBLE):
    """El evento `error`: el mismo sobre `{code, params, errors}` que los errores HTTP."""
    return frame("error", construir_sobre(codigo, estado))
