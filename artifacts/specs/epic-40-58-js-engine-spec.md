# Epic #40 + #58 — forge-diagram JS Engine: Architecture & Spec

**Status:** Draft · 2026-06-02 | Decisions resolved 2026-06-03
**Supersedes:** epic-40 Python plan (artifacts/plans/epic-40-wave-plan.md) — archived, not executed.
**Replaces:** issue #40 acceptance criterion "zero JS runtime / compile-time static SVG" — DROPPED.
**Core decision:** JS runtime engine, lyra-stack-grade visual bar. Settled — do not relitigate.

---

## Resolved Decisions (2026-06-03)

All four items below are closed. Do not relitigate.

### RD-1 — elkjs: HYBRID (gen-time bun layout, runtime DOM edges)

elkjs runs at **generation time via bun**. The forge-chart skill invokes a bun step that imports
`elk.bundled.js`, computes node x/y for auto-layout types, and injects the resulting positions
directly into the descriptor JSON (nodes[i].x / nodes[i].y populated). The browser engine receives
pre-positioned nodes and does NOT inline elk.bundled.js.

Edges are still DOM-measured at runtime (getBoundingClientRect + ResizeObserver). Bezier paths
redraw on every resize — only node positions are static.

Rationale: artifacts deploy to Cloudflare Pages (bandwidth matters) → no 1.6 MB per file.
bun is already first-class in the stack (CI bun install/bun lint). Losing node-reposition-on-resize
is acceptable because edge re-measurement on resize still keeps arrows accurate.

Impacts: §1.2 data flow updated, §1.4 size budget updated (elkjs removed from inline payload),
§4 runtime/gen-time table updated, §5 single-file contract updated, Slice S2 updated.

### RD-2 — Particles: opt-in, one-shot on trigger, loop via options.particles:"loop"

- Default: particles OFF. Descriptor must set `options.particles: true` to enable.
- Default mode: one-shot per edge on hover/use-case trigger (750 ms, easeInOutCubic).
- Continuous loop: `options.particles: "loop"` — engine runs spawnParticle() repeatedly on active edges.
- Rationale: Playwright screenshot captures must be motion-free by default (AC-9). Loop is an
  explicit opt-in for live dashboards / lyra-stack-style use-case animation.

### RD-3 — Card style: premium by type default + per-node override

- Architecture / hub-spoke types: premium card (accent bar, subtitle, tag badge, host badge) by default.
- Auto-layout types (flowchart, state, class, ER, sequence): simple box (title + optional subtitle) by default.
- Per-node override via `nodes[i].cardStyle: "premium" | "simple"` — overrides type default.
- Rationale: flowchart/state diagrams have many small nodes; premium cards are too heavy at that scale.
  The per-node override (option c from original OQ-3) is added on top of the type default (option b).

### RD-4 — NEW CONSTRAINT: Modular engine source for disjoint slice footprints

fd-engine source is structured as CORE module + per-type modules concatenated at generation time.
Slice S1 owns the bundler and core. Slices S2–S7 each own exactly one `types/*.js` file.
No shared registry file that multiple slices must edit. See §8 "Slice footprints" table.

Source tree:
```
plugins/forge/references/graph-templates/fd/
├── core.js          ← S1 — canvas setup, rect(), pairKey(), faceFor(), portAnchor(), stubLen()
├── edges.js         ← S1 — draw(), redraw(), ResizeObserver wiring, marker defs
├── particles.js     ← S7 — spawnParticle(), easeInOutCubic(), clearParticle(), loop mode
├── cards.js         ← S1 — renderNode(), premium vs simple card dispatch, .fd-card-premium
├── interactions.js  ← S7 — spotlight(), clearSpot(), use-case step sequencer, sidebar
├── bundler.js       ← S1 — concatenate fd/ modules → single inline <script> at gen time
│                           type registry: filename-based discovery (glob fd/types/*.js)
└── types/
    ├── architecture.js  ← S1 — declarative layout handler, zone placement (placeZones)
    ├── flowchart.js     ← S2 — bun elk layout call + node-position injection for flowchart
    ├── state.js         ← S2 — bun elk layout call + node-position injection for state
    ├── class.js         ← S3 — attribute-row node renderer, class-specific card structure
    ├── er.js            ← S3 — entity-row renderer, crow's-foot marker injection
    ├── sequence.js      ← S4 — participant strip, lifeline y-math, activation boxes
    ├── xychart.js       ← S5 — pure SVG math: bar/line/combined, axis ticks, grid lines
    ├── gantt.js         ← S6 — .fg-gantt-bar position map, section headers
    └── pie.js           ← S6 — arc path math, legend column
```

Type registry convention: `bundler.js` discovers types via `glob('fd/types/*.js')` at gen time —
no shared manifest file that slices must edit. Adding a new type = drop a file in `fd/types/`.
The only seam is `bundler.js` (owned by S1); later slices never touch it.

---

## 0. Decision Context (read-once, skip on repeat sessions)

### Why the Python plan was dropped

Epic #40 specified a Python port of beautiful-mermaid producing compile-time static SVG. Issue #58
specified an opt-in JS edge engine for fgraph live mode. The two were written as siblings.

The decision to merge and pivot is based on two constraints discovered in sequence:

