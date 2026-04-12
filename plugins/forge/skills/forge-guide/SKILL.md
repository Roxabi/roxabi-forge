---
name: forge-guide
description: 'Create a split-file multi-tab HTML document — user guide, architecture overview, project recap, comparison analysis, roadmap, or any rich multi-section doc. Triggers: "write a guide" | "create a guide" | "forge guide" | "multi-tab doc" | "visual doc" | "create a doc" | "make a recap" | "illustrate architecture" | "explain visually" | "document with forge".'
version: 0.3.0
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, ToolSearch
---

# Guide — Split-File Multi-Tab Document

Create any rich multi-section HTML document as a split-file: shell HTML + CSS + JS + tab fragments.
Output: `~/.roxabi/forge/<project>/visuals/` (exploration) or `~/projects/<project>/docs/visuals/` (final).

Covers: user guides, architecture overviews, project recaps, analysis/comparison matrices, roadmaps, feature plans, review reports.

**Read before generating:**

```
${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md        — brand detection, output paths, deploy commands
${CLAUDE_PLUGIN_ROOT}/references/base/reset.css      — concatenate first
${CLAUDE_PLUGIN_ROOT}/references/base/layout.css     — concatenate second
${CLAUDE_PLUGIN_ROOT}/references/base/typography.css — concatenate third
${CLAUDE_PLUGIN_ROOT}/references/base/components.css — concatenate fourth
${CLAUDE_PLUGIN_ROOT}/references/base/explainer-base.css — concatenate fifth (visual explainer components)
${CLAUDE_PLUGIN_ROOT}/references/aesthetics/         — select one based on detection logic
${CLAUDE_PLUGIN_ROOT}/references/shells/split.html   — HTML template with placeholders
${CLAUDE_PLUGIN_ROOT}/references/base/tab-loader.js    — substitute {NAME}, then inline via {TAB_LOADER_JS}
${CLAUDE_PLUGIN_ROOT}/references/base/theme-toggle.js — substitute {NAME}, then inline via {THEME_TOGGLE_JS}
${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md     — meta tag format + categories
${CLAUDE_PLUGIN_ROOT}/references/mermaid-guide.md    — only if a tab will contain a Mermaid diagram
${CLAUDE_PLUGIN_ROOT}/references/shape-vocabulary.md — if content has diagrams: semantic shape selection guide
${CLAUDE_PLUGIN_ROOT}/references/graph-templates/README.md — if content has diagrams: fgraph decision matrix + templates
```

**Directive: inline, never link** — `base/` and `aesthetics/` files are generation source, not runtime dependencies. Read → inline into output `<style>` block. Exception: `fgraph-base.css` is linked (not inlined) via `<link rel="stylesheet" href="../../_shared/fgraph-base.css">` when any tab uses fgraph diagrams — see `shell-processing.md § fgraph integration`.

---

## Design Phase — Frame → Structure → Style → Deliver

Decisions made across Phases 1–4 follow this lens. It is an overlay on the procedural phases, not a separate pre-phase: Frame runs in Phase 1 (context + aesthetic detection), Structure in Phase 2 (tab planning), Style in Phase 3 (generate), Deliver in Phase 4 (report + verify).

### Track selection (Phase 1 start)

