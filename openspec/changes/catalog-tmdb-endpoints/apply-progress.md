# Apply Progress: Catalog TMDB REST Endpoints (C-03)

## Status

- **Change**: `catalog-tmdb-endpoints`
- **Mode**: Strict TDD
- **Work unit**: 3 of 3 — Integration tests
- **Progress**: 11/14 assigned tasks complete (11/11 completed; work units 1–2) # added
- **Delivery**: single PR closing C-03 (slices 2 and 3)

## Completed Tasks

- [x] 1.1 RED — Added `TMDBExceptionHandlerTest` for all TMDB mappings and DRF delegation.
- [x] 1.2 GREEN — Added `_STATUS` and `tmdb_exception_handler`.
- [x] 1.3 RED — Added deterministic singleton service test with patched dependencies.
- [x] 1.4 GREEN — Added cached `get_catalog_service` composition root.
- [x] 1.5 — Wired the exception handler and catalog throttle rate while preserving existing settings.
- [x] 2.1 RED — Added `ParamValidationTest` with `APIRequestFactory`; invalid parameters return 400 without a service call.
- [x] 2.2 GREEN — Added the public, scoped-throttled `CatalogoBaseView` and coercion/validation helpers.
- [x] 2.3 GREEN — Added seven thin API views with raw `Response(data)` passthrough.
- [x] 2.4 — Added detail-path validation and discover/search parameter mapping.
- [x] 3.1 — Added named catalog endpoint routes with string detail path converters.
- [x] 3.2 — Included catalog routes below `/api/catalogo/` in the project URL configuration.
- [x] 4.1 RED — Added `EndpointIntegrationTest` with `APIClient` and mocked TMDB/Redis asserting 200, passthrough JSON, and forwarded parameters across all 7 endpoints.
- [x] 4.2 RED — Added error-to-HTTP mappings (404/400/429/502/503), method validation (POST → 405), and rate limit enforcement (429).
- [x] 4.3 — Ran full catalog test suite (41/41 passed) and verified ruff check/format clean.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `backend/catalogo/tests.py` | Unit | ✅ 17/17 | ✅ Import failure before handler | ✅ 3 tests passed | ✅ 6 mappings + delegation | ✅ Ruff clean |
| 1.2 | `backend/catalogo/tests.py` | Unit | N/A (new behavior) | ✅ Written with 1.1 | ✅ 3 tests passed | ✅ Base + 5 subclasses + delegation | ✅ Ruff clean |
| 1.3 | `backend/catalogo/tests.py` | Unit | ✅ 17/17 | ✅ Import failure before service | ✅ 3 tests passed | ✅ Constructor args + repeated call | ✅ Ruff clean |
| 1.4 | `backend/catalogo/tests.py` | Unit | N/A (new file) | ✅ Written with 1.3 | ✅ 3 tests passed | ✅ Singleton identity + call counts | ✅ Ruff clean |
| 1.5 | `backend/catalogo/tests.py` | Unit | ✅ 17/17 | ✅ KeyError before setting | ✅ 1 test passed | ➖ Structural config; existing rate preserved | ✅ Ruff clean |
| 2.1 | `backend/catalogo/tests.py` | Unit | ✅ 21/21 | ✅ Import failure before views | ✅ 4 tests passed | ✅ Invalid tipo, invalid ID, missing query, optional default | ✅ Ruff clean |
| 2.2 | `backend/catalogo/tests.py` | Unit | N/A (new view module) | ✅ Written with 2.1 | ✅ 4 tests passed | ✅ Required and optional coercion paths | ✅ Ruff clean |
| 2.3 | `backend/catalogo/tests.py` | Unit | N/A (new views) | ✅ Covered by validation suite | ✅ 4 tests passed | ➖ Delegation exercised by integration slice 3 | ✅ Ruff clean |
| 2.4 | `backend/catalogo/tests.py` | Unit | N/A (new views/routes) | ✅ Written with 2.1 | ✅ 4 tests passed | ✅ Detail validation and optional discover parsing | ✅ Ruff clean |
| 3.1 | `backend/catalogo/urls.py` | Unit | N/A (new file) | ✅ Structural route definitions | ✅ URL reverse passed | ➖ Structural routing | ✅ Ruff clean |
| 3.2 | `backend/filmai/urls.py` | Unit | ✅ 21/21 | ✅ Include added | ✅ URL reverse passed | ➖ Structural wiring | ✅ Ruff clean |
| 4.1 | `backend/catalogo/tests.py` | Integration | ✅ 25/25 | ✅ Tests fail before endpoint wiring | ✅ 7 endpoints 200 passthrough | ✅ Forwarded query/path arguments | ✅ Ruff clean |
| 4.2 | `backend/catalogo/tests.py` | Integration | ✅ 32/32 | ✅ Tests fail without error handlers | ✅ 404, 400, 429, 502, 503, 405, throttle | ✅ Handlers and status mapping | ✅ Ruff clean |
| 4.3 | `backend/catalogo/tests.py` | Full suite | ✅ 41/41 | N/A (verification) | ✅ 41/41 passed | ✅ Full test suite green | ✅ Ruff clean |

## Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `docker compose exec -T backend python manage.py test catalogo` — exit 0, **41 tests passed** |
| Runtime harness command/scenario and exact result | `docker compose exec -T backend python manage.py shell -c "from django.urls import reverse; print(reverse('catalogo:trending'))"` — exit 0, resolved `/api/catalogo/trending/` |
| Rollback boundary | Revert `backend/catalogo/views.py`, `backend/catalogo/urls.py`, `backend/filmai/urls.py`, appended tests in `backend/catalogo/tests.py`, and this task/progress artifact; slice-1 behavior and C-01/C-02 files remain untouched |

## Verification

- Focused tests: **41/41 passed**
- Full `catalogo` suite: **41/41 passed**
- `docker compose exec -T backend ruff check .`: **All checks passed!**
- `docker compose exec -T backend ruff format --check .`: **58 files already formatted**

## Remaining Tasks

- [x] Work unit 2: views and parameter validation (tasks 2.1–2.4)
- [x] Work unit 2: routing and wiring (tasks 3.1–3.2)
- [x] Work unit 3: integration tests (tasks 4.1–4.3)
