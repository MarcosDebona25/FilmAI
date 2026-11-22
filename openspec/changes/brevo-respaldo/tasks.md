# Tasks: Brevo as a fallback for Resend (issue #181)

## Review Workload Forecast

| Field                   | Value                                                                                                                        |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Estimated changed lines | ~700 (backend ~500, frontend and copy ~60, docs ~140)                                                                        |
| 400-line budget risk    | Medium                                                                                                                       |
| Chained PRs recommended | Yes — two PRs: providers and fallback (PR 1), limits and the `email_unavailable` code (PR 2)                                 |
| Delivery strategy       | ask-on-risk                                                                                                                  |
| Chain strategy          | Both PRs from `develop`, one worktree per PR in `~/FilmAI-worktrees/<branch>`; PR 2 stacks on PR 1 (merge commit, no rebase) |
| Blocking                | D-1 to D-6 of `proposal.md` confirmed by the user before task 1.1                                                            |
| CI                      | Active: `.github/workflows/ci.yml` runs on PRs to `main`, `develop`, `develop/**` and `feat/**`; it is the merge gate        |

### Work Units

| PR  | Goal                                                                                   | Est. lines | Focused test command                                                                                                         | Rollback boundary                                                                                         |
| --- | -------------------------------------------------------------------------------------- | ---------: | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 1   | Provider seam, `BrevoBackend`, `RespaldoBackend`, settings, validation, `.env.example` |       ~450 | `python manage.py test filmai.tests filmai.test_email_respaldo`                                                              | `EMAIL_BACKEND=filmai.email_backends.ResendBackend`; the refactored `ResendBackend` keeps its tests green |
| 2   | Throttle comment and tests, `email_unavailable` 503, atomic registration, copy, docs   |       ~250 | `python manage.py test usuarios.test_seguridad_throttles usuarios.test_errores_registro` and `npm run test:unit -- registro` | Revert the view wrappers; the code stays unused in the catalog                                            |

## Phase 0: Confirm the open decisions

- [x] 0.1 Ask the user D-1 to D-6 (`proposal.md`) and record the answers in
      `design.md` before writing code. If an answer differs from the
      recommendation, update `design.md`, the spec delta and these tasks first
- [x] 0.2 Explain: what a Django email backend is, why the fallback lives
      there and not in `enviar_correo()`, what "transient" means for an error

## Phase 1: Providers and fallback (PR 1)

- [x] 1.1 Create the branch from `develop` and its worktree; `codegraph init`
      in the new worktree
- [x] 1.2 Inside the backend container (`docker compose exec backend python`,
      no install): check which HTTP client the installed `resend` SDK uses,
      which exception a connection error and a timeout raise, and its default
      timeout. Write the result in `design.md` («Which errors fall back»)
- [x] 1.3 RED `filmai/tests.py` stays green as the regression net for
      `ResendBackend` (run it before touching the module)
- [x] 1.4 RED `filmai/test_email_respaldo.py` — `ProveedorBrevo` with
      `httpx.MockTransport`: URL, `api-key` header, `sender` parsed from
      `"FilmAI <x@y>"`, separate `to`/`cc`/`bcc`, `htmlContent` +
      `textContent`, text-only message wrapped in `<pre>`, `BREVO_TEST_RECIPIENT`
      redirect (only the count in the log), `cc`-only promoted to `to`,
      returns `messageId`
- [x] 1.5 RED: Brevo error mapping — 400 → not transient; 401, 402, 403, 429,
      500, `ConnectTimeout`, `ReadTimeout`, `ConnectError` → transient; the
      status and Brevo's `code` travel in `ErrorDeProveedor`
- [x] 1.6 RED: Resend error mapping with the SDK's own classes —
      `RateLimitError` (each of the three types), `ApplicationError`,
      `MissingApiKeyError`, `InvalidApiKeyError` and the transport error from
      1.2 → transient; `ValidationError`, `MissingRequiredFieldsError` → not
