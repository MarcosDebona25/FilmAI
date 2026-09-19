"""Seed inicial del catálogo (C-04c): `python manage.py seed_catalogo`.

La sync nocturna (C-04b) mantiene el catálogo FRESCO pero no lo hace CRECER:
lee la página 1 de cuatro listados, unas 60 producciones por noche, casi
todas ya vistas. Este comando puebla el corpus una vez, recorriendo TMDB por
género x década x tipo y materializando lo que encuentra.

Por qué así y no "las 10.000 más populares": el corpus ES el espacio de
búsqueda semántica (B-06). Un corpus de éxitos de este mes solo puede
recomendar éxitos de este mes; el usuario que pide «una de culto de los 80
sobre paranoia» necesita que esa película exista en nuestra base.

Es un comando de management y no una tarea Celery a propósito: corre decenas
de minutos bajo supervisión, y un proceso bloqueante con contador de progreso
es más fácil de mirar, interrumpir y retomar que una tarea cuyo único
resultado es una línea de log una hora después.

No escribe por su cuenta: cada producción pasa por `materializar()`, el único
camino de escritura del catálogo, igual que las vistas de detalle (C-04a) y
la sync (C-04b).

Uso:
    python manage.py seed_catalogo                  # 2.000 producciones, ~50 min
    python manage.py seed_catalogo --limite 10000   # ~4 h
    python manage.py seed_catalogo --dry-run        # recorre y cuenta, no escribe

Se puede cortar con Ctrl-C y volver a correr: lo que ya está fresco en la
base no se vuelve a pedir a TMDB.
"""

import logging
import random
import time
from typing import NamedTuple

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from catalogo.services.adapter import tmdb_a_dominio
from catalogo.services.materialization import claves_frescas, materializar
from catalogo.services.tmdb import get_catalog_service

logger = logging.getLogger(__name__)

# Décadas desde 1970: antes de eso TMDB tiene poco y disperso, y no es lo que
# un usuario del chatbot va a pedir. La década actual se incluye entera.
_DECADA_INICIAL = 1970

# ~50 minutos a 3 llamadas por producción. Un corpus útil que se puede ver
# terminar hoy vale más que uno perfecto que necesita la máquina despierta
# toda la noche; el objetivo de 10.000 del plan se pide explícitamente.
_LIMITE_POR_DEFECTO = 2000

# `total_pages` MIENTE: `/discover` reporta 1001 y la página 501 devuelve
# HTTP 400 ("Pages start at 1 and max at 500"). Verificado el 18/09/2026.
_MAX_PAGINAS = 500

# Dentro de cada combinación, los más votados primero: sci-fi de los 80 por
# votos devuelve Back to the Future y Blade Runner; por popularidad (el orden
# por defecto de TMDB) devuelve lo que trendea esta semana. Verificado en vivo.
_ORDEN = "vote_count.desc"

# Semilla fija del barajado: dos corridas recorren las combinaciones en el
# mismo orden, así una corrida interrumpida y retomada cubre el mismo terreno
# y un test puede afirmar el orden.
_SEMILLA = 2026

_TIPOS = ("movie", "tv")
_NOMBRE_TIPO = {"movie": "película", "tv": "serie"}


class Combinacion(NamedTuple):
    """Una celda del muestreo: un género de un tipo en una década."""

    tipo: str  # vocabulario de TMDB: "movie" / "tv"
    genero: int  # id de género de TMDB, distinto por tipo
    nombre_genero: str  # solo para el progreso en pantalla
    anio_desde: int
    anio_hasta: int


def _decadas(desde_anio, hasta_anio):
    """`[(1970, 1979), (1980, 1989), ...]` hasta la década que contiene `hasta_anio`."""
    inicio = desde_anio - desde_anio % 10
    return [(decada, decada + 9) for decada in range(inicio, hasta_anio + 1, 10)]


