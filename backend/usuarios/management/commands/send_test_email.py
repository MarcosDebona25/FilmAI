"""Comando de desarrollo: verifica la integración con Resend.

Uso:
    python manage.py send_test_email
    python manage.py send_test_email otro@correo.com

Sin argumento usa DEFAULT_FROM_EMAIL → RESEND_TEST_RECIPIENT según .env.
Con Resend configurado sin dominio propio, el destinatario final siempre es
RESEND_TEST_RECIPIENT (override del backend); el comando lo deja visible en
la salida para que el resultado no confunda.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


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
        override = settings.RESEND_TEST_RECIPIENT

        mensaje = (
            "Si leés esto, el envío de emails de FilmAI funciona.\n\n"
            f"Backend activo: {settings.EMAIL_BACKEND}\n"
            f"Destinatario solicitado: {destino}\n"
            + (
                f"RESEND_TEST_RECIPIENT activo: llega a {override} "
                "(sin dominio propio verificado).\n"
                if override and destino != override
                else ""
            )
        )

        send_mail(
            subject="FilmAI — Email de prueba",
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destino],
            fail_silently=False,
        )

        self.stdout.write(self.style.SUCCESS(f"Email enviado a {destino}"))
        if override and destino != override:
            self.stdout.write(
                self.style.WARNING(
                    f"  → RESEND_TEST_RECIPIENT activo: llegó (o llegará) a {override}"
                )
            )
