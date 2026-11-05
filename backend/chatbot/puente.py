"""El único punto donde el código async llama a código síncrono.

El ORM, TMDB, Ollama y las tools son funciones comunes: bloquean mientras esperan.
Llamarlas directo desde código async frenaría al event loop, que atiende a todos
los pedidos. `en_hilo` las corre en otro hilo y espera sin bloquear.

Lo usan: `orquestador.py` y, desde el PR 5, la vista del chat.
"""

from asgiref.sync import sync_to_async


def en_hilo(funcion, *args, **kwargs):
    """Corre `funcion` en el hilo de este pedido. Se usa con `await`.

    `thread_sensitive=True` hace que todo el pedido use un mismo hilo, y por lo
    tanto una misma conexión a la base. Django abre un hilo por pedido, así que las
    tools de un usuario no hacen fila detrás de las de otro.
    """
    return sync_to_async(funcion, thread_sensitive=True)(*args, **kwargs)