def _combinaciones(generos_por_tipo, desde_anio, hasta_anio):
    """Arma género x década x tipo y lo baraja con semilla fija.

    Barajado porque la corrida se corta —por `--limite`, por Ctrl-C, por una
    notebook que se cierra— y en orden de declaración el corte dejaría todo
    Action y nada de Western. Con semilla fija, para que sea reproducible.
    `random.Random(semilla)` es un generador propio: no toca el estado global
    de `random`, así que nada más en el proceso cambia de comportamiento.
    """
    combinaciones = [
        Combinacion(tipo, genero["id"], genero["name"], anio_desde, anio_hasta)
        for tipo, generos in generos_por_tipo.items()
        for genero in generos
        for anio_desde, anio_hasta in _decadas(desde_anio, hasta_anio)
    ]
    random.Random(_SEMILLA).shuffle(combinaciones)
    return combinaciones


def _recorrer(servicio, combinaciones):
    """Recorre `discover` en round-robin: página 1 de todas, después la 2...

    Es un generador: produce `(combinacion, pagina, items)` por cada página
    leída, y quien lo consume decide cuándo parar (el tope de `--limite`).
    Profundidad primero —agotar Action antes de mirar Drama— haría que una
    corrida interrumpida tuviera todo de un género y nada de los demás; en
    round-robin, una corrida interrumpida es una versión más chica del mismo
    corpus diverso.

    Una combinación sale de la ronda cuando se le acaban las páginas o cuando
    llega a la pared de las 500 (`_MAX_PAGINAS`): `total_pages` no es una
    promesa. Si una página falla, se avisa con `items=None` —el comando lo
    cuenta como error— y la combinación se saca de la ronda; una corrida de
    cuatro horas no puede morir por un 500 en una combinación.
    """
    pagina, activas = 1, list(combinaciones)
    while activas:
        siguientes = []
        for combinacion in activas:
            try:
                payload = servicio.discover(
                    combinacion.tipo,
                    genero=combinacion.genero,
                    page=pagina,
                    anio_desde=combinacion.anio_desde,
                    anio_hasta=combinacion.anio_hasta,
                    sort_by=_ORDEN,
                )
            except Exception:
                # Amplio a propósito: es el límite con TMDB.
                logger.exception(
                    "seed_catalogo: falló discover %s página %s", combinacion, pagina
                )
                yield combinacion, pagina, None
                continue

            yield combinacion, pagina, payload.get("results") or []
            if pagina < min(payload.get("total_pages", 1), _MAX_PAGINAS):
                siguientes.append(combinacion)
        activas = siguientes
        pagina += 1


