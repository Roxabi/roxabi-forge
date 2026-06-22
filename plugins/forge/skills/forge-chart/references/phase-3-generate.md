# Phase 3 — Generate (forge-chart)

> **Self-check:** if you are reading this file, the `Read ${CLAUDE_PLUGIN_ROOT}/skills/forge-chart/references/phase-3-generate.md` directive from `SKILL.md:Phase 3` resolved. If you are building a `forge-chart` output and have not seen this header, abort and report the unresolved path — Phase 3 body is mandatory for correct generation.

Read `shells/single.html` → substitute placeholders with content. The shell already contains:
- `{THEME_TOGGLE_JS}` placeholder (inline theme-toggle.js with `{NAME}` substituted)
- Diagram meta placeholders
- CSS placeholder slots

### Hero Section

Every chart SHOULD have a hero section. Use the **left border variant** by default. Exception: single quick diagrams (one fgraph block, no narrative) — a minimal title + diagram is acceptable without a hero.

```html
<section class="hero left-border">
  <div class="hero-inner">
    <div class="hero-label">{{EYEBROW}}</div>
    <h1>{{TITLE_PLAIN}} <span class="accent">{{TITLE_ACCENT}}</span></h1>
    <p>{{SUBTITLE}}</p>
    <div class="tag-row">
      <span class="tag {{TAG_TONE}}">{{TAG_TEXT}}</span>
    </div>
  </div>
</section>
```

Hero variants:
- `left-border` (default) — clean, minimal
- `top-border` — elegant, centered
- `elevated` — audit style with card background

### Section Labels (REQUIRED)

Use section labels with **dot prefix** for each major section:

```html
<div class="section-label dot">1.1 — Section Name</div>
```

Variants: `dot` (default), `triangle`, `square`.

### fgraph template inlining (diagram content)

Pick the matching template from `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/` and inline its body + `fgraph-base.css` into the output. For single-file output (Mode A), inline both into `<style>` and the diagram markup into `{CONTENT}`:

```html
<section class="diagram">
  <!-- inline fgraph template body — e.g. from graph-templates/radial-hub.html -->
  <div class="fgraph-wrap">
    <svg class="fgraph-edges" viewBox="0 0 100 100" preserveAspectRatio="none">
      <path class="fg-edge data" d="M 30,50 L 70,50" marker-end="url(#fg-arr-cyan)"/>
    </svg>
    <div class="fgraph-node pill" style="--x:20; --y:50">{{NODE_A}}</div>
    <div class="fgraph-node hexagon" style="--x:80; --y:50">{{NODE_B}}</div>
  </div>
</section>
```

No runtime JS — fgraph is declarative CSS + SVG. All custom props (`--x`, `--y`) live in the 0..100 coordinate space. Arrow markers (`fg-arr-*`) are defined in `fgraph-base.css`; ER templates also use `fg-er-*` crow's-foot markers.

Template picker — **default to the fd-engine premium path**; the static fgraph templates are *propositions* for print / no-JS only (full routing: `forge-chart/SKILL.md § Structure`):

| Shape | Path (premium default) |
|---|---|
| Architecture / hub-spoke / layered / multi-host / linear / ring — any node-edge topology | fd-engine descriptor `type:"architecture"` (or `"hub-spoke"`) |
| Flowchart / decision DAG | fd-engine descriptor `type:"flowchart"` + bun elk step |
| State machine | fd-engine descriptor `type:"state"` + bun elk step |
| Schema — UML class / ER | fd-engine descriptor `type:"class"` / `type:"er"` + bun elk step |
| API sequence | fd-engine descriptor `type:"sequence"` + bun elk step |
| Swimlane / multi-actor pipeline (preferred for lifecycles) | `lane-swim.html` |
| Timeline / gantt | fd-engine descriptor `type:"gantt"` |
| Proportion / share | fd-engine descriptor `type:"pie"` |
| Issue dependency graph (data-driven) | `dep-graph.html` |
| **Propositions** (print / no-JS, else generate bespoke via `type:"architecture"`) | `radial-hub` · `radial-ring` · `linear-flow` · `dual-cluster` · `layered` · `deployment-tiers` · `machine-clusters` |

### Phase Cards (when applicable)

For process flows with distinct phases, use phase cards:

```html
<div class="phases">
  <div class="phase-card p1">
    <div class="phase-num">Phase 1</div>
    <div class="phase-title">{{TITLE}}</div>
    <ul>
      <li>{{ITEM_1}}</li>
      <li>{{ITEM_2}}</li>
    </ul>
  </div>
  <!-- repeat for p2, p3, p4 -->
</div>
```

### fd-engine page shell + bootstrap (canonical pattern)

For fd-engine types (`architecture`, `hub-spoke`, `er`, `sequence`, etc.), the output HTML follows this structure. Full reference: `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/examples/fd-architecture.html`.

