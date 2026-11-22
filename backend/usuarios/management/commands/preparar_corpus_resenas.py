"""
Prepara los lotes de entrada para redactar el corpus de reseñas.

    python manage.py preparar_corpus_resenas --top 2000 --lote 25 --salida DIR
                                             [--omitir-existentes]

Toma las N producciones «más votadas» que todavía no tengan sus seis entradas
(2 idiomas por 3 bandas) en `backend/seed_data/resenas.jsonl.gz` y escribe
`DIR/entrada_0001.json`, `entrada_0002.json`... con hasta `--lote` producciones
cada una: {id_tmdb, tipo, titulo, anio, generos, sinopsis (≤ 300 caracteres)}.

Solo lee la base. Los datos de TMDB quedan en `DIR` (scratch), nunca en el repo.

«Más votadas»: el modelo NO guarda la cantidad de votos de TMDB, solo el
promedio, que premia títulos oscuros con pocos votos. Como `seed` y
`seed_catalogo` descubren por `vote_count.desc`, se ordena por `pk` (orden de
inserción) como proxy de popularidad; se saltean las sin sinopsis o sin póster. Ver `docs/decisiones.md` (21/11/2026).
La sinopsis y el título son los canónicos del catálogo (inglés).

Con `--omitir-existentes` se saltean además las producciones que ya figuran en
algún `entrada_*.json` de `DIR` y la numeración sigue desde el último archivo:
sirve para repetir el comando sin pisar ni duplicar lotes.
"""

import itertools
import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from catalogo.models import ProduccionAudiovisual
from catalogo.services.tmdb import get_catalog_service
from usuarios import corpus_resenas

LARGO_SINOPSIS = 300


def recortar(texto, largo=LARGO_SINOPSIS):
    """Recorta en el último espacio antes de `largo`, con «…» si cortó."""
    texto = " ".join((texto or "").split())
    if len(texto) <= largo:
        return texto
    corte = texto[: largo - 1].rsplit(" ", 1)[0] or texto[: largo - 1]
    return corte.rstrip(" ,;:.") + "…"


def ranking_por_votos(servicio, paginas, pausa=0.0):
    """`{(id_tmdb, tipo): puesto}` con los más votados de TMDB.

    Lee `discover` ordenado por `vote_count.desc`: `paginas` de películas y un
    tercio de series. Intercala 3 películas por cada serie. Si una página falla
    se corta ese tipo: con lo ya leído alcanza para elegir.
    """
    por_tipo = {"movie": [], "tv": []}
    for tipo, cuantas in (("movie", paginas), ("tv", max(1, paginas // 3))):
        for pagina in range(1, cuantas + 1):
            try:
                resultados = servicio.discover(
                    tipo, page=pagina, sort_by="vote_count.desc"
                ).get("results")
            except Exception:  # límite con TMDB: se usa lo leído hasta acá
                break
            por_tipo[tipo] += [(r["id"], tipo) for r in resultados or []]
            if pausa:
                time.sleep(pausa)
    mezcla = []
    peliculas, series = iter(por_tipo["movie"]), iter(por_tipo["tv"])
    for par in peliculas:
        mezcla.append(par)
        if len(mezcla) % 4 == 3:
            mezcla.extend(itertools.islice(series, 1))
    mezcla.extend(series)
    return {par: puesto for puesto, par in enumerate(mezcla)}


class Command(BaseCommand):
    help = "Escribe lotes JSON de producciones para redactar reseñas (solo lectura)."

    def add_arguments(self, parser):
        parser.add_argument("--top", type=int, required=True)
        parser.add_argument("--lote", type=int, default=25)
        parser.add_argument("--salida", required=True)
        parser.add_argument("--omitir-existentes", action="store_true")
        parser.add_argument(
            "--por-votos",
            type=int,
            metavar="PAGINAS",
            help=(
                "Ordena por votos reales de TMDB (PAGINAS de películas y un "
                "tercio de series) en lugar de por orden de inserción."
            ),
        )

    def handle(self, *args, **opciones):
        top, lote = opciones["top"], opciones["lote"]
        if top < 1 or lote < 1:
            raise CommandError("--top y --lote deben ser positivos.")
        salida = Path(opciones["salida"])
        salida.mkdir(parents=True, exist_ok=True)

        cubiertas = corpus_resenas.producciones_cubiertas(
            corpus_resenas.cargar_corpus()
        )
        en_salida = set()
        siguiente = 1
        if opciones["omitir_existentes"]:
            for archivo in sorted(salida.glob("entrada_*.json")):
                try:
                    for item in json.loads(archivo.read_text(encoding="utf-8")):
                        en_salida.add((item["id_tmdb"], item["tipo"]))
                    siguiente = max(siguiente, int(archivo.stem.split("_")[1]) + 1)
                except (ValueError, KeyError, TypeError, IndexError):
                    continue

        ranking = None
        if opciones["por_votos"]:
            ranking = ranking_por_votos(
                get_catalog_service(), opciones["por_votos"], pausa=0.2
            )

        candidatas = (
            ProduccionAudiovisual.objects.filter(
                disponible_en_tmdb=True, poster__startswith="/"
            )
            .exclude(titulo="")
            .exclude(sinopsis="")
            .order_by("pk")
        )
        items = []
        for p in candidatas.iterator():
            par = (p.id_tmdb, corpus_resenas.TIPO_MODELO_A_CORPUS[p.tipo])
            if ranking is not None and par not in ranking:
                continue
            if par in cubiertas or par in en_salida:
                continue
            items.append(
                {
                    "id_tmdb": p.id_tmdb,
                    "tipo": par[1],
                    "titulo": p.titulo,
                    "anio": p.fecha_lanzamiento.year if p.fecha_lanzamiento else None,
                    "generos": list(p.generos),
                    "sinopsis": recortar(p.sinopsis),
                }
            )
            if ranking is None and len(items) >= top:
                break

        if ranking is not None:
            items.sort(key=lambda i: ranking[(i["id_tmdb"], i["tipo"])])
            items = items[:top]

        archivos = 0
        for inicio in range(0, len(items), lote):
            nombre = salida / f"entrada_{siguiente + archivos:04d}.json"
            nombre.write_text(
                json.dumps(items[inicio : inicio + lote], ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            archivos += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(items)} producciones en {archivos} archivos en {salida}."
            )
        )
