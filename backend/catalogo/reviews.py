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
from catalogo.serializers_reviews import (
    ActualizarCalificacionSerializer,
    CalificacionSerializer,
    CrearCalificacionSerializer,
)
from catalogo.services.materialization import materializar


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
    """Crea la calificación de una producción para el usuario autenticado."""

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
