---
name: forge-presentation
description: >-
  Generate a long-form scroll presentation from an issue, a markdown file, or a
  free prompt. Single-file, offline-playable, hero + numbered sections,
  continuous scroll, reveal animations, and diverse section types. Triggers:
  "create presentation" | "long-form presentation" | "scroll presentation" |
  "forge presentation" | "visual article".
summary: 'long-form scroll presentation'
version: 0.1.0
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, ToolSearch, Agent
---

# Presentation — Long-Form Scroll Document

Generate a single-file HTML long-form presentation from a GitHub issue, a markdown file, or a free prompt. Output is a continuous-scroll document — hero section + numbered sections (§01, §02, ...), reveal animations on scroll, and diverse content types per section. Fully offline under `file://`.

Output: `~/.roxabi/forge/<project>/visuals/{name}.html`

Single-file presentation — all CSS and JS inlined in `{name}.html`. No split-file presentation shell.

**Exception — craft diagram SSoT:** dense premium craft canvases (hub-spoke, fixed geometry, SVG paths) live in sibling files `visuals/diagrams/{slug}.html` and embed via `<iframe class="diagram-frame">`. Relative paths keep `file://` offline safety. **Never** copy diagram CSS into the presentation. Full rules: `${CLAUDE_PLUGIN_ROOT}/references/composition-contract.md`.

**Read before generating:**

```
${CLAUDE_PLUGIN_ROOT}/references/showcase-index.html                  — full catalog of golden refs (read first)
${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md                         — brand detection, output paths, deploy commands
${CLAUDE_PLUGIN_ROOT}/references/composition-contract.md                — presentation × diagram layers (mandatory if any diagram)
${CLAUDE_PLUGIN_ROOT}/references/base/reset.css                       — inline 1st
${CLAUDE_PLUGIN_ROOT}/references/base/typography.css                  — inline 2nd
${CLAUDE_PLUGIN_ROOT}/references/aesthetics/{aesthetic}.css           — inline 3rd (one file, selected by detection)
${CLAUDE_PLUGIN_ROOT}/references/base/explainer-base.css               — inline 4th (scroll layout, sections, cards)
${CLAUDE_PLUGIN_ROOT}/references/base/presentation-shell.css           — inline 5th (hero-wordmark, section-h, kpi, caveat, footer)
${CLAUDE_PLUGIN_ROOT}/references/base/composition.css                 — inline 6th (panel-wrap, arch-wrap, diagram-embed)
${CLAUDE_PLUGIN_ROOT}/references/showcases/showcase-presentation.html   — golden scroll + iframe integration (read first)
${CLAUDE_PLUGIN_ROOT}/references/diagrams/examples/craft-hub-spoke.html — golden craft hub-spoke
${CLAUDE_PLUGIN_ROOT}/references/diagrams/examples/craft-deploy-flow.html — golden promote flow (curve h)
${CLAUDE_PLUGIN_ROOT}/references/diagrams/README.md                   — craft diagram authoring pipeline
${CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-qa-checklist.md        — pre-embed visual gate (mandatory per diagram)
${CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-anchors.js            — inline into each diagrams/*.html
${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md                      — meta tag format + categories
${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md                 — Track A/B detection
${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md                       — silent inference (reader/action/takeaway/tone)
${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md            — track-by-track behavior
${CLAUDE_PLUGIN_ROOT}/references/anti-patterns.md                     — Deliver gate (incl. composition §)
```

**Directive: inline, never link** — presentation CSS files are generation source, not runtime dependencies. Read → inline into the output `<style>` block. The only allowed external requests at runtime are CDN fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) and **relative** `diagrams/*.html` iframes.

**Diagram paths in presentations:**
- **Craft canvas** (>6 nodes, absolute layout, craft legend) → `visuals/diagrams/{slug}.html` + iframe (`craft-diagram` section type). Golden: `references/diagrams/examples/craft-hub-spoke.html`. Starter: `references/diagrams/craft-diagram-starter.html`.
- **fd-engine** (descriptor JSON, validate-fd exit 0) → `forge-chart` output; embed same iframe pattern if inside presentation.
- **≤6 nodes, print-safe** → inline fgraph template + `fgraph-base.css` in presentation `<style>` (no iframe).
- **Tables / forge swimlanes** → `panel-wrap` (not bare `tbl-wrap`).
- **Simple pipelines** → `arch-wrap` + `arch-pipeline`.