Run the brand book loader (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`) before any other decision:

- **Track A (branded)** — `forge.yml` found in project `brand/` → aesthetic/palette/typography locked; components pre-filled; `deliver_must_match` rules enforced at Deliver.
- **Track B (exploration)** — no brand book → full Frame judgment; Frame output drives aesthetic fallback via `forge-ops.md § Aesthetic Detection` priority 5.

Full track-by-track behavior: `${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md`.

Report the loaded brand book (or its absence) before starting Frame. Track is fixed at Phase 1 and does not change.

### Frame — What's this visual for?

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md` — three Frame questions, reader-action matrix, tone dimensions, example trace.

**For forge-guide specifically, Q2 (the ONE takeaway) is the most useful prompt.** A guide is a multi-tab document with multiple sections — without a committed Q2 takeaway, the tab set sprawls and the reader loses the thread. State Q2 in one sentence before picking tabs. If you can't, the scope is too wide — split into multiple guides.

- **Track A:** ask Q1 (reader-action) and Q2 (takeaway). **Skip Q3 (tone)** — tone is pre-constrained by brand voice rules in `deliver_must_match`. Q4 optional.
- **Track B:** ask Q1, Q2, and full Q3 (all four tone axes). Frame output produces a content-type signal for Aesthetic Detection priority 5.

Aesthetic is never chosen by Frame — it's mechanical (see `forge-ops.md § Aesthetic Detection`). Frame produces purpose, not CSS.

### Structure — Which rendering approach?

| Content | Rendering |
|---|---|
| Layered architecture (3–4 tiers) | fgraph `layered.html` — horizontal layers with dashed frames |
| Linear pipeline (2–4 stages) | fgraph `linear-flow.html` — source → middle → sink |
| Hub-and-spoke ≤ 6 peers with rich cards | fgraph `radial-hub.html` — center pill + satellites |
| Peer ring (no center hub) | fgraph `radial-ring.html` — N nodes in a circle |
| Multi-host / distributed deployment | fgraph `machine-clusters.html` — side-by-side frames |
| Flow / topology / > 8 nodes | Mermaid `flowchart` (dagre auto-layout) |
| Stacked **text-heavy** pipelines (paragraphs per stage) | CSS Grid cards |
| Data comparison (≥4 rows or ≥3 cols) | HTML tables |
| Single-page audit / long-form | TOC sidebar layout |

**Key distinction:** if the content is structural (nodes + edges + labels + badges), use fgraph even inside a guide. CSS Grid cards are for text-heavy content where each stage has paragraphs, not for topology diagrams with slot badges. Read `${CLAUDE_PLUGIN_ROOT}/references/shape-vocabulary.md` to pick the right shape per node.

**Ask:** Is the content scannable (headings + lists + tables) or narrative (paragraphs + inline diagrams)? Scannable → TOC sidebar or multi-tab with stat-grid heroes. Narrative → flat long-form with inline diagrams. A guide that is both scannable and narrative is a sign of unclear Frame Q2 — one takeaway can be skimmed *or* read, not both.

### Style — Which components?

All classes below exist in `base/components.css` + `base/explainer-base.css`. Rows are keyed on **doc type** (what the guide is) — rendering wrappers are orthogonal and listed separately below.

- **Track A:** `brand.components.hero` / `.section_label` / `.card_default` pre-fill the matching slots in the row for your doc type. Override only when content has no valid rendering using the brand default (see `design-phase-two-track.md § Style`).
- **Track B:** pick the row that matches your doc type. Frame tone drives variant selection when multiple rows apply.

| Doc type | Hero | Sections | Cards |
|---|---|---|---|
| User guide | `.hero.left-border` | `.section-label.dot` | `.card` (generic) |
| Architecture | `.hero.elevated` | `.section-label.square` | `.card.accent` (accent border-left) |
| Status / recap | `.hero` + `.stat-grid` | `.section-label.triangle` | `.phases` + `.phase-card.p1..p4` |
| Audit / review | `.hero.elevated` + `.verdict-badge` | `.section-label.dot` | `.finding.finding--high/medium/low` |
| Analysis / comparison | `.hero.left-border` | `.section-label.dot` | `.card` grid + `.table-wrap > table` |

**Rendering wrappers** — orthogonal to doc type. Apply these to whatever rendering the Structure phase chose:

| Rendering | Wrapper / component |
|---|---|
| Mermaid (any type) | `.diagram-shell` with `.zoom-controls` (never bare `<pre class="mermaid">`) |
| fgraph (any template) | `.fgraph-wrap.{tone}` + `.fgraph-edges` SVG + `.fgraph-node.{shape}.{tone}` (see `graph-templates/` + `shape-vocabulary.md`). Link `fgraph-base.css` in shell `<head>`. Use semantic shapes: `.cylinder` for data stores, `.hexagon` for agents, `.pill` for brokers, `.folded` for files, `.diamond` for decisions, `.circle` for events. |
| HTML table | `.table-wrap > table` with `<thead>` (enables sticky header + horizontal scroll) |
| CSS Grid cards | `.cards` container + `.card`/`.card.accent` per row |
| TOC sidebar | `.wrap--toc > .toc + .main--toc` layout (see Phase 3 TOC Sidebar section) |

Cross-doc: use `.card.info` / `.card.warning` / `.card.critical` for inline tonal callouts.

**Ask:** What visual hierarchy does this need? Quick scan → `.stat-grid`. Deep dive → `.finding` cards by severity. Ordered walk → `.phases`. Data compare → `.table-wrap > table`. Pick one — if two apply equally, the Frame Q2 takeaway is underspecified.

### Deliver — Generate + verify

**Always** (both tracks):
- Hero section present with eyebrow + title accent + subtitle.
- Section titles use `.section-title` or `.section-label` (never plain `<h2>`).
- Mermaid (if used) wrapped in `.diagram-shell` — never bare `<pre class="mermaid">`.
- **Body copy uses `var(--text)` for maximum readability on dark backgrounds.** `var(--text-muted)` is for intermediate emphasis only (subtitles, label rows); `var(--text-dim)` is for metadata only.
- No ASCII art, no emoji in headers.
- Tab buttons have `role="tab"` + `aria-selected` semantics.
- Interactive controls (theme toggle, zoom, tab buttons) have visible `:focus-visible` styling.
- Color pairs used for body copy meet 4.5:1 contrast (AAA when possible).
- Mermaid container is responsive — no horizontal scroll below 375px viewport.
- Verify Frame Q2 takeaway is visually emphasized in the Overview tab — the reader should spot it within 10 seconds of landing.

**Track A additionally:**
- Run every `brand.deliver_must_match` rule against the generated tab fragments and shell. Report pass/fail per rule with the tab/line location. Do not write any file until all rules pass or the user explicitly overrides a failing rule.
- If `brand.examples` list is non-empty, offer to visually diff the generated output against one canonical example tab before writing.

**If the doc has a TOC sidebar (audit / long-form):**
- TOC scroll observer wired (see Phase 3).
- Sections have stable `id` anchors matching TOC links.

---

## Shell Processing

Follow `${CLAUDE_PLUGIN_ROOT}/references/shell-processing.md` — the shared split-file pipeline.

**Guide-specific overrides:**

| Placeholder | Value |
|---|---|
| `{NAME}` | diagram slug |
| `{TITLE}` | free-form title from ARGS |
| `{EXTRA_STYLES}` | guide-specific CSS additions (if any) |

Let:
  ARGS := $ARGUMENTS
  AG   := `~/.roxabi/forge/`

---

## Phase 1 — Context Discovery

1. **Detect project** from ARGS or cwd. Unknown → DP(B). (See `forge-ops.md` for detection signals.)

2. **Run the brand book loader** (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`): Discovery → Parse → Apply. Determine Track A or Track B. Report the result before continuing.

3. **Output root** — follow `forge-ops.md` output paths.

4. **Slug** (kebab-case ≤30 chars). Check existing versions:
   ```bash
   ls {ROOT}/{SLUG}*.html 2>/dev/null
   ```
   ∃ v<N> → propose vN+1 and offer to mark old version `archived` in its meta.

5. **Apply the Aesthetic Detection precedence algorithm** (see `${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md` § Aesthetic Detection) to select the correct aesthetic file.

---

## Phase 2 — Structure

1. **Choose `diagram:category`** based on content type (from `${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md`):
   - User guide / tutorial → `guide`
   - Architecture / system design → `architecture`
   - Comparison / competitive analysis → `analysis`
   - Roadmap / implementation plan → `plan`
   - Status update / progress summary → `recap`
   - Code / design audit → `review`

2. **Plan tabs.** Propose from ARGS topic + confirm. Common sets:

   | Doc type | Typical tabs |
   |----------|-------------|
   | User guide | qs, setup, usage, agents, voice, architecture |
   | Architecture | overview, components, flow, deployment |
   | Analysis / comparison | overview, matrix, gaps, verdict |
   | Recap / status | summary, progress, decisions, next |
   | Roadmap | overview, phases, deps, risks |

3. **Inventory diagrams.** For each diagram or architectural visual in the source content:
   - Name it (e.g. "3-layer stack", "model runtime chain")
   - Count nodes and classify topology (layered / linear / radial / nested / grid)
   - Pick rendering: fgraph template | CSS Grid cards | Mermaid | table
   - If fgraph: note which shapes per node using `${CLAUDE_PLUGIN_ROOT}/references/shape-vocabulary.md` (cylinder, hexagon, pill, folded, diamond, circle, default rect)
   - If Mermaid: follow `${CLAUDE_PLUGIN_ROOT}/references/mermaid-guide.md` checklist
   Report the diagram inventory before proceeding to Phase 3. Do not write custom CSS for diagrams that have fgraph equivalents.

4. **Determine layout mode:**
   - **Standard multi-tab** — nav with tabs, panels switch on click
   - **Mono-page with TOC sidebar** — single panel with sticky TOC navigation (for audits, long-form docs)

---

## Phase 3 — Generate

**File paths:**
```
{ROOT}/{SLUG}.html
{ROOT}/css/{SLUG}.css
{ROOT}/js/{SLUG}.js
{ROOT}/tabs/{SLUG}/tab-{ID}.html    ← one per tab
```

Read `shells/split.html` → substitute placeholders. The shell contains all structure.

**Shell HTML:** diagram-meta block, Google Fonts link, CSS link, nav with tab buttons + theme toggle, panel placeholders, JS script.

**CSS file:** write `{BASE_STYLES}` (concatenated base CSS) + `{AESTHETIC_STYLES}` (aesthetic CSS) + any guide-specific styles to `{ROOT}/css/{SLUG}.css`.

**JS file:** write `{TAB_LOADER_JS}` (tab-loader.js with `{NAME}` substituted) + Mermaid init (if needed) to `{ROOT}/js/{SLUG}.js`.

### Header (REQUIRED for multi-tab)

Replace the plain nav title with a styled header:

```html
<header>
  <div class="header-eyebrow">{{EYEBROW}}</div>
  <h1>{{TITLE_PLAIN}} <span class="accent">{{TITLE_ACCENT}}</span></h1>
  <div class="header-subtitle">{{SUBTITLE}}</div>
  <div class="header-row">
    <span class="verdict-badge green">✓ {{BADGE_1}}</span>
    <span class="verdict-badge amber">⚠ {{BADGE_2}}</span>
  </div>
</header>
<nav class="topnav" aria-label="Main">
  <div class="tabs" role="tablist">
    {TABS}
  </div>
  <button class="theme-btn" id="theme-toggle" ...>◑ light</button>
</nav>
```

### TOC Sidebar (for mono-page guides)

For audit-style or long-form single-page docs, use the TOC sidebar layout:

```html
<div class="wrap--toc">
  <aside class="toc">
    <div class="toc-title">Contents</div>
    <a href="#overview">Overview</a>
    <a href="#section-1">1. Section Name</a>
    <a href="#section-2">2. Another Section</a>
  </aside>
  <main class="main--toc">
    <!-- content here -->
  </main>
</div>
```

Add TOC scroll observer to `{EXTRA_SCRIPTS}`:

```javascript
// TOC scroll observer
const tocLinks = document.querySelectorAll('.toc a')
const sections = document.querySelectorAll('.sec-head')
const observer = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      tocLinks.forEach(l => l.classList.remove('active'))
      const id = e.target.getAttribute('id')
      document.querySelector(`.toc a[href="#${id}"]`)?.classList.add('active')
    }
  })
}, { rootMargin: '-20% 0px -80% 0px' })
sections.forEach(s => observer.observe(s))
```

### Section Titles (REQUIRED)

Use styled section titles instead of plain `<h2>`:

```html
<div class="section-title">2.1 — Section Name</div>
```

Or with section label:

```html
<div class="section-label dot">1.1</div>
<h2>Section Name</h2>
```

### Finding Cards (for audit-style content)

For code/design reviews, use finding cards with severity:

```html
<div class="finding finding--high">
  <div class="finding-header">
    <span class="badge badge--risk high">HIGH</span>
    <span class="finding-title">{{ISSUE_TITLE}}</span>
  </div>
  <div class="finding-body">{{DESCRIPTION}}</div>
  <div class="finding-files"><code>{{FILE_NAME}}</code></div>
