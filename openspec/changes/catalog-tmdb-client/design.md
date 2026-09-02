# Design: TMDB API Client (C-01)

## Technical Approach

Thin, synchronous `httpx` wrapper returning raw parsed JSON (no Django model mapping). Auth via `api_key` query param (TMDB v3). Config centralized in `settings.py` (decouple loader); client reads `django.conf.settings` at instantiation. Manual retry loop for transitory errors only.

## Architecture Decisions

| Decision | Option | Tradeoff | Choice |
|---|---|---|---|
| Config location | `decouple.config()` in `client.py` vs in `settings.py` | Direct reads duplicate env access; no app reads env today | `settings.py` (via decouple); client reads `django.conf.settings` |
| Retry mechanism | httpx/httpcore transport retry vs manual loop vs `tenacity` | Transport retries are opaque & don't expose `Retry-After`; `tenacity` = new dep | Manual loop |
| Retry budget | `MAX_RETRIES=3`, `BASE_BACKOFF=1s`, factor 2, cap 8s | Unbounded risk loops; 3 retries + cap honors TMDB limits | `MAX_RETRIES=3`, exp backoff, `Retry-After` as floor |
| Test injection | Constructor `transport` kwarg | Patching `httpx.Client` is brittle | Inject `transport` (default `httpx.HTTPTransport()`) |

**Rationale**: matches existing convention; manual loop is transparent and testable via `MockTransport` + patched `time.sleep`.

## Data Flow

```
caller ─→ TMDBClient.<method>() ─→ _get(path, params)  [merge api_key]
                                        │
                                        ▼
                                _request() retry loop
                                        │
                          ┌─────────────┴──────────────┐
                          2xx→json │ 429/5xx/transport │ 4xx→raise (no retry)
                                   │   retry→sleep      │
                                   ▼                    ▼
                              parsed JSON          TMDBError subclass
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/catalogo/client.py` | Create | `TMDBClient` + retry loop + param builders |
| `backend/catalogo/exceptions.py` | Create | `TMDBError` hierarchy |
| `backend/catalogo/tests.py` | Modify | Replace stub with `MockTransport` tests |
| `backend/filmai/settings.py` | Modify | Add `TMDB_API_KEY`, `TMDB_API_BASE_URL`, `TMDB_TIMEOUT` |
| `backend/requirements.txt` | Modify | Add `httpx` |
| `.env.example` | Modify | Add `TMDB_TIMEOUT=5` under TMDB section |

## Interfaces / Contracts

```python
# exceptions.py
class TMDBError(Exception): ...
class TMDBRateLimited(TMDBError): ...   # 429
class TMDBNotFound(TMDBError): ...      # 404
class TMDBBadRequest(TMDBError): ...    # other 4xx
class TMDBServerError(TMDBError): ...   # 5xx
class TMDBTransportError(TMDBError): ...# network/timeout
```

```python
# client.py
class TMDBClient:
    def __init__(self, *, api_key=None, base_url=None, timeout=None, transport=None):
        # defaults from settings.TMDB_* ; timeout from settings.TMDB_TIMEOUT (5s)
        self.timeout = timeout if timeout is not None else settings.TMDB_TIMEOUT
        self._client = httpx.Client(base_url=..., timeout=..., transport=...)

    def get_trending(self, media_type="all", time_window="week", page=1) -> dict
    def get_now_playing(self, page=1) -> dict
    def discover(self, tipo, genero=None, anio=None, min_rating=None, page=1) -> dict
    def search(self, query, tipo, page=1) -> dict
    def get_movie_detail(self, id_tmdb) -> dict
    def get_tv_detail(self, id_tmdb) -> dict
    def get_keywords(self, id_tmdb, tipo) -> dict
```

Param building (`tipo` is a **path segment**, never a query param):

```python
_DISCOVER_YEAR_PARAM = {"movie": "primary_release_year", "tv": "first_air_date_year"}

def discover(self, tipo, genero=None, anio=None, min_rating=None, page=1):
    params = {"page": page}
    if genero is not None: params["with_genres"] = genero
    if anio is not None: params[_DISCOVER_YEAR_PARAM[tipo]] = anio
    if min_rating is not None: params["vote_average.gte"] = min_rating
    return self._get(f"/discover/{tipo}", params)
```

Verified against TMDB v3 docs: `with_genres`, `primary_release_year` (movie), `first_air_date_year` (tv), `vote_average.gte`, `page`; search: `query`, `page`.

Retry + mapping (private `_request(path, params)`):

```python
MAX_RETRIES, BASE_BACKOFF, BACKOFF_FACTOR, MAX_BACKOFF = 3, 1.0, 2, 8.0
# for attempt in range(MAX_RETRIES + 1):
#   try: resp = self._client.get(path, params={**params, "api_key": key})
#   except httpx.TransportError → delay, retry, else TMDBTransportError
#   2xx → resp.json(); 429/>=500 → delay = max(retry_after_delta,
#     min(BASE*FACTOR**attempt, MAX_BACKOFF)), retry, else RateLimited/ServerError
#   404 → TMDBNotFound; other 4xx → TMDBBadRequest (no retry)
# `Retry-After`: int seconds; HTTP-date falls back to exponential.
```

`settings.py` additions: `TMDB_API_KEY = config("TMDB_API_KEY", default="")`, `TMDB_API_BASE_URL = config("TMDB_API_BASE_URL", default="https://api.themoviedb.org/3")`, `TMDB_TIMEOUT = config("TMDB_TIMEOUT", default=5, cast=float)`.

## Testing Strategy

`django.test.SimpleTestCase` (no DB) + `httpx.MockTransport` handler inspecting `request.url`. Patch `time.sleep` to skip real delays. `@override_settings` for config.

| Spec scenario | Test |
|---|---|
| Default timeout / Explicit timeout | assert `client.timeout == 5.0` / `== 10.0` |
| Auth query param | handler asserts `request.url.params["api_key"]=="abc123"` |
| Not found / Server error | 404→`TMDBNotFound`; 503→`TMDBServerError` |
| Bad request / transport | 400→`TMDBBadRequest` (1 call); `httpx.ConnectError`→`TMDBTransportError` |
| Retry then success | 429 w/ `Retry-After:1` then 200 → result; handler called 2× |
| No retry on 4xx | 400 → raise, handler called once |
| Bounded retry | always 429 → `TMDBRateLimited`, 4 calls (MAX_RETRIES+1) |
| Trending defaults | path `/trending/all/week`, `page=1` |
| Discover filters | `/discover/movie`, `with_genres=28`, `primary_release_year=2024`, `vote_average.gte=7.5`; TV variant → `first_air_date_year` |
| Search movie | `/search/movie`, `query=Inception` |
| Detail / keywords | `/movie/550`, `/tv/{id}`, `/{tipo}/{id}/keywords` |
| Raw JSON returned | returned dict equals mocked body unchanged |

## Threat Matrix

N/A — outbound HTTP GET client only. No routing, shell, subprocess, VCS/PR automation, executable-file classification, or process integration.

## Migration / Rollout

No migration (no schema change). Add `httpx` to `requirements.txt`; rollback per proposal (delete `client.py`/`exceptions.py`, drop dep + env entry).

## Open Questions

- None blocking. Spec's "read via `decouple.config()`" = decouple loader in `settings.py`; client reads Django settings (matches codebase; only `settings.py` imports decouple).
