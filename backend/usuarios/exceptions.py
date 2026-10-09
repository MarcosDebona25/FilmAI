from typing import ClassVar

from rest_framework.exceptions import APIException, PermissionDenied

from .models import EstadoCuenta


class NombreUsuarioOcupado(APIException):
    status_code = 409
    default_detail: ClassVar[dict] = {
        "nombre_usuario": "El nombre de usuario ya está registrado."
    }
    default_code = "username_already_used"


class CuentaInactiva(PermissionDenied):
    """Cuenta de baja o sin confirmar; solo se lanza tras validar la credencial.

    HTTP y cuerpo heredado siguen siendo el 403 genérico: el manejador
    reemplaza `detail`, y el código identifica el estado para el frontend.
    """

    def __init__(self, usuario, detail=None):
        baja = usuario.estado == EstadoCuenta.BAJA
        self.codigo = "account_deactivated" if baja else "account_pending_confirmation"
        super().__init__(detail)


def cuenta_inactiva_login(usuario):
    """Mensaje interno heredado del serializer de credenciales."""
    if usuario.estado == EstadoCuenta.BAJA:
        return CuentaInactiva(usuario, "Tu cuenta fue dada de baja.")
    return CuentaInactiva(
        usuario, "Tu cuenta aún no está activa. Revisá tu correo para confirmarla."
    )
