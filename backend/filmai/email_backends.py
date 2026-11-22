"""Backends de email de Django: Resend, Brevo y Resend con Brevo de respaldo.

Motivación y diseño (docs/decisiones.md, 24/08/2026):
allauth y dj-rest-auth generan sus propios correos (confirmación de cuenta,
y a futuro password reset). Un `EMAIL_BACKEND` custom hace que TODO el email
transaccional salga por un proveedor sin tocar los adapters ni las vistas.

Restricción sin dominio propio verificado: Resend solo permite enviar desde
`onboarding@resend.dev` y únicamente al email dueño de la cuenta de la API
key (cualquier otro destinatario responde 403). Por eso existe
`RESEND_TEST_RECIPIENT`: si está configurado, TODOS los emails se redirigen a
esa dirección — así cualquier registro es probable end-to-end con una sola
bandeja. Al conseguir dominio propio, se borra esa variable del `.env` y el
backend envía a los destinatarios reales sin cambios de código.

Respaldo con Brevo (issue #181, docs/decisiones.md y openspec/specs/emails): cada
proveedor sabe enviar UN mensaje y, si falla, levanta `ErrorDeProveedor`
diciendo si el fallo es transitorio. Los tres backends son el mismo bucle
sobre una lista de proveedores: `[Resend]`, `[Brevo]` o `[Resend, Brevo]`.
`RespaldoBackend` prueba con Brevo solo si Resend levantó un error
transitorio; un mensaje que Resend aceptó nunca se reenvía.
"""

import html
import logging
from email.utils import parseaddr

import httpx
import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

# Tiempo máximo por fase (conexión, lectura) de cada llamada a un proveedor.
# El SDK de Resend trae 30 s por defecto (design.md, «Resend SDK, as installed»):
# con Resend lento más Brevo, un registro esperaría un minuto.
TIMEOUT_PROVEEDOR_SEGUNDOS = 10

URL_BREVO = "https://api.brevo.com/v3/smtp/email"

# Estados HTTP que indican que el PROVEEDOR no puede atender (clave caída,
# IP no autorizada, sin créditos, cuota agotada, caída): vale probar con otro.
# 400 y 422 (datos inválidos) y el resto de los 4xx no están: los mismos datos
# fallarían igual en el segundo proveedor.
_ESTADOS_TRANSITORIOS = frozenset({401, 402, 403, 429})


class ErrorDeProveedor(Exception):
    """Un proveedor no pudo enviar un mensaje.

    Guarda solo el nombre del proveedor, el estado HTTP y el tipo de error:
    el texto que devuelve el proveedor puede repetir destinatarios y no se
    copia, para que ningún log o traza lleve direcciones.
    """

    def __init__(self, proveedor, *, transitorio, estado=None, codigo=None):
        self.proveedor = proveedor
        self.transitorio = transitorio
        self.estado = estado
        self.codigo = codigo
        super().__init__(
            f"{proveedor} no pudo enviar (estado={estado} codigo={codigo})"
        )

    def __reduce__(self):
        # Celery serializa con pickle la excepción de una tarea fallida; sin esto
        # `pickle` la rearma con `args` (solo el texto) y el log muestra un
        # `UnpickleableExceptionWrapper` en lugar del error.
        return (
            _rearmar_error_de_proveedor,
            (self.proveedor, self.transitorio, self.estado, self.codigo),
        )


def _rearmar_error_de_proveedor(proveedor, transitorio, estado, codigo):
    return ErrorDeProveedor(
        proveedor, transitorio=transitorio, estado=estado, codigo=codigo
    )


class EnvioFallido(Exception):
    """Ningún proveedor activo pudo enviar el mensaje (todos fallaron)."""

    def __init__(self, errores):
        self.errores = list(errores)
        detalle = ", ".join(f"{e.proveedor}: {e.estado}" for e in self.errores)
        super().__init__(f"Ningún proveedor pudo enviar el email ({detalle})")

    def __reduce__(self):
        # Ver `ErrorDeProveedor.__reduce__`.
        return (EnvioFallido, (self.errores,))


def _es_transitorio(estado: int | None) -> bool:
    """Sin estado (red, timeout) o con estado de proveedor caído: transitorio."""
    return estado is None or estado in _ESTADOS_TRANSITORIOS or estado >= 500


def _extraer_html(message) -> str | None:
    """Devuelve la parte HTML si el mensaje es multipart/alternative."""
    for contenido, tipo in getattr(message, "alternatives", []):
        if tipo == "text/html":
            return contenido
    return None


