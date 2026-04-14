# Phase 3 — Generate (forge-chart)

> **Self-check:** if you are reading this file, the `Read ${CLAUDE_PLUGIN_ROOT}/skills/forge-chart/references/phase-3-generate.md` directive from `SKILL.md:Phase 3` resolved. If you are building a `forge-chart` output and have not seen this header, abort and report the unresolved path — Phase 3 body is mandatory for correct generation.

Read `shells/single.html` → substitute placeholders with content. The shell already contains:
- `{THEME_TOGGLE_JS}` placeholder (inline theme-toggle.js with `{NAME}` substituted)
- Diagram meta placeholders
- CSS placeholder slots

### Hero Section

Every chart SHOULD have a hero section. Use the **left border variant** by default. Exception: single quick diagrams (one Mermaid / fgraph block, no narrative) — a minimal title + diagram is acceptable without a hero.

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

### Diagram Shell (REQUIRED for Mermaid)

**NEVER use bare `<pre class="mermaid">`.** Always wrap in the diagram shell:

```html
<div class="diagram-shell">
  <div class="zoom-controls">
    <button data-zoom="in" title="Zoom in">+</button>
    <button data-zoom="fit" title="Fit">⤢</button>
    <button data-zoom="out" title="Zoom out">−</button>
  </div>
  <div class="mermaid-container" data-mermaid-out id="diagram-{{ID}}"></div>
  <script type="text/plain" data-mermaid>
    {{MERMAID_SOURCE}}
  </script>
</div>
```

### Mermaid Initialization

Add to `{HEAD_EXTRAS}`:

```html
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs'
  mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    themeVariables: {
      primaryColor: 'var(--surface)',
      primaryTextColor: 'var(--text)',
      primaryBorderColor: 'var(--accent)',
      lineColor: 'var(--text-dim)',
      secondaryColor: 'var(--border)',
      background: 'var(--bg)',
      edgeLabelBackground: 'var(--surface)',
      nodeTextColor: 'var(--text-muted)',
    },
    flowchart: { useMaxWidth: false, curve: 'basis' }
  })
</script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.2/dist/svg-pan-zoom.min.js"></script>
```

Add to `{EXTRA_SCRIPTS}` (after Mermaid render):

```javascript
// Mermaid render + pan/zoom init
(async function() {
  const container = document.getElementById('diagram-{{ID}}')
  const sourceEl = container?.previousElementSibling
  if (!container || !sourceEl) return
  const { svg } = await mermaid.render('mermaid-svg-{{ID}}', sourceEl.textContent)
  container.innerHTML = svg
  const svgEl = container.querySelector('svg')
  if (svgEl) {
    svgEl.setAttribute('height', '100%')
    svgEl.setAttribute('width', '100%')
    svgEl.style.maxWidth = 'none'
    if (window.svgPanZoom) {
      const pz = svgPanZoom(svgEl, {
        zoomEnabled: true, panEnabled: true,
        controlIconsEnabled: false,
        fit: true, center: true,
        minZoom: 0.15, maxZoom: 15
      })
      document.querySelector('[data-zoom="in"]')?.addEventListener('click', () => pz.zoomIn())
      document.querySelector('[data-zoom="out"]')?.addEventListener('click', () => pz.zoomOut())
      document.querySelector('[data-zoom="fit"]')?.addEventListener('click', () => { pz.resetZoom(); pz.resetPan(); pz.fit(); pz.center() })
    }
  }
})()
```

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
