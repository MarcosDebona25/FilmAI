"""Endpoints autenticados para gestionar listas e ítems del usuario."""

from collections import defaultdict
from typing import ClassVar

from django.db import IntegrityError, transaction
from django.db.models import (
    BigIntegerField,
    Case,
    CharField,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    Func,
    IntegerField,
    Max,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
    Window,
)
from django.db.models.functions import (
    Cast,
    Coalesce,
    Collate,
    Concat,
    Lower,
    LPad,
    NullIf,
    RowNumber,
)
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.models import Calificacion, ProduccionTraduccion, TipoProduccion
from catalogo.presupuesto import TopesTMDBMixin
from catalogo.services.adapter import tmdb_a_dominio
from catalogo.services.browse import NOTAS
from catalogo.services.materialization import materializar
from catalogo.services.traducciones import texto_localizado
from filmai.errores.base import ExcepcionAPI
from filmai.idioma import idioma_efectivo
from filmai.throttles import EscrituraThrottle

from .exceptions import (
    CalificacionImpideQuitarDeVistas,
    ItemDuplicado,
    ListaPredeterminadaProtegida,
    NombreListaDuplicado,
)
from .models import (
    MAX_ITEMS_POR_LISTA,
    MAX_LISTAS_PERSONALIZADAS,
    ClaveLista,
    Lista,
    Tiene,
    TipoLista,
)
from .pagination import ListaItemCursorPagination
from .serializers import (
    AgregarItemSerializer,
    ListaItemSerializer,
    ListaItemsQuerySerializer,
    ListaResumenSerializer,
    NombreListaSerializer,
    OrdenListasSerializer,
    PertenenciaQuerySerializer,
    QuitarItemQuerySerializer,
)
from .services import quitar_de_pendientes

_ORDEN_PREDETERMINADAS = Case(
    When(clave=ClaveLista.FAVORITOS, tipo=TipoLista.PREDETERMINADA, then=Value(0)),
    When(clave=ClaveLista.PENDIENTES, tipo=TipoLista.PREDETERMINADA, then=Value(1)),
    When(clave=ClaveLista.VISTAS, tipo=TipoLista.PREDETERMINADA, then=Value(2)),
    default=Value(3),
    output_field=IntegerField(),
)

# Política visual de la ListCard. Cambiar este valor ajusta la cantidad máxima
# que expone la API, sin convertirlo en una preferencia del cliente HTTP.
_MAX_PREVIEW_POSTERS = 5


def _listas_del_usuario(request, *, pertenencia=None):
    """Lista resúmenes con contadores, preview y pertenencia opcional."""
    listas = (
        Lista.objects.filter(usuario=request.user, activa=True)
        .annotate(
            cantidad_items=Count("items"),
            cantidad_peliculas=Count(
                "items", filter=Q(items__produccion__tipo=TipoProduccion.PELICULA)
            ),
            cantidad_series=Count(
                "items", filter=Q(items__produccion__tipo=TipoProduccion.SERIE)
            ),
        )
        .annotate(orden_predeterminada=_ORDEN_PREDETERMINADAS)
        # Las predeterminadas, fijas adelante; las personalizadas, en el orden
        # que eligió el usuario (L-02).
        .order_by("orden_predeterminada", "orden", "id")
    )

    if pertenencia is not None:
        id_tmdb, tipo = pertenencia
        item = Tiene.objects.filter(
            lista_id=OuterRef("pk"),
            produccion__id_tmdb=id_tmdb,
            produccion__tipo=tipo,
        )
        listas = listas.annotate(
            contiene=Exists(item), item_id=Subquery(item.values("pk")[:1])
        )

    return list(listas)


def _agregar_previews(listas, idioma=None):
    """Adjunta hasta el máximo configurado de pósters recientes por lista."""
    if not listas:
        return

    previews = (
        Tiene.objects.filter(
            lista_id__in=[lista.pk for lista in listas], produccion__poster__gt=""
        )
        .select_related("produccion")
        .prefetch_related("produccion__traducciones")
        .annotate(
            posicion=Window(
                expression=RowNumber(),
                partition_by=[F("lista_id")],
                order_by=[F("fecha_agregado").desc(), F("id").desc()],
            )
        )
        .filter(posicion__lte=_MAX_PREVIEW_POSTERS)
        .order_by("lista_id", "posicion")
    )
    posters = defaultdict(list)
    for item in previews:
        posters[item.lista_id].append(
            texto_localizado(item.produccion, "poster", idioma)
        )
    for lista in listas:
        lista.preview_posters = posters[lista.pk]


