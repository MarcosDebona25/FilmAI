"""
Compila las salidas redactadas en el corpus de reseñas.

    python manage.py compilar_corpus_resenas DIR

Lee `DIR/salida_*.jsonl` (una línea por (producción, idioma, banda), mismo
esquema que el corpus), descarta e informa las líneas inválidas, las fusiona con
`backend/seed_data/resenas.jsonl.gz` (las nuevas pisan a las viejas por clave) y
lo reescribe ordenado y determinista. Reglas en `usuarios/corpus_resenas.py`.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from usuarios import corpus_resenas


class Command(BaseCommand):
    help = "Valida DIR/salida_*.jsonl y los fusiona en el corpus de reseñas."

    def add_arguments(self, parser):
        parser.add_argument("directorio")

    def handle(self, *args, **opciones):
        directorio = Path(opciones["directorio"])
        archivos = sorted(directorio.glob("salida_*.jsonl"))
        if not archivos:
            raise CommandError(f"No hay salida_*.jsonl en {directorio}.")

        corpus = corpus_resenas.cargar_corpus()
        validas = invalidas = 0
        for archivo in archivos:
            texto = archivo.read_text(encoding="utf-8")
            for numero, linea in enumerate(texto.splitlines(), start=1):
                if not linea.strip():
                    continue
                try:
                    entrada = corpus_resenas.validar_entrada(json.loads(linea))
                except ValueError as error:
                    invalidas += 1
                    self.stderr.write(f"  inválida {archivo.name}:{numero}: {error}")
                    continue
                corpus[corpus_resenas.clave(entrada)] = entrada["textos"]
                validas += 1

        corpus_resenas.escribir_corpus(corpus)
        self.stdout.write(
            self.style.SUCCESS(
                f"Entradas válidas: {validas}. Inválidas: {invalidas}. "
                f"Total en el corpus: {len(corpus)}."
            )
        )
