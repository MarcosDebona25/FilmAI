"""Topes de llamadas a TMDB: por pedido HTTP y por IP (auditoría F6, 24/10/2026).

Buscar con texto en «Todo» hace hasta 10 llamadas (20 si hay que completar en
inglés) y el cliente reintenta cada una hasta 3 veces: sin tope, un solo pedido
podía terminar en 80 llamadas contra nuestra clave de TMDB. Y el límite del
catálogo (60 pedidos por minuto) cuenta pedidos, no llamadas.

La vista abre un contador con `contar_llamadas(ident)` y el cliente llama a
`registrar_llamada()` antes de cada pedido HTTP, reintentos incluidos. Cada
llamada cuenta para dos topes:

- **Por pedido**: el contador vive en una `ContextVar`, así cada pedido ve el
  suyo aunque varios corran a la vez. Pasado el tope, `TMDBPresupuestoAgotado`.
- **Por IP y por minuto**: un `incr` de la caché de Django (Redis en
  producción), atómico, en el momento de cada llamada. Cobrar al terminar el
  pedido dejaba pasar ráfagas: pedidos en paralelo veían todos el contador en
  cero (lo señaló PR-Agent en #129). Pasado el límite, 429 (Too Many Requests).

Lo que sale de la caché de Redis no llama al cliente, así que no cuenta. Fuera
de un pedido (Celery, la sync diaria, el seed) no hay contador ni topes.
"""

import contextvars
import math
import threading
import time
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import Throttled

from catalogo.exceptions import TMDBPresupuestoAgotado

# El máximo legítimo es Buscar con texto en «Todo» y en español: 20 llamadas.
# El margen deja lugar a algún reintento antes de cortar.
MAX_LLAMADAS_POR_PEDIDO = 30

# Ventana fija de reloj: la clave cambia cada minuto y vence sola. En el borde
# entre dos minutos pueden juntarse hasta el doble del límite; es el compromiso
# de un contador simple y atómico.
VENTANA_IP_SEGUNDOS = 60

_contador = contextvars.ContextVar("llamadas_tmdb", default=None)


class Contador:
    """Llamadas de un pedido. Buscar las hace desde varios hilos: va con lock."""

    def __init__(self, ident=None):
        self._lock = threading.Lock()
        self.total = 0
        self.ident = ident

    def sumar(self):
        with self._lock:
            self.total += 1
            return self.total


@contextmanager
def contar_llamadas(ident=None):
    """Abre el contador del pedido; `ident` es la IP a la que se le cobra."""
    contador = Contador(ident)
    token = _contador.set(contador)
    try:
        yield contador
    finally:
        _contador.reset(token)


def registrar_llamada():
    """Cuenta una llamada del pedido actual; pasado algún tope, la corta."""
    contador = _contador.get()
    if contador is None:
        return
    if contador.sumar() > MAX_LLAMADAS_POR_PEDIDO:
        raise TMDBPresupuestoAgotado(
            f"El pedido superó {MAX_LLAMADAS_POR_PEDIDO} llamadas a TMDB"
        )
    if contador.ident is not None:
        _cobrar_a_la_ip(contador.ident)


def _cobrar_a_la_ip(ident):
    ahora = time.time()
    clave = f"tmdb_llamadas:{ident}:{int(ahora // VENTANA_IP_SEGUNDOS)}"
    if _sumar(clave) > settings.TMDB_LLAMADAS_POR_IP_POR_MINUTO:
        resto = VENTANA_IP_SEGUNDOS - ahora % VENTANA_IP_SEGUNDOS
        raise Throttled(wait=math.ceil(resto))


def _sumar(clave):
    """`incr` atómico; si la clave no existe (primera llamada del minuto, o Redis
    la desalojó), se siembra en 1. `add` solo crea si no existe: si otro pedido
    la sembró justo antes, se vuelve a sumar (sugerencia de PR-Agent en #129)."""
    try:
        return cache.incr(clave)
    except ValueError:
        if cache.add(clave, 1, timeout=VENTANA_IP_SEGUNDOS * 2):
            return 1
        return cache.incr(clave)


def con_contexto(funcion):
    """`funcion` envuelta para correr en un hilo con el contexto del pedido.

    Los hilos de `ThreadPoolExecutor` no heredan las `ContextVar`: sin esto, las
    llamadas de Buscar no se contarían. Cada ejecución usa su propia copia del
    contexto (una copia no se puede usar en dos hilos a la vez), y todas
    comparten el mismo `Contador`.
    """
    contexto = contextvars.copy_context()

    def en_el_pedido(*args, **kwargs):
        return contexto.copy().run(funcion, *args, **kwargs)

    return en_el_pedido
