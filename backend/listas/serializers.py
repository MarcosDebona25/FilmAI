"""Serializers de entrada y salida para la API de listas."""

from rest_framework import serializers

from catalogo.services.adapter import dominio_a_tmdb

from .models import Lista


class NombreListaSerializer(serializers.Serializer):
    """Valida el nombre de una lista personalizada."""

    nombre = serializers.CharField()

    def validate_nombre(self, value):
        nombre = " ".join(value.split())
        if not nombre:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        if len(nombre) > 80:
            raise serializers.ValidationError(
                "El nombre no puede superar los 80 caracteres."
            )
        if not any(caracter.isalnum() for caracter in nombre):
            raise serializers.ValidationError(
                "El nombre debe incluir al menos una letra o número."
            )
        if any(not (caracter.isalnum() or caracter == " ") for caracter in nombre):
            raise serializers.ValidationError(
                "Solo se permiten letras, números y espacios."
            )

        usuario = self.context["request"].user
        lista_id = self.context.get("lista_id")
        existentes = Lista.objects.filter(usuario=usuario, nombre__iexact=nombre)
        if lista_id is not None:
            existentes = existentes.exclude(pk=lista_id)
        if existentes.exists():
            from .exceptions import NombreListaDuplicado

            raise NombreListaDuplicado
        return nombre


class PertenenciaQuerySerializer(serializers.Serializer):
    """Valida la producción cuya pertenencia a listas se quiere consultar."""

    id_tmdb = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=("movie", "tv"))


class AgregarItemSerializer(PertenenciaQuerySerializer):
    """Payload de alta de un ítem, en el vocabulario público de TMDB."""


class ListaResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
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
    titulo = serializers.CharField(source="produccion.titulo")
    poster = serializers.CharField(source="produccion.poster")
    anio = serializers.SerializerMethodField()

    def get_tipo(self, item):
        return dominio_a_tmdb(item.produccion.tipo)

    def get_anio(self, item):
        fecha = item.produccion.fecha_lanzamiento
        return fecha.year if fecha else None
