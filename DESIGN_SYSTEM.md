# Kivi Design System
## Canonical Reference — v1.0

**Document class:** Normative design specification
**Status:** Approved for implementation
**Document owner:** Basavaraj A. Naduvinamani
**Implementation targets:** `frontend/templates/` and `frontend/static/styles.css`
**Source contracts:** `PART_TWO_SPEC.md` §13 and `coordination/INTEGRATION_CONTRACT.md` v1.2

---

## 1. Document Authority and Scope

This document is the single canonical design specification for the Kivi local web application. It governs every material product and visual decision across all six surfaces.

### 1.1 Source hierarchy (descending authority)

1. `coordination/INTEGRATION_CONTRACT.md` v1.2 — schema, routes, typed statuses, field names
2. `backend/kivi/schemas.py` and `backend/kivi/enums.py` — exact Pydantic models and StrEnum values
3. `backend/kivi/app.py` — implemented FastAPI routes
4. `frontend/router.py` — implemented HTMX routes
5. `PART_TWO_SPEC.md` — product scope, data model, supported actions, evaluation contract
6. This document — visual system, component behavior, microcopy rules
7. HeyKivi visual reference study — palette and tone reference only.
8. `stitch-design/*.DESIGN.md` — secondary visual token references; no product authority

Product contracts always override visual references. Visual references are consulted for palette, type tone, and component intent only.

### 1.2 Application context

Kivi is served as a local FastAPI web application rendered in a standard Chromium-based browser at a 1440 x 900 desktop baseline. It is not a native Windows application. Native OS window chrome (title bar, minimize/maximize/close controls, drag region) is managed entirely by the operating system and browser; no frontend specification of those elements is appropriate or possible.

### 1.3 Normative language

This document uses RFC 2119 conventions. MUST denotes an absolute requirement. MUST NOT denotes an absolute prohibition. SHOULD denotes a strong recommendation. SHOULD NOT denotes a strong discouragement. MAY denotes an option.

### 1.4 Traceability requirement

Every material product or visual decision described in this document must be traceable to an existing route in `backend/kivi/app.py`, a field in `backend/kivi/schemas.py`, an enum value in `backend/kivi/enums.py`, or a purely visual treatment that does not imply new backend behavior.

---

## 2. Product-Design Principles

### 2.1 Quiet dignity

Micro-interactions MUST be cushioned, gentle, and unhurried. No aggressive glows, pulsing UI elements, or abrupt transforms. Transitions for interactive state changes MUST fall between 120 ms and 250 ms. A loading-pulse animation MAY use a 1,200 ms cycle. All easing MUST use `ease-out` or `cubic-bezier(0.22, 1, 0.36, 1)`.

### 2.2 Literary tone

Section headings, greeting text, and empty-state prose SHOULD use editorial sentence case, lowercase section labels, and conversational register. Kivi speaks as a precise, attentive colleague — not a system terminal.

### 2.3 Organic restraint

Colors, borders, and controls MUST feel warm and grounded — drawn from near-black canvas, warm cream ink, and a restrained lime-green accent. Saturation is always muted outside the primary accent. No synthetic neon, large solid-green blocks, or cyberpunk gradients.

### 2.4 Calm reassurance

Status indicators and lifecycle labels MUST be rendered unobtrusively. Destructive actions MUST be visually subdued at rest and reveal their weight only at hover or keyboard focus. No element should alarm a user before they have acted.

### 2.5 Truthfulness first

Every rendered value MUST originate from a real backend response. No value MAY be invented, estimated, or hard-coded in a production template. Empty states MUST say so plainly. Unavailable services MUST say so plainly without exposing internal implementation details.

### 2.6 Provenance as a first-class interaction

Take IDs are the primary provenance mechanism. They MUST be rendered as interactive elements that open the Evidence Drawer, not as decorative labels. Every Take ID chip MUST be keyboard-focusable and activatable.

### 2.7 Reduced-motion respect

All CSS animations and transitions MUST be suppressed when `prefers-reduced-motion: reduce` is set:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 3. Truthfulness and Contract-Alignment Rules

These rules take precedence over every aesthetic preference.

| ID | Rule |
|---|---|
| T-1 | Every field rendered in a template MUST correspond to a field in `schemas.py` or the integration contract. |
| T-2 | Query-status badges MUST use exact `QueryStatus` StrEnum values: `ANSWERED`, `NO_EVIDENCE`, `NEEDS_CLARIFICATION`, `CONFLICTING_EVIDENCE`, `SERVICE_ERROR`. |
| T-3 | Epistemic status values MUST match `EpistemicStatus`: `PROPOSED`, `APPROVED`, `REJECTED`, `CONDITIONAL`, `UNRESOLVED`. |
| T-4 | Lifecycle status values MUST match `LifecycleStatus`: `ACTIVE`, `SUPERSEDED`, `INVALIDATED`, `TOMBSTONED`. |
| T-5 | `retrieval_latency_ms` MUST be labeled "retrieval" when displayed. `end_to_end_latency_ms` MUST be labeled "completed in". Both are real measurements from `AskResponse`. |
| T-6 | `input_tokens` and `output_tokens` MUST only be displayed when both are non-null. When either is null the token line is omitted entirely. |
| T-7 | `estimated_cost_usd` is nullable. It MUST NOT be displayed when null. |
| T-8 | Import result counts MUST come from `CorpusImportResult` fields: `total`, `ingested`, `memories_created`, `unscoped`, `failed`. |
| T-9 | Evaluation metrics MUST be read from the live `EvaluationRunRead` response. No prior-run history, fabricated pass rates, or hard-coded values may appear. |
| T-10 | Error messages MUST NOT expose raw Python exception class names, stack traces, internal route paths, database error codes, or model provider API keys. |
| T-11 | The Inbox MUST NOT preselect a project, auto-detect scope from Take content, or display detected-entity metadata not present in `TakeRead`. |
| T-12 | The correction form MUST only appear on memories whose `lifecycle_status` is `ACTIVE`. |
| T-13 | The Revoke action calls `DELETE /htmx/takes/{take_id}`. It MUST NOT appear on a Take whose `is_deleted` is `true`. |
| T-14 | Import `error_type` values are mapped through the whitelist in §20.3 before display. Unknown values render as "processing error". Raw detail strings from unknown error types MUST NOT be rendered. |
| T-15 | No production template may contain a hard-coded Take ID, project name, or timestamp. This restriction does not apply to deterministic evaluation fixtures or automated test files. |
| T-16 | The frontend MUST branch on the `status` field of `AskResponse`, not on the HTTP status code alone. |

---

## 4. Color Tokens

The palette is derived from the authentic HeyKivi visual language. It operates on a near-black ground with a single vibrant lime-green accent. Pure black and pure white are avoided in favor of warm-neutral extremes.

### 4.1 Surface scale

| Token | Hex | Role |
|---|---|---|
| `--color-depth` | `#060a05` | Deepest layer — behind the page for visual depth only |
| `--color-canvas` | `#0b0e0a` | Global page background |
| `--color-surface-1` | `#121710` | Header bar, structural scaffolding |
| `--color-surface-2` | `#1a2016` | Cards, panels, main interaction surface |
| `--color-surface-3` | `#1e2519` | Inset wells, input fields, nested containers |
| `--color-surface-active` | `#1e2d18` | Selected card tint, active scope highlight |

### 4.2 Text scale

| Token | Hex | Role |
|---|---|---|
| `--color-ink-primary` | `#f4f1e6` | Headings, active text, primary content |
| `--color-ink-secondary` | `#b9b6a8` | Body prose, supporting commentary |
| `--color-ink-muted` | `#7d7b6f` | Metadata labels, secondary captions |
| `--color-ink-dim` | `#5a5855` | Timestamps, inactive navigation labels |
| `--color-ink-placeholder` | `#4e4c46` | Input placeholder text |

### 4.3 Accent and semantic scale

