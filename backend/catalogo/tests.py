from unittest.mock import patch

import httpx
from django.test import SimpleTestCase, override_settings

from catalogo.client import TMDBClient
from catalogo.exceptions import (
    TMDBBadRequest,
    TMDBNotFound,
    TMDBRateLimited,
    TMDBServerError,
    TMDBTransportError,
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
