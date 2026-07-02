---
name: forge-guide
description: >-
  Create a split-file multi-tab HTML document — user guide, architecture
  overview, project recap, comparison analysis, roadmap, or any rich
  multi-section doc. Triggers: "write a guide" | "create a guide" | "forge
  guide" | "multi-tab doc" | "visual doc" | "create a doc" | "make a recap"
  | "illustrate architecture" | "explain visually" | "document with forge".
summary: 'split-file multi-tab doc'
version: 0.3.1
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, ToolSearch, Agent
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

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md` — three Frame signals, reader-action matrix, tone dimensions, example trace.

**For forge-guide specifically, Signal 2 (the ONE takeaway) is the most critical to infer.** A guide is a multi-tab document with multiple sections — without a committed Signal 2 takeaway, the tab set sprawls and the reader loses the thread. Commit to it in one sentence internally before picking tabs. If the content scope is too wide to express in one sentence, split into multiple guides.

- **Track A:** infer Signal 1 (reader-action) and Signal 2 (takeaway) from the prompt. Tone is pre-constrained by brand voice rules in `deliver_must_match` — no tone inference needed.
- **Track B:** infer Signal 1, Signal 2, and full Signal 3 (all four tone axes) from the prompt and content. Frame output produces a content-type signal for Aesthetic Detection priority 5.

Aesthetic is never chosen by Frame — it's mechanical (see `forge-ops.md § Aesthetic Detection`). Frame produces purpose, not CSS.

### Structure — Which rendering approach?

| Content | Rendering |
|---|---|
| **Architecture / hub-spoke / layered / multi-host / linear / ring — any node-edge topology, any scale** | **fd-engine** `type:"architecture"` or `type:"hub-spoke"` + `scripts/gen-fd.py` + `validate-fd.py` (same pipeline as `forge-chart`); add `useCases[]` / `zones[]` as needed |
| Flow / pipeline / sequence / lifecycle | `lane-swim.html` (multi-actor / API sequence — preferred) · `layered.html` / `linear-flow.html` for simple layered flow |
| **Static fgraph propositions** (print / no-JS only) | `radial-hub` · `radial-ring` · `linear-flow` · `layered` / `deployment-tiers` · `machine-clusters` — hand-assigned `--x/--y`; prefer fd-engine whenever density or interactivity matters |
| Issue dependency graph | fgraph `dep-graph.html` — fed by `scripts/gen-deps.py` |
| Dense topology that does not fit one tab | Split across tab fragments **or** one fd-engine descriptor per diagram |
| Stacked **text-heavy** pipelines (paragraphs per stage) | CSS Grid cards |
| Data comparison (≥4 rows or ≥3 cols) | HTML tables |
| Single-page audit / long-form | TOC sidebar layout |

**Key distinction:** structural topology (nodes + edges) → **fd-engine + `gen-fd.py`** when ≥ 7 nodes or interactive; fgraph only for ≤ 6 node static diagrams. CSS Grid cards are for text-heavy stages with paragraphs, not slot-badge topology. Shape vocabulary: `${CLAUDE_PLUGIN_ROOT}/references/shape-vocabulary.md`. Full routing: `forge-chart/SKILL.md`.

**Check:** Is the content scannable (headings + lists + tables) or narrative (paragraphs + inline diagrams)? Scannable → TOC sidebar or multi-tab with stat-grid heroes. Narrative → flat long-form with inline diagrams. A guide that is both scannable and narrative is a sign of underspecified Frame Signal 2 — one takeaway can be skimmed *or* read, not both.

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
| fgraph (any template) | `.fgraph-wrap.{tone}` + `.fgraph-edges` SVG + `.fgraph-node.{shape}.{tone}` (see `graph-templates/` + `shape-vocabulary.md`). Link `fgraph-base.css` in shell `<head>` (Mode B — multi-tab docs). Use semantic shapes: `.cylinder` for data stores, `.hexagon` for agents, `.pill` for brokers, `.folded` for files, `.diamond` for decisions, `.circle` for events. |
| HTML table | `.table-wrap > table` with `<thead>` (enables sticky header + horizontal scroll) |
| CSS Grid cards | `.cards` container + `.card`/`.card.accent` per row |
| TOC sidebar | `.wrap--toc > .toc + .main--toc` layout (see Phase 3 TOC Sidebar section) |
| Progressive disclosure | `details.disclosure` for secondary info, `.has-tip` for term definitions |
| Metadata strip | `.kv-strip` for inline key-value pairs |
| Section anchor | `.summary-card` at start of each tab/section |

Cross-doc: use `.card.info` / `.card.warning` / `.card.critical` for inline tonal callouts.

### Battle-tested CSS defaults

These values are validated on real deployments. Override only with explicit reason.

| Selector | Property | Value | Why |
|---|---|---|---|
| `.panel` | `max-width` | `1280px` | 960px too narrow on modern viewports |
| `.topnav` | `min-height` | `3rem` | Use `min-height`, NOT `height`, to allow flex-wrap |
| `.topnav` | `flex-wrap` | `wrap` | Required when tab count × label length exceeds viewport |
| `.tabs` | `flex-wrap` | `wrap` | NOT `overflow-x: auto` (cuts off tabs invisibly to user) |
| `figure.card` | `padding` | `1rem` | 1.5rem leaves too little width for the diagram |
| `figure.card img` | `width` | `100%` | Required to scale UP narrow SVGs (`max-width: 100%` alone only scales DOWN) |
| `figure.card img` | `max-width` | `920px` | Cap at ergonomic reading width |
| `figure.card img` | `display, margin` | `block; 0 auto` | Center horizontally |
| `figcaption.card-label` | `font-size` | `0.8125rem` | 0.6875rem too small for diagram captions |
| `figcaption.card-label` | `text-align` | `center` | Caption sits under centered image |

**Check:** What visual hierarchy does this need? Quick scan → `.stat-grid`. Deep dive → `.finding` cards by severity. Ordered walk → `.phases`. Data compare → `.table-wrap > table`. Pick one — if two apply equally, the Frame Signal 2 takeaway is underspecified.

### Deliver — Generate + verify

**Always** (both tracks):
- Walk `references/anti-patterns.md` before emitting HTML — confirm no rule is violated, or invoke a named exception.
- Hero section present with eyebrow + title accent + subtitle.
- Section titles use `.section-title` or `.section-label` (never plain `<h2>`).
- fgraph templates: link `fgraph-base.css` from the shell `<head>` (Mode B — multi-tab docs) — do not inline per-tab.
- **Body copy uses `var(--text)` for maximum readability on dark backgrounds.** `var(--text-muted)` is for intermediate emphasis only (subtitles, label rows); `var(--text-dim)` is for metadata only.
- No ASCII art, no emoji in headers.
- Tab buttons have `role="tab"` + `aria-selected` semantics.
- Interactive controls (theme toggle, tab buttons) have visible `:focus-visible` styling.
- Color pairs used for body copy meet 4.5:1 contrast (AAA when possible).
- fgraph diagrams are responsive — `aspect-ratio` + `--x/--y` custom props keep layout intact below 375 px viewport.
- Verify Frame Q2 takeaway is visually emphasized in the Overview tab — the reader should spot it within 10 seconds of landing.

**Track A additionally:**
- Run every `brand.deliver_must_match` rule against the generated tab fragments and shell. Report pass/fail per rule with the tab/line location. Do not write any file until all rules pass or the user explicitly overrides a failing rule.
- If `brand.examples` list is non-empty, offer to visually diff the generated output against one canonical example tab before writing.

- Every tab/section starts with a `.summary-card` or `.stat-grid` (glance layer present).
- No visible text block exceeds 4 sentences without a break or disclosure wrapper.
- Metadata uses `.kv-strip` or structured table, not inline prose.

**If the doc has a TOC sidebar (audit / long-form):**
- TOC scroll observer wired (see Phase 3).
- Sections have stable `id` anchors matching TOC links.

---

## Output UX — Schema Over Prose

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/output-ux.md` — three-layer information architecture, 10 mandatory rules, anti-patterns.

