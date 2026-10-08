import threading
from datetime import date, timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import fakeredis
import httpx
import redis
from django.conf import settings
from django.core.cache import cache as dj_cache
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import (
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.throttling import ScopedRateThrottle

from catalogo.cache import (
    ENDPOINT_TTLS,
    REDIS_SOCKET_CONNECT_TIMEOUT,
    REDIS_SOCKET_TIMEOUT,
    TMDBClientCache,
    _build_key,
    get_redis,
)
from catalogo.client import TMDBClient
from catalogo.exceptions import (
    TMDBBadRequest,
    TMDBError,
    TMDBNotFound,
    TMDBRateLimited,
    TMDBServerError,
    TMDBTransportError,
    tmdb_exception_handler,
)
from catalogo.factories import CalificacionFactory, ResenaFactory
from catalogo.management.commands.seed_catalogo import (
    _MAX_PAGINAS,
    Combinacion,
    _combinaciones,
    _recorrer,
)
from catalogo.management.commands.seed_catalogo import Command as SeedCatalogo
from catalogo.models import (
    Calificacion,
    EstadoEmbedding,
    ProduccionAudiovisual,
    ProduccionEmbedding,
    Resena,
    TipoProduccion,
)
from catalogo.services.adapter import dominio_a_tmdb, tmdb_a_dominio
from catalogo.services.embeddings import (
    MODEL_VERSION,
    calcular_source_hash,
    construir_texto_canonico,
    generar_vector,
)
from catalogo.services.materialization import (
    _necesita_enriquecimiento,
    claves_frescas,
    materializar,
)
from catalogo.services.tmdb import get_catalog_service
from catalogo.tasks import (
    _MAX_PAGINAS_CAMBIOS,
    _ids_cambiados,
    backfill_embeddings,
    generar_embedding,
    sync_catalogo_diaria,
)
from catalogo.views import (
    DiscoverView,
    MovieDetailView,
    SearchView,
    _float_param,
    _int_param,
)


class TMDBClientTest(SimpleTestCase):
    def make_client(self, handler, **settings):
        transport = httpx.MockTransport(handler)
        return TMDBClient(transport=transport, **settings)

    def test_default_timeout_and_raw_json(self):
        body = {"results": [{"id": 550, "title": "Fight Club"}]}

        def handler(request):
            self.assertEqual(request.url.params["api_key"], "test-key")
            return httpx.Response(200, json=body)

        with override_settings(TMDB_API_KEY="test-key", TMDB_TIMEOUT=5.0):
            client = self.make_client(handler)

        self.assertEqual(client.timeout, 5.0)
        self.assertEqual(client.get_trending(), body)

    @override_settings(TMDB_API_KEY="test-key", TMDB_TIMEOUT=10.0)
    def test_explicit_timeout(self):
        client = self.make_client(lambda request: httpx.Response(200, json={}))

        self.assertEqual(client.timeout, 10.0)

    def test_default_timeout_when_unset(self):
        # Sin override de TMDB_TIMEOUT: settings.TMDB_TIMEOUT cae al default
        # del config (5.0) y el cliente lo toma.
        client = self.make_client(lambda request: httpx.Response(200, json={}))

        self.assertEqual(client.timeout, 5.0)

    def test_http_errors_map_to_domain_exceptions(self):
        cases = (
            (404, TMDBNotFound),
            (400, TMDBBadRequest),
            (503, TMDBServerError),
        )
        for status, exception in cases:
            with self.subTest(status=status):
                client = self.make_client(
                    lambda request, status=status: httpx.Response(status)
                )
                with self.assertRaises(exception):
                    client.get_movie_detail(550)

    def test_transport_error_maps_to_domain_exception(self):
        def handler(request):
            raise httpx.ConnectError("offline", request=request)

        client = self.make_client(handler)

        with patch("catalogo.client.time.sleep"):
            with self.assertRaises(TMDBTransportError):
                client.get_movie_detail(550)

    def test_retries_rate_limit_using_retry_after_then_returns_json(self):
        responses = iter(
            [
                httpx.Response(429, headers={"Retry-After": "1"}),
                httpx.Response(200, json={"page": 1}),
            ]
        )
        calls = []

        def handler(request):
            calls.append(request)
            return next(responses)

        client = self.make_client(handler)
        with patch("catalogo.client.time.sleep") as sleep:
            result = client.get_now_playing()

        self.assertEqual(result, {"page": 1})
        self.assertEqual(len(calls), 2)
        sleep.assert_called_once_with(1.0)

    def test_rate_limit_retries_are_bounded(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(429)

        client = self.make_client(handler)
        with patch("catalogo.client.time.sleep"):
            with self.assertRaises(TMDBRateLimited):
                client.get_now_playing()

        self.assertEqual(len(calls), 4)

    def test_bad_request_is_not_retried(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(400)

        client = self.make_client(handler)
        with self.assertRaises(TMDBBadRequest):
            client.get_now_playing()

        self.assertEqual(len(calls), 1)

    def test_discovery_and_detail_endpoint_parameters(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"ok": True})

        client = self.make_client(handler)
        self.assertEqual(client.get_trending(), {"ok": True})
        self.assertEqual(client.discover("movie", 28, 2024, 7.5, 1), {"ok": True})
        self.assertEqual(client.discover("tv", 18, 2023, 8, 2), {"ok": True})
        self.assertEqual(client.search("Inception", "movie"), {"ok": True})
        self.assertEqual(client.get_now_playing(2), {"ok": True})
        self.assertEqual(client.get_movie_detail(550), {"ok": True})
        self.assertEqual(client.get_tv_detail(1399), {"ok": True})
        self.assertEqual(client.get_keywords(550, "movie"), {"ok": True})

        self.assertEqual(str(requests[0].url.path), "/3/trending/all/week")
        self.assertEqual(requests[0].url.params["page"], "1")
        movie_params = requests[1].url.params
        self.assertEqual(str(requests[1].url.path), "/3/discover/movie")
        self.assertEqual(movie_params["with_genres"], "28")
        self.assertEqual(movie_params["primary_release_year"], "2024")
        self.assertEqual(movie_params["vote_average.gte"], "7.5")
        tv_params = requests[2].url.params
        self.assertEqual(tv_params["first_air_date_year"], "2023")
        self.assertNotIn("primary_release_year", tv_params)
        self.assertEqual(str(requests[3].url.path), "/3/search/movie")
        self.assertEqual(requests[3].url.params["query"], "Inception")
        self.assertEqual(str(requests[4].url.path), "/3/movie/now_playing")
        self.assertEqual(str(requests[5].url.path), "/3/movie/550")
        self.assertEqual(str(requests[6].url.path), "/3/tv/1399")
        self.assertEqual(str(requests[7].url.path), "/3/movie/550/keywords")


class TMDBCreditsTest(SimpleTestCase):
    """Reparto y directores (C-04a).

    Los endpoints de detalle de TMDB NO traen cast ni crew: viven en
    `/{tipo}/{id}/credits`, con la misma forma que `/keywords`. Sin esto, los
    campos `reparto` y `directores` quedarían siempre vacíos y la búsqueda
    semántica no podría encontrar nada por actor ni director.
    """

    def _client(self, sink):
        def handler(request):
            sink.append(request)
            return httpx.Response(200, json={"cast": [], "crew": []})

        return TMDBClient(api_key="test-key", transport=httpx.MockTransport(handler))

    def test_pega_al_endpoint_de_credits_de_cada_tipo(self):
        casos = (
            (550, "movie", "/3/movie/550/credits"),
            (1399, "tv", "/3/tv/1399/credits"),
        )
        for id_tmdb, tipo, path in casos:
            with self.subTest(tipo=tipo):
                requests = []
                client = self._client(requests)

                resultado = client.get_credits(id_tmdb, tipo)

                self.assertEqual(resultado, {"cast": [], "crew": []})
                self.assertEqual(str(requests[0].url.path), path)

    def test_reutiliza_el_mapeo_de_errores_del_cliente(self):
        # No reimplementa manejo de errores: pasa por el mismo `_request` que
        # el resto de los métodos (C-01), con sus reintentos y excepciones.
        client = TMDBClient(
            api_key="test-key",
            transport=httpx.MockTransport(lambda request: httpx.Response(404)),
        )

        with self.assertRaises(TMDBNotFound):
            client.get_credits(550, "movie")


class TMDBChangesTest(SimpleTestCase):
    """Lista de cambios (C-04b, fase 2).

    `/{tipo}/changes` devuelve los IDs que TMDB modificó en las últimas 24 h,
    paginados de a 100. Es lo que permite refrescar solo lo que cambió en vez
    de barrer el catálogo por fecha. Forma verificada en vivo el 17/09/2026:
    `{"page", "total_pages", "total_results", "results": [{"id", "adult",
    "softcore"}]}`.
    """

    def _client(self, sink):
        def handler(request):
            sink.append(request)
            return httpx.Response(
                200, json={"page": 1, "total_pages": 1, "results": [{"id": 550}]}
            )

        return TMDBClient(api_key="test-key", transport=httpx.MockTransport(handler))

    def test_pega_al_endpoint_de_changes_de_cada_tipo_con_su_pagina(self):
        casos = (("movie", "/3/movie/changes"), ("tv", "/3/tv/changes"))
        for tipo, path in casos:
            with self.subTest(tipo=tipo):
                requests = []
                client = self._client(requests)

                resultado = client.get_changes(tipo, page=2)

                self.assertEqual(resultado["results"], [{"id": 550}])
                self.assertEqual(str(requests[0].url.path), path)
                self.assertEqual(requests[0].url.params["page"], "2")

    def test_reutiliza_el_mapeo_de_errores_del_cliente(self):
        client = TMDBClient(
            api_key="test-key",
            transport=httpx.MockTransport(lambda request: httpx.Response(404)),
        )

        with self.assertRaises(TMDBNotFound):
            client.get_changes("movie")


class TMDBDiscoverRangoTest(SimpleTestCase):
    """Rango de años y orden en `discover` (C-04c).

    El seed muestrea por década, y `discover` hasta ahora solo aceptaba UN
    año (`anio`). TMDB expone el rango con parámetros de fecha, y —igual que
    con el año suelto— **el nombre difiere por tipo**: las películas filtran
    por `primary_release_date`, las series por `first_air_date`. Verificado
    contra la API el 18/09/2026.

    `sort_by` importa tanto como el filtro: sci-fi de los 80 ordenado por
    votos devuelve *Back to the Future*; con el orden por defecto
    (popularidad) devuelve lo que trendea esta semana.
    """

    def _client(self, sink):
        def handler(request):
            sink.append(request)
            return httpx.Response(200, json={"results": []})

        return TMDBClient(api_key="test-key", transport=httpx.MockTransport(handler))

    def test_el_rango_de_anios_usa_el_parametro_de_fecha_de_cada_tipo(self):
        casos = (
            ("movie", "primary_release_date", "first_air_date"),
            ("tv", "first_air_date", "primary_release_date"),
        )
        for tipo, esperado, ajeno in casos:
            with self.subTest(tipo=tipo):
                requests = []
                client = self._client(requests)

                client.discover(tipo, anio_desde=1980, anio_hasta=1989)

                params = requests[0].url.params
                self.assertEqual(params[f"{esperado}.gte"], "1980-01-01")
                self.assertEqual(params[f"{esperado}.lte"], "1989-12-31")
                # El parámetro del otro tipo no viaja: TMDB lo ignoraría en
                # silencio y la década no se aplicaría.
                self.assertNotIn(f"{ajeno}.gte", params)

    def test_reenvia_sort_by_cuando_se_lo_pasan(self):
        requests = []
        client = self._client(requests)

        client.discover("movie", sort_by="vote_count.desc")

        self.assertEqual(requests[0].url.params["sort_by"], "vote_count.desc")

    def test_sin_los_parametros_nuevos_la_consulta_no_cambia(self):
        # Los llamadores de C-03 y C-04b siguen funcionando igual: los
        # parámetros nuevos son opcionales y no viajan si no se los pasa.
        requests = []
        client = self._client(requests)

        client.discover("movie", genero=28, anio=2024, min_rating=7.5, page=2)

        params = requests[0].url.params
        self.assertEqual(params["with_genres"], "28")
        self.assertEqual(params["primary_release_year"], "2024")
        self.assertEqual(params["vote_average.gte"], "7.5")
        self.assertEqual(params["page"], "2")
        for ausente in (
            "sort_by",
            "primary_release_date.gte",
            "primary_release_date.lte",
        ):
            self.assertNotIn(ausente, params)


class TMDBGenresTest(SimpleTestCase):
    """Catálogo de géneros de TMDB (C-04c).

    El seed muestrea por género, y los ids de género son de TMDB, no nuestros.
    Se piden a la API en vez de copiarlos al código: una lista hardcodeada es
    correcta hasta el día que deja de serlo, y nada nos avisaría.

    Los dos tipos tienen catálogos DISTINTOS (verificado el 18/09/2026):
    película tiene `Action` (28) y `Adventure` (12) por separado; serie tiene
    `Action & Adventure` (10759). Los ids no son intercambiables, así que el
    tipo es parte de la consulta y de la clave de caché.
    """

    def _client(self, sink):
        def handler(request):
            sink.append(request)
            return httpx.Response(200, json={"genres": [{"id": 28, "name": "Action"}]})

        return TMDBClient(api_key="test-key", transport=httpx.MockTransport(handler))

    def test_pega_al_endpoint_de_generos_de_cada_tipo(self):
        casos = (("movie", "/3/genre/movie/list"), ("tv", "/3/genre/tv/list"))
        for tipo, path in casos:
            with self.subTest(tipo=tipo):
                requests = []
                client = self._client(requests)

                resultado = client.get_genres(tipo)

                self.assertEqual(resultado["genres"], [{"id": 28, "name": "Action"}])
                self.assertEqual(str(requests[0].url.path), path)

    def test_reutiliza_el_mapeo_de_errores_del_cliente(self):
        client = TMDBClient(
            api_key="test-key",
            transport=httpx.MockTransport(lambda request: httpx.Response(404)),
        )

        with self.assertRaises(TMDBNotFound):
            client.get_genres("movie")


class TMDBExceptionHandlerTest(SimpleTestCase):
    def test_maps_tmdb_exceptions_to_http_statuses(self):
        cases = (
            (TMDBNotFound("missing"), 404),
            (TMDBBadRequest("invalid"), 400),
            (TMDBRateLimited("slow down"), 429),
            (TMDBServerError("upstream"), 502),
            (TMDBTransportError("offline"), 503),
            (TMDBError("unknown"), 502),
        )

        for exception, status in cases:
            with self.subTest(exception=type(exception).__name__):
                context = {"view": self}
                response = tmdb_exception_handler(exception, context)

                self.assertIsInstance(response, Response)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.data, {"detail": str(exception)})

    def test_delegates_non_tmdb_exceptions_to_drf(self):
        exception = ValueError("unexpected")
        context = {"view": self}

        with patch("catalogo.exceptions.drf_exception_handler") as delegate:
            expected = object()
            delegate.return_value = expected

            response = tmdb_exception_handler(exception, context)

        self.assertIs(response, expected)
        delegate.assert_called_once_with(exception, context)


class GetCatalogServiceTest(SimpleTestCase):
    def tearDown(self):
        get_catalog_service.cache_clear()

    @patch("catalogo.services.tmdb.get_redis")
    @patch("catalogo.services.tmdb.TMDBClient")
    def test_returns_singleton_tmdb_client_cache(self, client, get_redis):
        redis_client = object()
        tmdb_client = object()
        get_redis.return_value = redis_client
        client.return_value = tmdb_client

        first = get_catalog_service()
        second = get_catalog_service()

        self.assertIsInstance(first, TMDBClientCache)
        self.assertIs(first, second)
        self.assertIs(first.client, tmdb_client)
        self.assertIs(first.redis, redis_client)
        client.assert_called_once_with()
        get_redis.assert_called_once_with()


class CatalogoSettingsTest(SimpleTestCase):
    def test_global_handler_preserva_tmdb_y_throttle(self):
        self.assertEqual(
            settings.REST_FRAMEWORK["EXCEPTION_HANDLER"],
            "filmai.exceptions.filmai_exception_handler",
        )
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["catalogo"],
            "60/min",
        )
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["recuperar_contrasena"],
            "1/min",
        )


