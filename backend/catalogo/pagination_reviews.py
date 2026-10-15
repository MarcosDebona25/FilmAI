"""Paginación de las reseñas (C-08)."""

from filmai.paginacion import CursorConTotal


class ResenaCursorPagination(CursorConTotal):
    """Cursor de 20 para los dos scrolls infinitos: la ficha y «Mis reseñas».

    Cursor y no `?page=2` por la misma razón que L-01 lo eligió para los ítems
    de una lista: con offset, una reseña nueva empuja todo una posición y la
    página siguiente repite el último ítem de la anterior. El cursor apunta a un
    valor, no a un lugar en la fila.

    El desempate por `-id` no es decorativo: `fecha` es un `DateField`, o sea un
    día sin hora, así que todas las reseñas de hoy empatan. Sin un segundo
    criterio estable el orden entre ellas podría cambiar de una consulta a otra
    y el cursor perdería el hilo.

    El `total` lo agrega `CursorConTotal`: el encabezado de §5c dice «Reseñas de
    la comunidad (N)», así que el número hace falta.
    """

    page_size = 20
    ordering = ("-fecha", "-id")
    # La comunidad de la ficha lo fija con el total sin filtros, para «Showing X
    # of N» (C-07). «Mis reseñas» no lo usa y la respuesta no lo trae.
    total_comunidad = None
    # «Mis reseñas» lo fija con el total propio sin filtros (15/10/2026), para
    # distinguir «no calificaste nada» de «nada con estos filtros».
    total_propias = None

    def extras(self):
        extras = {}
        if self.total_comunidad is not None:
            extras["total_comunidad"] = self.total_comunidad
        if self.total_propias is not None:
            extras["total_propias"] = self.total_propias
        return extras
