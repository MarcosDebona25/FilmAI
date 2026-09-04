# Tasks: TMDB Redis Cache (C-02)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~250 (range 220–280) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Cache layer + tests | PR 1 | `docker compose exec -T backend python manage.py test catalogo` | N/A — deterministic `fakeredis` + `httpx.MockTransport`, no external services | delete `backend/catalogo/cache.py`, drop `fakeredis` from `requirements.txt` |

## Phase 1: Foundation

- [x] 1.1 Add `fakeredis>=2.0,<3.0` to `backend/requirements.txt` (test-only dep)
- [x] 1.2 RED: in `backend/catalogo/tests.py` add `test_build_key_is_stable` — assert `_build_key(endpoint, params)` equal for param dicts in different key order
- [x] 1.3 GREEN: create `backend/catalogo/cache.py` with `ENDPOINT_TTLS` and `_build_key` (sha256 of sorted-param JSON, includes path-segment args)

## Phase 2: Cache-aside core

- [x] 2.1 RED: add `test_cache_hit_no_tmdb_call` and `test_cache_miss_calls_and_stores` (fresh `FakeRedis` per test)
- [x] 2.2 GREEN: implement `TMDBClientCache(client, redis)` with generic `_cached_call` + 7 mirror methods; `json.dumps`/`json.loads`; corrupt JSON → miss
- [x] 2.3 RED: add `test_ttl_applied_per_endpoint` — assert `redis.ttl(key)` ≈ `ENDPOINT_TTLS[endpoint]`
- [x] 2.4 GREEN: store via `redis.set(key, json.dumps(result), ex=ENDPOINT_TTLS[endpoint])`

## Phase 3: Degradation + factory

- [x] 3.1 RED: add degrade tests — GET raising `redis.ConnectionError` → TMDB called, no RedisError; SET raising → result still returned
- [x] 3.2 GREEN: catch only `redis.RedisError` (GET fail → bypass + skip SET; SET fail → swallow); let `TMDBError` propagate
- [x] 3.3 GREEN: add `get_redis()` factory using `redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)`
- [x] 3.4 Add `test_round_trip_preserves_structure` (nested dict stored → retrieved equal)

## Phase 4: Verification

- [x] 4.1 Verify `REDIS_URL` already defined in `backend/filmai/settings.py` (line 317) and documented in `.env.example` (line 98) — no edit needed
- [x] 4.2 Run `docker compose exec -T backend python manage.py test` + `ruff check .` + `ruff format --check .`

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `backend/catalogo/tests.py` | Unit | N/A (config) | ✅ Written | ✅ Passed | ➖ Structural | ✅ Clean |
| 1.2-1.3 | `backend/catalogo/tests.py` | Unit | ✅ 9/9 | ✅ Import failure | ✅ 16/16 | ✅ 2 key cases | ✅ Ruff clean |
| 2.1-2.4 | `backend/catalogo/tests.py` | Unit | ✅ 9/9 | ✅ Import failure | ✅ 16/16 | ✅ 7 endpoint cases | ✅ Ruff clean |
| 3.1-3.4 | `backend/catalogo/tests.py` | Unit | ✅ 9/9 | ✅ Import failure | ✅ 16/16 | ✅ GET/SET degradation + round-trip | ✅ Ruff clean |
| 4.1-4.2 | `backend/catalogo/tests.py` | Unit | ✅ 16/16 | N/A (verification) | ✅ 16/16 | ➖ Verification | ✅ Clean |

## Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `docker compose exec -T backend python manage.py test catalogo` — exit 0, 16 tests passed |
| Runtime harness command/scenario and exact result | N/A — deterministic `fakeredis` + `httpx.MockTransport`, no external runtime boundary |
| Rollback boundary | Delete `backend/catalogo/cache.py`, remove cache tests, and drop `fakeredis` from `backend/requirements.txt` |
