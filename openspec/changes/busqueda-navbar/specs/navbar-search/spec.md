# navbar-search Specification

## Purpose

The search field of the desktop navbar (13/11/2026): typing shows up to 5 suggestions of titles and people from `GET /api/catalogo/suggest/` (`tmdb-endpoints`), and Enter opens the Search page (`search-ui`) with the text. Mobile keeps the «Search» tab of `MobileTabs`. Follows the canvas artboard «Navbar · desktop».

## ADDED Requirements

### Requirement: Placement

On desktop (from 768 px) the navbar MUST show the search field on the right, before the account menu or the «Log in · Sign up» links, and MUST NOT show «Search» among the left links. Where the canvas decides the field does not fit (768–1023 px), it MUST show a magnifier button in the same place that expands the field in place and moves focus into it. Below 768 px the navbar MUST NOT show the field. On `/search` the navbar MUST NOT render the field.

#### Scenario: Desktop home

- GIVEN a 1440 px viewport on `/home`
- THEN the navbar's left links are «Home» and «Lists» (with a session)
- AND the search field sits before the account menu

#### Scenario: On the Search page

- GIVEN `/search?q=dune` on desktop
- THEN the navbar has no search field and the page's field has the focus

### Requirement: Suggestions

The field MUST ask for suggestions 250 ms after the last keystroke when the trimmed text has 2 characters or more, abort the previous request, show an answer only if its text is still the field's text, and keep answers per language and text for the visit. While a new answer loads, the previous list MUST stay. The list MUST show the suggestions in the order received and end with «See all results for “text”». A title MUST open its title page without `from`; a person MUST open `/search?person={id}&role={rol}`; Enter with no active option and «See all results» MUST open `/search?q={text}` with no other filter. After navigating, the field MUST be cleared and the list closed. An error MUST close the list without a message.

#### Scenario: Typing a name

- GIVEN the user types «nol» and then «nolan» within 250 ms
- THEN only `suggest/?q=nolan` is requested
- AND «Christopher Nolan · Director» is among the options

#### Scenario: Enter goes to Search

- GIVEN the field holds «dune» and no option is active
- WHEN the user presses Enter
- THEN the page becomes `/search?q=dune`

### Requirement: Accessible combobox

The field MUST follow the ARIA 1.2 combobox with list autocomplete and manual selection: `role="combobox"`, `aria-autocomplete="list"`, `aria-expanded`, `aria-controls` to a `role="listbox"`, and `aria-activedescendant` with the active option's id. Options MUST have `role="option"`, a stable id, `aria-selected` on the active one and an accessible name that includes the type and year, or the role. ↓ and ↑ MUST move the active option (past the last, back to the field); Enter MUST follow it; Escape MUST close the list and a second Escape clear the field; Tab MUST close it without choosing; Alt+↓ MUST reopen the last list. Typing MUST NOT activate an option. A polite live region, present from the start, MUST announce how many suggestions arrived, or that there are none.

#### Scenario: Keyboard only

- GIVEN suggestions for «dune» are open
- WHEN the user presses ↓ twice and Enter
- THEN the second option's page opens
- AND while it was active, the field's `aria-activedescendant` pointed to it

#### Scenario: Count is announced

- GIVEN the user types «chihiro»
- WHEN 2 suggestions arrive
- THEN the live region reads «2 suggestions»

### Requirement: Shortcut

On desktop, `/` MUST focus the navbar field (on `/search`, the page's field) unless the focus is in an editable element or a dialog is open; then it MUST type normally. The field MUST show a «/» hint while empty and unfocused.

#### Scenario: Typing a slash in a review

- GIVEN the focus is in the review text area
- WHEN the user types «/»
- THEN the character is typed and the focus stays there