| Token | Value | Role |
|---|---|---|
| `--color-accent` | `#a8e063` | Primary interactive accent: buttons, focus rings, APPROVED/ACTIVE indicators |
| `--color-accent-on` | `#1b1d18` | Text on accent-filled surfaces |
| `--color-accent-dim` | `#256b2f` | Accent container backgrounds, badge fills |
| `--color-accent-border` | `rgba(168,224,99,0.25)` | Active card borders, selected outlines |
| `--color-accent-surface` | `rgba(168,224,99,0.10)` | APPROVED/ACTIVE badge background |
| `--color-rose` | `#ff6b6b` | Destructive hover text, error text |
| `--color-rose-surface` | `rgba(255,107,107,0.10)` | Destructive hover fill |
| `--color-sand-surface` | `rgba(205,175,120,0.12)` | CONDITIONAL epistemic badge background |
| `--color-sand-text` | `#c9a96e` | CONDITIONAL epistemic badge text |
| `--color-amber-surface` | `rgba(232,137,43,0.12)` | PROPOSED epistemic badge background |
| `--color-amber-text` | `#e8892b` | PROPOSED epistemic badge text |
| `--color-steel-surface` | `rgba(255,255,255,0.05)` | SUPERSEDED, TOMBSTONED badge background |
| `--color-steel-text` | `#7d7b6f` | SUPERSEDED, TOMBSTONED badge text |
| `--color-conflict-surface` | `rgba(255,107,107,0.08)` | CONFLICTING_EVIDENCE claim background |
| `--color-conflict-text` | `#ff9b7a` | CONFLICTING_EVIDENCE claim text |
| `--color-border-hairline` | `rgba(255,255,255,0.07)` | Standard card and panel borders |
| `--color-border-divider` | `rgba(255,255,255,0.06)` | Section dividers, footer separators |

### 4.4 Status color supplement

Status meaning MUST NEVER rely on color alone. Every status MUST carry a visible text label. Color is a supplemental signal only.

| Status | Supplemental prefix | Color token |
|---|---|---|
| ANSWERED | (none) | — |
| NO_EVIDENCE | em-dash | `--color-amber-text` |
| NEEDS_CLARIFICATION | ? | `--color-ink-secondary` |
| CONFLICTING_EVIDENCE | left-right arrow | `--color-conflict-text` |
| SERVICE_ERROR | ! | `--color-rose` |

---

## 5. Typography Tokens

Three typeface voices are in use. The HeyKivi brand fonts (Fraunces, Switzer, Matter SemiMono) are specified in the brand reference but are not yet committed to the repository with licence files. Until they are, this specification uses cross-platform system stacks as the working baseline. Vendored custom fonts are an optional future enhancement that may be adopted after their files and licences are committed to `frontend/static/fonts/`.

### 5.1 Font stacks

| Voice | Stack | Token |
|---|---|---|
| Editorial (serif) | `Georgia, "Times New Roman", serif` | `--font-editorial` |
| Utilitarian (sans) | `system-ui, -apple-system, "Segoe UI", sans-serif` | `--font-sans` |
| Monospace | `ui-monospace, "SFMono-Regular", Consolas, monospace` | `--font-mono` |

### 5.2 Type scale

| Token | Family | Size | Weight | Line height | Letter spacing |
|---|---|---|---|---|---|
| `--type-display` | editorial | 32px | 400 | 40px | -0.02em |
| `--type-headline-lg` | editorial | 26px | 400 | 34px | -0.015em |
| `--type-headline-md` | editorial | 20px | 400 | 28px | -0.01em |
| `--type-headline-sm` | editorial | 18px | 400 | 24px | 0 |
| `--type-body-lg` | sans | 15px | 400 | 24px | 0 |
| `--type-body-md` | sans | 13px | 400 | 20px | 0 |
| `--type-body-sm` | sans | 12px | 400 | 17px | 0 |
| `--type-label-cat` | sans | 11px | 500 | 16px | 0.06em |
| `--type-label-nav` | sans | 13px | 400 | 18px | 0 |
| `--type-label-action` | sans | 13px | 500 | 16px | 0 |
| `--type-label-pill` | sans | 11px | 400 | 16px | 0 |
| `--type-code-id` | mono | 11px | 400 | 14px | 0.03em |
| `--type-code-ts` | mono | 11px | 400 | 14px | 0.01em |

### 5.3 Monospace use restriction

`--font-mono` MUST be used exclusively for: Take IDs, memory IDs as technical references, evaluation run IDs, and ISO timestamps in evidence metadata.

`--font-mono` MUST NOT be used for headings, body prose, navigation labels, status text, error messages, or any general UI copy.

---

## 6. Spacing and Sizing Tokens

### 6.1 Spacing scale

| Token | Value | Use |
|---|---|---|
| `--space-xs` | 4px | Icon margins, micro-gaps |
| `--space-sm` | 8px | Internal pill padding, tight gaps |
| `--space-md` | 14px | Between adjacent cards, form row gaps |
| `--space-lg` | 20px | Card internal padding, section breathing |
| `--space-xl` | 32px | Between major page sections |
| `--space-gutter` | 16px | Page horizontal gutter |
| `--space-margin` | 24px | Page outer margin; drawer safe margin |

### 6.2 Layout dimensions

| Token | Value | Use |
|---|---|---|
| `--layout-header-height` | 56px | Application header bar |
| `--layout-sidebar-width` | 280px | Contextual sidebar width |
| `--layout-content-reading` | 768px | Single-stream reading surfaces |
| `--layout-content-wide` | 1024px | Two-panel layouts such as Import and Eval |

The Import and Evaluation view MUST have enough horizontal room to display both panels comfortably. It MUST NOT be forced into the reading-column constraint.

### 6.3 Interactive target minimum

All interactive elements MUST have a minimum click/tap target area of 44 x 44 px.

---

## 7. Border, Radius, Elevation, and Texture Tokens

### 7.1 Border radius

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | 4px | Inline badges, status pills |
| `--radius-md` | 8px | Buttons, input fields, segmented controls |
| `--radius-lg` | 12px | Cards, panels |
| `--radius-full` | 999px | Pill tags, status capsules |

### 7.2 Borders

| Context | Value |
|---|---|
| Standard card | `1px solid var(--color-border-hairline)` |
| Active or selected card | `1px solid var(--color-accent-border)` |
| Section divider | `1px solid var(--color-border-divider)` |
| Input field at rest | `1px solid rgba(255,255,255,0.08)` |
| Input field focused | `1px solid var(--color-accent)` |

### 7.3 Elevation

Depth is conveyed through tonal layering and restrained shadow. No glossy highlights or specular gradients.

| Context | Shadow |
|---|---|
| Raised card | `0 2px 8px rgba(6,10,5,0.35), 0 0 0 1px rgba(255,255,255,0.06)` |
| Floating overlay or drawer | `0 0 0 1px rgba(255,255,255,0.10), 0 24px 64px -16px rgba(6,10,5,0.65)` |
| Standard card | border only |

### 7.4 Texture

The canvas MAY carry a subtle CSS noise texture at 2–4% opacity to break pure flatness. It MUST be imperceptible at normal reading distance, invisible when printed, and MUST NOT interfere with text legibility or status color meaning.

---

## 8. Motion and Interaction

### 8.1 Duration

| Transition type | Duration |
|---|---|
| Interactive state change (color, border) | 120–160 ms |
| Component appear or disappear | 180–220 ms |
| Drawer or panel reveal | 220–250 ms |
| Loading pulse cycle | 1,200 ms |

### 8.2 Easing

All transitions MUST use `ease-out` or `cubic-bezier(0.22, 1, 0.36, 1)`. The HeyKivi brand specifies `cubic-bezier(0.16, 1, 0.3, 1)` as an acceptable alternative for micro-interactions. Linear easing is forbidden except for loading pulse animations.

### 8.3 HTMX swap transitions

HTMX content swaps SHOULD use a CSS opacity fade (0 to 1, 180 ms) to avoid jarring flashes.

### 8.4 Scroll behavior

Conversation history on Ask and Briefing SHOULD scroll smoothly to the latest inserted message after a swap.

### 8.5 Reduced-motion suppression

Under `prefers-reduced-motion: reduce`, all animations and transitions MUST be suppressed per §2.7.

---

## 9. Global Application Shell

The shell is implemented in `frontend/templates/base.html`. The stylesheet MUST be updated to the dark palette defined in §4 and §5.

### 9.1 Shell structure

