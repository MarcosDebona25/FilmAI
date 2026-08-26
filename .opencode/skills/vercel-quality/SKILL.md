---
name: vercel-quality
description: "Trigger: validar calidad, revisar UI, checklist frontend, accessibility, performance, interactions. Control de calidad post-implementación con reglas MUST/SHOULD/NEVER."
license: Apache-2.0
metadata:
  author: vercel
  version: "1.0"
---

## Activation Contract

Activate after frontend implementation is complete. This skill audits the output against production-quality rules for interactions, animation, layout, accessibility, content, performance, dark mode, hydration, and design.

## Hard Rules

- NEVER activate during discovery or design phases. This is a post-build quality gate.
- NEVER rewrite code directly. Report violations with severity (MUST fix / SHOULD fix).
- Every finding must reference a specific rule from the guidelines below.
- If a rule is not applicable, skip it — do not fabricate issues.

## Decision Gates

| Situation                      | Action                                                 |
| ------------------------------ | ------------------------------------------------------ |
| Implementation is incomplete   | Refuse. Quality check runs on finished UI only.        |
| Violation is cosmetic (SHOULD) | Flag as warning. Do not block.                         |
| Violation is functional (MUST) | Flag as error. Explain impact.                         |
| User asks for fix              | Point to the rule; let implementation skill handle it. |

## Execution Steps

1. Load the implementation output (HTML/CSS/JSX/TSX files).
2. Audit against each rule category in order.
3. Report findings as a table: Category | Rule | Severity (MUST/SHOULD) | File/Line | Issue | Fix.
4. NEVER-rule violations are blocking MUST findings.
5. Summarize: total violations, blockers, warnings.

## Quality Rules

### Interactions

- MUST: Full keyboard support per WAI-ARIA APG patterns
- MUST: Visible focus rings (`:focus-visible`; group with `:focus-within`)
- MUST: Manage focus (trap, move, return) per APG patterns
- NEVER: `outline: none` without visible focus replacement
- MUST: Hit target ≥24px (mobile ≥44px); if visual <24px, expand hit area
- MUST: Mobile `<input>` font-size ≥16px to prevent iOS zoom
- NEVER: Disable browser zoom (`user-scalable=no`, `maximum-scale=1`)
- MUST: `touch-action: manipulation` to prevent double-tap zoom
- MUST: Hydration-safe inputs (no lost focus/value)
- NEVER: Block paste in `<input>`/`<textarea>`
- MUST: Loading buttons show spinner and keep original label
- MUST: Enter submits focused input; in `<textarea>`, ⌘/Ctrl+Enter submits
- MUST: Keep submit enabled until request starts; then disable with spinner
- MUST: Accept free text, validate after—don't block typing
- MUST: Allow incomplete form submission to surface validation
- MUST: Errors inline next to fields; on submit, focus first error
- MUST: `autocomplete` + meaningful `name`; correct `type` and `inputmode`
- MUST: Warn on unsaved changes before navigation
- MUST: Compatible with password managers & 2FA; allow pasting codes
- MUST: No dead zones on checkboxes/radios; label+control share one hit target
- MUST: URL reflects state (deep-link filters/tabs/pagination/expanded panels)
- MUST: Back/Forward restores scroll position
- MUST: Links use `<a>`/`<Link>` for navigation (support Cmd/Ctrl/middle-click)
- NEVER: Use `<div onClick>` for navigation
- SHOULD: Optimistic UI; reconcile on response; on failure rollback or offer Undo
- MUST: Confirm destructive actions or provide Undo window
- MUST: Use polite `aria-live` for toasts/inline validation
- SHOULD: Ellipsis (`…`) for options opening follow-ups and loading states
- MUST: Generous touch targets, clear affordances; avoid finicky interactions
- MUST: Delay first tooltip; subsequent peers instant
- MUST: `overscroll-behavior: contain` in modals/drawers
- MUST: During drag, disable text selection and set `inert` on dragged elements
- MUST: If it looks clickable, it must be clickable

### Animation