def _destinatarios(message, test_recipient: str, variable: str):
    """Devuelve `(to, cc, bcc)` listos para el proveedor.

    `to`, `cc` y `bcc` van como campos separados: fusionarlos en `to`
    expondría los BCC y cambiaría la semántica de los CC. Con destinatario de
    prueba todo se redirige a él; sin `to`, el primer campo disponible se
    promueve (los dos proveedores exigen un `to` no vacío).
    """
    to = list(message.to)
    cc = list(message.cc)
    bcc = list(message.bcc)

    if test_recipient:
        # La cantidad y no las direcciones: los logs no llevan correos.
        logger.info(
            "%s activo: %d destinatario(s) redirigidos",
            variable,
            len(to + cc + bcc),
        )
        return [test_recipient], [], []
    if not to and cc:
        return cc, [], bcc
    if not to and bcc:
        return bcc, cc, []
    return to, cc, bcc


class ProveedorResend:
    """Envía un mensaje con `resend.Emails.send` (API REST de Resend)."""

    nombre = "Resend"
    variable_clave = "RESEND_API_KEY"

    def __init__(self, **_):
        pass

    def configurado(self) -> bool:
        return bool(getattr(settings, "RESEND_API_KEY", ""))

    def enviar(self, message) -> str | None:
        """Envía el mensaje y devuelve el id de Resend (None si no hay `to`)."""
        to, cc, bcc = _destinatarios(
            message,
            getattr(settings, "RESEND_TEST_RECIPIENT", ""),
            "RESEND_TEST_RECIPIENT",
        )
        if not to:
            return None

        params: dict = {
            "from": message.from_email,
            "to": to,
            "subject": message.subject or "",
            # El contenido de allauth llega en text/plain (alternatives trae HTML).
            "text": message.body or "",
        }
        if cc:
            params["cc"] = cc
        if bcc:
            params["bcc"] = bcc
        html_content = _extraer_html(message)
        if html_content:
            params["html"] = html_content

        resend.api_key = settings.RESEND_API_KEY
        resend.default_http_client = resend.RequestsClient(
            timeout=TIMEOUT_PROVEEDOR_SEGUNDOS
        )
        try:
            respuesta = resend.Emails.send(params)
        except resend.exceptions.ResendError as exc:
            raise self._traducir(exc) from None
        return respuesta.get("id")

    def _traducir(self, exc) -> ErrorDeProveedor:
        """Convierte un error del SDK en `ErrorDeProveedor`.

        Manda el estado HTTP (`exc.code`), no la clase: el SDK levanta
        `ValidationError` también para un 401 o un 403 con cuerpo
        `validation_error`. Los fallos de transporte (conexión, DNS, TLS,
        timeout) llegan como `ResendError` con código 500 y tipo
        `HttpClientError`, así que caen solos en la categoría de los 5xx.
        """
        try:
            estado = int(exc.code)
        except (TypeError, ValueError):
            estado = None
        codigo = exc.error_type or None
        transitorio = _es_transitorio(estado)
        # Resend responde a una clave inválida con 400 (Bad Request) y
        # `validation_error` («API key is invalid»), no con 401 ni 403 como dice
        # su documentación (comprobado el 22/11/2026). Es una clave caída, no un
        # dato malo: se reconoce por el mensaje y pasa a Brevo. Del mensaje se
        # guarda solo el código, nunca el texto.
        if estado == 400 and "api key" in (getattr(exc, "message", "") or "").lower():
            transitorio = True
            codigo = "invalid_api_key"
        return ErrorDeProveedor(
            self.nombre, transitorio=transitorio, estado=estado, codigo=codigo
        )


class ProveedorBrevo:
    """Envía un mensaje con la API transaccional de Brevo (`/v3/smtp/email`)."""

    nombre = "Brevo"
    variable_clave = "BREVO_API_KEY"

    def __init__(self, transport=None, **_):
        # `transport` permite inyectar `httpx.MockTransport` en los tests.
        self._transport = transport

    def configurado(self) -> bool:
        return bool(getattr(settings, "BREVO_API_KEY", ""))

    def enviar(self, message) -> str | None:
        """Envía el mensaje y devuelve el `messageId` de Brevo (None si no hay `to`)."""
        to, cc, bcc = _destinatarios(
            message,
            getattr(settings, "BREVO_TEST_RECIPIENT", ""),
            "BREVO_TEST_RECIPIENT",
        )
        if not to:
            return None

        cuerpo = message.body or ""
        payload: dict = {
            "sender": self._remitente(message),
            "to": [{"email": direccion} for direccion in to],
            "subject": message.subject or "",
            # Sin plantilla Brevo exige `htmlContent`: un mensaje de solo texto
            # va escapado dentro de un <pre>.
            "htmlContent": _extraer_html(message)
            or f"<pre>{html.escape(cuerpo)}</pre>",
            "textContent": cuerpo,
        }
        if cc:
            payload["cc"] = [{"email": direccion} for direccion in cc]
        if bcc:
            payload["bcc"] = [{"email": direccion} for direccion in bcc]

        headers = {"api-key": settings.BREVO_API_KEY, "accept": "application/json"}
        try:
            with httpx.Client(
                timeout=TIMEOUT_PROVEEDOR_SEGUNDOS, transport=self._transport
            ) as cliente:
                respuesta = cliente.post(URL_BREVO, json=payload, headers=headers)
        except httpx.TransportError:
            # Conexión, DNS, TLS y timeouts (D-2: el de lectura también cae).
            raise ErrorDeProveedor(self.nombre, transitorio=True) from None

        if respuesta.is_success:
            try:
                return str(respuesta.json().get("messageId", ""))
            except (ValueError, AttributeError):
                return ""

        try:
            codigo = respuesta.json().get("code")
        except (ValueError, AttributeError):
            codigo = None
        raise ErrorDeProveedor(
            self.nombre,
            transitorio=_es_transitorio(respuesta.status_code),
            estado=respuesta.status_code,
            codigo=codigo if isinstance(codigo, str) else None,
        ) from None

    @staticmethod
    def _remitente(message) -> dict:
        """`BREVO_FROM_EMAIL` (o el remitente del mensaje) en `{name, email}`."""
        crudo = getattr(settings, "BREVO_FROM_EMAIL", "") or message.from_email
        nombre, direccion = parseaddr(crudo)
        remitente = {"email": direccion}
        if nombre:
            remitente["name"] = nombre
        return remitente