```
+------------------------------------------------------------------+
|  Application header — 56px, --color-surface-1                    |
|  [kivi wordmark]  [subtitle]  [nav: ask / briefing / inbox / …]  |
+--------------------+---------------------------------------------+
|  Contextual        |  Content stage                              |
|  sidebar           |  block content                              |
|  block sidebar     |                                             |
|  280px             |  expands to --layout-content-reading or     |
|                    |  --layout-content-wide as needed            |
+--------------------+---------------------------------------------+
```

### 9.2 Application header

- Background: `--color-surface-1`
- Height: `--layout-header-height` (56px)
- Bottom border: `1px solid var(--color-border-divider)`
- Kivi wordmark: `--type-headline-sm` / editorial font, `--color-ink-primary`
- Wordmark icon: soft-rounded square (12px radius) in `--color-accent-dim` with a "K" glyph in `--color-ink-primary`. MUST NOT be an oversized solid-green block.
- Subtitle: "project-scoped memory" in `--type-body-sm`, `--color-ink-muted`
- Navigation: right-aligned; see §10

The Kivi wordmark in the header is a brand mark, not the page `<h1>`. Each page template provides its own `<h1>` for the view title.

The header MUST NOT contain: native window controls, session controls, audio-capture indicators, or any element without a corresponding implemented route.

### 9.3 Contextual sidebar

The `{% block sidebar %}` slot hosts the Evidence Drawer panel on Ask (`/`) and Briefing (`/briefing`). On all other routes this block is empty and the sidebar column collapses. The sidebar is an inline, persistent panel — not a slide-in overlay. The sidebar background inherits `--color-canvas`.

### 9.4 Content stage

Background: `--color-surface-2`. Padding: `--space-lg`. The stage expands to `--layout-content-wide` for two-column layouts (Import and Eval) and to `--layout-content-reading` for single-stream conversational views.

---

## 10. Navigation Specification

### 10.1 Implemented routes (complete list)

| Label | Route | Template |
|---|---|---|
| ask kivi | `/` | `index.html` |
| briefing | `/briefing` | `briefing.html` |
| inbox | `/inbox` | `inbox.html` |
| timeline | `/timeline` | `timeline.html` |
| import and eval | `/import-eval` | `import_eval.html` |

There is no "Sources" navigation item. Source evidence is accessed exclusively through the Evidence Drawer. No additional navigation items MAY be added without a corresponding implemented route.

### 10.2 Navigation item visual treatment

- Font: `--type-label-nav`, `--color-ink-muted`
- Hover: `--color-ink-secondary`
- Active or current route: 2px bottom border in `--color-accent`, text `--color-ink-primary`. MUST NOT use a full solid-accent block as the selected indicator.
- Focus ring on `:focus-visible`: `outline: 2px solid var(--color-accent); outline-offset: 2px`

### 10.3 Heading hierarchy per page

Each page template MUST provide exactly one `<h1>` that names the current view (e.g., "ask kivi", "project timeline"). The Kivi wordmark in the header is NOT an `<h1>`.

---

## 11. Shared Component Specifications

### 11.1 Primary action button

Used for: "ask", "generate briefing", "scope take", "import", "run evaluation", "submit correction".

- Background: `--color-accent`
- Text: `--color-accent-on` (near-black), `--type-label-action`
- Radius: `--radius-md` (8px)
- Padding: `--space-sm` vertical, `--space-lg` horizontal
- Minimum height: 44px
- Hover: `background-color: #98cc59`
- Active: `transform: translateY(1px) scale(0.98)`
- Focus (`:focus-visible`): `outline: 2px solid var(--color-accent); outline-offset: 2px`

### 11.2 Secondary action button

Used for: "fetch latest", "try again".

- Background: `--color-surface-3`
- Text: `--color-ink-secondary`
- Border: `1px solid var(--color-border-hairline)`
- Radius: `--radius-md`
- Minimum height: 44px
- Hover: border shifts to `1px solid var(--color-accent-border)`

### 11.3 Destructive action (Revoke)

At rest: flat text in `--color-ink-dim`, no border, no background fill. Label: "revoke".

At hover or `:focus-visible`: text color `--color-rose`, background fill `--color-rose-surface`.

MUST require a browser-native `hx-confirm` dialog before executing the DELETE request. MUST NOT appear on a Take whose `is_deleted` is `true`.

### 11.4 Form inputs and selects

- Background: `--color-surface-3`
- Border at rest: `1px solid rgba(255,255,255,0.08)`
- Border at `:focus-visible`: `1px solid var(--color-accent)`, plus `box-shadow: 0 0 0 3px rgba(168,224,99,0.12)`
- Text: `--color-ink-primary`, `--type-body-md`
- Placeholder: `--color-ink-placeholder`
- Radius: `--radius-md` (8px)
- MUST use `outline: none` paired with the `box-shadow` focus ring to avoid OS-default blue outlines

### 11.5 Segmented pill selector

- Trough background: `--color-surface-3`, border: `1px solid var(--color-border-hairline)`, radius: `--radius-full`
- Inactive pill: text `--color-ink-muted`
- Selected pill: background `--color-surface-active`, text `--color-ink-primary`, border: `1px solid var(--color-accent-border)`
- MUST use `aria-pressed="true"` or a radio-button pattern for accessibility

### 11.6 Loading indicator

When an HTMX request is in flight:

- An `htmx-indicator` element becomes visible displaying inline text in `--color-ink-muted`, `--type-body-sm` (e.g., "retrieving evidence...")
- An optional 1,200 ms opacity pulse (0.4 to 1 to 0.4) MAY accompany the text
- The submit button MUST be disabled during the request
- The pulse MUST be suppressed under `prefers-reduced-motion`

### 11.7 Empty state

- Centered text in `--color-ink-dim`, `--type-body-md`
- MUST be truthful; MUST NOT show fabricated example cards or invented counts
- SHOULD include a one-sentence action hint where applicable

### 11.8 Dividers

Horizontal section divider: `border-top: 1px solid var(--color-border-divider)`. Padding above and below: `--space-md`.

---

## 12. Evidence and Take-ID Presentation

### 12.1 Take ID chip (interactive citation)

- Element: MUST be a `<button>` or `<a role="button">` — never a plain `<span>`
- Font: `--type-code-id` / monospace 11px
- Background: `rgba(168,224,99,0.12)`
- Text: `--color-accent`
- Border: `1px solid rgba(168,224,99,0.25)`
- Radius: `--radius-sm` (4px)
- Padding: 2px 6px
- Hover: `rgba(168,224,99,0.20)` background
- Focus (`:focus-visible`): `outline: 2px solid var(--color-accent); outline-offset: 2px`
- `aria-label`: "Inspect source: {take_id}"
- HTMX: `hx-get="/htmx/takes/{take_id}"`, `hx-target="#evidence-drawer"` (or `#evidence-drawer-container` on non-Ask/Briefing routes)

### 12.2 Take ID chip (deleted)

When the referenced Take has `is_deleted: true`:

- Text: `--color-ink-dim`
- Background: `rgba(255,255,255,0.05)`
- Border: `1px solid rgba(255,255,255,0.08)`
- Suffix: " (deleted)" in `--color-rose`, `--type-body-sm`
- Still activatable to view tombstone metadata in the drawer

### 12.3 Claim box

Default (ANSWERED):

- Background: `--color-surface-3`
- Border: `1px solid var(--color-border-hairline)`
- Radius: `--radius-md`
- Padding: `--space-sm`
- Claim text: `--type-body-md`, `--color-ink-secondary`
- Take ID chips below the text, separated by `--space-xs`

CONFLICTING_EVIDENCE variant:

- Background: `--color-conflict-surface`
- Border: `1px solid rgba(255,107,107,0.20)`
- Claim text: `--color-conflict-text`
- Take ID chips: amber tint (background `rgba(232,137,43,0.12)`, text `--color-amber-text`)

---

## 13. Epistemic Status Presentation

Epistemic status describes what the system believes about the content of a memory. It MUST be visually distinct from lifecycle status at all times.

**Source enum:** `backend/kivi/enums.py` — `EpistemicStatus`

### 13.1 Epistemic badge tokens

