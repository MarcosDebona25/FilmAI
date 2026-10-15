# Profile UI

## Purpose

The signed-in user's own screens, built from the canvas (15/10/2026): Profile (`/profile`), Settings (`/settings`) and Ratings & reviews (`/my-reviews`). Ratings & reviews consumes `reviews-api`. All visible text comes from the i18n catalog (`i18n-core`).

## Requirements

### Profile

`/profile` MUST show a header (avatar, name in the display typeface, `@username`, email and sign-up date), «Personal details» as a description list, and «Password» as a collapsible section (`aria-expanded`). «Edit profile» MUST replace Personal details with «Edit details»: first name, last name and username editable; email, birth date and gender read-only with a lock and a hint. Accounts without a local password (Google) MUST be offered an emailed link instead of the password form. On mobile, a «Your account» list MUST link to Ratings & reviews, Settings and Terms, and «Log out» MUST ask for confirmation with the same text as the desktop account menu.

### Avatar selection

While editing, a keyboard-accessible «Change avatar» control MUST open a dialog (a card on desktop, a sheet on mobile) with every active avatar as a radio group, focus starting on the selected one. «Save» MUST apply the choice to the profile draft and close; «Cancel» or Escape MUST discard it. Only saving the profile MUST persist the avatar and update the navbar.

### Unsaved changes

Canceling or following a same-tab link or browser history traversal with a modified draft MUST open «¿Salir sin guardar?». Continuing editing MUST preserve all fields and avatar. Confirming MUST discard the draft and complete the requested action. An unchanged or reverted draft MUST not prompt. Reloading or closing the tab MUST use the native browser warning.

### Username availability

Availability checks MUST ignore canceled responses and announce «Checking», «Available» or «Not available» as text, not only color. Errors saving MUST preserve the draft.

### Settings

`/settings` MUST show the breadcrumb Profile › Settings («‹ Profile» on mobile), Language (EN · ES, at anchor `t-idioma`), Privacy, Notifications as switches (`role="switch"`), Legal and Account. The app is dark only: there is no theme selector, and a saved «light» theme MUST still render dark. The account locale is persisted before the cookie/render change; a failed save preserves the old locale. Footer language links navigate with a real anchor/Link and remain available on mobile.

### Deactivation warning

The confirmation MUST be an `alertdialog` with focus on Cancel and say: «Esta acción es irreversible. Se cerrarán todas tus sesiones y no podrás volver a iniciar sesión ni reactivar tu cuenta. Asegurate de querer dar de baja la cuenta antes de continuar.» Canceling MUST not call the API. A failed request MUST leave the dialog available to retry and the account active.

### Ratings & reviews

`/my-reviews` MUST show the breadcrumb Profile › Ratings & reviews («‹ Profile» on mobile) and a list where each row has the poster (80 × 120 desktop, 56 × 84 mobile, a same-size placeholder when absent or failed), the title linking to its page with `?from=reviews`, then «★ rating», the type and «Rated on {date}». Ratings MUST read «★ number», never «X/10»; the accessible label says «Your rating: N out of 10». A review MUST be clamped to three lines with «Read more» / «Read less» only when it actually overflows at the current width. A rating without text MUST show a dashed «Add review» link to its title page.

#### Filters

A title search (applied 350 ms after the last key, up to 100 characters) and four filters MUST live in the URL (`q`, `review=with|without`, `type=movie|tv`, `rating=9…5|lt5`, `sort=newest|oldest|highest|lowest`) and be sent to `reviews/mias/` (`texto`, `clase`, `nota_min`/`nota_max`, `orden`). On desktop they are four labelled selects plus «Clear filters»; on mobile, a «Filters and sort» button with a count of active filters opens a sheet whose choices apply at once and whose main button reads «View N results», and each active filter shows as a removable chip next to «Sort: …». Clearing MUST keep the sort. The title page's «Ratings & reviews» crumb MUST return to the last filtered list of the tab.

#### States

Loading MUST show placeholder rows with a status label. A user with no ratings at all (`total_propias = 0`) MUST see an invitation to search instead of the filters; filters with no matches MUST say so and offer «Clear filters». A failed first load MUST offer retry. Further cursor pages MUST load on reaching the end and through a keyboard-accessible «Load more ratings» button; duplicate IDs MUST not repeat rows, and a page failure MUST keep the loaded rows and offer retry.

#### Actions

On desktop each row has «Edit» and a «More actions» menu (`role="menu"`, arrow keys, Escape returns focus) with «Delete review» (only when there is text) and «Remove rating»; on mobile one button opens a sheet with «Edit rating and review», «Delete review» and «Remove rating». They MUST use the title page's dialogs: the rating dialog preloaded with the rating and text, and confirmations that name what is lost, with the same toasts as the title page. An edited row stays in place even if it no longer matches the filters. Removing a rating MUST remove its row on success only and move focus to the page heading.

#### Scenario: Deleting text from an own row

- WHEN the user confirms text deletion
- THEN the row keeps its rating and offers «Add review»
- AND Watched membership is unchanged

#### Scenario: Returning from a title page

- GIVEN the list filtered by «TV shows» and «8 or higher»
- WHEN the user opens a title and follows the «Ratings & reviews» crumb
- THEN the same filtered list is shown
