# title-page-ui Specification

## Purpose

The title page of a movie or TV show (C-07), with the rating dialog (C-08's frontend half) and the list actions (L-04). Public: without a session it shows everything but the actions. Consumes `tmdb-endpoints` (detail and credits), `reviews-api` and `list-endpoints`. Visual source of truth: the canvas artboards «Title page · desktop» and «Title page · mobile».

## Requirements

### Requirement: Routes and origin

`/movie/{id}` and `/tv/{id}` MUST render the title page; a non-numeric id MUST answer 404 (Not Found). The breadcrumb MUST follow `?from=`: `home` → Home; `search` → Search; `reviews` → Profile › Ratings & reviews; `list-{id}` → Lists › {list name}; anything else or nothing → Home. The breadcrumb MUST sit at the top left, under the navbar and aligned with the poster, on a scrim pill that keeps it legible over any backdrop. On mobile it MUST be replaced by a back link to its last item, on the same pill.

#### Scenario: Coming from a list

- GIVEN a user opens `/movie/157336?from=list-4` with a session
- THEN the breadcrumb reads Lists › {name of list 4} › {title}

### Requirement: Title data

The page MUST show the backdrop band with the site navbar over it, the poster, the title (sized by length like the Home Hero), the tagline, the type, the year, the runtime (movies) or seasons and episodes (shows), the TMDB rating with its votes as «★ 8,5», the genres and the synopsis (folded only when it overflows). While the detail loads, the page MUST show a static skeleton (no pulse or shimmer animation, 18/10/2026) with the shape of the backdrop, poster, title, data, actions, genres, synopsis and three reviews. «Director and cast» MUST list the directors — for shows, the creators as «Created by» — and the cast with characters, folding over 10.

#### Scenario: A show

- GIVEN `/tv/1396`
- THEN it shows «5 seasons · 62 episodes» and «Created by Vince Gilligan»

### Requirement: Actions

Without a session the actions MUST be replaced by «Log in to rate or save», linking to the login with `?next=` back to the page; a signed-in user MUST NOT see it while the page loads. With a session: Rate (or «★ N» with «Your rating: N out of 10. Edit» as accessible name), Favorite, Watched, Watchlist as `aria-pressed` toggles over the lists API, whose icons fill with the accent color when on; turning Watched on for a title in Watchlist MUST turn Watchlist off and say so in a single toast, and the rating dialog MUST warn that rating also removes it from Watchlist, and «Add to list» with the user's own lists and inline creation. Removing from Watched a rated title MUST ask for confirmation and then delete the rating with it.

#### Scenario: Signed in while the detail loads

- GIVEN a signed-in user whose lists arrive before the title detail
- THEN the page shows the skeleton and no «Log in to rate or save»

#### Scenario: Watched with a rating

- GIVEN a rated title in Watched
- WHEN the user turns Watched off and confirms
- THEN the rating and review are deleted, Watched is off and the button reads «Rate» again

### Requirement: Where to watch

Below the genres the page MUST show, once the detail is loaded, the streaming availability in the viewer's country (added 18/10/2026; it consumes `GET /api/catalogo/{movie,tv}/{id}/providers/` from `tmdb-endpoints`). Only with a session, in the account's `pais` (27/10/2026, issue #124). Without a session it MUST NOT be requested; in its place the page MUST show the link «Log in to see where to watch it in your country» to `/login?next=<current path>`. A failed request MUST also hide it, because it is not critical content. While it loads it MUST show a static placeholder with `role="status"`.

With providers, the page MUST show a button line «Stream or rent» + up to four logos + «N options in {country}» (plural-aware, country name in the active language) that opens a panel («Where to watch», `role="dialog"`, closed with Escape or an outside click, `aria-expanded` on the button) with the non-empty groups Stream, Free, Rent and Buy. Logos MUST NOT be links: TMDB gives no per-platform URLs, so the panel has a single «See all options on TMDB» link (new tab) when `enlace` is present. A logo missing from TMDB MUST be replaced by the platform's initial. The panel MUST carry the JustWatch attribution «Data by JustWatch», linking to justwatch.com; this attribution is a condition of TMDB's data and MUST NOT be removed. With no providers for the country it MUST say «Not available to stream, rent or buy in {country} yet.»

#### Scenario: Account country

- GIVEN a signed-in user whose `pais` is `AR` opens `/movie/157336`
- THEN the page requests `providers/` and shows «Stream or rent … N options in Argentina»

#### Scenario: Without a session

- GIVEN a visitor without a session, whatever the browser region
- THEN no providers request is made and the page shows the link to log in

#### Scenario: Country without data

- GIVEN TMDB lists no providers for the viewer's country
- THEN the section reads «Not available to stream, rent or buy in {country} yet.»

### Requirement: Rating dialog

The dialog MUST offer a 1-10 star radiogroup operable by keyboard, an optional review up to 1000 characters with a counter, and the Watched notice when the title is not in Watched. Editing MUST preload, show the previous rating when it changes, offer «Remove rating», send only what changed, and delete the text apart when the user empties it. Every change MUST reload the lists.

### Requirement: Reviews

«Your review» MUST appear first when the user's rating has text, with Edit and Delete review (text only, after confirmation). The community reviews MUST be readable without a session, sortable (newest, oldest, highest, lowest), filterable by rating (9+ … below 5), titled «From the community (N)» or «Showing X of N», paginated with «Load more reviews», and say so when there are none.

#### Scenario: Filtering the community

- GIVEN three community reviews rated 10, 8 and 4
- WHEN the user picks «9 or higher»
- THEN the heading reads «Showing 1 of 3» and the request carries `nota_min=9`
