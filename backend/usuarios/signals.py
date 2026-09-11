"""
Señales de la app `usuarios`.

Al crear un `Usuario` (por cualquier vía: registro tradicional o Google OAuth) se crean automáticamente sus recursos por defecto:

- Las 3 listas predeterminadas (Favoritos, Pendientes, Vistas) — CU-009 / A-01.
- Un chat por defecto — B-01.

Los imports de `listas` y `chatbot` se hacen dentro de la función para evitar imports circulares en el arranque.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Usuario
from .provisioning import provisionar_recursos_por_defecto


@receiver(post_save, sender=Usuario)
def crear_recursos_por_defecto(sender, instance, created, **kwargs):
    """Crea listas predeterminadas y chat por defecto para usuarios nuevos."""
    if not created:
        return

    provisionar_recursos_por_defecto(instance)
