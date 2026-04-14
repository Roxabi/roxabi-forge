# Phase 3 — Generate (forge-guide)

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

