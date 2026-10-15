"""Paginación por cursor con el total de filas, compartida por los módulos."""

from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class CursorConTotal(CursorPagination):
    """`CursorPagination` que además responde `total`.

    `CursorPagination` no lo trae, y es deliberado en DRF: un cursor no sabe
    cuántas filas hay detrás y así evita el `COUNT(*)`. Pero las pantallas que
    lo usan muestran el número («Reseñas de la comunidad (N)», «Showing X of
    N»), así que hace falta.

    La respuesta es `total`, `next`, `previous` y `results`, y después lo que
    agregue `extras()` en cada subclase.
    """

    def paginate_queryset(self, queryset, request, view=None):
        """Cuenta el total acá, que es donde se ve el queryset completo.

        La alternativa era que la vista pasara el total como argumento a
        `get_paginated_response()`. Funciona, pero deja una trampa: ese método lo
        llama también DRF por su cuenta en las vistas genéricas
        (`ListAPIView.list()`), sin ese argumento. El día que alguien migre estas
        vistas de `APIView` a una genérica, la respuesta empezaría a traer
        `"total": null` **sin fallar** — y un encabezado que dice «Reseñas ()» no
        se parece lo suficiente a un error como para que alguien lo investigue.

        Contándolo acá no hay argumento que olvidar ni firma que no coincida con
        la de DRF, y el paginador sirve igual en una vista genérica.
        """
        # Siempre es un QuerySet: `CursorPagination` le pide `.order_by()` dos
        # líneas más abajo, así que una lista nunca llega hasta acá.
        self.total = queryset.count()
        return super().paginate_queryset(queryset, request, view)

    def extras(self):
        """Claves que la subclase agrega al final de la respuesta."""
        return {}

    def get_paginated_response(self, data):
        return Response(
            {
                "total": self.total,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
                **self.extras(),
            }
        )
