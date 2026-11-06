"""Lo que limita al chat: una respuesta a la vez por chat y N mensajes por hora.

Los dos contadores viven en la caché (Redis en producción), como los del TMDB en
`catalogo/presupuesto.py`: `add` e `incr` son atómicos en Redis, así que dos
pedidos simultáneos no pasan los dos.
"""

import math
import secrets
import time

from django.conf import settings
from django.core.cache import cache

VENTANA_MENSAJES_SEGUNDOS = 3600


def _clave_candado(chat_id):
    return f"chat:{chat_id}:en_curso"


def tomar_candado(chat_id):
    """Toma el candado «una respuesta en curso» y devuelve su token; `None` si ya está tomado.

    El valor guardado es un token al azar y no un `1`: así quien lo suelta puede
    comprobar que el candado sigue siendo suyo (ver `soltar_candado`).

    Vence solo a los `LLM_TIMEOUT_SECONDS + 35` segundos (60 con los 25 de
    siempre). Se deriva del tiempo del turno para que subirlo en `.env` nunca deje
    vencer el candado a mitad de un turno; los 35 s de margen cubren el guardado
    y la liberación. Si el proceso muere sin soltarlo, el vencimiento lo libera.
    """
    token = secrets.token_hex(16)
    vencimiento = math.ceil(settings.LLM_TIMEOUT_SECONDS + 35)
    return token if cache.add(_clave_candado(chat_id), token, vencimiento) else None


def soltar_candado(chat_id, token):
    """Suelta el candado solo si todavía es de este pedido.

    Si el pedido tardó tanto que el candado venció y otro pedido lo tomó, un
    `delete` a ciegas le sacaría el candado al nuevo. Entre el `get` y el `delete`
    hay una ventana mínima; para cerrarla del todo haría falta un script de Redis,
    y no se justifica para un candado que además vence solo.
    """
    clave = _clave_candado(chat_id)
    if cache.get(clave) == token:
        cache.delete(clave)


def sumar_mensaje(usuario_id):
    """Cuenta un mensaje en la hora actual. Devuelve `(dentro_del_tope, segundos_para_la_proxima_hora)`.

    Ventana fija de reloj: la clave cambia cada hora y vence sola. En el borde
    entre dos horas pueden juntarse hasta el doble del tope; es el compromiso de un
    contador simple y atómico (el mismo que el del TMDB).
    """
    ahora = time.time()
    ventana = int(ahora // VENTANA_MENSAJES_SEGUNDOS)
    clave = f"chat:{usuario_id}:mensajes:{ventana}"
    try:
        total = cache.incr(clave)
    except ValueError:
        # Primera del período, o Redis la desalojó. `add` solo crea si no existe:
        # si otro pedido la sembró justo antes, se vuelve a sumar.
        if cache.add(clave, 1, timeout=VENTANA_MENSAJES_SEGUNDOS * 2):
            total = 1
        else:
            total = cache.incr(clave)
    resto = math.ceil(VENTANA_MENSAJES_SEGUNDOS - ahora % VENTANA_MENSAJES_SEGUNDOS)
    return total <= settings.CHAT_MENSAJES_POR_HORA, resto
