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

### Requirement: An expired API cookie does not break the Admin session

These documentation views MUST authenticate through the Django session. Their
access MUST NOT depend on the API's JWT cookie, which may be expired or invalid
in the same browser.

#### Scenario: Staff has an invalid JWT cookie

- GIVEN a staff user with a valid Django Admin session and an invalid `access` cookie
- WHEN they request either documentation route
- THEN the route returns 200
