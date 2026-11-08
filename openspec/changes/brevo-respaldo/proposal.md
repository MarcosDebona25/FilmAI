# Proposal: Brevo as a fallback for Resend (issue #181)

## Intent

Every transactional email (registration confirmation, resend, password reset
and the password-updated notice) leaves through one Django backend,
`filmai.email_backends.ResendBackend`. If Resend is down, rejects our key or
the free quota runs out (100 per day, 3 000 per month), the email is simply
not sent:

- **Registration** raises inside `RegisterView.perform_create` after the user
  row exists: the visitor gets a 500 (Internal Server Error), the account stays
  `PENDIENTE` and a second attempt answers `email_already_used` until that
  pending account expires (`liberar_pendientes_vencidas`).
- **Resend confirmation** raises the same way: 500 (Internal Server Error).
- **Password reset** logs the error and answers the usual generic 200 (OK),
  so the user waits for an email that never arrives.
- **Password updated** logs the error; the password stays changed (by design).

A visitor who cannot confirm the account cannot use FilmAI at all. This change
adds Brevo's transactional API as an automatic second provider: Resend first,
Brevo only when Resend could not take the message.

## What is already decided

| Source                           | What it fixes                                                                                                                                                                                 |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/decisiones.md`, 24/08/2026 | One custom `EMAIL_BACKEND` carries all transactional mail; allauth and the views do not know the provider                                                                                     |
| `openspec/specs/emails`          | `enviar_correo()` is the single sending service; account emails stay synchronous (no Celery); reset keeps the generic answer; the password-updated notice never rolls back the password       |
| `email_backends.py`              | `to`/`cc`/`bcc` stay separate, HTML + plain text, no addresses in logs, `RESEND_TEST_RECIPIENT` redirect in development                                                                       |
| `email_validation.py`            | In production a missing key or a test recipient breaks start-up                                                                                                                               |
| Issue #181                       | Network errors, 5xx and 429 (Too Many Requests) fall back; a 422 (Unprocessable Entity) for invalid data does not; never send twice; log which provider sent each email; keep `fail_silently` |

## Decisions that need the user (rule 3 of `AGENTS.md`)

The plan below follows the **recommended** option of each. Nothing is
implemented until they are confirmed; `design.md` has the reasoning.

| #   | Question                                                                             | Recommendation                                                                                                                                                                                                                                               | Alternative                                                                                                 |
| --- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| D-1 | Does a 401/403 from Resend (missing or invalid key) fall back?                       | **Yes.** It is a provider-side failure, not bad message data, and the acceptance test of the issue forces Resend to fail with an invalid key                                                                                                                 | Only network/5xx/429, as the issue lists literally (then the manual test needs another way to break Resend) |
| D-2 | A read timeout from Resend is ambiguous (it may have accepted the email). Fall back? | **Yes.** A duplicated confirmation is harmless; a missing one blocks the account                                                                                                                                                                             | No fallback on read timeout (never duplicates, but loses the email)                                         |
| D-3 | Throttles with the combined capacity (~400/day)                                      | **Keep the current per-email/per-IP rates** and rewrite the comment: they limit abuse and domain reputation, not the global quota. No global cap, because one client could exhaust it and block every sign-up                                                | Add a global daily scope (e.g. `correo_global: 350/day`) shared by registration, resend and reset           |
| D-4 | Both providers fail during registration or resend                                    | **New code `email_unavailable`, 503 (Service Unavailable)**, translated in the frontend. Registration runs inside `transaction.atomic()` so the account is not created and the visitor can simply retry. Reset keeps the generic 200 (OK) (anti-enumeration) | Keep the account and answer 201 (Created) telling the user to use «resend» later                            |
| D-5 | Brevo's own sender and test recipient                                                | **`BREVO_FROM_EMAIL`** (Brevo cannot send as `onboarding@resend.dev`) and **`BREVO_TEST_RECIPIENT`** (own variable, same address in `.env.example`)                                                                                                          | Reuse `RESEND_TEST_RECIPIENT` for both providers                                                            |
| D-6 | Client for Brevo                                                                     | **`httpx`** (already in `requirements.txt`): one POST, no new dependency, `MockTransport` in tests as in `semantica.py`                                                                                                                                      | Official SDK `brevo-python` or `django-anymail`                                                             |

## Scope

### In Scope

- **`BrevoBackend`** in `filmai/email_backends.py`: `POST
https://api.brevo.com/v3/smtp/email` with `httpx`, same rules as Resend
  (separate `to`/`cc`/`bcc`, HTML + text, test redirect, no addresses in logs,
  no key → log and return 0).
- **Shared provider seam**: each provider sends one message and raises
  `ErrorDeProveedor(transitorio=...)`; `ResendBackend` is refactored on top of
  it without changing its behaviour or its tests.
- **`RespaldoBackend`** (`filmai.email_backends.RespaldoBackend`): Resend, then
  Brevo per message; only transient errors fall back; logs say which provider
  sent; both failing respects `fail_silently`.
- **Configuration**: `BREVO_API_KEY`, `BREVO_FROM_EMAIL`, `BREVO_TEST_RECIPIENT`
  in `settings.py` and `.env.example`; `validar_configuracion_email` extended;
  `send_test_email` shows the active chain.
- **Limits**: throttle comment and tests per D-3; `email_unavailable` per D-4
  (catalog, contract, `traducciones/`, frontend message for registration and
  resend).
- **Docs**: `docs/decisiones.md`, canonical spec `emails`, doc 05 and README
  where they say "Resend", `graphify update .`.

### Out of Scope

- **Sending through Celery** (Q-08). The emails spec forbids moving account
  emails to a queue silently; it stays a separate task.
- **Own domain, SPF/DKIM for a domain.** There is none yet. Brevo uses a
  verified single sender; the domain setup is a deploy task.
- **Retries on the same provider** or circuit breakers. One attempt per
  provider keeps a synchronous request bounded.
- **Brevo webhooks, bounces, delivery tracking.**
- **A third provider.** The chain is a list, so adding one later is one entry.

## Risks and rollback

| Risk                                                                                        | Mitigation                                                                                                | Rollback                                                      |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| A slow Resend plus Brevo makes registration hang                                            | Explicit timeouts (Brevo 10 s; Resend's SDK timeout verified and set, task 1.2); one attempt per provider | `EMAIL_BACKEND=filmai.email_backends.ResendBackend` in `.env` |
| Same email sent twice                                                                       | Fallback only on an exception from Resend; a 2xx is final. Ambiguous read timeout accepted per D-2        | —                                                             |
| Brevo blocks calls from unknown IPs ("Authorised IPs") or the single sender is not verified | Manual setup steps in task 4.1; the error is logged with Brevo's status and code                          | Remove `BREVO_API_KEY` / switch `EMAIL_BACKEND`               |
| Gmail-hosted sender fails DMARC through Brevo and lands in spam                             | Checked in the manual test (4.3); noted as a reason for an own domain                                     | Same as above                                                 |
| Brevo's free plan adds a "Sent with Brevo" footer                                           | Checked in the manual test; acceptable for a fallback                                                     | —                                                             |
| Registration in `transaction.atomic()` (D-4) changes when the user row commits              | Test: both providers fail → no `Usuario`, no `EmailAddress`; success path unchanged                       | Revert the view to its current body                           |

Each PR in `tasks.md` names its own rollback boundary.
