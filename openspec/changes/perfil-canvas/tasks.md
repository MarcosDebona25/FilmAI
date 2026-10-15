# Tasks: Perfil, Settings y Mis reseñas según el canvas

## Review Workload Forecast

| Field                   | Value                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------ |
| Estimated changed lines | ~1,800 (without generated catalogs or `graphify-out/`)                               |
| 400-line budget risk    | High as a single PR                                                                  |
| Chained PRs recommended | Yes — five, each against `develop/ui-design`                                         |
| Delivery strategy       | ask-on-risk                                                                          |
| Chain strategy          | Sequential: each PR starts from `develop/ui-design` after the previous one is merged |

## Phase 0: SDD (PR 1)

- [x] 0.1 `proposal.md`, `design.md`, `tasks.md`
- [x] 0.2 Decisions validated with the user (15/10/2026): dark only for now; keep the public-profile switch
- [x] 0.3 `docs/decisiones.md` entry
- [x] 0.4 `docs/05_Plan_de_Desarrollo.md`: these screens now built by Gonza

## Phase 1: Backend (PR 2)

- [x] 1.1 RED → GREEN: `q` matches canonical and translated titles, ignoring case and accents
- [x] 1.2 RED → GREEN: `texto=con|sin`, `clase=movie|tv`, `nota_min`/`nota_max`
- [x] 1.3 RED → GREEN: `orden` with a stable cursor (rating sorts use the unique key)
- [x] 1.4 RED → GREEN: `total` and `total_propias`; `tipo` alone still 400; invalid values 400 with stable codes
- [x] 1.5 Spec `reviews-api` updated

## Phase 2: Settings (PR 3)

- [ ] 2.1 `Switch` component (`role="switch"`) with tests
- [ ] 2.2 Settings per the canvas: breadcrumb or back link, Language, Privacy, Notifications, Legal, Account + alert dialog; no theme selector
- [ ] 2.3 `AccountProvider` keeps the app dark whatever the saved theme
- [ ] 2.4 Terms: desktop breadcrumb with a session
- [ ] 2.5 Tests and `e2e/preferencias.spec.ts`

## Phase 3: Profile (PR 4)

- [ ] 3.1 Header, Personal details, Edit details with availability, read-only fields
- [ ] 3.2 Avatar dialog (sheet on mobile) on `DialogShell`
- [ ] 3.3 Collapsible password form; reset for accounts without a local password
- [ ] 3.4 Mobile «Your account» list and logout confirmation
- [ ] 3.5 Tests, `e2e/perfil.spec.ts` and `e2e/hotfix-perfil.spec.ts`

## Phase 4: My reviews (PR 5)

- [ ] 4.1 `lib/my-reviews.ts`: URL ⇄ filters ⇄ API (unit tests)
- [ ] 4.2 Desktop filters and list; mobile sheet with chips and «View N results»
- [ ] 4.3 Edit and «More actions» with the title page's dialogs; «Add review» link; title links with `?from=reviews`
- [ ] 4.4 Tests and `e2e/mis-resenas.spec.ts`
- [ ] 4.5 Spec `profile-ui`, doc 05 (✅), delete `openspec/changes/perfil-canvas/`