class TMDBClientCacheTest(SimpleTestCase):
    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)

    def make_cache(self, body=None, calls=None):
        body = body or {"results": [{"id": 550, "title": "Fight Club"}]}
        calls = calls if calls is not None else []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json=body)

        client = TMDBClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )
        return TMDBClientCache(client, self.redis), calls

    def test_build_key_is_stable(self):
        first = _build_key("search", {"query": "Fight Club", "page": 1})
        second = _build_key("search", {"page": 1, "query": "Fight Club"})

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("tmdb:search:"))

    def test_cache_hit_no_tmdb_call(self):
        cache, calls = self.make_cache()
        params = {
            "media_type": "all",
            "time_window": "week",
            "page": 1,
            "language": "en-US",
        }
        self.redis.set(_build_key("trending", params), '{"cached": true}')

        result = cache.get_trending()

        self.assertEqual(result, {"cached": True})
        self.assertEqual(calls, [])

    def test_cache_miss_calls_and_stores(self):
        body = {"page": 1, "results": [{"id": 550}]}
        cache, calls = self.make_cache(body)

        result = cache.get_trending()

        key = _build_key(
            "trending",
            {
                "media_type": "all",
                "time_window": "week",
                "page": 1,
                "language": "en-US",
            },
        )
        self.assertEqual(result, body)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.redis.get(key), '{"page": 1, "results": [{"id": 550}]}')
        self.assertGreater(self.redis.ttl(key), 0)

    def test_ttl_applied_per_endpoint(self):
        endpoint_calls = (
            ("trending", lambda cache: cache.get_trending()),
            ("now_playing", lambda cache: cache.get_now_playing()),
            ("discover", lambda cache: cache.discover("movie")),
            ("search", lambda cache: cache.search("Fight Club", "movie")),
            ("movie_detail", lambda cache: cache.get_movie_detail(550)),
            ("tv_detail", lambda cache: cache.get_tv_detail(1399)),
            ("keywords", lambda cache: cache.get_keywords(550, "movie")),
        )

        for endpoint, invoke in endpoint_calls:
            with self.subTest(endpoint=endpoint):
                cache, _ = self.make_cache({"endpoint": endpoint})
                invoke(cache)
                key_params = {
                    "trending": {"media_type": "all", "time_window": "week", "page": 1},
                    "now_playing": {"page": 1},
                    "discover": {
                        "tipo": "movie",
                        "genero": None,
                        "anio": None,
                        "min_rating": None,
                        "page": 1,
                        "anio_desde": None,
                        "anio_hasta": None,
                        "sort_by": None,
                    },
                    "search": {"query": "Fight Club", "tipo": "movie", "page": 1},
                    "movie_detail": {"id_tmdb": 550},
                    "tv_detail": {"id_tmdb": 1399},
                    "keywords": {"id_tmdb": 550, "tipo": "movie"},
                }[endpoint]
                if endpoint != "keywords":
                    key_params["language"] = "en-US"
                key = _build_key(endpoint, key_params)
                self.assertAlmostEqual(
                    self.redis.ttl(key), ENDPOINT_TTLS[endpoint], delta=1
                )

    def test_redis_get_failure_bypasses_cache(self):
        cache, calls = self.make_cache({"direct": True})

        def failing_get(key):
            raise redis.ConnectionError("offline")

        self.redis.get = failing_get

        self.assertEqual(cache.get_movie_detail(550), {"direct": True})
        self.assertEqual(len(calls), 1)

    def test_redis_set_failure_still_returns_result(self):
        cache, calls = self.make_cache({"direct": True})

        def failing_set(*args, **kwargs):
            raise redis.ConnectionError("offline")

        self.redis.set = failing_set

        self.assertEqual(cache.get_movie_detail(550), {"direct": True})
        self.assertEqual(len(calls), 1)

    def test_round_trip_preserves_structure(self):
        body = {"page": 1, "nested": {"genres": [28, 878], "adult": False}}
        cache, calls = self.make_cache(body)

        self.assertEqual(cache.get_tv_detail(1399), body)
        self.assertEqual(cache.get_tv_detail(1399), body)
        self.assertEqual(len(calls), 1)  # second call hit Redis, not TMDB

    def test_credits_se_cachea_por_id_y_tipo(self):
        cache, calls = self.make_cache(body={"cast": [{"name": "Brad Pitt"}]})

        primera = cache.get_credits(550, "movie")
        segunda = cache.get_credits(550, "movie")

        # La segunda llamada sale de Redis: una sola ida a TMDB.
        self.assertEqual(primera, segunda)
        self.assertEqual(len(calls), 1)

        # Distinto tipo con el mismo id es otra producción, no un cache hit.
        cache.get_credits(550, "tv")
        self.assertEqual(len(calls), 2)

    def test_credits_tiene_ttl_propio(self):
        self.assertIn("credits", ENDPOINT_TTLS)

        cache, _ = self.make_cache()
        cache.get_credits(550, "movie")
        key = _build_key("credits", {"id_tmdb": 550, "tipo": "movie"})

        self.assertEqual(self.redis.ttl(key), ENDPOINT_TTLS["credits"])

    def test_changes_se_cachea_por_tipo_y_pagina(self):
        cache, calls = self.make_cache(body={"page": 1, "results": [{"id": 550}]})

        primera = cache.get_changes("movie", page=1)
        segunda = cache.get_changes("movie", page=1)

        self.assertEqual(primera, segunda)
        self.assertEqual(len(calls), 1)

        # Otra página u otro tipo son otra lista, no un cache hit.
        cache.get_changes("movie", page=2)
        cache.get_changes("tv", page=1)
        self.assertEqual(len(calls), 3)

    def test_changes_tiene_ttl_propio(self):
        # Corto porque la lista rueda a diario; largo para que una tarea
        # reintentada no vuelva a bajar ~100 páginas.
        self.assertIn("changes", ENDPOINT_TTLS)

        cache, _ = self.make_cache()
        cache.get_changes("movie", page=1)
        key = _build_key("changes", {"tipo": "movie", "page": 1})

        self.assertEqual(self.redis.ttl(key), ENDPOINT_TTLS["changes"])

    def test_genres_se_cachea_por_tipo(self):
        cache, calls = self.make_cache(body={"genres": [{"id": 28, "name": "Action"}]})

        primera = cache.get_genres("movie")
        segunda = cache.get_genres("movie")

        self.assertEqual(primera, segunda)
        self.assertEqual(len(calls), 1)

        # Serie tiene otro catálogo de géneros: no es un cache hit.
        cache.get_genres("tv")
        self.assertEqual(len(calls), 2)

    def test_genres_tiene_el_ttl_mas_largo(self):
        # Los géneros de TMDB son prácticamente estáticos: no hay motivo para
        # volver a pedirlos todos los días.
        self.assertIn("genres", ENDPOINT_TTLS)
        self.assertGreater(ENDPOINT_TTLS["genres"], ENDPOINT_TTLS["movie_detail"])

        cache, _ = self.make_cache()
        cache.get_genres("movie")
        key = _build_key("genres", {"tipo": "movie", "language": "en-US"})

        self.assertEqual(self.redis.ttl(key), ENDPOINT_TTLS["genres"])

    def test_get_redis_passes_bounded_timeouts(self):
        with patch("catalogo.cache.redis.Redis.from_url") as from_url:
            get_redis()
            from_url.assert_called_once_with(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
                socket_timeout=REDIS_SOCKET_TIMEOUT,
            )


class ParamValidationTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("catalogo.views.get_catalog_service")
    def test_invalid_tipo_returns_400_without_service_call(self, get_service):
        request = self.factory.get("/api/catalogo/discover/?tipo=book")

        response = DiscoverView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        get_service.assert_not_called()

    def test_optional_integer_param_preserves_none_default(self):
        self.assertIsNone(_int_param(None, "genero", default=None))

    @patch("catalogo.views.get_catalog_service")
    def test_non_finite_min_rating_returns_400_without_service_call(self, get_service):
        request = self.factory.get("/api/catalogo/discover/?min_rating=nan")

        response = DiscoverView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        get_service.assert_not_called()

    def test_float_param_rejects_non_finite(self):
        with self.assertRaises(ValidationError):
            _float_param("inf", "min_rating")
        with self.assertRaises(ValidationError):
            _float_param("nan", "min_rating")

    @patch("catalogo.views.get_catalog_service")
    def test_non_integer_detail_id_returns_400_without_service_call(self, get_service):
        request = self.factory.get("/api/catalogo/movie/not-an-id/")

        response = MovieDetailView.as_view()(request, id_tmdb="not-an-id")

        self.assertEqual(response.status_code, 400)
        get_service.assert_not_called()

    @patch("catalogo.views.get_catalog_service")
    def test_missing_search_query_returns_400_without_service_call(self, get_service):
        request = self.factory.get("/api/catalogo/search/?tipo=movie")

        response = SearchView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        get_service.assert_not_called()


