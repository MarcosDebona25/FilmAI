# Design: Perfil, Settings y Mis reseñas según el canvas

## 1. Who talks to whom

```
Browser (/profile, /settings, /my-reviews, /terms · "use client", session cookie)
   │ HTTP + JWT cookie + Accept-Language
   ▼
Django
   ├── profile/                      GET · PUT (name, last name, username, avatar)
   ├── avatars/                      the avatar catalog
   ├── auth/username-available/      live availability while editing
   ├── profile/change-password/      password change (logs out everywhere)
   ├── auth/password/reset/          Google accounts without a local password
   ├── preferences/                  language, notifications, public profile (theme kept, not offered)
   ├── account/deactivate/           deactivation
   └── reviews/mias/                 NOW with filters ──SQL──▶ Postgres
       reviews/{id}/ · reviews/{id}/texto/   edit and delete (C-08, title page dialogs)
```

Everything but the filters already exists; the screens are rebuilt over the same API.

## 2. Filters on `reviews/mias/`

| Param                   | Values                                                                                               | Default      |
| ----------------------- | ---------------------------------------------------------------------------------------------------- | ------------ |
| `q`                     | text, trimmed, up to 100; matches the canonical title or a translation, case- and accent-insensitive | —            |
| `texto`                 | `con`, `sin`                                                                                         | both         |
| `clase`                 | `movie`, `tv`                                                                                        | both         |
| `nota_min` / `nota_max` | 1–10 (same as the community, C-07)                                                                   | —            |
| `orden`                 | `fecha-desc`, `fecha-asc`, `nota-desc`, `nota-asc`                                                   | `fecha-desc` |

- `clase` and not `tipo`: `id_tmdb` + `tipo` already turn the response into one rating, and half of that pair is a 400 on purpose.
- Sorting by rating reuses the unique key of C-07 (`Cast(valor, bigint) × 10⁹ + id`) so the cursor stays stable.
- The page adds `total` (with filters) and `total_propias` (without them), for «View N results» and the empty state.

## 3. Screens

| Screen     | Canvas                                                                                                                                             | Built from                                                                                                                           |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Profile    | header, Personal details (`dl`), Edit details (form), Password (collapsible), mobile «Your account» list, avatar dialog/sheet, logout confirmation | `app/profile/page.tsx` logic (guard, availability, reset for Google accounts), `DialogShell` and `ConfirmDialog` from the title page |
| Settings   | breadcrumb, Language (EN                                                                                                                           | ES), Privacy (switch), Notifications (switches), Legal, Account + alert dialog                                                       | `AccountProvider` preferences; a `Switch` component (`role="switch"`) |
| My reviews | breadcrumb, search + four filters (selects on desktop, sheet with chips on mobile), list with folded text, Edit and «More actions»                 | `RatingDialog` and `ConfirmDialog` (C-08), `useDesborde`, `DialogShell`                                                              |
| Terms      | breadcrumb Profile › Settings › Terms with a session on desktop                                                                                    | —                                                                                                                                    |

- **Dark only**: the theme selector leaves Settings and `AccountProvider` stops applying «light», since the app's tokens exist only for dark. The `tema` preference stays in the API.
- **State in the URL** for My reviews filters, like Search (`q`, `texto`, `clase`, `nota`, `orden`), so the title page's «Ratings & reviews» crumb returns to the same filtered list.
- **All text from the catalog**: the hardcoded Spanish in Profile and My reviews goes away.

## 4. Delivery

Five PRs against `develop/ui-design`, each after the previous one is merged:

1. SDD and docs.
2. Backend: filters on `reviews/mias/`.
3. Settings (and the Terms breadcrumb, and dark only).
4. Profile.
5. My reviews; closes the change.
