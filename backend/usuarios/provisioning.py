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


def nombres_listas_predeterminadas():
    """Relaciona las claves del modelo con los nombres conservados en la base."""
    from listas.models import ClaveLista

    return dict(zip(ClaveLista.values, LISTAS_PREDETERMINADAS, strict=True))


def provisionar_recursos_por_defecto(usuario):
    """Asegura las listas y el único chat requeridos por el MVP."""
    from chatbot.models import Chat
    from listas.models import Lista, TipoLista

    listas_creadas = 0
    with transaction.atomic():
        for clave, nombre in nombres_listas_predeterminadas().items():
            lista = Lista.objects.filter(usuario=usuario, clave=clave).first()
            creada = False
            if lista is None:
                # Compatibilidad con recursos creados durante la expansión nullable.
                lista, creada = Lista.objects.get_or_create(
                    usuario=usuario,
                    nombre__iexact=nombre,
                    defaults={
                        "nombre": nombre,
                        "tipo": TipoLista.PREDETERMINADA,
                        "clave": clave,
                    },
                )
            if lista.tipo != TipoLista.PREDETERMINADA:
                raise ValidationError(
                    f"La lista reservada '{nombre}' no es predeterminada."
                )
            if lista.clave is None:
                lista.clave = clave
                lista.save(update_fields=["clave"])
            elif lista.clave != clave:
                raise ValidationError(
                    f"La lista reservada '{nombre}' tiene otra clave."
                )
            listas_creadas += creada

        _, chat_creado = Chat.objects.get_or_create(
            usuario=usuario,
            defaults={"titulo": "Chat", "contexto": CONTEXTO_CHAT_INICIAL},
        )

    return listas_creadas, chat_creado
