import logging
from typing import ClassVar

from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle
from rest_framework.views import APIView

from catalogo.models import ID_TMDB_MAXIMO
from catalogo.presupuesto import contar_llamadas
from catalogo.services.browse import NOTAS, anio_actual, explorar, generos_de_todo
from catalogo.services.creditos import creditos
from catalogo.services.fallback import servicio_localizado
from catalogo.services.idioma_tmdb import idioma_tmdb
from catalogo.services.materialization import (
    materializar_en_segundo_plano,
    materializar_listado_en_segundo_plano,
)
from catalogo.services.plataformas import plataformas
from catalogo.services.recomendado import recomendar
from catalogo.services.tmdb import get_catalog_service
from filmai.errores.validacion import ErrorValidacion
from usuarios.paises import es_pais_valido

logger = logging.getLogger(__name__)

_MISSING = object()


def _error_param(name, mensaje, codigo, parametros=None):
    """400 con el texto heredado y el código estable del parámetro."""
    return ErrorValidacion(
        {name: mensaje},
        codigo,
        parametros_por_ruta={(name,): parametros or {}},
    )


PAGINA_MAXIMA = 500


def _int_param(value, name, *, default=_MISSING, maximo=None):
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
    if maximo is not None and result > maximo:
        raise _error_param(
            name,
            f"Ensure this value is less than or equal to {maximo}.",
            "max_value",
            {"maxValue": maximo},
        )
    return result


def _id_tmdb(value):
    # Más allá del máximo de la columna, TMDB responde 404 (Not Found) seguro:
    # se corta acá, sin gastar la llamada (auditoría F7).
    return _int_param(value, "id_tmdb", maximo=ID_TMDB_MAXIMO)


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


def _opcion(valor, nombre, permitidos):
    if valor not in permitidos:
        raise _error_param(
            nombre,
            f"Must be one of: {', '.join(permitidos)}.",
            "invalid_choice",
            {"allowedValues": permitidos},
        )
    return valor


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


def _materializar_listado_sin_interrumpir(data, tipo_tmdb=None):
    """Encola lo que muestra un listado (C-04a) sin afectar la respuesta.

    Misma política que la ficha: el listado es passthrough de TMDB y se tiene
    que ver aunque la base o el broker fallen.
    """
    try:
        materializar_listado_en_segundo_plano(
            (data or {}).get("results", []), tipo_tmdb
        )
    except Exception:
        logger.exception("No se pudo encolar la materialización del listado")


# Cuánto puede reusar el navegador una respuesta del catálogo sin volver a
# pedirla. Corto a propósito: el TTL de Redis (`catalogo/cache.py`) ya evita
# llamar a TMDB; esto solo ahorra el viaje al backend al volver a una pantalla
# o recargar (22/10/2026).
CACHE_NAVEGADOR_SEGUNDOS = 5 * 60


# Los dos topes de llamadas a TMDB de la auditoría F6 (24/10/2026): `dispatch`
# abre el contador del pedido con la IP del cliente (la misma que usan los
# throttles de DRF, con `NUM_PROXIES`). Cada llamada a TMDB cuenta en el momento
# para el tope del pedido (503) y para el de la IP (429): ver `presupuesto.py`.
# Va en comentario y no en docstring: drf-spectacular usa el docstring heredado
# como descripción pública de cada endpoint del catálogo.
class _TopesTMDBMixin:
    def dispatch(self, request, *args, **kwargs):
        with contar_llamadas(ident=BaseThrottle().get_ident(request)):
            return super().dispatch(request, *args, **kwargs)


# Comprimido solo acá y no con `GZipMiddleware` global: el catálogo es público y
# no lleva secretos (sin cookies ni CSRF en la respuesta), así que no queda
# expuesto a BREACH. Un listado de 13 kB baja a ~5 kB.
@method_decorator(gzip_page, name="dispatch")
class CatalogoBaseView(_TopesTMDBMixin, APIView):
    authentication_classes: ClassVar = []
    permission_classes: ClassVar = [AllowAny]
    throttle_classes: ClassVar = [ScopedRateThrottle]
    throttle_scope = "catalogo"

    def _service(self, request):
        return servicio_localizado(idioma_tmdb(request), get_catalog_service)

    def finalize_response(self, request, response, *args, **kwargs):
        """Las respuestas 200 (OK) se pueden cachear en el navegador.

        Son públicas (sin autenticación, `authentication_classes = []`) y solo
        cambian con el idioma, que sale de `Accept-Language`: por eso el `Vary`.
        Los errores no se cachean, así un 503 (Service Unavailable) de TMDB no
        queda pegado.
        """
        response = super().finalize_response(request, response, *args, **kwargs)
        if response.status_code == 200:
            patch_cache_control(response, public=True, max_age=CACHE_NAVEGADOR_SEGUNDOS)
            patch_vary_headers(response, ["Accept-Language"])
        return response

    def _page(self, request):
        # TMDB no sirve páginas más allá de 500; sin tope, cada `page` distinto
        # sería otra clave de caché y otra llamada a TMDB.
        return _int_param(
            request.query_params.get("page"), "page", default=1, maximo=PAGINA_MAXIMA
        )


