# Error contract capability

## Purpose and evidence

Define the multilingual API contract implemented in F3 and consumed in F7.
`docs/i18n/errores.csv` maps every message observed in the 91 OT-01 references,
source branches absent from those references, and explicit non-API exclusions.

```text
Django validators → typed error + catalog → handler / explicit Response normalization
                                                  │ HTTP (codes + params)
                                                  ▼
                              ApiError → errors helper → en/es message catalogs
```

## Implementation progress

OT-30 starts with the general/domain/success registry and its typed exception.
HTTP contexts, parameter types and nonnegative known waits are validated there.
Validation leaf definitions and metadata preservation are also implemented,
including an explicit bridge for Django error lists and configured parameters.
The pure envelope builder and legacy-body merger are implemented and tested.
The metadata carrier must be constructed after the final DRF conversion; it
is not guaranteed to survive validate/validate_<field> rewrapping. Domain
serializer boundary adoption belongs to OT-31/OT-32. Handler integration
remains pending; existing endpoint responses are unchanged at this boundary.
The requirements below describe the completed contract, not this partial delivery.

## Requirements

### Requirement: Stable error envelope

Every API response with status 400–599 MUST contain these keys:

```json
{
  "code": "validation_error",
  "params": {},
  "errors": [
    { "field": "correo", "code": "email_already_used", "params": {} },
    { "field": null, "code": "passwords_do_not_match", "params": {} }
  ]
}
```

`code` MUST be a registered English snake_case identifier. `params` MUST be an
object containing only documented machine values. `errors` MUST be a list.
Validation uses top-level `validation_error`, HTTP 400 and one entry per error.
Each entry has exactly `field` (request field or null), `code` and `params`.
Non-validation failures use their specific top-level code and `errors: []`.
Existing request field names and enum values MUST retain their spelling.

#### Scenario: Normalize irregular and nested validation

- GIVEN dictionaries with string/list values, nested serializer errors or a root list
- WHEN the handler walks the real validation details
- THEN each leaf becomes an error entry, preserving order and all errors
- AND dictionary paths use dots, list positions use zero-based numeric segments
- AND `non_field_errors` and root-list errors use `field: null` at the root
- AND nested general errors use their parent path (for example `items.0`)
- AND no response text is parsed to decide a domain code

#### Scenario: Parameter values

- GIVEN a failed length, range, choice, avatar or age check
- THEN parameters come from validator/field configuration, not message parsing
- AND numbers are finite, limits are numeric and lists contain machine identifiers
- AND passwords, tokens, emails, raw payloads and interpolated sentences never enter params
- AND an error without interpolation arguments has `params: {}`
- AND Django ValidationError.error_list retains each code and params before DRF conversion
- AND parameter metadata is attached at the validator boundary when ErrorDetail would lose it

### Requirement: Debug is conditional

With `DEBUG=False`, `debug` MUST be absent, including all leaf entries.
With `DEBUG=True`, top-level `debug: {"message": "…"}` MAY contain the internal
message for diagnosis. It MUST NOT alter codes, parameters or status.
The frontend MUST never read `.debug`; the lint rule forbids it.
Internal Spanish messages remain in the backend; upstream diagnostics are
normalized to the catalog's internal message, rather than shown by the UI.

#### Scenario: Unexpected failure

- GIVEN an unhandled exception with an internal diagnostic
- WHEN `DEBUG=False`
- THEN the response uses `server_error`, HTTP 500, empty params/errors and no debug

### Requirement: Catalog as the sole production source

`backend/filmai/errores/catalogo.py` MUST register the following codes, valid
HTTP contexts, parameter schemas and internal messages. The CSV supplies the
exact existing messages and aliases; these tables define public semantics.
`{}` is the parameter schema whenever none is stated.

#### General and domain codes

