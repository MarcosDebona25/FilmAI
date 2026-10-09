# Internationalization core capability

## Approved scope

The user approved OT-13's 91 new bilingual messages and six curation decisions
on 08/10/2026. OT-11 and OT-12 are integrated into `feat/i18n-multiidioma`.
OT-71–83 implement the shared layers and the three approved pilot screens on
`develop`. Other visible screens retain their documented Spanish exceptions.

```text
Browser cookie + Accept-Language → Next.js request locale → en/es catalogs
          ▲                                      │ HTTP Accept-Language
          │ cookie mirrors authenticated account ▼
          └──────── Preferences response ← Django idioma_efectivo(request, user)
                                                   │
                                      recipient email / TMDB language
```

## OT-70: request infrastructure

The frontend request configuration resolves supported cookies and weighted,
regional `Accept-Language` values, with an English fallback. Invalid headers
fall back to English; unsupported cookies leave header resolution available.
The server layout supplies this locale to `html.lang` and the client provider
without URL prefixes. Legacy visible page text remains unchanged at this stage.
next-intl 4.14.9 provides the message-key and ICU-argument types through its
experimental declaration generator; the generated declaration is versioned
so a clean checkout can run TypeScript before the build.

OT-70's transitional `legacy` catalog contains the current Spanish copy for
settings, email confirmation, password reset and pure validation. Its 77
messages have matching English keys. The user approved 53 missing English
translations and the temporary `Mis reseñas` / `My reviews` title on 08/10/2026;
the other English messages reuse approved curated copy. The versioned OT-70
CSV records the source and approval of each message. It is separate from
OT-13's immutable approval record. OT-76 changes confirmation to voseo and fixes the password-help character list;
OT-77 seeds the complete approved design catalogs reproducibly.

The four existing metadata entry points resolve descriptions and page titles
through `generateMetadata`; branding and icons remain identical. Unit renders
use a real Spanish next-intl provider by default and may explicitly request
English while retaining an existing custom wrapper. Existing Spanish selectors
and assertions remain unchanged.

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
closure gates. OT-13 adds no production implementation or tests.

## Implementation progress

OT-20 is integrated through PRs #55, #56 and #57 with green CI, ending at
`51bcb2b`. It implements the nullable user locale without backfill, weighted
backend resolution, readable user fields, preferences writes, locale on new
traditional/Google accounts and known ES/EN development accounts. Existing
Google accounts and the reviews-only seed retain their saved language.

OT-70 is locally implemented in three units based on OT-40's final head.
Request configuration, 77 approved transitional messages, four localized
metadata entry points and the Spanish test provider are implemented; their
publication CI and integration remain pending. The backend passes 546 tests
and frontend passes 73 unit tests, build, types, lint and format. The unchanged
frontend tree retains the previously verified 30 e2e as prior evidence until
CI repeats them. Formatting, API-code consumption, selector synchronization,
routes, pilot migration, complete design catalogs, emails and TMDB are not
claimed complete by this frontend delivery.


## Implemented frontend behavior (OT-71–83)

`lib/format.ts` is the only formatting boundary: medium/long UTC dates, integers,
one-decimal ratings and hour/minute durations, using `en-US`/`es-AR`. Profile and
review cards consume it. `ApiError` exposes status, code, params and leaves,
without retaining prior response bodies. The translator prefers field-specific
copy, then code, then unknown; known waits use ICU plurals. CSRF bootstrap and
username availability also send `Accept-Language`.

The language control uses native grouped radios with full names and visible
focus. Signed-in users change language only in Settings; saving succeeds before
account/cookie/render change. Null saved language preserves device resolution.
Login and Google completion synchronize the account before navigation. Public
Landing/login/register show EN/ES at the top right; the desktop footer offers
full names. Authenticated footer links to `/settings#t-idioma`, shows the current
language in Information on desktop or a single mobile row, and omits sign-up/login
links. Navbar and avatar contain no language control.

Routes live in `lib/routes.ts`: `/profile`, `/settings`, `/my-reviews`, `/lists`,
`/complete-signup`, `/confirm-email/[key]`, `/reset-password/[uid]/[token]`.
`/lists` has protection but no new screen. Settings and both mail destinations
are bilingual. Opening a mail link uses the receiving device's cookie/header
resolution, even when it differs from the mail language (user confirmation on
08/10/2026); links do not override locale.

The generator reads approved CSVs from scratch, excludes sample/design/chatbot
rows and emails, and splits legal copy from the client catalog. It also copies
the stable enum contract into the frontend for Docker/Turbopack builds. Tests
verify reproducibility, key/argument/tag/plural/code/enum parity. ESLint rejects
visible literals outside 13 named legacy exceptions, debug reads and formatting
outside the shared module. CI covers `develop`; runtime fallback titles carry
`lang="en"` according to `campos_en_ingles`.

Persisted list items and personal-review rows MUST expose `campos_en_ingles` outside English, including separate title/poster fallback identities. The marker reuses prefetched translations; it MUST NOT introduce SQL queries per field or per row. English-native rows do not carry a fallback marker.
