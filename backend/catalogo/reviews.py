"""Calificaciones y reseñas del usuario (C-08, CU-015).

Separado de `views.py` a propósito: esas vistas son el passthrough de TMDB
(públicas, y que nunca deben romperse por un problema nuestro), y estas
escriben en nuestra base, exigen sesión y **fallan fuerte**. Si la producción
no se pudo guardar, la calificación no puede existir y no hay respuesta
alternativa que sirva; así que se deja propagar, al revés que en C-03.

El recurso público es la dupla «calificación + texto opcional», que CU-015
trata como una sola cosa que el usuario publica. El `{id}` de la ruta es la pk
de la `Calificacion`, porque la nota es lo que siempre existe: la `Resena` es
un 1:1 opcional que cuelga de ella.

Los dos borrados hacen cosas distintas a propósito (decisión del 26/09/2026):

- `DELETE /api/reviews/{id}/texto/` borra el texto y **conserva la nota**. Es
  el 🗑️ del modal de §5d.
- `DELETE /api/reviews/{id}/` borra la nota, y el texto cae por CASCADE. Es lo
  que el 409 de L-01 le pide al usuario para poder quitar algo de «Vistas».
"""

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.exceptions import CalificacionDuplicada
from catalogo.models import Calificacion, Resena
from catalogo.pagination_reviews import ResenaCursorPagination
from catalogo.serializers_reviews import (
    ActualizarCalificacionSerializer,
    CalificacionSerializer,
    CrearCalificacionSerializer,
    MiResenaSerializer,
    ProduccionQuerySerializer,
    ResenaComunidadSerializer,
)
from catalogo.services.adapter import tmdb_a_dominio
from catalogo.services.materialization import materializar


def _produccion_pedida(request):
    """`(id_tmdb, tipo_dominio)` de los query params, validados."""
    query = ProduccionQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    datos = query.validated_data
    return datos["id_tmdb"], tmdb_a_dominio(datos["tipo"])


def _calificacion_propia(request, calificacion_id):
    """La calificación del usuario autenticado, o 404.

    La de otra persona es 404 y no 403, igual que en L-01: un 403 confirmaría
    que esa fila existe. Para quien no es su dueño, no existe.
    """
    return get_object_or_404(
        Calificacion.objects.select_related("resena", "produccion"),
        pk=calificacion_id,
        usuario=request.user,
    )


class CalificacionesView(APIView):
    """Reseñas de la comunidad sobre una producción, y alta de la propia."""

    pagination_class = ResenaCursorPagination

    def get(self, request):
        """Las reseñas de los **demás** sobre una producción (§5c).

        Tres exclusiones, cada una con su motivo:

        - **Sin texto**: una nota sin escribir no tiene nada que leer.
        - **Moderadas** (`activa=False`): decisión del 26/09/2026, solo su autor
          las ve.
        - **La de quien pregunta**: la ficha la muestra aparte, arriba, en su
          propia card. Mandarla dos veces obligaría a deduplicar a cada
          consumidor, y una lista paginada no puede prometer que la propia caiga
          en la primera página.
        """
        id_tmdb, tipo = _produccion_pedida(request)
        resenas = (
            Resena.objects.filter(
                calificacion__produccion__id_tmdb=id_tmdb,
                calificacion__produccion__tipo=tipo,
                activa=True,
                calificacion__activa=True,
            )
            .exclude(calificacion__usuario=request.user)
            # Sin esto, serializar N reseñas dispara 2N consultas para traer la
            # calificación y el usuario de cada una (el problema N+1).
            .select_related("calificacion__usuario")
        )
        paginator = self.pagination_class()
        pagina = paginator.paginate_queryset(resenas, request, view=self)
        return paginator.get_paginated_response(
            ResenaComunidadSerializer(pagina, many=True).data, total=resenas.count()
        )

    def post(self, request):
        entrada = CrearCalificacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        # Validar ANTES de materializar: un valor fuera de rango no tiene por
        # qué costar tres llamadas a TMDB ni dejar una producción escrita de
        # rebote.
        produccion = materializar(datos["id_tmdb"], datos["tipo"])

        texto = datos.get("texto")
        try:
            with transaction.atomic():
                calificacion = Calificacion.objects.create(
                    usuario=request.user, produccion=produccion, valor=datos["valor"]
                )
                if texto:
                    Resena.objects.create(calificacion=calificacion, texto=texto)
        except IntegrityError:
            # `uq_calificacion_usuario_produccion`. El atomic() es el savepoint
            # que deja la transacción usable después del error (en PostgreSQL,
            # un error la aborta entera), el mismo patrón que `materializar()`.
            raise CalificacionDuplicada from None

        return Response(
            CalificacionSerializer(calificacion).data, status=status.HTTP_201_CREATED
        )


