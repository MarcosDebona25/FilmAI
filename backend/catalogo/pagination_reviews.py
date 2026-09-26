"""Paginación de las reseñas (C-08)."""

from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class ResenaCursorPagination(CursorPagination):
    """Cursor de 20 para los dos scrolls infinitos: la ficha y «Mis reseñas».

    Cursor y no `?page=2` por la misma razón que L-01 lo eligió para los ítems
    de una lista: con offset, una reseña nueva empuja todo una posición y la
    página siguiente repite el último ítem de la anterior. El cursor apunta a un
    valor, no a un lugar en la fila.

    El desempate por `-id` no es decorativo: `fecha` es un `DateField`, o sea un
    día sin hora, así que todas las reseñas de hoy empatan. Sin un segundo
    criterio estable el orden entre ellas podría cambiar de una consulta a otra
    y el cursor perdería el hilo.
    """

    page_size = 20
    ordering = ("-fecha", "-id")

    def get_paginated_response(self, data, *, total=None):
        """Agrega `total`, que la paginación por cursor no trae.

        No traerlo es a propósito en DRF: un cursor no sabe cuántas filas hay
        detrás y evita el `COUNT(*)`. Pero el encabezado de §5c dice «Reseñas de
        la comunidad (N)», así que el número hace falta y se cuenta aparte, una
        vez, con el índice de la producción.
        """
        return Response(
            {
                "total": total,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
