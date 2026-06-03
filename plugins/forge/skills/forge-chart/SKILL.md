---
name: forge-chart
description: >-
  Create a quick self-contained single-file HTML visual — native fgraph
  diagram (hub-and-spoke, gantt, pie, ER, sequence, state, dep-graph),
  architecture layout, CSS Grid explainer, or inline-SVG data-chart (scatter,
  bubble, radar, funnel). No server needed, works with file://. Triggers:
  "draw" | "diagram" | "visualize" | "sketch" | "map" | "show the flow" |
  "quick visual".
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

---

## fd-engine diagram types

The **fd-engine** (forge-diagram JS engine, S1) is the generation path for architecture diagrams and hub-spoke topologies. It replaces the static fgraph coordinate approach with DOM-measured bezier edges, providing lyra-stack-grade visual quality at any container size.

### Routing rule

When the user requests an **architecture diagram** or **hub-spoke topology** (rich cards, multi-node, edge annotations, zones, use-case walkthroughs):

1. Generate an **fd-engine descriptor JSON** (see schema below)
2. Embed it as `<script type="application/json" id="fd-data">` in the output HTML
3. Inline the **fd-engine bundle** via `buildEngine(fdDir, type)` from `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/fd/bundler.js`
4. Inline `fd-engine.css` from `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/fd-engine.css`
5. Inline `fgraph-base.css` (Mode A — single file)
6. Inline forge base CSS + selected aesthetic CSS

**Supported declarative types (S1):** `architecture`, `hub-spoke`

Auto-layout types (flowchart, state, class, er, sequence) are added in later slices (S2–S4). Do not route those types to fd-engine yet.

### Descriptor JSON schema (normative)

```json
{
  "type": "architecture",
  "title": "Diagram title",
  "theme": "lyra-v2",
  "layout": "declarative",
  "canvas": { "height": 1040 },
  "options": {
    "particles": false,
    "spotlight": true,
    "sidebar": true
  },
  "nodes": [
    {
      "id": "hub",
      "x": 50, "y": 55,
      "kind": "bus",
      "n": "NATS Bus",
      "img": "nats:alpine",
      "d": "JetStream · 4222/4223",
      "plane": "message",
      "h": "M1",
      "cardStyle": "premium"
    }
  ],
  "edges": [
    {
      "f": "telegram", "t": "hub",
      "plane": "message",
      "label": "lyra.inbound.*"
    }
  ],
  "zones": [
    {
      "id": "zoneM2",
      "nodes": ["llmw", "img"],
      "class": "zone-m2",
      "label": "M₂ · GPU on-demand"
    }
  ],
  "useCases": [
    {
      "title": "① text message",
      "desc": "Telegram → hub → clipool → turn-writer",
      "steps": [
        { "nodes": ["telegram"], "edge": ["telegram", "hub"], "label": "1. inbound" }
      ]
    }
  ]
}
```

### Field reference

