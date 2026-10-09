"""Filtros de template para saludos en emails transaccionales."""

from django import template

register = template.Library()


# Saludo de reserva por idioma: "Hola usuario," / "Hi there,".
_SIN_NOMBRE = {"es": "usuario", "en": "there"}


@register.filter
def nombre_completo(usuario, idioma="es") -> str:
    """Devuelve "Nombre Apellido"; "usuario" si ambos están vacíos.

    Regla global para emails (docs/decisiones.md, 24/08/2026): el saludo
    siempre muestra nombre + apellido del usuario de FilmAI, con fallback
    genérico para cuentas sin esos datos (p. ej. usuarios del seed).
    """
    nombre = (getattr(usuario, "nombre", "") or "").strip()
    apellido = (getattr(usuario, "apellido", "") or "").strip()
    texto = f"{nombre} {apellido}".strip()
    return texto or _SIN_NOMBRE.get(idioma, _SIN_NOMBRE["en"])
