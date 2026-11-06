"""Cómo sale el chat por la API: el historial (PR 4)."""

from rest_framework import serializers

from chatbot.models import Mensaje


class TarjetaSerializer(serializers.Serializer):
    """Una tarjeta guardada, igual que en el evento `tarjetas` (`eventos.Tarjeta`).

    Lee diccionarios del JSON de `Mensaje.tarjetas`, no modelos. Existe para que
    el contrato OpenAPI describa cada campo en lugar de «cualquier JSON».
    """

    id_tmdb = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=["movie", "tv"])
    titulo = serializers.CharField()
    poster = serializers.CharField(allow_null=True)
    anio = serializers.IntegerField(allow_null=True)


class MensajeSerializer(serializers.ModelSerializer):
    # Declarado a mano para tiparlo; por eso drf-spectacular ya no copia el
    # `help_text` del modelo y la descripción se repite acá.
    tarjetas = TarjetaSerializer(
        many=True,
        read_only=True,
        help_text=(
            "Hasta 3 tarjetas que el bot mostró con la respuesta, tal como se "
            "vieron, en el idioma de ese turno: no se vuelven a traducir. En los "
            "mensajes del usuario, lista vacía."
        ),
    )

    class Meta:
        model = Mensaje
        fields = ("id", "autor", "texto", "tarjetas", "fecha_hora")
        read_only_fields = fields


# Un mismo valor para el panel (`maxLength` del input) y el servidor: es un contrato
# compartido y por eso no es configurable (09/10/2026).
LARGO_MAXIMO_DEL_MENSAJE = 500


class EntradaMensajeSerializer(serializers.Serializer):
    """Lo que el panel manda: el texto de la pregunta (CU-013)."""

    texto = serializers.CharField(
        max_length=LARGO_MAXIMO_DEL_MENSAJE,
        trim_whitespace=True,
        help_text="La pregunta, de 1 a 500 caracteres una vez recortados los espacios.",
    )
