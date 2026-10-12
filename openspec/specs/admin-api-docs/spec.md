# admin-api-docs Specification

## Purpose

Allow trusted staff to inspect FilmAI's generated API documentation using the
existing Django Admin session.

## Requirements

### Requirement: Both documentation resources require staff

`GET /api/docs/` and `GET /api/schema/` MUST require a valid Django session
whose user has `is_staff=True`. An anonymous request or a session belonging to
a regular user MUST NOT expose either resource.

#### Scenario: A staff user opens Swagger

- GIVEN a staff user signed in through Django Admin
- WHEN they request `/api/docs/` and `/api/schema/`
- THEN both return 200

#### Scenario: A regular user or visitor requests documentation

- GIVEN no Django Admin session, or a session for a user without `is_staff`
- WHEN either documentation route is requested
- THEN access is denied

### Requirement: Access denial explains the next step

For browser requests, both documentation routes MUST respond with an HTML page
and HTTP 403. The page MUST show an admin login form when there is no usable
session, and an explanation naming the current account when the session lacks
`is_staff`, with an action to switch account. The page MUST be served in the
account's language, then the `Accept-Language` preference, then English.
Clients requesting JSON MUST receive a 403 JSON response with a useful
`detail` message.

#### Scenario: A visitor opens the schema in a browser

- GIVEN no Django session and an `Accept: text/html` request
- WHEN `/api/schema/` is opened
- THEN the response is an HTML page with status 403 containing the login form
- AND the form returns to `/api/schema/` after a successful login

#### Scenario: A signed-in user lacks staff permission

- GIVEN a valid session for a regular user
- WHEN `/api/docs/` is opened in a browser
- THEN the response explains that the current account lacks administration access
- AND offers to switch account and to go back to the application

#### Scenario: A programmatic client requests JSON

- GIVEN no Admin session and an `Accept: application/json` request
- WHEN `/api/schema/` is requested
- THEN the response is a 403 JSON object explaining how to get access

### Requirement: The login form only admits active staff

`POST /api/docs/login/` MUST require a CSRF token, authenticate by email or
username, and open the Django session only for active accounts with
`is_staff=True`. Wrong credentials, unknown accounts and regular accounts MUST
produce the same message. After ten failed attempts from one IP in sixty
minutes the form MUST answer 429 until the window expires. The page MUST state
this policy and the attempts left after a failure. The `next` value
MUST be `/api/docs/` or `/api/schema/`; anything else returns to `/api/docs/`.

#### Scenario: Staff logs in with email or username

- GIVEN a staff account
- WHEN the form is submitted with its email or username and a valid password
- THEN the user is redirected to the requested documentation route with a session

#### Scenario: A regular account submits a valid password

- GIVEN an account without `is_staff`
- WHEN the form is submitted with its correct credentials
- THEN no session is opened and the generic incorrect-credentials message appears

### Requirement: An expired API cookie does not break the Admin session

These documentation views MUST authenticate through the Django session. Their
access MUST NOT depend on the API's JWT cookie, which may be expired or invalid
in the same browser.

#### Scenario: Staff has an invalid JWT cookie

- GIVEN a staff user with a valid Django Admin session and an invalid `access` cookie
- WHEN they request either documentation route
- THEN the route returns 200

### Requirement: The generated schema has a versioned baseline

`contracts/openapi.yaml` MUST preserve the output of `python manage.py spectacular`.
A backend test MUST fail when the generated schema differs semantically from that
baseline. Reference regeneration MUST require `FILMAI_ACTUALIZAR_REFERENCIAS=1`.

#### Scenario: Schema changes without updating its contract

- GIVEN the generated schema differs from `contracts/openapi.yaml`
- WHEN the backend contract test runs without the regeneration variable
- THEN the test fails and leaves the versioned contract unchanged

#### Current limitation (OT-02)

The baseline captures existing introspection warnings and omissions from views
without declared serializers. It does not assert that every endpoint is fully
specified. OT-02 preserves this behavior rather than changing API documentation
outside its characterization scope.
