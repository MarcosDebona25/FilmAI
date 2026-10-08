from typing import ClassVar

from rest_framework.exceptions import APIException


class NombreUsuarioOcupado(APIException):
    status_code = 409
    default_detail: ClassVar[dict] = {
        "nombre_usuario": "El nombre de usuario ya está registrado."
    }
    default_code = "username_already_used"