---

## Design Phase — Frame → Structure → Style → Deliver

An overlay on Phases 1–4. Frame runs in Phase 1, Structure in Phase 2, Style in Phase 3, Deliver in Phase 4.

### Track selection (Phase 1 start)

Run `${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md` before any other decision:

- **Track A (branded)** — `forge.yml` found → aesthetic/palette/typography locked; `deliver_must_match` rules enforced.
- **Track B (exploration)** — no brand book → full Frame judgment.

Report the loaded brand book (or its absence) before starting Frame. Track is fixed at Phase 1.

Full track-by-track behavior: `${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md`.

### Frame — What's this presentation for?

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md` — three signals, reader-action matrix, tone dimensions.

**For forge-presentation specifically, Signal 1 (reader-action) determines section density.** A presentation for stakeholders needs fewer, more impactful sections with strong visual hierarchy. A presentation for engineers needs denser sections with more data tables, code blocks, and technical detail.

- **Track A:** infer Signal 1 (reader-action) and Signal 2 (takeaway). Tone pre-constrained by brand voice.
- **Track B:** infer Signal 1, Signal 2, and Signal 3 (all tone axes) from prompt and content.

Aesthetic is mechanical, not Frame-chosen. Frame produces purpose, not CSS.

### Structure — Section outline

Produce an in-memory section outline: ordered list of `{index, heading, type, content_notes}` per section.

| Section count guide | Use when |
|---|---|
| 3–5 sections | Single focused topic, brief overview, quick read |
| 6–10 sections (typical) | Feature deep-dive, project analysis, technical walkthrough |
| 11–15 sections | Comprehensive analysis, multi-phase plan, research document |
| Hard cap: 20 | Never exceed — content beyond 20 sections belongs in a multi-tab guide |

Typical sequence: `hero → intro (§01) → core content × 3–6 → [gallery | timeline] → caveats → method → footer`

Section type selection: see `§ Section Types` below.

### Style — CSS inline order

Inline in this order, no exceptions:

1. `reset.css`
2. `typography.css`
3. `{aesthetic}.css` (one file, from `references/aesthetics/`)
4. `explainer-base.css`
5. `composition.css`

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

1. **Detect project** from ARGS or cwd. Unknown → ask: "Which project is this presentation for?"

2. **Run brand book loader** (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`). Report Track A or B before continuing.

3. **Derive `{name}`** (kebab-case ≤30 chars) from issue slug / markdown filename / prompt slug.
   Re-invocation for the same `{PROJ}/{name}` **overwrites silently** — matches `forge-guide`/`forge-epic` deterministic-path behavior. Do not prompt.

4. **Apply Aesthetic Detection** (`forge-ops.md § Aesthetic Detection`). `--aesthetic <name>` override takes precedence. Allowed values: `editorial`, `roxabi`, `blueprint`, `caveman`, `lyra`, `lyra-v2`, `terminal`.

5. **Frame Trace** — emit one-line summary before Phase 2. Not a question; user can interrupt if wrong:
   ```
   Frame: reader={signal1_reader}, action={signal1_action}, takeaway={signal2}, tone={signal3_summary}. Generating...
   ```

---

## Phase 2 — Decision (Section Outline)

Produce the section outline silently (in-memory, no disk write). Each entry: `{index, heading, type, content_notes}`.

### Input extraction rules

| Input | Extract | Maps to |
|---|---|---|
| `#N` | Issue title | Hero wordmark + `<title>` |
| `#N` | Issue body H2 headings | Sections (§01, §02, ...) |
| `#N` | Issue body H2 body paragraphs | Section content |
| `#N` | Issue body code blocks | `code` sections |
| `#N` | Issue body tables | `table` sections |
| markdown path | First H1 | Hero wordmark |
| markdown path | H2 headings | Sections |
| markdown path | H2 body paragraphs | Section content |
| markdown path | Fenced code blocks | `code` sections |
| markdown path | Blockquotes | `quote` cards |
| markdown path | GFM tables or HTML tables | `table` sections |
| markdown path | Markdown images with substantive `alt` | `gallery` sections |
| markdown path | Lists of events with dates | `timeline` sections |
| markdown path | Key-value pairs, metrics | `kpi` sections |
| free prompt | Entire prompt | Hero + intro + content sections + closing |

### Diagram / data decision (Phase 2 — before outline finalizes)