class EndpointIntegrationTest(SimpleTestCase):
    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        # Estos tests cubren el contrato HTTP de C-03 (passthrough de TMDB) y
        # corren sin base de datos. La materialización que C-04a agregó a las
        # vistas de detalle se anula acá para no arrastrar escrituras a
        # Postgres a un `SimpleTestCase`; tiene su propia cobertura en
        # `VistasDeDetalleMaterializanTests`.
        parche = patch("catalogo.views.materializar")
        parche.start()
        self.addCleanup(parche.stop)

    def _make_service(self, body=None):
        body = body or {"results": [{"id": 550, "title": "Fight Club"}]}

        def handler(request):
            return httpx.Response(200, json=body)

        client = TMDBClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )
        return TMDBClientCache(client, self.redis)

    def _get(self, url):
        from rest_framework.test import APIClient

        client = APIClient()
        with patch(
            "catalogo.views.get_catalog_service", return_value=self._make_service()
        ):
            return client.get(url)

    def test_trending_returns_200(self):
        response = self._get("/api/catalogo/trending/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["title"], "Fight Club")

    def test_now_playing_returns_200(self):
        response = self._get("/api/catalogo/now-playing/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)

    def test_discover_returns_200(self):
        response = self._get("/api/catalogo/discover/?tipo=movie")

        self.assertEqual(response.status_code, 200)

    def test_search_returns_200(self):
        response = self._get("/api/catalogo/search/?query=Fight%20Club&tipo=movie")

        self.assertEqual(response.status_code, 200)

    def test_movie_detail_returns_200(self):
        response = self._get("/api/catalogo/movie/550/")

        self.assertEqual(response.status_code, 200)

    def test_tv_detail_returns_200(self):
        response = self._get("/api/catalogo/tv/1399/")

        self.assertEqual(response.status_code, 200)

    def test_keywords_returns_200(self):
        response = self._get("/api/catalogo/keywords/?id_tmdb=550&tipo=movie")

        self.assertEqual(response.status_code, 200)

    @patch("catalogo.views.get_catalog_service")
    def test_non_integer_detail_id_returns_400_through_url_routing(self, get_service):
        """Un `id_tmdb` no entero debe dar 400, no 404 (spec de C-03).

        `ParamValidationTest` ya cubre el caso llamando a la vista en forma
        directa, por lo que no detecta un conversor de URL que rechace el
        request antes de llegar a ella: ambas rutas de detalle deben resolver
        y delegar la validación a `_int_param`.
        """
        from rest_framework.test import APIClient

        client = APIClient()
        for url in ("/api/catalogo/movie/not-an-id/", "/api/catalogo/tv/not-an-id/"):
            with self.subTest(url=url):
                response = client.get(url)

                self.assertEqual(response.status_code, 400)
        get_service.assert_not_called()

    def test_post_returns_405(self):
        from rest_framework.test import APIClient

        client = APIClient()
        response = client.post("/api/catalogo/trending/")

        self.assertEqual(response.status_code, 405)

    def _make_failing_service(self, exc_class, message="TMDB error"):
        def handler(request):
            if exc_class is TMDBTransportError:
                raise httpx.TransportError(message)
            status = {
                TMDBNotFound: 404,
                TMDBBadRequest: 400,
                TMDBRateLimited: 429,
                TMDBServerError: 500,
            }[exc_class]
            return httpx.Response(status)

        client = TMDBClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )
        return TMDBClientCache(client, self.redis)

    def test_tmdb_not_found_returns_404(self):
        from rest_framework.test import APIClient

        client = APIClient()
        with patch(
            "catalogo.views.get_catalog_service",
            return_value=self._make_failing_service(TMDBNotFound, "Not found"),
        ):
            response = client.get("/api/catalogo/movie/99999/")

        self.assertEqual(response.status_code, 404)

    def test_tmdb_bad_request_returns_400(self):
        from rest_framework.test import APIClient

        client = APIClient()
        with patch(
            "catalogo.views.get_catalog_service",
            return_value=self._make_failing_service(TMDBBadRequest, "Bad request"),
        ):
            response = client.get("/api/catalogo/discover/", {"tipo": "movie"})

        self.assertEqual(response.status_code, 400)

    def test_tmdb_rate_limited_returns_429(self):
        from rest_framework.test import APIClient

        client = APIClient()
        with patch(
            "catalogo.views.get_catalog_service",
            return_value=self._make_failing_service(TMDBRateLimited, "Rate limited"),
        ):
            response = client.get("/api/catalogo/trending/")

        self.assertEqual(response.status_code, 429)

    def test_tmdb_server_error_returns_502(self):
        from rest_framework.test import APIClient

        client = APIClient()
        with patch(
            "catalogo.views.get_catalog_service",
            return_value=self._make_failing_service(TMDBServerError, "Server error"),
        ):
            response = client.get("/api/catalogo/trending/")

        self.assertEqual(response.status_code, 502)

    def test_tmdb_transport_error_returns_503(self):
        from rest_framework.test import APIClient

        client = APIClient()
        with patch(
            "catalogo.views.get_catalog_service",
            return_value=self._make_failing_service(
                TMDBTransportError, "Transport error"
            ),
        ):
            response = client.get("/api/catalogo/trending/")

        self.assertEqual(response.status_code, 503)

    def test_throttle_exceeded_returns_429(self):
        from django.core.cache import cache as dj_cache
        from rest_framework.test import APIClient

        dj_cache.clear()
        client = APIClient()
        with (
            patch(
                "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
                {**ScopedRateThrottle.THROTTLE_RATES, "catalogo": "1/min"},
            ),
            patch(
                "catalogo.views.get_catalog_service", return_value=self._make_service()
            ),
        ):
            first = client.get("/api/catalogo/trending/")
            second = client.get("/api/catalogo/trending/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)


class AdapterTests(SimpleTestCase):
    """Única traducción entre el vocabulario de TMDB y el del dominio (C-04a).

    Existe para que ningún `"movie"` crudo termine guardado en la columna
    `tipo`: si eso pasa, las consultas por tipo dejan de encontrar la fila y
    el error no se nota hasta mucho después.
    """

    def test_traduce_de_tmdb_a_dominio(self):
        casos = (
            ("movie", TipoProduccion.PELICULA),
            ("tv", TipoProduccion.SERIE),
        )
        for tipo_tmdb, esperado in casos:
            with self.subTest(tipo_tmdb=tipo_tmdb):
                self.assertEqual(tmdb_a_dominio(tipo_tmdb), esperado)

    def test_traduce_de_dominio_a_tmdb(self):
        casos = (
            (TipoProduccion.PELICULA, "movie"),
            (TipoProduccion.SERIE, "tv"),
        )
        for tipo_dominio, esperado in casos:
            with self.subTest(tipo_dominio=tipo_dominio):
                self.assertEqual(dominio_a_tmdb(tipo_dominio), esperado)

    def test_ida_y_vuelta_conserva_el_valor(self):
        for tipo_tmdb in ("movie", "tv"):
            with self.subTest(tipo_tmdb=tipo_tmdb):
                self.assertEqual(dominio_a_tmdb(tmdb_a_dominio(tipo_tmdb)), tipo_tmdb)

    def test_rechaza_valores_desconocidos(self):
        # "all" es un filtro válido de discovery (C-03) pero NO un tipo de
        # producción: materializar algo "all" no significa nada.
        for invalido in ("all", "pelicula", "", None, "MOVIE"):
            with self.subTest(invalido=invalido), self.assertRaises(ValueError):
                tmdb_a_dominio(invalido)

    def test_rechaza_tipos_de_dominio_desconocidos(self):
        for invalido in ("movie", "documental", "", None):
            with self.subTest(invalido=invalido), self.assertRaises(ValueError):
                dominio_a_tmdb(invalido)


class TextoCanonicoTests(SimpleTestCase):
    """Texto que se embebe y su huella (C-04a).

    No toca la base: `construir_texto_canonico` recibe cualquier objeto con
    los atributos de una producción, así que se puede probar con un doble.
    """

    def _produccion(self, **overrides):
        datos = {
            "titulo": "Fight Club",
            "generos": ["Drama", "Thriller"],
            "directores": ["David Fincher"],
            "reparto": ["Edward Norton", "Brad Pitt"],
            "keywords": ["insomnia", "dual identity"],
            "sinopsis": "An insomniac office worker...",
        }
        datos.update(overrides)
        return SimpleNamespace(**datos)

    def test_incluye_las_seis_secciones_en_orden(self):
        texto = construir_texto_canonico(self._produccion())

        self.assertEqual(
            [linea.split(":")[0] for linea in texto.splitlines()],
            ["Title", "Genres", "Directors", "Cast", "Keywords", "Synopsis"],
        )

    def test_el_orden_de_los_arrays_no_altera_el_texto(self):
        # TMDB no garantiza un orden estable entre respuestas: sin normalizar,
        # el hash cambiaría solo, disparando regeneraciones infinitas.
        a = construir_texto_canonico(
            self._produccion(generos=["Drama", "Thriller"], reparto=["B", "A"])
        )
        b = construir_texto_canonico(
            self._produccion(generos=["Thriller", "Drama"], reparto=["A", "B"])
        )

        self.assertEqual(a, b)

    def test_ignora_entradas_vacias_o_con_espacios(self):
        texto = construir_texto_canonico(
            self._produccion(generos=["  Drama  ", "", "   "], sinopsis="  hola  ")
        )

        self.assertIn("Genres: Drama", texto)
        self.assertIn("Synopsis: hola", texto)

    def test_tolera_una_produccion_sin_datos_opcionales(self):
        texto = construir_texto_canonico(
            self._produccion(
                generos=[], directores=[], reparto=[], keywords=[], sinopsis=""
            )
        )

        self.assertIn("Title: Fight Club", texto)
        self.assertIn("Genres: ", texto)

    def test_hash_es_estable_y_sensible_al_contenido(self):
        texto = construir_texto_canonico(self._produccion())
        otro = construir_texto_canonico(self._produccion(titulo="Se7en"))

        self.assertEqual(calcular_source_hash(texto), calcular_source_hash(texto))
        self.assertNotEqual(calcular_source_hash(texto), calcular_source_hash(otro))
        # SHA-256 en hexadecimal: 64 caracteres, que es el max_length del campo.
        self.assertEqual(len(calcular_source_hash(texto)), 64)

    def test_el_proveedor_todavia_no_esta_implementado(self):
        # Contrato explícito para B-06: hasta que Marcos conecte Ollama, la
        # tarea de Celery captura esto y deja el embedding en `failed`.
        with self.assertRaises(NotImplementedError):
            generar_vector("cualquier texto")

    def test_hay_una_version_de_modelo_declarada(self):
        self.assertTrue(MODEL_VERSION)
        self.assertLessEqual(len(MODEL_VERSION), 50)


class GenerarEmbeddingTaskTests(TestCase):
    """Idempotencia de la tarea de Celery (C-04a).

    Celery entrega "al menos una vez": la misma tarea puede llegar dos veces
    (reinicio del worker) o a dos workers en paralelo. Cada test acá cubre una
    de esas formas de duplicación.
    """

    def setUp(self):
        self.produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="Fight Club",
            generos=["Drama"],
            sinopsis="An insomniac office worker...",
        )

    def _hash_actual(self):
        return calcular_source_hash(construir_texto_canonico(self.produccion))

    @patch("catalogo.tasks.generar_vector")
    def test_sin_fila_de_embedding_no_hace_nada(self, generar):
        # Puede pasar si la producción se borró entre el encolado y el consumo.
        generar_embedding(self.produccion.id)

        generar.assert_not_called()

    @patch("catalogo.tasks.generar_vector", return_value=[0.5] * 1024)
    def test_pendiente_genera_y_queda_ready(self, generar):
        ProduccionEmbedding.objects.create(produccion=self.produccion)

        generar_embedding(self.produccion.id)

        embedding = ProduccionEmbedding.objects.get(produccion=self.produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.READY)
        self.assertEqual(len(embedding.vector), 1024)
        self.assertEqual(embedding.source_hash, self._hash_actual())
        self.assertEqual(embedding.model_version, MODEL_VERSION)
        generar.assert_called_once()

    @patch("catalogo.tasks.generar_vector")
    def test_ready_con_mismo_hash_no_recalcula(self, generar):
        ProduccionEmbedding.objects.create(
            produccion=self.produccion,
            estado=EstadoEmbedding.READY,
            vector=[0.1] * 1024,
            source_hash=self._hash_actual(),
            model_version=MODEL_VERSION,
        )

        generar_embedding(self.produccion.id)

        # Nada cambió: no se gasta una llamada al proveedor.
        generar.assert_not_called()

    @patch("catalogo.tasks.generar_vector")
    def test_una_fila_ya_reclamada_no_se_procesa_dos_veces(self, generar):
        # `processing` = otro worker ya la agarró.
        ProduccionEmbedding.objects.create(
            produccion=self.produccion,
            estado=EstadoEmbedding.PROCESSING,
        )

        generar_embedding(self.produccion.id)

        generar.assert_not_called()
        embedding = ProduccionEmbedding.objects.get(produccion=self.produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.PROCESSING)

    @patch("catalogo.tasks.generar_vector", side_effect=RuntimeError("Ollama caído"))
    def test_si_el_proveedor_falla_queda_failed_y_no_rompe_el_worker(self, generar):
        ProduccionEmbedding.objects.create(produccion=self.produccion)

        # No propaga: si explotara, el worker reintentaría en loop.
        generar_embedding(self.produccion.id)

        embedding = ProduccionEmbedding.objects.get(produccion=self.produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.FAILED)
        self.assertIsNone(embedding.vector)
        # La producción sigue visible en el catálogo pase lo que pase.
        self.assertTrue(
            ProduccionAudiovisual.objects.filter(pk=self.produccion.pk).exists()
        )

    def test_con_el_stub_real_queda_failed(self):
        # Sin mocks: hoy `generar_vector` lanza NotImplementedError (B-06).
        ProduccionEmbedding.objects.create(produccion=self.produccion)

        generar_embedding(self.produccion.id)

        embedding = ProduccionEmbedding.objects.get(produccion=self.produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.FAILED)

    @patch("catalogo.tasks.generar_vector", return_value=[0.5] * 1024)
    def test_un_failed_se_reintenta(self, generar):
        # El backfill de C-04b reencola los fallidos: tienen que ser
        # reclamables igual que los pendientes.
        ProduccionEmbedding.objects.create(
            produccion=self.produccion, estado=EstadoEmbedding.FAILED
        )

        generar_embedding(self.produccion.id)

        embedding = ProduccionEmbedding.objects.get(produccion=self.produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.READY)
        generar.assert_called_once()

    @patch("catalogo.tasks.generar_vector", return_value=[0.5] * 1024)
    def test_dos_ejecuciones_seguidas_llaman_al_proveedor_una_sola_vez(self, generar):
        ProduccionEmbedding.objects.create(produccion=self.produccion)

        generar_embedding(self.produccion.id)
        generar_embedding(self.produccion.id)

        self.assertEqual(generar.call_count, 1)
        self.assertEqual(ProduccionEmbedding.objects.count(), 1)


class BackfillEmbeddingsTests(TestCase):
    """Recuperación del trabajo de embeddings que quedó sin completar (C-04b, fase 3).

    `materializar()` encola el embedding UNA sola vez, cuando crea la fila. Si
    en ese momento el broker estaba caído o el proveedor falló, esa fila no la
    reintenta nadie: `get_or_create` devuelve `creado=False` para siempre. El
    backfill es lo que la rescata.

    `generar_embedding` va parcheada: acá se prueba a quién se reencola, no qué
    hace el worker después (eso tiene su propia suite).
    """

    def setUp(self):
        parche = patch("catalogo.tasks.generar_embedding")
        self.tarea = parche.start()
        self.addCleanup(parche.stop)

    def _embedding(self, id_tmdb, estado=EstadoEmbedding.PENDING, **extra):
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=id_tmdb,
            tipo=TipoProduccion.PELICULA,
            titulo=f"Peli {id_tmdb}",
            generos=["Drama"],
            sinopsis="Una sinopsis.",
        )
        if estado == EstadoEmbedding.READY:
            extra.setdefault("vector", [0.5] * 1024)
            extra.setdefault("model_version", MODEL_VERSION)
            extra.setdefault(
                "source_hash",
                calcular_source_hash(construir_texto_canonico(produccion)),
            )
        return ProduccionEmbedding.objects.create(
            produccion=produccion, estado=estado, **extra
        )

    def _ids_encolados(self):
        return {c.args[0] for c in self.tarea.delay.call_args_list}

    def test_reencola_los_pendientes_y_los_fallidos(self):
        pendiente = self._embedding(1, EstadoEmbedding.PENDING)
        fallido = self._embedding(2, EstadoEmbedding.FAILED)

        estadisticas = backfill_embeddings()

        self.assertEqual(
            self._ids_encolados(),
            {pendiente.produccion_id, fallido.produccion_id},
        )
        self.assertEqual(estadisticas["reencolados"], 2)

    def test_no_toca_los_que_ya_estan_en_proceso(self):
        # `processing` significa que otro worker la agarró hace un momento.
        # Reencolarla no la duplicaría (el claim atómico lo impide), pero
        # llenaría la cola de trabajo que alguien ya está haciendo.
        self._embedding(1, EstadoEmbedding.PROCESSING)

        backfill_embeddings()

        self.tarea.delay.assert_not_called()

    def test_un_ready_al_dia_no_se_toca(self):
        # Mismo texto y mismo modelo: el vector guardado sigue siendo válido.
        self._embedding(1, EstadoEmbedding.READY)

        estadisticas = backfill_embeddings()

        self.tarea.delay.assert_not_called()
        self.assertEqual(estadisticas["reencolados"], 0)

    def test_un_ready_cuyo_texto_cambio_se_reencola(self):
        # El caso real: la sync refrescó la producción desde TMDB y ahora tiene
        # otra sinopsis o más reparto. El vector quedó describiendo un texto
        # que ya no existe.
        embedding = self._embedding(1, EstadoEmbedding.READY)
        ProduccionAudiovisual.objects.filter(pk=embedding.produccion_id).update(
            sinopsis="Otra sinopsis completamente distinta."
        )

        estadisticas = backfill_embeddings()

        self.assertEqual(self._ids_encolados(), {embedding.produccion_id})
        self.assertEqual(estadisticas["desactualizados"], 1)

    def test_un_ready_de_otra_version_de_modelo_se_reencola(self):
        # El día que B-06 cambie MODEL_VERSION: los vectores viejos no son
        # comparables con los nuevos, así que hay que regenerarlos todos.
        embedding = self._embedding(
            1, EstadoEmbedding.READY, model_version="modelo-viejo-v0"
        )

        backfill_embeddings()

        self.assertEqual(self._ids_encolados(), {embedding.produccion_id})

    def test_el_limite_topea_cuantas_se_procesan_por_corrida(self):
        # Con 10.000 filas, una corrida sin tope encolaría 10.000 tareas de
        # golpe y dejaría al worker sin hacer otra cosa por horas.
        for id_tmdb in range(1, 6):
            self._embedding(id_tmdb, EstadoEmbedding.FAILED)

        estadisticas = backfill_embeddings(limite=2)

        self.assertEqual(self.tarea.delay.call_count, 2)
        self.assertEqual(estadisticas["reencolados"], 2)

    def test_el_limite_cuenta_las_dos_poblaciones_juntas(self):
        # El tope es del trabajo total de la corrida, no de cada grupo: si los
        # pendientes ya lo llenaron, los `ready` desactualizados esperan a la
        # próxima noche.
        self._embedding(1, EstadoEmbedding.PENDING)
        desactualizado = self._embedding(2, EstadoEmbedding.READY)
        ProduccionAudiovisual.objects.filter(pk=desactualizado.produccion_id).update(
            sinopsis="Otra sinopsis."
        )

        estadisticas = backfill_embeddings(limite=1)

        self.assertEqual(self.tarea.delay.call_count, 1)
        self.assertEqual(estadisticas["desactualizados"], 0)

    def test_procesa_las_mas_viejas_primero(self):
        # El backfill promete procesar las más viejas primero (por
        # fecha_actualizacion ascendente). Si hay 150 pendientes y el límite es
        # 100, debe procesar las 100 más viejas, no las 100 más nuevas.
        viejo = self._embedding(1, EstadoEmbedding.FAILED)
        ProduccionEmbedding.objects.filter(pk=viejo.pk).update(
            fecha_actualizacion=timezone.now() - timedelta(days=2)
        )

        medio = self._embedding(2, EstadoEmbedding.FAILED)
        ProduccionEmbedding.objects.filter(pk=medio.pk).update(
            fecha_actualizacion=timezone.now() - timedelta(days=1)
        )

        # El tercero tiene fecha_actualizacion = ahora (auto_now), así que es
        # el más nuevo y no debe ser procesado con límite 2.
        self._embedding(3, EstadoEmbedding.FAILED)

        estadisticas = backfill_embeddings(limite=2)

        # Solo se encolaron los 2 más viejos
        self.assertEqual(
            self._ids_encolados(),
            {viejo.produccion_id, medio.produccion_id},
        )
        self.assertEqual(estadisticas["reencolados"], 2)

    def test_si_no_hay_nada_no_hace_nada(self):
        # Caso borde: si no hay pending, failed, ni ready desactualizados, el
        # backfill debe retornar estadísticas en cero sin errores.
        self._embedding(1, EstadoEmbedding.READY)

        estadisticas = backfill_embeddings()

        self.tarea.delay.assert_not_called()
        self.assertEqual(estadisticas["reencolados"], 0)
        self.assertEqual(estadisticas["desactualizados"], 0)

    def test_el_restante_se_usa_para_ready_desactualizados(self):
        # Si hay 3 pendientes y 5 ready desactualizados con límite 5, debe
        # encolar 3 pendientes + 2 ready = 5 total. Verifica que el cálculo de
        # `restante` funciona correctamente con números realistas.
        for id_tmdb in range(1, 4):
            self._embedding(id_tmdb, EstadoEmbedding.FAILED)

        for id_tmdb in range(10, 15):
            desactualizado = self._embedding(id_tmdb, EstadoEmbedding.READY)
            ProduccionAudiovisual.objects.filter(
                pk=desactualizado.produccion_id
            ).update(sinopsis=f"Sinopsis {id_tmdb}")

        estadisticas = backfill_embeddings(limite=5)

        self.assertEqual(self.tarea.delay.call_count, 5)
        self.assertEqual(estadisticas["reencolados"], 5)
        self.assertEqual(estadisticas["desactualizados"], 2)


