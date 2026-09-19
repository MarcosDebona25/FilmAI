"""Endpoints autenticados para gestionar listas e ítems del usuario."""

from collections import defaultdict

from django.db import IntegrityError, transaction
from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
    Window,
)
from django.db.models.functions import RowNumber
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.models import Calificacion, TipoProduccion
from catalogo.services.adapter import tmdb_a_dominio
from catalogo.services.materialization import materializar

from .exceptions import (
    CalificacionImpideQuitarDeVistas,
    ItemDuplicado,
    ListaPredeterminadaProtegida,
    NombreListaDuplicado,
)
from .models import Lista, Tiene, TipoLista
from .pagination import ListaItemCursorPagination
from .serializers import (
    AgregarItemSerializer,
    ListaItemSerializer,
    ListaResumenSerializer,
    NombreListaSerializer,
    PertenenciaQuerySerializer,
)

_ORDEN_PREDETERMINADAS = Case(
    When(nombre="Favoritos", tipo=TipoLista.PREDETERMINADA, then=Value(0)),
    When(nombre="Pendientes", tipo=TipoLista.PREDETERMINADA, then=Value(1)),
    When(nombre="Vistas", tipo=TipoLista.PREDETERMINADA, then=Value(2)),
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
        .order_by("orden_predeterminada", "id")
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


def _agregar_previews(listas):
    """Adjunta hasta el máximo configurado de pósters recientes por lista."""
    if not listas:
        return

    previews = (
        Tiene.objects.filter(
            lista_id__in=[lista.pk for lista in listas], produccion__poster__gt=""
        )
        .select_related("produccion")
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
        posters[item.lista_id].append(item.produccion.poster)
    for lista in listas:
        lista.preview_posters = posters[lista.pk]


def _resumen_response(listas, *, incluir_pertenencia=False):
    _agregar_previews(listas)
    return ListaResumenSerializer(
        listas,
        many=True,
        context={"incluir_pertenencia": incluir_pertenencia},
    ).data


def _lista_propia(request, lista_id):
    return get_object_or_404(
        Lista.objects.filter(usuario=request.user, activa=True), pk=lista_id
    )


def _proteger_lista_predeterminada(lista):
    if lista.tipo == TipoLista.PREDETERMINADA:
        raise ListaPredeterminadaProtegida


class ListasView(APIView):
    """Lista y crea listas del usuario autenticado."""

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
            _resumen_response(listas, incluir_pertenencia=consultar_pertenencia)
        )

    def post(self, request):
        serializer = NombreListaSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                lista = Lista.objects.create(
                    usuario=request.user,
                    nombre=serializer.validated_data["nombre"],
                    tipo=TipoLista.PERSONALIZADA,
                )
        except IntegrityError:
            raise NombreListaDuplicado from None

        lista.cantidad_items = lista.cantidad_peliculas = lista.cantidad_series = 0
        lista.preview_posters = []
        return Response(
            ListaResumenSerializer(lista).data, status=status.HTTP_201_CREATED
        )


class ListaDetailView(APIView):
    """Renombra o elimina una lista personalizada."""

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

        lista_actualizada = next(
            resumen
            for resumen in _listas_del_usuario(request)
            if resumen.pk == lista.pk
        )
        return Response(_resumen_response([lista_actualizada])[0])

    def delete(self, request, lista_id):
        lista = _lista_propia(request, lista_id)
        _proteger_lista_predeterminada(lista)
        lista.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListaItemsView(APIView):
    """Pagina o agrega producciones a una lista propia."""

    pagination_class = ListaItemCursorPagination

    def get(self, request, lista_id):
        lista = _lista_propia(request, lista_id)
        items = Tiene.objects.filter(lista=lista).select_related("produccion")
        paginator = self.pagination_class()
        pagina = paginator.paginate_queryset(items, request, view=self)
        return paginator.get_paginated_response(
            ListaItemSerializer(pagina, many=True).data
        )

    def post(self, request, lista_id):
        lista = _lista_propia(request, lista_id)
        serializer = AgregarItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        produccion = materializar(
            serializer.validated_data["id_tmdb"], serializer.validated_data["tipo"]
        )
        try:
            with transaction.atomic():
                item = Tiene.objects.create(lista=lista, produccion=produccion)
        except IntegrityError:
            raise ItemDuplicado from None
        return Response(ListaItemSerializer(item).data, status=status.HTTP_201_CREATED)


class ListaItemDetailView(APIView):
    """Quita un ítem de una lista propia."""

    def delete(self, request, lista_id, item_id):
        lista = _lista_propia(request, lista_id)
        item = get_object_or_404(
            Tiene.objects.select_related("produccion"), pk=item_id, lista=lista
        )
        if (
            lista.tipo == TipoLista.PREDETERMINADA
            and lista.nombre == "Vistas"
            and Calificacion.objects.filter(
                usuario=request.user, produccion=item.produccion, activa=True
            ).exists()
        ):
            raise CalificacionImpideQuitarDeVistas
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
