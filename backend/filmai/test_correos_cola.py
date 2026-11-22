"""Correos de cuenta por Celery (Q-08): encolado, tarea y reintentos.

Dos mitades. `enviar_correo` renderiza y encola (se prueba con `apply_async`
reemplazado, sin broker). La tarea `enviar_correo_tarea` envía y reintenta (se
prueba ejecutándola en el acto con `.apply()`, que corre el cuerpo en este mismo
proceso sin pasar por Redis).
"""

import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from celery.exceptions import Retry
from django.conf import settings
from django.core import mail
from django.test import SimpleTestCase, override_settings
from kombu.exceptions import OperationalError

from filmai.correos.servicio import CorreoNoEncolado, enviar_correo
from filmai.email_backends import EnvioFallido, ErrorDeProveedor
from filmai.tasks import MAX_REINTENTOS, enviar_correo_tarea

DESTINATARIO = "secreto@example.com"
ENLACE = "https://filmai.test/confirm-email/clave-secreta/"


def _contexto():
    return {
        "user": SimpleNamespace(nombre="Ana", apellido="Pérez"),
        "activate_url": ENLACE,
    }


class EncoladoTests(SimpleTestCase):
    """`enviar_correo` no habla con ningún proveedor: renderiza y encola."""

    def test_encola_los_textos_renderizados_con_argsrepr_redactado(self):
        with patch.object(enviar_correo_tarea, "apply_async") as encolar:
            enviar_correo("confirmacion_registro", DESTINATARIO, _contexto(), "es")

        encolar.assert_called_once()
        kwargs = encolar.call_args.kwargs
        caso, asunto, texto, html, destinatario = kwargs["args"]
        self.assertEqual(caso, "confirmacion_registro")
        self.assertTrue(asunto.startswith("[FilmAI]"))
        self.assertIn(ENLACE, texto)
        self.assertIn(ENLACE, html)
        self.assertEqual(destinatario, DESTINATARIO)
        # Lo que el worker imprime al recibir la tarea no lleva dirección ni enlace.
        self.assertNotIn("secreto", kwargs["argsrepr"])
        self.assertNotIn("clave-secreta", kwargs["argsrepr"])
        self.assertIn("confirmacion_registro", kwargs["argsrepr"])

    def test_no_llama_a_send_mail_dentro_del_pedido(self):
        with (
            patch.object(enviar_correo_tarea, "apply_async"),
            patch("filmai.tasks.send_mail") as send_mail,
        ):
            enviar_correo("restablecer_contrasena", DESTINATARIO, _contexto(), "en")
        send_mail.assert_not_called()

    def test_la_publicacion_no_reintenta(self):
        """`retry=False`: con el broker caído el pedido falla en segundos."""
        with patch.object(enviar_correo_tarea, "apply_async") as encolar:
            enviar_correo("confirmacion_correo", DESTINATARIO, _contexto(), "es")
        self.assertIs(encolar.call_args.kwargs["retry"], False)

    def test_broker_caido_levanta_correo_no_encolado(self):
        # El mismo error que kombu levanta con Redis rechazando la conexión
        # (verificado con un `apply_async` real contra un puerto cerrado).
        caida = OperationalError("Error 111 connecting to redis:6379. Refused.")
        with patch.object(enviar_correo_tarea, "apply_async", side_effect=caida):
            with self.assertRaises(CorreoNoEncolado) as ctx:
                enviar_correo("confirmacion_registro", DESTINATARIO, _contexto(), "es")
        self.assertIs(ctx.exception.__cause__, caida)
        # El mensaje propio no copia el texto del error (podría llevar el host).
        self.assertNotIn("redis", str(ctx.exception))


_GUION_BROKER_CAIDO = """
import time
import django
django.setup()
from filmai.correos.servicio import CorreoNoEncolado, enviar_correo
inicio = time.monotonic()
try:
    enviar_correo("confirmacion_correo", "a@example.com", {"activate_url": "https://x.test/"}, "es")
except CorreoNoEncolado as error:
    print("CorreoNoEncolado", type(error.__cause__).__module__, type(error.__cause__).__name__, round(time.monotonic() - inicio, 1))
"""


