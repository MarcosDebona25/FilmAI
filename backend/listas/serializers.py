"""Serializers de entrada y salida para la API de listas."""

from django.utils import timezone
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from catalogo.models import ID_TMDB_MAXIMO
from catalogo.services.adapter import dominio_a_tmdb
from catalogo.services.explore import NOTAS
from catalogo.services.traducciones import ProduccionLocalizadaMixin
from filmai.errores.base import ExcepcionAPI
from filmai.errores.serializadores import FronteraErroresMixin

from .identidades import es_nombre_reservado
from .models import MAX_LISTAS_PERSONALIZADAS, Lista

_MAX_NOMBRE = 80


class NombreListaSerializer(FronteraErroresMixin, serializers.Serializer):
    """Valida el nombre de una lista personalizada."""

    nombre = serializers.CharField()

    def parametros_error(self, codigo, campo):
        if codigo == "max_length":
            return {"maxLength": _MAX_NOMBRE}
        return super().parametros_error(codigo, campo)

    def validate_nombre(self, value):
        nombre = " ".join(value.split())
        if not nombre:
            raise serializers.ValidationError(
                "El nombre no puede estar vacío.", code="blank"
            )
        if len(nombre) > _MAX_NOMBRE:
            raise serializers.ValidationError(
                "El nombre no puede superar los 80 caracteres.", code="max_length"
            )
        if not any(caracter.isalnum() for caracter in nombre):
            raise serializers.ValidationError(
                "El nombre debe incluir al menos una letra o número.",
                code="list_name_missing_alphanumeric",
            )
        if any(not (caracter.isalnum() or caracter == " ") for caracter in nombre):
            raise serializers.ValidationError(
                "Solo se permiten letras, números y espacios.",
                code="list_name_invalid_characters",
            )

        if es_nombre_reservado(nombre):
            raise ExcepcionAPI("list_name_reserved")

        usuario = self.context["request"].user
        lista_id = self.context.get("lista_id")
        existentes = Lista.objects.filter(usuario=usuario, nombre__iexact=nombre)
        if lista_id is not None:
            existentes = existentes.exclude(pk=lista_id)
        if existentes.exists():
            from .exceptions import NombreListaDuplicado

            raise NombreListaDuplicado
        return nombre


class PertenenciaQuerySerializer(FronteraErroresMixin, serializers.Serializer):
    """Valida la producción cuya pertenencia a listas se quiere consultar."""

    id_tmdb = serializers.IntegerField(min_value=1, max_value=ID_TMDB_MAXIMO)
    tipo = serializers.ChoiceField(choices=("movie", "tv"))


class AgregarItemSerializer(PertenenciaQuerySerializer):
    """Payload de alta de un ítem, en el vocabulario público de TMDB."""


# Las tres claves que acepta `estado`. Es constante para que el contrato OpenAPI
# la nombre `EstadoListaEnum` (ver `ENUM_NAME_OVERRIDES` en settings) en vez de
# chocar con el `EstadoEnum` del estado de cuenta.
ESTADOS_DE_LISTA = ("pendientes", "viendo", "vistas")


@extend_schema_serializer(component_name="CambioEstado")
class EstadoSerializer(PertenenciaQuerySerializer):
    """`PUT /api/lists/status/`: el título y su estado nuevo (o `null` para quitarlo).

    `estado` es obligatorio aunque sea `null`: un cuerpo sin la clave es casi
    seguro un error del cliente, y quitar el estado por omisión sería destructivo.
    """

    estado = serializers.ChoiceField(choices=ESTADOS_DE_LISTA, allow_null=True)
    # Solo el Undo la manda: la fecha que tenía el título en el estado al que
    # vuelve. Sin ella (o con `null`) el ingreso nuevo lleva la fecha de ahora.
    fecha_agregado = serializers.DateTimeField(required=False, allow_null=True)

    def validate_fecha_agregado(self, value):
        if value is not None and value > timezone.now():
            raise serializers.ValidationError(
                "La fecha no puede ser futura.", code="invalid"
            )
        return value


class OrdenListasSerializer(FronteraErroresMixin, serializers.Serializer):
    """`PUT /api/lists/order/`: las listas personalizadas en el orden nuevo (L-02).

    Viaja el orden completo y no un «mover una posición»: así el mismo contrato
    sirve para el arrastre y para «Move left / Move right». Los ids repetidos son
    un 400 porque no hay forma de saber cuál de las dos posiciones se quiso.
    """

    # No puede haber más ids que listas personalizadas posibles.
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
        max_length=MAX_LISTAS_PERSONALIZADAS,
    )

    def validate_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError(
                "Un id de lista aparece más de una vez.", code="unique"
            )
        return value


class ListaItemsQuerySerializer(FronteraErroresMixin, serializers.Serializer):
    """Filtros y orden del detalle de una lista (L-03, canvas «List detail»).

    Van en el backend porque la paginación es por cursor: filtrar en el cliente
    solo vería las páginas ya cargadas. Los nombres siguen a «Mis reseñas»
    (`q`, `clase`, `orden`) y los tramos de nota a Buscar (`nota=9+`…`m5`). La
    nota es la de TMDB, no la del usuario (decisión del 15/10/2026).
    """

    q = serializers.CharField(max_length=100, required=False, allow_blank=True)
    clase = serializers.ChoiceField(choices=("movie", "tv"), required=False)
    nota = serializers.ChoiceField(choices=tuple(NOTAS), required=False)
    orden = serializers.ChoiceField(
        choices=(
            "agregado-desc",
            "agregado-asc",
            "titulo-asc",
            "nota-desc",
            "nota-asc",
        ),
        default="agregado-desc",
    )


class ListaResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    clave = serializers.CharField(allow_null=True)
    tipo = serializers.CharField()
    cantidad_items = serializers.IntegerField()
    cantidad_peliculas = serializers.IntegerField()
    cantidad_series = serializers.IntegerField()
    preview_posters = serializers.ListField(child=serializers.CharField())

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get("incluir_pertenencia"):
            data["contiene"] = bool(instance.contiene)
            data["item_id"] = instance.item_id
            # Para que el Undo de la ficha devuelva el título con su fecha.
            data["fecha_agregado"] = (
                serializers.DateTimeField().to_representation(instance.fecha_item)
                if instance.fecha_item
                else None
            )
        return data


class ListaItemSerializer(ProduccionLocalizadaMixin, serializers.Serializer):
    item_id = serializers.IntegerField(source="pk")
    fecha_agregado = serializers.DateTimeField()
    id_tmdb = serializers.IntegerField(source="produccion.id_tmdb")
    tipo = serializers.SerializerMethodField()
    titulo = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()
    anio = serializers.SerializerMethodField()
    # La «★ 8.5» de la tarjeta (canvas «List detail»). `null` si TMDB todavía
    # no la calificó: TMDB manda 0 sin votos y la UI muestra «Unrated».
    calificacion_promedio = serializers.SerializerMethodField()
    # `false` cuando TMDB ya no tiene el título (lápida, #180): sin título ni
    # póster, y el frontend muestra la tarjeta «Title no longer available».
    disponible = serializers.BooleanField(source="produccion.disponible_en_tmdb")

    def get_calificacion_promedio(self, item):
        return item.produccion.calificacion_promedio or None

    def get_tipo(self, item):
        return dominio_a_tmdb(item.produccion.tipo)

    def get_anio(self, item):
        fecha = item.produccion.fecha_lanzamiento
        return fecha.year if fecha else None
