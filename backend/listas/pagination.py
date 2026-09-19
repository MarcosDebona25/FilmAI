"""Paginación de los ítems de una lista."""

from rest_framework.pagination import CursorPagination


class ListaItemCursorPagination(CursorPagination):
    """Cursor estable para el scroll infinito del detalle de lista."""

    page_size = 20
    ordering = ("-fecha_agregado", "-id")
