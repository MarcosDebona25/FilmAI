"""Paginación de los ítems de una lista."""

from filmai.paginacion import CursorConTotal


class ListaItemCursorPagination(CursorConTotal):
    """Cursor estable para el scroll infinito del detalle de lista.

    Agrega `total` —los ítems que pasan los filtros— para el «Showing X of N»
    del canvas (L-03). La N, sin filtros, es `cantidad_items` del resumen de la
    lista (`GET /api/lists/{id}/`).
    """

    page_size = 20
    ordering = ("-fecha_agregado", "-id")
