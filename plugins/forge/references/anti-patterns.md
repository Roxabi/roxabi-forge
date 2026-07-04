# Anti-patterns

Canonical list of visual/UX choices forbidden in Forge output. Sub-agents **must** consult this doc at Deliver phase, before emitting HTML. Every rule names the restriction and the reason so edge cases can be judged — not blindly followed.

Scattered prior restrictions from `tokens.md`, aesthetic CSS comments, and individual SKILL.md files are consolidated here. Those files now point to this one.

---

## Shadows

| Restriction | Reason | Exception |
|---|---|---|
| No `box-shadow` stacking (≥2 blur layers on one element) | Multi-layer shadows read as "SaaS landing page slop" — the signal is cheap polish, not substance. Flat surfaces + borders communicate structure more honestly. | A single subtle `box-shadow` is allowed on floating elements (modals, dropdowns) if the aesthetic demands elevation. |
| No `text-shadow` on body text, headings, or links | Creates illegible glyphs at small sizes; signals amateur glow effects. | Terminal aesthetic `.glow` class (and equivalents) for intentional CRT feel. |

---

## Backgrounds

| Restriction | Reason | Exception |
|---|---|---|
| No gradient backgrounds on cards, hero sections, or content surfaces | Gradients age visibly and tie the artifact to a specific year's design trend. Flat tokens keep artifacts timeless. | Single-stop radial masks for cursor spotlight / grid fade (caveman aesthetic primitives). |
| No stock imagery, no gradient overlays on text | Distracts from content; often wrong color calibration per aesthetic. | SVG diagrams/illustrations authored for the artifact. |

---

## Radii

| Restriction | Reason | Exception |
|---|---|---|
| No `border-radius > 8px` on content cards, buttons, or panels | Pillowy rounded shapes read as generic consumer UI. Forge output is tool output — sharp or mildly-rounded only. | Pills and badges (`border-radius: 999px`), circle avatars, and decorative graph nodes. |

---

## Decorative Glyphs

| Restriction | Reason | Exception |
|---|---|---|
| No `::before` / `::after` icons used decoratively (bullets, chevrons, arrows, checkmarks) | Pseudo-element icons fail in screenshots, break in reader mode, and leak into copy-paste. | Functional pseudo-elements (clearfix, focus rings, scroll indicators, pill separators) — anything structural, not decorative. |
| No emoji used as UI icons (✓, →, ⚡, 🔥) | Emoji rendering diverges across OS / browser / font; they signal informality inside technical output. | Emoji inside user-authored content passed through verbatim (issue titles, quotes). |

---

## Animation

| Restriction | Reason | Exception |
|---|---|---|
| No animation beyond theme-toggle and tab/hover feedback | Motion draws attention; most forge artifacts are read, not scrolled-through. Motion reserved for state change. | Theme toggle (≤0.15s), tab hover (≤0.15s), caveman breathing aura (15s ambient, opt-in), fgraph `.animated` dash march when flow direction matters. |
| No entrance animations on page load (fade-in, slide-up) | They delay first meaningful read. Readers want content, not choreography. | None. |
| Animation duration > 0.15s on interactive feedback | Anything slower feels laggy on 60Hz+ displays. | Ambient / background animations (aura, dash march) where slowness is the point. |

---

## Fonts

| Restriction | Reason | Exception |
|---|---|---|
| No Inter, Roboto, Arial, Helvetica, or bare `system-ui` as primary font | These are the universal "I didn't pick a font" fonts — they make every artifact look identical. Forge has a deliberate type palette. | Inside code blocks where `system-ui` monospace fallback is needed. |
| No more than 2 type families per artifact | Typographic zoo = no voice. | Specimen / type-exploration artifacts where comparing families is the point. |

**Acceptable primary pairs:** IBM Plex Sans + IBM Plex Mono · DM Sans + Fira Code · Plus Jakarta Sans + Azeret Mono. See `tokens.md`.

---

## Colors

| Restriction | Reason | Exception |
|---|---|---|
| No indigo/fuchsia/cyan-magenta-pink neon stack (the "cyberpunk SaaS" palette) | It's the default of a thousand AI tools and landing-page generators. Forge uses aesthetic-specific palettes; do not reach for this one. | Terminal aesthetic greens/ambers; caveman's single orange-red; other aesthetic-defined accents. |
| No `--text-dim` for body paragraphs (text someone reads more than one sentence of) | Fails WCAG AA contrast on muted surfaces — the artifact becomes unreadable to real users. | Metadata strips, captions, labels — text the reader skims. |
| No setting `--text-muted` and `--text-dim` to the same value | Collapses the three-tier contrast hierarchy; every tier passes AA or none do. | Never. |

See `tokens.md` § "Forbidden Colors for Body Text in Dark Mode" for specific hex values.

---

## Layout

| Restriction | Reason | Exception |
|---|---|---|
| No visible text block of > 4 sentences without a break, list, or `<details class="disclosure">` wrapper | Walls of prose bury the glance layer. Forge output is scanned; wall-of-text defeats it. | Long-form narrative sections that are clearly framed as "deep dive." |
| No inline metadata as prose ("This was created on Tuesday by Mickael using...") | Metadata belongs in a `.kv-strip` or table. Prose metadata is noise per sentence. | None. |
| No section where the `.summary-card` or `.stat-grid` glance layer is missing | Every tab/section must open with glance-level signal. Otherwise the reader is already deep-diving before they chose to. | Landing / hero sections where the summary IS the content. |

---

## When this doc applies

Every forge skill's Deliver phase links to this file. Before emitting HTML, the sub-agent walks these rules and confirms the output does not violate them (or is covered by a named exception). The point is not to enumerate bad HTML — it is to resist the gravitational pull toward generic output.

If a rule seems wrong for a specific artifact, do not silently violate. Either invoke a named exception, or raise the conflict with the user before shipping.

---

## Composition (presentation × craft diagrams)

| Restriction | Reason | Exception |
|---|---|---|
| No inline craft diagram CSS inside presentation HTML (`.craft-embed`, copied canvas rules, namespaced spoke CSS) | Two typographic/layout stacks collide — clipping, double titles, invisible reveals. | `composition.css` primitives only (`panel-wrap`, `arch-wrap`, `diagram-embed`). |
| No `.reveal` on both wrapper and `diagram-embed` child | Double `opacity: 0` — diagram stays invisible. | Reveal on `arch-wrap` / `panel-wrap` parent only. |
| No `figcaption` / `arch-title` when diagram SSoT already has a title | Duplicate headings in scroll doc. | External title only when diagram is purely decorative (rare). |
| No external SVG sprite refs in `diagrams/*.html` (`<use href="brand-icons.svg#…">`) | `file://` blocks cross-file sprite loads. | Inline `<symbol>` blocks from `diagrams/brand-icons.svg`. |
| No invented paths for third-party brand marks | Wrong logos break trust. | Simple Icons / official marks; custom glyphs for product-only nodes (REQ hub). |

Full layer model: `composition-contract.md`.

---

## See also

- `composition-contract.md` — presentation × diagram integration (7 levels)
- `tokens.md` — positive rules (what IS allowed for colors, fonts, tier hierarchy)
- `output-ux.md` — Deliver checklist including fact-sheet compilation + glance-layer requirements
- `aesthetics/*.css` — per-aesthetic tokens that scope the color rules above
