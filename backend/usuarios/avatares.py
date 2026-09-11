"""
Registro centralizado de avatares disponibles en FilmAI.

Este módulo define el conjunto válido de avatar_id y proporciona funciones
de validación para usar en serializers y formularios.

Para agregar o eliminar avatares, modificar el diccionario AVATARES.
"""

# Mapeo de avatar_id -> nombre/recurso del avatar
# Los IDs deben ser consecutivos starting from 1
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

# Conjunto de IDs válidos para validación rápida
AVATAR_IDS_VALIDOS = set(AVATARES.keys())

# ID por defecto
AVATAR_ID_DEFAULT = 1


def es_avatar_valido(avatar_id):
    """
    Verifica si un avatar_id es válido.

    Args:
        avatar_id: ID del avatar a validar

    Returns:
        bool: True si el avatar_id es válido, False en caso contrario
    """
    return avatar_id in AVATAR_IDS_VALIDOS


def obtener_avatar(avatar_id):
    """
    Obtiene el nombre/recurso del avatar dado un ID válido.

    Args:
        avatar_id: ID del avatar

    Returns:
        str: Nombre del avatar, o None si el ID es inválido
    """
    return AVATARES.get(avatar_id)


def validar_avatar_id(avatar_id):
    """
    Valida un avatar_id y lanza ValidationError si es inválido.

    Args:
        avatar_id: ID del avatar a validar

    Raises:
        ValidationError: Si el avatar_id no es válido
    """
    from django.core.exceptions import ValidationError

    if not es_avatar_valido(avatar_id):
        raise ValidationError(
            f"avatar_id inválido. Debe ser uno de: {sorted(AVATAR_IDS_VALIDOS)}"
        )
