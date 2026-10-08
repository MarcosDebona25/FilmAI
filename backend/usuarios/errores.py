"""Metadatos compartidos de validación del perfil y el registro."""

from django.core.validators import RegexValidator
from rest_framework import serializers

from filmai.errores.serializadores import FronteraErroresMixin

from .avatares import AVATAR_IDS_VALIDOS
from .validators import (
    MINIMUM_AGE,
    PERSON_NAME_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)


class CampoNombreUsuario(serializers.RegexField):
    """Conserva el mensaje de RegexField y asigna el código en su validador."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for validador in self.validators:
            if isinstance(validador, RegexValidator):
                validador.code = "username_invalid"


class FronteraUsuarioMixin(FronteraErroresMixin):
    def parametros_error(self, codigo, campo):
        if codigo == "username_invalid":
            return {"minLength": USERNAME_MIN_LENGTH, "maxLength": USERNAME_MAX_LENGTH}
        if codigo == "person_name_invalid":
            return {"maxLength": PERSON_NAME_MAX_LENGTH}
        if codigo == "minimum_age":
            return {"minAge": MINIMUM_AGE}
        if codigo == "avatar_invalid":
            return {"allowedIds": sorted(AVATAR_IDS_VALIDOS)}
        return super().parametros_error(codigo, campo)
