# Proposal: Catalog TMDB REST Endpoints (C-03)

## Intent

Expose the catalog to the Next.js frontend via read-only DRF endpoints that wrap
`TMDBClientCache` (C-02). No discovery data is reachable today; the frontend needs
a stable `/api/catalogo/*` surface to browse, search, and read movie/TV details.

## Scope

### In Scope
- 7 read-only GET endpoints, one per `TMDBClientCache` method
- Query-param + path-param validation (coerce types, reject invalid `tipo`/`id_tmdb`)
- `TMDBError` → HTTP status mapping via a DRF exception handler
- Wire `catalogo/urls.py` into `filmai/urls.py`
- Public rate limiting for the endpoints
- Tests (Django runner, mocked TMDB transport)

### Out of Scope
- DTO/model mapping and materialization (C-04a)
- Mutations: ratings/reviews (C-08)
- DRF pagination (forward TMDB `page` as-is)
- Auth (endpoints are public)

## Capabilities

### New Capabilities
- `tmdb-endpoints`: read-only DRF REST layer wrapping `TMDBClientCache`

### Modified Capabilities
- None

## Approach

Thin DRF views (function-based or `APIView` — resolve in design) that parse
validated query params, delegate to a shared `TMDBClientCache` instance, and return
the raw TMDB JSON unchanged (passthrough serialization). A DRF custom exception
handler maps `TMDBError` subclasses to HTTP statuses. Public (AllowAny) with a
`ScopedRateThrottle` per endpoint group.

### Endpoint map

| Endpoint | Cache method | Params |
|----------|-------------|--------|
| `GET /api/catalogo/trending/` | `get_trending` | media_type, time_window, page |
| `GET /api/catalogo/now-playing/` | `get_now_playing` | page |
| `GET /api/catalogo/discover/` | `discover` | tipo, genero, anio, min_rating, page |
| `GET /api/catalogo/search/` | `search` | query, tipo, page |
| `GET /api/catalogo/movie/{id_tmdb}/` | `get_movie_detail` | id_tmdb |
| `GET /api/catalogo/tv/{id_tmdb}/` | `get_tv_detail` | id_tmdb |
| `GET /api/catalogo/keywords/` | `get_keywords` | id_tmdb, tipo |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/catalogo/urls.py` | New | Endpoint routing |
| `backend/catalogo/views.py` | Modified | Add DRF views |
| `backend/catalogo/exceptions.py` | New handler | `TMDBError` → HTTP |
| `backend/filmai/urls.py` | Modified | `include("catalogo.urls")` |
| `backend/filmai/settings.py` | Modified | Throttle rates |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Error mapping ambiguity (429→429, 404→404, 5xx→502/503) | Med | Define explicit table in design |
| URL/view style (function vs APIView vs viewsets) | Low | Decide in design |
| Public throttle config (scope per group) | Med | `ScopedRateThrottle` per endpoint |
| `TMDBClientCache` singleton wiring | Med | Module-level lazy singleton in design |

## Rollback Plan

Revert `catalogo/urls.py` include and new views; C-01 client and C-02 cache are
untouched, so the change is isolated to the REST layer. No migrations.

## Dependencies

- C-01 `TMDBClient` and C-02 `TMDBClientCache` (already on main)

## Success Criteria

- [ ] All 7 endpoints return TMDB JSON with correct status codes
- [ ] `TMDBNotFound` → 404 and `TMDBRateLimited` → 429 verified
- [ ] Tests pass via `python manage.py test` (no real network)
