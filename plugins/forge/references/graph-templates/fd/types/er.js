// fd/types/er.js — ER diagram type module (S3b footprint)
// Glob-discovery: bundler.js discovers this file via glob('fd/types/*.js').
// Exports (shared IIFE scope, no ES import/export):
//   elkOptionsForType()    — ELK layout options: layered, DOWN, ORTHOGONAL, wider spacing
//   nodeSizeForType(node)  — fixed width 180px, height = 48 + attributes.length * 20px
//   erInit(descriptor)     — registers 'er' with window.__fdTypes
//
// Card defaults (RD-3): simple-box (auto-layout type).
// Per-node override via node.cardStyle='premium' resolved by cards.js:renderNode().
//
// Node structure: nodes carry node.attributes[] — array of
//   { name, type, pk?, fk? }
//   PK rows:      .fd-er-pk  — key-icon prefix span
//   FK rows:      .fd-er-fk  — link-icon prefix span
//   Regular rows: plain text
//   Entity header (table name): .fd-er-entity-name
//
// Crow's-foot SVG markers (injected into SVG overlay defs):
//   fd-arr-er-one          ||   one, mandatory (two vertical bars)
//   fd-arr-er-many         >|   many, mandatory (crow + one bar)
//   fd-arr-er-zero-or-one  o|   zero or one (circle + one bar)
//   fd-arr-er-zero-or-many o>   zero or many (circle + crow)
//   fd-arr-er-one-or-many  >||  one or many (crow + two bars)
//
// Edge descriptor carries:
//   edge.cardinalityF: 'one'|'many'|'zero-or-one'|'zero-or-many'|'one-or-many'
//   edge.cardinalityT: 'one'|'many'|'zero-or-one'|'zero-or-many'|'one-or-many'
//   marker-start = from-end cardinality  | marker-end = to-end cardinality
//
// ELK layout (gen-time bun step, RD-1):
//   algorithm: layered (Sugiyama), direction: DOWN, nodeSpacing=40, layerSpacing=64
//   edge routing: ORTHOGONAL — wider spacing than flowchart/class to accommodate attribute rows
//   Node positions (x/y in pixels, relative to canvas) injected by scripts/fd-layout.mjs.
//
// AC-4/AC-5: no external file links, no fetch. file:// safe. Single-file output.
// AC-10: SVG overlay uses position:absolute;inset:0 (pixel canvas, AC-10 compliant).
// Guard-safety §10: no diagram-tool lowercase banned token in plugins/forge/ (CI grep).
// biome-ignore: all functions share the concat bundle scope (no ES import/export)

const ER_TYPE = 'er'
// RD-3: auto-layout types default to simple card
const ER_CARD_DEFAULT = 'simple'

// ── ELK layout options ────────────────────────────────────────────────────────
//
// Returns the ELK graph layoutOptions object for ER diagrams.
// Used by scripts/fd-layout.mjs at generation time (RD-1).
//
// Wider spacing than flowchart (nodeSpacing=28) and class (nodeSpacing=32)
// because ER entity nodes carry attribute rows that make them significantly
// taller — more vertical breathing room prevents edge congestion.
//
// Canonical ELK option keys (verbatim property names):
//   'elk.algorithm'                              layered = Sugiyama-style
//   'elk.direction'                              DOWN = top-to-bottom
//   'elk.spacing.nodeNode'                       40px horizontal gap
//   'elk.layered.spacing.nodeNodeBetweenLayers'  64px vertical gap
//   'elk.edgeRouting'                            ORTHOGONAL routing
//   'elk.layered.nodePlacement.strategy'         BALANCED centering
function elkOptionsForType() {
  return {
    'elk.algorithm': 'layered',
    'elk.direction': 'DOWN',
    'elk.spacing.nodeNode': '40',
    'elk.layered.spacing.nodeNodeBetweenLayers': '64',
    'elk.edgeRouting': 'ORTHOGONAL',
    'elk.layered.nodePlacement.strategy': 'BALANCED',
  }
}

