"""
Clases de throttling personalizadas para FilmAI.

Proporcionan límites de solicitudes basados en criterios específicos del dominio
(ej: email) en lugar del default de DRF que usa IP.
"""

from rest_framework.throttling import SimpleRateThrottle


class EmailRateThrottle(SimpleRateThrottle):
    """
    Throttle basado en email para recuperación de contraseña.

    Limita las solicitudes de recuperación de contraseña por cuenta de email,
    no por IP. Esto previene que un atacante evada el límite cambiando de IP.

    El límite es de 5 solicitudes por día por email.
    """

    scope = "recuperar_contrasena_email"

    def get_cache_key(self, request, view):
        """
        Usa el email del request como clave de throttle.

        Si el email no está presente o no es válido, usa la IP como fallback
        para mantener protección básica contra abuso.
        """
        email = request.data.get("email", "").strip().lower()

        if email:
            # Throttle por email
            return self.cache_format % {"scope": self.scope, "ident": email}
        else:
            # Fallback: throttle por IP si no hay email
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.get_ident(request),
            }


class EmailThrottleStatusMixin:
    """
    Mixin para agregar información de intentos restantes en la respuesta.

    Los views que usan EmailRateThrottle pueden incluir este mixin para
    devolver cuántos intentos de recuperación le quedan al usuario.
    """

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        # Solo agregar información si la respuesta es exitosa
        if response.status_code == 200:
            email = request.data.get("email", "").strip().lower()
            if email:
                # Calcular intentos restantes
                throttle = EmailRateThrottle()
                throttle.scope = "recuperar_contrasena_email"
                cache_key = throttle.cache_format % {
                    "scope": throttle.scope,
                    "ident": email,
                }

                # Obtener conteo actual desde el cache
                current_count = throttle.cache.get(cache_key, 0)
                max_requests = int(throttle.rate.split("/")[0])
                remaining = max(0, max_requests - current_count)

                response.data["intentos_restantes"] = remaining

        return response
