"""Completa `generos_ids` y las traducciones de las producciones ya guardadas."""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from catalogo.exceptions import TMDBError
from catalogo.models import ProduccionAudiovisual
from catalogo.services.adapter import dominio_a_tmdb
from catalogo.services.materialization import guardar_traducciones, idiomas_traducidos
from catalogo.services.tmdb import get_catalog_service


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


def pendientes():
    """Producciones enriquecidas a las que les falta alguna traducción o los ids."""
    esperadas = len(idiomas_traducidos())
    return (
        ProduccionAudiovisual.objects.filter(fecha_enriquecimiento__isnull=False)
        .annotate(total_traducciones=Count("traducciones"))
        .filter(
            Q(total_traducciones__lt=esperadas) | (Q(generos_ids=[]) & ~Q(generos=[]))
        )
        .order_by("pk")
    )


def rellenar(limite=None, lote=200):
    """Procesa por lotes; cada ítem falla solo, sin cortar el resto."""
    procesadas = fallidas = 0
    ultimo = 0
    while limite is None or procesadas + fallidas < limite:
        tamanio = lote if limite is None else min(lote, limite - procesadas - fallidas)
        filas = list(pendientes().filter(pk__gt=ultimo)[:tamanio])
        if not filas:
            break
        for produccion in filas:
            ultimo = produccion.pk
            tipo_tmdb = dominio_a_tmdb(produccion.tipo)
            try:
                if not produccion.generos_ids and produccion.generos:
                    servicio = get_catalog_service()
                    detalle = (
                        servicio.get_movie_detail(produccion.id_tmdb)
                        if tipo_tmdb == "movie"
                        else servicio.get_tv_detail(produccion.id_tmdb)
                    )
                    produccion.generos_ids = [
                        genero["id"]
                        for genero in (detalle.get("genres") or [])
                        if isinstance(genero.get("id"), int)
                    ]
                    # Solo esta columna: no se toca el texto de los embeddings.
                    produccion.save(update_fields=["generos_ids"])
                guardar_traducciones(produccion, produccion.id_tmdb, tipo_tmdb)
                procesadas += 1
            except TMDBError:
                fallidas += 1
    return {
        "procesadas": procesadas,
        "fallidas": fallidas,
        "pendientes": pendientes().count(),
    }
