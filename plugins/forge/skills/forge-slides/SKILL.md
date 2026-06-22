---
name: forge-slides
description: >-
  Generate a magazine-quality scroll-snap presentation deck from an issue, a
  markdown file, or a free prompt. Single-file, offline-playable, keyboard +
  touch navigated, 10 slide types, 6 aesthetic presets. Triggers: "create
  deck" | "make a deck" | "slides from #N" | "slide deck" | "forge slides" |
  "presentation deck" | "pitch deck".
summary: 'scroll-snap presentation deck'
version: 0.1.0
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, ToolSearch, Agent
---

# Slides — Scroll-Snap Presentation Deck

Generate a single-file HTML presentation deck from a GitHub issue, a markdown file, or a free prompt. Output is a `100dvh` scroll-snap deck — keyboard navigated (`↑`/`↓`/`PgUp`/`PgDn`/`Home`/`End`), touch-swipeable, and fully offline under `file://`.

Output: `~/.roxabi/forge/<project>/slides/{name}.html`

Single-file — all CSS and JS inlined. No split-file, no external links at runtime (except CDN fonts). This is the correct distribution rule for `file://` offline safety; see CLAUDE.md § Distribution Rule.

**Read before generating:**

```
${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md                         — brand detection, output paths, deploy commands
${CLAUDE_PLUGIN_ROOT}/references/slide-patterns.md                    — 10 slide types, 6 aesthetic presets, init sequence (primary Phase 3 reference)
${CLAUDE_PLUGIN_ROOT}/references/base/reset.css                       — inline 1st
${CLAUDE_PLUGIN_ROOT}/references/base/typography.css                  — inline 2nd
${CLAUDE_PLUGIN_ROOT}/references/aesthetics/{aesthetic}.css           — inline 3rd (one file, selected by detection)
${CLAUDE_PLUGIN_ROOT}/references/slide-templates/slide-deck-base.css  — inline 4th
${CLAUDE_PLUGIN_ROOT}/references/slide-templates/slide-deck-base.js   — inline as <script type="module">
${CLAUDE_PLUGIN_ROOT}/references/slide-templates/deck-template.html   — reference shell (not output verbatim)
${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md                      — meta tag format + categories
${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md                 — Track A/B detection
${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md                       — silent inference (reader/action/takeaway/tone)
${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md            — track-by-track behavior
```

**Directive: inline, never link** — `slide-templates/` files are generation source, not runtime dependencies. Read → inline into the output `<style>` and `<script>` blocks. The only allowed external requests at runtime are CDN fonts (`fonts.googleapis.com`, `fonts.gstatic.com`). Diagram slides inline their fgraph template + `fgraph-base.css` directly — no diagram runtime, no CDN.

---

## Design Phase — Frame → Structure → Style → Deliver

An overlay on Phases 1–4. Frame runs in Phase 1, Structure in Phase 2, Style in Phase 3, Deliver in Phase 4.

### Track selection (Phase 1 start)

Run `${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md` before any other decision:

- **Track A (branded)** — `forge.yml` found → aesthetic/palette/typography locked; `deliver_must_match` rules enforced.
- **Track B (exploration)** — no brand book → full Frame judgment.

Report the loaded brand book (or its absence) before starting Frame. Track is fixed at Phase 1.

Full track-by-track behavior: `${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md`.

