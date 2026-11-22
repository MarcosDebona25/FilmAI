"""Tests de Brevo como respaldo de Resend (issue #181, PR 1 de 2).

Qué se prueba y con qué técnica:

- `ProveedorBrevo` se prueba con `httpx.MockTransport`: un transporte falso
  que reemplaza a la red. El cliente de httpx arma la petición real (URL,
  cabeceras, JSON) y, en vez de enviarla, se la entrega a una función nuestra
  que la guarda y devuelve la respuesta que queramos. Así se verifica lo que
  *saldría* por la red sin tocar la red ni la API de Brevo.
- `ProveedorResend` se prueba parchando `resend.Emails.send` con excepciones
  construidas con las clases del propio SDK (`RateLimitError`, etc.), no con
  excepciones inventadas: si una versión futura del SDK cambia una clase, el
  test se rompe en vez de seguir verde contra un error que ya no existe.
- `assertLogs` captura los mensajes que escribe un logger durante el bloque
  `with`; falla si no se escribe ninguno. Se usa para verificar qué proveedor
  envió y que ningún mensaje de log contenga direcciones de correo.
"""

import json
from io import StringIO
from unittest.mock import patch

import httpx
import resend
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from resend.exceptions import (
    ApplicationError,
    InvalidApiKeyError,
    MissingApiKeyError,
    MissingRequiredFieldsError,
    RateLimitError,
    ResendError,
    ValidationError,
)

from filmai.email_backends import (
    BrevoBackend,
    EnvioFallido,
    ErrorDeProveedor,
    ProveedorBrevo,
    ProveedorResend,
    RespaldoBackend,
)

LOGGER = "filmai.email_backends"
URL_BREVO = "https://api.brevo.com/v3/smtp/email"

PARA = "persona@destino-ejemplo.com"
COPIA = "copia@destino-ejemplo.com"
OCULTA = "oculta@destino-ejemplo.com"
PRUEBA = "bandeja@prueba-ejemplo.com"
REMITENTE_BREVO = "cuenta@filmai-ejemplo.com"
CLAVE_BREVO = "xkeysib-clave-secreta-de-prueba"
CLAVE_RESEND = "re_clave_secreta_de_prueba"


def _mensaje(**cambios):
    datos = {
        "subject": "Asunto de prueba",
        "body": "Cuerpo de prueba",
        "from_email": "FilmAI <onboarding@resend.dev>",
        "to": [PARA],
    }
    datos.update(cambios)
    return EmailMessage(**datos)


def _mensaje_html():
    mensaje = EmailMultiAlternatives(
        "Asunto HTML",
        "Texto plano",
        "FilmAI <onboarding@resend.dev>",
        [PARA],
    )
    mensaje.attach_alternative("<p>Hola</p>", "text/html")
    return mensaje


class _Brevo:
    """Transporte falso de Brevo que recuerda cada petición recibida."""

    def __init__(self, estado=201, cuerpo=None, error=None):
        self.estado = estado
        self.cuerpo = cuerpo if cuerpo is not None else {"messageId": "<id-brevo-1>"}
        self.error = error
        self.peticiones: list[httpx.Request] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.peticiones.append(peticion)
        if self.error is not None:
            raise self.error
        return httpx.Response(self.estado, json=self.cuerpo)

    @property
    def transporte(self):
        return httpx.MockTransport(self)

    def json(self, i=0):
        return json.loads(self.peticiones[i].content)


def _error_resend(clase, codigo, tipo, mensaje="detalle"):
    if clase is ResendError:
        # La clase base pide además `suggested_action`; las hijas la fijan solas.
        return clase(message=mensaje, error_type=tipo, code=codigo, suggested_action="")
    return clase(message=mensaje, error_type=tipo, code=codigo)