**CSS inline order (critical — fd-engine.css must come AFTER the aesthetic):**
```html
<style>
  /* 1. forge base reset */
  /* 2. aesthetic CSS (lyra-v2.css / cool-dark.css / etc.) */
  /* 3. fd-engine.css — must be LAST; its :root block maps short-name tokens
        from the aesthetic's universal tokens. Inlining before the aesthetic
        breaks the cascade direction and leaves --panel etc. undefined. */
  /* 4. fgraph-base.css (Mode A) */
  /* 5. diagram-specific overrides */
</style>
```

**Minimal DOM layout:**
```html
<div class="fd-layout">
  <div class="fd-main">
    <!-- canvas: explicit height required (set via JS from descriptor.canvas.height) -->
    <div class="fd-canvas" id="fd-canvas" style="height:920px">
      <!-- SVG overlay: pixel-space, NO viewBox, NO preserveAspectRatio (AC-10) -->
      <svg class="fd-edges" id="fd-edges"
           style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible"
           aria-hidden="true">
        <defs></defs>
      </svg>
      <!-- .fd-node divs and .fd-zone divs are injected by the bootstrap -->
    </div>
  </div>
  <!-- sidebar (spotlight / use-case panel) — optional -->
  <div class="sidebar" id="fd-sidebar">
    <div id="sbHeader">…</div>
    <div id="sbUc">…</div>
  </div>
</div>
```

**Descriptor JSON embedded inline:**
```html
<script type="application/json" id="fd-data">
{
  "type": "architecture",
  "title": "…",
  "theme": "lyra-v2",
  "layout": "declarative",
  "canvas": { "height": 920 },
  "options": { "particles": false, "spotlight": true, "sidebar": true },
  "nodes": […],
  "edges": […],
  "zones": […],
  "useCases": […]
}
</script>
```

**Bootstrap — SINGLE script block (critical):**

The `buildEngine()` bundle wraps everything in an IIFE. `initEngine`, `renderNodes`, `draw`, `wireResize` are IIFE-scoped only. The bundler injects `window.__fd = { initEngine, renderNodes, draw, wireResize }` so a separate `<script>` can bootstrap:

```html
<script>
/* buildEngine bundle inlined here (IIFE with window.__fd + window.__fdTypes exposed) */
(function(){ 'use strict'
  /* … fd/core.js … fd/edges.js … fd/cards.js … fd/types/architecture.js … */
  /* window.__fdTypes['architecture'] = { CARD_DEFAULT, placeZones, init } */
  window.__fd = { initEngine, renderNodes, draw, wireResize, … }
})()
</script>

<!-- bootstrap: runs after bundle sets window.__fd + window.__fdTypes -->
<script>
;(function(){
  function run() {
    var descriptor = JSON.parse(document.getElementById('fd-data').textContent)
    var canvasEl   = document.getElementById('fd-canvas')
    var svgEl      = document.getElementById('fd-edges')

    // 1. set canvas height (fd-engine.css --fd-canvas-h var or inline style)
    if (descriptor.canvas && descriptor.canvas.height) {
      canvasEl.style.height = descriptor.canvas.height + 'px'
    }

    // 2. init engine core (sets DESCRIPTOR, canvas, svg shared vars)
    window.__fd.initEngine(descriptor, canvasEl, svgEl)

    // 3. dispatch to type module
    var typeReg = window.__fdTypes && window.__fdTypes[descriptor.type]
    var typeDefault = typeReg ? typeReg.CARD_DEFAULT : 'simple'

    // 4. render nodes
    window.__fd.renderNodes(descriptor, typeDefault)

    // 5. draw edges (DOM-measured bezier overlay; init markers)
    if (window.__fd.initMarkers) window.__fd.initMarkers(/* uniquePlanes from descriptor */)
    window.__fd.draw()

    // 6. zone placement (type-specific)
    if (typeReg && typeof typeReg.placeZones === 'function') {
      typeReg.placeZones(descriptor)
    }

    // 7. wire ResizeObserver for responsive redraw
    window.__fd.wireResize()

    // 8. type-specific init (spotlight, use-case UI, etc.)
    if (typeReg && typeof typeReg.init === 'function') {
      typeReg.init(descriptor)
    }
  }

  // delay 80ms: Chrome needs one paint cycle after DOMContentLoaded
  // for getBoundingClientRect to return real pixel rects
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(run, 80) })
  } else {
    setTimeout(run, 80)
  }
})()
</script>
```

> **Note:** `setTimeout(..., 80)` is required — calling `draw()` immediately on `DOMContentLoaded` returns zero-rect nodes because the browser hasn't completed layout. Use 80ms consistently.

### Reveal Animation

Add reveal observer to `{EXTRA_SCRIPTS}` (skip for single quick diagrams with no `.reveal` elements):

```javascript
// Reveal on scroll
const obs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('visible')
      obs.unobserve(e.target)
    }
  })
}, { threshold: 0.15 })
document.querySelectorAll('.reveal').forEach(el => obs.observe(el))
```
