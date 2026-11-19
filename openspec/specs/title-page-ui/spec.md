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

The page MUST show the backdrop band with the site navbar over it, the poster, the title (sized by length like the Home Hero), the tagline, the type, the year, the runtime (movies) or seasons and episodes (shows), the TMDB rating with its votes as «★ 8,5», the genres and the synopsis (folded only when it overflows). While the detail loads, the page MUST show a static skeleton (no pulse or shimmer animation, 18/10/2026) with the shape of the backdrop, poster, title, data, actions, genres, synopsis and three reviews. «Director and cast» MUST list the directors — for shows, the creators as «Created by» — and the cast with characters, folding over 10. Each name MUST link to Search filtered by that person (`/search?person={id}&role=director` for directors and creators, `role=actor` for the cast; 15/11/2026), the same destination as the person's row in the navbar search, with a faint always-on underline so it reads as a link on touch screens (19/11/2026); the character is not part of the link. A person without a TMDB `id` in `credits/` MUST stay as plain text.

#### Scenario: From a name to the person's filmography

- GIVEN `/movie/157336`, whose credits list Christopher Nolan (TMDB id 525) as director
- WHEN the user follows his name in «Director and cast»
- THEN Search opens at `/search?person=525&role=director` with the chip «Christopher Nolan · Director»

#### Scenario: A show

- GIVEN `/tv/1396`
- THEN it shows «5 seasons · 62 episodes» and «Created by Vince Gilligan»

### Requirement: Actions

Without a session the actions MUST be replaced by «Log in to rate or save», linking to the login with `?next=` back to the page; a signed-in user MUST NOT see it while the page loads. With a session: Rate (or «★ N» with «Your rating: N out of 10. Edit» as accessible name), Favorite (an `aria-pressed` toggle over the lists API, whose heart fills with the accent color when on), the status button and «Add to list» with the user's own lists and inline creation (PR 4, 16/11/2026). The status button shows «Status» with a + when the title has none, and the name of the status (Watchlist, Watching or Watched) otherwise; it opens a menu (a bottom sheet on phones) with the three statuses as radios, the current one checked, and «Remove status». Picking one MUST be optimistic and call `PUT /api/lists/status/`; if it fails the button MUST go back and an error toast («Couldn't update the status. Try again.», no Undo) MUST show. A successful change MUST show a toast «Moved to Watching» with Undo for 6 s (a polite live region that also says «Undo available for 6 seconds»); Undo goes back one step with the same endpoint and shows «Back to Watchlist» for 2 s without Undo. A second change replaces the toast, and leaving the page closes it. Toasts are at the top center on desktop and at the bottom, 12 px over the tab bar, on phones. Rating a title in Watchlist or Watching moves it to Watched (the backend does it) and the toast says «Rated ★ 8 · Moved to Watched» with Undo, which restores the previous status and keeps the rating; rating one already in Watched (or with no status) says «Rated ★ 8» without Undo. Removing a status never touches the rating.

#### Scenario: Signed in while the detail loads

- GIVEN a signed-in user whose lists arrive before the title detail
- THEN the page shows the skeleton and no «Log in to rate or save»

While a status, Favorite or list change is saving, every action (the status button, Rate, Favorite, the list rows and the toast's Undo) MUST be disabled; a tap MUST NOT be silently dropped. After 200 ms of saving a «Saving…» toast with a spinner (no Undo) replaces the current toast; the usual toast or the error toast replaces it when the server answers. A save that answers within 200 ms MUST show no «Saving…» toast.

#### Scenario: Status with Undo

- GIVEN a title in Watchlist
- WHEN the user picks Watching in the status menu
- THEN the button reads «Watching» at once and a toast says «Moved to Watching» with Undo
- AND pressing Undo returns the title to Watchlist and shows «Back to Watchlist»

#### Scenario: Rating moves the title to Watched

- GIVEN a title in Watchlist
- WHEN the user rates it 8
- THEN the toast says «Rated ★ 8 · Moved to Watched» with Undo, the button reads «Watched» and Undo restores Watchlist keeping the rating

### Requirement: More like this title

The title page MUST show, after «Director and cast» and before the reviews, a
horizontal row «More like {title}» with the results of
`GET /api/catalogo/{tipo}/{id}/similar/`, with and without a session. Each
card MUST show its type. The request MUST start only when the row is about
400 px from the viewport, never with the detail: the detail MUST NOT wait for
it, and it MUST start after the credits request ends. Empty results, an answer
without `results` or an error MUST hide the row without an error message. The
row is the Home row (`MediaRow`) with its skeletons while loading, and is not
kept for the visit, because with a session it depends on «Vistas» (canvas,
section 14, 15/11/2026).

#### Scenario: Deferred load

- GIVEN a visitor opens `/movie/157336` and does not scroll
- THEN no request to `/similar/` is made

#### Scenario: Scrolling down

- GIVEN the visitor scrolls toward the reviews
- WHEN the row nears the viewport
- THEN up to 20 cards appear, movies and shows, each marked with its type
- AND their links keep the origin of the current page

### Requirement: Where to watch

Below the genres the page MUST show, once the detail is loaded, the streaming availability in the viewer's country (added 18/10/2026; it consumes `GET /api/catalogo/{movie,tv}/{id}/providers/` from `tmdb-endpoints`). Only with a session, in the account's `pais` (27/10/2026, issue #124). Without a session it MUST NOT be requested; in its place the page MUST show the link «Log in to see where to watch it in your country» to `/login?next=<current path>`. A failed request MUST also hide it, because it is not critical content. While it loads it MUST show a static placeholder with `role="status"`.

With providers, the page MUST show a button line «Stream or rent» + up to four logos + «N options in {country}» (plural-aware, country name in the active language) that ends in a chevron inside a circle (filled with the light colour on hover). The whole line is one button with `aria-expanded` and a 44 px tap area (canvas, section 17, 15/11/2026). It opens a modal dialog on desktop and a bottom sheet on mobile, with the same content («Where to watch», `role="dialog"`, `aria-modal`, labelled by its title), closed with Escape, its 44 px close button or a tap on the backdrop outside the box (19/11/2026), after which focus returns to the line (through a ref to the button, not to whatever had the focus: in Safari a click does not focus it and the `body` would get it). The content is one surface with hairlines between the non-empty groups Stream, Free, Rent and Buy, in that order, and 40 px logos without names (the name goes in the accessible label and the tooltip). Free joins TMDB's `free` and `ads`, appears only when it has data, and its heading reads «Free (with or without ads)» / «Gratis (con o sin publicidad)» (16/11/2026). Logos MUST NOT be links: TMDB gives no per-platform URLs, so the panel has a single «See all options on TMDB» link (new tab) when `enlace` is present. A logo missing from TMDB MUST be replaced by the platform's initial. The panel MUST carry the JustWatch attribution «Data by JustWatch», linking to justwatch.com; this attribution is a condition of TMDB's data and MUST NOT be removed. With no providers for the country it MUST say «Not available to stream, rent or buy in {country} yet.»

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