| Code                                 | HTTP context                          | Meaning and parameters                                                                                    |
| ------------------------------------ | ------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `validation_error`                   | 400                                   | Top-level serializer/validator failure; leaves carry specific codes.                                      |
| `not_authenticated`                  | 401                                   | Authentication absent; includes missing refresh cookie/token.                                             |
| `invalid_credentials`                | 400 login / 401 authentication        | Incorrect credentials; Password/Google login preserves current 400; authentication failures retain 401.   |
| `permission_denied`                  | 403                                   | Permission or CSRF denial.                                                                                |
| `documentation_staff_required`       | 403                                   | API documentation requires a staff Admin session.                                                         |
| `not_found`                          | 404                                   | Missing route/resource or invalid pagination cursor.                                                      |
| `method_not_allowed`                 | 405                                   | Unsupported HTTP verb; `method: string` from the request.                                                 |
| `not_acceptable`                     | 406                                   | No representation satisfies Accept.                                                                       |
| `unsupported_media_type`             | 415                                   | Unsupported Content-Type; `mediaType: string`.                                                            |
| `parse_error`                        | 400                                   | Malformed request body; no parser diagnostics in params.                                                  |
| `throttled`                          | 429                                   | Too many requests; wait policy is specified below.                                                        |
| `server_error`                       | 500                                   | Unexpected application failure.                                                                           |
| `upstream_bad_request`               | 400                                   | TMDB rejected request parameters.                                                                         |
| `upstream_not_found`                 | 404                                   | TMDB resource absent.                                                                                     |
| `upstream_error`                     | 502                                   | TMDB 5xx, unexpected HTTP response or exhausted retry budget.                                             |
| `upstream_unavailable`               | 503                                   | TMDB transport/decoding failure.                                                                          |
| `invalid_token`                      | 401                                   | JWT malformed, expired, blacklisted, wrong type or without required claims.                               |
| `session_revoked`                    | 401                                   | Valid JWT no longer matches the user's current password hash.                                             |
| `account_deactivated`                | 403                                   | Login to a deactivated account, only after credentials are verified.                                      |
| `account_pending_confirmation`       | 403                                   | Login to a pending account, only after credentials are verified.                                          |
| `link_expired`                       | 400                                   | Confirmation signature expired; legacy `codigo: expirado`.                                                |
| `link_invalid`                       | 400                                   | Bad/missing confirmation or reset token; legacy `codigo: invalido`. Reset expiry stays indistinguishable. |
| `already_confirmed`                  | 400                                   | Already consumed/cannot reactivate; legacy `codigo: ya_confirmada`.                                       |
| `list_name_duplicated`               | 409                                   | Existing name; legacy `codigo: nombre_lista_duplicado`.                                                   |
| `list_item_duplicated`               | 409                                   | Existing membership; legacy `codigo: item_duplicado`.                                                     |
| `default_list_protected`             | 409                                   | Cannot rename/delete default list; legacy `codigo: lista_predeterminada_protegida`.                       |
| `rating_blocks_removal_from_watched` | 409                                   | Remove rating first; legacy `codigo: calificacion_impide_quitar_de_vistas`.                               |
| `rating_duplicated`                  | 409                                   | Existing rating; legacy `codigo: calificacion_duplicada`.                                                 |
| `username_already_used`              | 400 validation / 409 profile conflict | Username already registered; profile conflict has empty errors.                                           |

#### Validation leaf codes