// ── Node size estimation ──────────────────────────────────────────────────────
//
// Returns {width, height} for a descriptor node.
// Used by scripts/fd-layout.mjs to populate elkjs graph node dimensions (RD-1).
//
// ER entity sizing:
//   width:  180px fixed (wider than flowchart — accommodates attribute names + types)
//   height: 48px base (entity name header row) + attributes.length × 20px per row
//
// Spec: fixed width 180px, height = 48 + attributes.length * 20px (task detail)
function nodeSizeForType(node) {
  const attrs = node.attributes || []
  return {
    width: 180,
    height: 48 + attrs.length * 20,
  }
}

// ── Crow's-foot marker injection ─────────────────────────────────────────────
//
// Injects 5 SVG <marker> defs into the SVG overlay's <defs> block.
// Called once after the SVG overlay element is created (before draw()).
//
// Marker id → cardinality glyph mapping:
//   fd-arr-er-one          ||   two vertical bars (one, mandatory)
//   fd-arr-er-many         >|   crow-foot + one bar (many, mandatory)
//   fd-arr-er-zero-or-one  o|   circle + one bar (optional singular)
//   fd-arr-er-zero-or-many o>   circle + crow-foot (optional plural)
//   fd-arr-er-one-or-many  >||  crow-foot + two bars (mandatory plural)
//
// SVG path conventions:
//   viewBox: 0 0 18 10 (wider than standard arrows to fit multi-glyph markers)
//   refX: 18 (marker tip at edge endpoint — path endpoint, not node center)
//   refY: 5  (vertical center)
//   markerWidth/Height: 18/10 (1:1 pixel mapping, AC-10 compliance)
//   orient: auto (rotate with edge direction)
//   stroke: var(--border-bright) via .fd-er-mk class (consistent with fgraph fg-er-* convention)
//   fill: none (outline strokes only)
//
// The marker shapes are drawn left-to-right (0→18) so orient=auto flips them
// correctly when used as marker-start (reversed orientation).
function injectErMarkers(svgEl) {
  // Guard: skip if defs already injected (idempotent on redraw)
  if (svgEl.querySelector('#fd-arr-er-one')) return

  let defs = svgEl.querySelector('defs')
  if (!defs) {
    defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs')
    svgEl.insertBefore(defs, svgEl.firstChild)
  }

  // Shared marker attributes
  const MK_W = 18
  const MK_H = 10
  const MK_CY = 5

  // CSS class for stroke styling — mirrors .fgraph-edges .mk-er-stroke convention
  // but scoped to the fd-engine SVG overlay (not .fgraph-edges)
  const CLS = 'fd-er-mk'

  // Helper: create a <marker> element with common attributes
  function mkMarker(id) {
    const m = document.createElementNS('http://www.w3.org/2000/svg', 'marker')
    m.setAttribute('id', id)
    m.setAttribute('viewBox', `0 0 ${MK_W} ${MK_H}`)
    m.setAttribute('refX', String(MK_W))
    m.setAttribute('refY', String(MK_CY))
    m.setAttribute('markerWidth', String(MK_W))
    m.setAttribute('markerHeight', String(MK_H))
    m.setAttribute('orient', 'auto')
    return m
  }

  // Helper: create a <path> with the shared stroke class
  function mkPath(d) {
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path')
    p.setAttribute('d', d)
    p.setAttribute('class', CLS)
    return p
  }

  // ── fd-arr-er-one: || (two vertical bars — one, mandatory) ──
  // Glyph: two parallel vertical bars at x=12 and x=16
  const mkOne = mkMarker('fd-arr-er-one')
  mkOne.appendChild(mkPath('M12,1 L12,9 M16,1 L16,9'))
  defs.appendChild(mkOne)

  // ── fd-arr-er-many: >| (crow-foot + one bar — many, mandatory) ──
  // Glyph: crow-foot fork at left, single bar at right
  //   crow: lines from (2,MK_CY) to (10,1) and (2,MK_CY) to (10,9), center line (2,5)→(10,5)
  //   bar:  vertical line at x=14
  const mkMany = mkMarker('fd-arr-er-many')
  mkMany.appendChild(mkPath('M2,5 L10,1 M2,5 L10,9 M2,5 L10,5 M14,1 L14,9'))
  defs.appendChild(mkMany)

  // ── fd-arr-er-zero-or-one: o| (circle + one bar — zero or one) ──
  // Glyph: small circle at left edge, single bar at right
  //   circle: cx=4, cy=5, r=3 (open circle = optional)
  //   bar:    vertical line at x=14
  const mkZeroOrOne = mkMarker('fd-arr-er-zero-or-one')
  const circZO = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
  circZO.setAttribute('cx', '4')
  circZO.setAttribute('cy', '5')
  circZO.setAttribute('r', '3')
  circZO.setAttribute('class', CLS)
  mkZeroOrOne.appendChild(circZO)
  mkZeroOrOne.appendChild(mkPath('M14,1 L14,9'))
  defs.appendChild(mkZeroOrOne)

  // ── fd-arr-er-zero-or-many: o> (circle + crow-foot — zero or many) ──
  // Glyph: small circle at left, crow-foot fork at right
  //   circle: cx=3, cy=5, r=2.5
  //   crow:   lines from (8,5) to (16,1), (8,5) to (16,9), center (8,5)→(16,5)
  const mkZeroOrMany = mkMarker('fd-arr-er-zero-or-many')
  const circZM = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
  circZM.setAttribute('cx', '3')
  circZM.setAttribute('cy', '5')
  circZM.setAttribute('r', '2.5')
  circZM.setAttribute('class', CLS)
  mkZeroOrMany.appendChild(circZM)
  mkZeroOrMany.appendChild(mkPath('M8,5 L16,1 M8,5 L16,9 M8,5 L16,5'))
  defs.appendChild(mkZeroOrMany)

  // ── fd-arr-er-one-or-many: >|| (crow-foot + two bars — one or many) ──
  // Glyph: crow-foot fork at left, two parallel bars at right
  //   crow: lines from (1,5) to (9,1), (1,5) to (9,9), center (1,5)→(9,5)
  //   bars: x=12 and x=16
  const mkOneOrMany = mkMarker('fd-arr-er-one-or-many')
  mkOneOrMany.appendChild(mkPath('M1,5 L9,1 M1,5 L9,9 M1,5 L9,5 M12,1 L12,9 M16,1 L16,9'))
  defs.appendChild(mkOneOrMany)
}

