# Localized account emails capability

## Approved scope and evidence

The user approved OT-13 editorial copy on 08/10/2026. Plan 2.8/3.6/F5 and OT-02 golden
references establish four real flows. Curated rows 603–634 supply the proposed
copy; no email-address-change endpoint is introduced by the confirmation design.

```text
Registration / allauth resend / password reset / committed password change
                              │ in-process call
                              ▼
           enviar_correo(case, recipient, context, language)
                              │ Django templates + shared HTML layout
                              │ renders in the request, then enqueues
                              ▼
            Celery task `filmai.enviar_correo` (Redis broker)
                              │ worker, retries with backoff
                              ▼
                    configured Django email backend
                    (RespaldoBackend: Resend first, Brevo for
                     the message Resend could not take)
```

## Requirements

### Requirement: Four cases, two languages, three parts

A single `enviar_correo(caso, destinatario, contexto, idioma)` service MUST
support registration confirmation, confirmation resend, password reset and
password-updated notification. Each case in `en` and `es` MUST have subject,
plain text and HTML, including password-updated, which currently has no HTML.
Subjects MUST contain the FilmAI prefix and no newline. HTML MUST share
`templates/correos/base.html` and set its language from the selected locale.
Plain text MUST remain understandable without styling or an HTML button.
Greetings MUST preserve the recipient's full name and use a localized fallback
when both name fields are empty; the current Spanish fallback MUST NOT leak
into English emails. Rendering checks MUST cover recipients without a name.

| Case                | Template directory               | Copy reference                   |
| ------------------- | -------------------------------- | -------------------------------- |
| Registration        | `confirmacion_registro/{en,es}`  | rows 603–613                     |
| Resend confirmation | `confirmacion_correo/{en,es}`    | rows 615–619 plus shared subject |
| Reset password      | `restablecer_contrasena/{en,es}` | rows 621–627                     |
| Password updated    | `contrasena_actualizada/{en,es}` | rows 629–634                     |

Resend preserves the registration subject unless separate copy is explicitly
approved. Allauth's adapter MUST delegate to the service; neither it nor the
password serializers MUST duplicate sending/layout rules.

#### Scenario: Render every supported variant

- GIVEN each of the four cases and each supported locale
- THEN subject, nonempty plain text and nonempty HTML exist
- AND HTML lang and all static copy match that locale
- AND rendered bodies contain no unresolved template/ICU placeholders
- AND URLs occur as actionable links in HTML and readable links in text

### Requirement: Recipient language wins

The service MUST use the recipient's supported saved locale, then the request
locale when the saved value is null, then English. Registration saves its locale
before sending. Language selection MUST not depend on a process-global locale.
The caller provides the effective locale; the service renders one complete
variant explicitly, allowing simultaneous sends in different languages.

#### Scenario: Recipient differs from request

- GIVEN a recipient saved as `es` and a request preferring `en`
- WHEN an account email is sent
- THEN its subject, text and HTML use Spanish
- GIVEN a null saved locale and a supported request locale
- THEN use that request locale; without either, use English

### Requirement: Configuration supplies link validity

The existing confirmation validity MUST remain 24 hours and password-reset
validity MUST remain 1 hour. Derive `expiryHours` from the applicable Django/
allauth settings; do not hardcode the duration into body templates.
The curated ICU wording describes singular/plural copy; Django templates MUST
render the same wording using context and template logic, without assuming
that Django interprets ICU syntax or adding a frontend i18n runtime to emails.

#### Scenario: Reset and confirmation copy track settings

- GIVEN confirmation expires after one day and reset after 3600 seconds
- THEN confirmation bodies describe 24 hours and reset bodies describe 1 hour
- WHEN the setting is changed in a focused test
- THEN the matching template renders the new supplied duration correctly

### Requirement: Shared routes remain coordinated

Confirmation links MUST use `FRONTEND_URL/confirm-email/<key>/` and reset links
MUST use `FRONTEND_URL/reset-password/<uid>/<token>/` after OT-75's coordinated
route migration. OT-75 migrates frontend routes, backend URLs, tests and golden mail references together.
The password-updated recovery action MUST lead to the actual login/recovery
flow; no new recovery endpoint or reusable reset token is invented.

