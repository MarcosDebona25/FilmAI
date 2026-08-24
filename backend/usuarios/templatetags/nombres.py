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
    texto = (
        f"{(usuario.nombre or '').strip()} {(usuario.apellido or '').strip()}".strip()
    )
    return texto or "usuario"