### Frame — What's this deck for?

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md` — three signals, reader-action matrix, tone dimensions.

**For forge-slides specifically, Signal 1 (reader-action) determines pacing.** A deck presented live to a room differs from one sent async for self-review: live → fewer words per slide, more visual breathing room; async → slightly denser content slides with self-contained context.

- **Track A:** infer Signal 1 (reader-action) and Signal 2 (takeaway). Tone pre-constrained by brand voice.
- **Track B:** infer Signal 1, Signal 2, and Signal 3 (all tone axes) from prompt and content.

Aesthetic is mechanical, not Frame-chosen. Frame produces purpose, not CSS.

### Structure — Deck outline

Produce an in-memory deck outline: ordered list of `{type, heading, content}` per slide.

| Slide count guide | Use when |
|---|---|
| 6–8 slides | Single focused argument, pitch hook, short briefing |
| 8–14 slides (typical) | Feature plan, project overview, team presentation |
| 15–20 slides | Multi-phase plan, competitive analysis, training |
| Hard cap: 30 | Never exceed — content beyond 30 slides belongs in a guide |

Typical sequence: `title → section → content × 3–5 → [quote] → [comparison | diagram | image] → closing`

Slide type selection: see `slide-patterns.md § 10 Slide Types`. Do not re-specify types here.

### Style — CSS inline order

Inline in this order, no exceptions:

1. `reset.css`
2. `typography.css`
3. `{aesthetic}.css` (one file, from `references/aesthetics/`)
4. `slide-deck-base.css`

`data-theme` on `<html>`: use `dark` unless brand detection or `--aesthetic` override specifies otherwise.

### Deliver — Write + verify

- Write to output path (silent overwrite if exists — matches forge-guide/forge-epic behavior).
- Inject diagram-meta block in `<head>`.
- Report file path + `file://` preview URL.
- Print acceptance checklist (see Phase 4).

**Track A additionally:** run every `brand.deliver_must_match` rule before writing. Report pass/fail per rule. Do not write until all pass or user overrides.

---

## Phase 1 — Context

Let:
  ARGS  := $ARGUMENTS
  AG    := `~/.roxabi/forge/`

### Input mode detection

Precedence: explicit path > `#N` > free prompt.

| Input | Detection | Title source |
|---|---|---|
| `#N` or `issue N` | `gh issue view N --json title,body` | Issue title |
| `/path/to/file.md` or `./relative.md` | Read file directly | First H1 |
| free prompt text | Use verbatim | Derive slug from first 5 words |

### Steps

1. **Detect project** from ARGS or cwd. Unknown → ask: "Which project is this deck for?"