| Field | Type | Notes |
|---|---|---|
| `type` | string | `"architecture"` or `"hub-spoke"` for S1 declarative path |
| `title` | string | Diagram title (used in `<title>` + hero) |
| `theme` | string | Aesthetic name — matches `references/aesthetics/*.css` filename stem |
| `layout` | string | `"declarative"` — LLM encodes `x`/`y` in 0..100 % space |
| `canvas.height` | number | Canvas height in px (default 800) |
| `options.particles` | bool \| "loop" | `false` (default) — particles OFF; `true` = one-shot on trigger; `"loop"` = continuous |
| `options.spotlight` | bool | Hover isolation + sidebar panel |
| `options.sidebar` | bool | Show sidebar panel |
| **nodes[].id** | string | Unique node ID (used in edges, zones, useCases) |
| **nodes[].x / y** | number | Position in 0..100 % coordinate space (declarative types only) |
| **nodes[].kind** | string | `"default"` \| `"bus"` \| `"store"` \| `"ext"` \| `"hub-int"` |
| **nodes[].n** | string | Display name |
| **nodes[].img** | string | Image/package label (mono subtitle) |
| **nodes[].d** | string | Description / role (short, one line) |
| **nodes[].plane** | string | Semantic plane: `control` \| `write` \| `read` \| `data` \| `async` \| `feedback` \| `message` \| `llm` |
| **nodes[].h** | string | Host badge: `"M1"` \| `"M2"` \| `"EX"` (external, no badge) |
| **nodes[].cardStyle** | string | Optional override: `"premium"` (default for architecture/hub-spoke) \| `"simple"` |
| **edges[].f / t** | string | From / to node IDs |
| **edges[].plane** | string | Semantic plane (determines edge color from aesthetic tokens) |
| **edges[].label** | string | Optional edge label (shown at bezier midpoint on hover) |
| **edges[].srcFace / dstFace** | string | Optional face override: `"top"` \| `"bottom"` \| `"left"` \| `"right"` |
| **zones[].id** | string | Must match the HTML element `id` for the zone div |
| **zones[].nodes** | string[] | Node IDs whose bounding rect defines the zone |
| **zones[].class** | string | CSS class on the zone div |
| **zones[].label** | string | Zone label text |
| **useCases[].title** | string | Use-case button label |
| **useCases[].desc** | string | HTML description (shown in sidebar) |
| **useCases[].steps[].nodes** | string[] | Nodes to highlight in this step |
| **useCases[].steps[].edge** | [f, t] \| null | Edge to activate + animate particle (if particles enabled) |
| **useCases[].steps[].label** | string | Step label in sidebar step list |

### Semantic planes

| Plane | Color token | Semantic |
|---|---|---|
| `control` | `--cyan` | dispatch, invoke, route |
| `write` | `--green` | writes to a store or file |
| `read` | `--purple` | reads from a store |
| `data` | `--plum` | payload, query result, token stream |
| `async` | `--amber` | pub/sub, queue, event, SSE |
| `feedback` | `--accent` | loss signal, correction, eval result |
| `message` | `--cyan` | NATS / message-bus (alias for control in lyra topology) |
| `llm` | `--purple` | LLM inference request/response |

### AC-10 guard (mandatory)

The fd-engine SVG overlay MUST use pixel-space positioning, NOT a viewBox stretch:

```html
<!-- CORRECT (AC-10) -->
<svg class="fd-edges" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible">

<!-- FORBIDDEN — causes giant arrowhead bug (#57 root cause) -->
<svg viewBox="0 0 100 100" preserveAspectRatio="none">
```

### Guard — fd-engine output purity

This section documents fd-engine. The output descriptor JSON uses `type:"architecture"`, `type:"hub-spoke"`. The guard contract (`grep -rn '\bmermaid\b' plugins/forge/` must be empty) applies to all fd-engine output files and to this SKILL.md. Do not embed any guarded token in generated HTML or descriptor JSON.