| EpistemicStatus | Background | Text | Display label |
|---|---|---|---|
| APPROVED | `--color-accent-surface` | `--color-accent` | "approved" |
| PROPOSED | `--color-amber-surface` | `--color-amber-text` | "proposed" |
| REJECTED | `rgba(255,107,107,0.08)` | `--color-rose` | "rejected" |
| CONDITIONAL | `--color-sand-surface` | `--color-sand-text` | "conditional" |
| UNRESOLVED | `--color-steel-surface` | `--color-steel-text` | "unresolved" |

`CONDITIONAL` uses a muted warm-sand treatment. `UNRESOLVED` uses neutral grey. Meaning MUST NOT depend on color alone — the text label is always required.

### 13.2 Epistemic badge anatomy

- Font: `--type-label-pill`, lowercase
- Radius: `--radius-full`
- Padding: 2px 8px
- Display: `inline-flex`, `align-items: center`
- Section label above badge group: "epistemic" in `--type-label-cat`, `--color-ink-dim`, uppercase

---

## 14. Lifecycle Status Presentation

Lifecycle status describes the operational state of a memory. It MUST be visually distinct from epistemic status.

**Source enum:** `backend/kivi/enums.py` — `LifecycleStatus`

### 14.1 Lifecycle badge tokens

| LifecycleStatus | Background | Text | Display label |
|---|---|---|---|
| ACTIVE | `--color-accent-surface` | `--color-accent` | "active" |
| SUPERSEDED | `--color-steel-surface` | `--color-steel-text` | "superseded" |
| INVALIDATED | `rgba(255,107,107,0.08)` | `--color-rose` | "invalidated" |
| TOMBSTONED | `rgba(255,255,255,0.04)` | `--color-ink-dim` | "deleted" |

The backend enum value `TOMBSTONED` is preserved in template conditionals. The display label shown to users is "deleted". No template conditional tests for the string "deleted".

### 14.2 Visual distinction from epistemic badges

One of the following MUST be applied:

- Section labels: "status" above lifecycle badges and "epistemic" above epistemic badges, each in `--type-label-cat`, uppercase, `--color-ink-dim`
- Or shape prefixes: filled pip before lifecycle labels, outlined ring before epistemic labels

### 14.3 Supersession chain display

When a `TimelineEntryRead` has `supersedes_memory_id` or `superseded_by_memory_ids`, the template MUST display the linkage:

- "supersedes `mem_xxxx`" — `--type-body-sm`, `--color-ink-muted`, ID in `--type-code-id`
- "superseded by `mem_xxxx`" — same treatment

Superseded memories MUST remain visible in the timeline at reduced visual weight (opacity 0.65). They MUST NOT be presented as current facts.

---

## 15. Typed Query-Result Presentation

Every `AskResponse` carries one of five `QueryStatus` values. Templates MUST branch on `response.status`. HTTP status codes MUST NOT be used as the primary branching condition.

**Source:** `backend/kivi/schemas.py` — `AskResponse`, `AnswerClaim`, `QueryStatus`
**Routes:** `POST /ask` and `POST /briefings` (both return `AskResponse`)

### 15.1 ANSWERED

- No query-status badge required
- Render `response.answer` in `--type-body-lg`, `--color-ink-primary`
- Below the answer, render "evidence and claims"
- Each `AnswerClaim` in `response.claims[]` renders as a claim box (§12.3) with its `supporting_take_ids` as Take ID chips
- Footer: see §15.6

### 15.2 NO_EVIDENCE

- Status badge: "no evidence", em-dash prefix, `--color-amber-surface` background, `--color-amber-text`
- Message: "I don't have any valid, project-scoped evidence to answer this question."
- NO answer text, NO fabricated explanation
- Footer: latency metadata if available

### 15.3 NEEDS_CLARIFICATION

- Status badge: "needs clarification", "?" prefix, `--color-surface-3` background, `--color-ink-secondary`
- Message: "The project scope isn't clear. Please choose a specific project from the selector above."
- The project scope selector SHOULD receive an accent border highlight as a visual prompt
- NO answer text

### 15.4 CONFLICTING_EVIDENCE

- Status badge: "conflicting evidence", left-right arrow prefix, `--color-conflict-surface` background, `--color-conflict-text`
- If `response.answer` is non-null, render it as an explanatory sentence prefixed with "Kivi found conflicting evidence:" in `--color-ink-muted`
- Render each claim in `response.claims[]` in its conflict-styled claim box (§12.3)
- MUST NOT choose a winner or suppress any claim
- Footer: latency metadata if available

### 15.5 SERVICE_ERROR

- Status badge: "service unavailable", "!" prefix, `--color-rose-surface` background, `--color-rose`
- Message: "Kivi is currently unable to reach its reasoning service. Check your configuration and try again."
- MUST NOT expose Python exception class names, stack traces, database error codes, or API keys
- Provide a "try again" secondary action button that re-submits through the existing form context. MUST NOT implement stored-request replay or any mechanism beyond re-triggering the HTMX form submission.

### 15.6 Response metadata footer

Present below every response bubble, separated by `1px solid var(--color-border-divider)`.

- Font: `--type-body-sm`, `--color-ink-dim`
- `retrieval_latency_ms`: "retrieval: {n} ms"
- `end_to_end_latency_ms`: "completed in: {n} ms"
- `input_tokens` / `output_tokens`: "{n} in / {n} out" — only when both fields are non-null
- `estimated_cost_usd`: not displayed
- MUST NOT display fabricated percentages, confidence scores, or quality ratings

---

## 16. Ask Kivi Specification

**Route:** `GET /` -> `index.html`
**HTMX submit:** `POST /htmx/ask` -> appends to `#chat-history`
**Evidence:** `GET /htmx/takes/{take_id}` -> `#evidence-drawer`
**Backend route:** `POST /ask` returning `AskResponse`

### 16.1 Page layout

Two-column: contextual sidebar (Evidence Drawer panel, 280px) on the left and conversation stage on the right. The sidebar collapses below the conversation at viewports narrower than 768px.

Page `<h1>`: "ask kivi" in `--type-headline-md`, editorial, `--color-ink-primary`.

### 16.2 Greeting state

On first load, one bot bubble: "Hello. I'm Kivi. Ask me anything about your projects." Rendered in `--type-body-lg`, `--color-ink-primary`. MUST be plain and honest — no fabricated capability claims.

### 16.3 Input area

**Row 1 — Project scope:**

- `<label for="project_id">`: "project" in `--type-label-cat`, `--color-ink-muted`, lowercase
- `<select id="project_id" name="project_id">`: populated from `GET /projects`
- First option: `value=""`, label "— no specific project —". MUST NOT be labeled "Auto/Detect".

**Row 2 — Question:**

- `<input type="text" name="question" required>`: placeholder "ask kivi..."
- Submit button: "ask" — primary action (§11.1)
- HTMX: `hx-post="/htmx/ask"`, `hx-target="#chat-history"`, `hx-swap="beforeend"`, `hx-indicator="#loading-indicator"`
- `hx-on::after-request`: clear the question input on success

### 16.4 Chat bubble visual treatment

User bubble (`align-self: flex-end`):
- Background: `--color-surface-3`, border: `1px solid var(--color-border-hairline)`
- Radius: `--radius-lg`, bottom-right corner `--radius-sm`
- Text: `--color-ink-primary`, `--type-body-md`, max-width 80%

Bot bubble (`align-self: flex-start`):
- Background: `--color-surface-2`, border: `1px solid var(--color-border-hairline)`
- Radius: `--radius-lg`, bottom-left corner `--radius-sm`
- Max-width: 80%

### 16.5 Prohibited Ask elements

Like/dislike controls, copy controls, new session or clear history controls, attachment controls, typing indicator animations.

---

## 17. Grounded Briefing Specification

**Route:** `GET /briefing` -> `briefing.html`
**HTMX submit:** `POST /htmx/briefing` -> appends to `#briefing-history`
**Backend route:** `POST /briefings` with `BriefingRequest` -> `AskResponse`
**Schema:** `backend/kivi/schemas.py` — `BriefingRequest`, `AskResponse`

`POST /briefings` is implemented in `app.py` as `ask()` invoked with the briefing focus as the question. The response is the same `AskResponse` type used by `/ask`. There is no separate `BriefingResponse` schema, and none MUST be implied or invented.

### 17.1 Visual treatment

Shares the two-column layout with Ask Kivi. The `AskResponse` component treatment from §15 applies in full.