1. **Quality ceiling of static SVG:** lyra-stack-v2.html (977 lines) demonstrates that the quality
   bar — true-pixel-space edge routing, proportional bezier curves, deduped port anchors, rAF particle
   flow — is only achievable with DOM measurement. `getBoundingClientRect()` cannot run at Python
   generation time. Static SVG with LLM-computed coordinates produced recurring layout bugs (7 R1-R7
   rules, 14-item QA checklist, 9/9 bubble-coord errors on PR #55). The root cause is that the LLM
   does geometry poorly; moving geometry to a Python layout engine (igraph Sugiyama) improves
   determinism but still cannot produce lyra-grade edge curves — elkjs and igraph both output raw
   coordinates, not DOM-measured bezier paths.

2. **preserveAspectRatio="none" is load-bearing for current fgraph:** PR #59 (fixing issue #57)
   confirmed that the stretched-grid SVG cannot be migrated to uniform-aspect without detaching edges
   from HTML nodes. The HTML nodes live in % space; the SVG overlay uses `none` to map SVG coords to
   HTML coords. The fix (PR #59) was a drift-lock guard, not an architectural fix. The architectural
   fix IS the JS engine from #58 — DOM measurement eliminates the stretched-grid entirely.

### What is kept from the original issues

From #40: the type coverage (flowchart, state, sequence, class, ER, xychart, gantt, pie), the 8
themes, the aesthetic mapping, the guard-safety contract (forge-diagram / no lowercase mermaid under
plugins/forge/), the wave-plan execution harness model.

From #58: the entire technical approach — `getBoundingClientRect` + ResizeObserver, rAF particle flow,
`getPointAtLength`, `marker-end` per semantic plane, single-file output.

The Python package `packages/forge-diagram/` from the wave plan is DROPPED in its entirety.

---

## 1. Engine Architecture

### 1.1 Conceptual Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  INPUT                                                              │
│  Diagram descriptor (JS object / JSON) — produced by LLM in        │
│  forge-chart skill, embedded in output HTML as <script type=        │
│  "application/json" id="fd-data">                                   │
│   { type, nodes[], edges[], layout?, theme?, options? }             │
└────────────────────────┬────────────────────────────────────────────┘
                         │ inline JS engine reads at DOMContentLoaded
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — NODE RENDERER                                           │
│  Reads descriptor nodes[]. Emits HTML .fd-node divs into            │
│  .fd-canvas (position:relative). Applies fgraph-base.css            │
│  classes (.fgraph-node, .hexagon, .cylinder, .pill, tones)          │
│  + lyra-style card structure (accent bar, title, subtitle, tag)     │
└────────────────────────┬────────────────────────────────────────────┘
                         │ nodes appended to DOM
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — LAYOUT ENGINE                                           │
│                                                                     │
│  Branch A — elkjs GEN-TIME (for auto-layout types: flowchart,       │
│  state, class, ER, sequence)                                        │
│    bun step at generation time: elkjs.layout(graph) →              │
│    x/y/width/height injected into descriptor nodes[] JSON.          │
│    elk.bundled.js is a bun tool — NEVER inlined in HTML output.    │
│    Browser receives pre-positioned descriptor; no elk at runtime.   │
│                                                                     │
│  Branch B — declarative (for hub-spoke, architecture, gantt,        │
│  pie, scatter, bubble, radar, funnel)                               │
│    LLM encodes explicit % positions in descriptor (same 0..100      │
│    space as current fgraph). No bun step invoked.                   │
│    Positions applied as style="--x:N;--y:N" → fgraph-base.css.     │
└────────────────────────┬────────────────────────────────────────────┘
                         │ all nodes at final pixel positions
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — EDGE ENGINE (lyra-stack technique, verbatim-adapted)    │
│                                                                     │
│  For each edge (f→t or f↔t):                                        │
│    rect(id) = getBoundingClientRect of .fd-node[data-id=id]         │
│             minus canvas.getBoundingClientRect() offset             │
│                                                                     │
│  Deduplication: canonical pairKey = [a,b].sort().join('|')         │
│  Port selection: faceFor(dx,dy) → top/bottom/left/right            │
│  Port slots: spread across face, proportional to slot count         │
│  Cubic bezier: stubLen = clamp(dist*0.35, 30, 220)                 │
│  Path: M src.x,src.y C c1x,c1y c2x,c2y dst.x,dst.y                │
│                                                                     │
│  SVG overlay: <svg class="fd-edges" style="                         │
│    position:absolute;inset:0;width:100%;height:100%;                │
│    pointer-events:none;overflow:visible">                           │
│  Markers: <marker id="fd-arr-{plane}"> per semantic plane          │
│  (plane = control / write / read / data / async / feedback)        │
│                                                                     │
│  ResizeObserver on .fd-canvas → redraw() re-runs full edge pass    │
└────────────────────────┬────────────────────────────────────────────┘
                         │ edges drawn as bezier SVG paths
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 4 — PARTICLE ENGINE (rAF, opt-in per diagram / per edge)    │
│                                                                     │
│  spawnParticle(edgeF, edgeT, plane):                                │
│    pathEl = svg.querySelector('[data-pk="f|t"]')                    │
│    len = pathEl.getTotalLength()                                    │
│    rAF loop: easeInOutCubic(t) → d = t*len                         │
│              pt = pathEl.getPointAtLength(d)                        │
│              move <circle> (core + halo) to pt.x, pt.y             │
│    Duration: 750ms default, configurable per edge                  │
│    Fire-and-forget OR continuous loop (options.particles mode)     │
└────────────────────────┬────────────────────────────────────────────┘
                         │ optional animation
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 5 — INTERACTIONS (opt-in)                                   │
│                                                                     │
│  Hover spotlight: dimmed class on canvas, hot class on touched      │
│  edges + neighbor nodes. Sidebar panel (lyra-style) optional.       │
│  Use-case step animation (optional: descriptor.useCases[])         │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow (generation time vs runtime)

```
GENERATION TIME (bun, dev machine — no Cloudflare)
══════════════════════════════════════════════════
LLM (forge-chart skill)
  ↓ produces diagram descriptor JSON
  │   (for auto-layout types: nodes[i].x/y are ABSENT at this stage)
  │
  ├─ if descriptor.layout === 'auto' (flowchart/state/class/ER/sequence):
  │    bun gen-time step:
  │      import elk.bundled.js (bun, dev machine only — NEVER inlined into output)
  │      elkjs.layout(graph) → PositionedGraph
  │      inject x/y/width/height into descriptor nodes[] in-place
  │    descriptor now has ALL nodes[i].x/y populated
  │
  ↓ reads bundler.js → concatenates fd/*.js + fd/types/{type}.js
  ↓ reads fgraph-base.css (inlined)
  ↓ reads forge base/ + aesthetic CSS (inlined)
  → assembles single HTML file with:
      <style>  forge base + aesthetic + fgraph-base  </style>
      <style>  fd-engine.css (canvas / overlay / node extension rules)  </style>
      <script type="application/json" id="fd-data">{ nodes[i] already have x,y }</script>
      <script> fd-engine.js (all layers 1-5, NO elk.bundled.js) </script>

OUTPUT: single self-contained .html — no fetch, no CDN, file://-safe, elk NOT inlined

RUNTIME (browser / file://)
═══════════════════════════
DOMContentLoaded:
  parse fd-data JSON
  renderNodes() → append .fd-node divs using x/y from descriptor (already computed)
  draw() → getBoundingClientRect all nodes → compute bezier paths → paint SVG overlay
  placeZones() → if descriptor.zones[], compute zone bounds from rect() calls
  new ResizeObserver(redraw).observe(canvas)  ← edges re-measure; node positions static
  if descriptor.options.particles → startParticles()
  if descriptor.useCases → wireUseCaseUI()
```

### 1.3 File Structure (net-new, under plugins/forge/)

```
plugins/forge/
├── references/
│   └── graph-templates/
│       ├── fd/                    ← NEW — modular engine source (see RD-4)
│       │   ├── bundler.js         ← S1 — glob fd/types/*.js → concatenate → inline <script>
│       │   ├── core.js            ← S1 — canvas setup, rect(), pairKey(), faceFor(), portAnchor(), stubLen()
│       │   ├── edges.js           ← S1 — draw(), redraw(), ResizeObserver, marker defs
│       │   ├── cards.js           ← S1 — renderNode(), premium/simple dispatch, .fd-card-premium
│       │   ├── particles.js       ← S7 — spawnParticle(), clearParticle(), easeInOutCubic(), loop mode
│       │   ├── interactions.js    ← S7 — spotlight(), clearSpot(), use-case step sequencer, sidebar
│       │   └── types/
│       │       ├── architecture.js ← S1 — declarative layout handler, zone placement
│       │       ├── flowchart.js   ← S2 — elk gen-time layout metadata, flowchart card rules
│       │       ├── state.js       ← S2 — elk gen-time layout metadata, state-specific shapes
│       │       ├── class.js       ← S3 — attribute/method row renderer
│       │       ├── er.js          ← S3 — entity row renderer, crow's-foot marker injection
│       │       ├── sequence.js    ← S4 — participant strip, lifeline y-math, activation boxes
│       │       ├── xychart.js     ← S5 — pure SVG math: bar/line/combined, axis ticks
│       │       ├── gantt.js       ← S6 — .fg-gantt-bar position map, section headers
│       │       └── pie.js         ← S6 — arc path math, legend column
│       ├── fd-engine.css          ← NEW (generated by S1 — static, not concatenated)
│       └── examples/
│           └── fd-{type}.html     ← one per type (flowchart, state, sequence, ...)
├── skills/
│   └── forge-chart/
│       └── SKILL.md              ← updated routing table (diagram types → fd-engine)
```

No `packages/forge-diagram/` Python package. No `scripts/render-diagram.py`.
`elk.bundled.js` is a bun-side tool — it lives in `node_modules` (already present via beautiful-mermaid
clone) and is NEVER copied into `plugins/forge/`.

### 1.4 Size Budget

| Component | Size (minified) | Where it lives | Inlined in HTML? |
|-----------|----------------|----------------|-----------------|
| elk.bundled.js | ~1.6 MB | bun node_modules (gen-time tool) | NO — never inlined |
| fd-engine.js (layers 1-5, concatenated) | ~25 KB | fd/ modules → bundled at gen time | YES |
| fd-engine.css | ~5 KB | graph-templates/ | YES |
| fgraph-base.css | ~20 KB | existing, inlined | YES |
| forge base + aesthetic CSS | ~30 KB | existing, inlined | YES |
| **Total per HTML (any type)** | **~80 KB** | — | — |

All diagram types (auto-layout and declarative) now produce ~80 KB HTML. elkjs is a generation-time
tool — it runs in bun, does layout, injects positions into the descriptor, and is never written to the
output file. This eliminates the 1.6 MB per-file cost that motivated the hybrid decision (RD-1).

---

## 2. Layout Strategy per Diagram Type

| Type | Layout source | Node card style | Edge rendering | elk gen-time bun step? |
|------|--------------|----------------|----------------|----------------------|
| **flowchart** | elkjs gen-time (layered/sugiyama) → x/y injected | simple box (pill=decision, diamond=gate) | DOM-measured bezier overlay | YES |
| **state** | elkjs gen-time (layered) → x/y injected | simple box (circle=start/end, diamond=decision) | DOM-measured bezier overlay | YES |
| **sequence** | elkjs gen-time (participant x-positions only) | simple pill per participant | DOM-measured horizontal arrows + lifeline y-math | YES |
| **class** | elkjs gen-time (layered) → x/y injected | simple box (header+attr/method rows) | DOM-measured bezier, dashed=implements | YES |
| **ER** | elkjs gen-time (layered) → x/y injected | simple box with attribute rows + PK/FK | DOM-measured bezier + crow's-foot markers | YES |
| **xychart** | none (pure SVG math) | SVG rects/polylines | n/a — chart not graph | NO |
| **gantt** | declarative (% positions from descriptor) | .fg-gantt-bar HTML divs | n/a — no edges | NO |
| **pie** | declarative (SVG arc math) | SVG arc paths | n/a | NO |
| **hub-spoke / architecture** | declarative (LLM encodes % coords) | premium card (accent bar, tag, host badge) | DOM-measured bezier overlay + opt-in particles | NO |
| **dep-graph** | declarative (gen-deps.py populates % coords) | .fg-dep-card HTML positioned | DOM-measured bezier, elbow-corridor routing | NO |
| **scatter / bubble / radar / funnel** | none (SVG math, inline) | SVG elements only | n/a | NO |

### Sequence diagram special handling

elkjs is used only for participant x-positions (horizontal spacing). Vertical positions (message
arrows, activation boxes) are computed by the engine from message order — each message = fixed row
height multiplied by message index. This matches beautiful-mermaid's sequence layout strategy.

### Node rendering: card vs simple box (resolved — RD-3)

| Context | Default card style | Override |
|---------|-------------------|----------|
| Architecture / hub-spoke | **Premium** (accent bar, subtitle, tag badge, host badge) | `nodes[i].cardStyle: "simple"` |
| Auto-layout types (flowchart, state, class, ER, sequence) | **Simple** (title + optional subtitle) | `nodes[i].cardStyle: "premium"` |
| Data-chart types (scatter, bubble, radar, funnel, pie, gantt, pie) | **SVG only** (no HTML nodes) | n/a — these types bypass the node/edge engine entirely |

Type default is set by the `types/*.js` module for that type. Per-node override is applied in
`cards.js:renderNode()` which checks `node.cardStyle` before applying the type default.

---

## 3. Reuse vs Build Table

| Component | Origin | Action | Notes |
|-----------|--------|--------|-------|
| `rect()` + `getBoundingClientRect` edge measurement | lyra-stack-v2.html (line 492-496) | **Lift verbatim** | Core of the technique |
| `pairKey()` deduplication | lyra-stack-v2.html (line 498) | **Lift verbatim** | |
| `faceFor()` port selection | lyra-stack-v2.html (line 501-513) | **Lift verbatim** | |
| `portAnchor()` slot spreader | lyra-stack-v2.html (line 516-528) | **Lift verbatim** | |
| `stubLen()` proportional bezier offset | lyra-stack-v2.html (line 531-534) | **Lift verbatim** | |
| `draw()` full edge pass | lyra-stack-v2.html (line 537-626) | **Lift + generalize** | Parametrize plane colors from descriptor |
| `spawnParticle()` rAF particle | lyra-stack-v2.html (line 640-691) | **Lift verbatim** | |
| `easeInOutCubic()` | lyra-stack-v2.html (line 633) | **Lift verbatim** | |
| `spotlight()` / `clearSpot()` | lyra-stack-v2.html (line 722-751) | **Lift + generalize** | Make sidebar optional |
| use-case animation state machine | lyra-stack-v2.html (line 770-948) | **Lift + make optional** | Only emitted when descriptor.useCases present |
| ResizeObserver redraw | lyra-stack-v2.html (line 960) | **Lift verbatim** | |
| `elk.bundled.js` | beautiful-mermaid (vendor) | **Use as bun tool** | ~1.6MB, sync API, no WASM — runs in bun at gen time; NEVER inlined in HTML |
| elkjs layout options (sugiyama, spacing) | beautiful-mermaid/src/layout-engine.ts | **Adapt into fd/types/{type}.js** | Port directionToElk(), spacing constants per type |
| elkjs node sizing | beautiful-mermaid/src/text-metrics.ts | **Adapt for bun** | char-width estimate or `@napi-rs/canvas` measureText at gen time |
| per-type parsers (flowchart, state, class, ER, sequence) | beautiful-mermaid/src/ | **NOT reused** | Mermaid syntax parsing not needed — LLM emits descriptor JSON directly |
| per-type renderers | beautiful-mermaid/src/ | **NOT reused** | LLM emits node/edge descriptors; fd-engine renders them |
| `fgraph-base.css` — all node shapes, tones, primitives | existing | **Reuse as-is** | Inlined per current distribution rules |
| `.fgraph-node.{shape,tone}` class vocabulary | existing | **Reuse as-is** | fd-engine adds `.fd-node` class alongside fgraph classes |
| crow's-foot markers (fg-er-*) | existing fgraph-base.css | **Reuse** | ER type uses existing SVG marker defs |
| lyra-card structure (accent bar, tag badge) | lyra-stack-v2.html CSS (lines 135-195) | **Extract + generalize** | Move to fd-engine.css as `.fd-card-premium` modifier |
| forge aesthetics / theming tokens | existing aesthetics/ | **Reuse as-is** | fd-engine.css consumes CSS vars (--amber, --cyan, etc.) |

**Not reused:** Python/igraph layout, Pillow text metrics, syrupy snapshots, render-diagram.py,
packages/forge-diagram/ scaffold, `bun run beautiful-mermaid` cross-validation step.

---

## 4. Runtime vs Generation-time Split

| Concern | Where it runs | Justification |
|---------|--------------|---------------|
| Mermaid syntax parsing | **NEVER** — LLM writes descriptor JSON directly | Eliminates parser complexity; LLM is already doing semantic parsing |
| elkjs graph layout | **Generation time — bun** (RD-1) | bun imports elk.bundled.js; x/y injected into descriptor before HTML assembly; elk NOT inlined |
| Node sizing for elkjs (text metrics) | **Generation time — bun** | canvas measureText() unavailable at gen time → use bun's `@napi-rs/canvas` or a simple char-width estimate; elkjs only needs approximate widths to avoid overlap |
| Edge measurement (`getBoundingClientRect`) | **Browser runtime** — MUST | DOM geometry only available post-layout; nodes are at elk-computed positions |
| Bezier path computation | **Browser runtime** | Depends on edge measurement |
| ResizeObserver re-measure (edges only) | **Browser runtime** | Node positions fixed; edges re-measure and redraw on resize |
| Particle animation | **Browser runtime** | rAF is browser-only; opt-in (RD-2) |
| Use-case step sequencer | **Browser runtime** | DOM interaction |
| CSS assembly (base + aesthetic + fgraph-base) | **Generation time** (forge-chart skill, LLM) | No change from current workflow |
| fd-engine.js assembly (concatenate fd/ modules) | **Generation time — bun** (bundler.js) | glob fd/ modules → single inline <script> |
| fd-engine.css | **Generation time** (inlined) | Static file, no assembly needed |
| Descriptor JSON (with x/y populated) | **Generation time** (LLM + bun elk step) | Final descriptor has all positions before HTML write |

---

## 5. file:// Safety + Single-File Contract

Rules (inherited from lyra-stack-v2 + fgraph, updated for RD-1):

1. **No fetch() calls** — all assets inlined at generation time.
2. **No CDN dependencies** — elkjs is a bun gen-time tool, not a runtime dependency. Fonts from
   Google Fonts acceptable (degrade gracefully offline; fall back to system fonts).
3. **elk.bundled.js is NOT inlined** — it is a generation-time bun tool only. Output HTML has no
   elk dependency whatsoever. elk runs in bun on the dev machine, writes positions into the
   descriptor JSON, and is done. The browser never sees it.
4. **fd-data JSON** embedded as `<script type="application/json" id="fd-data">` — not a separate
   file, not a fetch. Contains pre-computed node positions for auto-layout types.
5. **Single output file** — forge-chart skill writes one `.html` per diagram (~80 KB for all types).
   No `_shared/` references in fd-engine output (fgraph Mode A rule applies).
6. **No eval(), no dynamic import()** — engine is static inline JS.

Exception: fgraph Mode B (multi-tab docs with ≥2 diagrams) still links `_shared/fgraph-base.css`.
fd-engine.js is still inlined per-tab in Mode B (each tab is independently openable). No elk change
— all tabs are ~80 KB regardless of type.

---

## 6. #40 ↔ #58 Reconciliation

### Original ownership

| Issue | Original scope |
|-------|----------------|
| #40 | Type coverage (8 diagram types), themes, aesthetic mapping, forge-chart routing integration — Python engine |
| #58 | JS edge engine technique for fgraph live mode — opt-in, framed as sibling to #40 |

### New structure — APPLIED (2026-06-03)

#58 closed (folded into #40). #40 re-scoped to the JS engine (title + body). Python sub-issues
#41–#48 closed (superseded). 8 new sub-issues of #40 created:

| Slice | Issue | Owns (disjoint footprint) | Size | Blocked-by |
|-------|-------|---------------------------|------|-----------|
| S1 | **#60** | `fd/{core,edges,cards,bundler}.js`, `fd/types/architecture.js`, `fd-engine.css` | F-full | — |
| S2 | **#61** | `fd/types/{flowchart,state}.js`, `scripts/fd-layout.mjs` | F-full | #60 |
| S3 | **#65** | `fd/types/{class,er}.js` | F-lite | #61 |
| S4 | **#66** | `fd/types/sequence.js` | F-lite | #61 |
| S5 | **#62** | `fd/types/xychart.js` | F-lite | #60 |
| S6 | **#63** | `fd/types/{gantt,pie}.js` | F-lite | #60 |
| S7 | **#64** | `fd/particles.js`, `fd/interactions.js` | F-lite | #60 |
| S8 | **#67** | forge-chart `SKILL.md` routing; DELETE `graph-templates/{sequence,state,er,gantt,pie}.html` | F-lite | #60–#66 |

All `fd/*` paths are under `plugins/forge/references/graph-templates/` → guard-scoped (zero lowercase
`mermaid`). `scripts/fd-layout.mjs` (S2) is the only file outside `plugins/forge/`.

### Waves (orchestrator invokes one per call; merge between)

```
W1 = [60]            S1 core — blocks everything
W2 = [61,62,63,64]   S2,S5,S6,S7  (need only S1; disjoint) — parallel
W3 = [65,66]         S3,S4        (need S2/elkjs; disjoint) — parallel
W4 = [67]            S8 routing+cleanup (needs all) — guard-sensitive, last
```

### Orchestrator runbook (cold-session, 0 human gate)

Harness: `artifacts/plans/epic-40-58-wave.mjs`. Run from repo root `/home/mickael/projects/roxabi-forge`.
Preconditions: `gh auth status` OK; `git fetch origin`; set turn token budget `+3M`.

```
∀ wave W in [ [60], [61,62,63,64], [65,66], [67] ]  (do NOT start next until current all MERGED):
  1. git checkout staging && git merge --ff-only origin/staging
  2. Workflow({ scriptPath: "artifacts/plans/epic-40-58-wave.mjs", args: W })  → { results[], failed[] }
  3. ∀ result r with status 'pr-opened':
       a. gh pr checks <PR> --watch                         # required check 'ci' green
       b. Read artifacts/frames/epic-40/<issue>/*.png        # orchestrator IS the visual reviewer (no human)
       c. ci green ∧ PNGs acceptable → gh pr edit <PR> --add-label reviewed
          → auto-merge.yml: squash + update-behind-PRs + close issue
          else → re-invoke step 2 for [r.issue] alone (one cycle), or leave blocked
  4. poll until every wave PR MERGED (gh pr view <PR> --json state)
  5. ∀ issue in failed[]: skip its dependents in later waves
Dependency-skip: #60 fail → abort all · #61 fail → skip #65,#66,#67 · any W2/W3 fail → #67 blocked.
Closeout: epic #40 auto-closes (each PR "Closes #N"); optional post-merge audit + recap.
```

---

## 7. Acceptance Criteria (rewritten for JS engine)

- [ ] **AC-1 Visual bar:** A hub-spoke architecture diagram generated by forge-chart matches
  lyra-stack-v2.html quality: edges measured in real pixel space (no stretched-grid artifacts),
  arrowheads true-size at any container width, proportional bezier curves.
- [ ] **AC-2 All types render:** All 8 #40 types (flowchart, state, sequence, class, ER, xychart,
  gantt, pie) plus hub-spoke/architecture produce valid, legible HTML output.
- [ ] **AC-3 ResizeObserver:** Resizing the browser window (or the containing element) triggers
  edge redraw within one animation frame. No stale paths after resize.
- [ ] **AC-4 file:// safe:** All output files open correctly with a `file://` URL in Chrome,
  Firefox, and Safari. No network requests observed in DevTools Network tab.
- [ ] **AC-5 Single file:** Each diagram is one `.html` file. No sibling asset files required.
- [ ] **AC-6 Themes:** The existing forge aesthetics (lyra-v2, cool-dark, and others) apply
  correctly via CSS custom properties. Edge colors derive from aesthetic tokens (--amber, --cyan,
  --purple, etc.) not hardcoded hex.
- [ ] **AC-7 Guard-clean:** `grep -rn '\bmermaid\b' plugins/forge/` returns empty after all
  routing updates. CI `Mermaid guard` check passes.
- [ ] **AC-8 elkjs auto-layout quality:** Flowchart and state diagrams lay out without node
  overlap, with consistent edge routing, competitive with beautiful-mermaid reference output.
- [ ] **AC-9 Particles off by default:** rAF particle flow is opt-in (descriptor.options.particles
  = true). Default diagrams have no animation and pass Playwright screenshot QA without motion blur.
- [ ] **AC-10 No preserveAspectRatio="none" in engine output:** fd-engine SVG overlay uses
  `position:absolute;inset:0;width:100%;height:100%` (pixel canvas), not a viewBox stretch. This
  kills the giant-arrowhead bug class at the root (#57 root cause).

---

## 8. Phasing / Slices

### Slice S1 — fd-engine core (hub-spoke + architecture, no elkjs)
**Size:** F-full (new subsystem, ~400 LOC JS + CSS)
**Deliverables:**
- `graph-templates/fd-engine.js` (layers 1-3 for declarative layout branch, layer 4 particles, layer 5 spotlight)
- `graph-templates/fd-engine.css` (canvas container rules, `.fd-card-premium`, `.fd-node` extensions)
- `graph-templates/examples/fd-architecture.html` (lyra-stack-grade example: 8+ nodes, edges, zones)
- forge-chart SKILL.md: document fd-engine descriptor format; add hub-spoke/architecture routing
**Gates:** Playwright screenshot matches lyra-stack quality (AC-1). ResizeObserver fires (AC-3).
file:// safe (AC-4). Guard-clean (AC-7, S1 scope only). AC-10.

### Slice S2 — bun gen-time elk layout step + flowchart + state
**Size:** F-full (~200 LOC bun JS in fd/types/ + bun step wiring in forge-chart skill)
**Dependencies:** S1
**Deliverables:**
- `fd/types/flowchart.js` — flowchart-specific elk layout options (layered/sugiyama, directionToElk(), spacing); invoked by forge-chart skill bun step; injects x/y into descriptor
- `fd/types/state.js` — state-specific elk layout options; same pattern
- bun gen-time step in forge-chart skill (or `scripts/fd-layout.mjs`): reads descriptor, imports elk.bundled.js from node_modules, runs layout, writes positions back to descriptor JSON
- node-sizing utility (bun-side): char-width estimate or `@napi-rs/canvas` measureText
- examples/fd-flowchart.html, examples/fd-state.html (pre-positioned, verified layout)
**Gates:** No node overlap in generated output. Edge DOM-measurement correct (AC-8). Output HTML is ~80 KB (no elk inline). Bun step runs clean on dev machine (no network, no Cloudflare).

### Slice S3 — class + ER
**Size:** F-lite (~150 LOC JS: attribute-row node renderer, crow's-foot marker set)
**Dependencies:** S2
**Deliverables:**
- fd-engine.js: class node renderer (header + attr rows + method rows)
- fd-engine.js: ER node renderer (entity + PK/FK markers in row)
- ER SVG markers (fg-er-* — reuse existing or inline in fd-engine.css)
- examples/fd-class.html, examples/fd-er.html
**Gates:** Crow's-foot markers render true-size (AC-10 side effect). Attribute rows legible at default card width.

### Slice S4 — sequence
**Size:** F-lite (~150 LOC JS: participant x-layout via elkjs, message y-layout computed)
**Dependencies:** S2
**Deliverables:**
- fd-engine.js: sequence layout (participant strip + lifeline y-math + activation boxes)
- examples/fd-sequence.html
**Gates:** Participants non-overlapping. Message arrows cross lifelines horizontally (true pixel measurement).

### Slice S5 — xychart
**Size:** F-lite (~200 LOC JS: bar + line SVG math, axis ticks, grid lines)
**Dependencies:** S1 (aesthetic tokens only; no edge engine needed)
**Deliverables:**
- fd-engine.js: xychart renderer (pure SVG math, no node/edge engine)
- examples/fd-xychart.html (bar + line + combined)
**Gates:** Axes legible. Bar heights proportional to data. Line interpolation smooth.

### Slice S6 — gantt + pie
**Size:** F-lite (~100 LOC JS: wraps existing CSS primitives)
**Dependencies:** S1
**Deliverables:**
- fd-engine.js: gantt renderer (maps descriptor.bars[] → .fg-gantt-bar positions)
- fd-engine.js: pie renderer (arc path math, legend column)
- Delete or deprecate gantt.html, pie.html CDN-backed templates (fd-engine replaces them)
**Gates:** Matches existing native fgraph gantt/pie quality. No CDN dependency (AC-7 style).

### Slice S7 — particles + use-case animation
**Size:** F-lite (~200 LOC JS: rAF engine already in S1; this adds use-case step sequencer)
**Dependencies:** S1
**Deliverables:**
- fd-engine.js: use-case step sequencer (applyUcStep, syncButtons, selectUc — adapted from lyra-stack)
- descriptor.useCases[] schema documented in forge-chart SKILL.md
- examples/fd-architecture-uc.html (architecture example with 3 use-case walkthroughs)
**Gates:** Particles off by default (AC-9). Use-case play/pause/reset cycle works.

### Slice S8 — forge-chart routing + cleanup
**Size:** F-full (touches plugins/forge/, guard-sensitive)
**Dependencies:** S1..S7
**Deliverables:**
- forge-chart SKILL.md: full routing table update (all types → fd-engine descriptor format)
- Delete CDN-backed templates: gantt.html, pie.html, er.html (replaced by fd-engine path)
- Delete sequence.html, state.html fgraph templates (replaced by fd-engine)
- Guard check: `grep -rn '\bmermaid\b' plugins/forge/` must be empty
- shells/single.html: no change needed (fd-engine is inlined into output, not the shell)
**Gates:** All AC-1..AC-10. Lefthook mermaid-guard passes. CI Mermaid guard passes. No regression
on remaining fgraph templates (radial-hub, radial-ring, layered, machine-clusters, dep-graph,
lane-swim, system-architecture, scatter, bubble, radar, funnel — preserved as-is).

### Slice footprints (disjoint file groups)

Pairwise-disjoint per RD-4. S1 owns the shared seam (bundler.js, core modules); later slices add
files only — they do not edit any file owned by another slice.

| Slice | Owns (exclusive write) | Shared seam? |
|-------|----------------------|--------------|
| **S1** | `fd/core.js`, `fd/edges.js`, `fd/cards.js`, `fd/bundler.js`, `fd/types/architecture.js`, `fd-engine.css`, `examples/fd-architecture.html`, forge-chart SKILL.md (descriptor format + architecture routing) | bundler.js is the only seam — filename-based glob discovery means later slices add files, never edit bundler.js |
| **S2** | `fd/types/flowchart.js`, `fd/types/state.js`, bun layout step (`scripts/fd-layout.mjs` or inline in skill), `examples/fd-flowchart.html`, `examples/fd-state.html` | none |
| **S3** | `fd/types/class.js`, `fd/types/er.js`, `examples/fd-class.html`, `examples/fd-er.html` | none |
| **S4** | `fd/types/sequence.js`, `examples/fd-sequence.html` | none |
| **S5** | `fd/types/xychart.js`, `examples/fd-xychart.html` | none |
| **S6** | `fd/types/gantt.js`, `fd/types/pie.js`, `examples/fd-gantt.html`, `examples/fd-pie.html` | none |
| **S7** | `fd/particles.js`, `fd/interactions.js`, `examples/fd-architecture-uc.html` | none |
| **S8** | forge-chart SKILL.md (full routing table), DELETE: `graph-templates/{gantt,pie,er,sequence,state}.html` | touches plugins/forge/ — guard-sensitive, runs last |

Notes:
- `fd/bundler.js` (S1) discovers type modules via `glob('fd/types/*.js')` — S2..S6 add files to
  `fd/types/`; they never edit `bundler.js`. No shared manifest to conflict on.
- `scripts/fd-layout.mjs` (S2) is a NEW file, not a shared file. S3/S4 reuse the same bun step by
  reading the type module's elk options — the step itself does not need to be edited per type.
- S8 edits forge-chart SKILL.md, which S1 also touches. S8 depends-on S1..S7 so this is
  sequential (no conflict). S1's SKILL.md change is the descriptor format section only; S8 rewrites
  the routing table section. These are separate heading sections — if needed, split into two files.

### Slice dependency DAG

```
S1 (engine core + bundler + architecture type)
 ├─> S2 (bun elk step + flowchart.js + state.js)
 │    ├─> S3 (class.js + er.js)
 │    └─> S4 (sequence.js)
 ├─> S5 (xychart.js)
 ├─> S6 (gantt.js + pie.js)
 └─> S7 (particles.js + interactions.js)
                     └── all → S8 (routing + template deletions, guard-sensitive)
```

Critical path: S1 → S2 → S3/S4 → S8.
Parallel: S5, S6, S7 run concurrently with S2..S4 after S1 merges.

---

## 9. Residual Risks (open questions resolved — see Resolved Decisions section)

OQ-1, OQ-2, OQ-3 are all resolved (RD-1, RD-2, RD-3). No open questions remain.

### Risk R-1 — bun node-sizing accuracy at gen time

elkjs requires node width/height estimates to avoid overlap. The browser's `canvas.measureText()`
is unavailable at gen time. Options in S2:
- (a) `@napi-rs/canvas` — accurate, adds a bun dep
- (b) char-width heuristic (~7px/char at 13px font) — faster, may under-estimate wide labels
- (c) fixed node size per type (e.g. flowchart nodes = 120×40px) — simplest, may over-space

Recommendation: start with (c) fixed size per type in S2; switch to (b) heuristic if node overlap
is observed in QA screenshots. Do not add `@napi-rs/canvas` unless (b) is insufficient.
No human decision needed — S2 implementer decides.

### Risk R-2 — Sequence diagram y-layout precision

Sequence diagrams use elkjs for participant x-positions only. Message y-positions are computed by
the engine as `messageIndex * rowHeight`. If messages have multi-line labels, rowHeight must
expand — a fixed rowHeight will cause label clipping. S4 implementer must handle variable rowHeight
(measure label height in DOM after rendering participants, before drawing message arrows).

### Risk R-3 — S8 guard-clean after SKILL.md routing update

S8 edits forge-chart SKILL.md to add routing for all types. SKILL.md is under `plugins/forge/` —
any reference to diagram-type names must not contain the lowercase token `mermaid`. Type names in
the routing table (flowchart, state, sequence, class, er, xychart, gantt, pie) are guard-clean.
The guard is `\bmermaid\b` — type names are safe. Risk is low; include guard-check in S8 gates.

---

## 10. Guard Safety Contract (unchanged from epic-40-wave-plan.md §0)

All implementation agents must observe:

- Code identifiers: `forge_diagram`, `forge-diagram`, `fd-engine`, `fd-data` — NEVER `mermaid` / `forge_mermaid`
- The word `mermaid` (lowercase) may appear ONLY inside files that are NOT under `plugins/forge/`
- Capital `Mermaid` is exempt from the guard — docstrings/prose may say "Mermaid-compatible" freely
- Zero lowercase `mermaid` in any file under `plugins/forge/` (including fd-engine.js, fd-engine.css,
  forge-chart SKILL.md, any examples/)
- Post-edit self-check: `grep -rn '\bmermaid\b' plugins/forge/` MUST be empty before PR

Descriptor JSON schema uses `type` field values: `"flowchart"`, `"state"`, `"sequence"`, `"class"`,
`"er"`, `"xychart"`, `"gantt"`, `"pie"`, `"architecture"`, `"hub-spoke"`. Not "mermaid-*".

---

## 11. Descriptor JSON Schema (normative — LLM generates this)

```json
{
  "type": "architecture",
  "title": "Lyra — Architecture",
  "theme": "lyra-v2",
  "layout": "declarative",
  "canvas": { "height": 1040 },
  "options": {
    "particles": false,          // false (default) | true (one-shot on trigger) | "loop" (continuous)
    "spotlight": true,
    "sidebar": true
  },
  "nodes": [
    {
      "id": "hub",
      "x": 50, "y": 55,         // present for declarative types; injected by bun elk step for auto-layout types
      "kind": "bus",
      "n": "NATS Bus",
      "img": "nats:alpine",
      "d": "JetStream · 4222/4223",
      "plane": "message",
      "h": "M1",
      "cardStyle": "premium"     // optional; overrides type default (RD-3). "premium" | "simple"
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

For auto-layout types (`"layout": "auto"`), the LLM omits `x`/`y` on nodes. The forge-chart skill
runs a bun step (`scripts/fd-layout.mjs`) that imports elk.bundled.js, computes positions, and
writes `x`/`y` (in pixels, relative to canvas) back into the descriptor JSON before HTML assembly.
The output HTML descriptor always has all `x`/`y` populated — the browser engine never sees absent
positions.

For declarative types, `x` and `y` are in 0..100 % space (same as current fgraph convention).
The browser engine applies these as `style="left:Xpx;top:Ypx"` (converting % × canvas dimensions
for pixel-space edge measurement) or as `--x:N;--y:N` CSS props for fgraph-base.css primitives.

---

## 12. Reference Sources Used in This Spec

| Source | Path | What was extracted |
|--------|------|--------------------|
| lyra-stack-v2.html | /home/mickael/.roxabi/forge/lyra-stack-v2.html | Full JS technique (lines 395-977): rect(), draw(), spawnParticle(), use-case engine, ResizeObserver |
| Issue #58 | gh issue view 58 | Technical approach: getBoundingClientRect, rAF particles, opt-in live mode |
| Issue #40 | gh issue view 40 | Type coverage, phase plan, Python approach (now dropped) |
| Issue #57 / PR #59 | gh issue view 57, gh pr view 59 | preserveAspectRatio="none" load-bearing analysis, drift-lock outcome |
| fgraph-base.css | plugins/forge/references/graph-templates/fgraph-base.css | Node shapes, tones, SVG overlay pattern, coordinate system |
| graph-templates/README.md | plugins/forge/references/graph-templates/README.md | All 19 template types, shape vocabulary |
| epic-40-wave-plan.md | artifacts/plans/epic-40-wave-plan.md | Guard contract, wave harness, Python rationale (now superseded) |
| beautiful-mermaid layout-engine.ts | external_repos/beautiful-mermaid/src/layout-engine.ts | elkjs API, directionToElk(), node sizing pattern |
| forge-chart SKILL.md | plugins/forge/skills/forge-chart/SKILL.md | Current routing, distribution rules, generation workflow |

## Not Investigated

The following were not read (not needed for the design):

- Individual fgraph-auto.js and fgraph-interact.js (not reused — replaced by fd-engine.js)
- beautiful-mermaid per-type renderers (sequence/er/class/xychart) — not reused; LLM emits descriptor directly
- Individual graph-template HTML examples (radial-hub.html etc.) — structure understood via README.md
- forge-chart fixtures/README.md — no impact on engine architecture
