# Composition Contract — Presentation × Diagram Layers

> Canonical rules for combining **forge presentations** (scroll narrative) with **craft diagrams** (premium hub-spoke / swimlane canvases). Prevents the #1 integration failure: copying diagram CSS into the presentation shell.

**Applies to:** `forge-presentation`, `forge-guide` (when embedding dense diagrams), any `visuals/{name}.html` that references `visuals/diagrams/*.html`.

**Load with:** `references/base/composition.css` (inline 5th, after `explainer-base.css`).

---

## Level 0 — Intent (what are we building?)

| Artifact | Role | Must never |
|----------|------|------------|
| **Presentation** (`visuals/{name}.html`) | Narration, sections, tables, reveal scroll | Contain craft canvas CSS (absolute spokes, fixed 900×600 layout, IBM Plex diagram rules) |
| **Diagram SSoT** (`visuals/diagrams/{slug}.html`) | Self-contained craft canvas, title inside document | Know forge nav, chapter-cards, section numbering |
| **Shared tokens** (optional) | Semantic names: `--bg`, `--accent`, layer colors | Duplicate typography stacks or canvas geometry |

**Decision in one sentence:** fixed canvas + absolute geometry → diagram file; scroll prose + tables → presentation file.

---

## Level 1 — Block taxonomy (fixed capabilities)

Each block type has **bounded capabilities**. Do not mix stacks.

| Block | Capability | Contains | Reveal |
|-------|------------|----------|--------|
| `panel-wrap` | Tabular + forge swimlanes | `panel-head` + `tbl-wrap` / `.swimlanes` | Once on parent; stagger children |
| `arch-wrap` | Light native flows | `arch-pipeline`, `arch-node`, `forbidden-band` | Once on parent |
| `arch-wrap--flow` | Narrative swimlane (text nodes) | `arch-title` + `.swimlanes` | Once on parent |
| `diagram-embed` | Bridge to diagram SSoT | `<iframe class="diagram-frame">` | **Never** on child if parent already has `.reveal` |
| `diagram-frame` | Iframe viewport | `src`, `data-height`, optional `?embed=hero` | Height via `data-height` or `postMessage` |

### One title per layer

If the diagram HTML has an `h1` / `.title-block` → **no** external `arch-title`, `section-title` duplicate, or `figcaption` on the embed.

---

## Level 2 — Integration contracts

### Contract A — Diagram iframe (craft)

**Consumer (presentation):**

```html
<section id="layers">
  <div class="arch-wrap reveal">
    <figure class="diagram-embed" data-diagram="saas-ticketing-hub.html">
      <iframe
        class="diagram-frame"
        src="diagrams/saas-ticketing-hub.html"
        title="Ticketing · Dual-Layer"
        loading="lazy"
        scrolling="no"
        data-height="760"
      ></iframe>
    </figure>
  </div>
</section>
```

| Parameter | Value | Why |
|-----------|-------|-----|
| iframe `border` | `none` in section CSS (`#layers .diagram-frame { … }`) | Avoid grey double-frame |
| iframe `background` | `transparent` + `color-scheme: only dark` on parent | Prevents white flash (transparent alone ≠ parent bleed) |
| `data-height` | canvas height + padding (measure once) | Prevents vertical clip |
| `?embed=hero` | responsive scale + reduced padding | Narrow hero column |
| `.reveal` | wrapper only | Avoid double `opacity: 0` fade |

**Producer (diagram SSoT):**

- Title + subtitle inside the diagram document
- `html` + `body` both `background: transparent` when embed mode (class in `<head>` before paint)
- Brand icons: inline SVG from `diagrams/brand-icons.svg` — **no external sprite refs** (`file://` breaks `<use href="…">`)
- Official logos for third-party marks (Simple Icons) — never invented paths for GitHub/Vercel/Postgres/etc.
- Optional `postMessage` resize: `{ type: 'forge-diagram-resize', id: '…', height: N }`

**Forbidden:** `.craft-embed`, namespaced copy-paste of diagram CSS into presentation `<style>`.

### Contract B — Panel (data sections)

```html
<div class="panel-wrap reveal">
  <div class="panel-block">
    <div class="panel-head">Matrice visibilité · 5 acteurs × 5 surfaces</div>
    <div class="tbl-wrap">…</div>
  </div>
  <div class="panel-block">
    <div class="panel-head">Flux typiques · swimlane</div>
    <div class="swimlanes">…</div>
  </div>
</div>
```

- Accent top border, no nested box borders on `tbl-wrap` / `.swimlanes`
- `panel-head`: JetBrains Mono, uppercase, accent color
- Stagger: block 1 → block 2 on `.reveal.visible`

### Contract C — Native arch (no canvas)

- Horizontal steps: `arch-pipeline` (not `arch-row` with inline arrows)
- Multi-actor text swimlane: `arch-wrap--flow`
- Dense hub-spoke with SVG paths → **promote to diagram SSoT** (Contract A)

---

## Level 3 — Shared tokens (what to share)

**Share (semantic only):** `--bg`, `--accent`, `--border`, `--layer-business`, `--layer-tech`, `--layer-client`, `--layer-internal`

**Do not share:** presentation font stack (Outfit/Inter) into diagrams; diagram IBM Plex stack into presentation; reveal animation rules into diagrams.