### 17.2 Input area

**Row 1 — Project scope (required):**

- `<select name="project_id" required>`: first option `disabled selected value=""` — "— choose a project —"
- A briefing MUST be project-scoped. No unscoped submission is accepted.

**Row 2 — Focus statement:**

- `<input type="text" name="focus">`: placeholder "e.g., provide the current project state and unresolved items."
- Submit button: "generate briefing" — primary action (§11.1)

### 17.3 Initial state

One bot bubble: "Request a grounded briefing for a project."

---

## 18. Unscoped Inbox Specification

**Route:** `GET /inbox` -> `inbox.html`
**Data:** `GET /takes?unscoped_only=true` -> `list[TakeRead]`
**Scope action:** `POST /htmx/takes/{take_id}/scope` with `TakeScopeAssignmentRequest`
**Schema:** `backend/kivi/schemas.py` — `TakeRead`, `TakeScopeAssignmentRequest`

### 18.1 Page layout

Single-column content stage. No contextual sidebar.

Page `<h1>`: "unscoped inbox" in `--type-headline-md`, editorial, `--color-ink-primary`.

When takes exist: sub-heading "{n} take{s} awaiting a project" in `--type-body-md`, `--color-ink-muted`.

### 18.2 Empty state

"No unscoped takes at the moment." — centered, `--type-body-md`, `--color-ink-dim`.

### 18.3 Unscoped Take card

- Background: `--color-surface-2`
- Left accent stripe: 3px solid `--color-accent` (left border only)
- Border (right/top/bottom): `1px solid var(--color-border-hairline)`
- Radius: `--radius-lg`, Padding: `--space-lg`
- `id="take-{take.id}"` for HTMX `outerHTML` swap

**Header row:**
- Take ID: `--type-code-id`, `--color-ink-dim` — display only
- Source application: `take.source_application`, `--type-body-sm`, `--color-ink-secondary`
- Event timestamp: `take.event_ts`, `--type-code-ts`, `--color-ink-dim`

**Body:**
- `take.formatted_text` verbatim in `--type-body-md`, `--color-ink-primary`
- Container: left border 2px `--color-accent-border`, background `--color-surface-3`, padding `--space-sm --space-md`, radius `--radius-sm`

**Scope confirmation form:**
- Label: "assign to project" in `--type-label-cat`, `--color-ink-muted`, lowercase
- `<select name="project_id" required>`: first option `disabled selected value=""` — "— choose project —"
- MUST NOT preselect any project. Scope assignment requires explicit user confirmation.
- Submit button: "scope take" — primary action (§11.1)
- HTMX: `hx-post="/htmx/takes/{take_id}/scope"`, `hx-target="#take-{take_id}"`, `hx-swap="outerHTML"`

### 18.4 Post-scope confirmation state

The card replaces itself with:

- Background: `rgba(168,224,99,0.06)`, border: `1px solid var(--color-accent-border)`, radius: `--radius-md`
- Text: "Scoped to {project name}. Take {take_id} is now being processed." — `--type-body-sm`, `--color-ink-muted`

### 18.5 Prohibited Inbox elements

Automatic project detection or preselection, "Discard" action, "dismiss as noise" action, ambient listening indicators, waveform visualizations, Whisper model labels, audio duration, ASR confidence scores, detected entity anchors.

---

## 19. Timeline and Correction Specification

**Route:** `GET /timeline` -> `timeline.html`
**Data:** `GET /projects/{project_id}/timeline` via `GET /htmx/timeline/{project_id}` -> `ProjectTimelineResponse`
**Correction:** `POST /htmx/memories/{memory_id}/correct` with `MemoryCorrectionRequest`
**Revoke:** `DELETE /htmx/takes/{take_id}`
**Schema:** `backend/kivi/schemas.py` — `ProjectTimelineResponse`, `TimelineEntryRead`, `TimelineEvidenceRead`, `MemoryCorrectionRequest`

### 19.1 Page layout

Single-column content stage with `#evidence-drawer-container` below the timeline entries. No contextual sidebar.

Page `<h1>`: "project timeline" in `--type-headline-md`, editorial, `--color-ink-primary`.

### 19.2 Project selector

`<select id="project_id">` with the full project list. First option: "— choose a project —", `disabled selected`. On change, the tested JavaScript event listener fires the HTMX request:

```js
document.getElementById('project_id').addEventListener('change', function(e) {
    htmx.ajax('GET', '/htmx/timeline/' + e.target.value, '#timeline-results');
});
```

This listener is the verified, tested implementation. It MUST be preserved and MUST NOT be replaced with an untested declarative pattern unless that pattern is first verified correct.

### 19.3 Memory card anatomy

Each `TimelineEntryRead` in `timeline.entries` renders as a memory card.

- Background: `--color-surface-2`, Radius: `--radius-lg`, Padding: `--space-lg`
- Default border: `1px solid var(--color-border-hairline)`
- Highlighted (just corrected): `1px solid var(--color-accent-border)`, background `--color-surface-active`

**Header row:**
- Memory type: `entry.memory_type` in `--type-label-action`, `--color-ink-secondary`, sentence case
- Epistemic badge (§13): right-aligned
- Lifecycle badge (§14): right-aligned, `--space-xs` gap from epistemic

**Body:**
- Statement: `{entry.subject} {entry.predicate} {entry.object_value}` in `--type-body-lg`, `--color-ink-primary`
- Creation timestamp: `entry.created_at`, `--type-code-ts`, `--color-ink-dim`
- Supersession links when present (§14.3)
- `valid_from` and `valid_to` when present, labeled "valid from" / "valid to" in `--type-body-sm`, `--color-ink-dim`

**Evidence section:**

- Label: "evidence" in `--type-label-cat`, `--color-ink-dim`, uppercase
- Each `TimelineEvidenceRead`:
  - Take ID chip (§12.1): `hx-get="/htmx/takes/{ev.take_id}"`, `hx-target="#evidence-drawer-container"`
  - Source: `ev.source_application`, `--type-body-sm`, `--color-ink-muted`
  - Role: `ev.evidence_role`, `--type-body-sm`, italic, `--color-ink-dim`
  - If `ev.is_deleted`: suffix "(deleted)" in `--color-rose`; Revoke button absent
  - If not deleted: Revoke text button (§11.3), `aria-label="Revoke evidence: {ev.take_id}"`

**Correction form (ACTIVE memories only):**

- Label: "correct this memory" in `--type-label-cat`, `--color-ink-muted`, lowercase
- `<input type="text" name="corrected_value" required>`: placeholder "corrected value"
- `<input type="text" name="note">`: placeholder "optional note"
- `<input type="hidden" name="project_id" value="{timeline.project.id}">`
- Submit: "submit correction" — secondary action (§11.2)
- HTMX: `hx-post="/htmx/memories/{entry.memory_id}/correct"`, `hx-target="#timeline-results"`

After a successful correction, the timeline refreshes to show the new correction memory and the now-SUPERSEDED prior. The original memory value MUST NOT be edited in place.

### 19.4 Timeline error state

- Border: `1px solid rgba(255,107,107,0.30)`
- Message: "Something went wrong loading this project's timeline." — no internal exception detail
- A "try again" link re-fires the HTMX request

### 19.5 Prohibited Timeline elements

Filter chips for "corrections only" (no backend filter route), metric count chips (not in `ProjectTimelineResponse`), source pipeline chips (not in schema).

---

## 20. Import and Evaluation Specification

**Route:** `GET /import-eval` -> `import_eval.html`
**Import:** `POST /htmx/import` (multipart) -> `CorpusImportResult`
**Fetch eval:** `GET /htmx/evaluate/latest` -> `EvaluationRunRead`
**Run eval:** `POST /htmx/evaluate/run` with `{mode: "deterministic"}` -> `EvaluationRunRead`
**Case detail:** `GET /htmx/evaluate/cases/{case_id}` -> `EvaluationCaseResultRead`
**Schema:** `backend/kivi/schemas.py` — `CorpusImportResult`, `EvaluationRunRead`, `EvaluationMetricsRead`, `EvaluationCaseResultRead`

### 20.1 Page layout

Two-column grid at viewports wider than 1024px, each column independently scrollable. Single column below 1024px. The layout MUST NOT be constrained to `--layout-content-reading`.

