# Internationalization core capability

## Draft status and scope

OT-13 draft, pending approval of `docs/i18n/copia-propuesta.csv` and the six
curation questions. OT-11 and OT-12 are working references under review;
this document does not certify them as approved or describe implemented code.
The accepted technical decisions are recorded in OT-10 and plan sections 3–4.

```text
Browser cookie + Accept-Language → Next.js request locale → en/es catalogs
          ▲                                      │ HTTP Accept-Language
          │ cookie mirrors authenticated account ▼
          └──────── Preferences response ← Django idioma_efectivo(request, user)
                                                   │
                                      recipient email / TMDB language
```

## Requirements

### Requirement: Supported locales and backend resolution

The supported application locales MUST be `en` and `es`; the fallback MUST be
`en`. `Usuario.idioma` MUST accept these values or null, without a migration
backfill. `LANGUAGE_CODE` remains `es-ar`; error responses use codes, not
backend localization. JWT authentication occurs after Django middleware, so
`idioma_efectivo(request, usuario=None)` MUST resolve locale explicitly.

#### Scenario: Resolve effective backend language

- GIVEN an authenticated user with a supported saved locale
- THEN that locale wins over the request's `Accept-Language`
- GIVEN a null saved locale or no authenticated user
- THEN parse the header using Django's language parser and quality weights
- AND use the first supported preference, or `en` for absent/invalid/unsupported input
- AND regional language preferences resolve to a supported base when applicable

#### Scenario: Persist a new account's locale

- WHEN registration or Google signup creates an account
- THEN save the request locale on that account
- AND preference responses and user serializers expose `idioma`
- AND unsupported preference values return a coded validation error
- AND the development seed documents at least one known account per locale

### Requirement: Frontend locale and synchronization

next-intl MUST run without locale URL prefixes. `frontend/i18n/request.ts`
MUST resolve the render locale from supported `filmai_locale`, then
`Accept-Language`, then `en`. The account is the source of truth for signed-in
users; its cookie mirror determines the render. The root layout MUST set
`html.lang` and localized metadata from that resolved locale.
`apiFetch` MUST send one supported `Accept-Language` value for every request.

#### Scenario: Change locale without a session

- WHEN the visitor selects a supported language
- THEN update `filmai_locale` and refresh the rendered messages
- AND do not require an account

#### Scenario: Change locale with a session

- WHEN the user selects a supported language
- THEN persist it through `PUT /api/preferences/`
- AND on success update the cookie and refresh the render
- AND on failure keep the saved account preference and report a localized error

#### Scenario: Sign in with a different saved locale

- GIVEN the account locale differs from the render cookie
- WHEN login exposes that saved locale
- THEN replace the cookie with the account locale and refresh
- AND a null account locale leaves request/header resolution available until selection

### Requirement: Complete messages and parity

`frontend/messages/{en,es}` MUST contain equal key sets and compatible ICU
argument/tag sets. Keys identify function in English/camelCase, with no dots
inside a segment. Messages MUST be complete phrases; counts use ICU plurals
and inline links use `t.rich`. User names, custom lists, reviews and production
titles MUST NOT become fixed messages. `legal` MUST load only on the terms page;
`emails` is a backend template reference and MUST NOT enter the client provider.
The original equivalence JSON MUST remain immutable. OT-77 seeds only reviewed
usable rows from the curated CSV, plus explicitly approved missing copy.
Unresolved or excluded rows MUST NOT be silently seeded.

#### Scenario: Missing translation or parameter

- WHEN an English/Spanish key or a required ICU argument/tag is removed
- THEN parity checks fail
- AND every public exported code has an English and Spanish translation

### Requirement: Resolve API errors by registered code

Lookup MUST use `errors.fields.<field>.<code>`, then `errors.codes.<code>`,
then `errors.codes.unknown`. Field-specific copy MUST be approved together
with generic copy. Neither legacy response prose nor `.debug` may supply UI
text. Machine enum values and request fields retain their existing spelling.
Optional machine metadata MUST NOT become a mandatory ICU argument.
Known `retry_after_seconds` maps centrally to `retryAfterSeconds`; absence
selects the generic throttling message rather than inventing a wait.

#### Scenario: Unsupported response code

- GIVEN a network failure or a code absent from the frontend catalog
- THEN show the localized unknown fallback
- AND do not expose backend diagnostics or an internal field name

### Requirement: Locale-aware formatting and labels

`frontend/i18n/config.ts` MUST map `en` to `en-US` and `es` to `es-AR` for Intl,
and `frontend/lib/format.ts` MUST provide the shared format functions.
Short and long dates use `dateStyle: medium/long`; decimals use one decimal;
integers use default grouping. Duration uses NumberFormat unit formatting
with `narrow` in English and `short` in Spanish, joining hours/minutes with
one space. TMDB uses a separate `en-US`/`es-MX` map, with English fallback.
Labels for default lists and personal gender MUST resolve from stable enums.

#### Scenario: Format a display value

- WHEN dates, counts, ratings or durations are displayed
- THEN use the active locale and central formatting helpers
- AND tests compare with Intl output from their environment
- AND formatting overrides MUST NOT be scattered across components

### Requirement: Routes and bounded migration

Visible routes MUST become `/profile`, `/settings`, `/my-reviews`, `/lists`,
`/confirm-email/[key]`, `/reset-password/[uid]/[token]`, `/complete-signup`;
`/login` and `/register` stay unchanged. Shared route/protection lists MUST
come from `frontend/lib/routes.ts`. Backend links, frontend routes and the
phase-authorized tests MUST change together. No redirect is required by the
accepted development-only scope.

#### Scenario: Mixed interface during the agreed transition

- THEN fully migrate settings, email confirmation and password reset
- AND migrate shared API errors, validation, labels, formats, metadata and routes
- AND keep the other legacy screens in the explicit lint allowlist with Spanish tests
- AND remove each allowlist entry when its replacement UI is implemented
- AND do not translate chatbot copy or change account-deactivation copy/behavior

## Verification before final integration

Backend locale/registration/preferences/seed tests, frontend catalog/error
parity tests, Intl format tests and both-locale pilot e2e MUST pass in their
implementation phases. Lint, format, full suites and Next.js build remain
closure gates. This draft adds no production implementation or tests.