@override_settings(
    BREVO_API_KEY=CLAVE_BREVO,
    BREVO_FROM_EMAIL=f"FilmAI <{REMITENTE_BREVO}>",
    BREVO_TEST_RECIPIENT="",
)
class ProveedorBrevoTests(SimpleTestCase):
    def _enviar(self, mensaje, brevo=None):
        brevo = brevo or _Brevo()
        id_ = ProveedorBrevo(transport=brevo.transporte).enviar(mensaje)
        return id_, brevo

    def test_envia_por_post_a_la_url_con_la_clave_en_la_cabecera(self):
        # Verifica la "dirección" de la llamada: método, URL y autenticación.
        _, brevo = self._enviar(_mensaje())

        peticion = brevo.peticiones[0]
        self.assertEqual(peticion.method, "POST")
        self.assertEqual(str(peticion.url), URL_BREVO)
        self.assertEqual(peticion.headers["api-key"], CLAVE_BREVO)
        self.assertEqual(peticion.headers["accept"], "application/json")

    def test_devuelve_el_message_id(self):
        id_, _ = self._enviar(_mensaje())

        self.assertEqual(id_, "<id-brevo-1>")

    def test_remitente_sale_de_brevo_from_email_separando_nombre_y_direccion(self):
        # Brevo no acepta "Nombre <mail>" en un solo campo: pide nombre y mail.
        _, brevo = self._enviar(_mensaje())

        self.assertEqual(
            brevo.json()["sender"], {"name": "FilmAI", "email": REMITENTE_BREVO}
        )

    @override_settings(BREVO_FROM_EMAIL="")
    def test_sin_brevo_from_email_usa_el_remitente_del_mensaje(self):
        _, brevo = self._enviar(_mensaje(from_email="FilmAI <hola@filmai-ejemplo.com>"))

        self.assertEqual(
            brevo.json()["sender"],
            {"name": "FilmAI", "email": "hola@filmai-ejemplo.com"},
        )

    @override_settings(BREVO_FROM_EMAIL="solo@filmai-ejemplo.com")
    def test_remitente_sin_nombre_omite_el_campo_name(self):
        _, brevo = self._enviar(_mensaje())

        self.assertEqual(brevo.json()["sender"], {"email": "solo@filmai-ejemplo.com"})

    def test_to_cc_y_bcc_viajan_en_campos_separados(self):
        # Fusionarlos en `to` mostraría los BCC y cambiaría el sentido de los CC.
        _, brevo = self._enviar(_mensaje(cc=[COPIA], bcc=[OCULTA]))

        cuerpo = brevo.json()
        self.assertEqual(cuerpo["to"], [{"email": PARA}])
        self.assertEqual(cuerpo["cc"], [{"email": COPIA}])
        self.assertEqual(cuerpo["bcc"], [{"email": OCULTA}])

    def test_listas_vacias_se_omiten(self):
        _, brevo = self._enviar(_mensaje())

        cuerpo = brevo.json()
        self.assertNotIn("cc", cuerpo)
        self.assertNotIn("bcc", cuerpo)

    def test_asunto_html_y_texto(self):
        _, brevo = self._enviar(_mensaje_html())

        cuerpo = brevo.json()
        self.assertEqual(cuerpo["subject"], "Asunto HTML")
        self.assertEqual(cuerpo["htmlContent"], "<p>Hola</p>")
        self.assertEqual(cuerpo["textContent"], "Texto plano")

    def test_mensaje_solo_texto_se_envuelve_en_pre_escapado(self):
        # Brevo exige `htmlContent` sin plantilla: un mensaje de solo texto
        # (send_test_email, correos del admin) se rechazaría sin esta envoltura.
        _, brevo = self._enviar(_mensaje(body="a < b & c"))

        cuerpo = brevo.json()
        self.assertEqual(cuerpo["htmlContent"], "<pre>a &lt; b &amp; c</pre>")
        self.assertEqual(cuerpo["textContent"], "a < b & c")

    @override_settings(BREVO_TEST_RECIPIENT=PRUEBA)
    def test_destinatario_de_prueba_redirige_todo_y_el_log_solo_cuenta(self):
        with self.assertLogs(LOGGER, level="INFO") as logs:
            _, brevo = self._enviar(_mensaje(cc=[COPIA], bcc=[OCULTA]))

        cuerpo = brevo.json()
        self.assertEqual(cuerpo["to"], [{"email": PRUEBA}])
        self.assertNotIn("cc", cuerpo)
        self.assertNotIn("bcc", cuerpo)
        salida = "\n".join(logs.output)
        self.assertIn("BREVO_TEST_RECIPIENT activo: 3 destinatario(s)", salida)
        for direccion in (PARA, COPIA, OCULTA, PRUEBA):
            self.assertNotIn(direccion, salida)

    def test_solo_cc_se_promueve_a_to(self):
        _, brevo = self._enviar(_mensaje(to=[], cc=[COPIA]))

        cuerpo = brevo.json()
        self.assertEqual(cuerpo["to"], [{"email": COPIA}])
        self.assertNotIn("cc", cuerpo)

    def test_solo_bcc_se_promueve_a_to(self):
        _, brevo = self._enviar(_mensaje(to=[], bcc=[OCULTA]))

        cuerpo = brevo.json()
        self.assertEqual(cuerpo["to"], [{"email": OCULTA}])
        self.assertNotIn("bcc", cuerpo)

    def test_sin_destinatarios_no_llama_a_la_api(self):
        id_, brevo = self._enviar(_mensaje(to=[]))

        self.assertIsNone(id_)
        self.assertEqual(brevo.peticiones, [])

    def test_configurado_depende_de_la_clave(self):
        self.assertTrue(ProveedorBrevo().configurado())
        with override_settings(BREVO_API_KEY=""):
            self.assertFalse(ProveedorBrevo().configurado())


