# Delta for emails

## ADDED Requirements

### Requirement: Brevo fallback behind one email backend

`filmai.email_backends.RespaldoBackend` MUST try Resend first and, for each
message Resend could not take because of a transient failure, MUST send that
same message through Brevo's transactional API. Transient failures are
connection and TLS errors, timeouts, 5xx, 429 (Too Many Requests), 402
(Payment Required), 401 (Unauthorized) and 403 (Forbidden). A 400 (Bad
Request) or 422 (Unprocessable Entity) for invalid message data MUST NOT fall
back. A message Resend accepted (2xx) MUST NOT be sent through Brevo. Each
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
- AND a WARNING names Resend, 429 and the error type
- AND an INFO line names Brevo and its `messageId`

#### Scenario: Invalid Resend key

- GIVEN Resend raises `InvalidApiKeyError`
- WHEN any account email is sent
- THEN it is sent through Brevo

#### Scenario: Invalid message data

- GIVEN Resend raises `ValidationError` (422)
- WHEN the message is sent
- THEN Brevo is not called
- AND the error is raised, or 0 is returned with `fail_silently=True`

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
`BREVO_TEST_RECIPIENT` is set, or when `BREVO_FROM_EMAIL` is empty while
`DEFAULT_FROM_EMAIL` is a `@resend.dev` address. With `BrevoBackend` it MUST
fail without `BREVO_API_KEY` or with `BREVO_TEST_RECIPIENT`. The rules for
`ResendBackend` alone stay as they are.

#### Scenario: Missing Brevo key in production

- GIVEN `DEBUG=False`, `EMAIL_BACKEND=filmai.email_backends.RespaldoBackend` and no `BREVO_API_KEY`
- WHEN settings load
- THEN `ImproperlyConfigured` is raised

## MODIFIED Requirements

### Requirement: Preserve delivery and account security behavior

OT-50 extracts sending/layout structure before text changes. OT-51 supplies
expiry context and notification HTML, OT-52 adds English and recipient language,
and OT-53 switches Spanish to the reviewed table's voseo.
Do not silently route these synchronous account emails through Celery.
Unknown/inactive reset recipients MUST keep the generic success response
without mail, avoiding disclosure, also when no provider could send. Password-update notification MUST run only
after the password transaction commits; delivery failure MUST not roll back
that committed change. Existing reset-token consumption and session revocation
remain unchanged. Resend does not create a new email-change account flow.
When every provider fails, registration MUST answer 503 (Service Unavailable)
with code `email_unavailable` and MUST NOT leave the new account or its email
address stored; resending the confirmation MUST answer 503 (Service
Unavailable) with the same code. The frontend MUST show the translated message
for that code.

#### Scenario: Password transaction rolls back

- WHEN a password update does not commit
- THEN no password-updated notification is sent
- WHEN the password commits and sending fails
- THEN the password stays changed and the existing failure is logged

#### Scenario: No provider can send a registration email

- GIVEN Resend and Brevo both fail
- WHEN a visitor registers
- THEN the answer is 503 (Service Unavailable) with `code=email_unavailable`
- AND no account and no email address exist for that email
- AND a later registration with the same email succeeds once a provider recovers

#### Scenario: No provider can send a reset email

- GIVEN Resend and Brevo both fail
- WHEN a password reset is requested for an active account
- THEN the answer is the same generic 200 (OK) as for an unknown email
