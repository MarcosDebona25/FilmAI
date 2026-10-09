"""Completa `generos_ids` y las traducciones de las producciones ya guardadas."""

from django.core.management.base import BaseCommand

from catalogo.services.traducciones import rellenar


class Command(BaseCommand):
    help = (
        "Rellena generos_ids y ProduccionTraduccion de las producciones "
        "enriquecidas que todavía no los tienen. Idempotente: se puede repetir."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=None)
        parser.add_argument("--lote", type=int, default=200)

    def handle(self, *args, **options):
        resultado = rellenar(options["limite"], options["lote"])
        self.stdout.write(
            "Relleno finalizado: {procesadas} procesadas, {fallidas} con error, "
            "{pendientes} pendientes.".format(**resultado)
        )