@override_settings(BREVO_API_KEY=CLAVE_BREVO, BREVO_FROM_EMAIL=REMITENTE_BREVO)
class ErroresDeBrevoTests(SimpleTestCase):
    """Qué errores de Brevo justifican probar con otro proveedor ("transitorios")."""

    def _error(self, brevo):
        with self.assertRaises(ErrorDeProveedor) as ctx:
            ProveedorBrevo(transport=brevo.transporte).enviar(_mensaje())
        return ctx.exception

    def test_400_no_es_transitorio_porque_los_mismos_datos_fallarian_otra_vez(self):
        error = self._error(_Brevo(400, {"code": "invalid_parameter", "message": "x"}))

        self.assertFalse(error.transitorio)
        self.assertEqual(error.estado, 400)
        self.assertEqual(error.codigo, "invalid_parameter")

    def test_otros_4xx_tampoco_son_transitorios(self):
        for estado in (404, 405, 422):
            with self.subTest(estado=estado):
                self.assertFalse(self._error(_Brevo(estado, {})).transitorio)

    def test_401_402_403_429_y_5xx_son_transitorios(self):
        for estado in (401, 402, 403, 429, 500, 502, 503):
            with self.subTest(estado=estado):
                error = self._error(_Brevo(estado, {"code": "algo", "message": "m"}))
                self.assertTrue(error.transitorio)
                self.assertEqual(error.estado, estado)
                self.assertEqual(error.codigo, "algo")
                self.assertEqual(error.proveedor, "Brevo")

    def test_errores_de_red_y_timeouts_son_transitorios(self):
        peticion = httpx.Request("POST", URL_BREVO)
        for excepcion in (
            httpx.ConnectTimeout("t", request=peticion),
            httpx.ReadTimeout("t", request=peticion),
            httpx.ConnectError("c", request=peticion),
        ):
            with self.subTest(tipo=type(excepcion).__name__):
                error = self._error(_Brevo(error=excepcion))
                self.assertTrue(error.transitorio)
                self.assertIsNone(error.estado)

    def test_cuerpo_de_error_que_no_es_json_no_rompe_la_clasificacion(self):
        def handler(_peticion):
            return httpx.Response(502, text="<html>Bad Gateway</html>")

        with self.assertRaises(ErrorDeProveedor) as ctx:
            ProveedorBrevo(transport=httpx.MockTransport(handler)).enviar(_mensaje())

        self.assertTrue(ctx.exception.transitorio)
        self.assertEqual(ctx.exception.estado, 502)
        self.assertIsNone(ctx.exception.codigo)

    def test_el_error_no_arrastra_el_mensaje_de_brevo_ni_direcciones_ni_claves(self):
        # El mensaje de Brevo puede repetir destinatarios: no debe llegar a logs.
        brevo = _Brevo(400, {"code": "invalid_parameter", "message": f"{PARA} mal"})

        texto = str(self._error(brevo))

        self.assertNotIn(PARA, texto)
        self.assertNotIn(CLAVE_BREVO, texto)


