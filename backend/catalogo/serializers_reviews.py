"""Serializers de C-08: entrada y salida de calificaciones y reseñas.

En su propio módulo, como las vistas: `catalogo` no tenía serializers (C-03 es
passthrough y devuelve el JSON de TMDB tal cual), así que este es el primero.
"""

from rest_framework import serializers

from catalogo.models import Resena
from catalogo.services.adapter import dominio_a_tmdb

# El modelo define `max_length=1000` y el rango 1-10 por validadores y
# CheckConstraint. Acá se repiten como límites del serializer para que el error
# sea un 400 con el nombre del campo —que es lo que el modal de §5d resalta— y
# no un IntegrityError de la base.
_MAX_TEXTO = Resena._meta.get_field("texto").max_length
_MIN_VALOR, _MAX_VALOR = 1, 10


class _CalificacionEntradaBase(serializers.Serializer):
    """Lo que comparten crear y actualizar: el rango y el largo del texto."""

    valor = serializers.IntegerField(min_value=_MIN_VALOR, max_value=_MAX_VALOR)
    # `allow_blank=False` es lo que rechaza `texto: ""`. Vaciar el texto es
    # `DELETE /api/reviews/{id}/texto/`: si el PUT también lo hiciera, habría
    # dos caminos para lo mismo y uno quedaría sin tests el día que la regla
    # cambie.
    texto = serializers.CharField(max_length=_MAX_TEXTO, allow_blank=False)


class CrearCalificacionSerializer(_CalificacionEntradaBase):
    """`POST /api/reviews/`: qué producción, qué nota y, si hay, qué texto."""

    id_tmdb = serializers.IntegerField(min_value=1)
    # Vocabulario público de TMDB, igual que en C-03 y L-01; la traducción al
    # dominio la hace `materializar()`.
    tipo = serializers.ChoiceField(choices=("movie", "tv"))
    texto = serializers.CharField(
        max_length=_MAX_TEXTO, allow_blank=False, required=False
    )


class ActualizarCalificacionSerializer(_CalificacionEntradaBase):
    """`PUT /api/reviews/{id}/`: nota, texto, o las dos cosas.

    Los dos campos son opcionales por separado —se puede cambiar solo la nota o
    solo el texto—, pero mandar el cuerpo vacío no es una actualización: sin
    esta validación un PUT sin datos devolvería 200 sin haber hecho nada, y el
    frontend no tendría forma de notar el bug.
    """

    valor = serializers.IntegerField(
        min_value=_MIN_VALOR, max_value=_MAX_VALOR, required=False
    )
    texto = serializers.CharField(
        max_length=_MAX_TEXTO, allow_blank=False, required=False
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Indicá al menos `valor` o `texto` para actualizar."
            )
        return attrs


class CalificacionSerializer(serializers.Serializer):
    """Lo que el frontend necesita para pintar «Tu reseña» y el botón de la ficha."""

    id = serializers.IntegerField()
    valor = serializers.IntegerField()
    fecha = serializers.DateField()
    texto = serializers.SerializerMethodField()
    id_tmdb = serializers.IntegerField(source="produccion.id_tmdb")
    tipo = serializers.SerializerMethodField()

    def get_texto(self, calificacion):
        """`None` cuando se calificó sin escribir, que es un caso normal."""
        resena = getattr(calificacion, "resena", None)
        return resena.texto if resena else None

    def get_tipo(self, calificacion):
        return dominio_a_tmdb(calificacion.produccion.tipo)