**For forge-guide specifically:** multi-tab docs need a `.summary-card` at the start of every tab (Rule 9). The Overview tab IS the Glance layer — it must contain the Signal 2 takeaway, stat-grid, and key-value context. Deep content (edge cases, implementation details) lives in `details.disclosure` within later tabs.

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

## Context Isolation — Sub-Agent Generation

Heavy HTML/CSS/JS generation runs in a **sub-agent** to keep the main conversation context clean. The main skill thread handles decisions (Phase 1–2); the sub-agent handles file generation (Phase 3).

### When to delegate

| Condition | Action |
|---|---|
| Single-file chart, ≤ 200 lines output | Generate inline (no sub-agent) |
| Multi-tab guide (shell + CSS + JS + tabs) | **Always delegate Phase 3 to sub-agent** |
| Any output > ~300 lines total | **Delegate to sub-agent** |

Multi-tab guides produce 5–15 files. Always delegate Phase 3.

### How to delegate

1. Complete Phase 1 (context) and Phase 2 (tab plan + diagram inventory) in the main thread
2. Spawn a sub-agent with a self-contained prompt that includes:
   - The resolved decisions: aesthetic, tab plan, diagram inventory, output paths, slug
   - The content to render (extracted from user's request + any read context)
   - All file paths for base CSS, aesthetic CSS, shell template, JS files
   - The exact placeholder values for shell substitution
3. The sub-agent generates all files and returns the file paths
4. Main thread runs Phase 4 (report) with the returned paths

### Cluster specialization (for guides with ≥15 diagrams)

For large diagram sets, split Phase 3 SVG generation into N parallel sub-agents — one per visual cluster, NOT one per diagram. Each agent generates the same visual idiom repeatedly, which produces stylistic consistency.

Typical 5-agent split for a 20-30 diagram guide:

| Sub-agent | fgraph cluster | Layout idiom |
|---|---|---|
| FLOW | flow / pipeline / sequence (multi-actor, lifecycle) | swimlanes + lifelines + arrows (`lane-swim`) |
| LAYER | layered / linear flows | linear pipeline with arrows (`layered` / `linear-flow`) |
| DEP | dep-graphs | data-driven dependency columns (`dep-graph`) |
| HUB | hub-spoke + radial | radial / branching (fd-engine `hub-spoke`, `radial-hub` / `radial-ring`) |
| ARCH-VIS | architecture + data-charts (bubble / radar / scatter) | premium fd-engine + chart idioms |

Each cluster sub-agent receives:
- Its diagram list (path + source MD section + content brief per file)
- Shared style guide (anti-patterns + semantic colors)
- The benchmark SVG path as quality reference

Each writes self-contained SVG files to `{ROOT}/tabs/{SLUG}/diagrams/`. No path conflicts (distinct filenames per agent).

**HTML fragments parallelization** (similar pattern): for ≥10 tabs, split tab fragment filling into 4 parallel agents grouped by content density (light / medium / dense / special-format).

<!-- DUPE: same block lives in references/phase-3-generate.md — keep in sync if edited -->

### ⚠ CRITICAL — SVG path resolution in tab fragments

Tab fragments are loaded into the shell HTML via JS `fetch()`. Relative paths in `<img src="...">` resolve against the **document URL (the shell HTML)**, NOT the fragment URL.

| Path in fragment | Resolves to | OK? |
|---|---|---|
| `src="diagrams/X.svg"` | `{ROOT}/diagrams/X.svg` | ❌ 404 |
| `src="tabs/{SLUG}/diagrams/X.svg"` | `{ROOT}/tabs/{SLUG}/diagrams/X.svg` | ✓ |

**Always use the full path from shell root** in tab fragments. This is non-obvious because fragments live deeper in the tree.

### Sub-agent prompt template

```
Generate forge-guide output files.

Decisions (from Phase 1-2):
- Track: {A|B}
- Aesthetic: {file}
- Tab plan: {tab IDs and labels}
- Diagrams: {inventory from Phase 2}
- Output root: {path}
- Slug: {slug}

Read these reference files:
- {list of base CSS, aesthetic CSS, shell template, JS files}

Then generate:
- {ROOT}/{SLUG}.html
- {ROOT}/css/{SLUG}.css
- {ROOT}/js/{SLUG}.js
- {ROOT}/tabs/{SLUG}/tab-{ID}.html (one per tab)

Content to render:
{extracted content/topic}

Rules:
- Inline all CSS (base + aesthetic) into {ROOT}/css/{SLUG}.css
- Follow shell-processing.md substitution pipeline
- Use semantic tokens from components.css
- fgraph templates: link fgraph-base.css from the shell <head> (Mode B) — do not inline per-tab
```

The sub-agent has access to Read, Write, Edit, Bash, Glob, Grep tools — it can read all reference files and write all output files independently.

---

## Phase 1 — Context Discovery

1. **Detect project** from ARGS or cwd. Unknown → ask user. (See `forge-ops.md` for detection signals.)

2. **Run the brand book loader** (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`): Discovery → Parse → Apply. Determine Track A or Track B. Report the result before continuing.

3. **Output root** — follow `forge-ops.md` output paths.

4. **Slug** (kebab-case ≤30 chars). Check existing versions:
   ```bash
   ls {ROOT}/{SLUG}*.html 2>/dev/null
   ```
   ∃ v<N> → propose vN+1 and offer to mark old version `archived` in its meta.

5. **Apply the Aesthetic Detection precedence algorithm** (see `${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md` § Aesthetic Detection) to select the correct aesthetic file.

---

### Frame Trace

After inferring all signals, emit a one-line summary before proceeding to Phase 2. This is not a question — it is a statement the user can interrupt if the inference is wrong:

```
Frame: reader={signal1_reader}, action={signal1_action}, takeaway={signal2}, tone={signal3_summary}. Generating...
```

Example: `Frame: reader=new contributor, action=onboarding, takeaway=three-process NATS topology, tone=warm+technical. Generating...`

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
   - Count nodes and classify topology (architecture / hub-spoke / layered / linear / radial / flow / pipeline / dep-graph)
   - **≥ 7 nodes OR use-cases OR zones OR spotlight** → fd-engine descriptor + `gen-fd.py` + `validate-fd.py` (see `forge-chart/SKILL.md`)
   - **≤ 6 nodes, static, print-safe** → fgraph template from `graph-templates/` (or CSS Grid / table if not a graph)
   - Note shapes per node via `${CLAUDE_PLUGIN_ROOT}/references/shape-vocabulary.md`
   - If one tab cannot hold the topology: split across fragments (each fragment gets its own descriptor or fgraph template)
   Report the diagram inventory before Phase 3. Do not hand-assemble fd-engine HTML or copy `examples/fd-*.html` wholesale.

4. **Audit type ↔ content semantic match.** Misuse of a multi-actor swimlane (`lane-swim`) for a 1-actor pipeline is the #1 cause of "catastrophic" first-render. Verify each diagram's selected type:

   | diagram type | Use ONLY when | Common misuse |
   |---|---|---|
   | `architecture` / `hub-spoke` (fd-engine) | node-edge system; orchestrator + peers; any scale | ❌ pure linear pipeline (use `dep-graph` / `layered`) |
   | `lane-swim` (swimlane) | ≥2 actors exchange messages over time / multi-lane process / lifecycle | ❌ 1-actor pipeline (use `dep-graph` / `linear-flow`) |
   | `dep-graph` | Linear pipeline with dependencies, 1 actor | ❌ branching trees (use `hub-spoke`) |
   | `layered` / `linear-flow` | Source → middle → sink layered flow | ❌ multi-actor exchange (use `lane-swim`) |
   | `radial-hub` / `radial-ring` | Orchestrator + radial peers, no peer ordering | ❌ ordered steps (use `dep-graph`) |

   **Rule:** if `lane-swim` selected but only ONE entity acts → re-classify to `dep-graph` / `linear-flow` before Phase 3. Adding fake actors to fit the format produces unreadable diagrams.

5. **Determine layout mode:**
   - **Standard multi-tab** — nav with tabs, panels switch on click
   - **Mono-page with TOC sidebar** — single panel with sticky TOC navigation (for audits, long-form docs)

---

## Phase 2.5 — Benchmark Validation (mandatory for ≥5 diagrams)

Before mass-producing diagrams, produce ONE reference and validate visually.

**Why:** Downstream parallel agents imitate the reference SVG. Any anti-pattern in the benchmark (palette legend, fake actors, decorative sub-headers) propagates to all children.

**Procedure:**

1. Pick the most representative diagram (typically the core architecture or hub-spoke).
2. Generate as self-contained SVG via fgraph template.
3. Convert to PNG for visual inspection:

   | Platform | Install + invoke |
   |---|---|
   | Linux (Flatpak) | `flatpak --user run --branch=49 --filesystem="$PWD" --command=rsvg-convert org.gnome.Platform -z 2 -f png -o out.png in.svg` |
   | Linux (apt) | `sudo apt install librsvg2-bin` → `rsvg-convert -z 2 -f png -o out.png in.svg` |
   | macOS | `brew install librsvg` → `rsvg-convert -z 2 -f png -o out.png in.svg` |
   | Windows | WSL2 + Linux path above, OR skip PNG QA and rely on Phase 4 browser QA |
4. Validate against Anti-Patterns table (read first). Must pass:
   - No decorative all-caps sub-headers
   - No palette legend with dots
   - No fake actor swimlanes for 1-actor flows
   - Single optional marker (color OR dashed border, not both + text)
   - Semantic colors respected
5. Iterate until 🟢. Only then proceed to Phase 3.

**Skip condition:** guides with <5 diagrams may skip and inline-fix during Phase 3.

---

## Phase 3 — Generate

Read `${CLAUDE_PLUGIN_ROOT}/skills/forge-guide/references/phase-3-generate.md` before building the output.

---

## Phase 3.5 — SVG QA Loop (mandatory for ≥5 diagrams)

After Phase 3 generates all SVGs, run a visual QA pass.

**Step 1:** Convert all SVG → PNG into `{ROOT}/tabs/{SLUG}/diagrams/_previews/`. Requires `rsvg-convert` — see Phase 2.5 Step 3 for install commands per platform.

**Step 2:** Spawn up to 4 parallel QA agents (`Agent` tool, `subagent_type: general-purpose`), one per non-empty visual cluster (skip agents whose cluster has no diagrams):

| Agent | Cluster |
|---|---|
| A | flow / pipeline / sequence (lane-swim) |
| B | layered + linear flows + dep-graphs |
| C | hub-spoke + radial |
| D | architecture + data-charts (bubble / radar / scatter) + benchmark |

Each agent reads PNGs + benchmark + Anti-Patterns table. Reports verdict 🟢/🟡/🔴 per file + top systemic issues.

**Step 3:** Aggregate findings. Present DP:
- A · Fix 🔴 only (minimal viable)
- B · Fix 🔴 + systemic 🟡 (recommended)
- C · Sweep complete (all 🟡)

**Step 4:** Spawn 1 fix agent per cluster in parallel. Each agent receives its cluster's QA findings + targeted fix instructions. No worktree isolation needed (each SVG is a distinct file — no edit conflicts).

**Step 5:** Re-convert + re-QA to verify before Phase 4.

⚠ **PNG QA false-positive trap:** green/amber colors blur together in dark-mode PNG renders. For semantic color disputes, **trust SVG source inspection** (Read the file + verify color attribute) over PNG visual inspection. Track "claimed fixed" vs "actually applied" — fix agents sometimes report inline without effect.

⚠ **Agent-count note:** Phase 3.5's 4-agent QA split is independent from the cluster specialization generation split (5 agents, defined earlier in "Context Isolation → Cluster specialization"). QA covers the whole diagram set regardless of how many generation agents produced it.

---

## Phase 4 — Browser QA (mandatory for multi-tab guides)

Static analysis misses tab overflow, broken paths, and layout bugs. Real-browser test catches them.

**Prerequisite:** Playwright (`uv run --with playwright python3 ...`); `playwright install chromium` one-time.

**Step 1:** Start local server in `{ROOT}`:

```bash
cd {ROOT} && python3 -m http.server "${PORT:-8090}" &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT
```

**Step 2:** Capture all tabs via Playwright (1440×900 viewport, full-page screenshots):

```python
from playwright.sync_api import sync_playwright

tabs = [...]  # all tab IDs from Phase 2 tab plan; e.g. ['overview', 'setup', 'usage']
out = '{ROOT}/_qa-screenshots'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    page.goto('http://localhost:8090/{SLUG}.html')
    page.wait_for_selector('.tab-btn[data-tab="' + tabs[0] + '"]', state='visible')
    page.screenshot(path=f'{out}/00-initial.png', full_page=False)
    for i, t in enumerate(tabs, start=1):
        page.click(f'.tab-btn[data-tab="{t}"]')
        page.wait_for_selector(f'.panel[data-panel="{t}"].active', state='visible')
        page.wait_for_timeout(800)
        page.screenshot(path=f'{out}/{i:02d}-{t}.png', full_page=True)
        broken = page.evaluate(
            "Array.from(document.querySelectorAll('img'))"
            ".filter(img => !img.complete || img.naturalWidth === 0)"
            ".map(img => img.src)"
        )
        if broken: print(f'BROKEN in {t}:', broken)
    browser.close()
```

**Step 3:** Spawn 4 parallel QA agents (multimodal), each on 4 tabs. Check:
- Layout overflow / awkward whitespace
- Tab visibility (CRITICAL — all tabs visible, no `overflow-x: auto` cutoff)
- SVG sizing / centering / caption legibility
- Contrast on dark bg
- Marker badges visibility

**Step 4:** Apply targeted CSS/HTML fixes. Re-screenshot key tabs to verify.

**Common UX-killers caught here:**

| Symptom | Fix |
|---|---|
| Tabs 13-16 hidden (only first N visible) | `.tabs { flex-wrap: wrap }` instead of `overflow-x: auto` · `.topnav { min-height: 3rem }` |
| SVG renders small with whitespace around | `<img>` inline `style="width:100%"` (not just `max-width:100%`) + CSS `figure.card img { max-width: 920px }` |
| `<img>` 404 in tab fragments | Path must be from SHELL root: `src="tabs/{SLUG}/diagrams/X.svg"`, NOT `src="diagrams/X.svg"` |

---

## Phase 5 — Report

```
Created:
  {ROOT}/{SLUG}.html
  {ROOT}/css/{SLUG}.css
  {ROOT}/js/{SLUG}.js
  {ROOT}/tabs/{SLUG}/tab-{ID}.html  (×N)

View:    make forge → http://localhost:8090/{PROJ}/visuals/{SLUG}.html
         (or: cd ~/.roxabi/forge && python3 -m http.server "${PORT:-8090}")
Deploy:  make forge deploy
```

---

## Anti-Patterns (FORBIDDEN)

### Wireframe-level

| Anti-Pattern | Fix |
|---|---|
| `lane-swim` (swimlane) for 1-actor pipelines | Use `dep-graph` or `linear-flow` (linear pipeline) |
| Inventing fake actors to fill a `lane-swim` swimlane | If only one entity acts, re-classify the diagram type |
| Reference SVG that violates its own anti-patterns | Validate benchmark in Phase 2.5 BEFORE downstream agents imitate |

### Diagram-level (SVG content)

| Anti-Pattern | Fix |
|---|---|
| Custom CSS for diagrams with fgraph equivalents | Use fgraph templates + `shape-vocabulary.md` |
| Inline `style="color:#..."` on fgraph nodes/edges | Use `fgraph-base.css` tone classes |
| Hard-coded px coords on `.fgraph-node` | Use `--x`/`--y` custom props in 0..100 space |
| Decorative all-caps sub-headers ("ZERO TO FIRST COMMAND", "ÉTAPE 1") | Remove — purely chrome, no info value |
| Palette legend with colored dots/squares at bottom | Remove — color is self-explanatory |
| Triple-redundant optional markers (dashed + amber + text "(opt)") | Pick ONE signal |
| Cyclic loop on a single state when not semantically a cycle | Remove the loop |
| `.gris` (muted) applied to active steps | Reserve the `.gris` class for passive infra only |
| ASCII art in `<pre class="arch">` | Convert to the matching fgraph template |

### HTML/CSS-level

| Anti-Pattern | Fix |
|---|---|
| `.tabs { overflow-x: auto }` for nav | Use `.tabs { flex-wrap: wrap }` (overflow-x hides tabs without affordance) |
| `<img>` inline `style="max-width:100%"` only | Use `style="width:100%"` + CSS `max-width: NNN px` (so diagrams scale UP) |
| `<img src="diagrams/X.svg">` in tab fragments | Use full path from shell root: `src="tabs/{SLUG}/diagrams/X.svg"` |
| `.panel { max-width: 960px }` | Use `1280px` (modern viewport ergonomics) |
| Hex color in `<meta name="diagram:color">` | Use named color from `VALID_COLORS = {amber, blue, green, purple, orange, cyan, red, gold}` |
| Emoji in headers | Remove — text only |
| Plain `<h2>` for section titles | Use `.section-title` or `.section-label` |
| No header on multi-tab | Add styled header with eyebrow + badges |

$ARGUMENTS
