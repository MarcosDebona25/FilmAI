"""Registro de avatares generado desde las imágenes individuales del frontend."""

import json
from pathlib import Path
from urllib.parse import quote

_catalogo = json.loads(
    Path(__file__).with_name("avatar_catalog.json").read_text(encoding="utf-8")
)
AVATARES = {
    item["id"]: {
        "id": item["id"],
        "src": f"/avatars/recortados/{quote(item['filename'])}",
    }
    for item in _catalogo
    if item.get("active", True)
}
AVATAR_IDS_VALIDOS = set(AVATARES)

AVATAR_ID_DEFAULT = 1


def es_avatar_valido(avatar_id):
    """Indica si ``avatar_id`` pertenece al registro y es un entero."""
    return type(avatar_id) is int and avatar_id in AVATAR_IDS_VALIDOS


def obtener_avatar(avatar_id):
    """Obtiene la opción asociada o ``None``."""
    return AVATARES.get(avatar_id)


def validar_avatar_id(avatar_id):
    """Lanza ``ValidationError`` si el avatar no es válido."""
    from django.core.exceptions import ValidationError

    if not es_avatar_valido(avatar_id):
        raise ValidationError("Elegí un avatar disponible.", code="avatar_invalid")