#### Scenario: A localized email lands in a localized pilot page

- WHEN a link is opened after coordinated route migration
- THEN the matching frontend route exists
- AND the confirmation/reset pilot supports both application locales
- AND locale resolution still follows the i18n-core cookie/account rules

### Requirement: Brevo fallback behind one email backend

`filmai.email_backends.RespaldoBackend` MUST try Resend first and, for each
message Resend could not take because of a transient failure, MUST send that
same message through Brevo's transactional API. Transient failures are
connection and TLS errors, timeouts, 5xx, 429 (Too Many Requests), 402
(Payment Required), 401 (Unauthorized) and 403 (Forbidden). A 400 (Bad
Request) or 422 (Unprocessable Entity) for invalid message data from the first
provider MUST NOT fall back. Once a transient failure has happened, any error
from the fallback provider (for example a 400 (Bad Request) from Brevo for an
unverified sender) MUST count as a failure of both providers (`EnvioFallido`). A message Resend accepted (2xx) MUST NOT be sent through Brevo. Each
message MUST be tried once per provider. Callers (`enviar_correo()`, allauth's
adapter, the password flows) MUST NOT know which provider sent.

#### Scenario: Resend accepts

- GIVEN Resend answers 200 (OK) with an id
- WHEN a registration confirmation is sent
- THEN Brevo is not called
- AND the log names Resend and the id

#### Scenario: Resend quota exhausted

- GIVEN Resend raises `RateLimitError` with `daily_quota_exceeded`
- WHEN a password-reset email is sent
- THEN the same subject, text, HTML and recipient are sent through Brevo
- AND a WARNING names Resend, 429 (Too Many Requests) and the error type
- AND an INFO line names Brevo and its `messageId`

#### Scenario: Invalid Resend key

- GIVEN Resend raises `InvalidApiKeyError`
- WHEN any account email is sent
- THEN it is sent through Brevo

#### Scenario: Invalid message data

- GIVEN Resend raises `ValidationError` (422 (Unprocessable Entity))
- WHEN the message is sent
- THEN Brevo is not called
- AND the error is raised, or 0 is returned with `fail_silently=True`

#### Scenario: Fallback rejects after a transient failure

- GIVEN Resend answers 503 (Service Unavailable) and Brevo 400 (Bad Request)
- WHEN a message is sent with `fail_silently=False`
- THEN `EnvioFallido` is raised, not `ErrorDeProveedor`

#### Scenario: Partial batch

- GIVEN two messages and Resend fails only on the second
- WHEN they are sent in one call
- THEN the first is sent once, by Resend, and the second by Brevo
- AND the backend returns 2

### Requirement: Brevo follows the same sending rules

The Brevo provider MUST keep `to`, `cc` and `bcc` as separate fields, MUST send
`htmlContent` and `textContent`, MUST send as `BREVO_FROM_EMAIL` when set and
otherwise as the message's sender, MUST redirect every recipient to
`BREVO_TEST_RECIPIENT` when set, and MUST NOT write email addresses to the
logs. Without `BREVO_API_KEY` the provider MUST be skipped.
`filmai.email_backends.BrevoBackend` MUST offer Brevo alone with the same
rules.

#### Scenario: Development redirect

- GIVEN `BREVO_TEST_RECIPIENT` is set and the message has one `to` and one `bcc`
- WHEN Brevo sends it
- THEN the only recipient is the test address
- AND the log reports 2 redirected recipients and no address

#### Scenario: Both providers fail

- GIVEN Resend answers 503 (Service Unavailable) and Brevo 402 (Payment Required)
- WHEN a message is sent with `fail_silently=False`
- THEN `EnvioFallido` is raised and an ERROR names both providers and statuses
- WHEN it is sent with `fail_silently=True`
- THEN 0 is returned and the same ERROR is logged

### Requirement: Production configuration of the fallback

