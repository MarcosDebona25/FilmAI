# Delta for title-page-ui

Proposal (Q-7 in `proposal.md`): applies only if Gonza keeps PR 7.

## ADDED Requirements

### Requirement: People link to Search (13/11/2026)

`GET /api/catalogo/{tipo}/{id}/credits/` MUST include the TMDB `id` of each director, creator and cast member. In «Director and cast», each name MUST be a link to `/search?person={id}&role=director` (directors, and creators of shows) or `/search?person={id}&role=actor` (cast), with the name as its text. A name without an id MUST stay plain text.

#### Scenario: A creator

- GIVEN `/tv/1396`
- WHEN the user follows «Vince Gilligan» in «Created by»
- THEN the page is `/search?person=66633&role=director`
- AND Breaking Bad is among the results