| Code                             | Meaning and machine parameters                                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `required`                       | Missing field; Google token/extra profile fields use the actual field name.                                              |
| `blank`                          | Empty string; also the defensive empty-list-name validator.                                                              |
| `null`                           | Null is not allowed.                                                                                                     |
| `invalid`                        | Invalid primitive, email, date or regex; optional `expectedType: string` for catalog numbers.                            |
| `invalid_choice`                 | Value outside choices; optional `allowedValues: string[]` from field choices.                                            |
| `max_length`                     | Too long; `maxLength: integer`. List name uses 80.                                                                       |
| `min_length`                     | Too short; `minLength: integer`.                                                                                         |
| `min_value`                      | Below minimum; `minValue: number`. Positive catalog integers use 1.                                                      |
| `max_value`                      | Above maximum; `maxValue: number`. Rating limits remain 1–10.                                                            |
| `unique`                         | Generic uniqueness validator; domain-specific checks use their own code.                                                 |
| `not_a_dict`                     | Serializer input has the wrong object shape.                                                                             |
| `number_not_finite`              | NaN/infinity in catalog number parameter.                                                                                |
| `email_already_used`             | Registered email, including Google duplicate email before persistence.                                                   |
| `email_or_username_already_used` | Integrity race during social signup; no guessed field.                                                                   |
| `username_invalid`               | Alphanumeric 5–25; `minLength: 5`, `maxLength: 25`.                                                                      |
| `username_not_allowed`           | allauth's blacklisted username; do not publish the blacklist.                                                            |
| `person_name_invalid`            | Letters/spaces only; `maxLength: 50`.                                                                                    |
| `birth_date_in_future`           | Future birth date.                                                                                                       |
| `minimum_age`                    | Under the required age; `minAge: 13`.                                                                                    |
| `avatar_invalid`                 | Avatar not in the active registry; `allowedIds: integer[]`.                                                              |
| `local_password_unavailable`     | Google-only account cannot change a local password.                                                                      |
| `current_password_incorrect`     | Wrong old password.                                                                                                      |
| `passwords_do_not_match`         | Confirmation differs; field is `password2` or null according to the actual validator.                                    |
| `password_too_short_or_long`     | FilmAI length rule; `minLength: 8`, `maxLength: 20`.                                                                     |
| `password_no_upper`              | At least one uppercase character is required.                                                                            |
| `password_no_lower`              | At least one lowercase character is required.                                                                            |
| `password_no_digit`              | At least one digit is required.                                                                                          |
| `password_no_special`            | Required special character; `specialCharacters: "@#$%&*!"`.                                                              |
| `password_too_short`             | Django/allauth minimum length; `minLength: integer` from validator.                                                      |
| `password_too_common`            | Django common-password validator.                                                                                        |
| `password_entirely_numeric`      | Django numeric-password validator.                                                                                       |
| `password_too_similar`           | Django similarity check; optional `attribute: string` is the model field identifier, never its translated label.         |
| `google_authentication_failed`   | Operational OAuth verification/completion failure or HttpResponseBadRequest; invalid credentials use the top-level code. |
| `list_name_missing_alphanumeric` | No letter or digit in the list name.                                                                                     |
| `list_name_invalid_characters`   | Only letters, numbers and spaces are allowed.                                                                            |
| `review_update_empty`            | Neither `valor` nor `texto` was supplied; `fieldNames: ["valor", "texto"]`.                                              |

### Requirement: Normalize third-party codes at their origin

The installed libraries are the source of alias names, not assumptions about
translated messages. `dj_rest_auth/serializers.py`,
`dj_rest_auth/registration/serializers.py`, `dj_rest_auth/jwt_auth.py`,
`dj_rest_auth/views.py`, `allauth/account/adapter.py`, `rest_framework/{fields,exceptions}.py` and
`rest_framework_simplejwt/{authentication,serializers,tokens,exceptions}.py`
were inspected in the running backend for OT-11.

