"""Qué filas del catálogo hay que volver a pedir a TMDB y cuántas por noche (#180).

Los términos de TMDB no dejan guardar su contenido más de 180 días sin
refrescarlo. `fecha_enriquecimiento` dice cuándo se trajo el detalle por última
vez, así que una fila está *vencida* cuando esa fecha es NULL o muy vieja.

Este módulo decide dos cosas, y ninguna escribe en la base:

- cuántas filas refrescar esta noche (`cuota_nocturna`, aritmética pura), y
- cuáles (`a_refrescar`).

Refrescar de verdad lo hace `materializar(..., forzar=True)`, el único camino de
escritura del catálogo (ver `catalog-materialization`). Lo que este módulo
agrega es qué hacer cuando TMDB responde 404 (Not Found): ver `refrescar_fila`.
"""

import datetime as dt
import logging
import math
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, F, ProtectedError, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from catalogo.exceptions import TMDBNotFound
from catalogo.models import (
    ProduccionAudiovisual,
    ProduccionEmbedding,
    ProduccionTraduccion,
)
from catalogo.services.adapter import dominio_a_tmdb
from catalogo.services.materialization import materializar

logger = logging.getLogger(__name__)

# El tope de TMDB. No es una opción de configuración: es el plazo que hay que
# cumplir. `DIAS_REFRESCO_TMDB` (150) es el largo de la rotación y deja 30 días
# de margen, el equivalente a una semana de noches fallidas.
DIAS_LIMITE = 180
VENTANA_PLAZOS = 30


def detalle_cuota(total, por_dia, techo, dias_rotacion=None):
    """Cuántas filas refrescar esta noche y cuál de los tres números mandó.

    `por_dia[k]` es la cantidad de filas que llegan a los 180 días dentro de `k`
    noches (k = 1 es esta misma noche: ahí van las filas sin fecha y las ya
    vencidas). Es una función pura: no toca la base, así se prueba con números.

    - **rotación** = ceil(total / 150): lo que hay que renovar cada noche para
      que el catálogo entero dé una vuelta cada 150 días.
    - **plazos** = el máximo, sobre k = 1..30, de ceil(acumuladas hasta k / k):
      lo mínimo por noche para que ninguna fila llegue a 180 sin refrescarse
      (primero las que vencen antes).
    - **techo**: que una noche rara no deje al worker ocupado de más.
    """
    dias_rotacion = dias_rotacion or settings.DIAS_REFRESCO_TMDB
    rotacion = math.ceil(total / dias_rotacion)

    plazos, acumuladas = 0, 0
    for k in range(1, VENTANA_PLAZOS + 1):
        acumuladas += por_dia.get(k, 0)
        plazos = max(plazos, math.ceil(acumuladas / k))

    pedida = max(rotacion, plazos)
    if pedida > techo:
        limitada_por = "techo"
    elif plazos > rotacion:
        limitada_por = "plazos"
    else:
        limitada_por = "rotacion"
    return {
        "cuota": min(techo, pedida),
        "rotacion": rotacion,
        "plazos": plazos,
        "techo": techo,
        "limitada_por": limitada_por,
    }


def cuota_nocturna(total, por_dia, techo, dias_rotacion=None):
    """Solo el número de `detalle_cuota`: `min(techo, max(rotación, plazos))`."""
    return detalle_cuota(total, por_dia, techo, dias_rotacion)["cuota"]


