# Competitor Skills Analysis — Diagram/Visual Generators

**Date:** 2026-04-12
**Author:** Mickael + Claude
**Status:** Analysis complete → 3 issues opened

## Scope

Comparative analysis of three competing Claude Code skills that generate visual artifacts, benchmarked against our `roxabi-forge` plugin.

## Sources

| Repo | URL | Primary format |
|------|-----|----------------|
| **architecture-diagram-generator** | https://github.com/Cocoon-AI/architecture-diagram-generator | HTML + inline SVG |
| **fireworks-tech-graph** | https://github.com/yizhiyanhua-ai/fireworks-tech-graph | SVG + PNG |
| **visual-explainer** | https://github.com/nicobailon/visual-explainer | HTML (Mermaid, Chart.js) |
| **roxabi-forge** (ours) | `~/projects/roxabi-forge/` | HTML + fgraph SVG + Mermaid |

### Key files examined

**architecture-diagram-generator** (~300 lines total, minimal)
- `SKILL.md` (164 lines) — full design spec
- `assets/template.html` (320 lines) — single HTML scaffold
- `examples/{web-app,aws-serverless,microservices}.html` — sample outputs

**fireworks-tech-graph** (~2,500 lines)
- `SKILL.md` (427 lines) — workflow + diagram types + shape vocab
- `scripts/generate-from-template.py` (1,557 lines) — SVG generator
- `scripts/generate-diagram.sh` — orchestration wrapper
- `scripts/validate-svg.sh` — syntax validation
- `templates/*.svg` (10 files) — reference stubs
- `references/style-{1..7}-*.md` (7 style guides)
- `fixtures/*.json` (7 pre-built examples)
- `agents/openai.yaml` — skill trigger definition

**visual-explainer** (~5,500 lines)
- `SKILL.md` (475 lines) — workflow + anti-slop rules
- `commands/*.md` (8 commands: generate-web-diagram, generate-visual-plan, diff-review, plan-review, project-recap, fact-check, generate-slides, share)
- `references/css-patterns.md` (1,813 lines)
- `references/libraries.md` (612 lines — Mermaid, Chart.js, anime.js)
- `references/slide-patterns.md` (1,406 lines)
- `references/responsive-nav.md` (212 lines)
- `templates/{mermaid-flowchart,data-table,architecture,slide-deck}.html`
- `scripts/share.sh` — Vercel deployment

**roxabi-forge** (~8,000 lines)
- `plugins/forge/skills/{forge-init,forge-guide,forge-epic,forge-chart,forge-gallery}/SKILL.md`
- `plugins/forge/references/` — 22 docs (tokens, frame-phase, design-phase-two-track, output-ux, mermaid-guide, brand-book-schema, etc.)
- `plugins/forge/references/aesthetics/{lyra,roxabi,blueprint,editorial,terminal,caveman}.css`
- `plugins/forge/references/base/{reset,layout,typography,components,explainer-base}.css`
- `plugins/forge/references/gallery-templates/{pivot,simple,comparison,audio,multi-mode}-gallery.html` + `gallery-base.{css,js}`
- `plugins/forge/references/graph-templates/{radial-hub,linear-flow,radial-ring,layered,dual-cluster,machine-clusters,deployment-tiers}.html` + `fgraph-base.css`
- `plugins/forge/references/shells/{single,split}.html`

---

## 1. Pipeline — Input → Output

| Axis | Forge (ours) | Arch Diagram Gen | Fireworks | Visual Explainer |
|------|--------------|-----------------|-----------|-----------------|
| Phases | 4 explicit: Context → Decision → Generation → Deliver | 1 implicit: read SKILL.md → generate | 2 explicit: Claude→JSON, Python→SVG | 4 explicit: Gather → Verify → Design → Generate |
| Planning step | Frame (silent inference: reader, action, takeaway, tone) | None | None | Ultrathinking + fact sheet |
| Intermediate repr. | None (direct HTML) | None | **JSON fixture** → Python renders | None |
| Deterministic step | Shell substitution | None | **Python generator** (1557 lines) | None |
| Sub-agent delegation | Yes (>300 lines) | No | No | No |