| Source / current code or condition                                                                                                            | Registered target / rule                                                                                                                            |
| --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| DRF `required`, `blank`, `null`, `invalid`, `min_length`, `max_length`, `min_value`, `max_value`, `unique`, `invalid_choice`, `not_a_dict`    | Same code.                                                                                                                                          |
| DRF numeric `max_string_length`, `overflow`; DateField `datetime`                                                                             | `invalid`; preserve field, derive optional expectedType from the validator.                                                                         |
| DRF exceptions `parse_error`, `not_acceptable`, `unsupported_media_type`, `not_found`, `method_not_allowed`, `throttled`, `permission_denied` | Same code; derive parameters from request/exception metadata.                                                                                       |
| DRF `authentication_failed` / missing credentials                                                                                             | `invalid_credentials` / `not_authenticated`.                                                                                                        |
| dj-rest-auth “Unable to log in with provided credentials.”                                                                                    | `invalid_credentials` as a top-level failure, preserving login HTTP 400.                                                                            |
| dj-rest-auth missing username/email/password condition                                                                                        | `required` validation; field null for either identifier missing, password for missing password.                                                     |
| dj-rest-auth “The two password fields didn't match.”                                                                                          | `passwords_do_not_match`; never depend on translated punctuation.                                                                                   |
| dj-rest-auth “User is already registered with this e-mail address.”                                                                           | `email_already_used`; FilmAI overrides the inherited email field.                                                                                   |
| allauth `email_taken`, `duplicate_email`, `username_taken`, `username_blacklisted`                                                            | `email_already_used`, `username_already_used`, `username_not_allowed`.                                                                              |
| allauth `email_password_mismatch`, `username_password_mismatch`, `invalid_login`                                                              | `invalid_credentials`; avoid account-state disclosure.                                                                                              |
| allauth `invalid_or_expired_key`, `invalid_password_reset`                                                                                    | `link_invalid`; no invented expired/invalid distinction.                                                                                            |
| allauth `incorrect_password`, `enter_current_password`                                                                                        | `current_password_incorrect`, `required` on old_password.                                                                                           |
| allauth `rate_limited`, `too_many_login_attempts`                                                                                             | `throttled`; apply the same wait policy.                                                                                                            |
| allauth `account_inactive`, `unverified_primary_email`; dj-rest-auth disabled/unverified user                                                 | Resolve account state only after verified credentials; otherwise `invalid_credentials`.                                                             |
| SimpleJWT `token_not_valid`, TokenError for expired/blacklisted/wrong type/missing claims                                                     | `invalid_token`; remove the nested vendor diagnostic tree.                                                                                          |
| dj-rest-auth LogoutView direct Response: missing refresh cookie/request token; TokenError; AttributeError/TypeError                           | `not_authenticated` 401; `invalid_token` 401; `server_error` 500. These responses bypass the exception handler and MUST use explicit normalization. |
| SimpleJWT missing refresh token/cookie                                                                                                        | `not_authenticated`; identified at token extraction, not by translated text.                                                                        |
| SimpleJWT `password_changed`                                                                                                                  | `session_revoked`.                                                                                                                                  |
| SimpleJWT `user_not_found`, `user_inactive`, `no_active_account` outside login                                                                | `invalid_token`; no account-state details for an API session failure.                                                                               |

allauth's phone, email-management and login-code workflows are not public FilmAI
API endpoints. Their messages (`unknown_email`, `unknown_phone`, `phone_taken`,
`incorrect_code`, removal/address-limit conditions) MUST NOT be exposed by adding
new endpoints or guessing domain codes. Recovery for an unknown email retains
its generic success response. New reachable library codes MUST be registered
explicitly; backend tests MUST reject unknown codes rather than silently emit them.

### Requirement: Preserve account-state confidentiality

HTTP states MUST remain unchanged during multiidioma. A code identifies meaning,
not a universal status: the catalog records allowed statuses by explicit context
(for example invalid_credentials 400 for login and 401 for authentication,
username_already_used 400 for validation and 409 for profile conflict).
This contextual rule was approved by the user for OT-11.

#### Scenario: Invalid credentials for every account state

- GIVEN an absent, active, pending or deactivated account
- WHEN its supplied password or Google token is invalid
- THEN top-level code is `invalid_credentials` for password login
- AND invalid Google credentials also use top-level `invalid_credentials` with empty errors
- AND operational verification/transport failures use validation_error with google_authentication_failed
- AND no account-state code or parameter is included

#### Scenario: Valid credentials for inactive account

- GIVEN a pending/deactivated account
- WHEN its password or Google token has been verified
- THEN return HTTP 403 with account_pending_confirmation/account_deactivated respectively
- AND Google account-state validation occurs only after token verification