def _resumen_response(listas, *, incluir_pertenencia=False, idioma=None):
    _agregar_previews(listas, idioma)
    return ListaResumenSerializer(
        listas,
        many=True,
        context={"incluir_pertenencia": incluir_pertenencia},
    ).data


def _techo_de_items():
    return ExcepcionAPI(
        "list_items_limit_reached", parametros={"maxItems": MAX_ITEMS_POR_LISTA}
    )


def _lista_propia(request, lista_id):
    return get_object_or_404(
        Lista.objects.filter(usuario=request.user, activa=True), pk=lista_id
    )


def _proteger_lista_predeterminada(lista):
    if lista.tipo == TipoLista.PREDETERMINADA:
        raise ListaPredeterminadaProtegida


class ListasView(APIView):
    """Lista y crea listas del usuario autenticado."""

    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]

    def get(self, request):
        parametros = request.query_params
        consultar_pertenencia = "id_tmdb" in parametros or "tipo" in parametros
        pertenencia = None
        if consultar_pertenencia:
            serializer = PertenenciaQuerySerializer(data=parametros)
            serializer.is_valid(raise_exception=True)
            pertenencia = (
                serializer.validated_data["id_tmdb"],
                tmdb_a_dominio(serializer.validated_data["tipo"]),
            )

        listas = _listas_del_usuario(request, pertenencia=pertenencia)
        return Response(
            _resumen_response(
                listas,
                incluir_pertenencia=consultar_pertenencia,
                idioma=idioma_efectivo(request),
            )
        )

    def post(self, request):
        serializer = NombreListaSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        personalizadas = Lista.objects.filter(
            usuario=request.user, tipo=TipoLista.PERSONALIZADA
        ).count()
        if personalizadas >= MAX_LISTAS_PERSONALIZADAS:
            raise ExcepcionAPI(
                "list_limit_reached", parametros={"maxLists": MAX_LISTAS_PERSONALIZADAS}
            )
        try:
            with transaction.atomic():
                # La nueva va al final de las personalizadas, como en el canvas.
                ultima = Lista.objects.filter(
                    usuario=request.user, tipo=TipoLista.PERSONALIZADA
                ).aggregate(maximo=Max("orden"))["maximo"]
                lista = Lista.objects.create(
                    usuario=request.user,
                    nombre=serializer.validated_data["nombre"],
                    tipo=TipoLista.PERSONALIZADA,
                    orden=(ultima or 0) + 1,
                )
        except IntegrityError:
            raise NombreListaDuplicado from None

        lista.cantidad_items = lista.cantidad_peliculas = lista.cantidad_series = 0
        lista.preview_posters = []
        return Response(
            ListaResumenSerializer(lista).data, status=status.HTTP_201_CREATED
        )


def _resumen_de(request, lista_id):
    """El resumen de una lista propia, con contadores y preview."""
    _lista_propia(request, lista_id)
    lista = next(
        resumen for resumen in _listas_del_usuario(request) if resumen.pk == lista_id
    )
    return _resumen_response([lista], idioma=idioma_efectivo(request))[0]


class ListasOrdenView(APIView):
    """Guarda el orden de las listas personalizadas (L-02).

    Recibe los ids en el orden nuevo y devuelve todas las listas como
    `GET /api/lists/`. Es tolerante con lo que pudo cambiar en otra pestaña: los
    ids que ya no existen (o que no son del usuario) se ignoran, y las
    personalizadas que no vinieron quedan al final en su orden anterior. Así una
    lista recién creada en otra pestaña no hace fallar el reordenamiento.
    """

    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]

    def put(self, request):
        serializer = OrdenListasSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        with transaction.atomic():
            propias = list(
                Lista.objects.select_for_update()
                .filter(usuario=request.user, tipo=TipoLista.PERSONALIZADA)
                .order_by("orden", "id")
            )
            por_id = {lista.pk: lista for lista in propias}
            pedidas = [por_id[pk] for pk in ids if pk in por_id]
            # Un solo `set`: armarlo dentro de la comprensión lo recalculaba por
            # cada lista (costo cuadrático, revisión del 24/10/2026).
            pedidos = set(ids)
            resto = [lista for lista in propias if lista.pk not in pedidos]
            for posicion, lista in enumerate(pedidas + resto, start=1):
                lista.orden = posicion
            Lista.objects.bulk_update(propias, ["orden"])

        return Response(
            _resumen_response(
                _listas_del_usuario(request), idioma=idioma_efectivo(request)
            )
        )


