"""Fuente de códigos públicos, contextos HTTP y parámetros de máquina."""

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DefinicionCodigo:
    mensaje: str
    contextos: dict[str, int]
    parametros: dict[str, str] = field(default_factory=dict)
    categoria: str = "error"
    minimos: dict[str, int] = field(default_factory=dict)

    def validar_parametros(self, parametros):
        """Los parámetros son opcionales; nunca se aceptan claves desconocidas."""
        if not isinstance(parametros, dict):
            raise ValueError("Los parámetros deben ser un objeto.")
        for nombre, valor in parametros.items():
            tipo = self.parametros.get(nombre)
            if tipo is None or not _es_tipo(valor, tipo):
                raise ValueError(f"Parámetro no permitido: {nombre}.")
            if nombre in self.minimos and valor < self.minimos[nombre]:
                raise ValueError(f"Parámetro fuera de rango: {nombre}.")


def _es_tipo(valor, tipo):
    if tipo.endswith("[]"):
        return isinstance(valor, list) and all(
            _es_tipo(elemento, tipo[:-2]) for elemento in valor
        )
    if tipo == "string":
        return isinstance(valor, str)
    if isinstance(valor, bool):
        return False
    if tipo == "integer":
        return isinstance(valor, int)
    if tipo == "number":
        return isinstance(valor, int) or (
            isinstance(valor, float) and math.isfinite(valor)
        )
    return False


CATALOGO = {
    "validation_error": DefinicionCodigo(
        "Los datos enviados no son válidos.", {"validacion": 400}
    ),
    "not_authenticated": DefinicionCodigo(
        "Autenticación requerida. Por favor, iniciá sesión.", {"autenticacion": 401}
    ),
    "invalid_credentials": DefinicionCodigo(
        "Credenciales inválidas. Verificá tu correo/nombre de usuario y contraseña.",
        {"login": 400, "autenticacion": 401},
    ),
    "permission_denied": DefinicionCodigo(
        "No tenés permisos para realizar esta acción.", {"api": 403}
    ),
    "documentation_staff_required": DefinicionCodigo(
        "Para consultar esta documentación, ingresá al Admin con una cuenta staff.",
        {"documentacion": 403},
    ),
    "not_found": DefinicionCodigo("El recurso solicitado no existe.", {"api": 404}),
    "method_not_allowed": DefinicionCodigo(
        "Método HTTP no permitido para este endpoint.",
        {"api": 405},
        {"method": "string"},
    ),
    "not_acceptable": DefinicionCodigo(
        "No se puede satisfacer el encabezado Accept.", {"api": 406}
    ),
    "unsupported_media_type": DefinicionCodigo(
        "Tipo de contenido no soportado.", {"api": 415}, {"mediaType": "string"}
    ),
    "parse_error": DefinicionCodigo(
        "El cuerpo de la solicitud no es válido.", {"api": 400}
    ),
    "throttled": DefinicionCodigo(
        "Demasiadas solicitudes. Intentá de nuevo más tarde.",
        {"api": 429},
        {"retry_after_seconds": "integer"},
        minimos={"retry_after_seconds": 0},
    ),
    "server_error": DefinicionCodigo("Error interno del servidor.", {"api": 500}),
    "upstream_bad_request": DefinicionCodigo(
        "TMDB rechazó los parámetros de la solicitud.", {"tmdb": 400}
    ),
    "upstream_not_found": DefinicionCodigo(
        "El recurso solicitado no existe en TMDB.", {"tmdb": 404}
    ),
    "upstream_error": DefinicionCodigo("Error del servicio TMDB.", {"tmdb": 502}),
    "upstream_unavailable": DefinicionCodigo(
        "No se pudo consultar el servicio TMDB.", {"tmdb": 503}
    ),
    "invalid_token": DefinicionCodigo("El token no es válido.", {"autenticacion": 401}),
    "session_revoked": DefinicionCodigo(
        "La sesión fue revocada.", {"autenticacion": 401}
    ),
    "account_deactivated": DefinicionCodigo(
        "Tu cuenta fue dada de baja.", {"login": 403}
    ),
    "account_pending_confirmation": DefinicionCodigo(
        "Tu cuenta aún no está activa. Revisá tu correo para confirmarla.",
        {"login": 403},
    ),
    "link_expired": DefinicionCodigo("El enlace expiró.", {"enlace": 400}),
    "link_invalid": DefinicionCodigo("El enlace no es válido.", {"enlace": 400}),
    "already_confirmed": DefinicionCodigo(
        "La cuenta ya fue confirmada.", {"enlace": 400}
    ),
    "list_name_duplicated": DefinicionCodigo(
        "Ya tenés una lista con ese nombre.", {"listas": 409}
    ),
    "list_name_reserved": DefinicionCodigo(
        "Ese nombre está reservado para una lista predeterminada.", {"listas": 409}
    ),
    "list_item_duplicated": DefinicionCodigo(
        "La producción ya pertenece a esta lista.", {"listas": 409}
    ),
    "default_list_protected": DefinicionCodigo(
        "Las listas predeterminadas no se pueden modificar ni eliminar.",
        {"listas": 409},
    ),
    "rating_blocks_removal_from_watched": DefinicionCodigo(
        "Eliminá la calificación antes de quitar esta producción de Vistas.",
        {"listas": 409},
    ),
    "rating_duplicated": DefinicionCodigo(
        "Ya calificaste esta producción. Editá tu calificación.",
        {"calificaciones": 409},
    ),
    "username_already_used": DefinicionCodigo(
        "El nombre de usuario ya está registrado.", {"validacion": 400, "perfil": 409}
    ),
    "password_reset_requested": DefinicionCodigo(
        "Solicitud de recuperación recibida.",
        {"recuperacion": 200},
        categoria="success",
    ),
    "password_reset_completed": DefinicionCodigo(
        "La contraseña fue restablecida. Inicia sesión nuevamente.",
        {"recuperacion": 200},
        categoria="success",
    ),
    "password_updated": DefinicionCodigo(
        "Contraseña actualizada. Inicia sesión nuevamente en tus dispositivos.",
        {"perfil": 200},
        categoria="success",
    ),
    "account_deactivated_successfully": DefinicionCodigo(
        "Tu cuenta fue dada de baja. Tus datos se conservan.",
        {"cuenta": 200},
        categoria="success",
    ),
    "email_confirmed": DefinicionCodigo(
        "Correo confirmado.", {"confirmacion": 200}, categoria="success"
    ),
    "csrf_ready": DefinicionCodigo("ok", {"csrf": 200}, categoria="success"),
    "registration_pending_confirmation": DefinicionCodigo(
        "Correo de verificación enviado.", {"registro": 201}, categoria="success"
    ),
    "confirmation_email_sent": DefinicionCodigo(
        "Solicitud de confirmación recibida.",
        {"confirmacion": 200},
        categoria="success",
    ),
    "logged_out": DefinicionCodigo(
        "Sesión cerrada.", {"logout": 200}, categoria="success"
    ),
}


