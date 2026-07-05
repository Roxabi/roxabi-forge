---
name: forge-chart
description: >-
  Create a quick self-contained single-file HTML diagram — premium fd-engine
  node-edge visual (architecture, hub-spoke) with bezier edges, glow and
  edge-flow; or a swimlane, dependency graph, layered flow, or CSS explainer
  via fgraph static templates. No server needed, works with file://. Triggers:
  "draw" | "diagram" | "visualize" | "sketch" | "map" | "show the flow" |
  "quick visual".
summary: 'single-file native fgraph / CSS visual'
version: 0.6.0
allowed-tools: Read, Write, Bash, Glob, Grep, ToolSearch, Agent
---

# Chart — Single-File Quick Visual

Create a self-contained HTML file. All CSS/JS inline — no fetch, no external files, works with `file://`.
Use for: native fgraph topologies (hub-and-spoke, linear pipeline, layered), issue-dependency graphs, process/lifecycle swimlanes, or simple CSS explainer layouts.

Output: `~/.roxabi/forge/<project>/visuals/{slug}.html` or `~/.roxabi/forge/_shared/diagrams/{slug}.html`.

**Read before generating:**

```
${CLAUDE_PLUGIN_ROOT}/references/showcase-index.html          — full catalog of golden refs (read first)
${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md              — brand detection, output paths, deploy commands
${CLAUDE_PLUGIN_ROOT}/references/showcases/showcase-chart.html — golden fd-engine skill output (read first)
${CLAUDE_PLUGIN_ROOT}/references/base/reset.css            — concatenate first
${CLAUDE_PLUGIN_ROOT}/references/base/layout.css           — concatenate second
${CLAUDE_PLUGIN_ROOT}/references/base/typography.css       — concatenate third
${CLAUDE_PLUGIN_ROOT}/references/base/components.css       — concatenate fourth
${CLAUDE_PLUGIN_ROOT}/references/base/explainer-base.css   — concatenate fifth (visual explainer components)
${CLAUDE_PLUGIN_ROOT}/references/aesthetics/               — select one based on detection logic
${CLAUDE_PLUGIN_ROOT}/references/shells/single.html        — HTML template with placeholders
${CLAUDE_PLUGIN_ROOT}/references/base/theme-toggle.js      — substitute {NAME}, then inline via {THEME_TOGGLE_JS}
${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md           — meta tag format + categories
${CLAUDE_PLUGIN_ROOT}/references/composition-contract.md   — when output embeds in forge-presentation
${CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-anchors.js  — craft path engine (hand-authored diagrams)
${CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-qa-checklist.md
${CLAUDE_PLUGIN_ROOT}/references/graph-templates/README.md — graph/topology templates (read when visual type = architecture / topology / flow / pipeline / dep-graph / data-chart)
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

The **fd-engine** (forge-diagram JS engine) is the generation path for all diagram types that require node-to-node edges. It replaces the static fgraph coordinate approach with DOM-measured bezier edges, providing lyra-stack-grade visual quality at any container size.

### Production pipeline (mandatory)

All fd-engine types use **one path** — agents write JSON only; never hand-assemble HTML:

```bash
python3 scripts/gen-fd.py --in <descriptor.json> --out <output.html> [--theme lyra-v2] [--title "..."]
python3 scripts/validate-fd.py --html <output.html> [--expect fixtures/<slug>.expect.json]
```

`gen-fd.py` assembles `fd-shell.html`, inlines aesthetic + `fd-engine.css` + page shell, embeds `fd-data`, bundles the engine via bun (`fd/bundler.js`), and inlines `fd-bootstrap.js`.

**Exit 0 from `validate-fd.py` is required before writing to `~/.roxabi/forge/`.** Lyra regression: `bun run gen-fd:check`.

Manual step-by-step assembly (`buildEngine`, inline CSS, bootstrap by hand) is **debug-only** — see `references/phase-3-generate.md § manual fallback`.

### Type routing table

These are the **first-class types the generator proposes by default** — both route through the fd-engine premium path. Everything else — topology (radial-hub, system-architecture, layered, …) and data-charts (scatter, bubble, radar) — is served by the **fgraph static templates** (see Structure table below), not the engine.

| Type | Layout source | Node card default | Family |
|---|---|---|---|
| `architecture` | declarative (LLM encodes `x`/`y` 0..100) | premium | architecture — `useCases[]` is an optional field, **not** a separate type |
| `hub-spoke` | declarative (LLM encodes `x`/`y` 0..100) | premium | architecture |

> **Retired 2026-06-22 (premium-only purge):** Auto-layout (elk) and standalone chart types were retired — topology / flow / timeline / proportion needs are served by fgraph static templates; further premium types will be reconstructed premium-first.

### Aesthetic → theme mapping

The `theme` field in the descriptor maps to a file under `${CLAUDE_PLUGIN_ROOT}/references/aesthetics/`. Use the filename stem:

| Aesthetic file | `theme` value | Use when |
|---|---|---|
| `lyra-v2.css` | `"lyra-v2"` | Lyra / Roxabi project diagrams — **default**, reference look |
| `lyra.css` | `"lyra"` | Lyra v1 (warm ember) |
| `roxabi.css` | `"roxabi"` | Roxabi brand (amber / gold) |
| `editorial.css` | `"editorial"` | Neutral / no-brand, editorial contexts |
| `blueprint.css` | `"blueprint"` | Technical / schematic (blueprint) |
| `terminal.css` | `"terminal"` | Terminal / cyan aesthetic |
| `caveman.css` | `"caveman"` | Bold / high-energy |

Use the detected aesthetic (from `forge-ops.md § Aesthetic Detection`) to select the `theme` value. Both the descriptor `theme` field and the inlined aesthetic CSS must use the same aesthetic. `fd-engine.css` is self-bootstrapping: its `:root` block provides fallback values for all required tokens (`--panel`, `--panel2`, `--bd2`, `--mut`, `--mut2`, `--mono`, `--sans`, `--slate`, `--amber`, `--cyan`, `--vio`, `--emer`, `--sky`, `--orng`, `--rose`) by mapping them from universal forge tokens or hard lyra-v2 fallbacks. All aesthetics render correctly — `lyra-v2` is the default and produces the reference look.

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
      "cardStyle": "premium",
      "glow": true,
      "icon": "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><circle cx='12' cy='12' r='9'/><path d='M12 3v18M3 12h18'/></svg>"
    }
  ],
  "edges": [
    {
      "f": "telegram", "t": "hub",
      "plane": "message",
      "label": "lyra.inbound.*",
      "flow": true
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
| `type` | string | First-class: `"architecture"` \| `"hub-spoke"` (declarative) |
| `title` | string | Diagram title (used in `<title>` + hero) |
| `theme` | string | Aesthetic name — matches `references/aesthetics/*.css` filename stem (see aesthetic→theme mapping above) |
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
| **nodes[].icon** | string | Optional inline `<svg>…</svg>` string — rendered in the card header icon slot (`.fd-ico`). Craft bar. |
| **nodes[].glow** | bool | Optional — `true` adds an accent halo (`.fd-glow`) to the premium card. Use on the hub / hero node only. Craft bar. |
| **edges[].f / t** | string | From / to node IDs |
| **edges[].plane** | string | Semantic plane (determines edge color from aesthetic tokens) |
| **edges[].label** | string | Optional edge label (shown at bezier midpoint on hover) |
| **edges[].flow** | bool | Optional — `true` adds the ambient marching-dash animation (`.flow`, 20s) for passive data/async flow. Craft bar. |
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

### Craft Quality Bar (the reference standard — apply by default)

Distilled from the gold-standard lyra-diagram. Every diagram should reach this bar. Seven primitives, all defined in `fgraph-base.css` + `fd-engine.css`:

| # | Primitive | How to get it | Auto on fd-engine? |
|---|---|---|---|
| 1 | **Bézier edges** (Q-curves, not straight lines) | fd-engine computes DOM-measured beziers | ✅ automatic |
| 2 | **Ambient edge-flow** (slow 20s marching dash on passive data/async) | descriptor `edges[].flow: true` → `.flow` class; or hand-author `.fg-edge.flow` | ✅ via `edge.flow` |
| 3 | **Dual-font nodes** (Sans title / Mono descriptor) | fd `.fd-title` = `var(--sans)`, `.fd-sub` = `var(--mono)`; fgraph `.fgraph-title` (Outfit) + `.fgraph-sub` (Space Mono) | ✅ automatic (matches the lyra-diagram gold standard) |
| 4 | **Per-node SVG icon** | descriptor `nodes[].icon: "<svg>…</svg>"` → `.fd-ico` slot; or `.fgraph-node__icon` markup | ✅ via `node.icon` |
| 5 | **Accent glow** on hub / hero node | descriptor `nodes[].glow: true` → `.fd-glow`; or `.fg-glow` class | ✅ via `node.glow` |
| 6 | **3-depth palette** (`--bg` → `--panel` → `--surface`) | fd-engine bootstraps `--panel`/`--panel2`; primitives fall back `var(--panel, var(--surface))` | ✅ bootstrapped |
| 7 | **Edge labels** — mono | fd `.fd-elabel` (SVG text, revealed on hover/spotlight — no chip); hand-authored `.fg-edge-label` or auto `.fg-edge-lbl` (fgraph-auto live) add the bg-knockout chip | fd-engine = mono label on hover; **bg-knockout chips are fgraph-only** |

**Default directive:** prefer the **fd-engine path with `cardStyle: premium`** — it delivers primitives 1–6 automatically (bézier · edge-flow · dual-font · icon · glow · 3-depth palette). For 7 (edge-labels) it renders hover-revealed mono text — **always-on bg-knockout label chips remain static-fgraph only.** Reach for a static fgraph template for print/PDF/no-JS output (hand-author the craft), or when you specifically need always-on label chips. When generating an fd-engine descriptor, set `glow: true` on the hub, `flow: true` on passive data/async edges, and an `icon` on each node where a recognizable glyph aids scanning.

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

**Pre-draw gate (before Structure):** If an HTML `<table>`, bullet list, or two sentences carry the same information as the planned figure, do not draw — use prose instead. If the reader would need a guided tour to parse the diagram, split or simplify. Before committing to a figure, ask: can any node, arrow, or label be deleted or merged without losing information?

### Structure — Which visual type?

Content-driven in both tracks. Brand `structure_defaults` (if present) act as **tiebreakers only** when content topology is genuinely ambiguous.

**Premium routing (default).** Match the content to one row; every row routes through the fd-engine premium path (or a kept native template where no engine equivalent exists):

| Content | Type → path | Why |
|---|---|---|
| **Architecture / system / topology** — any node-edge arch (one or more components connecting peers), at any scale | **fd-engine `type:"architecture"`** (or `"hub-spoke"`) via `scripts/gen-fd.py` — premium, declarative; add `useCases[]` for walkthroughs | DOM-measured bezier edges, premium cards, spotlight. Replaces radial-hub / system-architecture / layered / machine-clusters / linear-flow / dual-cluster / radial-ring — one premium path, not seven flat templates |
| Flowchart / decision DAG | fgraph `layered` / `linear-flow` static templates | CSS-based layered layout, file://-safe |
| State machine / lifecycle | fgraph `lane-swim` / `layered` static templates | Multi-lane phase layout |
| Schema — UML class **or** entity-relationship | fgraph `layered` static template | Layered entity layout; annotate relationships with edge labels |
| Sequence — strict API request/response | fgraph `lane-swim` static template | Multi-actor lanes; annotate with phase separators |
| **Swimlane — multi-actor / multi-lane process pipeline (preferred for lifecycle walkthroughs)** | **`graph-templates/lane-swim.html`** | N vertical lanes × N rows, cubic bezier S-curves, phase separators |
| Timeline / schedule / roadmap | fgraph `lane-swim` static template | Horizontal phase rows, CSS-based, no CDN |
| Proportion / share | fgraph `funnel` / `bubble` / `radar` static templates | CSS-based proportion visuals |
| Funnel / stage conversion (explainer **component**) | `graph-templates/funnel.html` | Decreasing-width bars; embed as a component |
| Issue / dependency graph (live project, ≥ 5 issues) | `graph-templates/dep-graph.html` (fed by `scripts/gen-deps.py`) | Python-side topological layer assignment + elbow routing; data-driven, **no fd-engine equivalent** |
| **Comparison / matrix (≥4 rows or ≥3 cols)** | **HTML `<table>`** | Tabular data is not a graph |
| Simple timeline | `.steps` timeline component | Shared CSS, no auto-layout needed |
| Architecture layers (node topology, arrows, ≤8 nodes, **print/no-JS**) | foreignObject+CSS Flexbox SVG | No pixel math; inline SVG, no JS — print fallback only |
| Architecture layers (text-heavy, stacked, no arrows) | CSS Grid cards | When no node-to-node connections are needed |

**Propositions (consider — not auto-templated).** The following are **no longer first-class routing targets.** Treat each as a *proposition to consider*, not a default template. When one fits, **generate it bespoke via the fd-engine** (premium path) rather than filling the flat static template — reach for the static template only for **print / PDF / no-JS** output or when the user explicitly asks for that static look. Static authoring docs remain in `graph-templates/README.md`.

| Proposition | Was routed as | Generate instead via |
|---|---|---|
| Hub-and-spoke, rich cards | `radial-hub.html` | fd-engine `type:"hub-spoke"` |
| Full-system architecture (≥ 15 components) | `system-architecture.html` | fd-engine `type:"architecture"` + `useCases` |
| Layered / deployment tiers | `layered.html` / `deployment-tiers.html` | fd-engine `type:"architecture"` |
| Multi-host deployment | `machine-clusters.html` | fd-engine `type:"architecture"` |
| Linear pipeline / dual cluster / radial ring | `linear-flow.html` / `dual-cluster.html` / `radial-ring.html` | fd-engine `type:"architecture"` |
| X↔Y scatter / 3-var bubble / N-axis radar | `scatter.html` / `bubble.html` / `radar.html` | Data-charts via fgraph static templates — out of scope as first-class; propose only when explicitly requested |

**Decision rule (fd-engine first for node-edge diagrams):**

1. **Any node-edge architecture / topology, at any scale** (architecture / hub-spoke / system / layered / multi-host / linear / ring) → fd-engine descriptor + `python3 scripts/gen-fd.py --in <descriptor.json> --out <file>.html`. Premium is the default at **any** node count — static templates are propositions (print/no-JS), **not** the ≤6-node default. Quality bar: `graph-templates/examples/fd-architecture.html` and `fixtures/lyra-stack-v2.json`.
2. **Swimlane / multi-actor pipeline / sequence-style flow** → `lane-swim.html` (preferred for lifecycle walkthroughs, API / message sequences, and actor pipelines).
3. **Issue dependency graph** → `gen-deps.py` (never hand-fill `dep-graph.html`).
4. **Tabular data** → HTML `<table>`. **Stacked text, no arrows** → CSS Grid cards.
5. **Static fgraph** (`radial-hub`, `linear-flow`, `layered`, `system-architecture`, …) → propositions: print / PDF / no-JS only, or an explicit static-look request. Hand-assign `--x/--y` with R1 even-stride.

Swimlane for message-flow pipelines crossing multiple horizontal domains. Split only when the reader needs two genuinely different topologies — not because fd-engine "can't handle density" (it can).

**Visual target — read the golden example first (MANDATORY):** Every template ships a fully-rendered, placeholder-free golden example. Before filling a template, **`Read ${CLAUDE_PLUGIN_ROOT}/references/graph-templates/examples/<type>.html`** and treat it as the pixel-correct visual target your output must match — node spacing, arrow/marker proportions, label placement, density, the compact inline-CSS subset. The rendered example is a stronger anchor than any prose gate below.

- **fd-engine first-class** (read the golden before generating): `fd-architecture` — the canonical golden with `useCases[]`; `fd-architecture-uc.html` is the particles+interactions smoke
- **Native kept** (no engine equivalent): `lane-swim` (swimlane / sequence / pipeline) · `dep-graph` (data-driven) · `funnel` (explainer component)
- **Proposition examples** (static look / print fallback — not first-class): `radial-hub · system-architecture · layered · deployment-tiers · machine-clusters · dual-cluster · radial-ring · linear-flow · scatter · bubble · radar`

Note: the auto-layout (elk) and chart fd-engine types (`flowchart`, `state`, `class`, `er`, `sequence`, `gantt`, `pie`, `xychart`) were retired 2026-06-22 (premium-only purge) pending a premium-first rebuild — route those needs to the fgraph static templates above (`lane-swim` for sequence / pipeline).

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
| Swimlane / sequence / pipeline (`lane-swim.html`) | `.hero.left-border` | `.section-label.dot` | `.phases` (time-grouped arcs) + `.card.accent` legend |
| Radial hub (`radial-hub.html`, ≤ 6 peers) | `.hero.left-border` | `.section-label.dot` | `.card.accent` legend for edge types (pills/warn/ok) |
| System architecture (`system-architecture.html`) | header with `.fg-live-dot` + accent title | `.section-label.square` (optional) | built-in `.info-card-grid` row (3 cards); no extra hero needed |
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

**fd-engine outputs additionally:**
- Run `python3 scripts/validate-fd.py` on the generated HTML (or `--in/--out` one-shot) — **exit 0 required** before writing to `~/.roxabi/forge/`.
- For Lyra-scale architecture, use `fixtures/lyra-stack-v2.expect.json` or author a sibling `<slug>.expect.json` with node counts and `layout.pairs` min gaps.

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

**Default routing directive (quality bar):** for any node-and-edge diagram, the **fd-engine path with `cardStyle: premium`** is the default — it delivers the Craft Quality Bar (beziers, glow, icons, edge-flow, dual-font typography) automatically. Treat the static fgraph templates in the table below as **propositions / layout hints**, not the output ceiling: pick the one whose *shape* matches, then render it through the fd-engine descriptor (set `glow`/`flow`/`icon` per the Craft Quality Bar). Use a static template's raw HTML only for print/PDF/no-JS exports, where the craft must be hand-authored.

| Content | Path (premium default) |
|---------|----------|
| Architecture / system / topology (any scale) | fd-engine `type:"architecture"` / `"hub-spoke"` → `scripts/gen-fd.py` (+ optional `useCases[]`) |
| **Flow / pipeline / sequence / lifecycle** | **`graph-templates/lane-swim.html`** (multi-actor / API sequence — preferred) · `layered.html` / `linear-flow.html` for simple layered flow |
| Funnel / stage conversion (explainer **component**) | `graph-templates/funnel.html` |
| Issue / dependency graph (data-driven) | `graph-templates/dep-graph.html` (fed by `scripts/gen-deps.py`) |
| Comparison / matrix (≥4 rows or ≥3 cols) | HTML `<table>` |
| Architecture, stacked text-heavy, no arrows | CSS Grid cards |

**Propositions** (consider, not first-class — generate bespoke via the engine; static template only for print / no-JS): radial-hub · system-architecture · layered · deployment-tiers · machine-clusters · linear-flow · dual-cluster · radial-ring → `type:"architecture"`. Data-charts (scatter · bubble · radar) → fgraph static templates, only when the user explicitly asks for one. Timeline / proportion / UML / ER / state-machine fd-engine types were retired 2026-06-22 (premium-only purge) — no current premium path, rebuild later.

**Decision rule for architecture diagrams:** default to **fd-engine `type:"architecture"`** via `python3 scripts/gen-fd.py --in <descriptor.json> --out <file>.html` for any node-and-edge architecture, at **any scale** — it absorbs the old radial-hub / system-architecture / layered / deployment-tiers / machine-clusters / linear-flow / dual-cluster / radial-ring shapes into one premium path (set `glow` on the hub, `flow` on passive edges, `icon` per node). Use **swimlane** (`lane-swim`) for multi-actor pipelines and lifecycle walkthroughs. Reach for a static template's raw HTML only for print / no-JS export. Full matrix: `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/README.md`.

For dense architecture, **fd-engine handles density** — do **not** split or fall back to fgraph live mode; generate one fd-engine diagram via `gen-fd.py`.

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

### fd-engine path (MANDATORY when Structure selected fd-engine)

**Agent writes JSON only — never hand-assemble the HTML bundle.**

```bash
# 1. Write descriptor JSON (see § Descriptor JSON schema above)
# 2. Generate self-contained HTML:
python3 scripts/gen-fd.py --in <descriptor.json> --out <output.html> [--theme lyra-v2] [--title "..."]
```

`gen-fd.py` handles: aesthetic CSS inlining · fd-engine.css · page shell · `buildEngine()` bundle via bun · bootstrap.

**Canonical fixture:** `plugins/forge/skills/forge-chart/fixtures/lyra-stack-v2.json` — regression input for Lyra-scale architecture.

**Quality bar:** output must have connected DOM-measured edges (no floating SVG paths). Compare against `graph-templates/examples/fd-architecture.html` and `lyra-stack-v2.html`. `huashu-design/*` mockups are **not** forge-chart targets.

**Deliver gate (mandatory before writing output):**

```bash
python3 scripts/validate-fd.py --in <descriptor.json> --out /tmp/validate-fd.html [--title "..."]
# or after gen-fd:
python3 scripts/validate-fd.py --html <output.html> [--expect fixtures/<slug>.expect.json]
```

Do **not** report success until `validate-fd.py` exits 0. It checks: no unfilled placeholders · bundle symbols · all `.fd-node` are `position:absolute` · nodes inside canvas · min gaps (adapters, zone labels). Lyra regression: `bun run gen-fd:check`.


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

**Agent mental model (all paths):** three invariants — **paint order** (connectors readable under/at node edges), **semantic encoding** (color/shape = role, not decoration; R5), **spatial discipline** (computed gaps, legend outside drawable bounds; R1–R3, R8). fd-engine delegates paint + space to `gen-fd.py` + `validate-fd.py`; the rules below are the **fgraph static appendix** when hand-placing nodes.

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

**Static SVG double-rect (hand-authored inline nodes):** stack an opaque underlay before any semi-transparent styled rect (same x/y/w/h):

```html
<rect fill="var(--bg-card)" x="..." y="..." width="..." height="..." rx="6"/>
<rect fill="rgba(...)" stroke="..." x="..." y="..." width="..." height="..." rx="6"/>
```

Draw connector `<path>` elements before node groups (document order) when not using `.solid` / `.fg-edge-mask`.

**fd-engine `kind:"bus"` placement:** bus nodes sit in the vertical band *between* adjacent service rows — not overlapping either row. Row-to-row clearance ≥ ~4% of canvas height (vertical spacing analogue; not the R2 horizontal formula).

### R7. Overlay labels must not wrap

**CRITICAL:** `.fgraph-group__label` has `white-space: nowrap` + `max-width: calc(100% - 20px)` + `text-overflow: ellipsis`. Labels longer than the overlay width truncate; they never wrap into children. **Keep labels ≤ 20 chars** to avoid the truncation:

**Wrong:** `"Authenticator + GuardChain · trust levels"` — 42 chars, truncates to `"Authenticator + GuardCha…"` on a narrow overlay.

**Right:** `"Auth · Guard · trust"` — 20 chars, fits without truncation.

### R8. Legend & tone keys outside drawable bounds

**CRITICAL:** Semantic legends (plane/tone keys, bus legend, node-type swatches) belong in **page shell** chrome — `.bar .legend` (fd-engine), `.card.accent` below the diagram, `.kv-strip` — never inside `.fgraph-frame`, never overlapping the active node/edge bbox.

| Path | Rule |
|---|---|
| **fd-engine** | `.legend` in `.bar` above `#fd-canvas` — canonical (`examples/fd-architecture.html`) |
| **New fgraph static** | Prefer shell `.card.accent` tone key; do not add new in-wrap plane swatches |
| **Legacy templates** | Existing `{{LEGEND}}` / `.fgraph-legend` inside `.fgraph-wrap` remains valid — **one-line caption only**, not a tone matrix |
| **Live fgraph** | Runtime `.fgraph-legend--live` is exempt (`fgraph-interact.js` contract) |
| **`radar.html`** | Exception: in-SVG legend required (SC3: all text inside `<svg>`) |

**Wrong:** A 4-tone swatch grid inside a dashed `.fgraph-frame` boundary — competes with topology.

**Right:** fd-engine `.bar .legend` chips; or shell `.card.accent` listing only tones present (R5-aligned).

---

## Presentation embedding (forge-presentation)

When a chart will live **inside** a scroll presentation (`forge-presentation`), read:

- `${CLAUDE_PLUGIN_ROOT}/references/composition-contract.md`
- `${CLAUDE_PLUGIN_ROOT}/references/diagrams/README.md`
- `${CLAUDE_PLUGIN_ROOT}/references/diagrams/craft-qa-checklist.md`

| Chart output | Path | Embed |
|---|---|---|
| fd-engine / fgraph single-file | `visuals/diagrams/{slug}.html` | iframe from presentation |
| Craft hand-authored | `visuals/diagrams/{slug}.html` | iframe — `craft-diagram-starter.html` + `craft-anchors.js` |
| ≤6 nodes, inline in presentation | stay in `{name}.html` | inline fgraph in presentation `<style>` — no iframe |

**Craft authoring workflow (hand-authored hub-spoke / swimlane):**

1. **Read golden first:** `references/diagrams/examples/craft-hub-spoke.html` (hub-spoke) or `craft-deploy-flow.html` (promote `curve: h`)
2. Copy `references/diagrams/craft-diagram-starter.html` → `visuals/diagrams/{slug}.html`
3. Set `data-slug="{slug}.html"`, `data-canvas-width` / `data-canvas-height`, `diagram:title` meta
4. Every hub/spoke/lane node: `data-anchor="{id}"` — position with CSS classes only
5. Connections: edit `#craft-edges` JSON only (`curve`: `q` hub-spoke, `l` straight, `h` + `y` promote flows)
6. Inline `craft-anchors.js` verbatim (starter already includes it)
7. Inline brand `<symbol>` blocks — no external `brand-icons.svg`
8. Gate: `python3 ~/.roxabi/forge/scripts/check-craft-diagram.py {path} --check` exit 0
9. Visual gate: walk `craft-qa-checklist.md` at `file://`
10. Embed in presentation via `<iframe class="diagram-frame" src="diagrams/{slug}.html">` — title stays inside diagram only

**Craft authoring rules:**
1. `data-anchor` on every connected node — position with CSS only
2. Edges in `#craft-edges` JSON — **never** hand-edit `<path d="…">` after moving spokes
3. `postMessage` type: `forge-diagram-resize` with `id` matching `data-slug`
4. `check-craft-diagram.py --check` per diagram, then `check-composition.py` on presentation
5. Title inside diagram only — no duplicate in presentation

**fd-engine vs craft decision:**

| Signal | Path |
|---|---|
| Descriptor validates (`validate-fd.py` exit 0), DOM-measured edges OK | fd-engine via `gen-fd.py` |
| Custom zone labels, edge-label overlays, blocked/interdit arcs, >6 spokes | craft + `craft-anchors` |
| Premium craft bar (IBM Plex, legend, rule-badge) with fixed geometry | craft + `craft-anchors` |
| Print/no-JS, ≤6 nodes | inline fgraph in presentation (no iframe) |

**Promote flows** (staging → prod): use `curve: "h"` + shared `y` in craft-edges, not bezier arcs.

---

## Anti-Patterns (FORBIDDEN)

| Anti-Pattern | Fix |
|--------------|-----|
| Copying fd-engine / craft diagram CSS into presentation HTML | iframe to `diagrams/{slug}.html` per composition-contract |
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

Three layers — agent pre-flight (all paths), fgraph static appendix (R1–R7), mandatory scripts. Every item is binary — tick it or fix it.

**Agent pre-flight (8 items):**

- [ ] **Pre-draw:** table, bullets, or ≤2 sentences carry the takeaway → don't draw (see Frame pre-draw gate)
- [ ] **Route:** correct engine per Structure table (fd-engine default for node-edge arch; table for matrices)
- [ ] **Semantics (R5):** plane/tones reserved — red/rose = security only; exactly one focal `.fd-glow` on fd-engine
- [ ] **Paint (R6):** fgraph static — nodes over edges → `.solid` or `.fg-edge-mask`; fd-engine → N/A (validate-fd handles routing)
- [ ] **Legend (R8):** tone/plane keys in shell only (fd: `.bar .legend`; new work: `.card.accent`); legacy `.fgraph-legend` one-line caption OK
- [ ] **Frame trace:** `<title>` + `diagram:title` meta + hero `<h1>` state Signal 2 takeaway consistently
- [ ] **Anti-patterns:** pass `anti-patterns.md` walk (Deliver phase)
- [ ] **Scripts:** `validate-fd.py` exit 0 (fd-engine path); `validate-svg.sh` exit 0 (fgraph/static SVG path)

**fgraph static appendix — run R1–R7** (formulas in § Layout Rules above) when output is hand-placed static fgraph, not fd-engine and not live mode. Also verify: text fit (no overlap/truncation on node titles), `fgraph-base.css` inlined (Mode A), `foreignObject` roots have `xmlns` if used.

**fd-engine appendix:** craft bar — one `.fd-glow`, `.flow` on passive edges, dual-font pairing (Sans title + Mono descriptor), icons all-or-none per diagram.

**Delegated to scripts (do not duplicate manually):** marker units/refs, tag balance, path data (`validate-svg.sh`); node-in-canvas bounds, layout pair gaps (`validate-fd.py` + expect JSON).

$ARGUMENTS
