# Localized account emails capability

## Draft status and evidence

OT-13 draft, pending editorial approval. Plan 2.8/3.6/F5 and the OT-02 golden
references establish four real flows. Curated rows 603–634 supply the proposed
copy; no email-address-change endpoint is introduced by the confirmation design.

```text
Registration / allauth resend / password reset / committed password change
                              │ in-process call
                              ▼
           enviar_correo(case, recipient, context, language)
                              │ Django templates + shared HTML layout
                              ▼
                    configured Django email backend
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

| Case | Template directory | Copy reference |
| ---- | ------------------ | -------------- |
| Registration | `confirmacion_registro/{en,es}` | rows 603–613 |
| Resend confirmation | `confirmacion_correo/{en,es}` | rows 615–619 plus shared subject |
| Reset password | `restablecer_contrasena/{en,es}` | rows 621–627 |
| Password updated | `contrasena_actualizada/{en,es}` | rows 629–634 |

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
route migration. Before that order, retain the existing Spanish routes.
The password-updated recovery action MUST lead to the actual login/recovery
flow; no new recovery endpoint or reusable reset token is invented.

#### Scenario: A localized email lands in a localized pilot page

- WHEN a link is opened after coordinated route migration
- THEN the matching frontend route exists
- AND the confirmation/reset pilot supports both application locales
- AND locale resolution still follows the i18n-core cookie/account rules

### Requirement: Preserve delivery and account security behavior

OT-50 extracts sending/layout structure before text changes. OT-51 supplies
expiry context and notification HTML, OT-52 adds English and recipient language,
and OT-53 switches Spanish to the reviewed table's voseo.
Do not silently route these synchronous account emails through Celery.
Unknown/inactive reset recipients MUST keep the generic success response
without mail, avoiding disclosure. Password-update notification MUST run only
after the password transaction commits; delivery failure MUST not roll back
that committed change. Existing reset-token consumption and session revocation
remain unchanged. Resend does not create a new email-change account flow.

#### Scenario: Password transaction rolls back

- WHEN a password update does not commit
- THEN no password-updated notification is sent
- WHEN the password commits and sending fails
- THEN the password stays changed and the existing failure is logged

## Verification before closure

Use the in-memory email backend for rendering tests; do not send external
messages. Characterization references change only under the accepted F0
regeneration authorization. Test all eight variants, effective locale, expiry
context and URL routes. Review the rendered emails in a real client at OT-52
and OT-90 as required by the plan. This draft adds no sending code or tests.
