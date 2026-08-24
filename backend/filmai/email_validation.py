"""Validación de la configuración de email al arranque.

En producción la ausencia de ``RESEND_API_KEY`` (con ``ResendBackend`` activo)
o la presencia de ``RESEND_TEST_RECIPIENT`` son errores de configuración: deben
romper el arranque en vez de degradar silenciosamente el envío de emails o de
redirigir todos los destinatarios a una única dirección.
"""

from django.core.exceptions import ImproperlyConfigured

RESEND_BACKEND = "filmai.email_backends.ResendBackend"


def validar_configuracion_email(
    *,
    debug: bool,
    email_backend: str,
    resend_api_key: str,
    resend_test_recipient: str,
) -> None:
    """Levanta ``ImproperlyConfigured`` si la config de email es inválida.

    Solo aplica en producción (``debug=False``) con el backend de Resend
    seleccionado. En desarrollo sigue permitiéndose redirigir a un destinatario
    de prueba para testear end-to-end sin dominio propio verificado.
    """
    if debug or email_backend != RESEND_BACKEND:
        return

    if not resend_api_key:
        raise ImproperlyConfigured(
            "RESEND_API_KEY es obligatorio en producción con ResendBackend."
        )
    if resend_test_recipient:
        raise ImproperlyConfigured(
            "RESEND_TEST_RECIPIENT no está permitido en producción: "
            "redirigiría todos los emails a una única dirección."
        )