# Cada hoja conserva HTTP 400; el manejador utiliza validation_error arriba.
CATALOGO.update(
    {
        "required": DefinicionCodigo("Este campo es requerido.", {"validacion": 400}),
        "blank": DefinicionCodigo(
            "Este campo no puede estar en blanco.", {"validacion": 400}
        ),
        "null": DefinicionCodigo("Este campo no puede ser nulo.", {"validacion": 400}),
        "invalid": DefinicionCodigo(
            "Valor inválido.", {"validacion": 400}, {"expectedType": "string"}
        ),
        "invalid_choice": DefinicionCodigo(
            "La elección no es válida.",
            {"validacion": 400},
            {"allowedValues": "string[]"},
        ),
        "max_length": DefinicionCodigo(
            "El texto supera la longitud máxima.",
            {"validacion": 400},
            {"maxLength": "integer"},
        ),
        "min_length": DefinicionCodigo(
            "El texto no alcanza la longitud mínima.",
            {"validacion": 400},
            {"minLength": "integer"},
        ),
        "min_value": DefinicionCodigo(
            "El valor no alcanza el mínimo.",
            {"validacion": 400},
            {"minValue": "number"},
        ),
        "max_value": DefinicionCodigo(
            "El valor supera el máximo.", {"validacion": 400}, {"maxValue": "number"}
        ),
        "unique": DefinicionCodigo("Este valor ya existe.", {"validacion": 400}),
        "not_a_dict": DefinicionCodigo("Se esperaba un objeto.", {"validacion": 400}),
        "number_not_finite": DefinicionCodigo(
            "Se esperaba un número finito.", {"validacion": 400}
        ),
        "email_already_used": DefinicionCodigo(
            "El correo ya está registrado.", {"validacion": 400}
        ),
        "email_or_username_already_used": DefinicionCodigo(
            "El correo o nombre de usuario ya está registrado.", {"validacion": 400}
        ),
        "username_invalid": DefinicionCodigo(
            "Alfanumérico, 5-25 caracteres.",
            {"validacion": 400},
            {"minLength": "integer", "maxLength": "integer"},
        ),
        "username_not_allowed": DefinicionCodigo(
            "El nombre de usuario no está permitido.", {"validacion": 400}
        ),
        "person_name_invalid": DefinicionCodigo(
            "Solo letras y espacios entre palabras, máximo 50 caracteres.",
            {"validacion": 400},
            {"maxLength": "integer"},
        ),
        "birth_date_in_future": DefinicionCodigo(
            "La fecha de nacimiento no puede ser futura.", {"validacion": 400}
        ),
        "minimum_age": DefinicionCodigo(
            "Debés tener al menos 13 años.", {"validacion": 400}, {"minAge": "integer"}
        ),
        "terms_not_accepted": DefinicionCodigo(
            "Tenés que aceptar los Términos y Condiciones.", {"validacion": 400}
        ),
        "avatar_invalid": DefinicionCodigo(
            "El avatar no está disponible.",
            {"validacion": 400},
            {"allowedIds": "integer[]"},
        ),
        "country_invalid": DefinicionCodigo(
            "El país falta o no es un código ISO 3166-1 alfa-2 válido.",
            {"validacion": 400},
        ),
        "local_password_unavailable": DefinicionCodigo(
            "La cuenta no tiene contraseña local.", {"validacion": 400}
        ),
        "current_password_incorrect": DefinicionCodigo(
            "La contraseña actual es incorrecta.", {"validacion": 400}
        ),
        "passwords_do_not_match": DefinicionCodigo(
            "Las contraseñas no coinciden.", {"validacion": 400}
        ),
        "password_too_short_or_long": DefinicionCodigo(
            "La contraseña debe tener entre 8 y 20 caracteres.",
            {"validacion": 400},
            {"minLength": "integer", "maxLength": "integer"},
        ),
        "password_no_upper": DefinicionCodigo(
            "La contraseña debe contener al menos una mayúscula.", {"validacion": 400}
        ),
        "password_no_lower": DefinicionCodigo(
            "La contraseña debe contener al menos una minúscula.", {"validacion": 400}
        ),
        "password_no_digit": DefinicionCodigo(
            "La contraseña debe contener al menos un dígito.", {"validacion": 400}
        ),
        "password_no_special": DefinicionCodigo(
            "La contraseña debe contener un carácter especial (@#$%&*!).",
            {"validacion": 400},
            {"specialCharacters": "string"},
        ),
        "password_too_short": DefinicionCodigo(
            "La contraseña es demasiado corta.",
            {"validacion": 400},
            {"minLength": "integer"},
        ),
        "password_too_common": DefinicionCodigo(
            "La contraseña tiene un valor demasiado común.", {"validacion": 400}
        ),
        "password_entirely_numeric": DefinicionCodigo(
            "La contraseña es completamente numérica.", {"validacion": 400}
        ),
        "password_too_similar": DefinicionCodigo(
            "La contraseña es demasiado similar a los datos personales.",
            {"validacion": 400},
            {"attribute": "string"},
        ),
        "google_authentication_failed": DefinicionCodigo(
            "No se pudo autenticar con Google.", {"validacion": 400}
        ),
        "list_name_missing_alphanumeric": DefinicionCodigo(
            "El nombre debe incluir al menos una letra o número.", {"validacion": 400}
        ),
        "list_name_invalid_characters": DefinicionCodigo(
            "El nombre solo puede contener letras, números y espacios.",
            {"validacion": 400},
        ),
        "review_update_empty": DefinicionCodigo(
            "Indicá al menos valor o texto para actualizar.",
            {"validacion": 400},
            {"fieldNames": "string[]"},
        ),
    }
)


def obtener_codigo(codigo):
    try:
        return CATALOGO[codigo]
    except KeyError as exc:
        raise ValueError(f"Código no registrado: {codigo}.") from exc