@override_settings(RESEND_API_KEY=CLAVE_RESEND, RESEND_TEST_RECIPIENT="")
class ErroresDeResendTests(SimpleTestCase):
    """Se usan las clases del SDK instalado (resend 2.53.2), ver design.md."""

    def _error(self, excepcion):
        with patch("resend.Emails.send", side_effect=excepcion):
            with self.assertRaises(ErrorDeProveedor) as ctx:
                ProveedorResend().enviar(_mensaje())
        return ctx.exception

    def test_limite_de_cuota_en_sus_tres_tipos_es_transitorio(self):
        for tipo in (
            "rate_limit_exceeded",
            "daily_quota_exceeded",
            "monthly_quota_exceeded",
        ):
            with self.subTest(tipo=tipo):
                error = self._error(_error_resend(RateLimitError, 429, tipo))
                self.assertTrue(error.transitorio)
                self.assertEqual(error.estado, 429)
                self.assertEqual(error.codigo, tipo)
                self.assertEqual(error.proveedor, "Resend")

    def test_error_de_aplicacion_5xx_es_transitorio(self):
        error = self._error(_error_resend(ApplicationError, 500, "application_error"))

        self.assertTrue(error.transitorio)
        self.assertEqual(error.estado, 500)

    def test_clave_faltante_o_invalida_es_transitoria(self):
        # D-1: una clave caída es un problema del proveedor, no de los datos.
        casos = (
            _error_resend(MissingApiKeyError, 401, "missing_api_key"),
            _error_resend(InvalidApiKeyError, 403, "invalid_api_key"),
        )
        for excepcion in casos:
            with self.subTest(clase=type(excepcion).__name__):
                self.assertTrue(self._error(excepcion).transitorio)

    def test_validation_error_con_403_es_transitorio_porque_manda_el_estado(self):
        # Sin dominio propio, mandar a alguien que no es el dueño de la cuenta
        # responde 403 con tipo `validation_error`: el SDK lo levanta como
        # `ValidationError`, pero es un bloqueo del proveedor, no un dato malo.
        error = self._error(_error_resend(ValidationError, 403, "validation_error"))

        self.assertTrue(error.transitorio)
        self.assertEqual(error.estado, 403)

    def test_error_de_transporte_del_sdk_es_transitorio(self):
        # Conexión, DNS, TLS y timeouts llegan como ResendError 500
        # "HttpClientError" (el SDK atrapa las excepciones de `requests`).
        error = self._error(_error_resend(ResendError, 500, "HttpClientError"))

        self.assertTrue(error.transitorio)
        self.assertEqual(error.codigo, "HttpClientError")

    def test_datos_invalidos_no_son_transitorios(self):
        casos = (
            _error_resend(ValidationError, 400, "validation_error"),
            _error_resend(ValidationError, 422, "validation_error"),
            _error_resend(MissingRequiredFieldsError, 422, "missing_required_field"),
        )
        for excepcion in casos:
            with self.subTest(clase=type(excepcion).__name__, codigo=excepcion.code):
                self.assertFalse(self._error(excepcion).transitorio)

    def test_el_codigo_puede_llegar_como_texto(self):
        error = self._error(_error_resend(RateLimitError, "429", "rate_limit_exceeded"))

        self.assertTrue(error.transitorio)
        self.assertEqual(error.estado, 429)

    def test_una_excepcion_desconocida_no_se_envuelve(self):
        # Un bug nuestro no debe disfrazarse de falla del proveedor.
        with patch("resend.Emails.send", side_effect=RuntimeError("bug")):
            with self.assertRaises(RuntimeError):
                ProveedorResend().enviar(_mensaje())

    def test_el_error_no_arrastra_el_mensaje_del_sdk(self):
        error = self._error(
            _error_resend(
                ValidationError,
                403,
                "validation_error",
                f"solo a {PRUEBA} ({CLAVE_RESEND})",
            )
        )

        texto = str(error)
        self.assertNotIn(PRUEBA, texto)
        self.assertNotIn(CLAVE_RESEND, texto)
        self.assertIsNone(error.__cause__)

    @patch("resend.Emails.send")
    def test_el_sdk_se_configura_con_timeout_de_10_segundos(self, mock_send):
        mock_send.return_value = {"id": "abc"}

        ProveedorResend().enviar(_mensaje())

        self.assertIsInstance(resend.default_http_client, resend.RequestsClient)
        self.assertEqual(resend.default_http_client._timeout, 10)
        self.assertEqual(resend.api_key, CLAVE_RESEND)


