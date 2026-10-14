import logging
from typing import ClassVar

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from catalogo.services.browse import NOTAS, explorar, generos_de_todo
from catalogo.services.creditos import creditos
from catalogo.services.fallback import servicio_localizado
from catalogo.services.idioma_tmdb import idioma_tmdb
from catalogo.services.materialization import materializar_en_segundo_plano
from catalogo.services.recomendado import recomendar
from catalogo.services.tmdb import get_catalog_service
from filmai.errores.validacion import ErrorValidacion

logger = logging.getLogger(__name__)

_MISSING = object()


def _error_param(name, mensaje, codigo, parametros=None):
    """400 con el texto heredado y el código estable del parámetro."""
    return ErrorValidacion(
        {name: mensaje},
        codigo,
        parametros_por_ruta={(name,): parametros or {}},
    )


def _int_param(value, name, *, default=_MISSING):
    if value in (None, ""):
        if default is not _MISSING:
            return default
        raise _error_param(name, "This parameter is required.", "required")
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise _error_param(
            name, "Must be an integer.", "invalid", {"expectedType": "integer"}
        ) from None
    if result <= 0:
        raise _error_param(
            name, "Must be a positive integer.", "min_value", {"minValue": 1}
        )
    return result


def _float_param(value, name, *, default=None):
    if value in (None, ""):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise _error_param(
            name, "Must be a number.", "invalid", {"expectedType": "number"}
        ) from None
    if result != result or result in (float("inf"), float("-inf")):
        raise _error_param(name, "Must be a finite number.", "number_not_finite")
    return result


def _validate_tipo(value):
    if value not in {"movie", "tv"}:
        raise _error_param(
            "tipo",
            "Must be either 'movie' or 'tv'.",
            "invalid_choice",
            {"allowedValues": ["movie", "tv"]},
        )
    return value


def _materializar_sin_interrumpir(id_tmdb, tipo_tmdb):
    """Encola la materialización sin que un fallo afecte ni demore la respuesta.

    El contrato de estos endpoints (C-03) es passthrough puro de TMDB: si
    nuestra base o el broker están caídos, el usuario igual tiene que ver la
    ficha. El enriquecimiento corre en Celery (14/10/2026): hacerlo acá sumaba
    hasta un segundo a la primera visita.
    """
    try:
        materializar_en_segundo_plano(id_tmdb, tipo_tmdb)
    except Exception:
        # Amplio a propósito: es el límite entre el contrato de C-03 y todo lo
        # que puede salir mal del lado nuestro (base, broker).
        logger.exception(
            "No se pudo materializar la producción (%s, %s)", id_tmdb, tipo_tmdb
        )


class CatalogoBaseView(APIView):
    authentication_classes: ClassVar = []
    permission_classes: ClassVar = [AllowAny]
    throttle_classes: ClassVar = [ScopedRateThrottle]
    throttle_scope = "catalogo"

    def _service(self, request):
        return servicio_localizado(idioma_tmdb(request), get_catalog_service)

    def _page(self, request):
        return _int_param(request.query_params.get("page"), "page", default=1)


class TrendingView(CatalogoBaseView):
    def get(self, request):
        service = self._service(request)
        data = service.get_trending(
            request.query_params.get("media_type", "all"),
            request.query_params.get("time_window", "week"),
            self._page(request),
        )
        return Response(data)


class NowPlayingView(CatalogoBaseView):
    def get(self, request):
        data = self._service(request).get_now_playing(self._page(request))
        return Response(data)


class DiscoverView(CatalogoBaseView):
    def get(self, request):
        tipo = _validate_tipo(request.query_params.get("tipo", "movie"))
        genero = _int_param(request.query_params.get("genero"), "genero", default=None)
        anio = _int_param(request.query_params.get("anio"), "anio", default=None)
        min_rating = _float_param(
            request.query_params.get("min_rating"), "min_rating", default=None
        )
        # C-05: deja afuera títulos con pocos votos (`vote_count.gte` en TMDB).
        min_votos = _int_param(
            request.query_params.get("min_votes"), "min_votes", default=None
        )
        data = self._service(request).discover(
            tipo, genero, anio, min_rating, self._page(request), min_votos=min_votos
        )
        return Response(data)


class SearchView(CatalogoBaseView):
    def get(self, request):
        query = request.query_params.get("query")
        if not query:
            raise _error_param("query", "This parameter is required.", "required")
        tipo = _validate_tipo(request.query_params.get("tipo"))
        data = self._service(request).search(query, tipo, self._page(request))
        return Response(data)


