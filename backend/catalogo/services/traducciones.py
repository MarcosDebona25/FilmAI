"""Lectura por idioma y relleno de las traducciones guardadas."""

from django.conf import settings
from django.db.models import Count, Q

from catalogo.exceptions import TMDBError
from catalogo.models import ProduccionAudiovisual
from catalogo.services import materialization
from catalogo.services.adapter import dominio_a_tmdb
from catalogo.services.materialization import guardar_traducciones, idiomas_traducidos


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
    return {
        "procesadas": procesadas,
        "fallidas": fallidas,
        "pendientes": pendientes().count(),
    }
