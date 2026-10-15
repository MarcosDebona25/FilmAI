"""
Datos de desarrollo con correspondencia real (`seed`, modo por defecto).

Las producciones salen de TMDB (`materializar`), así que cada tarjeta lleva a
su ficha verdadera: las sintéticas de Faker tenían `id_tmdb` bajos que chocaban
con títulos reales y la ficha mostraba otra película. Sobre ese catálogo se
generan calificaciones, reseñas y listas con sentido: cada cuenta tiene gustos
(géneros), puntúa cerca de la nota de TMDB y escribe en su idioma.
"""

import datetime
import random
import time

from django.utils import timezone

from catalogo.models import Calificacion, ProduccionAudiovisual, Resena, TipoProduccion
from catalogo.services.materialization import materializar
from catalogo.services.tmdb import get_catalog_service
from listas.models import ClaveLista, Lista, Tiene, TipoLista
from listas.services import agregar_a_vistas

# Géneros de TMDB por tipo; se toman los más votados de cada uno.
PLAN_CATALOGO = {
    "movie": [878, 18, 35, 16, 27, 28, 53, 10749, 80],
    "tv": [18, 35, 10765, 80, 16, 9648],
}
POR_GENERO = 4
# Debajo de esto no hay con qué armar actividad con sentido.
MINIMO_REALES = 20
PAUSA_TMDB = 0.4

# Un perfil por cuenta, en el orden de `usuario001..003`.
PERFILES = [
    {
        "generos": {878, 28, 53, 10765},
        "calificaciones": 15,
        "pendientes": 6,
        "listas": {
            "Noches de ciencia ficción": {878, 10765},
            "Para ver con amigos": {28, 35},
        },
    },
    {
        "generos": {16, 35, 10751, 12},
        "calificaciones": 14,
        "pendientes": 5,
        "listas": {
            "Family movie night": {16, 10751},
            "Binge worthy series": {35, 10765, 16},
        },
    },
    {
        "generos": {18, 80, 9648, 10749},
        "calificaciones": 15,
        "pendientes": 6,
        "listas": {
            "Dramas que me marcaron": {18, 10749},
            "Series para maratonear": {80, 9648, 18},
        },
    },
]

TEXTOS = {
    "es": {
        "alta": [
            "Una de esas {t} que se quedan con vos días después de verlas. La dirección y el ritmo están muy cuidados y el final cierra con fuerza.",
            "Me encantó. Ya la había visto antes y volví a verla: aguanta perfecto el paso del tiempo. Se la recomiendo a cualquiera.",
            "Excelente. Los personajes están muy bien escritos y la historia nunca se siente estirada. De lo mejor que vi este año.",
            "Muy buena. Tiene momentos memorables y una banda sonora que acompaña sin sobrar. La volvería a ver sin dudarlo.",
        ],
        "media": [
            "Está bien: entretiene y tiene buenas ideas, pero se queda a mitad de camino y algunas partes se sienten largas.",
            "Correcta. Tiene un buen arranque y buenas actuaciones, aunque el desarrollo no termina de convencerme.",
            "Me gustó a medias. Lo mejor es la ambientación; la trama es bastante previsible para lo que promete.",
        ],
        "baja": [
            "No logró engancharme. El ritmo es irregular y el final me dejó con ganas de más. Quizás no era para mí.",
            "Esperaba bastante más. Tiene un par de buenas escenas, pero en general se siente desaprovechada.",
        ],
    },
    "en": {
        "alta": [
            "One of those {t} that stays with you for days. The direction and pacing are great and the ending lands.",
            "Loved it. I had seen it before and rewatched it: it holds up perfectly. Easy recommendation.",
            "Excellent. Well written characters and the story never drags. One of the best things I watched this year.",
            "Really good. Memorable moments and a score that supports the story without taking over. Would watch again.",
        ],
        "media": [
            "It's fine: entertaining with good ideas, but it stalls halfway and some stretches feel long.",
            "Decent. Strong start and good performances, though the middle didn't fully convince me.",
            "Liked it, kind of. The setting is the best part; the plot is predictable for what it promises.",
        ],
        "baja": [
            "Couldn't get into it. The pacing is uneven and the ending left me wanting more. Maybe it just wasn't for me.",
            "Expected a lot more. A couple of good scenes, but overall it feels like a missed opportunity.",
        ],
    },
}


def reales():
    """Producciones con póster de TMDB (ruta `/xxx.jpg`); las de Faker traen una URL."""
    return ProduccionAudiovisual.objects.filter(poster__startswith="/")