- MUST: Honor `prefers-reduced-motion` (provide reduced variant or disable)
- SHOULD: Prefer CSS > Web Animations API > JS libraries
- MUST: Animate compositor-friendly props (`transform`, `opacity`) only
- NEVER: Animate layout props (`top`, `left`, `width`, `height`)
- NEVER: `transition: all` — list properties explicitly
- SHOULD: Animate only to clarify cause/effect or add deliberate delight
- SHOULD: Choose easing to match the change (size/distance/trigger)
- MUST: Animations interruptible and input-driven (no autoplay)
- MUST: Correct `transform-origin` (motion starts where it physically should)

### Layout

- SHOULD: Optical alignment; adjust ±1px when perception beats geometry
- MUST: Deliberate alignment to grid/baseline/edges — no accidental placement
- SHOULD: Balance icon/text lockups (weight/size/spacing/color)
- MUST: Verify mobile, laptop, ultra-wide
- MUST: Respect safe areas (`env(safe-area-inset-*)`)
- MUST: Avoid unwanted scrollbars; fix overflows
- SHOULD: Flex/grid over JS measurement for layout

### Content & Accessibility

- MUST: Skeletons mirror final content to avoid layout shift
- MUST: `<title>` matches current context
- MUST: No dead ends; always offer next step/recovery
- MUST: Design empty/sparse/dense/error states
- SHOULD: Curly quotes; avoid widows/orphans (`text-wrap: balance`)
- MUST: `font-variant-numeric: tabular-nums` for number comparisons
- MUST: Redundant status cues (not color-only); icons have text labels
- MUST: Accessible names exist even when visuals omit labels
- MUST: Use `…` character (not `...`)
- MUST: `scroll-margin-top` on headings; "Skip to content" link; hierarchical `<h1>`–`<h6>`
- MUST: Resilient to user-generated content (short/avg/very long)
- MUST: Locale-aware dates/times/numbers
- SHOULD: `translate="no"` on brand names, code tokens, identifiers
- MUST: Accurate `aria-label`; decorative elements `aria-hidden`
- MUST: Icon-only buttons have descriptive `aria-label`
- MUST: Prefer native semantics before ARIA
- MUST: Text containers handle long content (`truncate`, `line-clamp-*`, `break-words`)
- MUST: Flex children need `min-w-0` to allow truncation
- MUST: Handle empty states — no broken UI for empty strings/arrays

### Performance

- MUST: Track and minimize re-renders
- MUST: Profile with CPU/network throttling
- MUST: Batch layout reads/writes; avoid reflows/repaints
- MUST: Mutations (`POST`/`PATCH`/`DELETE`) target <500ms
- SHOULD: Prefer uncontrolled inputs; controlled inputs cheap per keystroke
- MUST: Virtualize large lists (>50 items)
- MUST: Preload above-fold images; lazy-load the rest
- MUST: Prevent CLS (explicit image dimensions)
- SHOULD: Critical fonts: `<link rel="preload" as="font">` with `font-display: swap`

### Dark Mode & Theming

- MUST: `color-scheme: dark` on `<html>` for dark themes
- SHOULD: `<meta name="theme-color">` matches page background
- MUST: Native `<select>`: explicit `background-color` and `color` (Windows fix)

### Design

- SHOULD: Layered shadows (ambient + direct)
- SHOULD: Crisp edges via semi-transparent borders + shadows
- SHOULD: Nested radii: child ≤ parent; concentric
- SHOULD: Hue consistency: tint borders/shadows/text toward bg hue
- MUST: Accessible charts (color-blind-friendly palettes)
- MUST: Meet contrast — prefer APCA over WCAG 2
- MUST: Increase contrast on `:hover`/`:active`/`:focus`

## Output Contract

Return a table with columns: Category | Rule | Severity (MUST/SHOULD) | File:Line | Issue | Fix.

NEVER-rule violations are reported as blocking MUST findings. Then summarize: total violations found, blockers (MUST violations), warnings (SHOULD violations).

> La auditoría de calidad finalizó. Entregá este reporte a la skill de implementación para que corrija los bloqueantes. Los warnings quedan a criterio del equipo.
