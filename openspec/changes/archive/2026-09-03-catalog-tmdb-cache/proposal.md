# Proposal: TMDB Redis Cache (C-02)

## Intent

Add a Redis cache layer over the existing `TMDBClient` using the cache-aside
pattern: check Redis first; on hit return instantly; on miss call TMDB, store
with a TTL, then return. Cuts TMDB API cost and latency for live discovery and
adds resilience against the rate-limit/quota risk flagged in C-01.

## Scope

### In Scope

- Cache all 7 `TMDBClient` methods: `get_trending`, `get_now_playing`,
  `discover`, `search`, `get_movie_detail`, `get_tv_detail`, `get_keywords`.
- Cache-aside flow per method.
- Graceful degradation: Redis failure/timeout → bypass cache, call TMDB
  directly, never fail a request because Redis is down.
- TTL-only invalidation. TTL per endpoint:

  | Group | Methods | TTL |
  |---|---|---|
  | Lists | trending, now_playing, discover | 6h |
  | Search | search | 1h |
  | Details | movie_detail, tv_detail, keywords | 24h |

- Redis key: `tmdb:{endpoint}:{params_hash}` — stable hash of sorted query
  params.

### Out of Scope

- Manual/event-driven invalidation (TTL only).
- Catalog REST endpoints (C-03), materialization/embedding (C-04a), Celery
  sync (C-04b), UI.
- Changes to `TMDBClient`'s public contract or error hierarchy.

## Capabilities

### New Capabilities

- `tmdb-cache`: Redis cache-aside layer wrapping `TMDBClient`.

### Modified Capabilities

None.

## Approach

New cache class (e.g. `TMDBClientCache`) that receives a `TMDBClient` and a
Redis connection; composition over wrapping/inheritance (final shape decided in
design). Each public method mirrors the client, computes the key from endpoint +
sorted params, runs the cache-aside flow, and serializes JSON via
`json.dumps`/`json.loads`. Uses `redis>=5.2` (already in `requirements.txt`) and
the `redis` compose service (already up).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/catalogo/cache.py` | New | `TMDBClientCache` cache-aside layer |
| `backend/catalogo/tests.py` | Modified | cache-layer tests (strategy TBD — see risks) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Test strategy: `fakeredis` vs real Redis test container (strict TDD, `docker compose exec -T backend python manage.py test`) | Med | Resolve in design before specs/tasks |
| Cache composition: wrap `TMDBClient` vs new class taking the client | Med | Resolve in design; spec-level behavior unchanged either way |
| TTL mapping drift across code/tests/docs (needs a single source of truth) | Med | Centralize TTL map in one place; resolve in design |
| Stale data served until TTL expiry (no invalidation) | Med | TTLs chosen to match data volatility; acceptable for discovery |

## Rollback Plan

Additive layer. Revert = delete `backend/catalogo/cache.py` and its tests;
callers fall back to `TMDBClient` directly. No schema, migration, or env changes.

## Dependencies

- `redis>=5.2` (already in `requirements.txt`) + `redis` compose service.

## Success Criteria

- [ ] Cache hit returns without calling TMDB; miss calls TMDB then caches with
      the correct TTL
- [ ] Redis down → TMDB called directly, request still succeeds
- [ ] Stable key: same params in any order → same key
- [ ] `ruff check .` + `ruff format --check .` pass; `python manage.py test` green