Run the matrix in `composition-contract.md` § Level 7 for every visual block:

| Content signal | Section type | Output |
|---|---|---|
| Craft canvas, spokes, SVG paths | `craft-diagram` | `craft-diagram-starter.html` + `data-anchor` + `#craft-edges` + inline `craft-anchors.js` |
| fd-engine descriptor validates | `craft-diagram` or `architecture` | `forge-chart` HTML in `diagrams/`, embed via iframe |
| Table ± forge swimlane | `panel` | `panel-wrap` in presentation only |
| Linear <7 steps, no geometry | `pipeline` | `arch-wrap` + `arch-pipeline` |
| ≤6 node static topology | `architecture` | inline fgraph in presentation |

### Section types

| Type | When to use | Content shape |
|---|---|---|
| `hero` | First section always | Wordmark, release/date, tagline, optional background image |
| `intro` | Executive summary, overview | 2–3 paragraphs, optional KPI row, optional hero image |
| `content` | Default section type | Heading + paragraphs, optional cards or list |
| `split` | Text + image side by side | `.split` grid with text left, image right |
| `cards` | Multiple related items | Grid of `.modcard` or similar |
| `kpi` | Metrics summary | Row of `.kpi` stat boxes |
| `table` | Structured data | `<table>` with headers |
| `timeline` | Chronological events | `.timeline` with `.tl-item` entries |
| `gallery` | Image grid with lightbox | `.gallery-grid` with `.gfr` items |
| `code` | Code examples | `.codeblock` with syntax highlighting |
| `architecture` | System diagrams ≤6 nodes | Inline fgraph SVG or layered node diagram |
| `craft-diagram` | Craft hub-spoke / swimlane canvas | iframe → `diagrams/{slug}.html` (SSoT); title inside diagram only |
| `panel` | Tables + related swimlanes | `panel-wrap` + `panel-head` + `tbl-wrap` / `.swimlanes` |
| `trinity` | Three related concepts | `.trinity` with 3 cards |
| `pipeline` | Linear flow diagram | `.pipeline` with inputs → output |
| `quote` | Chapter breaks, pull quotes | `.chapter-card` with quote text |
| `caveats` | Limitations, warnings | `.caveat-grid` with warning/ok cards |
| `method` | How this was made | `.method` with key-value pairs |
| `footer` | Last section always | Brand wordmark, date, meta links |

### Meta values

| Field | Value |
|---|---|
| `diagram:category` | `analysis` or appropriate category from `diagram-meta.md` |
| `diagram:cat-label` | Matching label |
| `diagram:color` | match project (amber=warm, gold=Roxabi, cyan=Blueprint, etc.) |
| `diagram:badges` | `latest` |
| `diagram:issue` | issue number if input was `#N`, else omit |

---

## Phase 3 — Generation

Always delegate to a sub-agent when total output exceeds ~300 lines. A presentation with 6+ sections will always exceed this threshold — **always delegate Phase 3 to a sub-agent**.

### Craft diagram sub-workflow (per `craft-diagram` section)

Execute **before** wiring the presentation iframe:

1. Copy `${CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-diagram-starter.html` → `visuals/diagrams/{slug}.html`
2. Set `data-slug`, `diagram:title`, title block copy
3. Place hub/spokes with CSS — each node gets `data-anchor="{id}"`
4. Set `data-canvas-width` / `data-canvas-height` on `.diagram`
5. Edit `#craft-edges` JSON only for connections (`curve`: `q` hub-spoke, `h` promote flows)
6. Ensure `craft-anchors.js` is inlined (starter includes it)
7. Inline brand icon `<symbol>` blocks — no external `brand-icons.svg` refs
8. Run `python3 ~/.roxabi/forge/scripts/check-craft-diagram.py visuals/diagrams/{slug}.html --check`
9. Open `file://` + walk `craft-qa-checklist.md`
10. Then embed iframe in presentation

**Forbidden on craft diagrams:** hand-coded `<path d="…">` that will desync when spokes move; negative `left`/`right` on spoke/hub anchors (badges inside nodes OK); >6 anchors without splitting diagram (warn only if density still readable).

**postMessage contract:** diagrams emit `{ type: 'forge-diagram-resize', id: '{slug}.html', height }`; presentation listener filters on `forge-diagram-resize` and matches `iframe.src` to `e.data.id`.

### Sub-agent prompt template

