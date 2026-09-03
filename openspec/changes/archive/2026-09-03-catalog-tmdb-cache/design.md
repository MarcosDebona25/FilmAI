# Design: TMDB Redis Cache (C-02)

## Technical Approach

Add `TMDBClientCache`, a cache-aside wrapper that **composes** the C-01 `TMDBClient` (never modifies it). Each of the 7 public methods is mirrored with an identical signature; internally they run one generic flow: build key → Redis GET → on miss call TMDB → Redis SET with TTL → return. Redis errors degrade to a direct TMDB call. Plain JSON string serialization.

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|---|---|---|---|
| Composition shape | Dedicated cache class w/ DI vs subclass/monkeypatch `TMDBClient` | Dedicated `TMDBClientCache(client, redis)` | Keeps C-01 public contract untouched (out of scope); injectable fakes for tests; no global state |
| Test backend | `fakeredis` (in-memory) vs real `redis` compose service | `fakeredis` | Deterministic, no network, no flush; unit suite stays offline like C-01's `MockTransport` style; only `GET`/`SET` ops are used so fidelity gap is nil |
| TTL source of truth | Inline literals vs single mapping | `ENDPOINT_TTLS` dict in `cache.py`, imported by code + tests | One source of truth prevents drift |
| Stale window | Invalidation vs TTL-only | TTL-only | Accepted tradeoff (proposal); TTLs matched to data volatility |

## Data Flow

```
caller → TMDBClientCache.<method>() → _cached_call(endpoint, params, producer)
        │ Redis GET  (catch RedisError → bypass, skip SET)
        ├─ hit → json.loads → return
        └─ miss → producer() = TMDBClient.<method>()   (TMDBError propagates)
                  → Redis SET ex=TTL  (catch RedisError → ignore) → return
```

## Interfaces / Contracts

```python
# backend/catalogo/cache.py
ENDPOINT_TTLS = {
    "trending": 6*3600, "now_playing": 6*3600, "discover": 6*3600,          # lists
    "search": 1*3600,                                                        # search
    "movie_detail": 24*3600, "tv_detail": 24*3600, "keywords": 24*3600,      # details
}

def _build_key(endpoint: str, params: dict) -> str:
    canonical = json.dumps(params, sort_keys=True, default=str)
    return f"tmdb:{endpoint}:{sha256(canonical.encode()).hexdigest()[:16]}"

class TMDBClientCache:
    def __init__(self, client: TMDBClient, redis: "Redis"): ...
    def get_trending(self, media_type="all", time_window="week", page=1) -> dict
    def get_now_playing(self, page=1) -> dict
    def discover(self, tipo, genero=None, anio=None, min_rating=None, page=1) -> dict
    def search(self, query, tipo, page=1) -> dict
    def get_movie_detail(self, id_tmdb) -> dict
    def get_tv_detail(self, id_tmdb) -> dict
    def get_keywords(self, id_tmdb, tipo) -> dict
```

Canonical params **include path-segment args** (`tipo`, `id_tmdb`, `media_type`, `time_window`), not just query params — the client maps those into the URL path, so hashing query params only would collide (`discover("movie")` vs `discover("tv")`, `get_movie_detail(550)` vs `551`). This preserves the spec's intent ("identical logical calls map to the same key").

Serialization: `json.dumps(result)` stored as a Redis string; `json.loads(raw)` on hit. Redis client must use `decode_responses=True`. Corrupt JSON on hit → treated as miss.

Degradation: only `redis.RedisError` (base) is caught. GET failure → bypass and skip SET; SET failure → swallow, still return result. `TMDBError` subclasses propagate unchanged.

Settings: `REDIS_URL` already exists in `backend/filmai/settings.py` (`redis://redis:6379/0`); add a factory `get_redis()` that builds `redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)`. Verified: docker-compose redis service is `redis` on 6379 (healthcheck present).

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/catalogo/cache.py` | Create | `TMDBClientCache`, `ENDPOINT_TTLS`, `_build_key`, `get_redis()` |
| `backend/catalogo/tests.py` | Modify | Cache-layer tests |
| `backend/filmai/settings.py` | Modify | Add `get_redis()` factory (reuse existing `REDIS_URL`) |
| `backend/requirements.txt` | Modify | Add `fakeredis` (test dep) |
| `.env.example` | Modify | Add `REDIS_URL` |

## Testing Strategy

`SimpleTestCase` (no DB) + `fakeredis.FakeRedis(decode_responses=True)` + `TMDBClient` with `httpx.MockTransport` (C-01 style). Determinism: fresh `FakeRedis` per test — no shared state, no flush, no dependency on the compose `redis` service.

| Layer | Test |
|---|---|
| Hit | Pre-populate key → cached returned, handler called 0× |
| Miss | Handler called 1×; result stored; `redis.ttl(key)` ≈ `ENDPOINT_TTLS`; result returned |
| Degrade GET | Stub redis raising `redis.ConnectionError` → TMDB called, no RedisError propagates |
| Degrade SET | Stub redis raising on `.set` → result still returned |
| Stable key | `_build_key` equal for param dicts in different orders |
| Round-trip | Nested dict stored then retrieved equal |

## Threat Matrix

N/A — in-process cache-aside; no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

Additive; no migration. Rollback = delete `cache.py` + tests, drop `fakeredis`/`REDIS_URL`. Callers fall back to `TMDBClient`.

## Open Questions

- (resolved) docker-compose `redis` service confirmed as `redis:6379` with healthcheck; `redis>=5.2,<6.0` present in `requirements.txt`.
- Decide at apply whether to use a dedicated Redis DB index (e.g. `redis://redis:6379/1`) for the TMDB cache to avoid mixing with the DRF rate-limit keys (currently shares DB 0).