### 20.2 Import panel

`<h2>`: "import corpus" in `--type-headline-sm`, editorial, `--color-ink-primary`.

- File input label: "select a `.jsonl` corpus file" in `--type-body-md`, `--color-ink-secondary`
- `<input type="file" accept=".json,.jsonl" required>`
- Import button: "import" — primary action (§11.1)

**Import result outcomes:**

| Condition | Heading | Border |
|---|---|---|
| `ingested > 0` and `failed == 0` | "import complete" | `1px solid var(--color-accent-border)` |
| `ingested > 0` and `failed > 0` | "partially imported" | `1px solid rgba(232,137,43,0.40)` |
| `ingested == 0` and `failed > 0` | "import failed" | `1px solid rgba(255,107,107,0.40)` |

Summary list (all outcomes): total records, successfully ingested, memories created, unscoped records, failed records — from `CorpusImportResult` fields only.

**Per-record failure list** (when `result.failed > 0`):

- `take_id`: `--type-code-id`, `--color-ink-muted`
- `error_type`: mapped through whitelist §20.3 before display
- `detail`: displayed only for known error types; suppressed otherwise

### 20.3 Import error-type whitelist

The `error_type` field in `CorpusImportError` may contain Python exception class names. The template MUST apply the following mapping. Unknown values render as "processing error" with no raw detail string.

| error_type value | Display label | Show detail? |
|---|---|---|
| `IngestionError` | "could not process record" | yes (if explicitly sanitized) |
| `ProviderUnavailable` | "service unavailable" | no |
| any other value | "processing error" | no |

### 20.4 Evaluation panel

`<h2>`: "evaluation" in `--type-headline-sm`, editorial, `--color-ink-primary`.

Action row: "fetch latest" (secondary), "run evaluation" (primary).

**Evaluation result states:**

| State | Treatment |
|---|---|
| No runs found (404) | "No evaluation runs found. Run an evaluation to see results here." |
| Error (non-404) | "Could not load evaluation results." — no internal detail |
| Run loaded | Full result display (below) |

**Run summary row (EvaluationRunRead):**

- `run_id`: `--type-code-id`, `--color-ink-dim`
- `mode`: "deterministic" or "candidate" in `--type-label-pill`, `--color-ink-secondary`
- `started_at`: human-formatted, `--type-code-ts`, `--color-ink-dim`
- `case_count`: "{n} cases", `--type-body-sm`, `--color-ink-muted`

**Metrics grid (EvaluationMetricsRead):**

Two-column grid. Label in `--type-label-cat`, `--color-ink-dim`; value as percentage in `--type-body-md`, `--color-ink-primary`.

| Schema field | Display label |
|---|---|
| `pass_rate` | "pass rate" |
| `answer_correctness` | "answer correctness" |
| `abstention_precision` | "abstention precision" |
| `abstention_recall` | "abstention recall" |
| `conflict_detection_accuracy` | "conflict detection" |
| `project_scope_accuracy` | "project scope accuracy" |
| `decision_status_accuracy` | "decision status accuracy" |
| `temporal_correction_accuracy` | "temporal correction" |
| `provenance_coverage` | "provenance coverage" |
| `deletion_integrity` | "deletion integrity" |

Additional fields also shown:

- `retrieval_latency_p50_ms` / `retrieval_latency_p95_ms`: "retrieval p50 / p95"
- `end_to_end_latency_p50_ms` / `end_to_end_latency_p95_ms`: "end-to-end p50 / p95"
- `database_growth_bytes`: "database growth"
- `input_tokens` / `output_tokens`: "tokens used (in / out)"
- `estimated_cost_usd`: displayed only when non-null

**Integrity violations section:**

Shown only when at least one violation count is > 0. Each row: label in `--type-body-sm`, `--color-ink-secondary`; count in `--color-rose`, `--type-body-md`.

| Schema field | Display label |
|---|---|
| `cross_project_leakage_count` | "cross-project leakage" |
| `deleted_memory_resurrection_count` | "deleted-memory resurrection" |
| `invalid_citation_count` | "invalid citations" |
| `rejected_proposal_promotion_count` | "rejected-proposal promotion" |
| `fabricated_answer_count` | "fabricated answers" |

When all counts are zero: "No integrity violations detected." in `--type-body-sm`, `--color-accent`.

**Case inspection list (EvaluationRunRead.cases):**

Scrollable, max-height 320px, overflow-y auto.

Each `EvaluationCaseResultRead`:

- `case_id`: link `hx-get="/htmx/evaluate/cases/{case_id}"`, `hx-target="#eval-case-container"`, `--type-code-id`
- `category`: `--type-label-pill`, `--color-ink-muted`
- `question`: single line truncated, `--type-body-sm`, `--color-ink-secondary`
- `passed`: "pass" in `--color-accent` / "fail" in `--color-rose`, bold
- `failure_reasons[]`: joined, `--type-body-sm`, `--color-ink-muted` (fail cases only)
- `supporting_take_ids[]`: Take ID chips (§12.1), `hx-target="#evidence-drawer-container"`

### 20.5 Prohibited Evaluation elements

Fabricated evaluation history table listing multiple prior runs, radial gauges without implementation, fabricated latency as a performance guarantee, "Inspect logs" controls, model version or provider-secret labels in the UI.

---

## 21. Evidence Drawer Specification

**Component template:** `frontend/templates/components/evidence_drawer.html`
**Route:** `GET /htmx/takes/{take_id}` -> evidence drawer partial
**Schema:** `backend/kivi/schemas.py` — `TakeRead`

### 21.1 Drawer placement

The Evidence Drawer is an inline, persistent panel that updates in place via HTMX. It is not a slide-in overlay.

- On Ask (`/`) and Briefing (`/briefing`): `{% block sidebar %}` left column, target `#evidence-drawer`
- On Timeline and Import and Eval: `#evidence-drawer-container` below main content

### 21.2 Initial state

"Click a source citation to inspect the evidence here." — `--type-body-sm`, `--color-ink-dim`, centered.

Panel label: "evidence" in `--type-label-cat`, `--color-ink-dim`, uppercase. Panel element: `<aside aria-label="Evidence inspector">`.

### 21.3 Populated drawer (TakeRead present)

**Header row:**
- Label: "take details" in `--type-label-action`, `--color-ink-secondary`
- Take ID badge: `--type-code-id`, background `--color-surface-3`, border `--color-border-hairline`, `--radius-sm` — display only

**Project scope row:**
- Label: "project" in `--type-label-cat`, `--color-ink-dim`, uppercase
- Value: `take.project_id` or "unresolved" — `--type-body-md`, `--color-ink-secondary`

**Formatted output block:**
- Label: "formatted" in `--type-label-cat`, `--color-ink-dim`, uppercase
- Content: `take.formatted_text` in `--type-body-md`, `--color-ink-primary`
- Container: left border 2px `--color-accent-border`, background `--color-surface-3`, padding `--space-sm --space-md`, radius `--radius-sm`

**Raw capture block:**
- Label: "raw capture" in `--type-label-cat`, `--color-ink-dim`, uppercase
- Content: `take.raw_asr` in `--type-body-md`, `--color-ink-secondary`, italic
- Container: background `--color-surface-3`, border `--color-border-hairline`, padding `--space-sm --space-md`, radius `--radius-sm`
- When `take.raw_asr` is null: "Raw content has been removed." in `--type-body-sm`, `--color-ink-dim`, no italic

**Metadata grid (2-up):**
- "source": `take.source_application` — `--type-body-sm`, `--color-ink-secondary`
- "captured": `take.event_ts` formatted — `--type-code-ts`, `--color-ink-dim`
- "status" (full width): "active" in `--color-accent` / "deleted" in `--color-rose` — `--type-body-sm`, bold

### 21.4 Not-found state

"This source could not be found." — `--type-body-sm`, `--color-ink-muted`. Not alarming — a routine lookup miss.

### 21.5 Prohibited Drawer elements

Audio waveforms, playback controls, Whisper model version labels, audio duration, ASR confidence percentages, "Inspect logs" controls, "Revoke" button, schema fields not in `TakeRead`.

---

## 22. Loading, Empty, Success, Validation, and Failure States