### Requirement: Preserve throttling information

For a known wait, `throttled` MUST include `params.retry_after_seconds` as a
nonnegative integer, rounded upward, and an identical `Retry-After` seconds
header. Waiting zero seconds is distinct from an unavailable wait.
The known-wait source is `Throttled.wait` or the upstream response metadata.
TMDB retry metadata MUST be preserved at the HTTP-client boundary when present.
If the upstream supplies no usable wait, both `retry_after_seconds` and
`Retry-After` MUST be omitted; seconds MUST NOT be invented. This exception for
unknown waits was explicitly approved by the user for OT-11.

#### Scenario: DRF rate limit

- GIVEN Throttled(wait=41.2)
- THEN HTTP is 429, retry_after_seconds is 42 and Retry-After is "42"
- AND params contains no translated “wait” sentence

#### Scenario: Upstream rate limit with no known wait

- GIVEN TMDB returns 429 without usable Retry-After metadata
- THEN code is throttled and HTTP is 429
- AND params is empty and Retry-After is absent

### Requirement: Code-bearing successful responses

Successful responses that currently contain UI text MUST add these codes in F3
and remove their legacy `detail` in OT-83. Payloads with data retain those data;
204 responses remain empty. Do not inject error arrays into successful bodies.

| Current response / origin                                              | New code                                                                                                                 |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Recovery's generic email-sent response (`usuarios/views.py:247-254`)   | `password_reset_requested`; retain `intentos_restantes` as machine data.                                                 |
| Successful reset (`usuarios/views.py:279-280`)                         | `password_reset_completed`.                                                                                              |
| Successful authenticated change (`usuarios/perfil.py:112-114`)         | `password_updated`.                                                                                                      |
| Successful deactivation (`usuarios/cuenta.py:65-66`)                   | `account_deactivated_successfully`.                                                                                      |
| Successful email verification (`usuarios/views.py:226`)                | `email_confirmed`.                                                                                                       |
| CSRF bootstrap's detail "ok" (`usuarios/views.py:146`)                 | `csrf_ready`; preserve the CSRF cookie.                                                                                  |
| Registration, re-send verification, logout inherited from dj-rest-auth | `registration_pending_confirmation`, `confirmation_email_sent`, `logged_out` respectively; preserve other response data. |

### Requirement: Export and consume the contract

OT-34's `exportar_contrato` MUST generate versioned `contracts/error-codes.json`
from the production catalog, including codes, success/error category, allowed
HTTP contexts and parameter schemas. OT-11 MUST NOT create that export early.
The stale-export test compares the entire generated content.
The frontend requires English and Spanish translations for every public code;
lookup uses `errors.fields.<field>.<code>`, then `errors.codes.<code>`, then
`errors.codes.unknown`. `unknown` is a frontend fallback, never a backend code.
Parameters used by ICU follow their declared name; the helper maps the explicit
API key `retry_after_seconds` to ICU's `retryAfterSeconds` centrally.

### Requirement: Compatibility and verification gates

F3–F7 MUST add the envelope alongside every existing detail/codigo/field key.
Non-object root validation lists are normalized; their contents survive as
`non_field_errors` during the compatibility window. Codes MUST be obtained
from typed exceptions/validators, never inferred from message text.
OT-30 may adapt only the new OT-01 tests to compare legacy fields and test the
new envelope separately, as explicitly authorized by the user. Deliberate F0
reference changes need a reviewed diff and explicit regeneration environment
variable. Pre-plan tests retain the phase's original exceptions.
OT-82 migrates old assertions to codes; OT-83 removes legacy text keys.

#### Scenario: Contract verification

- GIVEN every 4xx/5xx response produced by the backend suite
- THEN a test client validates the envelope, status/context and all registered codes
- AND every catalog code has a focused behavior test
- AND DEBUG=False responses contain no debug
- AND reserved envelope names do not collide with serializer request fields
- AND removing a public code translation or changing the export fails CI
