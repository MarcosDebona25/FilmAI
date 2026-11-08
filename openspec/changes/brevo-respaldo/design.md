# Design: Brevo as a fallback for Resend (issue #181)

## Where this lives

```
RegisterView / ResendEmailVerificationView / RecuperarContrasenaView / guardar_contrasena
        │  (unchanged callers)
        ▼
filmai/correos/servicio.py :: enviar_correo()  ── django.core.mail.send_mail ──▶ settings.EMAIL_BACKEND
                                                                                   │
                         filmai.email_backends.RespaldoBackend  ◀──────────────────┘
                           │  per message, in order
                           ├─▶ ProveedorResend  ── resend SDK ──HTTPS──▶ api.resend.com
                           │      raises ErrorDeProveedor(transitorio=True|False)
                           └─▶ ProveedorBrevo   ── httpx ──────HTTPS──▶ api.brevo.com/v3/smtp/email
```

Nothing above `EMAIL_BACKEND` changes, except the registration view for D-4.
That is the point of the 24/08/2026 decision: the provider is a setting.

## Providers and backends

`filmai/email_backends.py` gets one small seam:

```python
class ErrorDeProveedor(Exception):
    def __init__(self, proveedor, *, transitorio, estado=None, codigo=None): ...

class Proveedor(Protocol):
    nombre: str                     # "Resend", "Brevo": used in logs
    def configurado(self) -> bool   # has its key
    def enviar(self, message) -> str  # returns the provider's message id
```

- `ProveedorResend.enviar` is today's `_send_one`, moved: it applies
  `RESEND_TEST_RECIPIENT`, builds the params and calls `resend.Emails.send`.
  It translates SDK errors into `ErrorDeProveedor` (table below).
- `ProveedorBrevo.enviar` builds Brevo's payload and POSTs it with
  `httpx.Client(timeout=10)`. It applies `BREVO_TEST_RECIPIENT` and
  `BREVO_FROM_EMAIL`.
- `ResendBackend`, `BrevoBackend` and `RespaldoBackend` are thin
  `BaseEmailBackend`s over a list of providers: `[Resend]`, `[Brevo]`,
  `[Resend, Brevo]`. One loop implements all three, so the single-provider
  backends keep exactly today's behaviour (no key → error log, return 0;
  failure → raise unless `fail_silently`).

Shared helpers, so the two providers cannot drift: `_destinatarios(message,
test_recipient)` (redirect and promotion of `cc`/`bcc` to `to` when `to` is
empty, same as Resend today) and `_extraer_html(message)`.

### Brevo payload

| Django `EmailMessage`                                                        | Brevo field                                                         |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `BREVO_FROM_EMAIL` or else `from_email`, parsed with `email.utils.parseaddr` | `sender: {"name", "email"}`                                         |
| `to` / `cc` / `bcc`                                                          | `to` / `cc` / `bcc`: lists of `{"email": ...}`; empty lists omitted |
| `subject`                                                                    | `subject`                                                           |
| `alternatives` `text/html`                                                   | `htmlContent`                                                       |
| `body`                                                                       | `textContent`                                                       |

Brevo requires `htmlContent` when there is no template. Every account email
has HTML, but a plain-text-only message (`send_test_email`, admin mail) would
be rejected: in that case `htmlContent` is the text escaped and wrapped in
`<pre>`. A test pins it.

Header `api-key: BREVO_API_KEY`, `accept: application/json`. Success is 201
(Created) with `{"messageId": ...}`.

## Which errors fall back

Fallback happens **only when the first provider raised**. A 2xx is final, so
an accepted email is never sent again.

