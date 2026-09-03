# Tasks: TMDB API Client (C-01)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~320 additions, ~1 deletion (client ~100, tests ~170, exceptions ~20, config/deps ~10) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Thin `TMDBClient` + exceptions + config + tests | PR 1 | `python manage.py test catalogo` (from `backend/`) | `python manage.py test` (from `backend/`) | Delete `catalogo/client.py` + `exceptions.py`, drop `httpx`, revert settings/`.env.example` — nothing existing depends on it |

## Phase 1: Foundation — dependency, config, exceptions

- [x] 1.1 Add `httpx` to `backend/requirements.txt` (pinned range, e.g. `httpx>=0.27,<1.0`)
- [x] 1.2 Add `TMDB_API_KEY`, `TMDB_API_BASE_URL`, `TMDB_TIMEOUT` (`cast=float`, default `5`) to `backend/filmai/settings.py`
- [x] 1.3 Add `TMDB_TIMEOUT=5` under the TMDB section of `.env.example`
- [x] 1.4 Create `backend/catalogo/exceptions.py` with `TMDBError` base + `TMDBRateLimited`, `TMDBNotFound`, `TMDBBadRequest`, `TMDBServerError`, `TMDBTransportError`

## Phase 2: Client core (TDD: RED → GREEN)

- [x] 2.1 RED — `catalogo/tests.py`: config tests (default timeout `5.0`; explicit `10.0` via `@override_settings`), auth query param (`api_key=abc123`), raw JSON passthrough — `httpx.MockTransport` + `SimpleTestCase`
- [x] 2.2 GREEN — `catalogo/client.py`: `TMDBClient.__init__` (reads `django.conf.settings`, injectable `transport`), `_get`/`_request` happy path (2xx → `.json()`), merge `api_key` into params
- [x] 2.3 REFACTOR — `ruff check .` + `ruff format .` on new files

## Phase 3: Error mapping + retry (TDD)

- [x] 3.1 RED — tests: 404→`TMDBNotFound`, 503→`TMDBServerError`, 400→`TMDBBadRequest` (single call), `httpx.ConnectError`→`TMDBTransportError`
- [x] 3.2 GREEN — status/transport → exception mapping in `_request` (404, other 4xx, 5xx, `httpx.TransportError`)
- [x] 3.3 RED — tests: 429 `Retry-After:1` then 200 (handler called 2×); always-429 → `TMDBRateLimited` after 4 calls; 400 never retries (1 call)
- [x] 3.4 GREEN — retry loop: `MAX_RETRIES=3`, exponential backoff (`BASE=1s`, factor 2, cap 8s), `Retry-After` as floor; tests patch `time.sleep`

## Phase 4: Discovery + detail methods (TDD)

- [x] 4.1 RED — endpoint tests: trending defaults (`/trending/all/week`), discover movie+tv filters (`with_genres`, `primary_release_year`/`first_air_date_year`, `vote_average.gte`), now_playing, search, movie/tv detail, keywords
- [x] 4.2 GREEN — implement `get_trending`, `get_now_playing`, `discover` (with `_DISCOVER_YEAR_PARAM`), `search`, `get_movie_detail`, `get_tv_detail`, `get_keywords`

## Phase 5: Verification

- [x] 5.1 Run `python manage.py test` (from `backend/`) — full suite green
- [x] 5.2 Run `ruff check .` + `ruff format --check .` (from `backend/`)
- [x] 5.3 Confirm no DB migration; verify rollback plan (additive-only client)