---

## Level 4 — Embed modes

| Context | Mode | Parent CSS | Diagram CSS |
|---------|------|------------|-------------|
| Hero right column | `?embed=hero` | `.hero-right .diagram-frame { border:none; background:transparent }` | scale + tight padding |
| Full-width section | standard | `#{section} .diagram-frame { border:none }` | `--bg` or transparent |
| Table / swimlane data | `panel-wrap` | `composition.css` | N/A |
| Simple pipeline (<7 nodes, no geometry) | `arch-wrap` | `composition.css` | N/A |

---

## Level 5 — Tooling

```bash
# Craft diagram QA (geometry, anchors, icons, hardcoded paths)
python3 ~/.roxabi/forge/scripts/check-craft-diagram.py \
  --dir ~/.roxabi/forge/{PROJ}/visuals/diagrams --check

# Presentation embed contract (no inline craft CSS, iframes registered)
python3 ~/.roxabi/forge/scripts/check-composition.py \
  --presentation ~/.roxabi/forge/{PROJ}/visuals/{name}.html --check

# fd-engine vs hand-authored audit
python3 ~/.roxabi/forge/scripts/audit-forge-diagrams.py
```

**Before shipping a presentation with diagrams:**

1. Author with `craft-anchors.js` + `#craft-edges` JSON (not hand-coded `d=` paths)
2. `check-craft-diagram.py --check` on each `diagrams/*.html`
3. Open each diagram standalone under `file://` (`craft-qa-checklist.md`)
4. `check-composition.py --check` on presentation
5. Playwright smoke capture (optional)

---

## Level 6 — Workflow (add content without one-by-one fixes)

### New craft diagram

1. Copy `references/diagrams/craft-diagram-starter.html` → `visuals/diagrams/{slug}.html`
2. Add `data-anchor` on nodes; position with CSS only
3. Edit `#craft-edges` JSON — **do not** hand-edit SVG `d=` attributes
4. Inline official brand icons; set `data-canvas-width/height`
5. `check-craft-diagram.py --check` + standalone `file://` review
6. Add iframe to presentation + `#xxx .diagram-frame` rules
7. `check-composition.py --check`

### New data section (table / swimlane)

1. Use `panel-wrap` + `panel-head` — never bare `tbl-wrap reveal` alone
2. Related blocks (matrix + flows) → two `panel-block` in one `panel-wrap`
3. No `.reveal` on children

### Promotion signal

When you edit absolute positions, SVG paths, or spoke coordinates inside the presentation → **stop** and move to `visuals/diagrams/`.

---

## Level 7 — Decision matrix

```
Content to add?
│
├─ Fixed canvas, spokes, SVG paths, craft legend
│  └─► visuals/diagrams/{slug}.html + iframe (Contract A)
│
├─ Table or forge swimlane
│  └─► panel-wrap (Contract B)
│
├─ Simple pipeline (<7 steps, no geometry)
│  └─► arch-wrap + arch-pipeline (Contract C)
│
└─ Multi-actor narrative swimlane (text only)
   └─► arch-wrap--flow
```

### When to use fd-engine (`forge-chart`) vs hand-authored craft HTML

| Need | Path |
|------|------|
| ≤8 nodes, descriptor-driven, validate-fd exit 0 | `forge-chart` → fd-engine single file; embed via iframe if inside presentation |
| Hub-spoke craft, dense labels, custom paths, premium quality bar | Hand-authored `diagrams/{slug}.html` from `craft-diagram-starter.html` |
| Quick inline in presentation, no iframe | `arch-pipeline` or static fgraph ≤6 nodes only |

---

## Anti-patterns (hard fail)

| Anti-pattern | Why it fails |
|--------------|--------------|
| Inline `.craft-embed` CSS in presentation | Cascade collision; clipping; double titles |
| `.reveal` on both `arch-wrap` and `diagram-embed` | Diagram invisible until scroll |
| `figcaption` + diagram internal title | Duplicate headings |
| `iframe background: transparent` without `html,body` transparent in diagram | White flash |
| External SVG sprite refs in diagrams | Broken under `file://` |
| Invented brand icons | Wrong marks; breaks trust |

See also: `anti-patterns.md` § Composition.

---

## File layout (canonical)

```
~/.roxabi/forge/{PROJ}/visuals/
├── {name}.html              # presentation (single file, CSS inlined)
├── diagrams/
│   ├── brand-icons.svg      # SSoT official marks (inlined into each diagram)
│   ├── {slug}.html          # craft diagram SSoT
│   └── …
└── scripts/
    └── check-composition.py # optional project override; default in ~/.roxabi/forge/scripts/
```

---

## See also

- `references/base/composition.css` — panel-wrap, arch-wrap, diagram-embed primitives
- `references/diagrams/README.md` — diagram authoring
- `references/diagrams/craft-diagram-starter.html` — starter template
- `references/diagrams/craft-anchors.js` — path engine (inline per diagram)
- `references/diagrams/craft-qa-checklist.md` — pre-embed visual gate
- `skills/forge-presentation/SKILL.md` — section type `craft-diagram`
- `skills/forge-chart/SKILL.md` — fd-engine vs craft decision