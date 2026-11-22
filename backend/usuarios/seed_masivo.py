"""
Lógica del seed masivo (`python manage.py seed_masivo`).

Pobla la base con cientos de cuentas ficticias y miles de calificaciones y
reseñas coherentes con el catálogo real, rápido: todo va por `bulk_create`, con
UN solo hash de contraseña. Las listas predeterminadas y el chat por defecto se
crean a mano (el `bulk_create` no dispara la señal `post_save` de `Usuario`)
replicando exactamente lo que hace `provisioning.provisionar_recursos_por_defecto`.

Todo es determinista con `semilla`: cada cuenta usa su propio generador
(`Random(f"{semilla}:{nombre_usuario}")`), así que su actividad no depende de
qué otras cuentas existan. El texto de las reseñas sale del corpus versionado
(`corpus_resenas`) y, sin entrada para ese título/idioma/banda, de las
plantillas por género (`seed_data/plantillas_genero.json`) y, si faltan,
de `seed_real.TEXTOS`.
"""

import datetime
import math
import random
from collections import Counter
from contextlib import contextmanager
from heapq import nsmallest

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.hashers import make_password
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from catalogo.models import (
    Calificacion,
    ProduccionAudiovisual,
    Resena,
    TipoProduccion,
)
from chatbot.models import Chat, Mensaje, TipoAutor
from listas.models import ClaveLista, Lista, Tiene, TipoLista
from usuarios import corpus_resenas, seed_real
from usuarios.avatares import AVATAR_IDS_VALIDOS
from usuarios.management.commands.seed import SEED_PASSWORD
from usuarios.models import EstadoCuenta, TipoGenero, Usuario
from usuarios.paises import pais_por_indice
from usuarios.provisioning import (
    CONTEXTO_CHAT_INICIAL,
    nombres_listas_predeterminadas,
)

PREFIJO = "masivo"
DOMINIO = "@filmai.com"
# Cuentas conocidas del seed, con los idiomas documentados.
CUENTAS_CONOCIDAS = (
    ("usuario001", "es"),
    ("usuario002", "en"),
    ("usuario003", "es"),
)
MINIMO_PRODUCCIONES = 20
MINIMO_CALIFICACIONES = 3
MAXIMO_CALIFICACIONES = 300
SIGMA_CALIFICACIONES = 1.0
# Cuentas sin verificar (pendiente) o dadas de baja, a mitades.
PROPORCION_CUENTAS_ANOMALAS = 0.03
PROPORCION_CON_LISTAS_PERSONALIZADAS = 0.6
PROPORCION_CON_CHAT = 0.25
PROPORCION_FAVORITOS = 0.7
MAXIMO_FAVORITOS = 30
# Regla de moderación (AD-01'/CU-017): 1 de cada 7 reseñas nace inactiva.
CADA_N_INACTIVA = 7
LOTE = 2000

NOMBRES = (
    "Lucía Martín Sofía Mateo Valentina Santiago Camila Diego Julieta Nicolás "
    "Paula Joaquín Martina Facundo Carla Tomás Agustina Lucas Florencia Bruno "
    "Emma Oliver Ava Noah Mia Liam Zoe Ethan Chloe Jack Grace Henry Ruby Leo"
).split()
APELLIDOS = (
    "García Fernández López Martínez Rodríguez Gómez Pérez Sánchez Romero Díaz "
    "Torres Ruiz Álvarez Castro Molina Silva Rojas Herrera Smith Johnson "
    "Brown Taylor Wilson Clark Walker Hall Young King Wright Scott Green"
).split()

# Géneros de TMDB (películas y series) con el nombre para las listas temáticas.
GENEROS = {
    28: ("Acción", "Action"),
    12: ("Aventura", "Adventure"),
    16: ("Animación", "Animation"),
    35: ("Comedia", "Comedy"),
    80: ("Crimen", "Crime"),
    99: ("Documental", "Documentary"),
    18: ("Drama", "Drama"),
    10751: ("Familia", "Family"),
    14: ("Fantasía", "Fantasy"),
    36: ("Historia", "History"),
    27: ("Terror", "Horror"),
    10402: ("Música", "Music"),
    9648: ("Misterio", "Mystery"),
    10749: ("Romance", "Romance"),
    878: ("Ciencia ficción", "Science fiction"),
    53: ("Suspenso", "Thriller"),
    10752: ("Bélica", "War"),
    37: ("Western", "Western"),
    10759: ("Acción y aventura", "Action and adventure"),
    10765: ("Ciencia ficción y fantasía", "Sci-fi and fantasy"),
}
PLANTILLAS_LISTA = {
    "es": ("Lo mejor de {g}", "{g} para el finde"),
    "en": ("Best of {g}", "{g} for the weekend"),
}

