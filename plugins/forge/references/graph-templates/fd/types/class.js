// fd/types/class.js — UML class diagram type module (Slice S3a)
// Glob-discovery: bundler.js discovers this file via glob('fd/types/*.js').
// Exports (shared IIFE scope, no ES import/export):
//   elkOptionsForType()   — ELK layout options for layered/DOWN, nodeSpacing=32, layerSpacing=56
//   nodeSizeForType(node) — per-node {width, height}: fixed 160px wide, height=40+(attrs+methods)*18
//   classInit(descriptor) — registers 'class' with window.__fdTypes, returns type contract
//
// Card structure (RD-3): simple-box base with attribute/method rows appended below title.
//   nodes carry node.attributes[] and node.methods[] — rendered as .fd-class-row divs.
//   Interfaces: node.kind='interface' → italic title, dashed border.
//   Abstract classes: node.kind='abstract' → italic title.
//
// Arrow types via edge.arrowType:
//   'inheritance'          solid line  + open triangle head (filled parent end)
//   'realization'          dashed line + open triangle head
//   'implements'           alias for 'realization'
//   'composition'          solid line  + filled diamond tail (at source)
//   'aggregation'          solid line  + open diamond tail (at source)
//   'association'          solid line  + open arrowhead
//   'dependency'           dashed line + open arrowhead
//   (default/undefined)    solid line  + open arrowhead (same as 'association')
//
// SVG markers are injected by initClassMarkers() called from classInit().
// Each marker id: fd-class-{arrowType}. Dash patterns set via CSS class on <path>.
//
// ELK layout (gen-time bun step, RD-1):
//   algorithm: layered (Sugiyama), direction: DOWN
//   nodeSpacing=32, layerSpacing=56, edge routing: ORTHOGONAL
//   Positions (x/y in pixels) injected into descriptor before HTML assembly.
//
// AC-10: no preserveAspectRatio / viewBox on SVG overlay — pixel-space only.
// Guard-safety contract — no diagram-tool token (CI grep covers plugins/forge/**/*).

const CLASS_TYPE = 'class'
// RD-3: auto-layout types default to simple card
const CLASS_CARD_DEFAULT = 'simple'

// Fixed card width for all class nodes (ensures column alignment in UML layout)
const CLASS_NODE_WIDTH = 160
// Base header height + per-row height for attribute/method rows
const CLASS_NODE_BASE_HEIGHT = 40
const CLASS_NODE_ROW_HEIGHT = 18

// ── ELK layout options ─────────────────────────────────────────────────────
//
// Class diagrams: layered layout with more spacing than flowchart (wider cards).
// Spec: nodeSpacing=32, layerSpacing=56, ORTHOGONAL routing.
function elkOptionsForType() {
  return {
    'elk.algorithm': 'layered',
    'elk.direction': 'DOWN',
    'elk.spacing.nodeNode': '32',
    'elk.layered.spacing.nodeNodeBetweenLayers': '56',
    'elk.edgeRouting': 'ORTHOGONAL',
    'elk.layered.nodePlacement.strategy': 'BALANCED',
  }
}

// ── Node size estimation ───────────────────────────────────────────────────
//
// Returns {width, height} for a descriptor node.
// Class nodes: fixed 160px wide.
// Height: 40px base (header) + 18px per attribute + 18px per method.
// This ensures elk allocates enough vertical space to avoid row content overlap.
function nodeSizeForType(node) {
  const attrs = (node.attributes || []).length
  const methods = (node.methods || []).length
  return {
    width: CLASS_NODE_WIDTH,
    height: CLASS_NODE_BASE_HEIGHT + (attrs + methods) * CLASS_NODE_ROW_HEIGHT,
  }
}

// ── Attribute/method row renderer ─────────────────────────────────────────
//
// Builds the HTML string for attribute and method rows inside a class card.
// Attributes are rendered above a divider, methods below.
// Visibility sigils: + public, - private, # protected, ~ package.
function buildClassRows(node) {
  const attrs = node.attributes || []
  const methods = node.methods || []

  let html = ''

  if (attrs.length > 0 || methods.length > 0) {
    html += '<div class="fd-class-divider"></div>'
  }

  for (const attr of attrs) {
    html += `<div class="fd-class-row fd-class-attr">${attr}</div>`
  }

  if (attrs.length > 0 && methods.length > 0) {
    html += '<div class="fd-class-divider"></div>'
  }

  for (const method of methods) {
    html += `<div class="fd-class-row fd-class-method">${method}</div>`
  }

  return html
}