def materializar_catalogo(stdout):
    """Trae de TMDB los más votados por género y los materializa. No borra nada.

    Una falla puntual (429 (Too Many Requests), red) se informa y sigue: el
    pool se mide al final. Es idempotente, `materializar` no duplica filas.
    """
    servicio = get_catalog_service()
    for tipo, generos in PLAN_CATALOGO.items():
        for genero in generos:
            try:
                resultados = (
                    servicio.discover(
                        tipo, genero=genero, page=1, sort_by="vote_count.desc"
                    ).get("results")
                    or []
                )
            except Exception as error:
                stdout.write(f"  discover {tipo}/{genero} falló: {error}")
                continue
            for resultado in resultados[:POR_GENERO]:
                try:
                    materializar(resultado["id"], tipo)
                except Exception as error:
                    stdout.write(f"  {tipo} {resultado.get('id')} falló: {error}")
                time.sleep(PAUSA_TMDB)


def _texto(idioma, valor, produccion, azar):
    banda = "alta" if valor >= 8 else "media" if valor >= 5 else "baja"
    es_serie = produccion.tipo == TipoProduccion.SERIE
    nombre = (
        ("serie" if es_serie else "película")
        if idioma == "es"
        else ("series" if es_serie else "movie")
    )
    return azar.choice(TEXTOS[idioma][banda]).format(t=nombre)


def generar_actividad(usuarios):
    """Calificaciones, reseñas y listas con sentido para cada cuenta.

    Reglas: calificada ⇒ en Vistas (como la API), Favoritos con nota ≥ 9,
    Pendientes sin lo ya visto, 1 de cada 7 reseñas inactiva (moderación,
    AD-01'/CU-017). Es determinista por cuenta.
    """
    pool = list(reales().order_by("id_tmdb"))
    ahora = timezone.now()
    resenas = 0
    for indice, usuario in enumerate(usuarios):
        perfil = PERFILES[indice % len(PERFILES)]
        azar = random.Random(usuario.nombre_usuario)
        idioma = usuario.idioma or "es"
        afines = [p for p in pool if set(p.generos_ids) & perfil["generos"]]
        resto = [p for p in pool if p not in afines]
        azar.shuffle(afines)
        azar.shuffle(resto)
        de_gusto = max(perfil["calificaciones"] - 4, 0)
        vistas = afines[:de_gusto] + resto[:4]
        pendientes = afines[de_gusto:][: perfil["pendientes"]]

        for produccion in vistas:
            base = round(produccion.calificacion_promedio or 7)
            ajuste = 1 if set(produccion.generos_ids) & perfil["generos"] else -1
            valor = max(1, min(10, base + ajuste + azar.choice([-1, 0, 0, 1])))
            calificacion = Calificacion.objects.create(
                usuario=usuario, produccion=produccion, valor=valor
            )
            dias = datetime.timedelta(days=azar.randint(1, 60))
            Calificacion.objects.filter(pk=calificacion.pk).update(
                fecha=(ahora - dias).date()
            )
            agregar_a_vistas(usuario, produccion)
            if azar.random() < 0.65:
                resena = Resena.objects.create(
                    calificacion=calificacion,
                    texto=_texto(idioma, valor, produccion, azar),
                )
                resenas += 1
                if resenas % 7 == 0:
                    resena.activa = False
                    resena.save(update_fields=["activa"])

        # Un par de vistas marcadas a mano, sin calificar.
        for produccion in resto[4:6]:
            agregar_a_vistas(usuario, produccion)

        favoritos = Lista.objects.get(usuario=usuario, clave=ClaveLista.FAVORITOS)
        for calificacion in Calificacion.objects.filter(usuario=usuario, valor__gte=9):
            Tiene.objects.get_or_create(
                lista=favoritos, produccion=calificacion.produccion
            )
        pendientes_lista = Lista.objects.get(
            usuario=usuario, clave=ClaveLista.PENDIENTES
        )
        for produccion in pendientes:
            vista = Tiene.objects.filter(
                lista__usuario=usuario,
                lista__clave=ClaveLista.VISTAS,
                produccion=produccion,
            ).exists()
            if not vista:
                Tiene.objects.get_or_create(
                    lista=pendientes_lista, produccion=produccion
                )

        orden = Lista.objects.filter(
            usuario=usuario, tipo=TipoLista.PERSONALIZADA
        ).count()
        for nombre, generos in perfil["listas"].items():
            orden += 1
            lista = Lista.objects.create(usuario=usuario, nombre=nombre, orden=orden)
            for produccion in [p for p in pool if set(p.generos_ids) & generos][:6]:
                Tiene.objects.get_or_create(lista=lista, produccion=produccion)