2. **Run brand book loader** (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`). Report Track A or B before continuing.

3. **Derive `{name}`** (kebab-case ≤30 chars) from issue slug / markdown filename / prompt slug.
   Re-invocation for the same `{PROJ}/{name}` **overwrites silently** — matches `forge-guide`/`forge-epic` deterministic-path behavior. Do not prompt.

4. **Apply Aesthetic Detection** (`forge-ops.md § Aesthetic Detection`). `--aesthetic <name>` override takes precedence. Allowed values: `editorial`, `roxabi`, `blueprint`, `caveman`, `lyra`, `terminal`.

5. **Frame Trace** — emit one-line summary before Phase 2. Not a question; user can interrupt if wrong:
   ```
   Frame: reader={signal1_reader}, action={signal1_action}, takeaway={signal2}, tone={signal3_summary}. Generating...
   ```

---

## Phase 2 — Decision (Deck Outline)

Produce the deck outline silently (in-memory, no disk write). Each entry: `{index, type, heading, content_notes}`.

### Input extraction rules

| Input | Extract | Maps to |
|---|---|---|
| `#N` | Issue title | `title` slide heading |
| `#N` | Issue body H2 headings | `section` slides |
| `#N` | Issue body H2 body paragraphs | `content` or `diagram` slides |
| `#N` | Issue body code blocks | `code` slides |
| markdown path | First H1 | `title` slide heading |
| markdown path | H2 headings | `section` slide per H2 |
| markdown path | H2 body paragraphs | `content` slides |
| markdown path | Fenced code blocks | `code` slides |
| markdown path | Blockquotes | `quote` slides |
| markdown path | GFM tables (`\|…\|`) or HTML tables | `table` slides |
| markdown path | Markdown images with substantive `alt` text | `image` slides (full-bleed) |
| markdown path | "A vs B" / two-column lists, decision matrices | `comparison` slides |
| free prompt | Entire prompt | `title` + `content` × N + `closing` minimum |

### Diagram slides

If source content includes architecture description, dependency list, or flow description:
- Architecture / hub-spoke / topology (any scale) → `diagram` slide via fd-engine descriptor `type:"architecture"` (premium); static `radial-hub.html` / `radial-ring.html` + inline `fgraph-base.css` only for print/no-JS
- Linear 2–3 stage pipeline → `diagram` slide via fd-engine `type:"architecture"` or `"flowchart"`; static `linear-flow.html` for print/no-JS
- Layered architecture → `diagram` slide via fd-engine `type:"architecture"`; static `layered.html` / `deployment-tiers.html` for print/no-JS
- Timeline / gantt → `diagram` slide with fd-engine descriptor `type:"gantt"`
- Proportion / share → `diagram` slide with fd-engine descriptor `type:"pie"`
- ER schema → `diagram` slide with fd-engine descriptor `type:"er"` + bun elk step
- API sequence → `diagram` slide with fd-engine descriptor `type:"sequence"` + bun elk step
- State machine → `diagram` slide with fd-engine descriptor `type:"state"` + bun elk step
- Issue dependency graph → `diagram` slide with `dep-graph.html`
- > 8 nodes or a shape no template covers → **split** across two diagram slides, or use `layered.html` with hand-assigned `--x/--y`

### Meta values

| Field | Value |
|---|---|
| `diagram:category` | `presentation` |
| `diagram:cat-label` | `Presentation` |
| `diagram:color` | match project (amber=Lyra, gold=Roxabi, cyan=Blueprint, etc.) |
| `diagram:badges` | `latest` |
| `diagram:issue` | issue number if input was `#N`, else omit |

---

## Phase 3 — Generation

Always delegate to a sub-agent when total output exceeds ~300 lines. A deck with 10+ slides will always exceed this threshold — **always delegate Phase 3 to a sub-agent**.

### Sub-agent prompt template

```
Generate forge-slides output (single-file HTML deck).

Decisions (from Phase 1–2):
- Track: {A|B}
- Aesthetic: {aesthetic}.css
- Input: {#N | path | prompt}
- Slide count: {N}
- Deck outline: {ordered list of type + heading + content_notes}
- Output path: ~/.roxabi/forge/{PROJ}/slides/{name}.html
- data-theme: {dark|light}

Read these reference files IN ORDER:
- {CLAUDE_PLUGIN_ROOT}/references/slide-patterns.md     ← primary generation reference
- {CLAUDE_PLUGIN_ROOT}/references/base/reset.css
- {CLAUDE_PLUGIN_ROOT}/references/base/typography.css
- {CLAUDE_PLUGIN_ROOT}/references/aesthetics/{aesthetic}.css
- {CLAUDE_PLUGIN_ROOT}/references/slide-templates/slide-deck-base.css
- {CLAUDE_PLUGIN_ROOT}/references/slide-templates/slide-deck-base.js
- {CLAUDE_PLUGIN_ROOT}/references/slide-templates/deck-template.html

Then generate one file:
  ~/.roxabi/forge/{PROJ}/slides/{name}.html

Rules:
- Single file — inline all CSS in order: reset → typography → aesthetic → slide-deck-base
- Inline slide-deck-base.js as <script type="module"> before </body>
- One <section class="slide slide--{type}"> per outline entry
- Add class="reveal" to child elements that should stagger in (headings, paragraphs, list items)
- Add --i CSS custom property for stagger index when overriding transition-delay inline
- diagram slides: inline the fgraph template HTML body inside the slide + inline fgraph-base.css content into the <style> block (Mode A distribution rule)
- Inject diagram-meta block in <head> (see diagram-meta.md)
- data-theme="{dark|light}" on <html>

**Escape rules (load-bearing — prevents XSS from untrusted source content):**
- All text content derived from issue body / markdown / prompt → HTML-escape (`&` `<` `>` `"` `'`) before inserting into element text nodes.
- `href` values (CTA links, image source URLs): allow only schemes `https://`, `http://`, `file://`, `mailto:`, `#anchor`, or relative paths. Reject `javascript:`, `data:`, `vbscript:`. Strip the attribute if invalid rather than emit `href="#"`.
- `src` / `background-image: url(...)` values: same allowlist; disallow `data:` SVG payloads (they can embed scripts).
- fgraph template placeholders (`{{TITLE}}`, `{{NODE_*}}`, `{{EDGE_*}}`, etc.): HTML-escape any author-supplied text before substitution. The templates ship as trusted markup; the substituted values are the untrusted portion.
```

### HTML structure

```html
<!doctype html>
<html lang="en" data-theme="{dark|light}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{Deck Title}</title>
  <!-- diagram-meta:start -->
  <meta name="diagram:title"     content="{Deck Title}">
  <meta name="diagram:date"      content="{YYYY-MM-DD}">
  <meta name="diagram:category"  content="presentation">
  <meta name="diagram:cat-label" content="Presentation">
  <meta name="diagram:color"     content="{color}">
  <meta name="diagram:badges"    content="latest">
  <!-- diagram-meta:end -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=…" rel="stylesheet">
  <style>
    /* reset.css */
    /* typography.css */
    /* {aesthetic}.css */
    /* slide-deck-base.css */
  </style>
</head>
<body>
  <div class="deck-progress" id="deck-progress"></div>
  <nav class="deck-dots" id="deck-dots" aria-label="Slide navigation"></nav>
  <div class="deck" id="deck">
    <!-- one <section class="slide slide--{type}"> per slide -->
  </div>
  <script type="module">
    /* slide-deck-base.js */
  </script>
</body>
</html>
```

See `slide-patterns.md` for the exact HTML shape of each slide type. Do not re-specify or deviate from those class names — `SlideEngine` resolves `.slide--{type}` and `.reveal` by exact string match.

---

## Phase 4 — Deliver

```
Created:
  ~/.roxabi/forge/{PROJ}/slides/{name}.html

View:    file://~/.roxabi/forge/{PROJ}/slides/{name}.html
         (or: make forge → http://localhost:8080/{PROJ}/slides/{name}.html)
Deploy:  make forge deploy
```

**Print acceptance checklist:**

- [ ] File written to `~/.roxabi/forge/{PROJ}/slides/{name}.html`
- [ ] Slide count: {N} slides (`slide--title` × 1, `slide--closing` × 1, others as planned)
- [ ] Aesthetic applied: `{aesthetic}.css` — `data-theme` matches
- [ ] CSS inline order verified: reset → typography → aesthetic → slide-deck-base
- [ ] `slide-deck-base.js` inlined as `<script type="module">`
- [ ] Scroll-snap: `.deck` has `scroll-snap-type: y mandatory`; each `.slide` has `scroll-snap-align: start`
- [ ] Keyboard nav: `↑`/`↓`, `PgUp`/`PgDn`, `Home`/`End` wired by `SlideEngine`
- [ ] Touch swipe: handled by `SlideEngine` pointer events
- [ ] `prefers-reduced-motion`: `.slide` and `.slide .reveal` transitions disabled via `@media (prefers-reduced-motion: reduce)`
- [ ] diagram-meta block present between `<!-- diagram-meta:start -->` and `<!-- diagram-meta:end -->`
- [ ] CDN allowlist: `fonts.googleapis.com`, `fonts.gstatic.com` (always). No other runtime CDNs — diagram slides inline their fgraph template + `fgraph-base.css`.

---

## Out of Scope (v0.1)

| Feature | Status |
|---|---|
| PDF export | Deferred — `@page` rules conflict with scroll-snap layout |
| Presenter mode (speaker notes + second screen) | Deferred — requires `BroadcastChannel` / `window.open` + postMessage |
| Remote control | Deferred — contradicts offline-first design |
| Pan/zoom in diagram slides | Deferred — presentation use case rarely needs it (fgraph templates cap at 6–8 nodes) |
| WYSIWYG editor | Out of scope — forge generates, not edits |
| Auto-resize on orientation change | Known limitation — manual `F5` refresh is the workaround |

---

$ARGUMENTS