CHAT = {
    "es": (
        "¿Qué me recomendás para ver esta noche?",
        "¡Claro! Según tus géneros favoritos, te sugiero algo de lo que venís calificando alto.",
        "Dale, mostrame más opciones.",
        "Acá tenés tres opciones que encajan con lo que venís mirando.",
        "Gracias, la primera me interesa.",
        "Buena elección, es de las más queridas de ese género.",
    ),
    "en": (
        "What would you recommend for tonight?",
        "Sure! Based on your favorite genres, here is something close to what you rate highly.",
        "Great, show me more options.",
        "Here are three options that fit what you have been watching.",
        "Thanks, the first one looks good.",
        "Good pick, it is one of the most loved in that genre.",
    ),
}


@contextmanager
def _sin_auto_now(*campos):
    """Desactiva `auto_now_add` de los campos (modelo, nombre) mientras dura.

    `bulk_create` pisa con «ahora» cualquier fecha puesta en un campo
    `auto_now_add`; sin esto habría que hacer un `bulk_update` por tabla para
    repartir las fechas en el pasado.
    """
    campos = [modelo._meta.get_field(nombre) for modelo, nombre in campos]
    originales = [c.auto_now_add for c in campos]
    for campo in campos:
        campo.auto_now_add = False
    try:
        yield
    finally:
        for campo, original in zip(campos, originales, strict=True):
            campo.auto_now_add = original


def _azar(semilla, *partes):
    return random.Random(":".join(str(p) for p in (semilla, *partes)))


def _muestra(azar, indices, pesos, k):
    """`k` índices distintos sin reemplazo, ponderados (Efraimidis-Spirakis)."""
    k = min(k, len(indices))
    if k <= 0:
        return []
    claves = [(-math.log(1.0 - azar.random()) / pesos[i], i) for i in indices]
    return [i for _, i in nsmallest(k, claves)]


def cantidad_calificaciones(azar, media, maximo=MAXIMO_CALIFICACIONES):
    """Cola larga: log-normal con esa media, entre 3 y `maximo`."""
    mu = math.log(max(media, 1)) - SIGMA_CALIFICACIONES**2 / 2
    valor = round(azar.lognormvariate(mu, SIGMA_CALIFICACIONES))
    return max(MINIMO_CALIFICACIONES, min(maximo, valor))


class Catalogo:
    """El catálogo elegible, en arreglos paralelos y en orden estable."""

    def __init__(self, semilla):
        filas = list(
            ProduccionAudiovisual.objects.filter(
                disponible_en_tmdb=True, poster__startswith="/"
            )
            .exclude(titulo="")
            .order_by("id_tmdb", "tipo")
            .values_list(
                "id", "id_tmdb", "tipo", "generos_ids", "calificacion_promedio"
            )
        )
        if len(filas) < MINIMO_PRODUCCIONES:
            raise CommandError(
                f"El catálogo tiene {len(filas)} producciones elegibles (con "
                f"póster de TMDB); hacen falta {MINIMO_PRODUCCIONES}. Corré "
                "`seed_catalogo` primero."
            )
        buzz = _azar(semilla, "popularidad")
        self.pk = [f[0] for f in filas]
        self.id_tmdb = [f[1] for f in filas]
        self.tipo = [f[2] for f in filas]
        self.generos = [set(f[3] or ()) for f in filas]
        self.promedio = [f[4] for f in filas]
        # El modelo no guarda `vote_count`: la popularidad se aproxima con el
        # promedio de TMDB al cuadrado por un factor log-normal sembrado.
        self.peso = [
            (max(f[4] or 7.0, 1.0) / 10) ** 2 * buzz.lognormvariate(0, 0.9)
            for f in filas
        ]
        self.indices = list(range(len(filas)))
        cuenta = Counter(g for gs in self.generos for g in gs if g in GENEROS)
        self.generos_tematicos = sorted(g for g, n in cuenta.items() if n >= 3)
        self.cuenta_generos = cuenta
        self.por_genero = {
            g: [i for i in self.indices if g in self.generos[i]]
            for g in self.generos_tematicos
        }


