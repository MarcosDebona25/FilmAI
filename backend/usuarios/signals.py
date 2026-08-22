"""
Señales de la app `usuarios`.

Al crear un `Usuario` (por cualquier vía: registro tradicional o Google OAuth)
se crean automáticamente sus recursos por defecto:

- Las 3 listas predeterminadas (Favoritos, Pendientes, Vistas) — CU-009 / A-01.
- Un chat por defecto — B-01.

Los imports de `listas` y `chatbot` se hacen dentro de la función para evitar
imports circulares en el arranque.
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Usuario

LISTAS_PREDETERMINADAS = ["Favoritos", "Pendientes", "Vistas"]


@receiver(post_save, sender=Usuario)
def crear_recursos_por_defecto(sender, instance, created, **kwargs):
    """Crea listas predeterminadas y chat por defecto para usuarios nuevos."""
    if not created:
        return

    with transaction.atomic():
        from listas.models import Lista, TipoLista

        for nombre in LISTAS_PREDETERMINADAS:
            Lista.objects.create(
                usuario=instance,
                nombre=nombre,
                tipo=TipoLista.PREDETERMINADA,
            )

        from chatbot.models import Chat

        Chat.objects.create(
            usuario=instance,
            titulo="Chat",
            contexto={
                "resumen_historial": "",
                "generos_preferidos": [],
                "ultima_recomendacion": None,
                "parametros_activos": [],
            },
        )
