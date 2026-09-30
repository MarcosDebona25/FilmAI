"""Operaciones de listas que otros módulos necesitan hacer.

Existe por la regla «calificada ⇒ en Vistas» (30/09/2026): calificar agrega la
producción a «Vistas» y borrar la calificación la saca. C-08 escribe entonces
en `Tiene`, que es de este módulo; en vez de armar a mano la consulta de la
lista «Vistas» desde `catalogo`, se la pide a quien es dueño de la tabla.

La vuelta no rige: marcar como vista sin calificar sigue siendo válido
(CU-011). Por eso estas funciones las llama solo C-08, y nunca al revés.

Ninguna abre su propia transacción: quien llama las pone dentro de la suya,
así la calificación y el ítem se guardan o se descartan juntos.
"""

from listas.models import Lista, Tiene, TipoLista

VISTAS = "Vistas"


def lista_vistas(usuario):
    """La lista predeterminada «Vistas» del usuario.

    `get()` y no `get_or_create()`: la crea la señal de alta del usuario
    (A-01). Si falta, el estado ya está roto y lo repara el comando
    `reparar_recursos_usuarios`; crearla acá escondería el problema.
    """
    return Lista.objects.get(
        usuario=usuario, nombre=VISTAS, tipo=TipoLista.PREDETERMINADA
    )


def agregar_a_vistas(usuario, produccion):
    """Agrega la producción a «Vistas». Si ya estaba, no hace nada.

    Devuelve `True` si la agregó. `get_or_create` cubre el caso de quien la
    marcó como vista antes de calificarla: un segundo ítem chocaría con
    `uq_tiene_lista_produccion`.
    """
    _, creado = Tiene.objects.get_or_create(
        lista=lista_vistas(usuario), produccion=produccion
    )
    return creado


def quitar_de_vistas(usuario, produccion):
    """Saca la producción de «Vistas». Si no estaba, no hace nada.

    Filtra por el dueño de la lista, no solo por la producción: la misma
    producción puede estar en las «Vistas» de otros usuarios. No falla si no
    estaba porque una calificación anterior a la regla puede no tener su ítem.
    """
    Tiene.objects.filter(
        lista__usuario=usuario,
        lista__nombre=VISTAS,
        lista__tipo=TipoLista.PREDETERMINADA,
        produccion=produccion,
    ).delete()