---

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
| Issue / dependency graph (live project, ≥ 5 issues) | `graph-templates/dep-graph.html` (fed by `scripts/gen-deps.py`) | Python-side topological layer assignment + elbow routing; declarative |
| Small dependency graph (≤ 6 nodes, hand-crafted) | `graph-templates/layered.html` or `linear-flow.html` | Hand-assign `--x/--y` with R1 even-stride; avoid dep-graph manual fill |
| Data flow (linear, 2–3 stages) | `graph-templates/linear-flow.html` | Unidirectional arrows, labels above |
| **Swimlane / message-flow pipeline** | **`graph-templates/lane-swim.html`** | N vertical lanes × N rows, cubic bezier S-curves, phase separators |
| API sequence | `graph-templates/sequence.html` | Participant lifelines + horizontal message arrows; cap 15 messages |
| State machine | `graph-templates/state.html` | `.fgraph-node.circle/.diamond` + semantic edge classes for start/end |
| Timeline / schedule | `graph-templates/gantt.html` | Date axis (`.fg-axis-date`) + horizontal bars; CSS-only, offline-safe |
| Proportion / share | `graph-templates/pie.html` | Pre-computed SVG arc paths + legend; no runtime |
| Entity-relationship schema | `graph-templates/er.html` | Entity boxes + crow's-foot markers (`.fg-er-*`) |
| **Hub-and-spoke, ≤ 6 peers, rich cards** | **`graph-templates/radial-hub.html`** | Pills, warn lines, multi-line |
| 7 radial nodes | `radial-ring.html` (no center) or split into sub-diagrams | fgraph caps at ~6 before labels collide |
| **Full-system architecture (≥ 15 components across ≥ 4 lifecycle layers)** | **`graph-templates/system-architecture.html`** | Users → cloud APIs → adapters → NATS bus strip → nested hub → stores → remote band; `.fg-bus-strip` spans full width; `.fgraph-group.{cluster,security-group}` overlays; 3-card executive summary row |
| Layered architecture (3–4 tiers) | `graph-templates/layered.html` or `deployment-tiers.html` | Dashed frames per layer, vertical fan-out |
| Multi-host deployment | `graph-templates/machine-clusters.html` | Cross-machine edge routing, wide aspect |
| Architecture layers (node topology, arrows needed, ≤8 nodes) | foreignObject+CSS Flexbox SVG | No pixel math; LLM only computes arrow coords; inline SVG, no JS |
| Architecture layers (text-heavy, stacked, no arrows) | CSS Grid cards | Fallback when no node-to-node connections needed |
| **Comparison / matrix (≥4 rows or ≥3 cols)** | **HTML `<table>`** | Tabular data is not a graph |
| Simple timeline | `.steps` timeline component | Shared CSS, no auto-layout needed |
| **2-variable correlation / X↔Y scatter** | **`graph-templates/scatter.html`** | Inline SVG data-chart; show relationship between two continuous variables |
| **3-variable data (X, Y + magnitude as size)** | **`graph-templates/bubble.html`** | Extends scatter; bubble radius encodes a third dimension |
| **Multi-axis comparison (N metrics, same scale)** | **`graph-templates/radar.html`** | Spider/radar chart; compare entities across N axes in one view |
| **Pipeline / stage conversion (funnel stages)** | **`graph-templates/funnel.html`** | Decreasing-width bars; show drop-off between sequential conversion stages |

**Decision rule:** pick the fgraph template whose shape matches (hub-and-spoke / linear / swimlane / layered / multi-host / ring / gantt / pie / er / sequence / state / dep-graph / **system-architecture**). Swimlane for message-flow pipelines, request lifecycles, clean-arch layer traces crossing multiple horizontal domains. **Full-system architecture (≥ 15 components across users → apis → adapters → bus → hub → stores) → `system-architecture.html`** — it composes nested `.fgraph-group` regions + the `.fg-bus-strip` primitive and ships a 3-card info row; prefer this over `radial-hub.html` whenever the reader's mental model is a top-to-bottom request lifecycle rather than "one hub, N peers". If > 8 nodes or complex flow that no other template covers → **split the diagram** or use `layered.html` with hand-assigned `--x/--y`. Tabular → HTML table. Architecture with node topology + arrows, ≤ 8 nodes → foreignObject+CSS Flexbox SVG. Stacked text-heavy, no arrows → CSS Grid cards.

**Visual target — read the golden example first (MANDATORY):** Every fgraph template ships a fully-rendered, placeholder-free golden example. Before filling a template, **`Read ${CLAUDE_PLUGIN_ROOT}/references/graph-templates/examples/<type>.html`** and treat it as the pixel-correct visual target your output must match — node spacing, arrow/marker proportions, label placement, density, the compact inline-CSS subset. The rendered example is a stronger anchor than any prose gate below (a self-check that "looks fine" mentally has passed on visibly broken output before — the example is what "correct" actually looks like). Examples exist for all 19 types: `dep-graph · deployment-tiers · dual-cluster · er · gantt · lane-swim · layered · linear-flow · machine-clusters · pie · radial-hub · radial-ring · scatter · bubble · radar · funnel · sequence · state · system-architecture`.