### 22.1 Loading

An `htmx-indicator` element with `aria-live="polite"` shows pulsing text during the HTMX request. The submit button is disabled. Pulse respects `prefers-reduced-motion`.

### 22.2 Empty states

| Surface | Copy |
|---|---|
| Inbox (no takes) | "No unscoped takes at the moment." |
| Timeline (no project selected) | "Select a project to view its memory timeline." |
| Timeline (no memories) | "No memories found for this project yet." |
| Evidence drawer (initial) | "Click a source citation to inspect the evidence here." |
| Evidence drawer (not found) | "This source could not be found." |
| Evaluation (no runs) | "No evaluation runs found. Run an evaluation to see results here." |

### 22.3 Inline success states

After non-navigating actions (scope take, correction), the HTMX swap replaces the element with a confirmation. Success treatment: accent-border container, accent-colored confirmation text.

### 22.4 Client-side validation

HTML5 `required` attributes MUST be set on all required fields. `setCustomValidity()` SHOULD provide plain-language error messages.

### 22.5 Backend error responses

| HTTP code and context | Human message |
|---|---|
| 409 correcting non-active memory | "This memory has already been superseded and cannot be corrected again." |
| 503 embedding unavailable | "The reasoning service is temporarily unavailable. Try again in a moment." |
| 404 Take not found | "This source could not be found." |
| 5xx unexpected | SERVICE_ERROR pattern (§15.5) |

MUST NOT expose Python exception class names, stack traces, SQL error codes, or provider API keys.

---

## 23. Responsive Behavior

### 23.1 Breakpoints

| Breakpoint | Width | Behavior |
|---|---|---|
| Desktop | 1024px and wider | Full two-column layout (sidebar + stage) |
| Narrow | 768px to 1023px | Single column; contextual sidebar stacks below stage |
| Mobile (graceful) | below 768px | Not a primary target; layout degrades without breaking |

### 23.2 Design baseline

Primary target: 1440 x 900. The layout MUST remain functional and unbroken at 1024px.

### 23.3 Navigation at narrow widths

At widths below 1024px, the header navigation SHOULD scroll horizontally rather than wrap to a second line.

### 23.4 Contextual sidebar at narrow widths

On Ask and Briefing at viewports below 768px, the Evidence Drawer panel stacks below the conversation stage. The `#evidence-drawer` target div remains in the DOM.

---

## 24. Accessibility and Keyboard Requirements

### 24.1 Focus rings

All interactive elements MUST display a visible focus ring on `:focus-visible`:

```css
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

Custom inputs use `outline: none` paired with the `box-shadow` focus treatment from §11.4.

### 24.2 Color contrast

| Pair | Approximate ratio | WCAG result |
|---|---|---|
| `--color-ink-primary` (#f4f1e6) on `--color-surface-2` (#1a2016) | ~12:1 | Passes AAA |
| `--color-ink-secondary` (#b9b6a8) on `--color-surface-2` | ~7:1 | Passes AA |
| `--color-ink-muted` (#7d7b6f) on `--color-surface-2` | ~3.6:1 | Passes AA large text only |
| `--color-accent` (#a8e063) on `--color-accent-on` (#1b1d18) | ~8:1 | Passes AA |

`--color-ink-muted` and `--color-ink-dim` MUST NOT carry primary content or interactive labels.

### 24.3 ARIA

| Element | Required attribute |
|---|---|
| Take ID chip | `aria-label="Inspect source: {take_id}"` |
| Revoke button | `aria-label="Revoke evidence: {take_id}"` |
| Evidence drawer panel | `aria-label="Evidence inspector"` |
| HTMX loading indicator container | `aria-live="polite"` |
| Dynamically updated status badges | `role="status"` |

### 24.4 Semantic HTML

- One `<h1>` per page (the view title, not the wordmark)
- Correct landmarks: `<header>`, `<nav>`, `<main>`, `<aside>` (contextual sidebar), `<section>`
- Take ID chips MUST be `<button>` or `<a role="button">`
- All form controls MUST have associated `<label>` elements

### 24.5 Keyboard navigation order

Header navigation -> project selector -> input field -> submit button -> result area -> citation buttons. Focus SHOULD move to newly inserted content after an HTMX swap where user attention is expected there.

---

## 25. Jinja2 and HTMX Implementation Constraints

### 25.1 No external CDN

All JavaScript, CSS, and font assets MUST be served locally. HTMX is vendored at `frontend/static/vendor/htmx.min.js`. No requests to Google Fonts, cdnjs, unpkg, or any external host are permitted.

### 25.2 No framework build step

No Node.js, npm, Webpack, Vite, or any build toolchain. CSS is plain CSS with custom properties. JavaScript is vanilla and inlined in templates only when no HTMX attribute achieves the same result.

### 25.3 No React, Vue, Angular, or Tailwind

All styling uses CSS custom properties and named classes in `frontend/static/styles.css`.

### 25.4 CSS custom properties

All design tokens from §4 through §7 MUST be expressed as CSS custom properties in `:root {}` in `styles.css`. The current `:root` block (which defines a light-mode palette) MUST be replaced with the Kivi dark token set. Inline `style=""` attributes MUST NOT define token values.

### 25.5 HTMX patterns in use

| Pattern | Usage |
|---|---|
| `hx-post` | Ask, Briefing, scope take, correct memory, import, run eval |
| `hx-get` | Fetch Take (evidence), fetch latest eval, fetch case |
| `hx-delete` | Revoke a Take |
| `hx-target` | All dynamic swap targets |
| `hx-swap` | `beforeend` for history; `outerHTML` for Take cards; `innerHTML` for panels |
| `hx-indicator` | Loading indicator per form |
| `hx-confirm` | Revoke destructive confirmation |
| `hx-disabled-elt` | Disable submit during request |
| `hx-on::after-request` | Clear question input after successful ask |

### 25.6 Template safety

- All template variables MUST be auto-escaped by Jinja2 with `autoescape=True`
- `| safe` MUST NOT be applied to any user-sourced or backend-provided field
- This includes `response.answer`, `claim.claim_text`, `take.formatted_text`, `take.raw_asr`, and correction note fields

---

## 26. Content and Microcopy Rules

### 26.1 Voice and register

- Kivi speaks in first person, present tense, plain sentence case
- Section headings use lowercase where meaningful: "ask kivi", "project timeline", "evidence"
- MUST NOT appear in user-visible text: MERKLE_ROOT, EPISTEMIC_KERNEL, INGESTION_GATEWAY, SYSTEM_NOMINAL, raw confidence percentages, embedding-vector jargon, cybersecurity terminal vocabulary

### 26.2 Status display labels

| Backend enum value | Human display |
|---|---|
| ANSWERED | (no badge needed — the answer is self-labeling) |
| NO_EVIDENCE | "no evidence" |
| NEEDS_CLARIFICATION | "needs clarification" |
| CONFLICTING_EVIDENCE | "conflicting evidence" |
| SERVICE_ERROR | "service unavailable" |
| APPROVED | "approved" |
| PROPOSED | "proposed" |
| REJECTED | "rejected" |
| CONDITIONAL | "conditional" |
| UNRESOLVED | "unresolved" |
| ACTIVE | "active" |
| SUPERSEDED | "superseded" |
| INVALIDATED | "invalidated" |
| TOMBSTONED | "deleted" (display only; backend enum value unchanged) |

### 26.3 Error message guidelines

| Situation | Correct message | Prohibited |
|---|---|---|
| Model provider not configured | "The reasoning service isn't configured yet. Add your API key to the environment and restart." | Raw AttributeError or class name |
| Import validation error | "One or more records are missing required fields." | ValidationError: 3 validation errors for TakeCreate |
| Correcting non-active memory | "This memory has already been superseded and cannot be corrected again." | 409 Conflict: memory is not ACTIVE |
| Embedding service down | "The reasoning service is temporarily unavailable. Try again in a moment." | ProviderUnavailable: model provider is not configured |

---

## 27. Implementation Acceptance Checklist

An implementation is complete only when every item below is satisfied.

### Visual system

- [ ] Dark background palette applied (`--color-canvas` #0b0e0a as page background)
- [ ] Editorial serif font stack used for headings and greeting text
- [ ] Sans font stack used for all body, label, and navigation text
- [ ] Monospace font stack used only for Take IDs, memory IDs, eval run IDs, and timestamps
- [ ] All design tokens expressed as CSS custom properties in `:root`
- [ ] No external CDN links in any template
- [ ] `prefers-reduced-motion` suppression applied globally

### Navigation

- [ ] Exactly five navigation items matching the five implemented routes
- [ ] No "Sources" navigation item
- [ ] Active navigation state is a thin bottom border, NOT a full solid-accent block
- [ ] All nav items keyboard-focusable with visible `:focus-visible` ring
- [ ] One `<h1>` per page (the view title); wordmark is not an `<h1>`

### Contract alignment

- [ ] Every rendered field traced to `schemas.py` or the integration contract
- [ ] Template branching on `response.status`, not HTTP code alone
- [ ] All five `QueryStatus` values have distinct, non-generic visual treatments
- [ ] Epistemic and lifecycle badges are visually distinct and never merged
- [ ] Exact backend enum values used in template conditionals
- [ ] `TOMBSTONED` backend value preserved in conditionals; display label is "deleted"

### Evidence and provenance

- [ ] All Take ID citations are `<button>` or `<a role="button">` elements
- [ ] All Take ID buttons call the correct HTMX route and target
- [ ] Evidence Drawer updates in place without page navigation
- [ ] Deleted Take chips render with "(deleted)" suffix and subdued styling
- [ ] Null `raw_asr` displays "Raw content has been removed."

### Actions and forms

- [ ] Correction form appears only on ACTIVE memories
- [ ] Revoke triggers `hx-confirm` before executing DELETE
- [ ] Inbox scope form does not preselect any project
- [ ] Import `error_type` values mapped through the whitelist (§20.3)
- [ ] No fabricated actions without a corresponding implemented route

### Typed response states

- [ ] ANSWERED: answer + claim boxes with Take ID chips
- [ ] NO_EVIDENCE: abstention message, no fabricated content
- [ ] NEEDS_CLARIFICATION: scope prompt, no answer
- [ ] CONFLICTING_EVIDENCE: all conflicting claims without choosing a winner
- [ ] SERVICE_ERROR: human message, no internal detail, form-context retry

### Accessibility

- [ ] All interactive elements have visible `:focus-visible` rings
- [ ] No status meaning conveyed by color alone — text label always present
- [ ] All form controls have associated `<label>` elements
- [ ] Minimum 44px target area for all interactive elements
- [ ] Correct heading hierarchy per page
- [ ] `aria-label` on Take ID chips and Revoke buttons
- [ ] `aria-live="polite"` on loading indicator container

### Prohibited elements absent

- [ ] No native OS window controls in the frontend
- [ ] No "Sources" page or navigation item
- [ ] No like/dislike controls
- [ ] No attachment controls
- [ ] No ambient listening indicators
- [ ] No waveform visualizations
- [ ] No Whisper model version labels
- [ ] No fabricated confidence percentages or audio durations
- [ ] No fabricated evaluation history table
- [ ] No fabricated decorative statistics
- [ ] No raw Python exception class names in user-visible text
- [ ] No hard-coded Take IDs, project names, or timestamps in production templates

---

## 28. Appendix: Retained Visual Ideas

| Source | Idea | Adopted as |
|---|---|---|
| HeyKivi visual reference study | Near-black canvas #0b0e0a, deepest layer #060a05 | `--color-canvas`, `--color-depth` in §4.1 |
| HeyKivi visual reference study | Warm cream primary text #f4f1e6 | `--color-ink-primary` in §4.2 |
| HeyKivi visual reference study | Lime-green primary accent #a8e063 | `--color-accent` in §4.3 |
| HeyKivi visual reference study | Destructive red #ff6b6b | `--color-rose` in §4.3 |
| HeyKivi visual reference study | Secondary text #b9b6a8 | `--color-ink-secondary` in §4.2 |
| HeyKivi visual reference study | Hairline borders rgba(255,255,255,0.07–0.10) | `--color-border-hairline` in §4.3 |
| HeyKivi visual reference study | Border radii: full=999px, lg=12px, md=8px, sm=4px | `--radius-*` tokens in §7.1 |
| HeyKivi visual reference study | Input focus: 3px lime glow rgba(168,224,99,0.12) | §11.4 |
| HeyKivi visual reference study | Button hover: shift to #98cc59 | §11.1 |
| HeyKivi visual reference study | Active button: translateY(1px) scale(0.98) | §11.1 |
| HeyKivi visual reference study | 150 ms micro-interaction timing | §8.1 (within 120–250 ms range) |
| HeyKivi visual reference study | prefers-reduced-motion suppression | §2.7 and §8.5 |
| Stitch | Editorial serif headings | §5.1 editorial font voice |
| Stitch | Monospace strictly for IDs and timestamps | §5.3 |
| Stitch | Lowercase section category labels | §10.2, §26.1 |
| Stitch | Organic card curvature 12px | `--radius-lg` |
| Stitch | Accent border for active and selected states | `--color-accent-border` |
| Stitch | Destructive actions subdued at rest, revealed at hover | §11.3 |
| Stitch | Take ID as first-class interactive element | §12.1 |

---

## 29. Appendix: Rejected Inventions

| Rejected element | Reason |
|---|---|
| Native OS window controls in the frontend | This is a browser application. Window chrome is managed by the OS and browser. |
| Native window title bar with drag region | Same. |
| "Sources" as an independent navigation page or route | No `/sources` route exists. Source evidence is accessed only through the Evidence Drawer. |
| New session or clear chat history control | No session-management route in the contract. |
| Like or dislike feedback controls | No feedback-submission route in the contract. |
| Copy recap or clipboard action | No copy route. Clipboard access is a future enhancement outside current scope. |
| Attachment or file upload control on Ask Kivi | No file-attachment route on `/ask`. |
| "Discard" or "dismiss as noise" action on Inbox Takes | No discard route. Only `POST /takes/{take_id}/scope` is supported. |
| Automatic project detection from Take content | Prohibited by INTEGRATION_CONTRACT §8: scope assignment is an explicit user confirmation, not a semantic inference. |
| Passive or ambient listening indicator | Audio capture is out of scope for Part Two. |
| Waveform visualization implying live audio stream | Same. |
| Ambient listening toggle | Same. |
| Whisper model version label in any UI surface | Internal implementation detail; no field in `TakeRead` or any contract schema. |
| Fabricated ASR confidence percentages | Not in any contract schema field. |
| Fabricated audio duration metadata | Not in any contract schema field. |
| Detected entity anchors in Inbox cards | Not in `TakeRead`. |
| Hashes or Merkle roots | Explicitly prohibited by Project Brief; not in any contract schema. |
| "Local vault" storage claim in the UI | Internal architecture detail; not a user-facing contract field. |
| "Deterministic truth integrity" radial gauge | No contract field provides this value. Would require fabrication. |
| "Contextual atmosphere photo card" | Decorative invention with no contract field or product function. |
| Scheduled synchronization indicator | No sync route in the contract. |
| Fabricated evaluation history table listing multiple prior runs | `GET /evaluate/latest` returns one run. Historical enumeration is not in the contract. |
| Invented evaluation metrics or hard-coded pass rates | All metric values must come from a live `EvaluationRunRead` response. |
| Fabricated latency displayed as a performance guarantee | Latency values from `AskResponse` are real measurements, not SLA claims. |
| Raw Python exception class names in user-visible text | Prohibited by §3 rule T-10. |
| Provider API keys or configuration secrets in error messages | Prohibited by §3 rule T-10. |
| "Inspect logs" control | No log-inspection route in the contract. |
| Fabricated explanatory paragraphs in memory cards | Memory cards render only fields from `TimelineEntryRead`. |
| Invented source quotations, Take IDs, or timestamps in production templates | All data must come from the backend. |
| "Curator" indicator or designated-curator role display | No curator field in any schema. |
| Project-scoped take-count or correction-chain-count metric chips on Timeline | Not in `ProjectTimelineResponse`. |
| Oversized solid-accent navigation selected state | Replaced by thin bottom-border treatment in §10.2. |
| Separate BriefingResponse schema | `POST /briefings` returns `AskResponse`. No separate type exists or should be implied. |
