# Design: Catalog TMDB REST Endpoints (C-03)

## Technical Approach

A thin, read-only DRF layer over `TMDBClientCache` (C-02). Seven `APIView`
subclasses parse/validate query and path params, delegate to a lazily-built
singleton cache, and return TMDB JSON **unchanged** (no serializer, no DRF
pagination). A DRF `EXCEPTION_HANDLER` maps `TMDBError` subclasses to HTTP
statuses; a shared `ScopedRateThrottle` bounds public load.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|---|---|---|---|
| View style | FBV `@api_view` · `APIView` · viewsets | Viewsets assume models/querysets + routers; wrong for custom-param read-only. FBV has no codebase precedent (`usuarios` is all class-based) and makes throttle/auth wiring fiddly. `APIView` matches convention and lets one base class DRY the four class attrs. | `APIView` subclasses over a shared `CatalogoBaseView` |
| Error mapping | Per-view try/except · DRF `EXCEPTION_HANDLER` | Per-view duplicates 5 mappings across 7 views. A single handler is the DRF idiom and covers future endpoints automatically. | Central `tmdb_exception_handler` |
| Singleton | Module-level instance · lazy getter | Module-level instance builds at import (reads settings + connects Redis at startup, breaks tests). A `lru_cache` getter builds on first request. | Lazy `get_catalog_service()` |
| Throttle | Global `DEFAULT_THROTTLE_CLASSES` · per-view `ScopedRateThrottle` | Global breaks existing `usuarios` views (no `throttle_scope` → `ImproperlyConfigured`). Per-view is isolated. | Per-view `ScopedRateThrottle`, scope `catalogo` |

## Data Flow

```
Browser ──> urls.py ──> CatalogoBaseView.get() ──> get_catalog_service()
                                                          │  (lru_cache)
                                          TMDBClientCache ──> TMDBClient ──> TMDB
                                                          └──> Redis (cache/TTL)
```

## Error Mapping

Resolved 502/503 split: 502 = TMDB *reachable* but returned 5xx; 503 = TMDB
*unreachable* (network/timeout/bad JSON).

| Exception | HTTP | Semantics |
|---|---|---|
| `TMDBNotFound` | 404 | resource absent upstream |
| `TMDBBadRequest` | 400 | invalid upstream request |
| `TMDBRateLimited` | 429 | TMDB throttle exceeded |
| `TMDBServerError` | 502 | upstream 5xx after retries |
| `TMDBTransportError` | 503 | network/timeout/unreadable |
| `TMDBError` (base) | 502 | fallback: upstream of unknown kind |

Handler in `catalogo/exceptions.py`:
```python
_STATUS = {TMDBNotFound: 404, TMDBBadRequest: 400, TMDBRateLimited: 429,
           TMDBServerError: 502, TMDBTransportError: 503}

def tmdb_exception_handler(exc, context):
    if isinstance(exc, TMDBError):
        return Response({"detail": str(exc)},
                        status=_STATUS.get(type(exc), 502))
    return drf_exception_handler(exc, context)
```
Wired via `REST_FRAMEWORK["EXCEPTION_HANDLER"] = "catalogo.exceptions.tmdb_exception_handler"`.

## Query-Param → Method-Arg Mapping

Shared `CatalogoBaseView` sets `authentication_classes = []`,
`permission_classes = [AllowAny]`, `throttle_classes = [ScopedRateThrottle]`,
`throttle_scope = "catalogo"`. Coercion helpers `_int_param` / `_float_param` /
`_validate_tipo` (tipo ∈ {movie, tv} else 400; `id_tmdb` positive int else 400).

| Endpoint | Cache call |
|---|---|
| `GET trending/` | `get_trending(media_type, time_window, page)` — defaults `all`/`week`/`1` |
| `GET now-playing/` | `get_now_playing(page)` |
| `GET discover/` | `discover(tipo, genero, anio, min_rating, page)` |
| `GET search/` | `search(query, tipo, page)` — `query` required, else 400 |
| `GET movie/<id_tmdb>/` | `get_movie_detail(id_tmdb)` |
| `GET tv/<id_tmdb>/` | `get_tv_detail(id_tmdb)` |
| `GET keywords/` | `get_keywords(id_tmdb, tipo)` — both query params |

Detail paths use the string converter `<id_tmdb>` (NOT `<int:>`, which 404s on
non-integer, contradicting the spec's 400 contract) and validate in-view.

## Routing

`backend/catalogo/urls.py` (new): `app_name = "catalogo"` with explicit `path()`
per endpoint. Include in `filmai/urls.py`: `path("api/catalogo/", include("catalogo.urls"))`.

## Singleton Wiring

`backend/catalogo/service.py` (new) — composition root:
```python
@lru_cache(maxsize=1)
def get_catalog_service():
    return TMDBClientCache(TMDBClient(), get_redis())
```
Views `from catalogo.service import get_catalog_service` and call it inside
`get()` (lazy). Tests patch `catalogo.views.get_catalog_service` (or
`catalogo.service.get_catalog_service`) with a fake built from
`httpx.MockTransport` + `fakeredis.FakeRedis`; reset via `cache_clear()`.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/catalogo/views.py` | Modify | 7 `APIView` classes + base |
| `backend/catalogo/urls.py` | Create | routing + `app_name` |
| `backend/catalogo/service.py` | Create | lazy singleton getter |
| `backend/catalogo/exceptions.py` | Modify | add `tmdb_exception_handler` |
| `backend/filmai/urls.py` | Modify | `include("catalogo.urls")` |
| `backend/filmai/settings.py` | Modify | `EXCEPTION_HANDLER` + `"catalogo": "60/min"` |
| `backend/catalogo/tests.py` | Modify | endpoint tests |

## Throttling

Single shared scope: `DEFAULT_THROTTLE_RATES["catalogo"] = "60/min"`. Applied
per-view (`throttle_scope = "catalogo"`), never globally. ScopedRateThrottle
keys by IP for anon and user PK when authenticated — one rate covers both with
no extra config. 60/min ≈ sane public browse rate; cache layer absorbs TMDB hits.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | exception handler statuses | call `tmdb_exception_handler(exc, {})` per class |
| Unit | param coercion/validation | call view `.get()` with `APIRequestFactory`; assert 400 on bad `tipo`/`id_tmdb`, no TMDB call |
| Integration | 7 endpoints | `APIClient` + patched `get_catalog_service` → fake `TMDBClientCache(httpx.MockTransport handler, fakeredis)`; assert 200 + passthrough JSON + forwarded args (inspect handler requests) |
| Integration | error → HTTP | handler returns 404/400/429/500/connect-error → assert 404/400/429/502/503 |
| Integration | throttle + GET-only | `override_settings` low rate → 429; POST → 405 |

## Threat Matrix

N/A — no shell command, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. (HTTP "routing" here is Django
URL dispatch, not shell/command routing.)

## Migration / Rollout

No migration. Rollback = revert `catalogo/urls.py` include + new views; C-01/C-02
untouched. Feature-flag not required (read-only surface).

## Open Questions

- None.