class BackfillIntegracionTests(TestCase):
    """El backfill con `generar_embedding` REAL: que el reencolado sirva.

    Los tests de arriba parchean la tarea y prueban A QUIÉN se reencola. Este
    prueba que reencolarlo alcance: `generar_embedding` solo reclama filas en
    `pending`/`failed`, así que un `ready` desactualizado que llegue al worker
    tal cual sale sin hacer nada y el vector viejo se queda para siempre.
    """

    def _delay_ejecuta_de_verdad(self):
        # `.delay()` normalmente escribe en el broker; acá ejecuta el cuerpo de
        # la tarea en el acto, que es lo que haría el worker al levantarla.
        return patch(
            "catalogo.tasks.generar_embedding.delay", side_effect=generar_embedding
        )

    @patch("catalogo.tasks.generar_vector", return_value=[0.25] * 1024)
    def test_un_ready_desactualizado_termina_con_el_vector_nuevo(self, _):
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="Fight Club",
            generos=["Drama"],
            sinopsis="Sinopsis vieja.",
        )
        ProduccionEmbedding.objects.create(
            produccion=produccion,
            estado=EstadoEmbedding.READY,
            vector=[0.5] * 1024,
            model_version=MODEL_VERSION,
            source_hash=calcular_source_hash(construir_texto_canonico(produccion)),
        )
        # La sync refrescó la producción: el texto canónico ya es otro.
        ProduccionAudiovisual.objects.filter(pk=produccion.pk).update(
            sinopsis="Sinopsis nueva, traída de TMDB."
        )
        produccion.refresh_from_db()

        with self._delay_ejecuta_de_verdad():
            backfill_embeddings()

        embedding = ProduccionEmbedding.objects.get(produccion=produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.READY)
        self.assertEqual(
            embedding.source_hash,
            calcular_source_hash(construir_texto_canonico(produccion)),
        )
        self.assertEqual(embedding.vector[0], 0.25)

    @patch("catalogo.tasks.generar_vector", return_value=[0.25] * 1024)
    def test_un_fallido_termina_ready(self, _):
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=551,
            tipo=TipoProduccion.PELICULA,
            titulo="Se7en",
            generos=["Thriller"],
            sinopsis="Una sinopsis.",
        )
        ProduccionEmbedding.objects.create(
            produccion=produccion, estado=EstadoEmbedding.FAILED
        )

        with self._delay_ejecuta_de_verdad():
            backfill_embeddings()

        embedding = ProduccionEmbedding.objects.get(produccion=produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.READY)


