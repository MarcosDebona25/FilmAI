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
MINIMUM_AGE = 13
USERNAME_REGEX = re.compile(
    rf"^[A-Za-z0-9]{{{USERNAME_MIN_LENGTH},{USERNAME_MAX_LENGTH}}}$"
)


# Nombres de usuario que se confunden con una cuenta del sistema o del equipo
# (issue #137, 28/10/2026). Los permisos dependen de `is_staff`/`is_superuser`,
# nunca del nombre: esto solo evita la suplantación. Se comparan en minúsculas,
# sin los dígitos del final y con los números leídos como letras («Adm1n»,
# «r00t», «admin2026»).
NOMBRES_USUARIO_RESERVADOS = frozenset(
    {
        "admin",
        "administrador",
        "administradora",
        "administrator",
        "ayuda",
        "helpdesk",
        "hostmaster",
        "noreply",
        "noresponder",
        "oficial",
        "official",
        "postmaster",
        "root",
        "security",
        "seguridad",
        "sistema",
        "soporte",
        "staff",
        "support",
        "system",
        "webmaster",
    }
)
# Estos se rechazan también dentro de otro nombre («FilmAIoficial»,
# «superadmin»). «admin» no va acá: dejaría afuera a «badminton».
FRAGMENTOS_USUARIO_RESERVADOS = (
    "administr",
    "filmai",
    "moderador",
    "moderator",
    "superadmin",
    "superuser",
    "sysadmin",
)
# Lo que se le suele agregar a un nombre para que parezca oficial
# («theadmin», «soporteoficial», «adminteam»).
_PREFIJOS_DECORATIVOS = ("the", "real", "soy", "el", "la", "im", "iam")
_SUFIJOS_DECORATIVOS = ("oficial", "official", "team", "equipo", "real", "hq")
_DIGITOS_COMO_LETRAS = (
    str.maketrans("0134578", "oieastb"),
    str.maketrans("0134578", "oleastb"),
)


def es_nombre_usuario_reservado(valor):
    """`True` si `valor` es, o imita, un nombre reservado."""
    minusculas = valor.lower()
    sin_digitos_finales = re.sub(r"\d+$", "", minusculas) or minusculas
    # Y sin ningún dígito: «1admin» o «a1dmin» (PR-Agent en #142).
    sin_digitos = re.sub(r"\d", "", minusculas) or minusculas
    lecturas = {
        texto.translate(tabla)
        for texto in (minusculas, sin_digitos_finales, sin_digitos)
        for tabla in _DIGITOS_COMO_LETRAS
    }
    lecturas |= {_sin_decorado(lectura) for lectura in lecturas}
    return any(
        lectura in NOMBRES_USUARIO_RESERVADOS
        or any(fragmento in lectura for fragmento in FRAGMENTOS_USUARIO_RESERVADOS)
        for lectura in lecturas
    )


def _sin_decorado(texto):
    """Quita un prefijo y un sufijo decorativos, si los tiene."""
    for prefijo in _PREFIJOS_DECORATIVOS:
        if texto.startswith(prefijo) and len(texto) > len(prefijo):
            texto = texto[len(prefijo) :]
            break
    for sufijo in _SUFIJOS_DECORATIVOS:
        if texto.endswith(sufijo) and len(texto) > len(sufijo):
            texto = texto[: -len(sufijo)]
            break
    return texto


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

    min_length = 8
    max_length = 20
    special_characters = "@#$%&*!"

    @property
    def parametros_por_codigo(self):
        return {
            "password_too_short_or_long": {
                "minLength": self.min_length,
                "maxLength": self.max_length,
            },
            "password_no_special": {"specialCharacters": self.special_characters},
        }

    def validate(self, password, user=None):
        if len(password) < self.min_length or len(password) > self.max_length:
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
        if not re.search(f"[{re.escape(self.special_characters)}]", password):
            raise ValidationError(
                _("La contraseña debe contener un carácter especial (@#$%&*!)."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "8-20 caracteres, con al menos una mayúscula, una minúscula, un dígito y un carácter especial (@#$%&*!)."
        )