| Failure                                                                                     | Resend                                                                                     | Brevo                    | Falls back?                                           |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------ | ----------------------------------------------------- |
| Connection error, DNS, TLS                                                                  | transport exception of the SDK's HTTP client (`requests`; verify in task 1.2)              | `httpx.TransportError`   | Yes                                                   |
| Read timeout (request sent, no answer)                                                      | same                                                                                       | `httpx.TimeoutException` | Yes — **D-2**                                         |
| 5xx                                                                                         | `ApplicationError` / `ResendError` with `code >= 500`                                      | status ≥ 500             | Yes                                                   |
| 429 (Too Many Requests): rate limit, daily or monthly quota                                 | `RateLimitError` (`rate_limit_exceeded`, `daily_quota_exceeded`, `monthly_quota_exceeded`) | 429                      | Yes                                                   |
| 402 (Payment Required): out of credits                                                      | —                                                                                          | 402                      | Yes                                                   |
| 401 (Unauthorized) / 403 (Forbidden): missing or invalid key, unknown IP, unverified sender | `MissingApiKeyError`, `InvalidApiKeyError`                                                 | 401 / 403                | Yes — **D-1**                                         |
| 400 (Bad Request) / 422 (Unprocessable Entity): invalid message data                        | `ValidationError`, `MissingRequiredFieldsError`                                            | 400                      | **No**: the same data would fail again; raise at once |
| Missing key in settings                                                                     | provider not `configurado()`                                                               | same                     | Skipped, next provider                                |
| Unknown exception                                                                           | anything else                                                                              | anything else            | No (treated as a bug, raised)                         |

**Why D-1 says yes.** An invalid or revoked key is exactly the "provider is
unusable" case the fallback is for, and the issue's manual acceptance test
forces Resend to fail with an invalid key. The risk (a misconfigured Resend
key going unnoticed because Brevo covers it) is handled by logging every
fallback at `WARNING` with the reason.

**Why D-2 says yes.** Resend may have accepted a message whose answer timed
out. Sending it again through Brevo can duplicate a confirmation or reset
email; both links stay valid and the user loses nothing. Not sending it blocks
the account. Resend's `Idempotency-Key` does not help here: it only
deduplicates retries **to Resend**.

## Sequence

```mermaid
sequenceDiagram
    participant S as enviar_correo()
    participant B as RespaldoBackend
    participant R as Resend
    participant V as Brevo

    S->>B: send_messages([msg])
    B->>R: Emails.send(params)
    alt 2xx
        R-->>B: {id}
        B->>B: log INFO "enviado vía Resend id=…"
    else transient (network, timeout, 5xx, 429, 401/403)
        R-->>B: error
        B->>B: log WARNING "Resend falló (429 daily_quota_exceeded); se intenta con Brevo"
        B->>V: POST /v3/smtp/email
        alt 201
            V-->>B: {messageId}
            B->>B: log INFO "enviado vía Brevo id=…"
        else any error
            V-->>B: error
            B->>B: log ERROR "ningún proveedor pudo enviar (Resend: 429, Brevo: 402)"
            B-->>S: raise EnvioFallido (or return 0 if fail_silently)
        end
    else 400/422 (invalid data)
        R-->>B: ValidationError
        B-->>S: raise (or 0 if fail_silently) — Brevo is not tried
    end
```

When both fail, `RespaldoBackend` raises `EnvioFallido`, chained (`from`) to
the last provider error and carrying each provider's name and status for the
log. Callers already catch `Exception`, so nothing else changes for reset and
the password notice.

## Logs

Logger `filmai.email_backends` (already routed to the console at `INFO`).
Each line names the provider and never an address:

- `INFO  Email enviado vía Brevo: id=<…> subject='…'`
- `WARNING  Resend no pudo enviar (estado=429 codigo=daily_quota_exceeded); se reintenta con Brevo`
- `ERROR  Ningún proveedor pudo enviar el email (Resend: 503, Brevo: 402)`
- `INFO  BREVO_TEST_RECIPIENT activo: 1 destinatario(s) redirigidos`

The subject is logged as today (it carries no personal data; the greeting is
in the body).

## Configuration

| Variable               | Use                                                                                                                  | Production                                                                            |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `EMAIL_BACKEND`        | `filmai.email_backends.RespaldoBackend` turns the fallback on. `ResendBackend` and `BrevoBackend` keep working alone | as today                                                                              |
| `BREVO_API_KEY`        | Brevo API v3 key                                                                                                     | required with `RespaldoBackend` or `BrevoBackend`                                     |
| `BREVO_FROM_EMAIL`     | Verified Brevo sender, e.g. `FilmAI <cuenta@…>` (**D-5**). Empty → `from_email` of the message                       | required with `RespaldoBackend` while `DEFAULT_FROM_EMAIL` is `onboarding@resend.dev` |
| `BREVO_TEST_RECIPIENT` | Development only: redirect every Brevo send                                                                          | rejected                                                                              |

`validar_configuracion_email` gets the new values as keyword arguments and,
with `debug=False`:

- `ResendBackend`: unchanged.
- `BrevoBackend`: requires `BREVO_API_KEY`; rejects `BREVO_TEST_RECIPIENT`.
- `RespaldoBackend`: requires both keys; rejects both test recipients;
  rejects an empty `BREVO_FROM_EMAIL` when `DEFAULT_FROM_EMAIL` ends in
  `@resend.dev` (Brevo cannot send as Resend's sandbox address).

Development keeps no requirement: the console backend still works without any
key, and `RespaldoBackend` without Brevo's key just behaves as Resend alone.

## Limits

### Capacity (free plans, November 2026; re-check before deploying)

| Provider     |  Per day |         Per month |
| ------------ | -------: | ----------------: |
| Resend       |      100 |             3 000 |
| Brevo        |      300 | ~9 000 (300 × 30) |
| **Combined** | **~400** |       **~12 000** |

Resend's monthly cap binds first in a steady month; Brevo then carries up to
300 a day.

### Throttles (D-3)

The current scopes count **per recipient email and per IP**: they stop one
person or one machine from spamming an inbox and burning the sender's
reputation. They do not bound the global quota, and raising them because the
quota grew would only allow more abuse per person. Recommendation: keep the
values and rewrite the comment in `settings.py` so it states what each scope
protects and the combined capacity.

A global daily scope (the alternative) would protect the quota, but any client
could exhaust it on purpose and block every sign-up for the day. With ~400 a
day for a course project, the provider failing is the more honest limit, and
D-4 makes that failure visible.

Tests pin the rates of the seven scopes and that each view uses its scopes, so
a change to a rate is a conscious one.

### When both providers fail (D-4)

| Flow                | Today                          | After                                                                                                                                                                   |
| ------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Registration        | 500, account left `PENDIENTE`  | 503 (Service Unavailable) `email_unavailable`; `perform_create` runs in `transaction.atomic()`, so no `Usuario` and no `EmailAddress` remain; the visitor retries later |
| Resend confirmation | 500                            | 503 (Service Unavailable) `email_unavailable`                                                                                                                           |
| Password reset      | generic 200 (OK), error logged | unchanged (anti-enumeration, emails spec)                                                                                                                               |
| Password updated    | error logged, password kept    | unchanged                                                                                                                                                               |

The view catches `EnvioFallido` only (not every `Exception`) and raises a DRF
`APIException` subclass with status 503 and code `email_unavailable`, so the
envelope comes from `filmai_exception_handler` like every other code. The
frontend translates `email_unavailable` from `traducciones/claves.csv` and
never reads `detail`. Registration and resend live in different views: the
resend view is dj-rest-auth's, wrapped with `as_view(...)` in `filmai/urls.py`
to keep the OpenAPI contract; the catch goes in a small wrapper there or in the
adapter's `send_mail`, decided at implementation against
`contracts/openapi.yaml`.

## Testing approach

All unit, no network, no Docker.

- Resend: `mock.patch("resend.Emails.send")` as in `filmai/tests.py`, with
  side effects built from the SDK's own exception classes.
- Brevo: `httpx.MockTransport` injected into the provider (same technique as
  `catalogo/tests_semantica.py`); asserts on the JSON body and headers.
- Backends: `override_settings` for keys and test recipients.
- Registration/resend: `RespaldoBackend` with both providers patched to fail;
  assert 503, code and that no user exists.
- The manual end-to-end check in Docker (task 4.3) is the only real send.

## Architecture decisions

| Decision                                                    | Rationale                                                                                                                                |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Fallback inside the email backend, not in `enviar_correo()` | Keeps the 24/08/2026 rule: one `EMAIL_BACKEND`, callers unaware. Also covers mail not sent by the service (admin, `send_test_email`)     |
| Per-message fallback, not per batch                         | A batch where Resend fails halfway must not resend the messages it already accepted                                                      |
| `httpx` for Brevo (D-6)                                     | One endpoint; already a dependency with a test transport used elsewhere; anymail would replace the Resend SDK too, which is out of scope |
| One attempt per provider                                    | The request is synchronous (registration waits for it); retries belong to a Celery move (Q-08)                                           |
| `RespaldoBackend` as an explicit `EMAIL_BACKEND` value      | Turning the fallback on is visible in `.env` and in the start-up validation; no hidden flag                                              |