With `DEBUG=False` and `RespaldoBackend`, start-up MUST fail when
`RESEND_API_KEY` or `BREVO_API_KEY` is missing, when `RESEND_TEST_RECIPIENT` or
`BREVO_TEST_RECIPIENT` is set, or when Brevo's effective sender (`BREVO_FROM_EMAIL`, or
`DEFAULT_FROM_EMAIL` when it is empty) has no `@` address or is a `@resend.dev`
address. With `BrevoBackend` it MUST fail without `BREVO_API_KEY`, with
`BREVO_TEST_RECIPIENT` or with that same invalid sender. The rules for
`ResendBackend` alone stay as they are.

#### Scenario: Missing Brevo key in production

- GIVEN `DEBUG=False`, `EMAIL_BACKEND=filmai.email_backends.RespaldoBackend` and no `BREVO_API_KEY`
- WHEN settings load
- THEN `ImproperlyConfigured` is raised

### Requirement: Preserve delivery and account security behavior

OT-50 extracts sending/layout structure before text changes. OT-51 supplies
expiry context and notification HTML, OT-52 adds English and recipient language,
and OT-53 switches Spanish to the reviewed table's voseo.
Unknown/inactive reset recipients MUST keep the generic success response
without mail, avoiding disclosure, also when the email could not be queued.
Password-update notification MUST be queued only
after the password transaction commits; a queueing failure MUST not roll back
that committed change. Existing reset-token consumption and session revocation
remain unchanged. Resend does not create a new email-change account flow.
When the email cannot be queued (the broker does not answer), registration MUST
answer 503 (Service Unavailable) with code `email_unavailable` and MUST NOT
leave the new account or its email address stored; resending the confirmation
MUST answer 503 (Service Unavailable) with the same code. The frontend MUST
show the translated message for that code. A provider that is down or out of
quota MUST NOT change the answer of any request: it is retried by the worker
(see «Account emails are sent by a Celery task»).

#### Scenario: Password transaction rolls back

- WHEN a password update does not commit
- THEN no password-updated notification is sent
- WHEN the password commits and sending fails
- THEN the password stays changed and the existing failure is logged

#### Scenario: The queue is down during registration

- GIVEN the broker does not answer
- WHEN a visitor registers
- THEN the answer is 503 (Service Unavailable) with `code=email_unavailable`
- AND no account and no email address exist for that email
- AND a later registration with the same email succeeds once the queue recovers

#### Scenario: The queue is down during a password reset

- GIVEN the broker does not answer
- WHEN a password reset is requested for an active account
- THEN the answer is the same generic 200 (OK) as for an unknown email
- AND an ERROR log names the user's primary key, not the email address

#### Scenario: Both providers are down during registration

- GIVEN Resend and Brevo both fail and the queue works
- WHEN a visitor registers
- THEN the answer is 201 (Created) and the account exists
- AND the worker retries the email (see below)

### Requirement: Account emails are sent by a Celery task

`enviar_correo()` MUST render subject, text and HTML inside the request and MUST
NOT call any provider: it MUST enqueue the task `filmai.enviar_correo` with
only serializable strings (case, subject, text, HTML, recipient). The task MUST
NOT read the database, so it can be enqueued inside the registration
transaction without racing its commit. Enqueueing MUST fail in a few seconds
when the broker does not answer, raising `CorreoNoEncolado`. The worker MUST
send through the configured `EMAIL_BACKEND` and MUST retry only
`EnvioFallido` (every provider failed transiently), with exponential backoff
(60 s base, 1800 s cap) and jitter, at most 8 retries (about 1 hour on average,
2 hours at most; always far below the 24-hour link validity). A non-transient
`ErrorDeProveedor` (400 (Bad Request) or 422 (Unprocessable Entity)) MUST NOT be
retried and MUST log an ERROR; so MUST exhausting the retries. No log, no task
`argsrepr` and no stored task result MAY contain recipient addresses or links.
`send_test_email` MUST keep sending synchronously, without the queue.

#### Scenario: Registration does not wait for the provider

- GIVEN the queue works and the providers are slow or failing
- WHEN a visitor registers
- THEN the answer is 201 (Created) and no provider was called inside the request