@override_settings(
    RESEND_API_KEY=CLAVE_RESEND,
    RESEND_TEST_RECIPIENT="",
    BREVO_API_KEY=CLAVE_BREVO,
    BREVO_FROM_EMAIL=REMITENTE_BREVO,
    BREVO_TEST_RECIPIENT="",
)
class RespaldoBackendTests(SimpleTestCase):
    """Resend primero; Brevo solo si Resend levantó un error transitorio."""

    def _backend(self, brevo, fail_silently=False):
        return RespaldoBackend(fail_silently=fail_silently, transport=brevo.transporte)

    def _sin_direcciones_ni_claves(self, logs):
        salida = "\n".join(logs.output)
        for secreto in (PARA, COPIA, OCULTA, PRUEBA, CLAVE_BREVO, CLAVE_RESEND):
            self.assertNotIn(secreto, salida)

    @patch("resend.Emails.send")
    def test_si_resend_acepta_brevo_no_se_llama(self, mock_send):
        mock_send.return_value = {"id": "res-1"}
        brevo = _Brevo()

        with self.assertLogs(LOGGER, level="INFO") as logs:
            enviados = self._backend(brevo).send_messages([_mensaje()])

        self.assertEqual(enviados, 1)
        self.assertEqual(brevo.peticiones, [])
        salida = "\n".join(logs.output)
        self.assertIn("vía Resend", salida)
        self.assertIn("res-1", salida)
        self.assertNotIn("vía Brevo", salida)

    def test_si_resend_falla_de_forma_transitoria_envia_brevo(self):
        casos = {
            "429": _error_resend(RateLimitError, 429, "daily_quota_exceeded"),
            "500": _error_resend(ApplicationError, 500, "application_error"),
            "red": _error_resend(ResendError, 500, "HttpClientError"),
            "401": _error_resend(MissingApiKeyError, 401, "missing_api_key"),
            "403": _error_resend(InvalidApiKeyError, 403, "invalid_api_key"),
        }
        for nombre, excepcion in casos.items():
            with (
                self.subTest(caso=nombre),
                patch("resend.Emails.send", side_effect=excepcion),
            ):
                brevo = _Brevo(cuerpo={"messageId": "<bre-9>"})
                with self.assertLogs(LOGGER, level="INFO") as logs:
                    enviados = self._backend(brevo).send_messages(
                        [_mensaje(cc=[COPIA])]
                    )

                self.assertEqual(enviados, 1)
                self.assertEqual(len(brevo.peticiones), 1)
                # Es el mismo mensaje: asunto, texto y destinatarios.
                cuerpo = brevo.json()
                self.assertEqual(cuerpo["subject"], "Asunto de prueba")
                self.assertEqual(cuerpo["to"], [{"email": PARA}])
                self.assertEqual(cuerpo["cc"], [{"email": COPIA}])
                salida = "\n".join(logs.output)
                self.assertIn("WARNING", salida)
                self.assertIn(f"Resend no pudo enviar (estado={excepcion.code}", salida)
                self.assertIn("se reintenta con Brevo", salida)
                self.assertIn("vía Brevo", salida)
                self.assertIn("<bre-9>", salida)
                self._sin_direcciones_ni_claves(logs)

    @patch("resend.Emails.send")
    def test_el_warning_nombra_el_estado_y_el_tipo_de_error(self, mock_send):
        mock_send.side_effect = _error_resend(
            RateLimitError, 429, "daily_quota_exceeded"
        )

        with self.assertLogs(LOGGER, level="WARNING") as logs:
            self._backend(_Brevo()).send_messages([_mensaje()])

        self.assertIn("estado=429 codigo=daily_quota_exceeded", logs.output[0])

    def test_datos_invalidos_en_resend_no_prueban_con_brevo(self):
        for excepcion in (
            _error_resend(ValidationError, 422, "validation_error"),
            _error_resend(MissingRequiredFieldsError, 422, "missing_required_field"),
        ):
            with (
                self.subTest(clase=type(excepcion).__name__),
                patch("resend.Emails.send", side_effect=excepcion),
            ):
                brevo = _Brevo()
                with self.assertRaises(ErrorDeProveedor) as ctx:
                    self._backend(brevo).send_messages([_mensaje()])
                self.assertFalse(ctx.exception.transitorio)
                self.assertEqual(brevo.peticiones, [])

    @patch(
        "resend.Emails.send",
        side_effect=_error_resend(ValidationError, 422, "validation_error"),
    )
    def test_datos_invalidos_con_fail_silently_devuelven_cero(self, _mock_send):
        brevo = _Brevo()

        with self.assertLogs(LOGGER, level="ERROR"):
            enviados = self._backend(brevo, fail_silently=True).send_messages(
                [_mensaje()]
            )

        self.assertEqual(enviados, 0)
        self.assertEqual(brevo.peticiones, [])

    @patch(
        "resend.Emails.send",
        side_effect=_error_resend(ApplicationError, 503, "application_error"),
    )
    def test_si_fallan_los_dos_levanta_envio_fallido_con_ambos_estados(self, _mock):
        brevo = _Brevo(402, {"code": "not_enough_credits", "message": "m"})

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            with self.assertRaises(EnvioFallido) as ctx:
                self._backend(brevo).send_messages([_mensaje()])

        self.assertEqual(
            str(ctx.exception),
            "Ningún proveedor pudo enviar el email (Resend: 503, Brevo: 402)",
        )
        self.assertEqual(
            [(e.proveedor, e.estado) for e in ctx.exception.errores],
            [("Resend", 503), ("Brevo", 402)],
        )
        self.assertIsInstance(ctx.exception.__cause__, ErrorDeProveedor)
        self.assertIn("Resend: 503, Brevo: 402", "\n".join(logs.output))
        self._sin_direcciones_ni_claves(logs)

    @patch(
        "resend.Emails.send",
        side_effect=_error_resend(InvalidApiKeyError, 403, "invalid_api_key"),
    )
    def test_un_400_de_brevo_tras_caer_resend_tambien_es_envio_fallido(self, _mock):
        # Resend cae y Brevo rechaza por configuración (remitente no verificado):
        # no fue un dato del usuario, así que termina en `EnvioFallido` y el PR 2
        # lo convierte en `email_unavailable` en vez de un 500.
        brevo = _Brevo(400, {"code": "invalid_parameter", "message": "m"})

        with self.assertLogs(LOGGER, level="ERROR"):
            with self.assertRaises(EnvioFallido) as ctx:
                self._backend(brevo).send_messages([_mensaje()])

        self.assertEqual(
            [(e.proveedor, e.estado) for e in ctx.exception.errores],
            [("Resend", 403), ("Brevo", 400)],
        )

    @patch(
        "resend.Emails.send",
        side_effect=_error_resend(ApplicationError, 503, "application_error"),
    )
    def test_si_fallan_los_dos_con_fail_silently_devuelve_cero_y_loguea_error(
        self, _mock
    ):
        brevo = _Brevo(402, {"code": "not_enough_credits", "message": "m"})

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            enviados = self._backend(brevo, fail_silently=True).send_messages(
                [_mensaje()]
            )

        self.assertEqual(enviados, 0)
        self.assertIn("Resend: 503, Brevo: 402", "\n".join(logs.output))

    @patch("resend.Emails.send")
    def test_lote_parcial_cada_mensaje_se_envia_una_sola_vez(self, mock_send):
        # Resend acepta el primero y falla en el segundo: el primero no se
        # reenvía por Brevo (el respaldo es por mensaje, no por lote).
        mock_send.side_effect = [
            {"id": "res-1"},
            _error_resend(RateLimitError, 429, "daily_quota_exceeded"),
        ]
        brevo = _Brevo()
        mensajes = [_mensaje(subject="Primero"), _mensaje(subject="Segundo")]

        enviados = self._backend(brevo).send_messages(mensajes)

        self.assertEqual(enviados, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(len(brevo.peticiones), 1)
        self.assertEqual(brevo.json()["subject"], "Segundo")

    @override_settings(BREVO_API_KEY="")
    @patch("resend.Emails.send")
    def test_sin_clave_de_brevo_se_comporta_como_resend_solo(self, mock_send):
        mock_send.side_effect = _error_resend(
            RateLimitError, 429, "daily_quota_exceeded"
        )
        brevo = _Brevo()

        with self.assertRaises(EnvioFallido) as ctx:
            self._backend(brevo).send_messages([_mensaje()])

        self.assertEqual([e.proveedor for e in ctx.exception.errores], ["Resend"])
        self.assertEqual(brevo.peticiones, [])

    @override_settings(RESEND_API_KEY="")
    @patch("resend.Emails.send")
    def test_sin_clave_de_resend_envia_solo_por_brevo(self, mock_send):
        brevo = _Brevo()

        enviados = self._backend(brevo).send_messages([_mensaje()])

        self.assertEqual(enviados, 1)
        mock_send.assert_not_called()
        self.assertEqual(len(brevo.peticiones), 1)

    @override_settings(RESEND_API_KEY="", BREVO_API_KEY="")
    @patch("resend.Emails.send")
    def test_sin_ninguna_clave_loguea_error_y_devuelve_cero(self, mock_send):
        brevo = _Brevo()

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            enviados = self._backend(brevo).send_messages([_mensaje(), _mensaje()])

        self.assertEqual(enviados, 0)
        mock_send.assert_not_called()
        self.assertEqual(brevo.peticiones, [])
        salida = "\n".join(logs.output)
        self.assertIn("2 email(s) NO enviados", salida)
        self.assertIn("RESEND_API_KEY", salida)
        self.assertIn("BREVO_API_KEY", salida)

    def test_lista_vacia_devuelve_cero(self):
        self.assertEqual(self._backend(_Brevo()).send_messages([]), 0)

    @patch("resend.Emails.send", side_effect=RuntimeError("bug propio"))
    def test_una_excepcion_desconocida_se_propaga_sin_probar_brevo(self, _mock):
        brevo = _Brevo()

        with self.assertRaises(RuntimeError):
            self._backend(brevo).send_messages([_mensaje()])

        self.assertEqual(brevo.peticiones, [])

    @patch("resend.Emails.send")
    @override_settings(RESEND_TEST_RECIPIENT=PRUEBA, BREVO_TEST_RECIPIENT=PRUEBA)
    def test_ningun_log_lleva_direcciones_ni_claves_aun_con_redireccion(
        self, mock_send
    ):
        mock_send.side_effect = _error_resend(
            ValidationError, 403, "validation_error", f"solo a {PRUEBA}"
        )

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            self._backend(_Brevo()).send_messages([_mensaje(cc=[COPIA], bcc=[OCULTA])])

        self._sin_direcciones_ni_claves(logs)


@override_settings(
    BREVO_API_KEY=CLAVE_BREVO,
    BREVO_FROM_EMAIL=REMITENTE_BREVO,
    BREVO_TEST_RECIPIENT="",
    RESEND_API_KEY=CLAVE_RESEND,
)
class BrevoBackendTests(SimpleTestCase):
    """`BrevoBackend` ofrece Brevo solo, con las mismas reglas."""

    def test_envia_solo_por_brevo_aunque_haya_clave_de_resend(self):
        brevo = _Brevo()

        with patch("resend.Emails.send") as mock_send:
            enviados = BrevoBackend(transport=brevo.transporte).send_messages(
                [_mensaje()]
            )

        self.assertEqual(enviados, 1)
        mock_send.assert_not_called()
        self.assertEqual(len(brevo.peticiones), 1)

    @override_settings(BREVO_API_KEY="")
    def test_sin_clave_no_llama_a_la_api(self):
        brevo = _Brevo()

        with self.assertLogs(LOGGER, level="ERROR"):
            enviados = BrevoBackend(transport=brevo.transporte).send_messages(
                [_mensaje()]
            )

        self.assertEqual(enviados, 0)
        self.assertEqual(brevo.peticiones, [])

    def test_error_propaga_salvo_fail_silently(self):
        brevo = _Brevo(503, {})

        with self.assertRaises(EnvioFallido):
            BrevoBackend(transport=brevo.transporte).send_messages([_mensaje()])
        with self.assertLogs(LOGGER, level="ERROR"):
            self.assertEqual(
                BrevoBackend(
                    fail_silently=True, transport=brevo.transporte
                ).send_messages([_mensaje()]),
                0,
            )


@override_settings(
    EMAIL_BACKEND="filmai.email_backends.RespaldoBackend",
    DEFAULT_FROM_EMAIL="FilmAI <onboarding@resend.dev>",
    RESEND_TEST_RECIPIENT=PRUEBA,
    BREVO_TEST_RECIPIENT="otra@prueba-ejemplo.com",
)
class SendTestEmailTests(SimpleTestCase):
    """El comando muestra la cadena de proveedores y las redirecciones activas.

    Se parchea `send_mail` del propio comando: así no se envía nada, ni
    siquiera por el backend de pruebas, y se puede leer el texto del mensaje.
    """

    def _correr(self, enviados=1):
        salida = StringIO()
        with patch(
            "usuarios.management.commands.send_test_email.send_mail",
            return_value=enviados,
        ) as mock_envio:
            call_command("send_test_email", PARA, stdout=salida)
        return mock_envio, salida.getvalue()

    def test_el_mensaje_lista_la_cadena_y_los_dos_destinatarios_de_prueba(self):
        mock_envio, salida = self._correr()

        texto = mock_envio.call_args.kwargs["message"]
        self.assertIn("Proveedores (en orden): Resend → Brevo", texto)
        self.assertIn(f"RESEND_TEST_RECIPIENT activo: llega a {PRUEBA}", texto)
        self.assertIn("BREVO_TEST_RECIPIENT activo: llega a otra@", texto)
        self.assertIn("RESEND_TEST_RECIPIENT activo", salida)
        self.assertIn("BREVO_TEST_RECIPIENT activo", salida)

    @override_settings(EMAIL_BACKEND="filmai.email_backends.ResendBackend")
    def test_con_resend_solo_no_menciona_brevo(self):
        mock_envio, salida = self._correr()

        texto = mock_envio.call_args.kwargs["message"]
        self.assertIn("Proveedores (en orden): Resend", texto)
        self.assertNotIn("BREVO_TEST_RECIPIENT", texto + salida)

    def test_si_no_se_envio_el_error_menciona_las_dos_claves(self):
        with self.assertRaisesMessage(CommandError, "BREVO_API_KEY"):
            self._correr(enviados=0)