class ProduccionEmbeddingModelTests(TestCase):
    """Garantías que aporta la base de datos, no el código Python (C-04a).

    Se prueban contra Postgres real (de ahí `TestCase` y no `SimpleTestCase`)
    porque son restricciones del esquema: aunque alguien inserte por fuera del
    ORM, tienen que seguir cumpliéndose.
    """

    def setUp(self):
        self.produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="Fight Club",
        )

    def test_nace_pendiente_y_sin_vector(self):
        embedding = ProduccionEmbedding.objects.create(produccion=self.produccion)

        self.assertEqual(embedding.estado, EstadoEmbedding.PENDING)
        self.assertIsNone(embedding.vector)
        self.assertEqual(embedding.source_hash, "")
        self.assertEqual(embedding.model_version, "")

    def test_se_accede_desde_la_produccion_como_embedding(self):
        ProduccionEmbedding.objects.create(produccion=self.produccion)
        self.produccion.refresh_from_db()

        self.assertEqual(self.produccion.embedding.produccion_id, self.produccion.id)

    def test_una_sola_fila_de_embedding_por_produccion(self):
        ProduccionEmbedding.objects.create(produccion=self.produccion)

        # `transaction.atomic` aísla el error: sin él, el fallo dejaría la
        # transacción del test rota para las consultas siguientes.
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProduccionEmbedding.objects.create(produccion=self.produccion)

        self.assertEqual(ProduccionEmbedding.objects.count(), 1)

    def test_estado_ready_exige_vector(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProduccionEmbedding.objects.create(
                produccion=self.produccion,
                estado=EstadoEmbedding.READY,
                vector=None,
            )

    def test_estado_ready_con_vector_es_valido(self):
        embedding = ProduccionEmbedding.objects.create(
            produccion=self.produccion,
            estado=EstadoEmbedding.READY,
            vector=[0.0] * 1024,
            source_hash="a" * 64,
            model_version="stub-v1",
        )
        embedding.refresh_from_db()

        self.assertEqual(embedding.estado, EstadoEmbedding.READY)
        self.assertEqual(len(embedding.vector), 1024)

    def test_borrar_la_produccion_borra_su_embedding(self):
        ProduccionEmbedding.objects.create(produccion=self.produccion)

        self.produccion.delete()

        self.assertEqual(ProduccionEmbedding.objects.count(), 0)


# ---------------------------------------------------------------------------
# Materialización on-demand (C-04a, fase 5)
# ---------------------------------------------------------------------------
# Respuestas de TMDB recortadas a los campos que consume el enriquecimiento.
# El reparto de la película trae 12 personas a propósito: el mapeo se queda con
# las 10 primeras, que en TMDB vienen ordenadas por `order` (billing).

_DETALLE_MOVIE = {
    "id": 550,
    "title": "Fight Club",
    "poster_path": "/fight-club.jpg",
    "overview": "An insomniac office worker...",
    "release_date": "1999-10-15",
    "status": "Released",
    "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
    "vote_average": 8.4,
    "runtime": 139,
}

_CREDITS_MOVIE = {
    "cast": [{"name": f"Actor {numero:02d}"} for numero in range(1, 13)],
    "crew": [
        {"name": "David Fincher", "job": "Director"},
        {"name": "Jim Uhls", "job": "Screenplay"},
    ],
}

_KEYWORDS_MOVIE = {"keywords": [{"name": "insomnia"}, {"name": "dual identity"}]}

_DETALLE_TV = {
    "id": 1396,
    "name": "Breaking Bad",
    "poster_path": "/breaking-bad.jpg",
    "overview": "A chemistry teacher diagnosed with cancer...",
    "first_air_date": "2008-01-20",
    "status": "Ended",
    "genres": [{"id": 18, "name": "Drama"}],
    "vote_average": 8.9,
    "number_of_seasons": 5,
    "number_of_episodes": 62,
    "episode_run_time": [47],
    # Quien firma una serie. TMDB lo publica acá, no en el crew.
    "created_by": [{"id": 66633, "name": "Vince Gilligan"}],
}

# El crew de una serie NO trae `job: "Director"`: en TV los directores son por
# episodio, así que TMDB no los expone a nivel serie. Verificado contra la API
# real el 15/09/2026 — `/tv/1396/credits` devuelve Executive Producer, Casting,
# Costume Design y demás, ningún Director. Este fixture lo refleja: cuando
# llevaba un Director inventado, los tests pasaban y la realidad no.
_CREDITS_TV = {
    "cast": [{"name": "Bryan Cranston"}, {"name": "Aaron Paul"}],
    "crew": [
        {"name": "Michelle MacLaren", "job": "Executive Producer"},
        {"name": "Dave Porter", "job": "Original Music Composer"},
    ],
}

# Mismo contenido que en películas, pero TMDB lo devuelve bajo otra clave.
_KEYWORDS_TV = {"results": [{"name": "new mexico"}, {"name": "drug dealer"}]}

# Lo que devuelven los LISTADOS de TMDB, contrastado contra la API real el
# 17/09/2026. Son resúmenes: traen `id`, `title`/`name`, `overview`,
# `genre_ids` (IDs numéricos), pero NO géneros con nombre, créditos ni keywords.
# Por eso la sync no escribe desde acá: llama a `materializar()` por ítem.
#
# Solo `trending/all` trae `media_type`, y la documentación de TMDB dice que
# puede incluir `person` (gente, no producciones). En las otras tres fuentes el
# tipo está implícito en el endpoint.
_LISTADO_TRENDING = {
    "page": 1,
    "results": [
        {"id": 550, "media_type": "movie", "title": "Fight Club"},
        {"id": 1396, "media_type": "tv", "name": "Breaking Bad"},
        {"id": 287, "media_type": "person", "name": "Brad Pitt"},
    ],
    "total_pages": 1,
}
_LISTADO_NOW_PLAYING = {
    "page": 1,
    "results": [{"id": 27205, "title": "Inception"}],
    "total_pages": 1,
}
_LISTADO_DISCOVER_MOVIE = {
    "page": 1,
    "results": [{"id": 155, "title": "The Dark Knight"}],
    "total_pages": 1,
}
_LISTADO_DISCOVER_TV = {
    "page": 1,
    "results": [{"id": 1399, "name": "Game of Thrones"}],
    "total_pages": 1,
}


def _pagina_de_cambios(pagina, total_pages, ids):
    """Una página de `/{tipo}/changes` con la forma real (17/09/2026)."""
    return {
        "page": pagina,
        "total_pages": total_pages,
        "results": [{"id": id_tmdb, "adult": False} for id_tmdb in ids],
    }


def _servicio_tmdb_falso():
    """Doble del `TMDBClientCache`: enriquecimiento (C-04a) y listados (C-04b)."""
    return Mock(
        get_movie_detail=Mock(return_value=_DETALLE_MOVIE),
        get_tv_detail=Mock(return_value=_DETALLE_TV),
        get_credits=Mock(
            side_effect=lambda id_tmdb, tipo: (
                _CREDITS_MOVIE if tipo == "movie" else _CREDITS_TV
            )
        ),
        get_keywords=Mock(
            side_effect=lambda id_tmdb, tipo: (
                _KEYWORDS_MOVIE if tipo == "movie" else _KEYWORDS_TV
            )
        ),
        get_trending=Mock(return_value=_LISTADO_TRENDING),
        get_now_playing=Mock(return_value=_LISTADO_NOW_PLAYING),
        # discover_listado: devuelve el listado correcto según el tipo (movie o tv)
        discover=Mock(
            side_effect=lambda tipo, **kwargs: (
                _LISTADO_DISCOVER_MOVIE if tipo == "movie" else _LISTADO_DISCOVER_TV
            )
        ),
        # Sin cambios por defecto: la pasada de refresco no toca nada salvo
        # que un test diga lo contrario.
        get_changes=Mock(side_effect=lambda tipo, page: _pagina_de_cambios(1, 1, [])),
    )


class _ParchesDeMaterializacion:
    """Aísla la materialización de TMDB y del broker de Celery.

    Es un mixin para poder combinarlo tanto con `TestCase` como con
    `TransactionTestCase`, según lo que necesite cada grupo de tests.
    """

    def setUp(self):
        super().setUp()
        self.servicio = _servicio_tmdb_falso()
        parche_servicio = patch(
            "catalogo.services.materialization.get_catalog_service",
            return_value=self.servicio,
        )
        parche_tarea = patch("catalogo.services.materialization.generar_embedding")
        parche_servicio.start()
        self.tarea = parche_tarea.start()
        self.addCleanup(parche_servicio.stop)
        self.addCleanup(parche_tarea.stop)


class MaterializacionBase(_ParchesDeMaterializacion, TestCase):
    """Base de los tests que verifican qué queda escrito en Postgres.

    Se usa `TestCase` (y no `SimpleTestCase`) porque acá lo que se prueba es
    justamente el estado de la base después de materializar.
    """


class MaterializacionPeliculaTests(MaterializacionBase):
    """Alta de una película nueva: mapeo de campos y encolado (C-04a)."""

    def test_mapea_los_campos_del_detalle(self):
        produccion = materializar(550, "movie")

        self.assertEqual(produccion.id_tmdb, 550)
        self.assertEqual(produccion.tipo, TipoProduccion.PELICULA)
        self.assertEqual(produccion.titulo, "Fight Club")
        self.assertEqual(produccion.poster, "/fight-club.jpg")
        self.assertEqual(produccion.sinopsis, "An insomniac office worker...")
        self.assertEqual(str(produccion.fecha_lanzamiento), "1999-10-15")
        self.assertEqual(produccion.estatus, "Released")
        self.assertEqual(produccion.generos, ["Drama", "Thriller"])
        self.assertEqual(produccion.calificacion_promedio, 8.4)
        self.assertEqual(produccion.duracion, 139)

    def test_una_pelicula_no_tiene_temporadas_ni_episodios(self):
        produccion = materializar(550, "movie")

        self.assertIsNone(produccion.cantidad_temporadas)
        self.assertIsNone(produccion.cantidad_episodios)

    def test_reparto_se_recorta_a_diez_y_directores_se_filtran_por_job(self):
        produccion = materializar(550, "movie")

        self.assertEqual(len(produccion.reparto), 10)
        self.assertEqual(produccion.reparto[0], "Actor 01")
        self.assertEqual(produccion.directores, ["David Fincher"])

    def test_keywords_de_pelicula_salen_de_la_clave_keywords(self):
        produccion = materializar(550, "movie")

        self.assertEqual(produccion.keywords, ["insomnia", "dual identity"])

    def test_crea_el_embedding_pendiente_y_lo_encola_una_sola_vez(self):
        # `captureOnCommitCallbacks(execute=True)` ejecuta los callbacks de
        # `on_commit` al salir del bloque. Hace falta porque `TestCase` envuelve
        # cada test en una transacción que revierte a propósito: sin COMMIT,
        # Django nunca correría el callback y el encolado no ocurriría.
        with self.captureOnCommitCallbacks(execute=True):
            produccion = materializar(550, "movie")

        embedding = ProduccionEmbedding.objects.get(produccion=produccion)
        self.assertEqual(embedding.estado, EstadoEmbedding.PENDING)
        self.assertIsNone(embedding.vector)
        self.tarea.delay.assert_called_once_with(produccion.id)

    def test_el_encolado_espera_a_que_la_transaccion_se_confirme(self):
        """El worker nunca debe recibir el id de una fila que aún no existe.

        `generar_embedding` corre en otro proceso, con otra conexión: si el
        mensaje sale antes del COMMIT, el worker busca la fila, no la encuentra
        y se va sin generar nada. Encolar en `on_commit` lo vuelve imposible.
        """
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            materializar(550, "movie")
            # Todavía dentro de la transacción: no puede haberse encolado nada.
            self.tarea.delay.assert_not_called()

        # Y el encolado quedó registrado para ejecutarse al confirmar.
        self.assertEqual(len(callbacks), 1)

    def test_fecha_de_lanzamiento_vacia_queda_en_null(self):
        # TMDB devuelve "" (no null) para estrenos sin fecha confirmada.
        self.servicio.get_movie_detail.return_value = {
            **_DETALLE_MOVIE,
            "release_date": "",
        }

        produccion = materializar(550, "movie")

        self.assertIsNone(produccion.fecha_lanzamiento)

    def test_la_fila_queda_persistida(self):
        materializar(550, "movie")

        self.assertTrue(
            ProduccionAudiovisual.objects.filter(
                id_tmdb=550, tipo=TipoProduccion.PELICULA
            ).exists()
        )


class MaterializacionTiposDeCampoTests(MaterializacionBase):
    """La fila que `materializar()` DEVUELVE tiene los tipos de la base.

    TMDB manda las fechas como texto (`"1999-10-15"`), y asignar ese string a
    un `DateField` deja el objeto en memoria con un `str` hasta que alguien lo
    relee. Quien serialice el valor de retorno se lleva el string: le pasaba al
    `POST /api/lists/{id}/items/` de L-01, que hacía
    `ListaItemSerializer(item).data` sobre la producción recién materializada y
    moría con `AttributeError: 'str' object has no attribute 'year'` — un 500
    al agregar a una lista cualquier producción que no estuviera ya en la base.

    Lo destapó el test de integración de C-08 (26/09/2026). No se veía antes
    porque los tests de listas usan `ProduccionAudiovisualFactory`, que escribe
    un `date` de verdad, o mockean `materializar()` entera.
    """

    def test_la_fila_devuelta_trae_fecha_lanzamiento_como_date(self):
        produccion = materializar(550, "movie")

        self.assertIsInstance(produccion.fecha_lanzamiento, date)
        self.assertEqual(produccion.fecha_lanzamiento, date(1999, 10, 15))

    def test_la_fila_devuelta_se_puede_serializar_sin_releerla(self):
        # El caso de L-01 en una línea: `.year` sobre lo que devuelve la
        # materialización, sin pasar por la base.
        produccion = materializar(550, "movie")

        self.assertEqual(produccion.fecha_lanzamiento.year, 1999)

    def test_una_produccion_sin_fecha_sigue_quedando_en_none(self):
        # TMDB omite `release_date` en títulos sin estrenar y a veces manda "".
        self.servicio.get_movie_detail.return_value = {
            **_DETALLE_MOVIE,
            "release_date": "",
        }

        produccion = materializar(550, "movie")

        self.assertIsNone(produccion.fecha_lanzamiento)


class MaterializacionSerieTests(MaterializacionBase):
    """Alta de una serie: TMDB usa otras claves para la misma información."""

    def test_mapea_los_campos_propios_de_una_serie(self):
        produccion = materializar(1396, "tv")

        self.assertEqual(produccion.tipo, TipoProduccion.SERIE)
        # `name` en vez de `title`, `first_air_date` en vez de `release_date`.
        self.assertEqual(produccion.titulo, "Breaking Bad")
        self.assertEqual(str(produccion.fecha_lanzamiento), "2008-01-20")
        self.assertEqual(produccion.cantidad_temporadas, 5)
        self.assertEqual(produccion.cantidad_episodios, 62)
        # Una serie no tiene `runtime`: se usa el primer `episode_run_time`.
        self.assertEqual(produccion.duracion, 47)

    def test_keywords_de_serie_salen_de_la_clave_results(self):
        produccion = materializar(1396, "tv")

        self.assertEqual(produccion.keywords, ["new mexico", "drug dealer"])

    def test_directores_de_serie_salen_de_created_by(self):
        # Sin esto, `Directors:` quedaría vacío en el texto canónico de TODA
        # serie y nadie podría encontrarlas por su autor.
        produccion = materializar(1396, "tv")

        self.assertEqual(produccion.directores, ["Vince Gilligan"])

    def test_serie_sin_created_by_cae_al_crew(self):
        # Algunas miniseries y documentales sí traen un Director en el crew.
        self.servicio.get_tv_detail.return_value = {
            **_DETALLE_TV,
            "created_by": [],
        }
        self.servicio.get_credits.side_effect = None
        self.servicio.get_credits.return_value = {
            "cast": [],
            "crew": [{"name": "Ava DuVernay", "job": "Director"}],
        }

        produccion = materializar(1396, "tv")

        self.assertEqual(produccion.directores, ["Ava DuVernay"])

    def test_serie_sin_autor_conocido_queda_vacia(self):
        self.servicio.get_tv_detail.return_value = {**_DETALLE_TV, "created_by": []}

        produccion = materializar(1396, "tv")

        self.assertEqual(produccion.directores, [])

    def test_serie_sin_duracion_de_episodio_queda_en_null(self):
        self.servicio.get_tv_detail.return_value = {
            **_DETALLE_TV,
            "episode_run_time": [],
        }

        produccion = materializar(1396, "tv")

        self.assertIsNone(produccion.duracion)

    def test_consulta_los_endpoints_de_series(self):
        materializar(1396, "tv")

        self.servicio.get_tv_detail.assert_called_once_with(1396)
        self.servicio.get_movie_detail.assert_not_called()
        self.servicio.get_credits.assert_called_once_with(1396, "tv")
        self.servicio.get_keywords.assert_called_once_with(1396, "tv")


class MaterializacionIdempotenteTests(MaterializacionBase):
    """Abrir dos veces el mismo detalle no duplica ni reencola nada (C-04a)."""

    def test_fila_existente_y_completa_no_vuelve_a_consultar_tmdb(self):
        # "Completa" es un hecho registrado, no una deducción a partir del
        # título: lo declara `fecha_enriquecimiento` (C-04b, fase 1).
        ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="Fight Club",
            fecha_enriquecimiento=timezone.now(),
        )

        materializar(550, "movie")

        self.servicio.get_movie_detail.assert_not_called()
        self.servicio.get_credits.assert_not_called()
        self.servicio.get_keywords.assert_not_called()

    def test_forzar_reenriquece_una_fila_que_el_criterio_saltearia(self):
        # La puerta por la que la sync refresca lo que TMDB reporta como
        # cambiado, aunque `fecha_enriquecimiento` sea reciente. Sin esto, la
        # sync tendría que borrar la fecha (acción a distancia) o escribir por
        # su cuenta (el segundo camino de escritura que el spec prohíbe).
        hace_una_hora = timezone.now() - timedelta(hours=1)
        ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="Fight Club",
            fecha_enriquecimiento=hace_una_hora,
        )

        produccion = materializar(550, "movie", forzar=True)

        self.servicio.get_movie_detail.assert_called_once_with(550)
        self.assertEqual(produccion.directores, ["David Fincher"])
        self.assertGreater(produccion.fecha_enriquecimiento, hace_una_hora)

    def test_materializar_dos_veces_deja_una_fila_y_un_embedding(self):
        primera = materializar(550, "movie")
        segunda = materializar(550, "movie")

        self.assertEqual(primera.pk, segunda.pk)
        self.assertEqual(ProduccionAudiovisual.objects.count(), 1)
        self.assertEqual(ProduccionEmbedding.objects.count(), 1)

    def test_no_reencola_si_el_embedding_ya_existia(self):
        with self.captureOnCommitCallbacks(execute=True):
            materializar(550, "movie")
        self.tarea.delay.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            materializar(550, "movie")

        self.tarea.delay.assert_not_called()

    def test_fila_incompleta_se_repara_con_datos_de_tmdb(self):
        # Con título pero sin `fecha_enriquecimiento`: la forma exacta de una
        # fila nacida de un listado de TMDB, que trae título pero no géneros,
        # reparto ni keywords. Con el criterio viejo (`not titulo`) esta fila
        # habría contado como completa para siempre.
        ProduccionAudiovisual.objects.create(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Fight Club"
        )

        produccion = materializar(550, "movie")

        # Se verifica sobre lo que un listado NO puede traer: si el reparto y
        # los directores aparecen, el detalle se pidió de verdad.
        self.assertEqual(produccion.directores, ["David Fincher"])
        self.assertEqual(len(produccion.reparto), 10)
        self.assertIsNotNone(produccion.fecha_enriquecimiento)
        self.assertEqual(ProduccionAudiovisual.objects.count(), 1)

    def test_tipo_no_soportado_no_materializa_nada(self):
        with self.assertRaises(ValueError):
            materializar(550, "all")

        self.assertEqual(ProduccionAudiovisual.objects.count(), 0)


class MaterializacionCarreraTests(MaterializacionBase):
    """Dos requests simultáneos sobre la misma producción (C-04a).

    La constraint `uq_produccion_tmdb_tipo` garantiza que solo uno inserte; lo
    que se prueba acá es que el que pierde se recupere en vez de reventar.
    """

    def test_colision_de_insert_devuelve_la_fila_que_gano(self):
        ganadora = ProduccionAudiovisual.objects.create(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Fight Club"
        )

        # La búsqueda previa no la ve (cuando consultamos todavía no existía) y
        # el INSERT choca contra la constraint; el rescate sí la encuentra.
        with (
            patch(
                "catalogo.services.materialization._buscar_produccion",
                side_effect=[None, ganadora],
            ),
            patch.object(
                ProduccionAudiovisual.objects,
                "create",
                side_effect=IntegrityError("uq_produccion_tmdb_tipo"),
            ),
        ):
            produccion = materializar(550, "movie")

        self.assertEqual(produccion.pk, ganadora.pk)
        self.assertEqual(ProduccionAudiovisual.objects.count(), 1)

    def test_un_integrityerror_ajeno_a_la_carrera_se_propaga(self):
        # Si tras la colisión la fila sigue sin aparecer, el error no venía de
        # la carrera y disfrazarlo de "ya existía" ocultaría un bug real.
        with (
            patch(
                "catalogo.services.materialization._buscar_produccion",
                side_effect=[None, None],
            ),
            patch.object(
                ProduccionAudiovisual.objects,
                "create",
                side_effect=IntegrityError("otra violación cualquiera"),
            ),
            self.assertRaises(IntegrityError),
        ):
            materializar(550, "movie")