**Key insight:** Fireworks is the only one with a **compiled intermediate representation** (JSON→SVG). Deterministic rendering, but less flexibility. Forge and Visual Explainer rely on Claude producing correct HTML directly, compensating with verification gates (Frame / fact sheet).

---

## 2. Document Construction

| Axis | Forge | Arch Diagram Gen | Fireworks | Visual Explainer |
|------|-------|-----------------|-----------|-----------------|
| Output format | HTML (single or split) | Single HTML + inline SVG | SVG + PNG | Single HTML |
| Hierarchy | **3-layer UX**: Glance → Scan → Deep | Header → Diagram → Cards → Footer | Title → Containers → Nodes → Legend | **Depth tiers**: Hero → Elevated → Flat → Recessed |
| Multi-section | Tab system (tab-loader.js) | None | None | Sticky TOC + IntersectionObserver |
| Progressive disclosure | `<details class="disclosure">` | None | None | `<details>` + collapsibles |
| Content scope | Guides, epics, galleries, charts | Architecture diagrams only | 14 diagram types | Diagrams, plans, reviews, recaps, slides |

---

## 3. Template System

| Axis | Forge | Arch Diagram Gen | Fireworks | Visual Explainer |
|------|-------|-----------------|-----------|-----------------|
| Template count | 10 gallery+graph + 2 shells + 6 aesthetics | 1 HTML scaffold | 10 SVG stubs + 7 fixtures | 4 HTML references |
| Template role | **Lifted directly** — copy + fill placeholders | Flexible scaffold | Documentation only (Python generates from scratch) | Read-before-generate |
| Selection logic | Decision tree (reader-action + topology) | None (one template) | Style index 1–7 | Content-type table |
| Shared primitives | `gallery-base.{css,js}` (745 lines) + `fgraph-base.css` (466 lines) | None | `STYLE_PROFILES` dict (50+ tokens × 7 styles) | None |

---

## 4. Styling System

| Axis | Forge | Arch Diagram Gen | Fireworks | Visual Explainer |
|------|-------|-----------------|-----------|-----------------|
| Token contract | 8 core + 15 palette + 8 semantic = 31 | 7 component-type colors | 50+ × 7 styles = 350+ | ~15 per theme |
| Theme switching | 6 aesthetic files | None (dark only) | 7 styles | Varied per generation |
| Dark/light | Dark-first | Dark only | Per-style | **Both** (`prefers-color-scheme`) |
| Typography | IBM Plex (fixed) | JetBrains Mono (fixed) | Per-style | Varied (5+ curated pairings) |
| Anti-patterns | Scattered | None | None | **67-line anti-slop list** |
| Brand enforcement | **`forge.yml` + `deliver_must_match`** | None | None | None |

---

## 5. Rendering Engines

| Engine | Forge | Arch Diagram Gen | Fireworks | Visual Explainer |
|--------|-------|-----------------|-----------|-----------------|
| Pure HTML/CSS | Primary | Wrapper only | None | Primary |
| Inline SVG | fgraph (5 templates) | **Primary** (hand-drawn) | **Primary** (Python-generated) | Minimal |
| Mermaid | Yes (>8 nodes) | None | None | **Primary** (flowchart, sequence, ER, state, mind map) |
| Chart.js | None | None | None | Dashboards |
| Custom JS | gallery-base.js (filters, lightbox) | None | None | Zoom, TOC, anime.js |
| PNG export | None | None | **`rsvg-convert`** | None |
| Slides | None | None | None | **scroll-snap deck** |

---

## 6. Reference Material Volume

| Metric | Forge | Arch Diagram Gen | Fireworks | Visual Explainer |
|--------|-------|-----------------|-----------|-----------------|
| SKILL.md lines | ~1,000 (5 skills) | 164 | 427 | 475 |
| Reference docs | 22 files, ~2,000 lines | 0 | 8 + 7 fixtures | 4 files, 4,043 lines |
| CSS/JS base | ~5,000 lines | ~130 inline | ~350 (Python-encoded) | ~200/template |
| Working examples | 10 templates (~130KB) | 3 outputs | 7 JSON fixtures | 4 templates |
| **Total guidance** | **~8,000+** | **~300** | **~2,500** | **~5,500** |

