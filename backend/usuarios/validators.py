"""
Validadores de autenticación (CU-001).

- `ComplejidadContrasenaValidator`: reglas de contraseña del CU-001
  (8-20 caracteres, mayúscula, minúscula, dígito y carácter especial).
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# Nombre de usuario alfanumérico, 5-25 caracteres (CU-001)
USERNAME_MIN_LENGTH = 5
USERNAME_MAX_LENGTH = 25
PERSON_NAME_MAX_LENGTH = 50
USERNAME_REGEX = re.compile(
    rf"^[A-Za-z0-9]{{{USERNAME_MIN_LENGTH},{USERNAME_MAX_LENGTH}}}$"
)


def normalizar_nombre(valor):
    """Quita espacios sobrantes y conserva uno entre partes del nombre."""
    return " ".join(valor.split())


def validar_nombre_persona(valor):
    """Valida el nombre ya normalizado y devuelve el valor para persistir."""
    valor = normalizar_nombre(valor)
    if (
        not valor
        or len(valor) > PERSON_NAME_MAX_LENGTH
        or not all(parte.isalpha() for parte in valor.split(" "))
    ):
        raise ValidationError(
            "Solo letras y espacios entre palabras, máximo 50 caracteres.",
            code="person_name_invalid",
        )
    return valor


class ComplejidadContrasenaValidator:
    """Validador de contraseña según las reglas del CU-001"""

    def validate(self, password, user=None):
        if len(password) < 8 or len(password) > 20:
            raise ValidationError(
                _("La contraseña debe tener entre 8 y 20 caracteres."),
                code="password_too_short_or_long",
            )
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("La contraseña debe contener al menos una mayúscula."),
                code="password_no_upper",
            )
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("La contraseña debe contener al menos una minúscula."),
                code="password_no_lower",
            )
        if not re.search(r"\d", password):
            raise ValidationError(
                _("La contraseña debe contener al menos un dígito."),
                code="password_no_digit",
            )
        if not re.search(r"[@#$%&*!]", password):
            raise ValidationError(
                _("La contraseña debe contener un carácter especial (@#$%&*!)."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "8-20 caracteres, con al menos una mayúscula, una minúscula, un dígito y un carácter especial (@#$%&*!)."
        )
