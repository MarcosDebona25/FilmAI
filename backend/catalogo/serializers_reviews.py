"""Serializers de C-08: entrada y salida de calificaciones y reseñas.

En su propio módulo, como las vistas: `catalogo` no tenía serializers (C-03 es
passthrough y devuelve el JSON de TMDB tal cual), así que este es el primero.
"""

from rest_framework import serializers

from catalogo.models import ID_TMDB_MAXIMO, Resena
from catalogo.services.adapter import dominio_a_tmdb
from catalogo.services.traducciones import ProduccionLocalizadaMixin
from filmai.errores.serializadores import FronteraErroresMixin
from usuarios.models import EstadoCuenta

# El modelo define `max_length=1000` y el rango 1-10 por validadores y
# CheckConstraint. Acá se repiten como límites del serializer para que el error
# sea un 400 con el nombre del campo —que es lo que el modal de §5d resalta— y
# no un IntegrityError de la base.
_MAX_TEXTO = Resena._meta.get_field("texto").max_length
_MIN_VALOR, _MAX_VALOR = 1, 10
# El orden de las dos listas de reseñas: la comunidad (C-07) y «Mis reseñas».
_ORDENES = ("fecha-desc", "fecha-asc", "nota-desc", "nota-asc")


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

    id_tmdb = serializers.IntegerField(min_value=1, max_value=ID_TMDB_MAXIMO)
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
    # Con `true`, el texto no se puede editar ni borrar (409 `review_moderated`):
    # el frontend lo usa para bloquear esos controles y explicar por qué.
    moderada = serializers.BooleanField(read_only=True)
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

    id_tmdb = serializers.IntegerField(min_value=1, max_value=ID_TMDB_MAXIMO)
    tipo = serializers.ChoiceField(choices=("movie", "tv"))


class ComunidadQuerySerializer(ProduccionQuerySerializer):
    """`?orden=&nota_min=&nota_max=` de las reseñas de la comunidad (C-07).

    Los límites de nota son inclusivos: «9 o más» es `nota_min=9` y «menos de
    5» es `nota_max=4`.
    """

    orden = serializers.ChoiceField(choices=_ORDENES, default="fecha-desc")
    nota_min = serializers.IntegerField(min_value=1, max_value=10, required=False)
    nota_max = serializers.IntegerField(min_value=1, max_value=10, required=False)


class MisResenasQuerySerializer(FronteraErroresMixin, serializers.Serializer):
    """Filtros de «Mis reseñas» (perfil según el canvas, 15/10/2026).

    El tipo va como `clase` y no como `tipo`: en esta misma ruta, `id_tmdb` +
    `tipo` devuelven la calificación de una ficha.
    """

    q = serializers.CharField(max_length=100, required=False, allow_blank=True)
    texto = serializers.ChoiceField(choices=("con", "sin"), required=False)
    clase = serializers.ChoiceField(choices=("movie", "tv"), required=False)
    nota_min = serializers.IntegerField(min_value=1, max_value=10, required=False)
    nota_max = serializers.IntegerField(min_value=1, max_value=10, required=False)
    orden = serializers.ChoiceField(choices=_ORDENES, default="fecha-desc")


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
    # De una cuenta dada de baja quedan el texto y la nota, no la identidad
    # (decisión del 26/10/2026): los dos campos van en `null` y el frontend
    # muestra «Usuario dado de baja».
    nombre_usuario = serializers.SerializerMethodField()
    avatar_id = serializers.SerializerMethodField()
    autor_dado_de_baja = serializers.SerializerMethodField()

    def get_autor_dado_de_baja(self, resena) -> bool:
        return resena.calificacion.usuario.estado == EstadoCuenta.BAJA

    def get_nombre_usuario(self, resena) -> str | None:
        usuario = resena.calificacion.usuario
        return None if self.get_autor_dado_de_baja(resena) else usuario.nombre_usuario

    def get_avatar_id(self, resena) -> int | None:
        usuario = resena.calificacion.usuario
        return None if self.get_autor_dado_de_baja(resena) else usuario.avatar_id


class MiResenaSerializer(ProduccionLocalizadaMixin, CalificacionSerializer):
    """Una ReviewCard de «Mis reseñas» (P-06), que además navega a la ficha.

    Extiende la de la ficha con el título y el póster: P-06 muestra una lista de
    producciones que el usuario calificó, y sin el título no habría a dónde
    clickear. Hereda el `id`, que es lo que necesitan editar y eliminar.
    """

    titulo = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()
