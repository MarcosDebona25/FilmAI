"""
Clases de throttling personalizadas para FilmAI.

Proporcionan límites de solicitudes basados en criterios específicos del dominio
(ej: email) en lugar del default de DRF que usa IP.
"""

import hashlib

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
                # El cache puede devolver una lista o un entero dependiendo de la implementación
                cache_value = throttle.cache.get(cache_key, 0)
                if isinstance(cache_value, list):
                    current_count = len(cache_value)
                else:
                    current_count = cache_value

                max_requests = int(throttle.rate.split("/")[0])
                remaining = max(0, max_requests - current_count)

                response.data["intentos_restantes"] = remaining

        return response


def _cuerpo(request):
    datos = request.data
    return datos if hasattr(datos, "get") else {}


class PorIPThrottle(SimpleRateThrottle):
    """Límite por IP del cliente (respeta `NUM_PROXIES`, ver settings.py)."""

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PorCuentaThrottle(SimpleRateThrottle):
    """Límite por cuenta o correo, sin importar desde qué IP llegue el pedido.

    Defiende contra quien prueba contraseñas (o dispara correos) rotando de IP.
    La identidad se normaliza (minúsculas, sin espacios) y se guarda como hash:
    así `Ana@x.com` y `ana@x.com` comparten contador y la clave de caché no
    lleva datos personales ni caracteres raros.

    Sin identidad en el pedido (cuerpo vacío o sin los campos esperados) no hay
    nada que limitar por cuenta: ese pedido lo cubre el límite por IP.
    """

    campos: tuple = ()

    @staticmethod
    def identidad_de(valor):
        normalizado = str(valor).strip().lower()
        return hashlib.sha256(normalizado.encode()).hexdigest()[:32]

    def get_cache_key(self, request, view):
        cuerpo = _cuerpo(request)
        for campo in self.campos:
            valor = cuerpo.get(campo)
            if isinstance(valor, str) and valor.strip():
                return self.cache_format % {
                    "scope": self.scope,
                    "ident": self.identidad_de(valor),
                }
        return None


class LoginCuentaThrottle(PorCuentaThrottle):
    scope = "login_cuenta"
    campos = ("email", "username")


class LoginIPThrottle(PorIPThrottle):
    scope = "login_ip"


class RegistroCorreoThrottle(PorCuentaThrottle):
    scope = "registro_correo"
    campos = ("correo", "email")


class RegistroIPThrottle(PorIPThrottle):
    scope = "registro_ip"


class ReenvioCorreoThrottle(PorCuentaThrottle):
    scope = "reenvio_correo"
    campos = ("email", "correo")


class ReenvioEnfriamientoThrottle(PorCuentaThrottle):
    """Una confirmación por minuto al mismo correo (enfriamiento)."""

    scope = "reenvio_enfriamiento"
    campos = ("email", "correo")


class ReenvioIPThrottle(PorIPThrottle):
    scope = "reenvio_ip"