class BrokerCaidoRealTests(SimpleTestCase):
    """Sin simular `apply_async`: publica de verdad contra un puerto cerrado.

    Comprueba lo que los demás tests dan por cierto: con Redis sin responder, la
    publicación falla rápido con `kombu.exceptions.OperationalError` y
    `enviar_correo` la convierte en `CorreoNoEncolado`. Corre en un proceso
    aparte porque la suite fuerza las tareas en el acto (modo eager) y la
    configuración de Celery no se puede cambiar a mitad de proceso.
    """

    def test_publicar_con_el_puerto_cerrado_falla_rapido_con_correo_no_encolado(self):
        entorno = {
            **os.environ,
            "CELERY_BROKER_URL": "redis://:x@127.0.0.1:1/1",
            "DJANGO_SETTINGS_MODULE": "filmai.settings",
        }
        salida = subprocess.run(
            [sys.executable, "-c", _GUION_BROKER_CAIDO],
            cwd=settings.BASE_DIR,
            env=entorno,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        # La última línea: el arranque de Django puede imprimir otras antes.
        linea = salida.stdout.strip().splitlines()[-1] if salida.stdout else ""
        self.assertTrue(linea.startswith("CorreoNoEncolado"), salida.stderr[-500:])
        _, modulo, clase, segundos = linea.split()
        self.assertEqual((modulo, clase), ("kombu.exceptions", "OperationalError"))
        self.assertLess(float(segundos), 5)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TareaTests(SimpleTestCase):
    """`enviar_correo_tarea` envía con el backend y decide qué se reintenta."""

    def setUp(self):
        mail.outbox.clear()
        self.args = ("confirmacion_registro", "[FilmAI] Hola", "texto", "<p>html</p>")

    def ejecutar(self):
        return enviar_correo_tarea.apply(args=(*self.args, DESTINATARIO))

    def test_exito_envia_texto_y_html_al_destinatario(self):
        resultado = self.ejecutar()
        self.assertTrue(resultado.successful())
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, [DESTINATARIO])
        self.assertEqual(correo.subject, "[FilmAI] Hola")
        self.assertEqual(correo.body, "texto")
        self.assertEqual(correo.alternatives, [("<p>html</p>", "text/html")])

    def test_la_politica_de_reintentos_es_la_acordada(self):
        """Solo `EnvioFallido`, backoff exponencial con jitter, ~1 hora en total."""
        self.assertEqual(enviar_correo_tarea.autoretry_for, (EnvioFallido,))
        self.assertEqual(enviar_correo_tarea.retry_backoff, 60)
        self.assertEqual(enviar_correo_tarea.retry_backoff_max, 1800)
        self.assertTrue(enviar_correo_tarea.retry_jitter)
        self.assertEqual(enviar_correo_tarea.max_retries, MAX_REINTENTOS)
        self.assertTrue(enviar_correo_tarea.ignore_result)
        # Peor caso (sin jitter): 1+2+4+8+16 min, luego 30 min por reintento. Muy
        # por debajo de las 24 horas de vigencia del enlace.
        peor_caso = sum(min(60 * 2**n, 1800) for n in range(MAX_REINTENTOS))  # segundos
        self.assertLess(peor_caso, 3 * 3600)
        self.assertGreater(peor_caso, 3600)

    def test_envio_fallido_programa_un_reintento_con_espera(self):
        fallo = EnvioFallido([ErrorDeProveedor("Resend", transitorio=True, estado=503)])
        with (
            patch("filmai.tasks.send_mail", side_effect=fallo),
            patch.object(enviar_correo_tarea, "retry", side_effect=Retry()) as retry,
        ):
            self.ejecutar()
        retry.assert_called_once()
        self.assertIs(retry.call_args.kwargs["exc"], fallo)
        # Con jitter la espera es un valor entre 0 y el backoff del primer intento.
        self.assertTrue(0 <= retry.call_args.kwargs["countdown"] <= 60)

    def test_agotados_los_reintentos_se_loguea_error(self):
        fallo = EnvioFallido([ErrorDeProveedor("Resend", transitorio=True, estado=503)])
        with (
            patch("filmai.tasks.send_mail", side_effect=fallo) as send_mail,
            self.assertLogs("filmai.tasks", "ERROR") as logs,
        ):
            resultado = self.ejecutar()
        # El intento original más los reintentos (en modo eager corren de seguido).
        self.assertEqual(send_mail.call_count, 1 + MAX_REINTENTOS)
        self.assertTrue(resultado.failed())
        self.assertIn("NO enviado", logs.output[-1])

    def test_error_no_transitorio_no_reintenta_y_loguea_error(self):
        invalido = ErrorDeProveedor("Resend", transitorio=False, estado=422)
        with (
            patch("filmai.tasks.send_mail", side_effect=invalido) as send_mail,
            self.assertLogs("filmai.tasks", "ERROR") as logs,
        ):
            resultado = self.ejecutar()
        send_mail.assert_called_once()
        self.assertTrue(resultado.failed())
        self.assertIn("NO enviado", logs.output[0])

    def test_los_logs_de_la_tarea_no_llevan_direcciones_ni_enlaces(self):
        texto_con_enlace = f"Confirmá en {ENLACE}"
        self.args = ("confirmacion_registro", "[FilmAI] Hola", texto_con_enlace, "<p/>")
        fallo = EnvioFallido([ErrorDeProveedor("Brevo", transitorio=True, estado=402)])
        with self.assertLogs("filmai.tasks", "DEBUG") as logs:
            self.ejecutar()  # éxito
            with patch("filmai.tasks.send_mail", side_effect=fallo):
                self.ejecutar()  # agotado
            with patch(
                "filmai.tasks.send_mail",
                side_effect=ErrorDeProveedor("Resend", transitorio=False, estado=400),
            ):
                self.ejecutar()  # no transitorio
        todo = "\n".join(logs.output)
        self.assertGreaterEqual(len(logs.output), 3)
        for secreto in ("secreto", "example.com", "clave-secreta", "filmai.test"):
            self.assertNotIn(secreto, todo)

    def test_sin_proveedor_configurado_se_loguea_error(self):
        """Un backend que devuelve 0 (sin claves) no se da por enviado."""
        with (
            patch("filmai.tasks.send_mail", return_value=0),
            self.assertLogs("filmai.tasks", "ERROR"),
        ):
            self.ejecutar()
