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

Template picker — see `${CLAUDE_PLUGIN_ROOT}/references/graph-templates/README.md`:

| Shape | Template |
|---|---|
| Hub-and-spoke (≤ 6 peers) | `radial-hub.html` |
| Peer ring | `radial-ring.html` |
| Linear pipeline | `linear-flow.html` |
| Two peers sharing resources | `dual-cluster.html` |
| Layered architecture (3–4 tiers) | `layered.html` / `deployment-tiers.html` |
| Multi-host deployment | `machine-clusters.html` |
| Timeline / gantt | `gantt.html` |
| Proportion / share | `pie.html` |
| ER schema | `er.html` |
| API sequence | `sequence.html` |
| State machine | `state.html` |
| Issue dependency graph | `dep-graph.html` |

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
