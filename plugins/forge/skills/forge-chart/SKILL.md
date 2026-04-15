---
name: forge-chart
description: >-
  Create a quick self-contained single-file HTML visual — native fgraph
  diagram (hub-and-spoke, gantt, pie, ER, sequence, state, dep-graph),
  architecture layout, or CSS Grid explainer. No server needed, works
  with file://. Triggers: "draw" | "diagram" | "visualize" | "sketch" | "map"
  | "show the flow" | "quick visual".
summary: 'single-file native fgraph / CSS visual'
version: 0.3.0
allowed-tools: Read, Write, Bash, Glob, Grep, ToolSearch, Agent
---

# Chart — Single-File Quick Visual

Create a self-contained HTML file. All CSS/JS inline — no fetch, no external files, works with `file://`.
Use for: native fgraph topologies (hub-and-spoke, linear pipeline, layered), gantt timelines, pie proportions, ER schemas, sequence diagrams, state machines, issue-dependency graphs, or simple CSS explainer layouts.

Output: `~/.roxabi/forge/<project>/visuals/{slug}.html` or `~/.roxabi/forge/_shared/diagrams/{slug}.html`.

**Read before generating:**

```
${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md              — brand detection, output paths, deploy commands
${CLAUDE_PLUGIN_ROOT}/references/base/reset.css            — concatenate first
${CLAUDE_PLUGIN_ROOT}/references/base/layout.css           — concatenate second
${CLAUDE_PLUGIN_ROOT}/references/base/typography.css       — concatenate third
${CLAUDE_PLUGIN_ROOT}/references/base/components.css       — concatenate fourth
${CLAUDE_PLUGIN_ROOT}/references/base/explainer-base.css   — concatenate fifth (visual explainer components)
${CLAUDE_PLUGIN_ROOT}/references/aesthetics/               — select one based on detection logic
${CLAUDE_PLUGIN_ROOT}/references/shells/single.html        — HTML template with placeholders
${CLAUDE_PLUGIN_ROOT}/references/base/theme-toggle.js      — substitute {NAME}, then inline via {THEME_TOGGLE_JS}
${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md           — meta tag format + categories
${CLAUDE_PLUGIN_ROOT}/references/graph-templates/README.md — graph/topology templates (read when visual type = architecture / topology / timeline / proportion / schema / sequence / state / dep-graph)
${CLAUDE_PLUGIN_ROOT}/skills/forge-chart/fixtures/README.md — fixture format + regression inputs (no runner yet; hashes populate in future)
```

**Directive: inline, never link** — `base/` and `aesthetics/` files are generation source, not runtime dependencies. Read → inline into output `<style>` block.

**Exception — graph-templates/fgraph-base.css has two distribution modes:**
- **Mode A (default — single-file HTML):** inline into output `<style>` block, same as `base/`. Required for anything that must work with `file://`.
- **Mode B (multi-tab docs):** copy to `~/.roxabi/forge/_shared/fgraph-base.css` once, then reference via `<link rel="stylesheet" href="../../_shared/fgraph-base.css">` in the shell `<head>`. Use when ≥ 2 tabs in the same doc use fgraph classes. Matches the `gallery-base.{css,js}` precedent.
- Decision rule: `forge-chart` single-file output → Mode A. Multi-tab roadmap / spec shell → Mode B. See `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/README.md` "Inlined vs shared" for the full rulebook.

---

## Design Phase — Frame → Structure → Style → Deliver

Decisions made across Phases 1–4 follow this lens. It is an overlay on the procedural phases, not a separate pre-phase: Frame runs in Phase 1 (context + aesthetic detection), Structure in Phase 2 (visual type), Style in Phase 3 (generate), Deliver in Phase 4 (report + verify).

### Track selection (Phase 1 start)