```
Generate forge-presentation output (single-file HTML long-form scroll).

Decisions (from Phase 1–2):
- Track: {A|B}
- Aesthetic: {aesthetic}.css
- Input: {#N | path | prompt}
- Section count: {N}
- Section outline: {ordered list of type + heading + content_notes}
- Output path: ~/.roxabi/forge/{PROJ}/visuals/{name}.html
- data-theme: {dark|light}

Read these reference files IN ORDER:
- {CLAUDE_PLUGIN_ROOT}/references/composition-contract.md
- {CLAUDE_PLUGIN_ROOT}/references/base/reset.css
- {CLAUDE_PLUGIN_ROOT}/references/base/typography.css
- {CLAUDE_PLUGIN_ROOT}/references/aesthetics/{aesthetic}.css
- {CLAUDE_PLUGIN_ROOT}/references/base/explainer-base.css
- {CLAUDE_PLUGIN_ROOT}/references/base/composition.css
- {CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md
- {CLAUDE_PLUGIN_ROOT}/references/diagrams/README.md (if any craft-diagram section)
- {CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-qa-checklist.md (mandatory per craft diagram)
- {CLAUDE_PLUGIN_ROOT}/references/showcases/showcase-presentation.html (golden integration)
- {CLAUDE_PLUGIN_ROOT}/references/diagrams/examples/craft-hub-spoke.html (golden craft)
- {CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-diagram-starter.html (copy base per craft section)
- {CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-anchors.js (inline verbatim into each diagrams/*.html)

Then generate:
  ~/.roxabi/forge/{PROJ}/visuals/{name}.html
  ~/.roxabi/forge/{PROJ}/visuals/diagrams/*.html (one per craft-diagram section)

Rules:
- Presentation single file — inline CSS: reset → typography → aesthetic → explainer-base → composition
- Craft diagrams: separate visuals/diagrams/{slug}.html — NEVER inline craft canvas CSS in presentation
- iframe: figure.diagram-embed without nested .reveal; no figcaption when diagram has title
- Hero section first: wordmark, release/date line, tagline, scroll indicator
- Fixed nav with section links (optional, skip if ≤4 sections)
- Sections: §01, §02, §03... with `.section-h` heading structure
- Add class="reveal" to sections and major elements for scroll animations
- Include inline <script> for IntersectionObserver reveal + optional lightbox
- craft-diagram sections: iframe to diagrams/{slug}.html; section-scoped #id .diagram-frame { border:none; background:transparent }
- craft diagrams: data-slug="{slug}.html" must match iframe src filename; edges only in #craft-edges JSON — never hand-coded <path d=>
- craft diagrams: postMessage type forge-diagram-resize (presentation listener must use same type)
- architecture sections (≤6 nodes): inline fgraph template + fgraph-base.css into <style>
- panel sections: panel-wrap not bare tbl-wrap
- Before deliver: python3 ~/.roxabi/forge/scripts/check-craft-diagram.py on each diagrams/*.html --check; check-composition.py on presentation if diagram-embed present
- Inject diagram-meta block in <head> (see diagram-meta.md)
- data-theme="{dark|light}" on <html>
- Footer section last: brand wordmark, date, meta links

**Escape rules (load-bearing — prevents XSS from untrusted source content):**
- All text content derived from issue body / markdown / prompt → HTML-escape (`&` `<` `>` `"` `'`) before inserting into element text nodes.
- `href` values (links, image source URLs): allow only schemes `https://`, `http://`, `file://`, `mailto:`, `#anchor`, or relative paths. Reject `javascript:`, `data:`, `vbscript:`. Strip the attribute if invalid rather than emit `href="#"`.
- `src` / `background-image: url(...)` values: same allowlist; disallow `data:` SVG payloads.
- fgraph template placeholders: HTML-escape any author-supplied text before substitution.
```

### HTML structure

```html
<!doctype html>
<html lang="en" data-theme="{dark|light}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{Presentation Title}</title>
  <!-- diagram-meta:start -->
  <meta name="diagram:title"     content="{Title}">
  <meta name="diagram:date"      content="{YYYY-MM-DD}">
  <meta name="diagram:category"  content="{category}">
  <meta name="diagram:cat-label" content="{Label}">
  <meta name="diagram:color"     content="{color}">
  <meta name="diagram:badges"    content="latest">
  <!-- diagram-meta:end -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=..." rel="stylesheet">
  <style>
    /* reset.css */
    /* typography.css */
    /* {aesthetic}.css */
    /* explainer-base.css */
  </style>
