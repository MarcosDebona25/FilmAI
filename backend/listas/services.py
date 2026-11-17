"""Operaciones de listas que otros módulos necesitan hacer.

**Estado único por título** (PR 4, 15/11/2026). Un usuario tiene cada título en
una sola de tres listas —«Pendientes» (Watchlist), «Viendo» (Watching) o
«Vistas» (Watched)— o en ninguna. Favoritos y las personalizadas son
independientes. `poner_estado` es la única función que escribe esas tres
listas: la usan el endpoint de estado, agregar un ítem a una predeterminada y
calificar, así la exclusividad no depende de que cada camino se acuerde de ella.

Calificar mueve a «Vistas» desde cualquier estado (regla del 30/09/2026
ampliada). Después el estado cambia libremente y la nota se conserva; la vuelta
ya no rige: calificada no implica estar en «Vistas». Lo único que sigue igual es
que borrar la nota saca de «Vistas» (`quitar_de_vistas`, R4).

`poner_estado` abre su propia transacción (se anida como savepoint si quien
llama ya tiene una): así la calificación y el ítem se guardan o se descartan
juntos, y el cambio de estado nunca deja al título sin estado a medias.
"""

from django.db import transaction

from listas.models import ClaveLista, Lista, Tiene, TipoLista

# Las listas de estado. Favoritos no está: es independiente.
CLAVES_DE_ESTADO = (ClaveLista.PENDIENTES, ClaveLista.VIENDO, ClaveLista.VISTAS)


def poner_estado(usuario, produccion, estado):
    """Pone la producción en el estado pedido y la saca de las otras dos listas.

    `estado` es una clave de `CLAVES_DE_ESTADO`, o `None` para dejarla sin
    estado. Devuelve `(estado_anterior, item)`: la clave en la que estaba (o
    `None`) y el `Tiene` actual (`None` si ya no tiene estado). Sirve de Undo:
    volver a llamarla con el estado anterior deshace el cambio.

    Si ya estaba en ese estado no hace nada (el ítem conserva su fecha), así un
    doble clic o un reintento son inocuos. Si por datos viejos estaba en más de
    un estado, el anterior es el de la fecha más reciente y todos se unifican.

    Bloquea las listas de estado del usuario (`select_for_update`): dos cambios
    en paralelo sobre el mismo título se ejecutan uno detrás del otro y no
    pueden dejarlo en dos estados.
    """
    if estado is not None and estado not in CLAVES_DE_ESTADO:
        raise ValueError(f"«{estado}» no es una lista de estado")

    with transaction.atomic():
        listas = {
            lista.clave: lista
            for lista in Lista.objects.select_for_update()
            .filter(
                usuario=usuario,
                tipo=TipoLista.PREDETERMINADA,
                clave__in=CLAVES_DE_ESTADO,
            )
            .order_by("pk")
        }
        # Sin una de las tres, el estado ya está roto (lo repara el comando
        # `reparar_recursos_usuarios`): crearla acá escondería el problema.
        if len(listas) != len(CLAVES_DE_ESTADO):
            raise Lista.DoesNotExist(
                f"Al usuario {usuario.pk} le faltan listas de estado"
            )

        actuales = list(
            Tiene.objects.filter(lista__in=listas.values(), produccion=produccion)
            .select_related("lista")
            .order_by("-fecha_agregado", "-pk")
        )
        anterior = actuales[0].lista.clave if actuales else None

        item = None
        for actual in actuales:
            if actual.lista.clave == estado and item is None:
                item = actual
            else:
                actual.delete()
        if estado is not None and item is None:
            item = Tiene.objects.create(lista=listas[estado], produccion=produccion)
    return anterior, item


def quitar_de_vistas(usuario, produccion):
    """Saca la producción de «Vistas». Si no estaba, no hace nada.

    La usa borrar una calificación (R4): sin nota no hay con qué sostener que se
    vio, y el usuario puede volver a marcarla. Filtra por el dueño de la lista,
    no solo por la producción: la misma producción puede estar en las «Vistas»
    de otros usuarios. No toca «Pendientes» ni «Viendo»: si después de calificar
    cambió el estado, borrar la nota no lo pisa.
    """
    Tiene.objects.filter(
        lista__usuario=usuario,
        lista__clave=ClaveLista.VISTAS,
        lista__tipo=TipoLista.PREDETERMINADA,
        produccion=produccion,
    ).delete()
