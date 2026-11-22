"""Comando de desarrollo: verifica el envío de emails (Resend, Brevo o ambos).

Uso:
    python manage.py send_test_email
    python manage.py send_test_email otro@correo.com

Sin argumento usa DEFAULT_FROM_EMAIL como destino. Muestra la cadena de
proveedores del EMAIL_BACKEND activo (por ejemplo Resend → Brevo) y los
destinatarios de prueba configurados: con un destinatario de prueba, el
destino final siempre es ese (override del backend), y el comando lo deja
visible en la salida para que el resultado no confunda.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

# Cadena de proveedores de cada backend, en orden de intento.
CADENAS = {
    "filmai.email_backends.ResendBackend": ("Resend",),
    "filmai.email_backends.BrevoBackend": ("Brevo",),
    "filmai.email_backends.RespaldoBackend": ("Resend", "Brevo"),
}

# Destinatario de prueba de cada proveedor, por nombre de variable.
DESTINATARIOS_DE_PRUEBA = {
    "Resend": "RESEND_TEST_RECIPIENT",
    "Brevo": "BREVO_TEST_RECIPIENT",
}


class Command(BaseCommand):
    help = "Envía un email de prueba usando el EMAIL_BACKEND configurado."

    def add_arguments(self, parser):
        parser.add_argument(
            "destinatario",
            nargs="?",
            default=None,
            help="Email destino (opcional). Por defecto DEFAULT_FROM_EMAIL.",
        )

    def handle(self, *args, **options):
        destino = options["destinatario"] or settings.DEFAULT_FROM_EMAIL
        cadena = CADENAS.get(settings.EMAIL_BACKEND, ())
        redirecciones = {
            proveedor: getattr(settings, DESTINATARIOS_DE_PRUEBA[proveedor], "")
            for proveedor in cadena
        }
        activas = {p: r for p, r in redirecciones.items() if r and destino != r}

        mensaje = (
            "Si leés esto, el envío de emails de FilmAI funciona.\n\n"
            f"Backend activo: {settings.EMAIL_BACKEND}\n"
            + (f"Proveedores (en orden): {' → '.join(cadena)}\n" if cadena else "")
            + f"Destinatario solicitado: {destino}\n"
            + "".join(
                f"{DESTINATARIOS_DE_PRUEBA[p]} activo: llega a {r} "
                "(sin dominio propio verificado).\n"
                for p, r in activas.items()
            )
        )

        enviados = send_mail(
            subject="FilmAI — Email de prueba",
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destino],
            fail_silently=False,
        )

        # Los backends devuelven 0 (y loguean error) si falta la clave del
        # proveedor: el comando debe fallar en vez de reportar un envío que no
        # ocurrió.
        if enviados != 1:
            raise CommandError(
                f"El email no se envió (send_mail devolvió {enviados!r}). Verificá "
                "RESEND_API_KEY, BREVO_API_KEY y la configuración de EMAIL_BACKEND."
            )

        self.stdout.write(self.style.SUCCESS(f"Email enviado a {destino}"))
        for proveedor, redireccion in activas.items():
            self.stdout.write(
                self.style.WARNING(
                    f"  → {DESTINATARIOS_DE_PRUEBA[proveedor]} activo: llegó "
                    f"(o llegará) a {redireccion} si lo envía {proveedor}"
                )
            )
