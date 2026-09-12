"""Registro centralizado de avatares disponibles."""

AVATARES = {
    1: "avatar_default",
    2: "avatar_02",
    3: "avatar_03",
    4: "avatar_04",
    5: "avatar_05",
    6: "avatar_06",
    7: "avatar_07",
    8: "avatar_08",
    9: "avatar_09",
    10: "avatar_10",
}

AVATAR_IDS_VALIDOS = set(AVATARES.keys())

AVATAR_ID_DEFAULT = 1


def es_avatar_valido(avatar_id):
    """Indica si ``avatar_id`` pertenece al registro y es un entero."""
    return type(avatar_id) is int and avatar_id in AVATAR_IDS_VALIDOS


def obtener_avatar(avatar_id):
    """Obtiene el recurso asociado o ``None``."""
    return AVATARES.get(avatar_id)


def validar_avatar_id(avatar_id):
    """Lanza ``ValidationError`` si el avatar no es válido."""
    from django.core.exceptions import ValidationError

    if not es_avatar_valido(avatar_id):
        raise ValidationError(
            f"avatar_id inválido. Debe ser uno de: {sorted(AVATAR_IDS_VALIDOS)}"
        )
