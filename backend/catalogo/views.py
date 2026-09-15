import logging
from typing import ClassVar

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from catalogo.services.materialization import materializar
from catalogo.services.tmdb import get_catalog_service

logger = logging.getLogger(__name__)

_MISSING = object()


def _int_param(value, name, *, default=_MISSING):
    if value in (None, ""):
        if default is not _MISSING:
            return default
        raise ValidationError({name: "This parameter is required."})
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Must be an integer."}) from None
    if result <= 0:
        raise ValidationError({name: "Must be a positive integer."})
    return result


def _float_param(value, name, *, default=None):
    if value in (None, ""):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Must be a number."}) from None
    if result != result or result in (float("inf"), float("-inf")):
        raise ValidationError({name: "Must be a finite number."}) from None
    return result


def _validate_tipo(value):
    if value not in {"movie", "tv"}:
        raise ValidationError({"tipo": "Must be either 'movie' or 'tv'."})
    return value


def _materializar_sin_interrumpir(id_tmdb, tipo_tmdb):
    """Materializa la producción sin que un fallo afecte la respuesta.

    El contrato de estos endpoints (C-03) es passthrough puro de TMDB: si
    nuestra base está caída o el enriquecimiento falla, el usuario igual tiene
    que ver la ficha. `materializar()` propaga sus errores a propósito para que
    quien la llama fije la política; acá la política es registrar y seguir.
    """
    try:
        materializar(id_tmdb, tipo_tmdb)
    except Exception:
        # Amplio a propósito: es el límite entre el contrato de C-03 y todo lo
        # que puede salir mal del lado nuestro (base, red, TMDB, broker).
        logger.exception(
            "No se pudo materializar la producción (%s, %s)", id_tmdb, tipo_tmdb
        )


class CatalogoBaseView(APIView):
    authentication_classes: ClassVar = []
    permission_classes: ClassVar = [AllowAny]
    throttle_classes: ClassVar = [ScopedRateThrottle]
    throttle_scope = "catalogo"

    def _page(self, request):
        return _int_param(request.query_params.get("page"), "page", default=1)


class TrendingView(CatalogoBaseView):
    def get(self, request):
        service = get_catalog_service()
        data = service.get_trending(
            request.query_params.get("media_type", "all"),
            request.query_params.get("time_window", "week"),
            self._page(request),
        )
        return Response(data)


class NowPlayingView(CatalogoBaseView):
    def get(self, request):
        data = get_catalog_service().get_now_playing(self._page(request))
        return Response(data)


class DiscoverView(CatalogoBaseView):
    def get(self, request):
        tipo = _validate_tipo(request.query_params.get("tipo", "movie"))
        genero = _int_param(request.query_params.get("genero"), "genero", default=None)
        anio = _int_param(request.query_params.get("anio"), "anio", default=None)
        min_rating = _float_param(
            request.query_params.get("min_rating"), "min_rating", default=None
        )
        data = get_catalog_service().discover(
            tipo, genero, anio, min_rating, self._page(request)
        )
        return Response(data)


class SearchView(CatalogoBaseView):
    def get(self, request):
        query = request.query_params.get("query")
        if not query:
            raise ValidationError({"query": "This parameter is required."})
        tipo = _validate_tipo(request.query_params.get("tipo"))
        data = get_catalog_service().search(query, tipo, self._page(request))
        return Response(data)


class MovieDetailView(CatalogoBaseView):
    def get(self, request, id_tmdb):
        id_tmdb = _int_param(id_tmdb, "id_tmdb")
        data = get_catalog_service().get_movie_detail(id_tmdb)
        _materializar_sin_interrumpir(id_tmdb, "movie")
        return Response(data)


class TVDetailView(CatalogoBaseView):
    def get(self, request, id_tmdb):
        id_tmdb = _int_param(id_tmdb, "id_tmdb")
        data = get_catalog_service().get_tv_detail(id_tmdb)
        _materializar_sin_interrumpir(id_tmdb, "tv")
        return Response(data)


class KeywordsView(CatalogoBaseView):
    def get(self, request):
        id_tmdb = _int_param(request.query_params.get("id_tmdb"), "id_tmdb")
        tipo = _validate_tipo(request.query_params.get("tipo"))
        data = get_catalog_service().get_keywords(id_tmdb, tipo)
        return Response(data)