class ListaDetailView(APIView):
    """Lee, renombra o elimina una lista propia.

    `GET` sirve a las predeterminadas también: el detalle (L-03) y la miga
    «Lists > {nombre}» de la ficha (`?from=list-{id}`) lo necesitan para todas.
    """

    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]

    def get(self, request, lista_id):
        return Response(_resumen_de(request, lista_id))

    def put(self, request, lista_id):
        lista = _lista_propia(request, lista_id)
        _proteger_lista_predeterminada(lista)
        serializer = NombreListaSerializer(
            data=request.data,
            context={"request": request, "lista_id": lista.pk},
        )
        serializer.is_valid(raise_exception=True)
        lista.nombre = serializer.validated_data["nombre"]
        try:
            with transaction.atomic():
                lista.save(update_fields=["nombre"])
        except IntegrityError:
            raise NombreListaDuplicado from None

        return Response(_resumen_de(request, lista.pk))

    def delete(self, request, lista_id):
        lista = _lista_propia(request, lista_id)
        _proteger_lista_predeterminada(lista)
        lista.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class _Unaccent(Func):
    """`unaccent()` de PostgreSQL (la extensión ya está instalada para `__unaccent`)."""

    function = "UNACCENT"
    output_field = CharField()


# Un cursor necesita un criterio único: la nota y el título se combinan con el
# id del ítem en una sola clave, como `clave_nota` en «Mis reseñas».
_ORDENES_ITEMS = {
    "agregado-desc": ("-fecha_agregado", "-id"),
    "agregado-asc": ("fecha_agregado", "id"),
    "titulo-asc": ("clave_titulo",),
    "nota-desc": ("-clave_nota",),
    "nota-asc": ("clave_nota",),
}

_CALIFICADA = Q(produccion__calificacion_promedio__gt=0)


def _filtrar_items(items, datos):
    """Aplica búsqueda, tipo y tramo de nota de TMDB al detalle de una lista."""
    q = (datos.get("q") or "").strip()
    if q:
        # Mismo criterio que «Mis reseñas»: título canónico o traducido, sin
        # acentos ni mayúsculas, con `Exists` para no repetir ítems.
        traducido = ProduccionTraduccion.objects.filter(
            produccion=OuterRef("produccion"), titulo__unaccent__icontains=q
        )
        items = items.filter(
            Q(produccion__titulo__unaccent__icontains=q) | Exists(traducido)
        )
    if "clase" in datos:
        items = items.filter(produccion__tipo=tmdb_a_dominio(datos["clase"]))
    if "nota" in datos:
        # Un título sin nota de TMDB no entra en ningún tramo, tampoco en
        # «Below 5» (decisión del 15/10/2026).
        minimo, maximo = NOTAS[datos["nota"]]
        items = items.filter(_CALIFICADA)
        if minimo is not None:
            items = items.filter(produccion__calificacion_promedio__gte=minimo)
        if maximo is not None:
            items = items.filter(produccion__calificacion_promedio__lte=maximo)
    return items


def _anotar_clave_orden(items, orden, idioma):
    """Anota la clave única que usa el cursor para ordenar por nota o por título."""
    if orden.startswith("nota"):
        # Nota por 1000 (TMDB trae tres decimales) seguida del id del ítem. Sin
        # nota, el título queda al final en los dos sentidos.
        sin_nota = -1 if orden == "nota-desc" else 10_001
        nota = Case(
            When(
                _CALIFICADA,
                then=Cast(
                    F("produccion__calificacion_promedio") * 1000, BigIntegerField()
                ),
            ),
            default=Value(sin_nota),
            output_field=BigIntegerField(),
        )
        return items.annotate(
            clave_nota=ExpressionWrapper(
                nota * 1_000_000_000 + F("id"), output_field=BigIntegerField()
            )
        )
    if orden == "titulo-asc":
        # Por el título que se ve: el traducido si existe, si no el canónico.
        # Sin acentos ni mayúsculas y con collation «C», para que el orden de la
        # base y la comparación del cursor sean el mismo.
        traduccion = ProduccionTraduccion.objects.filter(
            produccion=OuterRef("produccion"), idioma=idioma
        ).values("titulo")[:1]
        titulo = Coalesce(
            NullIf(Subquery(traduccion), Value("")), F("produccion__titulo")
        )
        return items.annotate(
            clave_titulo=Collate(
                Concat(
                    Lower(_Unaccent(titulo)),
                    Value(" "),
                    LPad(Cast("id", CharField()), 12, Value("0")),
                    output_field=CharField(),
                ),
                "C",
            )
        )
    return items