class MaterializacionFrescuraTests(SimpleTestCase):
    """Cuándo una fila necesita (re)traer el detalle de TMDB (C-04b, fase 1).

    `_necesita_enriquecimiento()` es una decisión pura sobre un atributo, así
    que se prueba sin base de datos, con un objeto que finge ser la producción.

    Reemplaza el criterio de C-04a (`not titulo`), que dejaba de servir en
    cuanto la sync creara filas desde listados: esas traen título pero no
    géneros, reparto ni keywords, y con el criterio viejo contaban como
    completas para siempre.
    """

    def _produccion(self, fecha_enriquecimiento):
        # Con título a propósito: así el criterio viejo (`not titulo`) dice
        # "completa" y el RED falla por aserción, no por un AttributeError.
        return SimpleNamespace(
            titulo="Fight Club", fecha_enriquecimiento=fecha_enriquecimiento
        )

    def test_una_fila_que_nunca_se_enriquecio_lo_necesita(self):
        self.assertTrue(_necesita_enriquecimiento(self._produccion(None)))

    def test_una_fila_recien_enriquecida_no_lo_necesita(self):
        self.assertFalse(_necesita_enriquecimiento(self._produccion(timezone.now())))

    def test_una_fila_mas_vieja_que_la_red_de_seguridad_lo_necesita(self):
        # La ventana es solo una red de seguridad: lo que cambió de verdad lo
        # dice la lista de cambios de TMDB (fase 2). Pero si esa lista se
        # perdiera, nada debería quedar sin refrescar para siempre.
        hace_91_dias = timezone.now() - timedelta(days=91)

        self.assertTrue(_necesita_enriquecimiento(self._produccion(hace_91_dias)))

    def test_una_fila_dentro_de_la_ventana_no_lo_necesita(self):
        # Fija el borde: 89 días adentro, 91 afuera. Si alguien mueve la
        # constante sin querer, uno de los dos tests lo delata.
        hace_89_dias = timezone.now() - timedelta(days=89)

        self.assertFalse(_necesita_enriquecimiento(self._produccion(hace_89_dias)))