def contar_plazos(ahora=None):
    """`(total, por_dia)` con dos consultas, sin importar cuántas filas haya.

    Un `COUNT` del catálogo y un `GROUP BY` por el día en que se enriqueció cada
    fila, solo de las que cumplen 180 días dentro de los próximos 30 (a lo sumo
    31 grupos, con el de las filas sin fecha). El día se pasa a «noches que
    faltan» en Python.

    Se cuenta desde el comienzo del día de enriquecimiento: es más temprano que
    la hora real, así que el error siempre va para el lado seguro (pide un poco
    más por noche, nunca menos).
    """
    ahora = ahora or timezone.now()
    desde = ahora - timedelta(days=DIAS_LIMITE - VENTANA_PLAZOS)
    zona = timezone.get_current_timezone()

    total = ProduccionAudiovisual.objects.count()
    grupos = (
        ProduccionAudiovisual.objects.filter(
            Q(fecha_enriquecimiento__isnull=True) | Q(fecha_enriquecimiento__lte=desde)
        )
        .annotate(dia=TruncDate("fecha_enriquecimiento", tzinfo=zona))
        # `order_by()` vacío: el orden por defecto del modelo (`titulo`) se
        # sumaría al GROUP BY y devolvería una fila por título.
        .order_by()
        .values("dia")
        .annotate(cantidad=Count("pk"))
    )

    por_dia = {}
    for grupo in grupos:
        dia = grupo["dia"]
        if dia is None:
            k = 1
        else:
            vence = dt.datetime.combine(
                dia + timedelta(days=DIAS_LIMITE), dt.time.min, tzinfo=zona
            )
            k = max(1, math.ceil((vence - ahora) / timedelta(days=1)))
        if k <= VENTANA_PLAZOS:
            por_dia[k] = por_dia.get(k, 0) + grupo["cantidad"]
    return total, por_dia


def a_refrescar(cuota):
    """Las `cuota` filas a refrescar esta noche: sin fecha primero, luego las más viejas.

    Puede alcanzar filas más jóvenes que 150 días: es la rotación funcionando.
    Desempata por `pk` para que dos corridas seguidas elijan el mismo orden.
    """
    if cuota <= 0:
        return []
    return list(
        ProduccionAudiovisual.objects.order_by(
            F("fecha_enriquecimiento").asc(nulls_first=True), "pk"
        )[:cuota]
    )


def filas_pasadas_de_180(ahora=None):
    """Filas con fecha que ya pasaron los 180 días: lo que el resumen avisa."""
    ahora = ahora or timezone.now()
    return ProduccionAudiovisual.objects.filter(
        fecha_enriquecimiento__lt=ahora - timedelta(days=DIAS_LIMITE)
    ).count()


def filas_sin_fecha():
    """Filas que nunca se enriquecieron: su edad real se desconoce."""
    return ProduccionAudiovisual.objects.filter(
        fecha_enriquecimiento__isnull=True
    ).count()


# Qué le pasó a cada fila en `refrescar_fila`.
REFRESCADA = "refrescada"
PRIMER_404 = "primer_404"  # solo anotó la fecha; la fila sigue vencida
MISMO_DIA_404 = "mismo_dia_404"  # reintento la misma noche: no cuenta
BORRADA = "borrada"
LAPIDA = "lapida"
FALLIDA = "fallida"  # timeout, 500, 429, 401…: se reintenta mañana

# Todo lo que viene de TMDB y se pierde al pasar a lápida. Lo que queda es la
# identidad (`id_tmdb`, `tipo`) y el estado del propio refresco.
_CAMPOS_DE_CONTENIDO = (
    "titulo",
    "poster",
    "sinopsis",
    "fecha_lanzamiento",
    "reparto",
    "directores",
    "estatus",
    "generos",
    "generos_ids",
    "keywords",
    "calificacion_promedio",
    "cantidad_temporadas",
    "cantidad_episodios",
    "duracion",
)


def refrescar_fila(produccion):
    """Vuelve a pedir una fila a TMDB y devuelve qué pasó (`REFRESCADA`, …).

    Solo el 404 (Not Found) dice que TMDB ya no tiene el título; cualquier otro
    error (timeout, 500, 429, 401) es un refresco fallido y la fila sigue
    vencida para mañana. Nunca lanza: una fila mala no frena a las demás.
    """
    try:
        materializar(produccion.id_tmdb, dominio_a_tmdb(produccion.tipo), forzar=True)
    except TMDBNotFound:
        return _registrar_404(produccion)
    except Exception:
        logger.exception(
            "refrescar_vencidos: falló (%s, %s)", produccion.id_tmdb, produccion.tipo
        )
        return FALLIDA
    return REFRESCADA