class _BackendPorProveedores(BaseEmailBackend):
    """Bucle común: cada mensaje se prueba con los proveedores en orden.

    - Los proveedores sin clave se saltean; sin ninguno configurado se loguea
      un error y se devuelve 0 (no romper flujos donde el email no es crítico).
    - Un 2xx es definitivo: el mensaje no se reenvía.
    - Un error transitorio pasa al siguiente proveedor (WARNING con el motivo);
      uno no transitorio (datos inválidos) en el primer proveedor se levanta de
      inmediato. En el respaldo, cualquier error cuenta como «falló también».
    - Si fallan todos se levanta `EnvioFallido`, o se devuelve 0 con
      `fail_silently`.
    """

    clases_de_proveedores: tuple = ()

    def __init__(self, fail_silently=False, transport=None, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.proveedores = [
            clase(transport=transport) for clase in self.clases_de_proveedores
        ]

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        activos = [p for p in self.proveedores if p.configurado()]
        if not activos:
            logger.error(
                "%s sin clave (%s): %d email(s) NO enviados. "
                "Configurala en .env o volvé al console backend.",
                type(self).__name__,
                " / ".join(p.variable_clave for p in self.proveedores),
                len(email_messages),
            )
            return 0

        enviados = 0
        for message in email_messages:
            try:
                self._enviar_con_respaldo(message, activos)
                enviados += 1
            except (ErrorDeProveedor, EnvioFallido) as exc:
                # El texto de estas excepciones no lleva direcciones ni claves.
                logger.error("%s", exc)
                if not self.fail_silently:
                    raise
            except Exception:
                logger.exception("Error enviando email (%s)", message.subject)
                if not self.fail_silently:
                    raise
        return enviados

    def _enviar_con_respaldo(self, message, activos) -> None:
        errores: list[ErrorDeProveedor] = []
        for i, proveedor in enumerate(activos):
            try:
                id_mensaje = proveedor.enviar(message)
            except ErrorDeProveedor as error:
                # Un dato inválido en el primer proveedor no se reintenta: fallaría
                # igual en el otro. Pero si ya hubo un fallo transitorio, el error
                # del respaldo (aunque sea un 400 (Bad Request), p. ej. remitente
                # no verificado en Brevo) significa que no hay con quién enviar.
                if not error.transitorio and not errores:
                    raise
                errores.append(error)
                if i + 1 < len(activos):
                    logger.warning(
                        "%s no pudo enviar (estado=%s codigo=%s); se reintenta con %s",
                        proveedor.nombre,
                        error.estado,
                        error.codigo,
                        activos[i + 1].nombre,
                    )
                continue
            logger.info(
                "Email enviado vía %s: id=%s subject=%r",
                proveedor.nombre,
                id_mensaje,
                message.subject,
            )
            return
        raise EnvioFallido(errores) from errores[-1]


class ResendBackend(_BackendPorProveedores):
    """Envía `EmailMessage` vía `resend.Emails.send` (API REST de Resend).

    - Requiere `RESEND_API_KEY`; sin key no hace nada (log de error) para no
      romper flujos en entornos donde el email no es crítico.
    - Si `RESEND_TEST_RECIPIENT` está definido, redirige todos los envíos a
      esa dirección (modo testing sin dominio propio).
    """

    clases_de_proveedores = (ProveedorResend,)


class BrevoBackend(_BackendPorProveedores):
    """Envía solo por Brevo (`BREVO_API_KEY`, `BREVO_FROM_EMAIL`)."""

    clases_de_proveedores = (ProveedorBrevo,)


class RespaldoBackend(_BackendPorProveedores):
    """Resend primero; Brevo para el mensaje que Resend no pudo tomar."""

    clases_de_proveedores = (ProveedorResend, ProveedorBrevo)
