# Proposal: TMDB API Client (C-01)

## Intent

Build `TMDBClient`, the thin service that talks to TMDB API v3. It is the
foundation of the catalog module: C-02 (Redis cache), C-03 (catalog endpoints),
and the UI (C-05/C-06/C-07) all depend on it. This is the "live TMDB" half of
the hybrid catalog — discovery is served live from TMDB with a Redis cache;
PostgreSQL stays the source of truth for user data and semantic search.

## Scope

### In Scope

- `httpx`-based client (new dependency → `backend/requirements.txt`)
- Settings via `python-decouple`: `TMDB_API_KEY`, `TMDB_API_BASE_URL`,
  `TMDB_TIMEOUT` (default 5s); timeout is new in `.env.example`
- Exception hierarchy in `backend/catalogo/exceptions.py`
- Retry/backoff on transitory errors only (429/5xx/network), honoring
  `Retry-After`; NO retry on 4xx
- Methods: `get_trending`, `get_now_playing`, `discover`, `search`,
  `get_movie_detail`, `get_tv_detail`, `get_keywords`
- Tests with `httpx.MockTransport` (no real API calls)

### Out of Scope

Redis cache (C-02), catalog endpoints (C-03), materialization + embedding
(C-04a), Celery sync (C-04b), all UI work.

## Capabilities

### New Capabilities

- `tmdb-client`: TMDB API v3 HTTP client for live catalog discovery.

### Modified Capabilities

None.

## Approach

Thin wrapper over `httpx` returning raw parsed JSON — no mapping to Django
models (that is C-04a). Auth via `api_key` query param (`?api_key=...`).
Transitory-error retry with exponential backoff keyed to `Retry-After`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/catalogo/client.py` | New | `TMDBClient` service |
| `backend/catalogo/exceptions.py` | New | `TMDBError` hierarchy |
| `backend/requirements.txt` | Modified | add `httpx` |
| `.env.example` | Modified | add `TMDB_TIMEOUT` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| TMDB rate limiting / quota cost | Med | honor `Retry-After`, backoff; cache lands in C-02 |
| Env var naming drift (`TMDB_BASE_URL` vs existing `TMDB_API_BASE_URL`) | Med | resolve in Open Questions before spec |

## Rollback Plan

Client is additive; nothing existing depends on it. Revert = delete
`backend/catalogo/client.py` + `exceptions.py`, remove `httpx` from
`requirements.txt`, remove `TMDB_TIMEOUT` from `.env.example`.

## Dependencies

- `httpx` (new) in `backend/requirements.txt`

## Success Criteria

- [ ] Every method returns parsed JSON, covered by `httpx.MockTransport` tests
- [ ] 429/5xx/network retry with backoff; 4xx never retry
- [ ] `ruff check .` + `ruff format --check .` pass; `python manage.py test` green
- [ ] Exception hierarchy maps status codes correctly

## Open Questions

- Resolved: use the existing `TMDB_API_BASE_URL` from `.env.example` (confirmed
  with the maintainer before spec).