class VistasDeDetalleMaterializanTests(TestCase):
    """El detalle sigue siendo passthrough de TMDB y además materializa (C-04a).

    Se parchea `get_catalog_service` en los dos módulos que lo usan: la vista
    lo llama para armar la respuesta y el enriquecimiento lo llama de nuevo
    (en producción esa segunda llamada es un acierto de caché en Redis).
    """

    def setUp(self):
        # El throttle `catalogo` (60/min) guarda su contador en la caché
        # compartida: sin limpiarla, otros tests de la suite podrían dejarla
        # gastada y estos responderían 429.
        dj_cache.clear()
        self.servicio = _servicio_tmdb_falso()
        for modulo in ("catalogo.views", "catalogo.services.materialization"):
            parche = patch(f"{modulo}.get_catalog_service", return_value=self.servicio)
            parche.start()
            self.addCleanup(parche.stop)
        parche_tarea = patch("catalogo.services.materialization.generar_embedding")
        self.tarea = parche_tarea.start()
        self.addCleanup(parche_tarea.stop)
        self.api = APIClient()

    def test_detalle_de_pelicula_materializa_sin_tocar_la_respuesta(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api.get("/api/catalogo/movie/550/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, _DETALLE_MOVIE)

        produccion = ProduccionAudiovisual.objects.get(
            id_tmdb=550, tipo=TipoProduccion.PELICULA
        )
        self.assertEqual(produccion.titulo, "Fight Club")
        self.assertEqual(produccion.embedding.estado, EstadoEmbedding.PENDING)
        self.tarea.delay.assert_called_once_with(produccion.id)

    def test_detalle_de_serie_materializa_sin_tocar_la_respuesta(self):
        response = self.api.get("/api/catalogo/tv/1396/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, _DETALLE_TV)

        produccion = ProduccionAudiovisual.objects.get(
            id_tmdb=1396, tipo=TipoProduccion.SERIE
        )
        self.assertEqual(produccion.titulo, "Breaking Bad")
        self.assertEqual(produccion.embedding.estado, EstadoEmbedding.PENDING)

    def test_abrir_el_detalle_dos_veces_no_duplica_nada(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.api.get("/api/catalogo/movie/550/")
            self.api.get("/api/catalogo/movie/550/")

        self.assertEqual(ProduccionAudiovisual.objects.count(), 1)
        self.assertEqual(ProduccionEmbedding.objects.count(), 1)
        self.tarea.delay.assert_called_once()

    def test_un_fallo_al_materializar_no_rompe_la_respuesta(self):
        # Contrato de C-03: el detalle es passthrough puro de TMDB. Si nuestra
        # base o el enriquecimiento fallan, el usuario igual ve la ficha.
        with patch(
            "catalogo.views.materializar", side_effect=RuntimeError("base caída")
        ):
            response = self.api.get("/api/catalogo/movie/550/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, _DETALLE_MOVIE)
        self.assertEqual(ProduccionAudiovisual.objects.count(), 0)


class MaterializacionConcurrenciaTests(_ParchesDeMaterializacion, TransactionTestCase):
    """Dos hilos reales materializando la misma producción (C-04a).

    `MaterializacionCarreraTests` fuerza el `IntegrityError` con un mock; acá
    se provoca de verdad, con dos conexiones a Postgres compitiendo por la
    constraint `uq_produccion_tmdb_tipo`.

    Requiere `TransactionTestCase` y no `TestCase`: este último encierra el
    test entero en una transacción que nadie más ve, así que un segundo hilo
    ni siquiera encontraría la fila del primero. `TransactionTestCase` commitea
    de verdad y limpia truncando las tablas al final.

    Acordado el 14/09/2026: es una prueba de confianza extra y **no bloquea el
    merge**. Si resultara inestable por timing, se marca con `@skip` dejando
    escrito el motivo — el test determinístico de la carrera sigue cubriendo
    el criterio de aceptación.
    """

    def test_dos_hilos_simultaneos_dejan_una_sola_fila(self):
        barrera = threading.Barrier(2)
        ids_devueltos = []
        errores = []

        def materializar_en_paralelo():
            try:
                # Suelta a los dos hilos lo más cerca posible en el tiempo.
                barrera.wait(timeout=5)
                ids_devueltos.append(materializar(550, "movie").pk)
            except Exception as error:
                errores.append(error)
            finally:
                # Cada hilo abre su propia conexión a Postgres; si no la
                # cierra, queda ocupando la tabla y el truncado final del
                # TransactionTestCase se cuelga esperándola.
                connection.close()

        hilos = [threading.Thread(target=materializar_en_paralelo) for _ in range(2)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=10)

        self.assertEqual(errores, [])
        # Los dos hilos llegaron al final. Sin esto, un hilo colgado (el
        # `join` se rinde por timeout y el test sigue) dejaría una sola
        # entrada en la lista y la aserción de abajo daría verde igual.
        self.assertEqual(len(ids_devueltos), 2)
        # Los dos hilos terminan apuntando a la misma fila, exista una carrera
        # real o haya ganado uno por varios milisegundos.
        self.assertEqual(len(set(ids_devueltos)), 1)
        self.assertEqual(ProduccionAudiovisual.objects.count(), 1)
        self.assertEqual(ProduccionEmbedding.objects.count(), 1)


class IdsCambiadosTests(SimpleTestCase):
    """El paginador de la lista de cambios de TMDB (C-04b, fase 2).

    `_ids_cambiados` junta en un set los IDs de todas las páginas. Se prueba
    con un servicio falso cuyo `get_changes` fabrica la página pedida, así el
    test decide cuántas páginas "hay".
    """

    def _servicio(self, total_pages, ids_de):
        servicio = Mock()
        servicio.get_changes.side_effect = lambda tipo, page: _pagina_de_cambios(
            page, total_pages, ids_de(page)
        )
        return servicio

    def test_recorre_todas_las_paginas_y_junta_los_ids(self):
        # Tres páginas: {1, 2}, {3, 4}, {5}.
        servicio = self._servicio(
            3, lambda p: range(2 * p - 1, 2 * p + 1) if p < 3 else [5]
        )

        ids = _ids_cambiados(servicio, "movie")

        self.assertEqual(ids, {1, 2, 3, 4, 5})
        servicio.get_changes.assert_has_calls(
            [call("movie", 1), call("movie", 2), call("movie", 3)]
        )
        self.assertEqual(servicio.get_changes.call_count, 3)

    def test_se_detiene_en_el_tope_de_paginas(self):
        # TMDB dice que hay muchas más páginas que el tope: se piden solo las
        # del tope. Lo que quede afuera lo cubre la red de seguridad de 90 días.
        servicio = self._servicio(_MAX_PAGINAS_CAMBIOS + 50, lambda p: [p])

        ids = _ids_cambiados(servicio, "tv")

        self.assertEqual(servicio.get_changes.call_count, _MAX_PAGINAS_CAMBIOS)
        self.assertEqual(len(ids), _MAX_PAGINAS_CAMBIOS)

    def test_tolera_items_sin_id_y_respuestas_sin_results(self):
        servicio = Mock()
        servicio.get_changes.return_value = {
            "page": 1,
            "total_pages": 1,
            "results": [{"id": 550, "adult": False}, {"adult": False}, {}],
        }
        self.assertEqual(_ids_cambiados(servicio, "movie"), {550})

        servicio.get_changes.return_value = {"page": 1, "total_pages": 1}
        self.assertEqual(_ids_cambiados(servicio, "movie"), set())


class SyncCatalogoTests(TestCase):
    """La pasada de descubrimiento de la sync nocturna (C-04b, fase 2).

    `materializar` va mockeada entera: el enriquecimiento ya tiene su suite.
    Lo que se prueba acá es que la sync recorra las cuatro fuentes, resuelva el
    tipo de cada ítem según de dónde vino, no se caiga por un ítem malo, y
    cuente bien lo que hizo.
    """

    def setUp(self):
        self.servicio = _servicio_tmdb_falso()
        parche_servicio = patch(
            "catalogo.tasks.get_catalog_service", return_value=self.servicio
        )
        # La tarea importa `materializar` adentro de la función (evita el
        # import circular con materialization.py), así que se parchea donde
        # vive, no en catalogo.tasks.
        parche_materializar = patch("catalogo.services.materialization.materializar")
        parche_servicio.start()
        self.materializar = parche_materializar.start()
        self.addCleanup(parche_servicio.stop)
        self.addCleanup(parche_materializar.stop)

    def test_materializa_cada_item_soportado_con_el_tipo_de_su_fuente(self):
        sync_catalogo_diaria()

        # trending trae el tipo en cada ítem; en las otras tres fuentes el tipo
        # lo dicta el endpoint. `person` no está: no es una producción.
        self.materializar.assert_has_calls(
            [
                call(550, "movie"),  # trending, media_type=movie
                call(1396, "tv"),  # trending, media_type=tv
                call(27205, "movie"),  # now_playing → siempre película
                call(155, "movie"),  # discover("movie")
                call(1399, "tv"),  # discover("tv")
            ],
            any_order=True,
        )
        self.assertEqual(self.materializar.call_count, 5)

    def test_person_se_saltea_sin_lanzar_y_cuenta_como_omitida(self):
        estadisticas = sync_catalogo_diaria()

        ids_materializados = [c.args[0] for c in self.materializar.call_args_list]
        self.assertNotIn(287, ids_materializados)
        self.assertEqual(estadisticas["omitidas"], 1)

    def test_un_item_que_falla_no_aborta_la_corrida(self):
        # Un título que TMDB no devuelve no puede tirar abajo la noche entera.
        # Misma política que las vistas de detalle, y por la misma razón.
        def explota_en_fight_club(id_tmdb, tipo_tmdb):
            if id_tmdb == 550:
                raise RuntimeError("TMDB returned HTTP 404")
            return Mock()

        self.materializar.side_effect = explota_en_fight_club

        estadisticas = sync_catalogo_diaria()

        # Los otros cuatro se procesaron igual, y el fallo quedó contado.
        # sync_catalogo_diaria atrapa excepciones por ítem y continúa, así que
        # call_count refleja todos los intentos (incluido el que falló).
        self.assertEqual(self.materializar.call_count, 5)
        self.assertEqual(estadisticas["errores"], 1)

    def test_las_estadisticas_distinguen_nuevas_de_ya_existentes(self):
        # Fight Club ya estaba en la base; los otros cuatro son nuevos.
        ProduccionAudiovisual.objects.create(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Fight Club"
        )

        estadisticas = sync_catalogo_diaria()

        self.assertEqual(
            estadisticas,
            {
                "nuevas": 4,
                "ya_existentes": 1,
                "refrescadas": 0,
                "omitidas": 1,
                "errores": 0,
            },
        )

    def _cambios(self, movie=(), tv=()):
        """Hace que TMDB reporte estos IDs como modificados hoy."""
        self.servicio.get_changes.side_effect = lambda tipo, page: _pagina_de_cambios(
            1, 1, movie if tipo == "movie" else tv
        )

    def test_refresca_con_forzar_solo_lo_que_tenemos_y_tmdb_dice_que_cambio(self):
        for id_tmdb, tipo in (
            (550, TipoProduccion.PELICULA),
            (27205, TipoProduccion.PELICULA),
            (1396, TipoProduccion.SERIE),
        ):
            ProduccionAudiovisual.objects.create(id_tmdb=id_tmdb, tipo=tipo, titulo="x")
        # 550 lo tenemos y cambió → se refresca. 27205 lo tenemos pero no
        # cambió → no. 999999 cambió pero no lo tenemos → ni se mira: si no,
        # la sync estaría rastreando los ~10.000 cambios diarios de TMDB.
        self._cambios(movie=[550, 999999])

        estadisticas = sync_catalogo_diaria()

        llamadas = self.materializar.call_args_list
        self.assertIn(call(550, "movie", forzar=True), llamadas)
        self.assertNotIn(call(27205, "movie", forzar=True), llamadas)
        self.assertNotIn(999999, [c.args[0] for c in llamadas])
        self.assertEqual(estadisticas["refrescadas"], 1)

    def test_si_la_lista_de_cambios_falla_el_descubrimiento_sigue(self):
        self.servicio.get_changes.side_effect = RuntimeError("TMDB returned HTTP 500")

        estadisticas = sync_catalogo_diaria()

        # Las cuatro fuentes se recorrieron igual; el fallo quedó contado una
        # vez por tipo (movie y tv se piden por separado).
        self.assertEqual(self.materializar.call_count, 5)
        self.assertEqual(estadisticas["errores"], 2)
        self.assertEqual(estadisticas["refrescadas"], 0)

    def test_el_refresco_va_primero_y_el_descubrimiento_no_duplica(self):
        # El refresco va primero a propósito: si un ítem está en /changes Y en
        # trending, se refresca primero (forzar=True) y luego se salta en
        # descubrimiento porque ya existe. Sin esto, se enriquecería dos veces.
        ProduccionAudiovisual.objects.create(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Fight Club"
        )
        # 550 está en /changes (se refresca) Y en trending (se materializaría)
        self._cambios(movie=[550])

        estadisticas = sync_catalogo_diaria()

        # Se refresca primero (forzar=True)
        self.assertIn(call(550, "movie", forzar=True), self.materializar.call_args_list)
        # No se cuenta como "nueva" porque ya existía antes de la corrida
        self.assertEqual(estadisticas["refrescadas"], 1)
        self.assertEqual(estadisticas["nuevas"], 4)  # los otros 4 de trending

    def test_un_item_en_changes_y_en_trending_se_materializa_dos_veces(self):
        # Si un ítem está en /changes Y en trending, se materializa dos veces:
        # una en refresco (forzar=True) y otra en descubrimiento (sin forzar).
        # Esto es ineficiente pero es el comportamiento actual.
        # 550 ya existe, está en /changes, también aparece en trending
        ProduccionAudiovisual.objects.create(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Fight Club"
        )
        self._cambios(movie=[550])

        estadisticas = sync_catalogo_diaria()

        # 550 se refresca (forzar=True)
        self.assertIn(call(550, "movie", forzar=True), self.materializar.call_args_list)
        # 550 también se materializa en descubrimiento (sin forzar)
        self.assertIn(call(550, "movie"), self.materializar.call_args_list)
        # Se cuenta en ya_existentes por el descubrimiento (porque ya existía)
        self.assertEqual(estadisticas["refrescadas"], 1)
        self.assertEqual(estadisticas["ya_existentes"], 1)
        self.assertEqual(estadisticas["nuevas"], 4)  # los otros 4 de trending

    def test_multiples_items_en_changes_algunos_fallan(self):
        # Si /changes devuelve 5 IDs y 3 fallan en materializar, el conteo
        # debe ser correcto: 2 refrescadas, 3 errores.
        for id_tmdb in (550, 27205, 155, 1396, 1399):
            ProduccionAudiovisual.objects.create(
                id_tmdb=id_tmdb, tipo=TipoProduccion.PELICULA, titulo="x"
            )
        self._cambios(movie=[550, 27205, 155, 1396, 1399])

        # Hacer que 3 de ellos fallen SOLO en el refresco (forzar=True)
        # En descubrimiento (sin forzar) deben funcionar normalmente
        def falla_tres_en_refresco(id_tmdb, tipo_tmdb, forzar=False):
            if forzar and id_tmdb in (27205, 155, 1396):
                raise RuntimeError("TMDB timeout")
            return Mock()

        self.materializar.side_effect = falla_tres_en_refresco

        estadisticas = sync_catalogo_diaria()

        # 2 se refrescaron (550 y 1399), 3 fallaron en el refresco
        self.assertEqual(estadisticas["refrescadas"], 2)
        self.assertEqual(estadisticas["errores"], 3)

    def test_movie_changes_funciona_tv_changes_falla(self):
        # Si /movie/changes funciona pero /tv/changes falla, el refresco de
        # movie se hace igual. El fallo de tv se cuenta como 1 error.
        ProduccionAudiovisual.objects.create(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Fight Club"
        )
        ProduccionAudiovisual.objects.create(
            id_tmdb=1396, tipo=TipoProduccion.SERIE, titulo="Breaking Bad"
        )

        # /movie/changes devuelve 550, /tv/changes falla
        def changes_por_tipo(tipo, page):
            if tipo == "movie":
                return _pagina_de_cambios(1, 1, [550])
            else:  # tv
                raise RuntimeError("TMDB returned HTTP 500")

        self.servicio.get_changes.side_effect = changes_por_tipo

        estadisticas = sync_catalogo_diaria()

        # 550 se refrescó (movie funcionó)
        self.assertIn(call(550, "movie", forzar=True), self.materializar.call_args_list)
        self.assertEqual(estadisticas["refrescadas"], 1)
        # 1 error (el fallo de /tv/changes)
        self.assertEqual(estadisticas["errores"], 1)

    def test_base_vacia_changes_no_hace_nada(self):
        # Si la base está vacía y /changes devuelve 1000 IDs, el refresco
        # no debe intentar materializarlos (no hay nada que refrescar).
        self._cambios(movie=[550, 27205, 155, 1396, 1399])

        estadisticas = sync_catalogo_diaria()

        # No se refrescó nada (base vacía)
        self.assertEqual(estadisticas["refrescadas"], 0)
        # materializar NO se llamó con forzar=True (no hay nada que refrescar)
        llamadas_con_forzar = [
            c
            for c in self.materializar.call_args_list
            if c.kwargs.get("forzar") or (len(c.args) > 2 and c.args[2])
        ]
        self.assertEqual(len(llamadas_con_forzar), 0)
        # Pero el descubrimiento sí se hizo (5 ítems nuevos de trending)
        self.assertEqual(estadisticas["nuevas"], 5)


class SyncCatalogoIntegracionTests(_ParchesDeMaterializacion, TestCase):
    """La sync con `materializar` REAL y TMDB falso: lo que queda en la base.

    El mixin ya parchea el servicio en materialization.py; acá se parchea
    además en catalogo.tasks, que lo usa para los listados.
    """

    def setUp(self):
        super().setUp()
        parche = patch("catalogo.tasks.get_catalog_service", return_value=self.servicio)
        parche.start()
        self.addCleanup(parche.stop)

    def test_dos_corridas_seguidas_dejan_las_mismas_filas(self):
        # Idempotencia de punta a punta: la segunda noche no duplica nada y
        # reporta cero nuevas, porque `materializar` ya las encuentra.
        with self.captureOnCommitCallbacks(execute=True):
            primera = sync_catalogo_diaria()
            segunda = sync_catalogo_diaria()

        self.assertEqual(primera["nuevas"], 5)
        self.assertEqual(segunda["nuevas"], 0)
        self.assertEqual(segunda["ya_existentes"], 5)
        self.assertEqual(ProduccionAudiovisual.objects.count(), 5)
        self.assertEqual(ProduccionEmbedding.objects.count(), 5)
        # Todas pasaron por el detalle, no quedaron con la forma del listado.
        self.assertFalse(
            ProduccionAudiovisual.objects.filter(fecha_enriquecimiento=None).exists()
        )

    def test_una_fila_fresca_se_cuenta_pero_no_se_le_pide_el_detalle(self):
        # Fija el significado de `ya_existentes`: mide presencia, no escritura.
        # El nombre viejo (`actualizadas`) sugería lo contrario.
        with self.captureOnCommitCallbacks(execute=True):
            sync_catalogo_diaria()
        self.servicio.get_movie_detail.reset_mock()
        self.servicio.get_tv_detail.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            estadisticas = sync_catalogo_diaria()

        self.assertEqual(estadisticas["ya_existentes"], 5)
        self.assertEqual(estadisticas["refrescadas"], 0)
        self.servicio.get_movie_detail.assert_not_called()
        self.servicio.get_tv_detail.assert_not_called()

    def test_el_refresco_reenriquece_solo_lo_que_tmdb_dice_que_cambio(self):
        # Dos películas completas y frescas: el criterio de fecha las saltearía.
        ayer = timezone.now() - timedelta(days=1)
        cambiada = ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="viejo",
            fecha_enriquecimiento=ayer,
        )
        intacta = ProduccionAudiovisual.objects.create(
            id_tmdb=27205,
            tipo=TipoProduccion.PELICULA,
            titulo="Inception",
            fecha_enriquecimiento=ayer,
        )
        self.servicio.get_changes.side_effect = lambda tipo, page: _pagina_de_cambios(
            1, 1, [550] if tipo == "movie" else []
        )

        with self.captureOnCommitCallbacks(execute=True):
            estadisticas = sync_catalogo_diaria()

        ids_pedidos = [c.args[0] for c in self.servicio.get_movie_detail.call_args_list]
        self.assertIn(550, ids_pedidos)
        self.assertNotIn(27205, ids_pedidos)
        cambiada.refresh_from_db()
        intacta.refresh_from_db()
        self.assertEqual(cambiada.titulo, "Fight Club")  # vino del detalle
        self.assertGreater(cambiada.fecha_enriquecimiento, ayer)
        self.assertEqual(intacta.fecha_enriquecimiento, ayer)
        self.assertEqual(estadisticas["refrescadas"], 1)

    def test_calificacion_y_resena_sobreviven_al_refresco(self):
        # Criterio de aceptación de C-04b, probado directo. `Calificacion`
        # cuelga de la producción con on_delete=CASCADE: si el refresco fuera
        # "borrar e insertar" en vez de un UPDATE, se llevaría en silencio
        # todo lo que el usuario escribió sobre ese título.
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=550,
            tipo=TipoProduccion.PELICULA,
            titulo="viejo",
            fecha_enriquecimiento=timezone.now() - timedelta(days=1),
        )
        calificacion = CalificacionFactory(produccion=produccion, valor=9)
        resena = ResenaFactory(calificacion=calificacion, texto="La primera regla...")
        self.servicio.get_changes.side_effect = lambda tipo, page: _pagina_de_cambios(
            1, 1, [550] if tipo == "movie" else []
        )

        with self.captureOnCommitCallbacks(execute=True):
            sync_catalogo_diaria()

        produccion.refresh_from_db()
        self.assertEqual(produccion.titulo, "Fight Club")  # sí se refrescó
        calificacion_despues = Calificacion.objects.get(pk=calificacion.pk)
        self.assertEqual(calificacion_despues.valor, 9)
        self.assertEqual(calificacion_despues.produccion_id, produccion.pk)
        self.assertEqual(Resena.objects.get(pk=resena.pk).texto, "La primera regla...")


# ---------------------------------------------------------------------------
# Seed inicial del catálogo (C-04c, fase 2)
# ---------------------------------------------------------------------------
# Forma real de `/genre/{tipo}/list` (verificada el 18/09/2026):
# `{"genres": [{"id": 28, "name": "Action"}, ...]}`. Dos géneros de película y
# uno de serie alcanzan para cubrir el producto género x década x tipo sin que
# las combinaciones se vuelvan ilegibles.
_GENEROS_MOVIE = {"genres": [{"id": 28, "name": "Action"}, {"id": 18, "name": "Drama"}]}
_GENEROS_TV = {"genres": [{"id": 18, "name": "Drama"}]}

# TMDB pagina `discover` de a 20 ítems.
_POR_PAGINA = 20

_LOGGER_SEED = "catalogo.management.commands.seed_catalogo"


def _discover_paginado(catalogo, total_pages=None):
    """Un `discover` falso que pagina como TMDB.

    `catalogo` mapea `(tipo_tmdb, id_genero) -> [ids]`. El fake calcula
    `total_pages` del largo real, salvo que un test lo fuerce para simular el
    `total_pages` mentiroso de TMDB (reporta 1001 y rechaza la página 501).
    Los filtros de década y orden se aceptan y se ignoran: lo que se prueba
    acá es el recorrido, no el filtrado (eso ya lo cubre `TMDBDiscoverRangoTest`).
    """

    def discover(tipo, genero=None, page=1, **_):
        ids = catalogo.get((tipo, genero), [])
        inicio = (page - 1) * _POR_PAGINA
        return {
            "page": page,
            "results": [
                {"id": id_tmdb} for id_tmdb in ids[inicio : inicio + _POR_PAGINA]
            ],
            "total_pages": total_pages or max(1, -(-len(ids) // _POR_PAGINA)),
        }

    return discover


def _servicio_seed_falso(catalogo, total_pages=None):
    """Doble del servicio para el seed: géneros fijos y `discover` paginado."""
    servicio = _servicio_tmdb_falso()
    servicio.get_genres = Mock(
        side_effect=lambda tipo: _GENEROS_MOVIE if tipo == "movie" else _GENEROS_TV
    )
    servicio.discover = Mock(side_effect=_discover_paginado(catalogo, total_pages))
    return servicio


class ClavesFrescasTests(TestCase):
    """`claves_frescas()`: lo que `materializar()` NO volvería a enriquecer.

    El seed la consulta una vez al arrancar para saltear filas sin llamar a
    `materializar()` por cada una. Tiene que usar la MISMA definición de
    "fresca" que `_necesita_enriquecimiento`, o el seed saltearía filas que la
    materialización sí refrescaría (o al revés).
    """

    def test_devuelve_solo_las_enriquecidas_dentro_de_la_ventana(self):
        ahora = timezone.now()
        ProduccionAudiovisual.objects.create(
            id_tmdb=1,
            tipo=TipoProduccion.PELICULA,
            titulo="fresca",
            fecha_enriquecimiento=ahora - timedelta(days=1),
        )
        ProduccionAudiovisual.objects.create(
            id_tmdb=2,
            tipo=TipoProduccion.SERIE,
            titulo="nunca enriquecida",
            fecha_enriquecimiento=None,
        )
        ProduccionAudiovisual.objects.create(
            id_tmdb=3,
            tipo=TipoProduccion.PELICULA,
            titulo="vencida",
            fecha_enriquecimiento=ahora - timedelta(days=91),
        )

        self.assertEqual(claves_frescas(), {(1, TipoProduccion.PELICULA)})


_GENEROS_POR_TIPO = {"movie": _GENEROS_MOVIE["genres"], "tv": _GENEROS_TV["genres"]}


class SeedCombinacionesTests(SimpleTestCase):
    """Cómo se arma el espacio de muestreo: género x década x tipo."""

    def test_cruza_genero_decada_y_tipo(self):
        combinaciones = _combinaciones(
            _GENEROS_POR_TIPO, desde_anio=2000, hasta_anio=2026
        )

        # 3 géneros (2 movie + 1 tv) x 3 décadas (2000, 2010, 2020) = 9. La
        # década en curso entra entera (hasta 2029): el filtro es por rango de
        # fechas y a TMDB no le molesta que el tope esté en el futuro.
        self.assertEqual(len(combinaciones), 9)
        self.assertEqual(
            {(c.tipo, c.genero, c.anio_desde, c.anio_hasta) for c in combinaciones},
            {
                (tipo, genero, decada, decada + 9)
                for tipo, genero in (("movie", 28), ("movie", 18), ("tv", 18))
                for decada in (2000, 2010, 2020)
            },
        )
        # El nombre viaja para el progreso en pantalla.
        self.assertEqual({c.nombre_genero for c in combinaciones}, {"Action", "Drama"})

    def test_desde_anio_se_redondea_a_la_decada(self):
        combinaciones = _combinaciones(
            {"tv": _GENEROS_TV["genres"]}, desde_anio=1985, hasta_anio=1999
        )

        self.assertEqual(
            [(c.anio_desde, c.anio_hasta) for c in sorted(combinaciones)],
            [(1980, 1989), (1990, 1999)],
        )

    def test_el_orden_es_barajado_y_determinista(self):
        # Barajado: cortar a mitad de ronda en orden de declaración sesgaría
        # hacia el primer género de la lista. Determinista: dos corridas
        # recorren el mismo camino, así que retomar no cambia el muestreo.
        primera = _combinaciones(_GENEROS_POR_TIPO, desde_anio=2000, hasta_anio=2026)
        segunda = _combinaciones(_GENEROS_POR_TIPO, desde_anio=2000, hasta_anio=2026)

        self.assertEqual(primera, segunda)
        self.assertNotEqual(primera, sorted(primera))


class SeedRecorridoTests(SimpleTestCase):
    """El recorrido round-robin de `discover` y la pared de las 500 páginas."""

    def _combinacion(self, genero, nombre="Action"):
        return Combinacion("movie", genero, nombre, 2020, 2029)

    def test_pide_pagina_1_de_todas_antes_que_la_2_de_ninguna(self):
        # Round-robin: una corrida interrumpida a mitad de camino tiene un poco
        # de todo, no todo de Action y nada de Drama.
        servicio = _servicio_seed_falso(
            {("movie", 28): list(range(1, 26)), ("movie", 18): [100, 101]}
        )
        combinaciones = [self._combinacion(28), self._combinacion(18, "Drama")]

        recorrido = [
            (c.genero, pagina) for c, pagina, _ in _recorrer(servicio, combinaciones)
        ]

        # Action tiene 2 páginas, Drama 1: la 2 de Action va DESPUÉS de la 1 de
        # Drama, y Drama no se vuelve a pedir.
        self.assertEqual(recorrido, [(28, 1), (18, 1), (28, 2)])

    def test_pasa_a_discover_el_rango_de_la_decada_y_el_orden_por_votos(self):
        servicio = _servicio_seed_falso({("movie", 28): [1]})

        list(_recorrer(servicio, [self._combinacion(28)]))

        # El rango viaja como `anio_desde`/`anio_hasta`: es el CLIENTE quien
        # lo traduce al parámetro de fecha de cada tipo (fase 1). El orden por
        # votos trae los clásicos, no lo que trendea esta semana.
        servicio.discover.assert_called_once_with(
            "movie",
            genero=28,
            page=1,
            anio_desde=2020,
            anio_hasta=2029,
            sort_by="vote_count.desc",
        )

    def test_se_corta_en_500_paginas_aunque_tmdb_reporte_mas(self):
        # Verificado en vivo el 18/09/2026: `total_pages` dice 1001 y la
        # página 501 devuelve HTTP 400. Sin este tope, una corrida de cuatro
        # horas moriría cerca del final por un `TMDBBadRequest`.
        servicio = _servicio_seed_falso(
            {("movie", 28): list(range(1, 20_001))}, total_pages=1001
        )

        paginas = [
            pagina for _, pagina, _ in _recorrer(servicio, [self._combinacion(28)])
        ]

        self.assertEqual(_MAX_PAGINAS, 500)
        self.assertEqual(paginas, list(range(1, 501)))

    def test_una_pagina_que_falla_avisa_y_saca_la_combinacion_de_la_ronda(self):
        servicio = _servicio_seed_falso({("movie", 18): [100]})

        def explota_en_action(tipo, genero=None, page=1, **kwargs):
            if genero == 28:
                raise RuntimeError("TMDB returned HTTP 500")
            return _discover_paginado({("movie", 18): [100]})(tipo, genero, page)

        servicio.discover.side_effect = explota_en_action

        with self.assertLogs(_LOGGER_SEED, level="ERROR"):
            recorrido = list(
                _recorrer(
                    servicio, [self._combinacion(28), self._combinacion(18, "Drama")]
                )
            )

        # La página fallida se reporta con `None` (el comando la cuenta como
        # error) y la de Drama se lee igual: un 500 en una combinación no
        # tira la corrida.
        self.assertEqual(
            [(c.genero, items) for c, _, items in recorrido],
            [(28, None), (18, [{"id": 100}])],
        )


class SeedCatalogoTests(TestCase):
    """El comando `seed_catalogo` con `materializar` mockeada.

    El enriquecimiento ya tiene su suite; lo que se prueba acá es que el
    comando recorra las combinaciones, saltee lo que no hace falta pedir,
    respete el tope, sobreviva a un ítem malo y cuente bien lo que hizo.

    Todos los tests arrancan en la década de 2020 (`--desde-anio 2020`) para
    que cada género tenga UNA combinación y el recorrido sea legible: con los
    géneros del fake son tres — Action/movie, Drama/movie y Drama/tv.
    """

    def setUp(self):
        self.catalogo = {
            ("movie", 28): [1, 2, 3],
            ("movie", 18): [4, 5],
            ("tv", 18): [6],
        }
        self.servicio = _servicio_seed_falso(self.catalogo)
        parche_servicio = patch(
            "catalogo.management.commands.seed_catalogo.get_catalog_service",
            return_value=self.servicio,
        )
        parche_materializar = patch(
            "catalogo.management.commands.seed_catalogo.materializar"
        )
        parche_servicio.start()
        self.materializar = parche_materializar.start()
        self.addCleanup(parche_servicio.stop)
        self.addCleanup(parche_materializar.stop)

    def _correr(self, *argumentos):
        """Corre el comando como desde la terminal y devuelve (estadísticas, salida).

        `call_command` acepta una instancia: así el test puede leer las
        estadísticas del objeto después, sin parsear la salida.
        """
        comando = SeedCatalogo()
        salida = StringIO()
        call_command(comando, "--desde-anio", "2020", *argumentos, stdout=salida)
        return comando.estadisticas, salida.getvalue()

    def _ids_materializados(self):
        return [c.args[0] for c in self.materializar.call_args_list]

    def test_materializa_cada_item_con_el_tipo_de_su_combinacion(self):
        estadisticas, _ = self._correr()

        self.materializar.assert_has_calls(
            [
                call(1, "movie"),
                call(2, "movie"),
                call(3, "movie"),
                call(4, "movie"),
                call(5, "movie"),
                call(6, "tv"),
            ],
            any_order=True,
        )
        self.assertEqual(
            estadisticas,
            {"materializadas": 6, "ya_estaban": 0, "omitidas": 0, "errores": 0},
        )

    def test_limite_corta_la_corrida_a_mitad_de_ronda(self):
        estadisticas, _ = self._correr("--limite", "4")

        self.assertEqual(self.materializar.call_count, 4)
        self.assertEqual(estadisticas["materializadas"], 4)

    def test_las_frescas_se_saltean_sin_llamar_a_materializar(self):
        # Retomar una corrida interrumpida tiene que ser gratis: lo que ya
        # está fresco ni siquiera llega a `materializar()`. Lo que está pero
        # nunca se enriqueció (la corrida anterior murió a mitad de la ficha)
        # SÍ se manda, para que quede completo.
        ProduccionAudiovisual.objects.create(
            id_tmdb=1,
            tipo=TipoProduccion.PELICULA,
            titulo="fresca",
            fecha_enriquecimiento=timezone.now(),
        )
        ProduccionAudiovisual.objects.create(
            id_tmdb=2,
            tipo=TipoProduccion.PELICULA,
            titulo="",
            fecha_enriquecimiento=None,
        )

        estadisticas, _ = self._correr()

        self.assertNotIn(1, self._ids_materializados())
        self.assertIn(2, self._ids_materializados())
        self.assertEqual(estadisticas["ya_estaban"], 1)
        self.assertEqual(estadisticas["materializadas"], 5)

    def test_las_frescas_no_consumen_el_limite(self):
        # `--limite` cuenta lo que ESTA corrida materializa: al retomar con el
        # mismo valor, lo que ya estaba no descuenta cupo. Una fresca entre
        # seis y tope 5: si la fresca descontara, saldrían 4 materializadas.
        ProduccionAudiovisual.objects.create(
            id_tmdb=1,
            tipo=TipoProduccion.PELICULA,
            titulo="fresca",
            fecha_enriquecimiento=timezone.now(),
        )

        estadisticas, _ = self._correr("--limite", "5")

        self.assertEqual(estadisticas["materializadas"], 5)
        self.assertEqual(estadisticas["ya_estaban"], 1)

    def test_un_item_que_falla_se_cuenta_y_la_corrida_sigue(self):
        def explota_en_el_2(id_tmdb, tipo_tmdb):
            if id_tmdb == 2:
                raise RuntimeError("TMDB returned HTTP 404")
            return Mock()

        self.materializar.side_effect = explota_en_el_2

        with self.assertLogs(_LOGGER_SEED, level="ERROR"):
            estadisticas, _ = self._correr()

        self.assertEqual(self.materializar.call_count, 6)
        self.assertEqual(estadisticas["errores"], 1)
        self.assertEqual(estadisticas["materializadas"], 5)

    def test_una_pagina_de_discover_que_falla_se_cuenta_como_error(self):
        discover_sano = self.servicio.discover.side_effect

        def explota_en_action(tipo, genero=None, page=1, **kwargs):
            if genero == 28:
                raise RuntimeError("TMDB returned HTTP 500")
            return discover_sano(tipo, genero=genero, page=page, **kwargs)

        self.servicio.discover.side_effect = explota_en_action

        with self.assertLogs(_LOGGER_SEED, level="ERROR"):
            estadisticas, _ = self._correr()

        self.assertEqual(sorted(self._ids_materializados()), [4, 5, 6])
        self.assertEqual(estadisticas["errores"], 1)

    def test_un_titulo_en_dos_generos_se_materializa_una_vez(self):
        # Una película es Action Y Drama a la vez: aparece en las dos
        # combinaciones. La segunda vez se saltea y se cuenta como omitida.
        self.catalogo[("movie", 18)] = [4, 1]

        estadisticas, _ = self._correr()

        self.assertEqual(self._ids_materializados().count(1), 1)
        self.assertEqual(estadisticas["omitidas"], 1)
        self.assertEqual(estadisticas["materializadas"], 5)

    def test_el_mismo_id_en_movie_y_tv_son_dos_producciones(self):
        # El id de TMDB solo es único DENTRO de un tipo: la película 18 y la
        # serie 18 no tienen nada que ver. La clave es (id, tipo).
        self.catalogo[("tv", 18)] = [1]

        estadisticas, _ = self._correr()

        self.assertIn(call(1, "movie"), self.materializar.call_args_list)
        self.assertIn(call(1, "tv"), self.materializar.call_args_list)
        self.assertEqual(estadisticas["omitidas"], 0)

    def test_tipos_restringe_el_muestreo(self):
        self._correr("--tipos", "movie")

        self.servicio.get_genres.assert_called_once_with("movie")
        tipos_pedidos = {c.args[0] for c in self.servicio.discover.call_args_list}
        self.assertEqual(tipos_pedidos, {"movie"})

    def test_dry_run_recorre_pero_no_escribe(self):
        estadisticas, salida = self._correr("--dry-run")

        self.assertGreater(self.servicio.discover.call_count, 0)
        self.materializar.assert_not_called()
        # Reporta lo que HABRÍA materializado, y avisa que no escribió.
        self.assertEqual(estadisticas["materializadas"], 6)
        self.assertIn("dry-run", salida)

    def test_pausa_espera_entre_materializaciones(self):
        with patch("catalogo.management.commands.seed_catalogo.time.sleep") as sleep:
            self._correr("--pausa", "0.5")

        self.assertEqual(sleep.call_args_list, [call(0.5)] * 6)

    def test_ctrl_c_imprime_el_resumen_y_no_explota(self):
        # Lo materializado hasta el corte queda guardado (cada `materializar`
        # es su propia transacción), así que el comando cierra prolijo con el
        # resumen en vez de un traceback.
        def interrumpe_en_la_tercera(id_tmdb, tipo_tmdb):
            if self.materializar.call_count == 3:
                raise KeyboardInterrupt
            return Mock()

        self.materializar.side_effect = interrumpe_en_la_tercera

        estadisticas, salida = self._correr()

        self.assertEqual(estadisticas["materializadas"], 2)
        self.assertIn("Interrumpido", salida)
        self.assertIn("materializadas=2", salida)

    def test_el_progreso_dice_donde_esta_y_el_resumen_cuenta_todo(self):
        _, salida = self._correr("--limite", "100")

        # Una línea por página leída: contador, objetivo y qué combinación es.
        self.assertIn("Action · película · 2020-2029 · página 1", salida)
        self.assertIn("Drama · serie · 2020-2029 · página 1", salida)
        self.assertIn("/100]", salida)
        self.assertIn("materializadas=6 ya_estaban=0 omitidas=0 errores=0", salida)


class SeedCatalogoIntegracionTests(_ParchesDeMaterializacion, TestCase):
    """El seed con `materializar` REAL y TMDB falso: lo que queda en la base.

    El mixin parchea el servicio en materialization.py (detalle, créditos y
    keywords); acá se le agregan géneros y `discover`, y se parchea el mismo
    objeto en el comando.
    """

    def setUp(self):
        super().setUp()
        self.servicio.get_genres = Mock(
            side_effect=lambda tipo: _GENEROS_MOVIE if tipo == "movie" else _GENEROS_TV
        )
        self.servicio.discover = Mock(
            side_effect=_discover_paginado(
                {("movie", 28): [550, 155], ("movie", 18): [550], ("tv", 18): [1396]}
            )
        )
        parche = patch(
            "catalogo.management.commands.seed_catalogo.get_catalog_service",
            return_value=self.servicio,
        )
        parche.start()
        self.addCleanup(parche.stop)

    def _correr(self):
        comando = SeedCatalogo()
        with self.captureOnCommitCallbacks(execute=True):
            call_command(comando, "--desde-anio", "2020", stdout=StringIO())
        return comando.estadisticas

    def test_las_filas_quedan_enriquecidas_y_la_segunda_corrida_no_agrega_nada(self):
        primera = self._correr()
        self.servicio.get_movie_detail.reset_mock()
        self.servicio.get_tv_detail.reset_mock()
        segunda = self._correr()

        # 550 está en Action y en Drama: una sola fila. Tres en total.
        self.assertEqual(primera["materializadas"], 3)
        self.assertEqual(primera["omitidas"], 1)
        self.assertEqual(ProduccionAudiovisual.objects.count(), 3)
        self.assertEqual(ProduccionEmbedding.objects.count(), 3)
        # Todas pasaron por la ficha completa, no quedaron con la forma del listado.
        self.assertFalse(
            ProduccionAudiovisual.objects.filter(fecha_enriquecimiento=None).exists()
        )
        serie = ProduccionAudiovisual.objects.get(
            id_tmdb=1396, tipo=TipoProduccion.SERIE
        )
        self.assertEqual(serie.titulo, "Breaking Bad")
        self.assertEqual(serie.directores, ["Vince Gilligan"])
        # La segunda corrida: nada nuevo, nada duplicado, y ni una ficha pedida.
        self.assertEqual(segunda["materializadas"], 0)
        self.assertEqual(segunda["ya_estaban"], 3)
        self.assertEqual(ProduccionAudiovisual.objects.count(), 3)
        self.servicio.get_movie_detail.assert_not_called()
        self.servicio.get_tv_detail.assert_not_called()