def _registrar_404(produccion):
    """Aplica la regla de los dos 404 en noches distintas.

    El primero solo anota la fecha. El segundo cuenta únicamente si la fecha
    anotada es anterior a hoy (en la zona horaria del servidor): un reintento a
    mano la misma noche no puede ser «el segundo».
    """
    try:
        produccion = ProduccionAudiovisual.objects.get(pk=produccion.pk)
    except ProduccionAudiovisual.DoesNotExist:
        # `materializar` ya descartó el cascarón vacío de un id que TMDB no
        # conoce (auditoría F7): no hay nada más que hacer.
        return BORRADA

    hoy = timezone.localdate()
    if produccion.fecha_404 is None:
        produccion.fecha_404 = hoy
        produccion.save(update_fields=["fecha_404"])
        return PRIMER_404
    if produccion.fecha_404 >= hoy:
        return MISMO_DIA_404

    try:
        # Su propio savepoint: en Postgres un error aborta la transacción que
        # lo contiene, y el UPDATE de la lápida solo puede correr una vez
        # deshecho este intento. Revisar y borrar son una sola operación: si
        # alguien calificó o listó el título, `PROTECT` hace fallar el DELETE.
        with transaction.atomic():
            produccion.delete()
    except (ProtectedError, IntegrityError):
        # `IntegrityError`: la calificación llegó entre la lectura de Django y el
        # DELETE; la clave foránea de la base es la última barrera.
        _convertir_en_lapida(produccion)
        return LAPIDA
    return BORRADA


def _convertir_en_lapida(produccion):
    """Deja solo `id_tmdb` y `tipo`: sin contenido de TMDB, traducciones ni vector."""
    with transaction.atomic():
        ProduccionTraduccion.objects.filter(produccion=produccion).delete()
        ProduccionEmbedding.objects.filter(produccion=produccion).delete()
        for nombre in _CAMPOS_DE_CONTENIDO:
            campo = ProduccionAudiovisual._meta.get_field(nombre)
            setattr(produccion, nombre, campo.get_default())
        produccion.disponible_en_tmdb = False
        # La lápida también rota cada 150 días, como cualquier fila.
        produccion.fecha_enriquecimiento = timezone.now()
        produccion.save()


def refrescar_vencidas():
    """La corrida nocturna: elige la cuota, refresca cada fila y devuelve el resumen."""
    ahora = timezone.now()
    total, por_dia = contar_plazos(ahora)
    cuota = detalle_cuota(total, por_dia, settings.CELERY_REFRESCO_TECHO)
    filas = a_refrescar(cuota["cuota"])

    resultados = [refrescar_fila(fila) for fila in filas]
    cuenta = {nombre: resultados.count(nombre) for nombre in set(resultados)}

    pasadas = filas_pasadas_de_180()
    resumen = {
        **cuota,
        "elegidas": len(filas),
        "refrescadas": cuenta.get(REFRESCADA, 0),
        "no_encontradas": sum(
            cuenta.get(r, 0) for r in (PRIMER_404, MISMO_DIA_404, BORRADA, LAPIDA)
        ),
        "borradas": cuenta.get(BORRADA, 0),
        "lapidas": cuenta.get(LAPIDA, 0),
        "fallidas": cuenta.get(FALLIDA, 0),
        "pasadas_de_180": pasadas,
        "sin_fecha": filas_sin_fecha(),
    }

    logger.info("refrescar_vencidos: %s", resumen)
    if pasadas:
        logger.warning(
            "refrescar_vencidos: %s filas siguen con más de %s días sin refrescar",
            pasadas,
            DIAS_LIMITE,
        )
    if resumen["limitada_por"] == "techo":
        logger.warning(
            "refrescar_vencidos: la cuota quedó limitada por el techo (%s); los "
            "plazos pedían %s por noche",
            resumen["techo"],
            max(resumen["rotacion"], resumen["plazos"]),
        )
    return resumen