// ── Cardinality marker id resolver ───────────────────────────────────────────
//
// Maps a cardinality string to the corresponding SVG marker id.
// Returns null for unrecognised or absent values (no marker applied).
//
// Supported cardinality values:
//   'one'          → fd-arr-er-one
//   'many'         → fd-arr-er-many
//   'zero-or-one'  → fd-arr-er-zero-or-one
//   'zero-or-many' → fd-arr-er-zero-or-many
//   'one-or-many'  → fd-arr-er-one-or-many
function erMarkerFor(cardinality) {
  const MAP = {
    one: 'fd-arr-er-one',
    many: 'fd-arr-er-many',
    'zero-or-one': 'fd-arr-er-zero-or-one',
    'zero-or-many': 'fd-arr-er-zero-or-many',
    'one-or-many': 'fd-arr-er-one-or-many',
  }
  return MAP[cardinality] || null
}

// ── ER entity node renderer ───────────────────────────────────────────────────
//
// Renders the attribute-row structure inside each .fd-node element.
// Called after cards.js:renderNodes() has created the base .fd-node div.
//
// Node content layout:
//   .fd-er-entity-name  — entity (table) name header
//   .fd-er-divider      — horizontal rule separating header from attributes
//   .fd-er-attr         — one per attribute row:
//     .fd-er-pk           PK rows: key-icon prefix (★ or key glyph)
//     .fd-er-fk           FK rows: link-icon prefix (⊹ or chain glyph)
//     .fd-er-attr-name    attribute name text
//     .fd-er-attr-type    attribute type text (right-aligned, muted)
//
// Entity name is taken from node.n (the standard name field).
// Attributes come from node.attributes[] = [{ name, type, pk?, fk? }].
//
// The base .fd-node element is already positioned by positionErNodes().
// This function only sets innerHTML — it does not touch position/style.
function renderErEntity(el, node) {
  const attrs = node.attributes || []
  const name = node.n || node.id || '?'

  let html = `<div class="fd-er-entity-name">${name}</div>`
  if (attrs.length > 0) {
    html += '<div class="fd-er-divider"></div>'
    for (const attr of attrs) {
      let prefix = ''
      if (attr.pk) {
        prefix = '<span class="fd-er-pk" title="Primary Key">🔑</span>'
      } else if (attr.fk) {
        prefix = '<span class="fd-er-fk" title="Foreign Key">⊹</span>'
      }
      html += `<div class="fd-er-attr">`
      html += `${prefix}<span class="fd-er-attr-name">${attr.name}</span>`
      html += `<span class="fd-er-attr-type">${attr.type || ''}</span>`
      html += `</div>`
    }
  }

  el.innerHTML = html
}