</head>
<body>

<!-- NAV (fixed, optional) -->
<nav class="topnav">...</nav>

<!-- HERO -->
<section class="hero">
  <div class="hero-left">
    <div class="eyebrow">...</div>
    <div class="hero-wordmark">{Title}<sup>3</sup></div>
    <div class="hero-release">{DATE}</div>
    <div class="hero-tagline">{Tagline}</div>
  </div>
  <div class="hero-right"><!-- optional background --></div>
  <div class="hero-scroll">↓ scroll</div>
</section>

<!-- SECTION §01 -->
<section id="section-1" class="reveal">
  <div class="section-h">
    <div class="section-n">§ 01</div>
    <div>
      <div class="eyebrow">...</div>
      <div class="section-title">...</div>
      <div class="section-sub">...</div>
    </div>
  </div>
  <!-- content -->
</section>

<!-- More sections... -->

<!-- FOOTER -->
<footer>
  <div class="foot-brand">{Title}</div>
  <div class="foot-date">— {DATE}</div>
  <div class="foot-meta">...</div>
</footer>

<!-- LIGHTBOX (if gallery sections present) -->
<div class="lightbox" id="lb">...</div>

<script>
  // Reveal on scroll
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));

  // iframe height: data-height fallback + optional postMessage from diagrams
  document.querySelectorAll('.diagram-frame').forEach(function (iframe) {
    var h = parseInt(iframe.dataset.height || '400', 10);
    iframe.style.height = h + 'px';
  });
  window.addEventListener('message', function (e) {
    if (!e.data || e.data.type !== 'forge-diagram-resize') return;
    document.querySelectorAll('.diagram-frame').forEach(function (iframe) {
      if (iframe.src && iframe.src.includes(e.data.id)) {
        iframe.style.height = Math.max(e.data.height, parseInt(iframe.dataset.height || '200', 10)) + 'px';
      }
    });
  });

  // Lightbox (optional)
  // ...
</script>
</body>
</html>
```

---

## Phase 4 — Deliver

```
Created:
  ~/.roxabi/forge/{PROJ}/visuals/{name}.html

View:    file://~/.roxabi/forge/{PROJ}/visuals/{name}.html
         (or: make forge → http://localhost:8080/{PROJ}/visuals/{name}.html)
Deploy:  make forge deploy
```

**Print acceptance checklist:**

- [ ] File written to `~/.roxabi/forge/{PROJ}/visuals/{name}.html`
- [ ] Section count: {N} sections (hero + §01...§XX + footer)
- [ ] Aesthetic applied: `{aesthetic}.css` — `data-theme` matches
- [ ] CSS inline order verified: reset → typography → aesthetic → explainer-base → composition
- [ ] Reveal animations: `.reveal` on sections; IntersectionObserver adds `.visible` (not `.v`)
- [ ] Craft diagrams: `data-anchor` + `#craft-edges` + inlined `craft-anchors.js` (no orphan hardcoded paths)
- [ ] `check-craft-diagram.py --check` exit 0 on each `diagrams/*.html`
- [ ] Composition: no inline `.craft-embed`; craft diagrams in `diagrams/*.html` + iframe
- [ ] `check-composition.py --check` exit 0 (if any diagram-embed present)
- [ ] Hero section: wordmark + release date + tagline + scroll indicator
- [ ] Sections numbered: §01, §02, §03... with `.section-h` structure
- [ ] `prefers-reduced-motion`: transitions disabled via `@media (prefers-reduced-motion: reduce)`
- [ ] diagram-meta block present between `<!-- diagram-meta:start -->` and `<!-- diagram-meta:end -->`
- [ ] CDN allowlist: `fonts.googleapis.com`, `fonts.gstatic.com` (always). No other runtime CDNs — diagram sections inline their fgraph template + CSS.
- [ ] Lightbox wired if gallery sections present

---

## Out of Scope (v0.1)

| Feature | Status |
|---|---|
| PDF export | Deferred — requires separate print stylesheet |
| Multi-tab variant | Deferred — use `forge-guide` for tab-based docs |
| Auto-generated diagrams from text | Deferred — use explicit `craft-diagram` / `architecture` sections + composition matrix |
| WYSIWYG editor | Out of scope — forge generates, not edits |

---

$ARGUMENTS