class BrowseView(CatalogoBaseView):
    """Buscar (C-06): texto opcional, tipo y filtros, en una sola respuesta.

    `q` admite cualquier texto: se recorta y se mide después (decisión del
    14/10/2026; títulos como «WALL·E» necesitan signos). Qué llamadas hace a
    TMDB para cada combinación lo decide `services/browse.py`.
    """

    MAX_TEXTO = 50
    tipos: ClassVar = ["all", "movie", "tv"]

    def get(self, request):
        params = request.query_params
        q = (params.get("q") or "").strip() or None
        if q and len(q) > self.MAX_TEXTO:
            raise _error_param(
                "q",
                f"Ensure this field has no more than {self.MAX_TEXTO} characters.",
                "max_length",
                {"maxLength": self.MAX_TEXTO},
            )
        tipo = self._opcion(params.get("tipo", "all"), "tipo", self.tipos)
        nota = params.get("nota") or None
        if nota is not None:
            self._opcion(nota, "nota", list(NOTAS))
        page = self._page(request)
        if page > 500:
            raise _error_param(
                "page",
                "Ensure this value is less than or equal to 500.",
                "max_value",
                {"maxValue": 500},
            )
        datos = explorar(
            self._service(request),
            q=q,
            tipo=tipo,
            genero=_int_param(params.get("genero"), "genero", default=None),
            anio=_int_param(params.get("anio"), "anio", default=None),
            nota=nota,
            page=page,
        )
        return Response(datos)

    @staticmethod
    def _opcion(valor, nombre, permitidos):
        if valor not in permitidos:
            raise _error_param(
                nombre,
                f"Must be one of: {', '.join(permitidos)}.",
                "invalid_choice",
                {"allowedValues": permitidos},
            )
        return valor


class MovieDetailView(CatalogoBaseView):
    def get(self, request, id_tmdb):
        id_tmdb = _int_param(id_tmdb, "id_tmdb")
        data = self._service(request).get_movie_detail(id_tmdb)
        _materializar_sin_interrumpir(id_tmdb, "movie")
        return Response(data)


class TVDetailView(CatalogoBaseView):
    def get(self, request, id_tmdb):
        id_tmdb = _int_param(id_tmdb, "id_tmdb")
        data = self._service(request).get_tv_detail(id_tmdb)
        _materializar_sin_interrumpir(id_tmdb, "tv")
        return Response(data)


class CreditsView(CatalogoBaseView):
    """Directores (en series, los creadores) y reparto con personaje (C-07)."""

    tipo = None  # "movie" o "tv", lo fija la ruta

    def get(self, request, id_tmdb):
        id_tmdb = _int_param(id_tmdb, "id_tmdb")
        return Response(creditos(self._service(request), self.tipo, id_tmdb))


class GenresView(CatalogoBaseView):
    """Lista de géneros de TMDB en el idioma efectivo, cacheada por idioma.

    Con ella el frontend resuelve la etiqueta de un `generos_ids`/`genre_ids`.
    Un nombre vacío en el idioma pedido se completa con el inglés del mismo id.
    """

    def get(self, request):
        tipo = request.query_params.get("tipo", "movie")
        idioma = idioma_tmdb(request)
        if tipo == "all":
            # Buscar (C-06): los de películas y los de series sin par.
            return Response(
                {
                    "genres": generos_de_todo(
                        _generos_localizados("movie", idioma),
                        _generos_localizados("tv", idioma),
                    )
                }
            )
        tipo = _validate_tipo(tipo)
        return Response({"genres": _generos_localizados(tipo, idioma)})


def _generos_localizados(tipo, idioma):
    """Géneros de TMDB en `idioma`; un nombre vacío se completa con el inglés."""
    generos = get_catalog_service(idioma).get_genres(tipo).get("genres") or []
    if any(not (genero.get("name") or "").strip() for genero in generos):
        en_ingles = {
            genero.get("id"): genero.get("name")
            for genero in get_catalog_service().get_genres(tipo).get("genres") or []
        }
        for genero in generos:
            if not (genero.get("name") or "").strip():
                genero["name"] = en_ingles.get(genero.get("id")) or ""
    return generos


class KeywordsView(CatalogoBaseView):
    def get(self, request):
        id_tmdb = _int_param(request.query_params.get("id_tmdb"), "id_tmdb")
        tipo = _validate_tipo(request.query_params.get("tipo"))
        data = get_catalog_service().get_keywords(id_tmdb, tipo)
        return Response(data)


class RecommendedView(APIView):
    """«Recomendado para ti» del Home (C-05), solo con sesión.

    `tipo` es `all` (por defecto), `movie` o `tv`. Responde `{generos, results}`:
    los nombres de los géneros usados (como mucho 3, en el idioma del pedido) y
    hasta 15 títulos con la forma de TMDB más `media_type`. Sin calificaciones
    de 7 o más, las dos listas vienen vacías.
    """

    # No hereda de `CatalogoBaseView`, que es pública: usa la autenticación y el
    # permiso por defecto del proyecto (cookie JWT + `IsAuthenticated`), así que
    # sin sesión DRF responde 401 antes de llegar a `get`.
    throttle_classes: ClassVar = [ScopedRateThrottle]
    throttle_scope = "catalogo"
    tipos: ClassVar = ["all", "movie", "tv"]

    def get(self, request):
        tipo = request.query_params.get("tipo", "all")
        if tipo not in self.tipos:
            raise _error_param(
                "tipo",
                "Must be one of 'all', 'movie' or 'tv'.",
                "invalid_choice",
                {"allowedValues": self.tipos},
            )
        idioma = idioma_tmdb(request)
        datos = recomendar(
            request.user,
            tipo,
            servicio=servicio_localizado(idioma, get_catalog_service),
            nombres_de_generos=lambda t: {
                genero["id"]: genero["name"]
                for genero in _generos_localizados(t, idioma)
            },
        )
        return Response(datos)