// ── ER attribute row CSS ──────────────────────────────────────────────────────
//
// Injects ER-specific CSS rules into the document once (idempotent).
// These rules style the entity/attribute layout inside .fd-node for type 'er'.
// Inlined here (not in fd-engine.css) so the type module is self-contained
// and the file:// safety contract is maintained (AC-4/AC-5).
//
// Colors use CSS vars from the aesthetic layer:
//   --fd-plane-data, --text, --text-muted, --border, --border-bright
//
// fd-er-mk: marker stroke class — mirrors .fgraph-edges .mk-er-stroke
//   but scoped to fd-engine SVG overlay (not .fgraph-edges parent).
function injectErCss() {
  const STYLE_ID = 'fd-er-style'
  if (document.getElementById(STYLE_ID)) return

  const style = document.createElement('style')
  style.id = STYLE_ID
  style.textContent = `
/* fd/types/er.js — ER entity node styles */

/* Entity name header */
.fd-er-entity-name {
  font-family: var(--mono, monospace);
  font-size: 11px;
  font-weight: 700;
  color: var(--text, #fafafa);
  text-align: center;
  padding: 4px 8px 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -.1px;
}

/* Divider between header and attribute rows */
.fd-er-divider {
  height: 1px;
  background: var(--border-bright, #30363d);
  margin: 2px 0;
}

/* Attribute row */
.fd-er-attr {
  display: flex;
  align-items: baseline;
  gap: 3px;
  font-family: var(--mono, monospace);
  font-size: 9.5px;
  padding: 1px 8px;
  line-height: 1.5;
  overflow: hidden;
}

/* PK icon (key glyph — gold tint) */
.fd-er-pk {
  color: var(--amber, #f59e0b);
  font-size: 8.5px;
  flex-shrink: 0;
}

/* FK icon (link glyph — muted tint) */
.fd-er-fk {
  color: var(--fd-plane-data, #a78bfa);
  font-size: 8.5px;
  flex-shrink: 0;
}

/* Attribute name — grows to fill available width */
.fd-er-attr-name {
  flex: 1;
  color: var(--text, #fafafa);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Attribute type — right-aligned, muted */
.fd-er-attr-type {
  color: var(--text-muted, #8b93a1);
  white-space: nowrap;
  flex-shrink: 0;
  font-size: 8.5px;
}

/* Crow's-foot marker stroke — inherits from edge color context */
.fd-er-mk {
  stroke: var(--border-bright, #30363d);
  fill: none;
  stroke-width: 1.4;
}

/* fd-node width override for ER type (180px per spec) */
.fd-node.fd-er-node {
  width: 180px;
  padding: 6px 0 5px;
  background: linear-gradient(180deg, var(--bg-panel, #13191f), var(--bg-card, #161b22));
  border: 1px solid var(--border-hi, #30363d);
  border-radius: 8px;
}
`
  document.head.appendChild(style)
}

// ── ER entity shape setup ─────────────────────────────────────────────────────
//
// Applies ER-specific structure to each .fd-node element after renderNodes().
// Sets the fd-er-node marker class and calls renderErEntity() to populate
// the entity header + attribute rows.
function applyErShapes(descriptor) {
  const nodes = descriptor.nodes || []
  for (const node of nodes) {
    const el = nodeEl[node.id]
    if (!el) continue
    // Mark as ER node for CSS targeting
    el.classList.add('fd-er-node')
    // Render entity content (name header + attribute rows)
    renderErEntity(el, node)
  }
}