Run the brand book loader (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`) before any other decision:

- **Track A (branded)** — `forge.yml` found in project `brand/` → aesthetic/palette/typography locked; components pre-filled; `deliver_must_match` rules enforced at Deliver.
- **Track B (exploration)** — no brand book → full Frame judgment; Frame output drives aesthetic fallback via `forge-ops.md § Aesthetic Detection` priority 5.

Full track-by-track behavior: `${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md`.

Report the loaded brand book (or its absence) before starting Frame. Track is fixed at Phase 1 and does not change.

### Frame — What's this visual for?

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md` — three Frame signals, reader-action matrix, tone dimensions, example trace.

**For forge-chart specifically, Signal 4 (sentence verb) is the most useful internal check.** A chart is usually a single visual with one dominant reader action — *see*, *debug*, *decide*, *learn*, *trust*. Infer the verb from the prompt before picking topology: a *see* verb tolerates spacious fgraph; a *debug* verb demands dense stat-grid + high contrast.

- **Track A:** infer Signal 1 (reader-action) and Signal 2 (takeaway) from the prompt. Tone is pre-constrained by brand voice rules in `deliver_must_match` — no tone inference needed.
- **Track B:** infer Signal 1, Signal 2, and full Signal 3 (all four tone axes) from the prompt and content. Frame output produces a content-type signal for Aesthetic Detection priority 5.

Aesthetic is never chosen by Frame — it's mechanical (see `forge-ops.md § Aesthetic Detection`). Frame produces purpose, not CSS.

### Structure — Which visual type?

Content-driven in both tracks. Brand `structure_defaults` (if present) act as **tiebreakers only** when content topology is genuinely ambiguous.

| Content | Approach | Why |
|---|---|---|
| Issue / dependency graph | `graph-templates/dep-graph.html` (fed by `scripts/gen-deps.py`) | Python-side topological layer assignment + elbow routing; declarative |
| Data flow (linear, 2–3 stages) | `graph-templates/linear-flow.html` | Unidirectional arrows, labels above |
| API sequence | `graph-templates/sequence.html` | Participant lifelines + horizontal message arrows; cap 15 messages |
| State machine | `graph-templates/state.html` | `.fgraph-node.circle/.diamond` + semantic edge classes for start/end |
| Timeline / schedule | `graph-templates/gantt.html` | Date axis (`.fg-axis-date`) + horizontal bars; CSS-only, offline-safe |
| Proportion / share | `graph-templates/pie.html` | Pre-computed SVG arc paths + legend; no runtime |
| Entity-relationship schema | `graph-templates/er.html` | Entity boxes + crow's-foot markers (`.fg-er-*`) |
| **Hub-and-spoke, ≤ 6 peers, rich cards** | **`graph-templates/radial-hub.html`** | Pills, warn lines, multi-line |
| 7 radial nodes | `radial-ring.html` (no center) or split into sub-diagrams | fgraph caps at ~6 before labels collide |
| Layered architecture (3–4 tiers) | `graph-templates/layered.html` or `deployment-tiers.html` | Dashed frames per layer, vertical fan-out |
| Multi-host deployment | `graph-templates/machine-clusters.html` | Cross-machine edge routing, wide aspect |
| Architecture layers (node topology, arrows needed, ≤8 nodes) | foreignObject+CSS Flexbox SVG | No pixel math; LLM only computes arrow coords; inline SVG, no JS |
| Architecture layers (text-heavy, stacked, no arrows) | CSS Grid cards | Fallback when no node-to-node connections needed |
| **Comparison / matrix (≥4 rows or ≥3 cols)** | **HTML `<table>`** | Tabular data is not a graph |
| Simple timeline | `.steps` timeline component | Shared CSS, no auto-layout needed |

**Decision rule:** pick the fgraph template whose shape matches (hub-and-spoke / linear / layered / multi-host / ring / gantt / pie / er / sequence / state / dep-graph). If > 8 nodes or complex flow that no template covers → **split the diagram** or use `layered.html` with hand-assigned `--x/--y`. Tabular → HTML table. Architecture with node topology + arrows, ≤ 8 nodes → foreignObject+CSS Flexbox SVG. Stacked text-heavy, no arrows → CSS Grid cards.

**foreignObject rules (MANDATORY when using this type):**
- Every `<foreignObject>` root element MUST have `xmlns="http://www.w3.org/1999/xhtml"` — omitting it causes silent render failure in Chrome/Edge
- Node labels: max 24 chars — foreignObject clips overflow silently
- Draw order: SVG `<line>`/`<path>` edges BEFORE `<g>` node groups — nodes paint over edges via DOM order (no masking rect needed)
- Use `--diag-*` semantic color tokens (see `references/tokens.md`) for node type styling
- Not suitable for print/PDF export — Chromium drops foreignObject content in print pipeline

**Node shapes (fgraph):** When using fgraph, pick the right shape modifier for each node. Read [`${CLAUDE_PLUGIN_ROOT}/references/shape-vocabulary.md`](${CLAUDE_PLUGIN_ROOT}/references/shape-vocabulary.md) for the full semantic mapping. Quick reference: `.cylinder` = database, `.hexagon` = agent/worker, `.diamond` = decision/gate, `.circle` = event/trigger, `.folded` = file/config, `.pill` = bus/broker, default rect = service/process.

**Arrow modifiers (fgraph):** `.dashed` = optional/async, `.thick` = critical path, `.animated` = live stream. Compose with tones: `<path class="fg-edge amber thick">`.

**Shared primitives reference:** reach for these instead of re-inventing —

- **Info-card summary row** (`.info-card-grid` → `.info-card` → `.info-card__dot` / `__title` / `__list`): 3-col landing row for "Frontend / Backend / Database" or "What / Why / How" overviews. Defined in `base/components.css`, example in `shells/single.html`.
- **Architecture tier palette** (`--arch-frontend`, `--arch-backend`, `--arch-database`, `--arch-cloud`, `--arch-security`, `--arch-external`): semantic color tokens for tier-oriented diagrams. Defined in `references/tokens.md`. Complementary to `--diag-*` (flow-oriented).
- **Boundary / cluster groups** (`.fgraph-group.{region,cluster,security-group}` + `.fgraph-group__label`): dashed frames that wrap 2+ related fgraph nodes as a VPC / bounded context / security zone. Defined in `graph-templates/fgraph-base.css`.
- **Pixel-exact layout constants** (`--layer-h`, `--layer-h-simple`, `--layer-gap` sourced from `references/shape-vocabulary.md` § Pixel-exact layout): `LAYER_H_BADGE=116px`, `LAYER_H_SIMPLE=101px`, `LAYER_GAP=50px`. Use when the diagram stacks ≥3 layer rows.

**Check:** How many nodes? Any cycles? If the content sketches twice — once radial, once linear — which reads faster on a 1200px screen? Content that takes two sketches to understand is a signal to split the diagram, not to cram both into one.

### Style — Which components?

All classes below exist in `base/components.css` + `base/explainer-base.css`.

- **Track A:** component slots (hero, section-label, card, timeline, badges) are **pre-filled** from `brand.components.*`. Override a slot only when the content's Structure output has no valid rendering using the brand default (see `design-phase-two-track.md § Style` partial override rule). Stylistic preference is not a valid reason.
- **Track B:** pick the row that matches your Structure output. Frame tone drives variant selection when multiple rows could apply.

| Visual type | Hero | Sections | Extra |
|---|---|---|---|
| Dep-graph (`dep-graph.html`) | `.hero.left-border` | `.section-label.dot` | `.card.accent` legend for phase/status colors |
| Linear flow (`linear-flow.html`) | `.hero.left-border` | `.section-label.dot` | `.phases` + `.phase-card` |
| Sequence (`sequence.html`) | `.hero.left-border` | `.section-label.dot` | `.phases` (time-grouped arcs) + `.card.accent` legend |
| State machine (`state.html`) | `.hero.left-border` | `.section-label.dot` | `.card.accent` legend for state meanings |
| Radial hub (`radial-hub.html`, ≤ 6 peers) | `.hero.left-border` | `.section-label.dot` | `.card.accent` legend for edge types (pills/warn/ok) |
| Gantt (`gantt.html`) | `.hero.top-border` | `.section-label.triangle` | `.stat-grid` for milestones (optional) |
| Pie (`pie.html`) | `.hero.left-border` | `.section-label.dot` | `.card.accent` legend if > 5 slices |
| ER schema (`er.html`) | `.hero.left-border` | `.section-label.square` | `.card.accent` legend for relationship types |
| Architecture layers (`layered.html` / `deployment-tiers.html`) | `.hero.elevated` | `.section-label.square` | `.stat-grid` + `.stat` |
| Timeline (steps) | `.hero.top-border` | `.section-label.triangle` | `.steps` + `.step` + `.step-num` |
| Explainer | `.hero.left-border` | `.section-label.dot` | `.io-strip` + `.io-box` + `.io-arrow` |
| Comparison | `.hero.left-border` | `.section-label.dot` | `.table-wrap > table` |

**Rendering wrappers** — orthogonal to visual type. Apply these to whatever rendering the Structure phase chose:

| Rendering | Wrapper / component |
|---|---|
| fgraph (all templates) | `.fgraph-wrap` + `.fgraph-frame` + `.fgraph-edges` + `.fgraph-node.{shape}.{tone}` (shapes: `.cylinder`/`.hexagon`/`.diamond`/`.circle`/`.folded`/`.pill` — see `shape-vocabulary.md`) |
| HTML table | `.table-wrap > table` with `<thead>` (enables sticky header + horizontal scroll) |
| CSS Grid cards | `.cards` container + `.card`/`.card.accent` per row |
| Timeline | `.steps` container + `.step > .step-num` per entry |
| Explainer I/O flow | `.io-strip` + `.io-box` + `.io-arrow` |
| Progressive disclosure | `details.disclosure` for secondary info, `.has-tip` for term definitions |
| Metadata strip | `.kv-strip` for inline key-value pairs |
| Section anchor | `.summary-card` at start of each tab/section |

Cross-type: use `.card.info` / `.card.warning` / `.card.critical` for inline tonal callouts.

**Signal:** What's the ONE thing the reader should walk away remembering (Frame Signal 2)? A number → `.stat-grid`. A path through steps → `.steps` timeline. A comparison → `.table-wrap > table`. A decision with trade-offs → `.io-strip`. If more than one answer fits, the diagram is doing too much — Frame Signal 2 is underspecified.

### Deliver — Generate + verify

**Always** (both tracks):
- Walk `references/anti-patterns.md` before emitting HTML — confirm no rule is violated, or invoke a named exception.
- fgraph templates: inline `fgraph-base.css` into the output `<style>` block per the Mode A distribution rule (`graph-templates/README.md § Distribution rule`).
- SVG sizing: `.fgraph-edges` gets `viewBox="0 0 100 100" preserveAspectRatio="none"` + `vector-effect: non-scaling-stroke` on path children.
- No ASCII art, no emoji in section headers.
- Interactive controls (zoom, theme) are `<button>` with visible `:focus-visible` styling.
- **Body copy uses `var(--text)` for maximum readability on dark backgrounds.** `var(--text-muted)` is for intermediate emphasis only (subtitles, label rows); `var(--text-dim)` is for metadata only. Never `var(--text-dim)` on `var(--surface)` for any body copy.
- Color pairs meet 4.5:1 contrast minimum (body text AAA when possible).
- Verify Frame Q2 takeaway is visually emphasized — the reader should spot it without reading the whole diagram.

**Track A additionally:**
- Run every `brand.deliver_must_match` rule against the generated output. Report pass/fail per rule with location. Do not write the file until all rules pass or the user explicitly overrides a failing rule.
- If `brand.examples` list is non-empty, offer to visually diff the generated output against one example before writing.

- Every tab/section starts with a `.summary-card` or `.stat-grid` (glance layer present).
- No visible text block exceeds 4 sentences without a break or disclosure wrapper.
- Metadata uses `.kv-strip` or structured table, not inline prose.

**If the chart is a rich explainer** (multi-section, long-form):
- Hero section present (`.hero.left-border` / `.elevated` / `.top-border`) with eyebrow + title accent.
- Section labels present (`.section-label.dot` / `.triangle` / `.square`).
- Reveal observer wired for `.reveal` elements.

**If the chart is a single quick diagram** (one fgraph block, no narrative):
- Hero and section labels are **optional** — a minimal title + diagram is acceptable.
- Reveal observer is **not needed** (no `.reveal` elements to observe).

---

## Output UX — Schema Over Prose

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/output-ux.md` — three-layer information architecture, 10 mandatory rules, anti-patterns.

**For forge-chart specifically:** the Glance layer (`.hero` + `.stat-grid` or `.summary-card`) is critical — a single chart must communicate its takeaway above the fold. Use progressive disclosure (`details.disclosure`) for explanatory text below the diagram.

---

## Shell Processing

1. Read `shells/single.html` template
2. Concatenate base CSS files in order: `reset → layout → typography → components → explainer-base`
3. Read selected aesthetic CSS
4. Read `base/theme-toggle.js`, substitute `{NAME}` with the diagram slug
5. Substitute placeholders:
   - `{NAME}` → diagram slug (for localStorage key scoping)
   - `{BASE_STYLES}` → concatenated base CSS
   - `{AESTHETIC_STYLES}` → aesthetic CSS (editorial.css if default)
   - `{TITLE}`, `{DATE}`, `{CATEGORY}`, `{CAT_LABEL}`, `{COLOR}`, `{BADGES}` → diagram metadata
   - `{HEAD_EXTRAS}` → (empty by default; add Google Fonts preconnect here if the aesthetic requires it)
   - `{CONTENT}` → diagram body (hero section, `.fgraph-wrap` / template body, cards, etc.)
   - `{EXTRA_STYLES}` → diagram-specific CSS (if any)
   - `{THEME_TOGGLE_JS}` → theme-toggle.js with `{NAME}` substituted (runs before {EXTRA_SCRIPTS})
   - `{EXTRA_SCRIPTS}` → reveal observer (optional; no diagram runtime — all rendering is static CSS/SVG)
6. Output: single self-contained HTML file (file:// safe)

fgraph note: single-file output has **no runtime JS** for diagrams — all layout is declarative CSS with `--x`/`--y` custom props in the 0..100 coordinate space. Pick the template that matches the shape; fill `{{PLACEHOLDERS}}`.

Let:
  ARGS := $ARGUMENTS

---

## Context Isolation — Sub-Agent Generation

Heavy HTML/CSS/JS generation runs in a **sub-agent** to keep the main conversation context clean. The main skill thread handles decisions (Phase 1–2); the sub-agent handles file generation (Phase 3).

### When to delegate

| Condition | Action |
|---|---|
| Single quick diagram (one fgraph block, no narrative) | Generate inline (no sub-agent) |
| Rich explainer (multi-section with hero + phases + diagram) | **Delegate Phase 3 to sub-agent** |
| Any output > ~300 lines total | **Delegate to sub-agent** |

### How to delegate

1. Complete Phase 1 (context) and Phase 2 (visual type selection) in the main thread
2. Spawn a sub-agent with a self-contained prompt that includes:
   - The resolved decisions: aesthetic, visual type, output paths, slug
   - The content to render (extracted from user's request + any read context)
   - All file paths for base CSS, aesthetic CSS, shell template, JS files
   - The exact placeholder values for shell substitution
3. The sub-agent generates all files and returns the file paths
4. Main thread runs Phase 4 (report) with the returned paths

### Sub-agent prompt template

```
Generate forge-chart output file.

Decisions (from Phase 1-2):
- Track: {A|B}
- Aesthetic: {file}
- Visual type: {fgraph template name|CSS Grid|foreignObject+Flexbox SVG|etc.}
- Output path: {path}
- Slug: {slug}

Read these reference files:
- {list of base CSS, aesthetic CSS, shell template, JS files}

Then generate:
- {output file path}

Content to render:
{extracted content/topic}

Rules:
- Inline all CSS (base + aesthetic) into output
- Follow shell-processing.md substitution pipeline
- Use semantic tokens from components.css
- fgraph templates: inline fgraph-base.css into <style> (Mode A) — do not link
- Single-file output must work with file://
```

The sub-agent has access to Read, Write, Bash, Glob, Grep tools — it can read all reference files and write the output file independently.

---

## Phase 1 — Context

1. Detect project from ARGS or cwd.
2. Issue number in ARGS (`#N` or `NNN-`) → filename `{N}-{slug}.html`, set `diagram:issue` meta.
3. Cross-project / no project → `~/.roxabi/forge/_shared/diagrams/`.
4. **Run the brand book loader** (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`): Discovery → Parse → Apply. Determine Track A or Track B. Report the result before continuing.
5. Apply the Aesthetic Detection precedence algorithm (see `${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md` § Aesthetic Detection) to select the correct aesthetic file. If Track A, `forge.yml` already locks it at priority 2.

---

### Frame Trace

After inferring all signals, emit a one-line summary before proceeding to Phase 2. This is not a question — it is a statement the user can interrupt if the inference is wrong:

```
Frame: reader={signal1_reader}, action={signal1_action}, takeaway={signal2}, tone={signal3_summary}. Generating...
```

Example: `Frame: reader=new contributor, action=onboarding, takeaway=three-process NATS topology, tone=warm+technical. Generating...`

---

## Phase 2 — Visual Type

| Content | Approach |
|---------|----------|
| Task / issue dependency graph | `graph-templates/dep-graph.html` (fed by `scripts/gen-deps.py`) |
| Data flow between services (linear) | `graph-templates/linear-flow.html` |
| API / message sequence | `graph-templates/sequence.html` |
| State machine | `graph-templates/state.html` |
| Timeline / schedule / roadmap | `graph-templates/gantt.html` |
| Proportion / share / composition | `graph-templates/pie.html` |
| Entity-relationship schema | `graph-templates/er.html` |
| **Hub-and-spoke / message bus / gateway (≤ 6 peers, rich cards)** | **`graph-templates/radial-hub.html` + `fgraph-base.css`** |
| Architecture layers (stacked, text-heavy) | CSS Grid cards |
| Layered architecture (3–4 tiers) | `graph-templates/layered.html` or `deployment-tiers.html` |
| Multi-host deployment | `graph-templates/machine-clusters.html` |
| Simple timeline | CSS flex with connectors |

**Decision rule for architecture diagrams:**
- Linear pipeline (2–3 stages) → `linear-flow.html`
- Radial / hub-and-spoke with rich cards (pills, warn, multi-line) → `radial-hub.html` / `radial-ring.html`
- Layered architecture (3–4 tiers) → `layered.html` or `deployment-tiers.html`
- Multi-host deployment → `machine-clusters.html`
- Architecture with node topology + arrows, ≤ 8 nodes → foreignObject+CSS Flexbox SVG
- Stacked text-heavy, no arrows → CSS Grid cards (fallback)
- > 8 nodes or a shape no template covers → **split the diagram** into sub-diagrams, or use `layered.html` with hand-assigned `--x/--y`
- See `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/README.md` for the full decision matrix.

fgraph-radial caps at ~6 satellites before labels collide. For dense graphs (> 8 nodes) split into sub-diagrams rather than cramming.

Choose `diagram:category` + `diagram:color` from `${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md`.

---

## Phase 3 — Generate

Read `${CLAUDE_PLUGIN_ROOT}/skills/forge-chart/references/phase-3-generate.md` before building the output.


---

## Domain Patterns

Canonical AI/infra diagram topologies. When a prompt matches one of these, reach for the listed shape + arrow semantics instead of reinventing. Sourced from fireworks-tech-graph.

| Pattern | Core shape | Key nodes | Dominant flow |
|---|---|---|---|
| **RAG (Retrieval-Augmented Generation)** | linear-flow with branch | query → retriever (vector store) → augmented prompt → LLM → answer | control + data reads; vector store is `.cylinder` |
| **Agentic Search** | radial-hub around planner | planner (hex) ↔ {search, scrape, summarize, synthesize} tools | control spokes outward, data returns inward |
| **Mem0 / Memory-tiered** | layered | working memory (hot) → episodic (warm) → semantic (cold) → archive | write-through (down) + recall (up) |
| **Multi-Agent** | dual-cluster or radial-ring | N agents around shared blackboard / message bus (`.pill`) | async pub/sub on bus edges |
| **Tool Call** | linear-flow | LLM → tool router → {tool₁, tool₂, ...} → result → LLM | control down, data back up |
| **5-layer Agent Architecture** | layered (4 layers tall) | perception → memory → planning → action → feedback | feedback arrow closes the loop bottom→top |

### Arrow semantics

Composes with tone classes on `.fg-edge`. Pick the one that names the flow:

| Flow | Class | Visual | When |
|---|---|---|---|
| **Data** | `.fg-edge.data` (purple default) | solid | payloads, query results, tokens |
| **Control** | `.fg-edge.control` (accent default) | solid | "invoke X", "route to Y", dispatch |
| **Memory** | `.fg-edge.write` (green, dashed) | dashed | writes to a store; pair with `.fg-edge.read` for reads |
| **Feedback** | `.fg-edge.feedback` (amber default) | solid | loss signal, reward, RLHF, user correction, eval |
| **Async** | `.fg-edge.async` (muted, dashed) | dashed | pub/sub, queue, event emission |

Use `.thick` to promote the critical path (one per diagram — usually the end-to-end user path).

### Memory tiers (Mem0-style) colorway

When drawing tiered memory, bind tiers to the palette consistently across diagrams in the same doc:

| Tier | Token | Semantic |
|---|---|---|
| Working / hot | `var(--arch-frontend)` (cyan) | in-context, ephemeral |
| Episodic / warm | `var(--arch-backend)` (green) | session-scoped |
| Semantic / cold | `var(--arch-database)` (violet) | long-term, queryable |
| Archive | `var(--arch-external)` (slate) | compacted, rarely read |

---

## Anti-Patterns (FORBIDDEN)

| Anti-Pattern | Fix |
|--------------|-----|
| Linking to a CDN diagram library | Use a native `graph-templates/*.html` — inline `fgraph-base.css` per Mode A |
| ASCII art in `<pre class="arch">` | Convert to the matching fgraph template |
| Emoji in headers | Remove — use text only |
| Inline `style="color:#..."` on fgraph nodes/edges | Use `fgraph-base.css` tone classes (`.amber`, `.cyan`, `.purple`, `.green`, `.red`) |
| Hard-coded px coords on `.fgraph-node` | Use `--x`/`--y` custom props in 0..100 space |
| Plain `<h2>` for section titles | Use `.section-title` class |
| No hero section (multi-section chart) | Add hero with left-border variant |

---

## Phase 4 — Report

```
Created: {path}/{slug}.html

Open:    file://{path}/{slug}.html     (no server needed)

Serve + Deploy: see forge-ops.md
```

### Visual Quality Gates (run before writing file)

14-item pre-flight checklist. Every item is binary — tick it or fix it. Sourced from the gmdiagram QC pattern + architecture-diagram-generator conventions.

- [ ] **Text fit:** no labels overlap, no text overflows its container, no truncation ellipses on node titles
- [ ] **Arrow routing:** SVG paths do not pass through unrelated node boxes; endpoints land on node edges (not centers)
- [ ] **foreignObject xmlns:** every `<foreignObject>` root has `xmlns="http://www.w3.org/1999/xhtml"` — silent failure in Chrome/Edge otherwise
- [ ] **Layer gaps:** vertical spacing between layered rows matches `--layer-gap` (50px default from `shape-vocabulary.md`); no row heights drift from `--layer-h`
- [ ] **CSS class names:** semantic classes only (`.fgraph-node.cylinder`, `.arch-frontend`) — no inline `style="color:#..."` on nodes/edges (tokens only)
- [ ] **ViewBox fit:** content fills 80–95% of declared dimensions — no large empty regions, no clipping
- [ ] **Text escaping:** `&`, `<`, `>`, `"`, `'` escaped in labels/titles rendered inside SVG `<text>` or `<foreignObject>`
- [ ] **Legend accuracy:** legend lists only node types + edge tones actually present in the diagram — no leftover entries
- [ ] **Title accuracy:** `<title>` + `diagram:title` meta + hero `<h1>` all state the Frame Signal 2 takeaway consistently
- [ ] **Marker refs:** every `url(#id)` arrow marker has a matching `<marker id="id">` in `<defs>` (including `fg-arr-*` arrow markers and, for ER diagrams, `fg-er-one`/`fg-er-many`/`fg-er-zero-one`/`fg-er-one-many`/`fg-er-zero-many` crow's-foot markers)
- [ ] **Tag balance:** SVG + HTML parse cleanly (no unclosed tags, no stray `<`/`>` in text nodes)
- [ ] **fgraph inlining:** `fgraph-base.css` is inlined into the output `<style>` (Mode A) — no `<link>` to `_shared/fgraph-base.css`
- [ ] **Color contrast:** body text uses `var(--text)` not `var(--text-dim)` on `var(--surface)`; AA minimum, AAA preferred
- [ ] **SVG validator:** `bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate-svg.sh <output>` exits 0 (checks tag balance, attr quotes, marker refs, path data, rsvg-convert smoke — skips gracefully if tools absent)

$ARGUMENTS
