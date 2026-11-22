# Auth UI

## Purpose

The sign-up screens a visitor uses to create an account (CU-001, CU-002): the three-step registration at `/register` (decided in the canvas, sections 16 and 17; shipped in #225, 16/11/2026), the Google sign-up that completes it at `/complete-signup`, and the «Check your email» state with its resend. Login, password reset and email confirmation are described in `docs/02` (CU-002, CU-003, CU-020) and `docs/04`. Backend contracts: `POST /api/auth/registration/`, `GET /api/auth/username-available/`, `POST /api/auth/registration/resend-email/` and `POST /api/auth/google/`; the account emails are in `emails`, the error codes in `error-contract`. All visible text comes from the i18n catalog (`i18n-core`); the UI never reads `detail`, `debug` or `codigo` from a response.

## Requirements

### Requirement: Three steps with progress

`/register` MUST split the form into three steps and MUST show a continuous 4 px progress bar (`role="progressbar"`, value = the current step out of 3) under the logo, one title for all steps, a full-width «Continue» and a «‹ Back» link under it. The fields of each step MUST be:

1. email, password and password confirmation, plus «Continue with Google» as an alternative;
2. first name, last name, username, date of birth, gender and country;
3. avatar (optional, chosen in a paginated dialog) and acceptance of the Terms and Conditions.

All steps MUST stay mounted in the same grid cell, so the card never changes size when the step or an error changes; the inactive steps MUST be `inert` (out of the keyboard and the accessibility tree). Moving to a step MUST put the focus on its first field. «Back» MUST keep what was typed and MUST be hidden, keeping its place, on step 1. Enter in a field MUST do what the main button does. A polite live region that exists from the first render MUST announce «Step N of 3» when the step changes.

#### Scenario: Going through the steps

- GIVEN a visitor on step 1 of `/register` with valid email and passwords
- WHEN they press «Continue»
- THEN the bar moves to 2 of 3 and the focus lands on first name
- AND pressing «Back» returns to step 1 with the email and passwords still filled in

#### Scenario: An invalid step does not advance

- GIVEN a visitor on step 1 with an empty email
- WHEN they press «Continue»
- THEN they stay on step 1, the errors of that step's fields are visible and the focus goes to the first invalid field

### Requirement: Field validation while typing

A field's error MUST appear when the user types an invalid value (or empties a field they had typed in) and MUST go away when it is corrected; moving through the fields without typing MUST NOT show errors. The password MUST show its four rules (8 to 20 characters, upper and lower case, a digit, one of `@#$%&*!`) as a checklist that marks each one as it is met, and the confirmation MUST be validated again when the original password is edited. The date of birth MUST follow the locale-aware date input of `i18n-core` («Locale-aware formatting and labels»), the country starts empty (never preselected from the browser) and is required, and the gender error MUST be linked to its `<select>` with `aria-describedby`. Each field MUST reserve one line for its message, so showing an error never moves the layout (#175).

#### Scenario: Checking the password rules

- GIVEN the password field on step 1
- WHEN the user types `Abcdef1!`
- THEN the four rules show as met and no error is shown

### Requirement: Username availability

While the user types a valid username on step 2, the screen MUST ask `GET /api/auth/username-available/?username=` 400 ms after the last key, cancelling the previous request, and MUST show «Available» inside the field with a check, or the error `username_already_used` (taken) or `username_not_allowed` (reserved; the list of reserved names is never shown). A network error, an unsuccessful response or 429 (Too Many Requests) MUST leave the state as unknown and MUST NOT block «Continue»: the server decides on submit. If «Continue» is pressed while the check is running, the click MUST stay pending and advance when the username turns out available, or stay on the step with the error in the field when it is taken; editing the username MUST cancel the pending click.

#### Scenario: Continue while the check is running

- GIVEN a valid username whose check has not answered
- WHEN the user presses «Continue»
- THEN the screen waits
- AND if the answer is «taken», it stays on step 2 with the error in the username field

### Requirement: Submitting the registration

Pressing the main button on step 3 without accepting the Terms MUST NOT create the account and MUST flag the checkbox. With them accepted, the screen MUST send `POST /api/auth/registration/` with the nine fields, `acepta_terminos: true` and, if one was chosen, `avatar_id` (a failed avatar catalog request hides the avatar group and the field is not sent). When the answer is 201 (Created) the screen MUST save the email in the browser (`sessionStorage`, to resend after an expired link) and show «Check your email» (see the last requirement). The account stays pending until the emailed link is opened (CU-002).

#### Scenario: Registration accepted

- GIVEN the three steps complete and the Terms accepted
- WHEN the visitor submits
- THEN the screen shows «Check your email» with the address

### Requirement: Server errors return to the step of the field

When the server rejects the registration with field errors, the screen MUST map them by field and go back to the step of the first field with an error, in the order of the steps (email, password and confirmation; then the step 2 fields; then avatar and Terms), leave it focused with the message on that field, and mark a taken username as taken. The message MUST come from the error code through the catalog, so changing the language (the EN | ES selector stays active) changes the message. An error that is not tied to a field MUST be shown as an alert on the current step. Errors on the Terms or the avatar stay on step 3.

#### Scenario: Error on an earlier step

- GIVEN a submit on step 3 that the server rejects with `email_already_used` on `correo` and `terms_not_accepted`
- WHEN the answer arrives
- THEN the screen goes back to step 1 with the focus on the email and the message on that field

#### Scenario: Email service unavailable

- GIVEN a submit on step 3 and a task queue that does not accept the email
- WHEN the server answers 503 (Service Unavailable) with `email_unavailable`
- THEN no account was created and the visitor stays on step 3, with the catalog text of `email_unavailable` in an alert (never the server's text)
- AND the main button is enabled so they can try again

### Requirement: Google sign-up is steps 2 and 3

«Continue with Google» on step 1 of `/register` MUST mark a pending Google sign-up in the browser (`sessionStorage`, with its origin, `register`) and go to `/complete-signup`. A visitor who pressed Google on `/login` and whose Google account has no FilmAI account (the answer is 400 (Bad Request) with `required` on `nombre_usuario`, `pais`, `fecha_nacimiento` or `genero`) MUST be taken to the same screen, with origin `login`. `/complete-signup` MUST show the progress bar starting at step 1's width (Google was step 1) and then filling to the current step, MUST ask on step 2 for username, date of birth, gender and country, and on step 3 for the avatar (optional) and the Terms. The step 3 action MUST be the Google button, inert until the Terms are accepted; it asks Google for a fresh `id_token` (one-use: the one from the first click is never stored) and sends `POST /api/auth/google/` with `id_token`, the step 2 fields, `acepta_terminos: true` and, if chosen, `avatar_id`. The account is created active (no confirmation email); the screen MUST clear the pending mark, sync the interface language with the account and go to `/home`.

A screen opened with no pending Google sign-up MUST redirect to `/login`. «Back» on step 2 MUST discard the sign-up and return to the origin screen (`/register` or `/login`); «Back» on step 3 returns to step 2 keeping what was typed.

#### Scenario: Completing the sign-up

- GIVEN a visitor who pressed «Continue with Google» on `/register`
- WHEN they fill step 2, choose an avatar, accept the Terms and press the Google button
- THEN the screen sends the fields with a fresh `id_token`, and on success goes to `/home`

#### Scenario: Server rejects a step 2 field

- GIVEN the Google confirmation answered with `username_already_used` on `nombre_usuario`
- WHEN the answer arrives
- THEN the screen goes back to step 2 with the focus on the username, a notice that the highlighted fields need fixing, and the error in the field
- AND an error with no field, or one on the Terms or the avatar, stays on step 3 and shows no such notice

#### Scenario: No pending sign-up

- GIVEN a visitor who types `/complete-signup` in the address bar
- THEN they are redirected to `/login`

### Requirement: Check your email and resend

After a registration, and when a confirmation link has expired, the screen MUST show «Check your email» with the address and a «Resend link» button that stays disabled for 60 seconds, with a live countdown. Pressing it MUST send `POST /api/auth/registration/resend-email/` with `{email}` and restart the 60 seconds. An error MUST show the catalog text of its code under the button. When the answer is 503 (Service Unavailable) with `email_unavailable`, the text is «We couldn’t send the email. Try again in a few minutes.» (catalog), and the server's text is never shown. The expired-link screen (`/confirm-email/[key]`) MUST resend to the email saved in the browser and, when there is none, MUST ask for it before resending.

#### Scenario: Resending after the wait

- GIVEN the «Check your email» screen after 60 seconds
- WHEN the visitor presses «Resend link» and the server accepts it
- THEN the countdown starts again

#### Scenario: Resend with the queue down

- GIVEN the «Check your email» screen after 60 seconds
- WHEN the visitor presses «Resend link» and the server answers 503 (Service Unavailable) with `email_unavailable`
- THEN the screen shows the catalog text of `email_unavailable`
- AND the response's `detail` text is not shown

### Requirement: Accessibility and tests

Every field MUST have an associated label and its error linked with `aria-describedby`, the Terms link MUST open `/terms` in another tab, and the focus MUST follow each step or error as described above. The behavior is covered by `frontend/tests/access-screens.test.tsx` (registration, confirmation and resend), `frontend/tests/complete-signup.test.tsx` (Google sign-up), `frontend/tests/google-auth.test.ts` and the Playwright flows `frontend/e2e/registro.spec.ts` and `frontend/e2e/alta-google.spec.ts`, which also check that nothing shifts between steps or with errors in both languages.