class Command(BaseCommand):
    help = (
        "Puebla el catálogo desde TMDB muestreando por género x década x tipo. "
        "Resumible: lo que ya está fresco en la base no se vuelve a pedir."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limite",
            type=int,
            default=_LIMITE_POR_DEFECTO,
            help=(
                "Cuántas producciones materializar EN ESTA CORRIDA "
                f"(default {_LIMITE_POR_DEFECTO}, ~50 min). Lo que ya estaba "
                "fresco no descuenta."
            ),
        )
        parser.add_argument(
            "--desde-anio",
            type=int,
            default=_DECADA_INICIAL,
            help=(
                f"Primera década a muestrear (default {_DECADA_INICIAL}); "
                "se redondea al inicio de la década."
            ),
        )
        parser.add_argument(
            "--tipos",
            nargs="+",
            choices=_TIPOS,
            default=list(_TIPOS),
            help="Qué tipos muestrear (default: movie tv).",
        )
        parser.add_argument(
            "--pausa",
            type=float,
            default=0.0,
            help=(
                "Segundos de espera entre materializaciones. TMDB no publica "
                "límites y el cliente ya reintenta los 429; es un freno manual "
                "por si una corrida larga empieza a recibirlos."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Recorre discover y cuenta qué haría, pero no materializa nada.",
        )

    def handle(self, *args, **options):
        limite = options["limite"]
        if limite < 1:
            raise CommandError("--limite debe ser al menos 1.")

        servicio = get_catalog_service()
        # Los ids de género son de TMDB y difieren por tipo (película tiene
        # Action y Adventure separados; serie tiene Action & Adventure): se
        # piden a la API, no se copian al código.
        generos_por_tipo = {
            tipo: servicio.get_genres(tipo)["genres"] for tipo in options["tipos"]
        }
        combinaciones = _combinaciones(
            generos_por_tipo, options["desde_anio"], timezone.now().year
        )
        if not combinaciones:
            raise CommandError(
                f"No hay décadas desde {options['desde_anio']}: nada que muestrear."
            )

        self.estadisticas = {
            "materializadas": 0,  # pasaron por materializar() en esta corrida
            "ya_estaban": 0,  # frescas en la base: ni se le pidieron a TMDB
            "omitidas": 0,  # repetidas dentro de la corrida (un título, dos géneros)
            "errores": 0,  # materializar() o una página de discover fallaron
        }
        self.stdout.write(
            f"{len(combinaciones)} combinaciones (género x década x tipo), "
            f"objetivo: {limite} producciones"
            + (" — dry-run, no se escribe nada" if options["dry_run"] else "")
        )

        try:
            self._sembrar(servicio, combinaciones, limite, options)
        except KeyboardInterrupt:
            # Cada materializar() es su propia transacción: lo hecho hasta acá
            # está guardado. Cerrar con el resumen, no con un traceback.
            self.stdout.write(
                self.style.WARNING(
                    "Interrumpido. Lo materializado queda guardado; volvé a "
                    "correr el comando para retomar."
                )
            )
        self._resumen(options["dry_run"])

    def _sembrar(self, servicio, combinaciones, limite, options):
        # Una consulta al arrancar, no una por ítem. Es lo que hace gratis
        # retomar: lo fresco se saltea acá y nunca llega a materializar().
        frescas = claves_frescas()
        # Lo ya visto EN ESTA corrida: un título con dos géneros aparece en dos
        # combinaciones y tiene que contar una sola vez.
        vistas = set()

        for combinacion, pagina, items in _recorrer(servicio, combinaciones):
            if items is None:
                self.estadisticas["errores"] += 1
                continue
            self._progreso(combinacion, pagina, limite)
            tipo = tmdb_a_dominio(combinacion.tipo)
            for item in items:
                self._procesar(item, combinacion.tipo, tipo, frescas, vistas, options)
                if self.estadisticas["materializadas"] >= limite:
                    return

    def _procesar(self, item, tipo_tmdb, tipo, frescas, vistas, options):
        id_tmdb = item.get("id")
        if id_tmdb is None:
            self.estadisticas["omitidas"] += 1
            return
        # El id de TMDB solo es único dentro de un tipo: la clave es (id, tipo).
        clave = (id_tmdb, tipo)
        if clave in vistas:
            self.estadisticas["omitidas"] += 1
            return
        vistas.add(clave)
        if clave in frescas:
            self.estadisticas["ya_estaban"] += 1
            return

        if not options["dry_run"]:
            try:
                materializar(id_tmdb, tipo_tmdb)
            except Exception:
                # Amplio a propósito: es el límite con TMDB y con la base. Un
                # título que TMDB no devuelve se loguea, se cuenta y se sigue;
                # misma política que la sync y las vistas de detalle.
                logger.exception("seed_catalogo: falló (%s, %s)", id_tmdb, tipo_tmdb)
                self.estadisticas["errores"] += 1
                return
            if options["pausa"]:
                time.sleep(options["pausa"])
        self.estadisticas["materializadas"] += 1

    def _progreso(self, combinacion, pagina, limite):
        self.stdout.write(
            f"[{self.estadisticas['materializadas']}/{limite}] "
            f"{combinacion.nombre_genero} · {_NOMBRE_TIPO[combinacion.tipo]} · "
            f"{combinacion.anio_desde}-{combinacion.anio_hasta} · página {pagina}"
        )

    def _resumen(self, dry_run):
        contadores = " ".join(f"{k}={v}" for k, v in self.estadisticas.items())
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"dry-run, nada se escribió: {contadores}")
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Seed completado: {contadores}"))
        logger.info("seed_catalogo: %s", self.estadisticas)