// ── Class-specific node HTML injector ─────────────────────────────────────
//
// Augments rendered .fd-node elements with UML class card structure:
//   - header: stereotype label (interface/abstract), class name
//   - attribute rows and method rows appended below the title bar
//   - interface/abstract kind modifiers applied as CSS classes
//
// Called after cards.js renderNodes() has created the base .fd-node elements.
function applyClassShapes(descriptor) {
  const nodes = descriptor.nodes || []
  for (const node of nodes) {
    const el = nodeEl[node.id]
    if (!el) continue

    const kind = node.kind || ''

    // Apply kind-specific CSS classes for visual differentiation
    if (kind === 'interface') {
      el.classList.add('fd-class-interface')
    } else if (kind === 'abstract') {
      el.classList.add('fd-class-abstract')
    }

    // Build stereotype header + attribute/method rows
    let stereoHtml = ''
    if (kind === 'interface') {
      stereoHtml = '<div class="fd-class-stereo">&laquo;interface&raquo;</div>'
    } else if (kind === 'abstract') {
      stereoHtml = '<div class="fd-class-stereo">&laquo;abstract&raquo;</div>'
    }

    const rowsHtml = buildClassRows(node)

    // Prepend stereotype and append rows to existing card HTML
    if (stereoHtml) {
      el.innerHTML = stereoHtml + el.innerHTML
    }
    el.innerHTML += rowsHtml
  }
}