**Dependency graph exception:** `dep-graph.html` is data-driven and requires `gen-deps.py` for correct topological layout (column widths, corridor routing). For hand-crafted small dependency graphs (≤ 6 nodes), use `layered.html` with hand-assigned `--x/--y` following R1 even-stride — manual fill of dep-graph.html produces irregular layouts because the template's positioning formulas are designed for Python-side injection, not human ad-hoc placement.

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
| System architecture (`system-architecture.html`) | header with `.fg-live-dot` + accent title | `.section-label.square` (optional) | built-in `.info-card-grid` row (3 cards); no extra hero needed |
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
- **Inline VERBATIM** — copy the entire canonical edge/marker block from `fgraph-base.css` (marker `<defs>` + `.fg-edge` rule) without trimming or partial-copying. Hand-trimming the edge CSS or marker defs is the root cause of giant-arrowhead regressions; see the anti-pattern entry at the bottom of this skill for the enforcement rule.
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
| **Swimlane / message-flow / request lifecycle** | **`graph-templates/lane-swim.html`** |
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
| 2-variable correlation / X↔Y scatter | `graph-templates/scatter.html` |
| 3-variable data (X, Y + magnitude as bubble size) | `graph-templates/bubble.html` |
| Multi-axis comparison (N metrics, radar/spider) | `graph-templates/radar.html` |
| Pipeline / stage conversion (funnel) | `graph-templates/funnel.html` |

**Decision rule for architecture diagrams:**
- Linear pipeline (2–3 stages) → `linear-flow.html`
- Swimlane / message-flow / request lifecycle (N lanes × N rows) → `lane-swim.html`
- Radial / hub-and-spoke with rich cards (pills, warn, multi-line) → `radial-hub.html` / `radial-ring.html`
- Layered architecture (3–4 tiers) → `layered.html` or `deployment-tiers.html`
- Multi-host deployment → `machine-clusters.html`
- Architecture with node topology + arrows, ≤ 8 nodes → foreignObject+CSS Flexbox SVG
- Stacked text-heavy, no arrows → CSS Grid cards (fallback)
- > 8 nodes or a shape no template covers → **split the diagram** into sub-diagrams, or use `layered.html` with hand-assigned `--x/--y`
- See `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/README.md` for the full decision matrix.

fgraph-radial caps at ~6 satellites before labels collide. For dense graphs (> 8 nodes) split into sub-diagrams rather than cramming — **or** use Live mode (below).

### Live mode (opt-in, interactive) — alternative to splitting

Dense architecture (> 8 nodes) that must stay ONE diagram **and** be explorable → `live` mode instead of splitting. Nodes stay declarative (`--x/--y`); a small inlined runtime auto-routes edges from the rendered node rects (no hand-authored `<path>`, resize-safe, no `preserveAspectRatio` stretch) and adds hover-spotlight + tone/group filtering.

**Two modes, one design-system:**
- **static** (default) — hand-authored, or `gen-fgraph.py --mode static`. Print/PDF/embed-safe. Existing 15 templates unchanged.
- **live** (opt-in) — `gen-fgraph.py --mode live`, or a hand-authored `data-fgraph="live"` wrap. Interactive. **Breaks print/PDF** (needs JS) — never use it for PDF export.

**Data-driven:** `scripts/gen-fgraph.py --in <graph>.json --out <file>.html [--mode live|static]` generalizes `gen-deps.py` to any node/edge graph (DAG-layered rows, R1 even-stride placement). `dep-graph.html` stays the issue-specific generator.