</div>
```

Severity levels: `finding--high` (red), `finding--medium` (amber), `finding--low` (cyan).

### Stat Grid (for overview tabs)

```html
<div class="stat-grid">
  <div class="stat">
    <span class="stat__value">{{NUMBER}}</span>
    <span class="stat__label">{{LABEL}}</span>
  </div>
</div>
```

### Diagram Shell (REQUIRED for Mermaid tabs)

**NEVER use bare `<pre class="mermaid">`.** Always wrap in the diagram shell:

```html
<div class="diagram-shell">
  <div class="zoom-controls">
    <button data-zoom="in" title="Zoom in">+</button>
    <button data-zoom="fit" title="Fit">⤢</button>
    <button data-zoom="out" title="Zoom out">−</button>
  </div>
  <div class="mermaid-container" data-mermaid-out id="diagram-{{TAB_ID}}"></div>
  <script type="text/plain" data-mermaid>
    {{MERMAID_SOURCE}}
  </script>
</div>
```

See `${CLAUDE_PLUGIN_ROOT}/references/mermaid-guide.md` for the full checklist on dynamic tab rendering.

### Tab fragments — content patterns by tab type:

| Tab type | Content |
|----------|---------|
| Overview / intro | Header + `<p>` + `.stat-grid` + `.cards` grid (2–4 cards) |
| Step-by-step | Section titles + `<ol>` + `<pre><code>` |
| Architecture | Section title + fgraph diagram (`.fgraph-wrap` with semantic shapes) or Mermaid (in `.diagram-shell`) + description |
| Comparison | Section title + `.table-wrap > table` with `<thead>` |
| Status / KPIs | Section title + `.stat-grid` + progress indicators |
| Decisions / log | `<h3>` entries with date + rationale `<p>` |
| Audit / Review | TOC sidebar + `.finding` cards by severity |

**Dark mode text — always:**
- Paragraphs, list items, card body → `color: var(--text-muted)` (`#9ca3af`)
- Column headers, dates, metadata → `color: var(--text-dim)` (`#6b7280`)