def _crear_cuentas(faltantes, semilla, hash_clave, hoy):
    """Arma (sin guardar) los `Usuario` de las cuentas que faltan."""
    cuentas = []
    for numero, (nombre_usuario, idioma) in faltantes:
        azar = _azar(semilla, "cuenta", nombre_usuario)
        if nombre_usuario.startswith(PREFIJO) and (
            azar.random() < PROPORCION_CUENTAS_ANOMALAS
        ):
            estado = azar.choice((EstadoCuenta.PENDIENTE, EstadoCuenta.BAJA))
        else:
            estado = EstadoCuenta.ACTIVA
        dias_registro = azar.randint(60, 700)
        cuentas.append(
            Usuario(
                nombre_usuario=nombre_usuario,
                correo=f"{nombre_usuario}{DOMINIO}",
                password=hash_clave,
                nombre=azar.choice(NOMBRES),
                apellido=azar.choice(APELLIDOS),
                fecha_nacimiento=hoy
                - datetime.timedelta(days=azar.randint(18 * 365, 60 * 365)),
                genero=azar.choice(TipoGenero.values),
                pais=pais_por_indice(numero),
                estado=estado,
                fecha_registro=hoy - datetime.timedelta(days=dias_registro),
                fecha_aceptacion_terminos=timezone.now()
                - datetime.timedelta(days=dias_registro),
                avatar_id=azar.choice(sorted(AVATAR_IDS_VALIDOS)),
                idioma=idioma,
            )
        )
    return cuentas


