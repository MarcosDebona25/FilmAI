"""Backend de email de Django sobre la API HTTP de Resend.

Motivación y diseño (docs/decisiones.md, 24/08/2026):
allauth y dj-rest-auth generan sus propios correos (confirmación de cuenta,
y a futuro password reset). Un `EMAIL_BACKEND` custom hace que TODO el email
transaccional salga por Resend sin tocar los adapters ni las vistas.

Restricción sin dominio propio verificado: Resend solo permite enviar desde
`onboarding@resend.dev` y únicamente al email dueño de la cuenta de la API
key (cualquier otro destinatario responde 403). Por eso existe
`RESEND_TEST_RECIPIENT`: si está configurado, TODOS los emails se redirigen a
esa dirección — así cualquier registro es probable end-to-end con una sola
bandeja. Al conseguir dominio propio, se borra esa variable del `.env` y el
backend envía a los destinatarios reales sin cambios de código.
"""

import logging

import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendBackend(BaseEmailBackend):
    """Envía `EmailMessage` vía `resend.Emails.send` (API REST de Resend).

    - Requiere `RESEND_API_KEY`; sin key no hace nada (log de error) para no
      romper flujos en entornos donde el email no es crítico.
    - Si `RESEND_TEST_RECIPIENT` está definido, redirige todos los envíos a
      esa dirección (modo testing sin dominio propio).
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "")
        test_recipient = getattr(settings, "RESEND_TEST_RECIPIENT", "")
        if not api_key:
            logger.error(
                "ResendBackend sin RESEND_API_KEY: %d email(s) NO enviados. "
                "Configurá RESEND_API_KEY en .env o volvé al console backend.",
                len(email_messages),
            )
            return 0

        resend.api_key = api_key
        enviados = 0
        for message in email_messages:
            try:
                self._send_one(message, test_recipient)
                enviados += 1
            except Exception:
                logger.exception(
                    "Error enviando email vía Resend (%s)", message.subject
                )
                if not self.fail_silently:
                    raise
        return enviados

    def _send_one(self, message, test_recipient: str) -> None:
        # `to`, `cc` y `bcc` van como campos separados: fusionarlos en `to`
        # expondría los BCC y cambiaría la semántica de los CC.
        to = list(message.to)
        cc = list(message.cc)
        bcc = list(message.bcc)

        if test_recipient:
            logger.info(
                "RESEND_TEST_RECIPIENT activo: redirigiendo email para %s hacia %s",
                ", ".join(to + cc + bcc),
                test_recipient,
            )
            to = [test_recipient]
            cc = []
            bcc = []
        elif not to and cc:
            # Resend exige un `to` no vacío: si solo hay CC, se promueve a `to`.
            to = cc
            cc = []
        elif not to and bcc:
            # Ídem para mensajes que solo llevan BCC.
            to = bcc
            bcc = []

        if not to:
            return

        cuerpo = message.body or ""
        params: dict = {
            "from": message.from_email,
            "to": to,
            "subject": message.subject or "",
        }
        if cc:
            params["cc"] = cc
        if bcc:
            params["bcc"] = bcc
        # El contenido de allauth llega en text/plain (alternatives trae HTML).
        html = self._extraer_html(message)
        if html:
            params["html"] = html
            params["text"] = cuerpo
        else:
            params["text"] = cuerpo

        respuesta = resend.Emails.send(params)
        logger.info(
            "Email enviado vía Resend: id=%s subject=%r",
            respuesta.get("id"),
            message.subject,
        )

    @staticmethod
    def _extraer_html(message) -> str | None:
        """Devuelve la parte HTML si el mensaje es multipart/alternative."""
        for contenido, tipo in getattr(message, "alternatives", []):
            if tipo == "text/html":
                return contenido
        return None