class CalificacionDetailView(APIView):
    """Actualiza o elimina una calificación propia."""

    def put(self, request, calificacion_id):
        calificacion = _calificacion_propia(request, calificacion_id)
        entrada = ActualizarCalificacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        with transaction.atomic():
            if "valor" in datos:
                calificacion.valor = datos["valor"]
                calificacion.save(update_fields=["valor"])
            if "texto" in datos:
                # `update_or_create` cubre los dos casos con una sola llamada:
                # cambiar el texto, y escribirlo por primera vez cuando la
                # calificación se creó sin nada escrito.
                Resena.objects.update_or_create(
                    calificacion=calificacion, defaults={"texto": datos["texto"]}
                )

        calificacion.refresh_from_db()
        return Response(CalificacionSerializer(calificacion).data)

    def delete(self, request, calificacion_id):
        """Borra la calificación y, por CASCADE, su texto.

        Es físico, no lógico: CU-015 pide eliminar «permanentemente», y
        `activa` ya significa una sola cosa —moderada por un administrador
        (AD-01')—. Con dos sentidos, «¿por qué no se ve esta reseña?» no
        tendría respuesta.
        """
        _calificacion_propia(request, calificacion_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResenaTextoView(APIView):
    """Borra el texto de una calificación propia, conservando la nota."""

    def delete(self, request, calificacion_id):
        calificacion = _calificacion_propia(request, calificacion_id)
        # Idempotente: borrar el texto de una calificación que no lo tiene no
        # es un error que describa ningún problema, y así el frontend puede
        # reintentar sin interpretar un 404 ambiguo (¿no existe la calificación
        # o no existía el texto?).
        Resena.objects.filter(calificacion=calificacion).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MisCalificacionesView(APIView):
    """Las calificaciones propias: la lista de P-06, o la de una ficha.

    Una sola ruta con dos formas de respuesta según los query params:

    - **Sin filtro** → la lista paginada de «Mis reseñas» (P-06).
    - **Con `id_tmdb` y `tipo`** → un objeto solo, porque el UNIQUE
      `(usuario, produccion)` garantiza que no puede haber más de una. Devolver
      `{"results": [...]}` obligaría al frontend a desempacar algo que nunca
      tiene dos elementos.

    Medio filtro es un 400 y no «todas»: un bug del frontend que olvide `tipo`
    devolvería la lista entera y la ficha mostraría la calificación de otra
    película, que es peor que un error visible.

    A diferencia de la comunidad, acá entran las calificaciones sin texto (desde
    P-06 se pueden editar) y las moderadas (su autor las sigue viendo).
    """

    pagination_class = ResenaCursorPagination

    def get(self, request):
        propias = (
            Calificacion.objects.filter(usuario=request.user, activa=True)
            .select_related("produccion", "resena")
            .order_by("-fecha", "-id")
        )
        if request.query_params:
            id_tmdb, tipo = _produccion_pedida(request)
            calificacion = get_object_or_404(
                propias, produccion__id_tmdb=id_tmdb, produccion__tipo=tipo
            )
            return Response(MiResenaSerializer(calificacion).data)

        paginator = self.pagination_class()
        pagina = paginator.paginate_queryset(propias, request, view=self)
        return paginator.get_paginated_response(
            MiResenaSerializer(pagina, many=True).data, total=propias.count()
        )