**Contract** (emit exactly; consumed by `fgraph-auto.js` + `fgraph-interact.js`):
```html
<div class="fgraph-wrap {accent}" data-fgraph="live" data-interactive="true">
  <div class="fgraph-node {shape} {tone}" data-node="id" data-group="g" style="--x:..;--y:..">…</div>
  <script type="application/json" class="fgraph-edge-data">
    [{"f":"a","t":"b","tone":"orange","mods":["thick"],"label":"…"}]
  </script>
  <svg class="fgraph-edges" data-coord="px"></svg>   <!-- empty; runtime draws -->
</div>
```
- Inline `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/fgraph-auto.js` + `fgraph-interact.js` into the output `<script>` block (Mode A, file://-safe) — same directive as `theme-toggle.js`. Live styling ships inside `fgraph-base.css` (no extra file). Runtime injects its own markers (`fg-arr-{tone}--live`) and is a strict no-op on any page without a `data-fgraph="live"` wrap.

**QC delta vs static:** in live mode R4 (straight-arrow), arrow-routing, and R6 (node masking) are **auto-satisfied** — anchors land on node borders by construction → mark N/A. Add instead: runtime no-ops on static pages · edges redraw on resize (`ResizeObserver`) · markers injected · `data-coord="px"` present on the live `<svg>`.

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

## Layout Rules (CRITICAL)

These rules apply to ANY fgraph diagram with multiple node rows — `system-architecture`, `layered`, `machine-clusters`, `deployment-tiers`. Each rule caused a real bug in a prior rendering cycle. Skip these and the output will overlap, clip, or look visibly uneven on first render.

Each rule has a **formula** (mechanical check) and **Wrong / Right** examples. Compute the math before writing the template, not after.

### R1. Even-stride horizontal distribution

**CRITICAL:** For N cards in a row, card centers go at `(100 / 2N) × (2i+1)` for `i = 0..N-1`. This guarantees equal left/right edge margins AND equal inter-card gaps.

| N | Centers |
|---|---|
| 2 | `25, 75` |
| 3 | `16.67, 50, 83.33` |
| 4 | `12.5, 37.5, 62.5, 87.5` |
| 5 | `10, 30, 50, 70, 90` |

**Wrong:** `--x: 12, 37, 63, 85` for 4 cards — gaps between centers are 25/26/22, right edge margin (100 − 85 − w/2 = 5.5%) is 3% larger than left (12 − w/2 = 2.5%). Visibly uneven.

**Right:** `--x: 12.5, 37.5, 62.5, 87.5` for 4 cards — stride is 25, both edge margins equal.

### R2. Minimum inter-card gap

**CRITICAL:** Inter-card gap must be ≥ 2%. For cards with center stride `s` and width `w`: `s − w ≥ 2`. Cards set to touch (`s = w`) look like one wide shape; cards overlapping (`s < w`) mis-render.

**Wrong:** Stride 17, width 17% → 0% gap, cards literally touching with no visual break. (Hit this on the Lyra stores row.)

**Right:** Stride 17, width 15% → 2% gap. Or stride 25 (4-card row), width 19% → 6% gap.

### R3. Row clearance from frame label

**CRITICAL:** When a `.fgraph-frame` dashed region has a label + sub at the top, the FIRST node row's top edge must be ≥ 2% below the frame sub. Card height ≈ `3% + (N_lines × 2%)` where N_lines = title + sub lines. Top edge = `--y − card_height / 2`.

| Card content | Height estimate | Half-height |
|---|---|---|
| Title + 1 sub | 6% | 3% |
| Title + 2 subs | 8% | 4% |
| Title + 3 subs | 10% | 5% |
| Title + pill + 3 subs | 12% | 6% |

**Wrong:** Frame sub at `top: 29%`, adapter row at `--y: 34`, card has 4 lines (half-height 6%) → top edge at `y = 28`, which clips the frame sub at y=29.

**Right:** Frame sub at `top: 26.5%`, adapter row at `--y: 34`, same 4-line card → top edge at y=28, 1.5% below sub. Safe.

### R4. Straight-arrow invariant

**CRITICAL:** Vertical data flow ⇒ `arrow.start.x == arrow.end.x`. Horizontal data flow ⇒ `arrow.start.y == arrow.end.y`. Any drift is a typo, not a design choice — it reads as "the flow goes sideways", confusing the reader.

Use non-straight paths only for **intentional cross-section routes** (e.g., Anthropic API ⇒ hub LLM layer crossing three rows — those MUST be cubic beziers with two control points).

**Wrong:** `M 16,79 L 14,83` for an Agent (x=14) → AgentStore (x=14) connection — diagonal because of a typo.

**Right:** `M 14,79 L 14,83` — purely vertical. Or if intentional, use a labeled curve: `M 62.5,22 C 62.5,40 56,55 48,66` with two control points demonstrating the long route.

### R5. Semantic edge color reservation

**CRITICAL:** Edge colors carry meaning. Reserve each for its one purpose; don't reuse for aesthetic variety.

| Color | Reserved for | Never |
|---|---|---|
| `cyan` | Network ingress (external user → service) | Internal calls |
| `orange` | Message bus / NATS / Kafka / event flow | Auth |
| `purple` | Storage read/write (to `.fgraph-node.purple`) | Ingress |
| `red` / `rose` | **Security-only** — auth flows, guard boundaries, admin alerts | Anything else |
| `amber` | Cloud-API outbound (to `.fgraph-node.amber`) | Internal |
| `dim` | Phase-2 / planned / informational | Live flows |

**Wrong:** A red dashed curve for "Anthropic API → hub LLM" combined with a `.fgraph-group.security-group` (also rose dashed) → reader sees one broken rose shape instead of two separate flows. (Hit this on Lyra.)

**Right:** Amber dashed for Anthropic-API outbound (matches cloud-API amber tone); reserve red dashed for the security-group boundary + auth alerts back to admin.

### R6. Node opacity & arrow masking

**CRITICAL:** Default tone backgrounds on `.fgraph-node.{tone}` are `rgba(..., 0.14)` — arrows routing BEHIND a toned node show through. Use `.fgraph-node.solid` for any node that sits over an edge path, or place an explicit `.fg-edge-mask` rect before the path.

**Wrong:** Hub interior with purple tinted Agent + MemoryManager cards; Anthropic curve crosses behind Agent → stroke shows through the tint, reads as "the arrow crosses inside the Agent card".

**Right:** `.fgraph-node.purple.solid` — opaque `--bg-card` base + purple tint via `background-image`; arrow stroke cleanly masked. Or: `<rect class="fg-edge-mask" x="..." y="..." width="..." height="..."/>` immediately before the `<path>`.

### R7. Overlay labels must not wrap

**CRITICAL:** `.fgraph-group__label` has `white-space: nowrap` + `max-width: calc(100% - 20px)` + `text-overflow: ellipsis`. Labels longer than the overlay width truncate; they never wrap into children. **Keep labels ≤ 20 chars** to avoid the truncation:

**Wrong:** `"Authenticator + GuardChain · trust levels"` — 42 chars, truncates to `"Authenticator + GuardCha…"` on a narrow overlay.

**Right:** `"Auth · Guard · trust"` — 20 chars, fits without truncation.

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
| `markerUnits="userSpaceOnUse"` on an arrow `<marker>` | **Remove it.** The `.fgraph-edges` SVG is `preserveAspectRatio="none"` (stretched) — `userSpaceOnUse` sizes the head in the 0..100 user space, which the non-uniform scale blows up to ~60–80px distorted arrowheads. Markers MUST omit `markerUnits` (→ `strokeWidth` default) with `markerWidth="6" markerHeight="6"`; strokes stay crisp via `vector-effect: non-scaling-stroke`. Copy the canonical defs from `fgraph-base.css`, never hand-author. |

---

## Phase 4 — Report

```
Created: {path}/{slug}.html

Open:    file://{path}/{slug}.html     (no server needed)

Serve + Deploy: see forge-ops.md
```

### Visual Quality Gates (run before writing file)

14-item pre-flight checklist. Every item is binary — tick it or fix it. Sourced from the gmdiagram QC pattern + architecture-diagram-generator conventions.

- [ ] **Even-stride (R1):** for every N-card row, compute `(100/2N)×(2i+1)` and verify each `--x` matches; edge margins and inter-card gaps are all equal
- [ ] **Min gap (R2):** for every card row, `stride − width ≥ 2%` (cards do not touch)
- [ ] **Row clearance (R3):** first row inside a `.fgraph-frame` has top edge ≥ 2% below frame sub label (compute half-height by content line count)
- [ ] **Straight arrows (R4):** vertical flow paths have `start.x == end.x`; horizontal have `start.y == end.y`; all diagonal paths are labeled intentional beziers with explicit control points
- [ ] **Edge semantics (R5):** red/rose reserved for security only; cyan for ingress; orange for message bus; purple for storage; amber for cloud-API out; dim for phase-2
- [ ] **Solid nodes (R6):** every `.fgraph-node.{tone}` that sits over an edge path has `.solid` class; or an explicit `.fg-edge-mask` rect precedes the crossing path
- [ ] **Overlay label length (R7):** every `.fgraph-group__label` is ≤ 20 chars (otherwise it truncates with ellipsis)
- [ ] **Text fit:** no labels overlap, no text overflows its container, no truncation ellipses on node titles
- [ ] **Arrow routing:** SVG paths do not pass through unrelated node boxes; endpoints land on node edges (not centers)
- [ ] **foreignObject xmlns:** every `<foreignObject>` root has `xmlns="http://www.w3.org/1999/xhtml"` — silent failure in Chrome/Edge otherwise
- [ ] **Layer gaps:** vertical spacing between layered rows matches `--layer-gap` (50px default from `shape-vocabulary.md`); no row heights drift from `--layer-h`
- [ ] **CSS class names:** semantic classes only (`.fgraph-node.cylinder`, `.arch-frontend`) — no inline `style="color:#..."` on nodes/edges (tokens only)
- [ ] **ViewBox fit:** content fills 80–95% of declared dimensions — no large empty regions, no clipping
- [ ] **Text escaping:** `&`, `<`, `>`, `"`, `'` escaped in labels/titles rendered inside SVG `<text>` or `<foreignObject>`
- [ ] **Legend accuracy:** legend lists only node types + edge tones actually present in the diagram — no leftover entries
- [ ] **Title accuracy:** `<title>` + `diagram:title` meta + hero `<h1>` all state the Frame Signal 2 takeaway consistently
- [ ] **Marker units:** no `<marker>` uses `markerUnits="userSpaceOnUse"` (giant/distorted heads on the stretched `.fgraph-edges` SVG); every arrow/crow's-foot marker omits `markerUnits` and uses `markerWidth="6" markerHeight="6"`
- [ ] **Marker refs:** every `url(#id)` arrow marker has a matching `<marker id="id">` in `<defs>` (including `fg-arr-*` arrow markers and, for ER diagrams, `fg-er-one`/`fg-er-many`/`fg-er-zero-one`/`fg-er-one-many`/`fg-er-zero-many` crow's-foot markers)
- [ ] **Tag balance:** SVG + HTML parse cleanly (no unclosed tags, no stray `<`/`>` in text nodes)
- [ ] **fgraph inlining:** `fgraph-base.css` is inlined into the output `<style>` (Mode A) — no `<link>` to `_shared/fgraph-base.css`
- [ ] **Color contrast:** body text uses `var(--text)` not `var(--text-dim)` on `var(--surface)`; AA minimum, AAA preferred
- [ ] **SVG validator:** `bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate-svg.sh <output>` exits 0 (checks tag balance, attr quotes, marker refs, path data, rsvg-convert smoke — skips gracefully if tools absent)

$ARGUMENTS
