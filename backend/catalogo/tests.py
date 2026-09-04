from unittest.mock import patch

import fakeredis
import httpx
import redis
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from rest_framework.response import Response

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
from catalogo.service import get_catalog_service


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
                response = tmdb_exception_handler(exception, {})

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

    @patch("catalogo.service.get_redis")
    @patch("catalogo.service.TMDBClient")
    def test_returns_singleton_tmdb_client_cache(self, client, get_redis):
        redis_client = object()
        tmdb_client = object()
        get_redis.return_value = redis_client
        client.return_value = tmdb_client

        first = get_catalog_service()
        second = get_catalog_service()

        self.assertIsInstance(first, TMDBClientCache)
        self.assertIs(first, second)
        client.assert_called_once_with()
        get_redis.assert_called_once_with()


class CatalogoSettingsTest(SimpleTestCase):
    def test_tmdb_handler_and_throttle_are_configured(self):
        self.assertEqual(
            settings.REST_FRAMEWORK["EXCEPTION_HANDLER"],
            "catalogo.exceptions.tmdb_exception_handler",
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
        params = {"media_type": "all", "time_window": "week", "page": 1}
        self.redis.set(_build_key("trending", params), '{"cached": true}')

        result = cache.get_trending()

        self.assertEqual(result, {"cached": True})
        self.assertEqual(calls, [])

    def test_cache_miss_calls_and_stores(self):
        body = {"page": 1, "results": [{"id": 550}]}
        cache, calls = self.make_cache(body)

        result = cache.get_trending()

        key = _build_key(
            "trending", {"media_type": "all", "time_window": "week", "page": 1}
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
                    },
                    "search": {"query": "Fight Club", "tipo": "movie", "page": 1},
                    "movie_detail": {"id_tmdb": 550},
                    "tv_detail": {"id_tmdb": 1399},
                    "keywords": {"id_tmdb": 550, "tipo": "movie"},
                }[endpoint]
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

    def test_get_redis_passes_bounded_timeouts(self):
        with patch("catalogo.cache.redis.Redis.from_url") as from_url:
            get_redis()
            from_url.assert_called_once_with(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
                socket_timeout=REDIS_SOCKET_TIMEOUT,
            )
