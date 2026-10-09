"""Exporta las identidades y nombres reservados para los consumidores."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from listas.identidades import contrato_enums


class Command(BaseCommand):
    help = "Exporta el contrato de listas predeterminadas, género y nombres reservados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            type=Path,
            default=Path(settings.BASE_DIR).parent / "contracts" / "enums.json",
        )

    def handle(self, *args, **options):
        salida = options["salida"]
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(
            json.dumps(contrato_enums(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(f"Contrato exportado: {salida}")
