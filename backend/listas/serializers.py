"""Serializers de entrada y salida para la API de listas."""

from rest_framework import serializers

from catalogo.services.adapter import dominio_a_tmdb
from catalogo.services.traducciones import campos_en_ingles, texto_localizado
from filmai.errores.base import ExcepcionAPI
from filmai.errores.serializadores import FronteraErroresMixin

from .identidades import es_nombre_reservado
from .models import Lista

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

    id_tmdb = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=("movie", "tv"))


class AgregarItemSerializer(PertenenciaQuerySerializer):
    """Payload de alta de un ítem, en el vocabulario público de TMDB."""


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
        return data


class ListaItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(source="pk")
    fecha_agregado = serializers.DateTimeField()
    id_tmdb = serializers.IntegerField(source="produccion.id_tmdb")
    tipo = serializers.SerializerMethodField()
    titulo = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()
    anio = serializers.SerializerMethodField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        idioma = self.context.get("idioma")
        if idioma and idioma != "en":
            data["campos_en_ingles"] = campos_en_ingles(instance.produccion, idioma)
        return data

    def get_titulo(self, item):
        return texto_localizado(item.produccion, "titulo", self.context.get("idioma"))

    def get_poster(self, item):
        return texto_localizado(item.produccion, "poster", self.context.get("idioma"))

    def get_tipo(self, item):
        return dominio_a_tmdb(item.produccion.tipo)

    def get_anio(self, item):
        fecha = item.produccion.fecha_lanzamiento
        return fecha.year if fecha else None


class QuitarItemQuerySerializer(FronteraErroresMixin, serializers.Serializer):
    """`?borrar_calificacion=` al quitar un ítem de «Vistas» (C-08, fase 3).

    `BooleanField` acepta las formas usuales (`true`, `1`, `false`, `0`) y
    rechaza cualquier otra con un 400. Eso es deliberado: si un typo como
    `borrar_calificacion=tru` se interpretara como `false`, el usuario habría
    confirmado el borrado en el modal y recibiría un 409 sin entender por qué.

    El default es `False`, así que no mandarlo conserva exactamente el
    comportamiento anterior: el flag es permiso explícito, no una orden.
    """

    borrar_calificacion = serializers.BooleanField(default=False)