def _planificar(usuario, catalogo, semilla, calificaciones_medias, hoy):
    """Qué hace una cuenta: calificaciones, estados, favoritos y listas.

    Devuelve un dict con índices del catálogo; no toca la base.
    """
    azar = _azar(semilla, usuario.nombre_usuario)
    idioma = usuario.idioma or "es"
    cantidad = cantidad_calificaciones(azar, calificaciones_medias)
    cantidad = min(cantidad, len(catalogo.indices))
    resto = len(catalogo.indices) - cantidad
    pendientes_n = min(resto, azar.randint(0, min(40, 2 + cantidad // 2)))
    viendo_n = min(resto - pendientes_n, azar.randint(0, 3))
    extras_n = min(
        resto - pendientes_n - viendo_n, azar.randint(0, min(5, cantidad // 5 + 1))
    )

    # Gustos: 2 a 4 géneros, los más frecuentes del catálogo pesan más.
    candidatos = catalogo.generos_tematicos
    gustos = set()
    if candidatos:
        pesos_genero = {g: float(catalogo.cuenta_generos[g]) for g in candidatos}
        gustos = set(_muestra(azar, candidatos, pesos_genero, azar.randint(2, 4)))
    pesos = [
        peso * (0.4 if not (gs & gustos) else 1 + 3 * len(gs & gustos))
        for peso, gs in zip(catalogo.peso, catalogo.generos, strict=True)
    ]
    elegidas = _muestra(
        azar, catalogo.indices, pesos, cantidad + pendientes_n + viendo_n + extras_n
    )
    azar.shuffle(elegidas)
    vistas = elegidas[:cantidad]
    pendientes = elegidas[cantidad : cantidad + pendientes_n]
    viendo = elegidas[cantidad + pendientes_n : cantidad + pendientes_n + viendo_n]
    extras = elegidas[cantidad + pendientes_n + viendo_n :]

    sesgo = azar.gauss(0, 0.7)
    dias_registro = (hoy - usuario.fecha_registro).days
    calificaciones = []
    for i in vistas:
        afin = bool(catalogo.generos[i] & gustos)
        base = catalogo.promedio[i] or 7.0
        valor = round(base + (0.6 if afin else -0.6) + sesgo + azar.gauss(0, 1.2))
        fecha = usuario.fecha_registro + datetime.timedelta(
            days=azar.randint(0, max(dias_registro, 1))
        )
        calificaciones.append((i, max(1, min(10, valor)), fecha))

    altas = [c[0] for c in calificaciones if c[1] >= 9]
    favoritos = [i for i in altas if azar.random() < PROPORCION_FAVORITOS]
    favoritos = favoritos[:MAXIMO_FAVORITOS]

    personalizadas = []
    if len(gustos) >= 2 and azar.random() < PROPORCION_CON_LISTAS_PERSONALIZADAS:
        temas = sorted(gustos)
        azar.shuffle(temas)
        for orden, genero in enumerate(temas[:2], start=1):
            nombre_genero = GENEROS[genero][0 if idioma == "es" else 1]
            nombre = PLANTILLAS_LISTA[idioma][orden - 1].format(g=nombre_genero)
            items = _muestra(
                azar, catalogo.por_genero[genero], catalogo.peso, azar.randint(4, 8)
            )
            personalizadas.append((nombre, orden, items))

    def reciente():
        return hoy - datetime.timedelta(days=azar.randint(0, 60))

    return {
        "usuario": usuario,
        "idioma": idioma,
        "calificaciones": calificaciones,
        "favoritos": favoritos,
        "pendientes": [(i, reciente()) for i in pendientes],
        "viendo": [(i, reciente()) for i in viendo],
        "extras": [(i, reciente()) for i in extras],
        "personalizadas": personalizadas,
        "con_chat": azar.random() < PROPORCION_CON_CHAT,
        "azar": azar,
    }


def _texto(catalogo, i, idioma, valor, corpus, azar):
    """Texto del corpus para (título, idioma, banda), o plantilla de respaldo."""
    banda = corpus_resenas.banda_de_nota(valor)
    tipo = corpus_resenas.TIPO_MODELO_A_CORPUS[catalogo.tipo[i]]
    textos = corpus.get((catalogo.id_tmdb[i], tipo, idioma, banda))
    if textos:
        return azar.choice(textos)
    por_genero = corpus_resenas.plantillas_genero()
    generos = sorted(g for g in catalogo.generos[i] if g in por_genero)
    if generos:
        frases = por_genero[azar.choice(generos)].get(idioma, {}).get(banda)
        if frases:
            es_serie = catalogo.tipo[i] == TipoProduccion.SERIE
            nombre = (
                ("serie" if es_serie else "película")
                if idioma == "es"
                else ("series" if es_serie else "movie")
            )
            return azar.choice(frases).replace("{t}", nombre)
    es_serie = catalogo.tipo[i] == TipoProduccion.SERIE
    nombre = (
        ("serie" if es_serie else "película")
        if idioma == "es"
        else ("series" if es_serie else "movie")
    )
    return azar.choice(seed_real.TEXTOS[idioma][banda]).format(t=nombre)


def reiniciar(stdout):
    """Borra todo lo que no es del staff; conserva staff y catálogo."""
    ajenos = {"usuario__is_staff": False}
    for etiqueta, consulta in (
        ("mensajes", Mensaje.objects.filter(chat__usuario__is_staff=False)),
        ("reseñas", Resena.objects.filter(calificacion__usuario__is_staff=False)),
        ("calificaciones", Calificacion.objects.filter(**ajenos)),
        ("ítems de lista", Tiene.objects.filter(lista__usuario__is_staff=False)),
        ("chats", Chat.objects.filter(**ajenos)),
        ("listas", Lista.objects.filter(**ajenos)),
        ("correos", EmailAddress.objects.filter(user__is_staff=False)),
        ("cuentas sociales", SocialAccount.objects.filter(user__is_staff=False)),
        ("usuarios", Usuario.objects.filter(is_staff=False)),
    ):
        consulta.delete()
        stdout.write(f"  borrado: {etiqueta}")


def sembrar(
    stdout,
    usuarios=500,
    semilla=42,
    reiniciar_todo=False,
    calificaciones_medias=38,
    porcentaje_resenas=80,
    corpus=None,
):
    """Corre el seed masivo dentro de una transacción; devuelve los conteos."""
    if usuarios < 0 or calificaciones_medias < 1:
        raise CommandError("--usuarios y --calificaciones-medias deben ser positivos.")
    if not 0 <= porcentaje_resenas <= 100:
        raise CommandError("--porcentaje-resenas va de 0 a 100.")
    corpus = corpus_resenas.cargar_corpus() if corpus is None else corpus
    hoy = timezone.localdate()
    cuentas_pedidas = [
        *CUENTAS_CONOCIDAS,
        *(
            (f"{PREFIJO}{n:04d}", "es" if n % 2 else "en")
            for n in range(1, usuarios + 1)
        ),
    ]
    resumen = Counter()
    with transaction.atomic():
        catalogo = Catalogo(semilla)
        if reiniciar_todo:
            stdout.write("Reiniciando (se conservan staff y catálogo)…")
            reiniciar(stdout)
        existentes = set(
            Usuario.objects.filter(
                correo__in=[f"{n}{DOMINIO}" for n, _ in cuentas_pedidas]
            ).values_list("nombre_usuario", flat=True)
        )
        faltantes = [
            (numero, cuenta)
            for numero, cuenta in enumerate(cuentas_pedidas)
            if cuenta[0] not in existentes
        ]
        stdout.write(
            f"Cuentas pedidas: {len(cuentas_pedidas)}; ya existían "
            f"{len(existentes)}; a crear: {len(faltantes)}."
        )
        if not faltantes:
            return resumen

        hash_clave = make_password(SEED_PASSWORD)
        nuevas = _crear_cuentas(faltantes, semilla, hash_clave, hoy)
        with _sin_auto_now((Usuario, "fecha_registro")):
            Usuario.objects.bulk_create(nuevas, batch_size=LOTE)
        resumen["usuarios"] = len(nuevas)
        EmailAddress.objects.bulk_create(
            [
                EmailAddress(
                    user=u,
                    email=u.correo,
                    verified=u.estado != EstadoCuenta.PENDIENTE,
                    primary=True,
                )
                for u in nuevas
            ],
            batch_size=LOTE,
        )
        stdout.write(f"  {len(nuevas)} cuentas creadas.")

        # Actividad: solo las cuentas activas (una pendiente no entró nunca).
        planes = []
        for n, usuario in enumerate(nuevas, start=1):
            if usuario.estado == EstadoCuenta.ACTIVA:
                planes.append(
                    _planificar(usuario, catalogo, semilla, calificaciones_medias, hoy)
                )
            if n % 100 == 0:
                stdout.write(f"  actividad planificada: {n}/{len(nuevas)}")

        listas = []
        for usuario in nuevas:
            for clave, nombre in nombres_listas_predeterminadas().items():
                listas.append(
                    Lista(
                        usuario=usuario,
                        nombre=nombre,
                        tipo=TipoLista.PREDETERMINADA,
                        clave=clave,
                    )
                )
        for plan in planes:
            for nombre, orden, _items in plan["personalizadas"]:
                listas.append(
                    Lista(usuario=plan["usuario"], nombre=nombre, orden=orden)
                )
        Lista.objects.bulk_create(listas, batch_size=LOTE)
        resumen["listas"] = len(listas)
        por_lista = {(le.usuario_id, le.clave or le.nombre): le for le in listas}

        chats = [
            Chat(usuario=u, titulo="Chat", contexto=CONTEXTO_CHAT_INICIAL)
            for u in nuevas
        ]
        with _sin_auto_now((Chat, "fecha")):
            for chat, usuario in zip(chats, nuevas, strict=True):
                chat.fecha = usuario.fecha_registro
            Chat.objects.bulk_create(chats, batch_size=LOTE)
        resumen["chats"] = len(chats)

        calificaciones = []
        dueno = []
        for plan in planes:
            for i, valor, fecha in plan["calificaciones"]:
                calificaciones.append(
                    Calificacion(
                        usuario=plan["usuario"],
                        produccion_id=catalogo.pk[i],
                        valor=valor,
                        fecha=fecha,
                    )
                )
                dueno.append((plan, i))
        with _sin_auto_now((Calificacion, "fecha")):
            Calificacion.objects.bulk_create(calificaciones, batch_size=LOTE)
        resumen["calificaciones"] = len(calificaciones)
        stdout.write(f"  {len(calificaciones)} calificaciones.")

        # Reseñas: exactamente el porcentaje pedido, repartido al azar.
        cantidad = round(len(calificaciones) * porcentaje_resenas / 100)
        con_resena = sorted(
            _azar(semilla, "resenas").sample(range(len(calificaciones)), cantidad)
        )
        azar_texto = _azar(semilla, "textos")
        resenas = []
        for orden, indice in enumerate(con_resena, start=1):
            calificacion = calificaciones[indice]
            plan, i = dueno[indice]
            resenas.append(
                Resena(
                    calificacion=calificacion,
                    texto=_texto(
                        catalogo,
                        i,
                        plan["idioma"],
                        calificacion.valor,
                        corpus,
                        azar_texto,
                    ),
                    activa=orden % CADA_N_INACTIVA != 0,
                    fecha=min(
                        hoy,
                        calificacion.fecha
                        + datetime.timedelta(days=azar_texto.randint(0, 20)),
                    ),
                )
            )
        with _sin_auto_now((Resena, "fecha")):
            Resena.objects.bulk_create(resenas, batch_size=LOTE)
        resumen["resenas"] = len(resenas)
        resumen["resenas_inactivas"] = sum(not r.activa for r in resenas)
        stdout.write(f"  {len(resenas)} reseñas.")

        resumen["items"] = _crear_items(planes, catalogo, por_lista, hoy)
        resumen["mensajes"] = _crear_mensajes(planes, chats, hoy)
        stdout.write(
            f"  {resumen['items']} ítems de lista, {resumen['mensajes']} mensajes."
        )
    return resumen


def _crear_items(planes, catalogo, por_lista, hoy):
    """Vistas, Favoritos, Pendientes, Viendo y personalizadas, con bulk."""

    def momento(fecha):
        return timezone.make_aware(
            datetime.datetime.combine(fecha, datetime.time(12, 0))
        )

    items = []
    for plan in planes:
        uid = plan["usuario"].pk
        fechas = {i: f for i, _v, f in plan["calificaciones"]}
        # Calificada ⇒ Vistas; Favoritos solo con nota ≥ 9 (ya filtrado).
        for i, fecha in fechas.items():
            items.append((por_lista[(uid, ClaveLista.VISTAS)], i, fecha))
        for i in plan["favoritos"]:
            items.append((por_lista[(uid, ClaveLista.FAVORITOS)], i, fechas[i]))
        for i, fecha in plan["extras"]:
            items.append((por_lista[(uid, ClaveLista.VISTAS)], i, fecha))
        for i, fecha in plan["pendientes"]:
            items.append((por_lista[(uid, ClaveLista.PENDIENTES)], i, fecha))
        for i, fecha in plan["viendo"]:
            items.append((por_lista[(uid, ClaveLista.VIENDO)], i, fecha))
        for nombre, _orden, indices in plan["personalizadas"]:
            for i in indices:
                items.append((por_lista[(uid, nombre)], i, hoy))
    objetos = [
        Tiene(lista=lista, produccion_id=catalogo.pk[i], fecha_agregado=momento(f))
        for lista, i, f in items
    ]
    with _sin_auto_now((Tiene, "fecha_agregado")):
        Tiene.objects.bulk_create(objetos, batch_size=LOTE)
    return len(objetos)


def _crear_mensajes(planes, chats, hoy):
    """Unos pocos mensajes (2 a 6) para un subconjunto de cuentas."""
    chat_de = {c.usuario_id: c for c in chats}
    mensajes = []
    for plan in planes:
        if not plan["con_chat"]:
            continue
        azar = plan["azar"]
        chat = chat_de[plan["usuario"].pk]
        textos = CHAT[plan["idioma"]]
        inicio = timezone.now() - datetime.timedelta(
            days=azar.randint(0, 30), minutes=azar.randint(0, 600)
        )
        for n in range(azar.randint(2, 6)):
            mensajes.append(
                Mensaje(
                    chat=chat,
                    autor=TipoAutor.USUARIO if n % 2 == 0 else TipoAutor.CHATBOT,
                    texto=textos[n % len(textos)],
                    fecha_hora=inicio + datetime.timedelta(minutes=n),
                )
            )
    with _sin_auto_now((Mensaje, "fecha_hora")):
        Mensaje.objects.bulk_create(mensajes, batch_size=LOTE)
    return len(mensajes)