// ── Pixel-space node positioning ──────────────────────────────────────────
//
// For auto-layout types, descriptor.nodes[i].x/y hold pixel coords
// injected by the bun elk step at generation time (RD-1).
// Overrides the % CSS var positioning set by cards.js.
function positionClassNodes(descriptor) {
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

// ── UML SVG marker injection ───────────────────────────────────────────────
//
// Injects <marker> elements for the 6 UML relationship arrow types.
// Called from classInit() before draw().
//
// Marker id convention: fd-class-{arrowType}
//
// UML arrow shapes:
//   inheritance / realization / implements:
//     open triangle head (hollow, stroke-colored — not filled)
//   composition:
//     filled diamond tail at source node
//   aggregation:
//     open diamond tail at source node (hollow)
//   association / dependency / default:
//     open arrowhead (standard chevron)
//
// Dash patterns are applied by applyClassEdgeStyles() via .fd-class-dashed CSS class.
// AC-10: no preserveAspectRatio or viewBox on SVG overlay.
function initClassMarkers() {
  if (!svg) return
  var defs = svg.querySelector('defs')
  if (!defs) {
    defs = document.createElementNS(NS, 'defs')
    svg.insertBefore(defs, svg.firstChild)
  }

  // Inject per-marker color CSS rules
  var styleEl = document.createElementNS(NS, 'style')
  styleEl.textContent = [
    '#fd-class-inheritance path { fill: var(--bg-card, #161b22); stroke: var(--fd-class-stroke, #8aa0bd); stroke-width: 1.5; }',
    '#fd-class-realization path { fill: var(--bg-card, #161b22); stroke: var(--fd-class-stroke, #8aa0bd); stroke-width: 1.5; }',
    '#fd-class-implements path { fill: var(--bg-card, #161b22); stroke: var(--fd-class-stroke, #8aa0bd); stroke-width: 1.5; }',
    '#fd-class-composition path { fill: var(--fd-class-stroke, #8aa0bd); stroke: none; }',
    '#fd-class-aggregation path { fill: var(--bg-card, #161b22); stroke: var(--fd-class-stroke, #8aa0bd); stroke-width: 1.5; }',
    '#fd-class-association path { fill: var(--fd-class-stroke, #8aa0bd); stroke: none; }',
    '#fd-class-dependency path { fill: var(--fd-class-stroke, #8aa0bd); stroke: none; }',
    '#fd-class-default path { fill: var(--fd-class-stroke, #8aa0bd); stroke: none; }',
  ].join('\n')
  defs.appendChild(styleEl)

  // Marker definitions for each UML arrow type
  var markerDefs = [
    // Inheritance: open hollow triangle at arrow head (target end)
    {
      id: 'fd-class-inheritance',
      w: 12,
      h: 12,
      rx: 10,
      ry: 6,
      d: 'M0,0 L10,5 L0,10 Z',
    },
    // Realization: same open triangle (dashed line applied in CSS)
    {
      id: 'fd-class-realization',
      w: 12,
      h: 12,
      rx: 10,
      ry: 6,
      d: 'M0,0 L10,5 L0,10 Z',
    },
    // Implements: alias of realization
    {
      id: 'fd-class-implements',
      w: 12,
      h: 12,
      rx: 10,
      ry: 6,
      d: 'M0,0 L10,5 L0,10 Z',
    },
    // Composition: filled diamond at source (marker-start)
    {
      id: 'fd-class-composition',
      w: 14,
      h: 10,
      rx: 12,
      ry: 5,
      d: 'M0,5 L6,0 L12,5 L6,10 Z',
    },
    // Aggregation: open diamond at source (marker-start)
    {
      id: 'fd-class-aggregation',
      w: 14,
      h: 10,
      rx: 12,
      ry: 5,
      d: 'M0,5 L6,0 L12,5 L6,10 Z',
    },
    // Association: standard open arrowhead at target (marker-end)
    {
      id: 'fd-class-association',
      w: 9,
      h: 9,
      rx: 7,
      ry: 4,
      d: 'M0,0 L7,3 L0,6',
    },
    // Dependency: same open arrowhead (dashed line applied in CSS)
    {
      id: 'fd-class-dependency',
      w: 9,
      h: 9,
      rx: 7,
      ry: 4,
      d: 'M0,0 L7,3 L0,6',
    },
    // Default fallback: open arrowhead
    {
      id: 'fd-class-default',
      w: 9,
      h: 9,
      rx: 7,
      ry: 4,
      d: 'M0,0 L7,3 L0,6',
    },
  ]

  var def, marker, path, i
  for (i = 0; i < markerDefs.length; i++) {
    def = markerDefs[i]
    if (svg.querySelector(`#${def.id}`)) continue

    marker = document.createElementNS(NS, 'marker')
    marker.setAttribute('id', def.id)
    marker.setAttribute('markerWidth', String(def.w))
    marker.setAttribute('markerHeight', String(def.h))
    marker.setAttribute('refX', String(def.rx))
    marker.setAttribute('refY', String(def.ry))
    marker.setAttribute('orient', 'auto')
    // AC-10: no preserveAspectRatio on any SVG element

    path = document.createElementNS(NS, 'path')
    path.setAttribute('d', def.d)
    marker.appendChild(path)
    defs.appendChild(marker)
  }
}

// ── Edge style post-processing ────────────────────────────────────────────
//
// Applies UML-specific arrow markers and dash patterns after draw().
//
// Per-edge edge.arrowType mapping:
//   'inheritance'  → marker-end: fd-class-inheritance (solid line)
//   'realization'  → marker-end: fd-class-realization (dashed line)
//   'implements'   → marker-end: fd-class-implements  (dashed line, alias)
//   'composition'  → marker-start: fd-class-composition (solid line, filled diamond tail)
//   'aggregation'  → marker-start: fd-class-aggregation (solid line, open diamond tail)
//   'association'  → marker-end: fd-class-association (solid line)
//   'dependency'   → marker-end: fd-class-dependency  (dashed line)
//   default        → marker-end: fd-class-default     (solid line)
//
// Directional key uses "f>t" pattern (same as edges.js directed dedup).
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — called by bootstrap after draw() */
function applyClassEdgeStyles() {
  if (!DESCRIPTOR?.edges) return
  var arrowType, dirKey, pathEl, i
  var edges = DESCRIPTOR.edges
  for (i = 0; i < edges.length; i++) {
    arrowType = edges[i].arrowType || 'default'
    // Look up path by directed key (consistent with edges.js directed dedup)
    dirKey = `${edges[i].f}>${edges[i].t}`
    pathEl = svg.querySelector(`path[data-pk="${dirKey}"]`)
    if (!pathEl) continue

    // Apply dashed stroke for relationship types that use dashed lines
    if (arrowType === 'realization' || arrowType === 'implements' || arrowType === 'dependency') {
      pathEl.classList.add('fd-class-dashed')
    }

    // Apply marker-end and marker-start per arrowType
    if (arrowType === 'composition' || arrowType === 'aggregation') {
      // Diamond tail goes at the source (composite/aggregate end)
      pathEl.setAttribute('marker-start', `url(#fd-class-${arrowType})`)
      // Remove default marker-end if present (these use source markers only)
      pathEl.removeAttribute('marker-end')
    } else {
      // All other types: arrowhead at target end
      pathEl.setAttribute('marker-end', `url(#fd-class-${arrowType})`)
    }
  }
}

// ── init ──────────────────────────────────────────────────────────────────
//
// Called by the fd-engine bootstrap after parsing fd-data JSON.
// Returns the type contract consumed by the engine orchestrator.
//
// Bootstrap call order:
//   1. renderNodes(descriptor, typeDefault)  — cards.js simple cards
//   2. positionNodes(descriptor)             — elk pixel-space positions
//   3. applyShapes(descriptor)               — class rows + interface/abstract styling
//   4. draw()                                — edges.js bezier overlay
//   5. applyClassEdgeStyles()                — UML marker + dash assignment
//   6. new ResizeObserver(redraw).observe(canvas)
function classInit(descriptor) {
  const t = descriptor.type
  if (t !== CLASS_TYPE) {
    console.warn('[fd] class.js init() called with unexpected type:', t)
  }

  // Inject UML SVG markers into the SVG overlay defs
  initClassMarkers()

  return {
    typeDefault: CLASS_CARD_DEFAULT,
    placeZones: null,
    positionNodes: positionClassNodes,
    applyShapes: applyClassShapes,
    elkOptions: elkOptionsForType,
    nodeSizer: nodeSizeForType,
  }
}

// ── glob-discovery registration ───────────────────────────────────────────
// bundler.js discovers fd/types/*.js and concatenates them into the inline
// <script>. At runtime each type module self-registers here.
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[CLASS_TYPE] = {
  CARD_DEFAULT: CLASS_CARD_DEFAULT,
  placeZones: null,
  init: classInit,
  elkOptions: elkOptionsForType,
  nodeSizer: nodeSizeForType,
}
