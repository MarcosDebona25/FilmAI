"""Serializers de C-08: entrada y salida de calificaciones y reseñas.

En su propio módulo, como las vistas: `catalogo` no tenía serializers (C-03 es
passthrough y devuelve el JSON de TMDB tal cual), así que este es el primero.
"""

from rest_framework import serializers

from catalogo.models import Resena
from catalogo.services.adapter import dominio_a_tmdb
from catalogo.services.traducciones import texto_localizado
from filmai.errores.serializadores import FronteraErroresMixin

# El modelo define `max_length=1000` y el rango 1-10 por validadores y
# CheckConstraint. Acá se repiten como límites del serializer para que el error
# sea un 400 con el nombre del campo —que es lo que el modal de §5d resalta— y
# no un IntegrityError de la base.
_MAX_TEXTO = Resena._meta.get_field("texto").max_length
_MIN_VALOR, _MAX_VALOR = 1, 10


class _CalificacionEntradaBase(FronteraErroresMixin, serializers.Serializer):
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

    def parametros_error(self, codigo, campo):
        if codigo == "review_update_empty":
            return {"fieldNames": ["valor", "texto"]}
        return super().parametros_error(codigo, campo)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Indicá al menos `valor` o `texto` para actualizar.",
                code="review_update_empty",
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


class ProduccionQuerySerializer(FronteraErroresMixin, serializers.Serializer):
    """Valida `?id_tmdb=&tipo=` de las lecturas.

    Se validan como cualquier payload en vez de leerlos a mano de
    `request.query_params`: así un `tipo=person` responde 400 nombrando el campo
    y no un 500 más adentro, y el contrato queda declarado en un solo lugar.
    Mismo enfoque que `PertenenciaQuerySerializer` en L-01.
    """

    id_tmdb = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=("movie", "tv"))


class ResenaComunidadSerializer(serializers.Serializer):
    """Una ReviewCard de «Reseñas de la comunidad» (§5c).

    Se arma desde la `Resena` —no desde la `Calificacion`— porque esta lista
    solo contiene reseñas con texto: el texto es la fila, y la nota y el autor
    cuelgan de ella.

    No lleva el id: son de solo lectura. Exponer el id de la reseña de otra
    persona invitaría a que el frontend intente operar sobre ella, y la API
    contestaría 404 — mejor no ofrecer la llave de una puerta que no abre.
    """

    valor = serializers.IntegerField(source="calificacion.valor")
    texto = serializers.CharField()
    fecha = serializers.DateField()
    nombre_usuario = serializers.CharField(source="calificacion.usuario.nombre_usuario")
    avatar_id = serializers.IntegerField(source="calificacion.usuario.avatar_id")


class MiResenaSerializer(CalificacionSerializer):
    """Una ReviewCard de «Mis reseñas» (P-06), que además navega a la ficha.

    Extiende la de la ficha con el título y el póster: P-06 muestra una lista de
    producciones que el usuario calificó, y sin el título no habría a dónde
    clickear. Hereda el `id`, que es lo que necesitan editar y eliminar.
    """

    titulo = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()

    def get_titulo(self, calificacion):
        return texto_localizado(
            calificacion.produccion, "titulo", self.context.get("idioma")
        )

    def get_poster(self, calificacion):
        return texto_localizado(
            calificacion.produccion, "poster", self.context.get("idioma")
        )
