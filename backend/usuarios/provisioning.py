"""Provisión consistente de los recursos iniciales de un usuario."""

from django.core.exceptions import ValidationError
from django.db import transaction

LISTAS_PREDETERMINADAS = ("Favoritos", "Pendientes", "Vistas")
CONTEXTO_CHAT_INICIAL = {
    "resumen_historial": "",
    "generos_preferidos": [],
    "ultima_recomendacion": None,
    "parametros_activos": [],
}


def provisionar_recursos_por_defecto(usuario):
    """Asegura las listas y el único chat requeridos por el MVP."""
    from chatbot.models import Chat
    from listas.models import Lista, TipoLista

    listas_creadas = 0
    with transaction.atomic():
        for nombre in LISTAS_PREDETERMINADAS:
            lista, creada = Lista.objects.get_or_create(
                usuario=usuario,
                nombre=nombre,
                defaults={"tipo": TipoLista.PREDETERMINADA},
            )
            if lista.tipo != TipoLista.PREDETERMINADA:
                raise ValidationError(
                    f"La lista reservada '{nombre}' no es predeterminada."
                )
            listas_creadas += creada

        _, chat_creado = Chat.objects.get_or_create(
            usuario=usuario,
            defaults={"titulo": "Chat", "contexto": CONTEXTO_CHAT_INICIAL},
        )

    return listas_creadas, chat_creado