---

## 7. Unique Strengths per Repo

### Arch Diagram Gen
- **Simplicity** — 300 lines total, zero moving parts
- Proof that minimal SKILL.md + one template produces good diagrams

### Fireworks Tech Graph
- **Deterministic rendering pipeline** (JSON→Python→SVG→PNG)
- Collision-avoidant orthogonal arrow routing
- 7 polished style presets switchable by index
- **PNG export** via `rsvg-convert`
- **Arrow semantic system** (6 flow types: control/write/read/data/async/feedback)

### Visual Explainer
- **Fact-sheet verification** before generation (anti-hallucination)
- Ultrathinking instruction
- **67-line anti-slop checklist**
- **Slide deck engine** (scroll-snap)
- Vercel share script (zero-auth)
- `prefers-color-scheme` dual-theme in every output
- IntersectionObserver TOC tracking

## 8. What Forge Does That None of Them Do

- **Brand book system** (`forge.yml` + `deliver_must_match`) — compile-time brand enforcement
- **Two-track execution** (branded vs exploration)
- **Gallery engine** (5 specialized templates with shared JS)
- **Sub-agent delegation** (auto for >300 lines)
- **Multi-tab split files** (shell + tabs + shared CSS/JS)
- **3-layer UX enforcement** (Glance/Scan/Deep validated at Deliver)
- **Aesthetic library** (6 swappable CSS files, formal token contract)
- **fgraph coordinate system** (0–100 space with CSS vars + matching SVG viewBox)

---

## 9. Action Points

### Tier 1 — High value, low effort (→ Issue #3)

1. **Anti-slop reference doc** (`references/anti-patterns.md`) — consolidate scattered restrictions. [Visual Explainer]
2. **Arrow semantic vocabulary for fgraph** — `.fg-edge.{control,write,read,data,async,feedback}`. [Fireworks]
3. **Deliver-phase fact-sheet** — enumerate factual claims before write. [Visual Explainer]
4. **Light-mode token overrides** in 6 aesthetics — `@media (prefers-color-scheme: light)`. [Visual Explainer]

### Tier 2 — Medium effort, strategic

5. **`forge-slides` skill** (scroll-snap deck) — new artifact class. [Visual Explainer] (→ Issue #4)
6. PNG export for charts (`rsvg-convert` or Puppeteer). [Fireworks] *(not scheduled)*
7. Per-artifact share script (Vercel/CF preview). [Visual Explainer] *(not scheduled)*

### Tier 3 — Research before commit (→ Issue #5)

8. **Auto-layout mode for fgraph** (collision-avoidant routing). [Fireworks] — Python router is 200+ lines; Mermaid covers >8 nodes.
9. **JSON intermediate representation** — decouples LLM from SVG but adds build step + schema. Current recommendation: **don't do this.**

---

## 10. Gap → Source Mapping

| Gap | Source | File reference |
|-----|--------|----------------|
| Fact-sheet verification | Visual Explainer | `commands/diff-review.md:66`, `commands/plan-review.md:84` |
| Anti-slop checklist | Visual Explainer | `SKILL.md:407-474` |
| PNG export | Fireworks | `scripts/generate-diagram.sh`, `rsvg-convert` pipeline |
| Collision-avoidant routing | Fireworks | `scripts/generate-from-template.py:837-906` (`build_orthogonal_route`) |
| Slide deck | Visual Explainer | `templates/slide-deck.html`, `references/slide-patterns.md` (1,406 lines) |
| Dual light/dark theme | Visual Explainer | `@media (prefers-color-scheme)` in every template |
| Arrow flow semantics | Fireworks | `generate-from-template.py:FLOW_ALIASES` + `MARKER_IDS` |
| Zero-auth sharing | Visual Explainer | `scripts/share.sh` (83 lines, Vercel) |