---

## Anti-Patterns (FORBIDDEN)

| Anti-Pattern | Fix |
|--------------|-----|
| Bare `<pre class="mermaid">` | Use diagram shell with `.mermaid-wrap` |
| ASCII art in `<pre class="arch">` | Convert to Mermaid flowchart or fgraph |
| Emoji in headers | Remove — use text only |
| `rgba()` in Mermaid `style` directives | Use hex colors only |
| `theme: 'dark'` in Mermaid config | Use `theme: 'base'` + custom `themeVariables` |
| Plain `<h2>` for section titles | Use `.section-title` class |
| No header on multi-tab | Add styled header with eyebrow + badges |
| Plain nav title only | Replace with full header component |
| Custom CSS for diagrams with fgraph equivalents | Use fgraph templates + `shape-vocabulary.md` — link `fgraph-base.css`, do not reinvent |

---

## Phase 4 — Report

```
Created:
  {ROOT}/{SLUG}.html
  {ROOT}/css/{SLUG}.css
  {ROOT}/js/{SLUG}.js
  {ROOT}/tabs/{SLUG}/tab-{ID}.html  (×N)

View:    make forge → http://localhost:8080/{PROJ}/visuals/{SLUG}.html
         (or: cd ~/.roxabi/forge && python3 -m http.server 8080)
Deploy:  make forge deploy
```

$ARGUMENTS
