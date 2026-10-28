"""Lectura por idioma y relleno de las traducciones guardadas."""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q

from catalogo.exceptions import TMDBError
from catalogo.models import ProduccionAudiovisual
from catalogo.services import materialization
from catalogo.services.adapter import dominio_a_tmdb
from catalogo.services.materialization import guardar_traducciones, idiomas_traducidos

logger = logging.getLogger(__name__)

# Dónde quedó la última corrida acotada (pk de la última fila intentada).
_CLAVE_CURSOR = "catalogo:traducciones:cursor"


def texto_localizado(produccion, campo, idioma):
    """`titulo`, `sinopsis` o `poster` en el idioma pedido, con respaldo canónico.

    Recorre `produccion.traducciones.all()` en vez de filtrar: así aprovecha el
    `prefetch_related("produccion__traducciones")` de los listados y no hace una
    consulta por fila. Un campo traducido vacío cae al valor en inglés.
    """
    if idioma and idioma != settings.IDIOMA_POR_DEFECTO:
        for traduccion in produccion.traducciones.all():
            if traduccion.idioma == idioma:
                return getattr(traduccion, campo) or getattr(produccion, campo)
    return getattr(produccion, campo)


def campos_en_ingles(produccion, idioma, campos=("titulo", "poster")):
    """Marca el respaldo canónico sin consultar traducciones por cada campo."""
    if not idioma or idioma == settings.IDIOMA_POR_DEFECTO:
        return []
    traduccion = next(
        (fila for fila in produccion.traducciones.all() if fila.idioma == idioma), None
    )
    return [
        campo
        for campo in campos
        if getattr(produccion, campo)
        and (traduccion is None or not getattr(traduccion, campo))
    ]


class ProduccionLocalizadaMixin:
    """Título, póster y `campos_en_ingles` de `instance.produccion` en el idioma.

    Lo comparten las filas que cuelgan de una producción («Mis reseñas» y los
    ítems de una lista). Cada serializer declara sus `titulo` y `poster` como
    `SerializerMethodField`: si los declarara el mixin, DRF los pondría primero
    y cambiaría el orden de las claves de la respuesta.
    """

    def to_representation(self, instance):
        data = super().to_representation(instance)
        idioma = self.context.get("idioma")
        if idioma and idioma != "en":
            data["campos_en_ingles"] = campos_en_ingles(instance.produccion, idioma)
        return data

    def get_titulo(self, instance):
        return texto_localizado(
            instance.produccion, "titulo", self.context.get("idioma")
        )

    def get_poster(self, instance):
        return texto_localizado(
            instance.produccion, "poster", self.context.get("idioma")
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


def _leer_cursor():
    try:
        return int(cache.get(_CLAVE_CURSOR) or 0)
    except Exception:
        # La caché es una comodidad: sin ella se arranca desde el principio.
        logger.warning("rellenar: no se pudo leer el cursor", exc_info=True)
        return 0


def _guardar_cursor(valor):
    try:
        cache.set(_CLAVE_CURSOR, valor, None)
    except Exception:
        logger.warning("rellenar: no se pudo guardar el cursor", exc_info=True)


def rellenar(limite=None, lote=200):
    """Procesa por lotes; cada ítem falla solo, sin cortar el resto.

    Con `limite` (la sync nocturna) la corrida retoma donde terminó la anterior
    —un cursor por `pk` guardado en la caché— y al agotar los pendientes vuelve
    al principio. Sin eso, las filas que fallan seguirían siendo siempre las
    primeras de `pendientes()` y ocuparían el límite todas las noches, dejando
    sin traducir a las demás. Sin `limite` (el comando manual) se recorre todo
    desde `pk` 0.
    """
    procesadas = fallidas = 0
    acotada = limite is not None
    ultimo = inicio = _leer_cursor() if acotada else 0
    # Tras volver al principio solo se recorre hasta el punto de partida, para
    # no reintentar en la misma corrida lo que ya se intentó.
    tope = None
    while limite is None or procesadas + fallidas < limite:
        tamanio = lote if limite is None else min(lote, limite - procesadas - fallidas)
        consulta = pendientes().filter(pk__gt=ultimo)
        if tope is not None:
            consulta = consulta.filter(pk__lte=tope)
        filas = list(consulta[:tamanio])
        if not filas:
            if inicio > 0 and tope is None:
                tope, ultimo = inicio, 0
                continue
            ultimo = 0
            break
        for produccion in filas:
            ultimo = produccion.pk
            tipo_tmdb = dominio_a_tmdb(produccion.tipo)
            try:
                if not produccion.generos_ids and produccion.generos:
                    # El mismo punto de acceso a TMDB que usa la materialización.
                    servicio = materialization.get_catalog_service()
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
    if acotada:
        _guardar_cursor(ultimo)
    return {
        "procesadas": procesadas,
        "fallidas": fallidas,
        "pendientes": pendientes().count(),
    }
