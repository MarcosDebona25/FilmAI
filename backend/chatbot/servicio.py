"""Lo que el chat guarda y lee de la base, fuera del turno en sí.

Lo usan: la vista SSE (PR 5) para guardar cada turno y la vista del historial.
Es código sync, como todo el ORM: la vista async lo llama a través de `en_hilo`.
"""

from django.db import transaction
from django.utils import timezone

from catalogo.models import ProduccionAudiovisual
from catalogo.services.recomendado import TIPO_TMDB
from chatbot.models import Chat, Mensaje, TipoAutor

# Lo que el prompt necesita de cada tarjeta: `titulo` y `anio` para nombrarla,
# `id_tmdb` y `tipo` para no repetirla. El póster no lo lee nadie.
_CLAVES_RECORDADAS = ("id_tmdb", "tipo", "titulo", "anio")
# Unos 10 turnos de 3 tarjetas: el doble de lo que cubren los 10 mensajes de
# historial que recibe el modelo (SDD del 28/10/2026).
TOPE_RECOMENDADOS = 30


def fecha_de_hoy():
    """La fecha (ISO) que se anota en cada entrada de `ya_recomendados`.

    Sirve para recortar a los 180 días lo que quedó de TMDB (`chatbot.recorte`).
    Un solo lugar para escribirla: `sumar_recomendados` la llama cada vez que una
    tarjeta se muestra, sea la primera o una repetida.
    """
    return timezone.localdate().isoformat()


def guardar_turno(chat, texto, resultado):
    """Guarda la pregunta, la respuesta y lo recomendado, todo o nada.

    Devuelve `(pregunta, respuesta)`: el evento `fin` lleva los dos ids. No
    atrapa errores; si la base falla, la vista responde `chat_unavailable`.
    """
    with transaction.atomic():
        # Se vuelve a leer: el `chat` que llega lo cargó la vista al empezar el
        # turno, y `contexto` pudo cambiar desde entonces. `select_for_update`
        # además bloquea la fila hasta el COMMIT, para que dos guardados no se
        # pisen la lista (el candado del PR 5 ya lo evita; esto es la segunda red).
        chat = Chat.objects.select_for_update().get(pk=chat.pk)
        pregunta = Mensaje.objects.create(
            chat=chat, autor=TipoAutor.USUARIO, texto=texto
        )
        respuesta = Mensaje.objects.create(
            chat=chat,
            autor=TipoAutor.CHATBOT,
            texto=resultado.texto,
            tarjetas=resultado.tarjetas,
        )
        chat.contexto["ya_recomendados"] = sumar_recomendados(
            chat.contexto.get("ya_recomendados", []), resultado.tarjetas
        )
        chat.save(update_fields=["contexto"])
    return pregunta, respuesta


def sumar_recomendados(previas, tarjetas):
    """Las tarjetas nuevas al final, sin repetir, y solo las últimas 30.

    La lista va de la más vieja a la más nueva. Un título que se repite sale de
    donde estaba y pasa al final: se mostró de nuevo, así que es reciente. La
    clave es `(id_tmdb, tipo)` porque TMDB numera películas y series por separado.
    Cada entrada nueva lleva la `fecha` de hoy, y una repetida la renueva.
    """
    nuevas = {}
    hoy = fecha_de_hoy()
    for tarjeta in tarjetas:
        recordada = {clave: tarjeta[clave] for clave in _CLAVES_RECORDADAS}
        recordada["fecha"] = hoy
        # Un dict conserva el orden de inserción: un repetido del mismo turno
        # queda una sola vez, en su primer lugar.
        nuevas.setdefault((tarjeta["id_tmdb"], tarjeta["tipo"]), recordada)
    viejas = [t for t in previas if (t["id_tmdb"], t["tipo"]) not in nuevas]
    return (viejas + list(nuevas.values()))[-TOPE_RECOMENDADOS:]


def historial_de(usuario):
    """Los mensajes del usuario. Sin chat no hay mensajes: vuelve vacío.

    El orden lo pone la paginación de la vista.
    """
    return Mensaje.objects.filter(chat__usuario=usuario)


def titulos_recordados(ya_recomendados):
    """Los `{titulo, anio}` de `ya_recomendados` para el prompt.

    Las entradas recortadas (sin `titulo`, ver `chatbot.recorte`) se resuelven desde
    el catálogo con una sola consulta, con el título canónico (en inglés): resolver
    el idioma pediría otra consulta por las traducciones, y al modelo le alcanza
    para no repetir. Un id que ya no está en el catálogo, o es una lápida, queda
    afuera de la línea «Ya recomendados» pero sigue en la lista que evita repetir.
    """
    faltan = {t["id_tmdb"] for t in ya_recomendados if "titulo" not in t}
    producciones = {}
    if faltan:
        filas = ProduccionAudiovisual.objects.filter(
            id_tmdb__in=faltan, disponible_en_tmdb=True
        ).only("id_tmdb", "tipo", "titulo", "fecha_lanzamiento")
        producciones = {(p.id_tmdb, TIPO_TMDB[p.tipo]): p for p in filas}

    titulos = []
    for entrada in ya_recomendados:
        if "titulo" in entrada:
            titulos.append({"titulo": entrada["titulo"], "anio": entrada["anio"]})
            continue
        produccion = producciones.get((entrada["id_tmdb"], entrada["tipo"]))
        if produccion is not None and produccion.titulo:
            fecha = produccion.fecha_lanzamiento
            titulos.append(
                {"titulo": produccion.titulo, "anio": fecha.year if fecha else None}
            )
    return titulos