#### Scenario: Transient failure is retried

- GIVEN every provider fails transiently
- WHEN the task runs
- THEN it schedules a retry with a jittered backoff, up to 8 times
- AND after the last one an ERROR log names the case and the task id, not the address

#### Scenario: Invalid message data

- GIVEN Resend answers 422 (Unprocessable Entity)
- WHEN the task runs
- THEN it is not retried and an ERROR is logged

### Requirement: A failed enqueue does not spend the throttle quota

When registration or resend end in `email_unavailable`, that attempt MUST NOT
count toward the throttles of the view (`RegistroCorreoThrottle`,
`RegistroIPThrottle`, and the three resend throttles). The rates MUST NOT change.
An attempt that reaches the queue MUST count as before.

#### Scenario: Six registrations with the queue down

- GIVEN the broker does not answer and a limit of 5 per hour per email
- WHEN the same email registers six times in a row
- THEN every answer is 503 (Service Unavailable), none is 429 (Too Many Requests)

## Verification before closure

Use the in-memory email backend for rendering tests; do not send external
messages. Characterization references change only under the accepted F0
regeneration authorization. Test all eight variants, effective locale, expiry
context and URL routes. Review the rendered emails in a real client at OT-52
and OT-90 as required by the plan. OT-13 adds no sending code or tests.

## Implementation progress

Since Q-08 (22/11/2026) the sends are queued, see «Account emails are sent by a Celery task». OT-50 centralizes the four sends in `filmai.correos.servicio.enviar_correo`.
Spanish templates retain their previous copy and rendered whitespace. Three
HTML variants share `correos/base.html`; reset retains its separate title,
action, warning and secondary color. Password notification remains text-only
until OT-51. Registration/reset routes and transaction/failure policies stay
unchanged. The user authorized only retargeting the notification failure mock
to the service transport, preserving its assertions.

All four original F0 references remain identical without regeneration. Three
new tests verify formats, invalid internal inputs and transport failure. The
full local suite passes 523 tests; integration awaits rebase and exact-head CI.
Expiry context/notification HTML (OT-51), recipient language/English (OT-52)
and reviewed Spanish copy (OT-53) remain future requirements.

### Status after OT-51/52/53 (08/10/2026)

All eight variants (4 cases × `en`/`es`) render subject, text and HTML from
`correos/<case>/<locale>/`, sharing the neutral `correos/base.html` layout and
`correos/base_<locale>.html` copy. Callers pass `idioma_efectivo(request,
user)`. Expiry hours come from settings through `vigencia_en_horas`. The
password-updated action links to `FRONTEND_URL/login/`. The nameless greeting
fallback (`usuario` / `there`) was approved by the user on 08/10/2026. OT-75 switches links to the English routes. Rendering is verified in both
languages; review in a real mail client is still pending.


### OT-75/90 follow-up

Links MUST NOT force the recipient's language on the receiving browser: use
that device's cookie, then browser preference, then English (confirmed by the
user on 08/10/2026). The pilot routes support both locales. HTML previews and
EML files for all eight variants live under `traducciones/revision-correos/`; no
external mail was sent to create them. Do not equate browser rendering with
verification in Gmail/Outlook/another real email client.

### Visual design from the canvas (12/10/2026)

The shared `correos/base.html` follows the four email artboards of the design
canvas: dark card (no top accent bar since 06/11/2026, issue #175), ticket mark
(the navbar's `TicketMark`, served as `/correos/ticket.png` from `FRONTEND_URL`
since 21/11/2026, because mail clients do not render inline SVG)
and `FilmAI` wordmark, 40px
display title, primary yellow button (secondary outlined button for
password-updated), copyable link row and a divider before the warning and
signature. The reason and rights lines sit below the card. Colors are the
design tokens (`#0d0d14`, `#15151f`, `#262636`, `#a6a6b8`, `#84849a`,
`#f5c518`); the previous orange and the `color_secundario` context value are
removed. Copy, subjects and plain text are unchanged. HTML stays table-based with
inline styles and system-font fallbacks for mail clients that ignore web fonts.
