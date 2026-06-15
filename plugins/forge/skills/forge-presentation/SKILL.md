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

Single-file — all CSS and JS inlined. No split-file, no external links at runtime (except CDN fonts). This is the correct distribution rule for `file://` offline safety; see CLAUDE.md § Distribution Rule.

**Read before generating:**

```
${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md                         — brand detection, output paths, deploy commands
${CLAUDE_PLUGIN_ROOT}/references/base/reset.css                       — inline 1st
${CLAUDE_PLUGIN_ROOT}/references/base/typography.css                  — inline 2nd
${CLAUDE_PLUGIN_ROOT}/references/aesthetics/{aesthetic}.css           — inline 3rd (one file, selected by detection)
${CLAUDE_PLUGIN_ROOT}/references/base/explainer-base.css               — inline 4th (scroll layout, sections, cards)
${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md                      — meta tag format + categories
${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md                 — Track A/B detection
${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md                       — silent inference (reader/action/takeaway/tone)
${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md            — track-by-track behavior
```

**Directive: inline, never link** — presentation CSS files are generation source, not runtime dependencies. Read → inline into the output `<style>` block. The only allowed external requests at runtime are CDN fonts (`fonts.googleapis.com`, `fonts.gstatic.com`). Diagram sections inline their fgraph template + `fgraph-base.css` directly — no diagram runtime, no CDN.

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
| `architecture` | System diagrams | Inline fgraph SVG or layered node diagram |
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
| `diagram:color` | match project (amber=Lyra, gold=Roxabi, cyan=Blueprint, etc.) |
| `diagram:badges` | `latest` |
| `diagram:issue` | issue number if input was `#N`, else omit |

---

## Phase 3 — Generation

Always delegate to a sub-agent when total output exceeds ~300 lines. A presentation with 6+ sections will always exceed this threshold — **always delegate Phase 3 to a sub-agent**.

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
- {CLAUDE_PLUGIN_ROOT}/references/base/reset.css
- {CLAUDE_PLUGIN_ROOT}/references/base/typography.css
- {CLAUDE_PLUGIN_ROOT}/references/aesthetics/{aesthetic}.css
- {CLAUDE_PLUGIN_ROOT}/references/base/explainer-base.css
- {CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md

Then generate one file:
  ~/.roxabi/forge/{PROJ}/visuals/{name}.html

Rules:
- Single file — inline all CSS in order: reset → typography → aesthetic → explainer-base
- Hero section first: wordmark, release/date line, tagline, scroll indicator
- Fixed nav with section links (optional, skip if ≤4 sections)
- Sections: §01, §02, §03... with `.section-h` heading structure
- Add class="reveal" to sections and major elements for scroll animations
- Include inline <script> for IntersectionObserver reveal + optional lightbox
- diagram sections: inline the fgraph template HTML + inline fgraph-base.css content into the <style> block
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
      if (e.isIntersecting) { e.target.classList.add('v'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));

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
- [ ] CSS inline order verified: reset → typography → aesthetic → explainer-base
- [ ] Reveal animations: `.reveal` class on sections, IntersectionObserver in `<script>`
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
| Auto-generated diagrams from text | Deferred — requires explicit diagram sections |
| WYSIWYG editor | Out of scope — forge generates, not edits |

---

$ARGUMENTS