class ListaItemsView(TopesTMDBMixin, APIView):
    """Pagina o agrega producciones a una lista propia."""

    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]

    pagination_class = ListaItemCursorPagination

    def get(self, request, lista_id):
        lista = _lista_propia(request, lista_id)
        query = ListaItemsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        datos = query.validated_data
        idioma = idioma_efectivo(request)
        items = _filtrar_items(
            Tiene.objects.filter(lista=lista)
            .select_related("produccion")
            .prefetch_related("produccion__traducciones"),
            datos,
        )
        paginator = self.pagination_class()
        paginator.ordering = _ORDENES_ITEMS[datos["orden"]]
        items = _anotar_clave_orden(items, datos["orden"], idioma)
        pagina = paginator.paginate_queryset(items, request, view=self)
        return paginator.get_paginated_response(
            ListaItemSerializer(
                pagina, many=True, context={"idioma": idioma_efectivo(request)}
            ).data
        )

    def post(self, request, lista_id):
        lista = _lista_propia(request, lista_id)
        serializer = AgregarItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_tmdb = serializer.validated_data["id_tmdb"]
        tipo = serializer.validated_data["tipo"]
        con_techo = lista.tipo == TipoLista.PERSONALIZADA
        # Antes de materializar, para no gastar llamadas a TMDB. Un título que
        # ya está es un duplicado aunque la lista esté llena (PR-Agent, #135):
        # un doble clic no tiene que decir «la lista está llena».
        if con_techo and lista.items.count() >= MAX_ITEMS_POR_LISTA:
            if lista.items.filter(
                produccion__id_tmdb=id_tmdb, produccion__tipo=tmdb_a_dominio(tipo)
            ).exists():
                raise ItemDuplicado
            raise _techo_de_items()
        produccion = materializar(id_tmdb, tipo)
        try:
            with transaction.atomic():
                if con_techo:
                    # Se vuelve a contar con la lista bloqueada: dos altas en
                    # paralelo con 999 ítems pasaban las dos el chequeo de arriba.
                    Lista.objects.select_for_update().get(pk=lista.pk)
                    if lista.items.count() >= MAX_ITEMS_POR_LISTA:
                        raise _techo_de_items()
                item = Tiene.objects.create(lista=lista, produccion=produccion)
                # Lo que ya viste deja de estar pendiente (14/10/2026). En el
                # mismo atomic: si el alta falla, «Pendientes» queda intacta.
                if (
                    lista.tipo == TipoLista.PREDETERMINADA
                    and lista.clave == ClaveLista.VISTAS
                ):
                    quitar_de_pendientes(request.user, produccion)
        except IntegrityError:
            raise ItemDuplicado from None
        return Response(
            ListaItemSerializer(
                item, context={"idioma": idioma_efectivo(request)}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ListaItemDetailView(APIView):
    """Quita un ítem de una lista propia."""

    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]

    def delete(self, request, lista_id, item_id):
        """Quita el ítem, y con `?borrar_calificacion=true` también la calificación.

        CU-011 pide que no se pueda desmarcar como «vista» una producción
        calificada sin eliminar antes esa calificación: si la calificaste, la
        viste, y quitarla de «Vistas» afirmaría lo contrario.

        Hasta la fase 3 de C-08 eso era un callejón sin salida —el 409 mandaba
        al usuario a otra pantalla—. Con el flag, la UI puede advertir qué se
        pierde («Se eliminarán tu calificación de 9/10 y tu reseña») y hacerlo
        en el momento. El 409 sin flag no cambia: es lo que le avisa al frontend
        que tiene que preguntar primero.

        Las dos escrituras van en **una** transacción. Dos llamadas HTTP desde
        el frontend no serían atómicas: si la segunda fallara, el usuario
        perdería la calificación y la producción seguiría en «Vistas» —el costo
        pagado y nada obtenido—.
        """
        lista = _lista_propia(request, lista_id)
        item = get_object_or_404(
            Tiene.objects.select_related("produccion"), pk=item_id, lista=lista
        )
        query = QuitarItemQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        # La regla es solo de «Vistas»: quitar de Favoritos algo calificado
        # nunca estuvo bloqueado, así que el flag tampoco borra nada ahí.
        calificacion = None
        if lista.tipo == TipoLista.PREDETERMINADA and lista.clave == ClaveLista.VISTAS:
            calificacion = Calificacion.objects.filter(
                usuario=request.user, produccion=item.produccion, activa=True
            ).first()
            if (
                calificacion is not None
                and not query.validated_data["borrar_calificacion"]
            ):
                raise CalificacionImpideQuitarDeVistas

        with transaction.atomic():
            if calificacion is not None:
                # La `Resena` cae por CASCADE; es lo que el modal advierte.
                calificacion.delete()
            item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