class TrendingView(CatalogoBaseView):
    # Los dos parámetros van al path de TMDB (`/trending/{media_type}/{time_window}`):
    # sin validarlos, `media_type=../movie/550` llevaba el pedido a otro endpoint
    # (auditoría F6). `person` también existe en TMDB, pero FilmAI no muestra personas.
    media_types: ClassVar = ["all", "movie", "tv"]
    time_windows: ClassVar = ["day", "week"]

    def get(self, request):
        params = request.query_params
        media_type = _opcion(
            params.get("media_type", "all"), "media_type", self.media_types
        )
        time_window = _opcion(
            params.get("time_window", "week"), "time_window", self.time_windows
        )
        page = self._page(request)
        data = self._service(request).get_trending(media_type, time_window, page)
        # En «all» cada ítem trae su `media_type`.
        _materializar_listado_sin_interrumpir(
            data, media_type if media_type in ("movie", "tv") else None
        )
        return Response(data)


class NowPlayingView(CatalogoBaseView):
    def get(self, request):
        data = self._service(request).get_now_playing(self._page(request))
        _materializar_listado_sin_interrumpir(data, "movie")
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
        _materializar_listado_sin_interrumpir(data, tipo)
        return Response(data)


class SearchView(CatalogoBaseView):
    def get(self, request):
        query = request.query_params.get("query")
        if not query:
            raise _error_param("query", "This parameter is required.", "required")
        tipo = _validate_tipo(request.query_params.get("tipo"))
        data = self._service(request).search(query, tipo, self._page(request))
        _materializar_listado_sin_interrumpir(data, tipo)
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
        tipo = _opcion(params.get("tipo", "all"), "tipo", self.tipos)
        nota = params.get("nota") or None
        if nota is not None:
            _opcion(nota, "nota", list(NOTAS))
        page = self._page(request)
        datos = explorar(
            self._service(request),
            q=q,
            tipo=tipo,
            genero=_int_param(params.get("genero"), "genero", default=None),
            anio=_int_param(params.get("anio"), "anio", default=None),
            nota=nota,
            page=page,
            a_estrenar=self._a_estrenar(params.get("a_estrenar")),
            decada=self._decada(params.get("decada")),
        )
        # Cada ítem de Buscar trae su `media_type`.
        _materializar_listado_sin_interrumpir(datos)
        return Response(datos)

    def _decada(self, valor):
        """Década del selector de año (antes de 1990): 1900, 1910… hasta la actual."""
        decada = _int_param(valor, "decada", default=None)
        if decada is None:
            return None
        permitidas = [str(d) for d in range(1900, anio_actual() // 10 * 10 + 1, 10)]
        # `allowedValues` es una lista de textos en el contrato de errores.
        _opcion(str(decada), "decada", permitidas)
        return decada

    def _a_estrenar(self, valor):
        """«A estrenar» del selector de año: `true` o nada."""
        if valor in (None, ""):
            return False
        return _opcion(valor, "a_estrenar", ["true"]) == "true"


class MovieDetailView(CatalogoBaseView):
    def get(self, request, id_tmdb):
        id_tmdb = _id_tmdb(id_tmdb)
        data = self._service(request).get_movie_detail(id_tmdb)
        _materializar_sin_interrumpir(id_tmdb, "movie")
        return Response(data)


class TVDetailView(CatalogoBaseView):
    def get(self, request, id_tmdb):
        id_tmdb = _id_tmdb(id_tmdb)
        data = self._service(request).get_tv_detail(id_tmdb)
        _materializar_sin_interrumpir(id_tmdb, "tv")
        return Response(data)


class CreditsView(CatalogoBaseView):
    """Directores (en series, los creadores) y reparto con personaje (C-07)."""

    tipo = None  # "movie" o "tv", lo fija la ruta

    def get(self, request, id_tmdb):
        id_tmdb = _id_tmdb(id_tmdb)
        return Response(creditos(self._service(request), self.tipo, id_tmdb))


class ProvidersView(CatalogoBaseView):
    """Plataformas donde ver la producción en `?pais=XX` (ISO 3166-1 alfa-2).

    El país lo manda el cliente y no sale de la sesión: el endpoint sigue
    siendo público y cacheable, como el resto del catálogo.
    """

    tipo = None  # "movie" o "tv", lo fija la ruta

    def get(self, request, id_tmdb):
        id_tmdb = _id_tmdb(id_tmdb)
        pais = request.query_params.get("pais")
        if not es_pais_valido(pais):
            raise _error_param(
                "pais",
                "Must be a valid ISO 3166-1 alpha-2 country code.",
                "country_invalid",
            )
        return Response(plataformas(self._service(request), self.tipo, id_tmdb, pais))


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
        id_tmdb = _id_tmdb(request.query_params.get("id_tmdb"))
        tipo = _validate_tipo(request.query_params.get("tipo"))
        data = get_catalog_service().get_keywords(id_tmdb, tipo)
        return Response(data)


class RecommendedView(_TopesTMDBMixin, APIView):
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