- [x] 1.7 GREEN: `ErrorDeProveedor`, `EnvioFallido`, the `Proveedor` protocol,
      `ProveedorResend` (today's `_send_one` moved), `ProveedorBrevo` with
      `httpx.Client(timeout=10)`, shared `_destinatarios` and `_extraer_html`;
      `ResendBackend` and `BrevoBackend` over the shared loop
- [x] 1.8 RED `RespaldoBackend`: - Resend OK → Brevo never called; log says Resend - Resend 429 / 5xx / network / 401 → Brevo sends; WARNING with the
      reason, INFO says Brevo - Resend 422 → Brevo not called; raises (or 0 with `fail_silently`) - both fail → `EnvioFallido` with both statuses; with `fail_silently`
      returns 0 and logs ERROR - two messages, Resend fails only on the second → first sent once by
      Resend, second by Brevo, return value 2 - no `BREVO_API_KEY` → behaves as Resend alone; no Resend key → Brevo
      alone; neither → error log, 0 (as today) - no log line contains an address (assert over `assertLogs` output)
- [x] 1.9 GREEN: `RespaldoBackend`
- [x] 1.10 Settings: `BREVO_API_KEY`, `BREVO_FROM_EMAIL`,
      `BREVO_TEST_RECIPIENT` next to the `RESEND_*` block; update the
      `EMAIL_BACKEND` error message to list the three backends
- [x] 1.11 RED `validar_configuracion_email` (in `filmai/tests.py`): the
      matrix of «Configuration» in `design.md` — `BrevoBackend` without key,
      with test recipient; `RespaldoBackend` missing either key, with either
      test recipient, empty `BREVO_FROM_EMAIL` with a `@resend.dev` default
      sender; valid production config passes; `debug=True` never raises
- [x] 1.12 GREEN: extend `validar_configuracion_email` (keyword-only
      arguments, so the call in `settings.py` names each one)
- [x] 1.13 `.env.example`: «Opción C — Resend con Brevo de respaldo», each
      variable with its comment and how to verify the single sender in Brevo
- [x] 1.14 `send_test_email`: print the provider chain and both test
      recipients; mention `BREVO_API_KEY` in the failure hint
- [x] 1.15 Explain each test as it is written (skill
      `explicar-al-implementar`): why `MockTransport`, why the SDK's own
      exception classes, what `assertLogs` checks
- [x] 1.16 `ruff format . && ruff check .`; full `python manage.py test`
      (never two runs at once on the machine)

## Phase 2: Limits and the `email_unavailable` code (PR 2)

- [x] 2.1 RED `usuarios/test_seguridad_throttles.py`: the seven email scopes
      keep their rates (D-3) and each view (registration, resend, reset)
      lists the expected throttle classes
- [x] 2.2 `settings.py`: rewrite the comment above the registration/resend
      scopes and the reset ones — what each protects (one inbox, one IP,
      reputation) and the combined free capacity (~400/day, ~12 000/month)
- [x] 2.3 RED `usuarios/test_errores_registro.py`: with both providers
      failing, `POST` registration → 503 (Service Unavailable),
      `code=email_unavailable`, no `Usuario`, no `EmailAddress`; a retry
      after the providers recover → 201 (Created)
- [x] 2.4 RED: resend confirmation with both providers failing → 503
      (Service Unavailable) `email_unavailable`; reset still answers the
      generic 200 (OK); password change still commits
- [x] 2.5 GREEN: `email_unavailable` in `filmai/errores/catalogo.py`
      (`{"registro": 503, "reenvio": 503}`), the `APIException` subclass,
      `transaction.atomic()` in `RegisterView.perform_create`, the catch of
      `EnvioFallido` for resend (wrapper in `filmai/urls.py` or adapter;
      check `contracts/openapi.yaml` does not change shape)
- [x] 2.6 Contract tests: `test_cobertura_codigos`, `test_contrato_codigos`,
      `test_metadatos_errores`; regenerate `contracts/` only if a test asks
      for it
- [x] 2.7 Copy: `email_unavailable` in `traducciones/claves.csv` (en/es,
      approved by the user), generated catalogs, `npm run i18n:check`
- [x] 2.8 Frontend: registration and resend show the translated message for
      `email_unavailable` (by code, never `detail`); Vitest for both
- [x] 2.9 `ruff format . && ruff check .`; `npx prettier --check .`; full
      backend suite; `npm run test:unit -- --maxWorkers=4`

## Phase 3: Documentation (last PR of the chain)

- [x] 3.1 `docs/decisiones.md`: entry «Brevo como respaldo de Resend» with
      D-1 to D-6 as answered, the error table, capacity and affected files
- [x] 3.2 Canonical spec `openspec/specs/emails/spec.md`: merge the delta of
      `specs/emails/spec.md`
- [x] 3.3 `docs/05_Plan_de_Desarrollo.md` and `README.md`: where they say the
      email goes through Resend, add the fallback and the new variables
- [x] 3.4 `graphify update .` and commit `graphify-out/` with the docs
- [x] 3.5 Keep `openspec/changes/brevo-respaldo/` until phase 4 is done: the
      coordinator archives (deletes) it at the end, after the manual check

## Phase 4: Brevo account and manual check

- [ ] 4.1 Brevo account: create an API v3 key; verify the single sender of
      `BREVO_FROM_EMAIL`; check «Authorised IPs» (Settings → Security) and
      either allow the development/production IP or disable the restriction,
      or every call answers 401 (Unauthorized)
- [x] 4.2 SPF/DKIM: without an own domain only the single sender applies.
      Note in `docs/decisiones.md` that a Gmail sender may fail DMARC through
      Brevo, and that the domain setup is part of the deploy
- [ ] 4.3 Manual end-to-end in Docker (`-p filmai`, `RUN_MIGRATIONS=false`
      from a worktree), with `EMAIL_BACKEND=filmai.email_backends.RespaldoBackend`: 1. Valid Resend key: registration, resend and reset arrive; the log says
      «vía Resend» and Brevo is not called 2. `RESEND_API_KEY=re_invalida`, restart backend: the same three arrive;
      the log shows the WARNING with 401/403 and «vía Brevo» 3. Invalid keys in both: registration answers 503
      (Service Unavailable) with the translated message and leaves no
      account; reset answers the generic 200 (OK) 4. Check the received email: HTML renders, plain text present, «Sent
      with Brevo» footer present or not, spam folder or inbox
- [ ] 4.4 Record the result of 4.3 in `docs/decisiones.md`

## Phase 5: Q-08, account emails by Celery (same PR #244)

- [x] 5.1 `filmai/tasks.py`: task `filmai.enviar_correo` (strings only, no DB
      reads), retries `EnvioFallido` with backoff 60 s, cap 1800 s, jitter and
      8 retries; no retry for non-transient `ErrorDeProveedor`; ERROR log when
      it fails for good; `acks_late` and `ignore_result`
- [x] 5.2 `enviar_correo()` renders and enqueues with redacted `argsrepr` and
      `retry=False`; `CorreoNoEncolado` when the broker does not answer;
      `CELERY_BROKER_TRANSPORT_OPTIONS` so enqueueing fails in ~2 s
- [x] 5.3 `email_unavailable` now means «could not enqueue»; adapter translates
      `CorreoNoEncolado`; reset keeps the generic 200 (OK) and logs the pk; the
      password notice logs the pk
- [x] 5.4 `devolver_cupo` in `usuarios/throttles.py`, called by the exception
      handler on `email_unavailable`; rates unchanged
- [x] 5.5 Tests: enqueue and redaction, task success/retry/no retry/logs,
      real publish against a closed port, queue down in the four flows,
      registration without waiting for the provider, quota refund
- [x] 5.6 `send_test_email` stays synchronous (it calls `send_mail` directly)
- [x] 5.7 Docs: `docs/decisiones.md`, `docs/05_Plan_de_Desarrollo.md`,
      `README.md` and the canonical spec `openspec/specs/emails/spec.md`
- [ ] 5.8 Manual check with real accounts (the user): with the worker stopped
      the registration answers 201 (Created) and the email arrives when the
      worker starts again
