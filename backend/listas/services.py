"""Operaciones de listas que otros módulos necesitan hacer.

Existe por la regla «calificada ⇒ en Vistas» (30/09/2026): calificar agrega la
producción a «Vistas» y borrar la calificación la saca. C-08 escribe entonces
en `Tiene`, que es de este módulo; en vez de armar a mano la consulta de la
lista «Vistas» desde `catalogo`, se la pide a quien es dueño de la tabla.

La vuelta no rige: marcar como vista sin calificar sigue siendo válido
(CU-011). Por eso `agregar_a_vistas` y `quitar_de_vistas` las llama solo C-08,
y nunca al revés.

Desde el 14/10/2026, además, entrar a «Vistas» saca de «Pendientes»: lo que
ya viste dejó de estar pendiente. Rige por los dos caminos (el botón Watched y
calificar) y solo en el momento en que la producción entra: volver a agregarla
a «Pendientes» para verla de nuevo sigue permitido.

Ninguna abre su propia transacción: quien llama las pone dentro de la suya,
así la calificación y el ítem se guardan o se descartan juntos.
"""

from listas.models import ClaveLista, Lista, Tiene, TipoLista


def lista_vistas(usuario):
    """La lista predeterminada «Vistas» del usuario.

    `get()` y no `get_or_create()`: la crea la señal de alta del usuario
    (A-01). Si falta, el estado ya está roto y lo repara el comando
    `reparar_recursos_usuarios`; crearla acá escondería el problema.
    """
    return Lista.objects.get(
        usuario=usuario, clave=ClaveLista.VISTAS, tipo=TipoLista.PREDETERMINADA
    )


def agregar_a_vistas(usuario, produccion):
    """Agrega la producción a «Vistas» y la saca de «Pendientes».

    Si ya estaba en «Vistas» no hace nada, tampoco con «Pendientes»: quien la
    volvió a agregar ahí para verla de nuevo no la pierde al calificarla.
    Devuelve `True` si la agregó. `get_or_create` cubre el caso de quien la
    marcó como vista antes de calificarla: un segundo ítem chocaría con
    `uq_tiene_lista_produccion`.
    """
    _, creado = Tiene.objects.get_or_create(
        lista=lista_vistas(usuario), produccion=produccion
    )
    if creado:
        quitar_de_pendientes(usuario, produccion)
    return creado


def quitar_de_pendientes(usuario, produccion):
    """Saca la producción de «Pendientes» del usuario. Si no estaba, no hace nada.

    Devuelve `True` si la sacó, para que quien llama pueda avisarlo.
    """
    borrados, _ = Tiene.objects.filter(
        lista__usuario=usuario,
        lista__clave=ClaveLista.PENDIENTES,
        lista__tipo=TipoLista.PREDETERMINADA,
        produccion=produccion,
    ).delete()
    return borrados > 0


def quitar_de_vistas(usuario, produccion):
    """Saca la producción de «Vistas». Si no estaba, no hace nada.

    Filtra por el dueño de la lista, no solo por la producción: la misma
    producción puede estar en las «Vistas» de otros usuarios. No falla si no
    estaba porque una calificación anterior a la regla puede no tener su ítem.
    """
    Tiene.objects.filter(
        lista__usuario=usuario,
        lista__clave=ClaveLista.VISTAS,
        lista__tipo=TipoLista.PREDETERMINADA,
        produccion=produccion,
    ).delete()
