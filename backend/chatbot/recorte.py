"""Recorte nocturno de las tarjetas del chat y su rehidratación (#180, PR 3).

Los términos de TMDB no dejan guardar su contenido más de 180 días sin
refrescarlo. Una tarjeta guardada en `Mensaje.tarjetas` lleva título, póster y año
copiados de TMDB, y esa copia no se refresca sola. La salida (decisión del
07/11/2026): cuando el mensaje cumple 180 días, la tarjeta queda como
`{id_tmdb, tipo}` y el historial la reconstruye desde el catálogo local, que sí se
refresca (`catalogo.refrescar_vencidos`). Lo mismo vale para `ya_recomendados`.

Lo usan: la tarea `chatbot.recortar_tarjetas` (`recortar`) y la vista del historial
(`rehidratar`).
"""

from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from catalogo.models import ProduccionAudiovisual
from catalogo.services.recomendado import TIPO_TMDB
from catalogo.services.traducciones import texto_localizado
from chatbot.models import Chat, Mensaje

# Cuántas filas se reescriben por `UPDATE`: `bulk_update` arma un solo SQL por lote
# en vez de uno por fila.
_LOTE = 500
# El bot muestra hasta 3 tarjetas por respuesta (`mostrar_tarjetas`).
_POSICIONES_DE_TARJETA = range(3)
# Lo que sobrevive al recorte: con el id y el tipo se vuelve a encontrar la fila.
_CLAVES_QUE_QUEDAN = ("id_tmdb", "tipo")


def _recortada(tarjeta):
    return {clave: tarjeta[clave] for clave in _CLAVES_QUE_QUEDAN}


def _recortar_mensajes(limite):
    """Recorta las tarjetas de los mensajes anteriores a `limite`. Devuelve cuántos."""
    # `has_key` mira si la clave existe en el JSON. Se prueba en cada posición de
    # tarjeta: así un mensaje ya recortado no se vuelve a leer, ni a escribir.
    con_titulo = Q()
    for posicion in _POSICIONES_DE_TARJETA:
        con_titulo |= Q(**{f"tarjetas__{posicion}__has_key": "titulo"})
    pendientes = Mensaje.objects.filter(con_titulo, fecha_hora__lt=limite)

    cambiados = []
    for mensaje in pendientes.iterator(chunk_size=_LOTE):
        mensaje.tarjetas = [_recortada(t) for t in mensaje.tarjetas]
        cambiados.append(mensaje)
    Mensaje.objects.bulk_update(cambiados, ["tarjetas"], batch_size=_LOTE)
    return len(cambiados)


def _es_vieja(entrada, limite):
    """Una entrada sin fecha, o con una que no se entiende, se trata como vieja."""
    try:
        return date.fromisoformat(entrada["fecha"]) < limite
    except (KeyError, TypeError, ValueError):
        return True


def _sin_titulo_las_viejas(entradas, limite):
    return [
        {k: v for k, v in e.items() if k not in ("titulo", "anio")}
        if _es_vieja(e, limite)
        else e
        for e in entradas
    ]


def _candidatos(limite):
    """Los pk de los chats con algo para recortar. Sin candado: solo detecta."""
    return [
        chat.pk
        for chat in Chat.objects.only("contexto").iterator(chunk_size=_LOTE)
        if (entradas := chat.contexto.get("ya_recomendados", []))
        != _sin_titulo_las_viejas(entradas, limite)
    ]


def _recortar_recomendados(limite):
    """Les quita `titulo` y `anio` a las entradas viejas de `ya_recomendados`."""
    cambiados = 0
    for pk in _candidatos(limite):
        # Cada chat se relee con candado, igual que `guardar_turno`: un turno del
        # usuario a las 04:30 escribe este mismo JSON, y reescribir la copia leída
        # antes le pisaría la tarjeta recién mostrada.
        with transaction.atomic():
            chat = Chat.objects.select_for_update().get(pk=pk)
            entradas = chat.contexto.get("ya_recomendados", [])
            nuevas = _sin_titulo_las_viejas(entradas, limite)
            # Comparar con lo que hay es lo que vuelve idempotente a la tarea: una
            # segunda corrida no encuentra nada distinto y no escribe.
            if nuevas != entradas:
                chat.contexto["ya_recomendados"] = nuevas
                chat.save(update_fields=["contexto"])
                cambiados += 1
    return cambiados


def recortar():
    """La corrida de la noche. Devuelve cuántos mensajes y chats reescribió."""
    dias = timedelta(days=settings.DIAS_DE_TARJETAS)
    ahora = timezone.now()
    return {
        "mensajes": _recortar_mensajes(ahora - dias),
        "chats": _recortar_recomendados(timezone.localdate(ahora) - dias),
    }


def _tarjeta_rehidratada(tarjeta, produccion, idioma):
    """La tarjeta completa desde la fila local, o con `titulo: None` si no sirve."""
    if produccion is None or not produccion.disponible_en_tmdb:
        # Falta la fila o es una lápida (TMDB ya no tiene el título): el panel
        # muestra «Title no longer available», sin enlace.
        return {**_recortada(tarjeta), "titulo": None, "poster": None, "anio": None}
    fecha = produccion.fecha_lanzamiento
    nota = produccion.calificacion_promedio
    return {
        **_recortada(tarjeta),
        "titulo": texto_localizado(produccion, "titulo", idioma),
        "poster": texto_localizado(produccion, "poster", idioma) or None,
        "anio": fecha.year if fecha else None,
        "nota_tmdb": round(nota, 1) if nota else None,
    }


def rehidratar(mensajes, idioma):
    """Completa en memoria las tarjetas recortadas de una página de mensajes.

    Hace como mucho dos consultas por página, sean cuantas sean las tarjetas: una
    para las producciones y otra, del `prefetch_related`, para sus traducciones.
    Sin tarjetas recortadas no consulta nada. Nunca llama a TMDB ni escribe en la
    base: lo guardado sigue recortado.
    """
    pedidas = {
        (t["id_tmdb"], t["tipo"])
        for mensaje in mensajes
        for t in mensaje.tarjetas
        if "titulo" not in t
    }
    if not pedidas:
        return
    # Un `id_tmdb` puede ser una película y una serie a la vez: se trae por id y se
    # separa por tipo en Python.
    producciones = ProduccionAudiovisual.objects.filter(
        id_tmdb__in={id_tmdb for id_tmdb, _ in pedidas}
    ).prefetch_related("traducciones")
    por_clave = {(p.id_tmdb, TIPO_TMDB[p.tipo]): p for p in producciones}
    for mensaje in mensajes:
        mensaje.tarjetas = [
            t
            if "titulo" in t
            else _tarjeta_rehidratada(
                t, por_clave.get((t["id_tmdb"], t["tipo"])), idioma
            )
            for t in mensaje.tarjetas
        ]
