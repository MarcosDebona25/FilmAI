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
and HTTP 403. The page MUST say that a staff account is required, explain when
the current session lacks permission, and link to the Django Admin login with
`next` returning to the requested route. Clients requesting JSON MUST receive
a 403 JSON response with a useful `detail` message.

#### Scenario: A visitor opens the schema in a browser

- GIVEN no Admin session and an `Accept: text/html` request
- WHEN `/api/schema/` is opened
- THEN the response is an HTML page with status 403
- AND the login link returns to `/api/schema/` after successful sign-in

#### Scenario: A signed-in user lacks staff permission

- GIVEN a valid session for a regular user
- WHEN `/api/docs/` is opened in a browser
- THEN the response explains that the current account lacks administration access

#### Scenario: A programmatic client requests JSON

- GIVEN no Admin session and an `Accept: application/json` request
- WHEN `/api/schema/` is requested
- THEN the response is a 403 JSON object explaining how to get access

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
