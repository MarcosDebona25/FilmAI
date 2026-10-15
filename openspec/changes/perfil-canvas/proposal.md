# Proposal: Perfil, Settings y Mis reseñas según el canvas (P-02, P-03, P-06)

## Intent

`/profile`, `/settings` and `/my-reviews` were built before the canvas («9 · Profile and settings» and «6 · Ratings & reviews») and do not match it. Doc 05 marks them «🔁 Rehacer». They also have bugs found on 15/10/2026:

- Profile and My reviews mix languages: with the interface in English they show «Mi perfil», «Editar perfil», «Mis reseñas», and Spanish sentences with English dates. Part of their text is hardcoded outside the i18n catalog (AGENTS.md §10).
- My reviews leaves two loading cards at the bottom forever, has no breadcrumb, no filters and no link to the title page, and still uses the old rating modal instead of the title page's dialogs (C-08).
- Settings uses checkboxes where the canvas draws switches, and offers a light theme that is broken across the app (only the background and the accent change; the app's own tokens exist only for dark).

These screens were Marcos's in the 13/10/2026 split; on 15/10/2026 the user took them over (Marcos had not started them).

## Scope

### In Scope

Backend:

- Filters on `GET /api/reviews/mias/` for the list: title search, with or without review, type, rating and sort, keeping the cursor pagination and returning the filtered and unfiltered totals. The parameter names must not collide with `id_tmdb` + `tipo`, which turn the response into a single rating.

Frontend:

- **Profile** (desktop and mobile): header with avatar, name, `@username`, email and «Member since»; «Personal details» as a list; «Edit profile» switches to an edit form (first name, last name, username with live availability, read-only email, birth date and gender) with Cancel / Save changes; avatar picker as a dialog (a sheet on mobile) opened from the avatar while editing; «Password» as a collapsible form with the logout warning. On mobile, a «Your account» list (Ratings & reviews, Settings, Terms, Log out with confirmation).
- **Settings** (desktop and mobile): breadcrumb Profile › Settings (back link on mobile); Language (EN | ES); Privacy (public profile) as a switch, kept on the user's request though the canvas does not draw it; Notifications as switches; Legal → Terms; Account → Deactivate with an alert dialog. **No theme selector** for now (decided 15/10/2026): the app forces dark even if an account has «light» saved, until the light palette exists.
- **My reviews** (desktop and mobile): breadcrumb Profile › Ratings & reviews; search by title; Show (all, with review, no review), Type, Rating and Sort (desktop selects; on mobile a «Filters and sort» sheet with chips of the active filters and «View N results»); list with poster, title linking to the title page (`?from=reviews`), «★ N · type · Rated on date», text folded after three lines, «Add review» when there is none; Edit plus a «More actions» menu (Delete review, Remove rating), reusing the title page's dialogs.
- **Terms**: the desktop breadcrumb Profile › Settings › Terms with a session (the pending item in doc 05).

### Out of Scope

- The light theme (decided 15/10/2026: dark only for now).
- Making reviews or lists private: `perfil_publico` is stored but changes nothing yet.
- Lists (L-02, L-03), still Marcos's.

## Risks

| Risk                                                                                             | Mitigation                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Rewriting screens that already have tests and e2e (`e2e/perfil.spec.ts`, Marcos's account flows) | Keep the behaviour (unsaved-changes guard, availability check, password reset for Google accounts, deactivation); rewrite the tests that assert the old layout and say so in each PR |
| `tipo` already means «single rating» on `reviews/mias/`                                          | Use `clase` for the type filter; a test proves `tipo` alone still answers 400                                                                                                        |
| A saved «light» theme would break the app once the selector disappears                           | `AccountProvider` applies dark always until the light palette exists                                                                                                                 |
