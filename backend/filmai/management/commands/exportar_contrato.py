"""Exporta `contracts/error-codes.json` desde el catálogo de códigos."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from filmai.errores.contrato import serializar_contrato


class Command(BaseCommand):
    help = "Exporta el contrato versionado de códigos de error y de éxito."

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            type=Path,
            default=Path(settings.BASE_DIR).parent / "contracts" / "error-codes.json",
        )

    def handle(self, *args, **options):
        salida = options["salida"]
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(serializar_contrato(), encoding="utf-8")
        self.stdout.write(f"Contrato exportado: {salida}")
