"""Validación de la configuración de email al arranque.

En producción la ausencia de la clave de un proveedor activo o la presencia de
un destinatario de prueba (``RESEND_TEST_RECIPIENT``, ``BREVO_TEST_RECIPIENT``)
son errores de configuración: deben romper el arranque en vez de degradar
silenciosamente el envío de emails o de redirigir todos los destinatarios a una
única dirección.
"""

from email.utils import parseaddr

from django.core.exceptions import ImproperlyConfigured

RESEND_BACKEND = "filmai.email_backends.ResendBackend"
BREVO_BACKEND = "filmai.email_backends.BrevoBackend"
RESPALDO_BACKEND = "filmai.email_backends.RespaldoBackend"


def validar_configuracion_email(
    *,
    debug: bool,
    email_backend: str,
    resend_api_key: str,
    resend_test_recipient: str,
    brevo_api_key: str = "",
    brevo_from_email: str = "",
    brevo_test_recipient: str = "",
    default_from_email: str = "",
) -> None:
    """Levanta ``ImproperlyConfigured`` si la config de email es inválida.

    Solo aplica en producción (``debug=False``) con un backend de Resend, de
    Brevo o de respaldo seleccionado. En desarrollo sigue permitiéndose
    redirigir a un destinatario de prueba para testear end-to-end sin dominio
    propio verificado, y el respaldo funciona con una sola clave.
    """
    if debug or email_backend not in (RESEND_BACKEND, BREVO_BACKEND, RESPALDO_BACKEND):
        return

    usa_resend = email_backend in (RESEND_BACKEND, RESPALDO_BACKEND)
    usa_brevo = email_backend in (BREVO_BACKEND, RESPALDO_BACKEND)
    nombre = email_backend.rsplit(".", 1)[-1]

    if usa_resend:
        if not resend_api_key:
            raise ImproperlyConfigured(
                f"RESEND_API_KEY es obligatorio en producción con {nombre}."
            )
        if resend_test_recipient:
            raise ImproperlyConfigured(
                "RESEND_TEST_RECIPIENT no está permitido en producción: "
                "redirigiría todos los emails a una única dirección."
            )
    if usa_brevo:
        if not brevo_api_key:
            raise ImproperlyConfigured(
                f"BREVO_API_KEY es obligatorio en producción con {nombre}."
            )
        if brevo_test_recipient:
            raise ImproperlyConfigured(
                "BREVO_TEST_RECIPIENT no está permitido en producción: "
                "redirigiría todos los emails a una única dirección."
            )
        # Brevo envía como `BREVO_FROM_EMAIL` o, sin ella, como el remitente del
        # mensaje (`DEFAULT_FROM_EMAIL`). Si esa dirección falta, está mal
        # escrita o es la de pruebas de Resend, Brevo rechaza cada correo con
        # 400 (Bad Request): mejor que el arranque lo diga.
        remitente = parseaddr(brevo_from_email or default_from_email)[1].lower()
        if "@" not in remitente or remitente.endswith("@resend.dev"):
            raise ImproperlyConfigured(
                f"Con {nombre}, Brevo necesita un remitente propio verificado en "
                "Brevo: definí BREVO_FROM_EMAIL como «Nombre <direccion@dominio>». "
                "No sirve una dirección @resend.dev."
            )