// ── ER edge post-processing ───────────────────────────────────────────────────
//
// Applies crow's-foot marker-start / marker-end to SVG path elements
// based on edge.cardinalityF (from-end) and edge.cardinalityT (to-end).
// Called after draw() has created the path elements.
//
// The SVG overlay is accessed via the `svg` free variable from core.js.
// Path elements carry data-f / data-t attributes set by edges.js draw().
function applyErEdgeMarkers(descriptor) {
  if (!descriptor?.edges) return
  for (const edge of descriptor.edges) {
    // edges.js uses pairKey for path data-pk attribute
    const pk = [edge.f, edge.t].sort().join('|')
    const pathEl = svg?.querySelector(`path[data-pk="${pk}"]`)
    if (!pathEl) continue

    const startMarkerId = erMarkerFor(edge.cardinalityF)
    const endMarkerId = erMarkerFor(edge.cardinalityT)

    if (startMarkerId) {
      pathEl.setAttribute('marker-start', `url(#${startMarkerId})`)
    }
    if (endMarkerId) {
      pathEl.setAttribute('marker-end', `url(#${endMarkerId})`)
    }
  }
}

// ── Pixel-space node positioning ─────────────────────────────────────────────
//
// For auto-layout types, descriptor.nodes[i].x/y hold pixel coordinates
// injected by the bun elk step at generation time (RD-1).
// Applies them as pixel left/top on each .fd-node element.
// Clears the CSS var --x/--y props set by cards.js (% space → pixel space).
function positionErNodes(descriptor) {
  const nodes = descriptor.nodes || []
  for (const node of nodes) {
    const el = nodeEl[node.id]
    if (!el) continue
    el.style.left = `${node.x || 0}px`
    el.style.top = `${node.y || 0}px`
    el.style.removeProperty('--x')
    el.style.removeProperty('--y')
  }
}

// ── init ──────────────────────────────────────────────────────────────────────
//
// Called by the fd-engine bootstrap after parsing fd-data JSON.
// Returns the type contract consumed by the engine orchestrator:
//   typeDefault     — CARD_DEFAULT ('simple' for auto-layout types)
//   elkOptionsForType — elk layout options function (gen-time bun step reads this)
//   nodeSizeForType — node size estimator (gen-time bun step reads this)
//   positionNodes   — pixel positioning from elk-injected x/y
//   applyShapes     — ER entity renderer + fd-er-node class injection
//   applyEdgeHooks  — crow's-foot marker application (post-draw)
//   placeZones      — null (ER has no zone descriptors)
//
// Bootstrap call order:
//   1. injectErCss()                  — once, inject ER CSS rules
//   2. renderNodes(descriptor, 'simple') — cards.js base card creation
//   3. positionNodes(descriptor)      — pixel positioning
//   4. applyShapes(descriptor)        — ER entity content injection
//   5. injectErMarkers(svg)           — SVG marker defs injection
//   6. draw()                         — edges.js bezier overlay
//   7. applyEdgeMarkers(descriptor)   — crow's-foot marker application
//   8. new ResizeObserver(redraw).observe(canvas)
function erInit(descriptor) {
  const t = descriptor.type
  if (t !== 'er') {
    console.warn('[fd] er.js init() called with unexpected type:', t)
  }

  // Inject ER CSS rules (idempotent)
  injectErCss()

  return {
    typeDefault: ER_CARD_DEFAULT,
    placeZones: null,
    // Post-render hooks called by bootstrap after renderNodes()
    positionNodes: positionErNodes,
    applyShapes: applyErShapes,
    // injectMarkers is called with the SVG element before draw()
    injectMarkers: injectErMarkers,
    // applyEdgeHooks is called after draw() to apply cardinality markers
    applyEdgeHooks: applyErEdgeMarkers,
    // Gen-time elk helpers (read by fd-layout.mjs bun step)
    elkOptions: elkOptionsForType,
    nodeSizer: nodeSizeForType,
  }
}

// ── glob-discovery registration ───────────────────────────────────────────────
// bundler.js discovers fd/types/*.js and concatenates them into the inline
// <script>. At runtime each type module self-registers so the bootstrap
// can dispatch without knowing type names at build time (RD-4).
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[ER_TYPE] = {
  CARD_DEFAULT: ER_CARD_DEFAULT,
  placeZones: null,
  init: erInit,
  elkOptions: elkOptionsForType,
  nodeSizer: nodeSizeForType,
  // Expose marker helpers for introspection / testing
  injectMarkers: injectErMarkers,
  markerFor: erMarkerFor,
}
