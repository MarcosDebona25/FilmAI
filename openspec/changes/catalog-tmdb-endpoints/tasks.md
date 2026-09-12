# Tasks: Catalog TMDB REST Endpoints (C-03)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~400-520 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Exception handler + service singleton + settings wiring | PR 1 | `docker compose exec -T backend python manage.py test catalogo.tests.TMDBExceptionHandlerTest catalogo.tests.GetCatalogServiceTest` | N/A — pure unit tests, no runtime path | revert exceptions.py/service.py/settings.py edits |
| 2 | Base view + coercion helpers + 7 views + routing include | PR 2 | `docker compose exec -T backend python manage.py test catalogo.tests.ParamValidationTest` | `docker compose exec backend python manage.py shell` → `reverse("catalogo:trending")` | revert views.py, urls.py, filmai/urls.py include |
| 3 | Endpoint integration + error→HTTP + throttle + GET-only | PR 3 | `docker compose exec -T backend python manage.py test catalogo` | `docker compose up -d backend` then `curl localhost:8000/api/catalogo/trending/` | revert tests.py only (behavior already merged) |

## Phase 1: Foundation

- [x] 1.1 RED: add `TMDBExceptionHandlerTest` asserting `tmdb_exception_handler` maps TMDBNotFound→404, TMDBBadRequest→400, TMDBRateLimited→429, TMDBServerError→502, TMDBTransportError→503, base TMDBError→502, and delegates non-TMDB to `drf_exception_handler`
- [x] 1.2 GREEN: add `tmdb_exception_handler(exc, context)` + `_STATUS` map in `backend/catalogo/exceptions.py`
- [x] 1.3 RED: add `GetCatalogServiceTest` asserting `get_catalog_service()` returns a `TMDBClientCache` and returns the same instance on repeat calls
- [x] 1.4 GREEN: create `backend/catalogo/service.py` with `@lru_cache(maxsize=1) get_catalog_service()` returning `TMDBClientCache(TMDBClient(), get_redis())`
- [x] 1.5 Set `REST_FRAMEWORK["EXCEPTION_HANDLER"]="catalogo.exceptions.tmdb_exception_handler"` and `DEFAULT_THROTTLE_RATES["catalogo"]="60/min"` in `backend/filmai/settings.py`

## Phase 2: Views + helpers

- [x] 2.1 RED: add `ParamValidationTest` (`APIRequestFactory`) asserting 400 on invalid `tipo`, non-integer `id_tmdb`, missing `query` on search — with no service call
- [x] 2.2 GREEN: add `CatalogoBaseView` (`authentication_classes=[]`, `AllowAny`, `ScopedRateThrottle`, `throttle_scope="catalogo"`) + `_int_param`/`_float_param`/`_validate_tipo` in `backend/catalogo/views.py`
- [x] 2.3 GREEN: add 7 `APIView` subclasses (Trending, NowPlaying, Discover, Search, MovieDetail, TVDetail, Keywords) calling `get_catalog_service()` and returning `Response(data)` passthrough
- [x] 2.4 Detail views use `<id_tmdb>` string converter + in-view `_int_param` → 400 on invalid; discover maps `tipo`/`genero`/`anio`/`min_rating` to the cache call

## Phase 3: Routing + wiring

- [x] 3.1 Create `backend/catalogo/urls.py` with `app_name="catalogo"` and explicit `path()` per endpoint (`trending/`, `now-playing/`, `discover/`, `search/`, `movie/<id_tmdb>/`, `tv/<id_tmdb>/`, `keywords/`)
- [x] 3.2 Add `path("api/catalogo/", include("catalogo.urls"))` to `backend/filmai/urls.py`

## Phase 4: Integration tests

- [x] 4.1 RED: add `EndpointIntegrationTest` (`APIClient` + patch `catalogo.views.get_catalog_service` → `TMDBClientCache` over `httpx.MockTransport` + `fakeredis.FakeRedis`) asserting 200 + passthrough JSON + forwarded args per endpoint
- [x] 4.2 RED: add error→HTTP cases (404/400/429/502/503), GET-only (POST → 405), and throttle (`override_settings` low rate → 429)
- [x] 4.3 Run `docker compose exec -T backend python manage.py test catalogo` — all green; `ruff format . && ruff check .`
