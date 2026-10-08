"""Filtros de template para saludos en emails transaccionales."""

from django import template

register = template.Library()


@register.filter
def nombre_completo(usuario) -> str:
    """Devuelve "Nombre Apellido"; "usuario" si ambos están vacíos.

    Regla global para emails (docs/decisiones.md, 24/08/2026): el saludo
    siempre muestra nombre + apellido del usuario de FilmAI, con fallback
    genérico para cuentas sin esos datos (p. ej. usuarios del seed).
    """
    nombre = (getattr(usuario, "nombre", "") or "").strip()
    apellido = (getattr(usuario, "apellido", "") or "").strip()
    texto = f"{nombre} {apellido}".strip()
    return texto or "usuario"
