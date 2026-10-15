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

    Agrega `total` a la respuesta, que `CursorPagination` no trae. No traerlo es
    deliberado en DRF: un cursor no sabe cuántas filas hay detrás y así evita el
    `COUNT(*)`. Pero el encabezado de §5c dice «Reseñas de la comunidad (N)», así
    que el número hace falta.
    """

    page_size = 20
    ordering = ("-fecha", "-id")
    # La comunidad de la ficha lo fija con el total sin filtros, para «Showing X
    # of N» (C-07). «Mis reseñas» no lo usa y la respuesta no lo trae.
    total_comunidad = None
    # «Mis reseñas» lo fija con el total propio sin filtros (15/10/2026), para
    # distinguir «no calificaste nada» de «nada con estos filtros».
    total_propias = None

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

    def get_paginated_response(self, data):
        cuerpo = {
            "total": self.total,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        }
        if self.total_comunidad is not None:
            cuerpo["total_comunidad"] = self.total_comunidad
        if self.total_propias is not None:
            cuerpo["total_propias"] = self.total_propias
        return Response(cuerpo)
