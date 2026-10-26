"""Límite común de escrituras por usuario (decisión del 26/10/2026)."""

from rest_framework.permissions import SAFE_METHODS
from rest_framework.throttling import UserRateThrottle


class EscrituraThrottle(UserRateThrottle):
    """60 escrituras por minuto por usuario en reseñas, listas y perfil.

    La revisión de seguridad del 24/10/2026 encontró esas escrituras sin ningún
    límite: un script podía crear reseñas, listas e ítems sin tope. Las lecturas
    no cuentan (`GET`, `HEAD`, `OPTIONS`): una persona que navega nunca lo
    alcanza. El contador es por usuario y lo comparten todos esos endpoints.
    """

    scope = "escritura"

    def allow_request(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().allow_request(request, view)
