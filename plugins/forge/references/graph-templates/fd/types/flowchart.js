// fd/types/flowchart.js — flowchart type module (S2 footprint)
// Glob-discovery: bundler.js discovers this file via glob('fd/types/*.js').
// Exports (shared IIFE scope, no ES import/export):
//   elkOptionsForType()    — ELK layout options for layered/sugiyama, DOWN, ORTHOGONAL routing
//   nodeSizeForType(node)  — per-node {width, height} estimates for gen-time bun elk step
//   flowchartInit()        — registers 'flowchart' with window.__fdTypes
//
// Card defaults (RD-3): simple-box (auto-layout type — flowchart has many small nodes).
// Per-node override via node.cardStyle='premium' is resolved by cards.js:renderNode().
//
// Node shape classes (applied by applyFlowchartShapes after renderNodes):
//   decision nodes (kind='decision' | kind='gate' | shape='diamond') → fd-shape-diamond
//   terminal nodes (kind='terminal' | kind='start' | kind='end') → fd-shape-pill
//   default → standard rect (no extra shape class)
//
// ELK layout (gen-time bun step, RD-1):
//   algorithm: layered (Sugiyama), direction: DOWN, nodeSpacing=28, layerSpacing=48
//   edge routing: ORTHOGONAL, node placement: BALANCED
//   Positions (x/y in pixels, relative to canvas top-left) are injected into the
//   descriptor JSON before HTML assembly. The browser receives pre-positioned nodes.
//
// Guard-safety contract §10 — no diagram-tool token in plugins/forge/ (CI grep).
// All functions are injected into the concat bundle scope (no ES import/export).

const FLOWCHART_TYPE = 'flowchart'
// RD-3: auto-layout types default to simple card (flowchart nodes are small)
const FLOWCHART_CARD_DEFAULT = 'simple'

// ── ELK layout options ────────────────────────────────────────────────────────
//
// Returns the ELK graph layoutOptions object for gen-time bun invocation.
// Ported from the bmd layout-engine.ts directionToElk() pattern.
//
// Canonical ELK options (verbatim property names — bun step reads these directly):
//   'elk.algorithm'                              layered = Sugiyama-style layered layout
//   'elk.direction'                              DOWN = top-to-bottom flow
//   'elk.spacing.nodeNode'                       horizontal gap between sibling nodes (28px)
//   'elk.layered.spacing.nodeNodeBetweenLayers'  vertical gap between layers (48px)
//   'elk.edgeRouting'                            ORTHOGONAL = right-angle edge segments
//   'elk.layered.nodePlacement.strategy'         BALANCED = horizontally centered placement
function elkOptionsForType() {
  return {
    'elk.algorithm': 'layered',
    'elk.direction': 'DOWN',
    'elk.spacing.nodeNode': '28',
    'elk.layered.spacing.nodeNodeBetweenLayers': '48',
    'elk.edgeRouting': 'ORTHOGONAL',
    'elk.layered.nodePlacement.strategy': 'BALANCED',
  }
}

// ── Node size estimation ──────────────────────────────────────────────────────
//
// Returns {width, height} for a descriptor node.
// Used by the gen-time bun elk step to provide approximate node dimensions
// so elkjs can avoid overlap (Risk R-1 from spec §9).
// Strategy (c) from spec: fixed size per shape type.
// Switch to char-width heuristic if overlap is observed in QA screenshots.
//   default rect                → 140 × 40 px  (standard process box)
//   diamond (decision/gate)     →  60 × 60 px  (equal sides for rotated square)
//   circle (terminal/start/end) →  36 × 36 px  (small circle terminus)
function nodeSizeForType(node) {
  const kind = node.kind || ''
  const shape = node.shape || ''

  // Diamond: decision gates (rotated square — equal W/H so elk does not squash)
  if (kind === 'diamond' || kind === 'decision' || kind === 'gate' || shape === 'diamond') {
    return { width: 60, height: 60 }
  }

  // Circle: terminal/start/end nodes
  if (kind === 'circle' || kind === 'terminal' || kind === 'start' || kind === 'end') {
    return { width: 36, height: 36 }
  }

  // Default: standard rectangular process box
  return { width: 140, height: 40 }
}

// ── Flowchart shape class injector ───────────────────────────────────────────
//
// Applies flowchart-specific CSS shape classes to already-rendered .fd-node
// elements (after cards.js:renderNodes() has created them).
//
// Shape classes (fd-engine.css):
//   fd-shape-diamond → rotated square via CSS clip-path (decision nodes)
//   fd-shape-pill    → fully-rounded via border-radius (terminal/start/end nodes)
//   (default rect: no extra class — fgraph-node styling applies)
//
// The card style default (FLOWCHART_CARD_DEFAULT='simple') is passed to
// renderNodes() from cards.js. Per-node override (node.cardStyle='premium')
// is resolved inside cards.js:renderNode() — this module does not re-implement it.
function applyFlowchartShapes(descriptor) {
  const nodes = descriptor.nodes || []
  for (const node of nodes) {
    const el = nodeEl[node.id]
    if (!el) continue

    const kind = node.kind || ''
    const shape = node.shape || ''

    if (kind === 'diamond' || kind === 'decision' || kind === 'gate' || shape === 'diamond') {
      el.classList.add('fd-shape-diamond')
    } else if (kind === 'circle' || kind === 'terminal' || kind === 'start' || kind === 'end' || shape === 'pill') {
      el.classList.add('fd-shape-pill')
    }
  }
}

// ── Pixel-space node positioning ─────────────────────────────────────────────
//
// For auto-layout types, descriptor.nodes[i].x/y hold pixel coordinates
// injected by the bun elk step at generation time (RD-1, spec §1.2 data flow).
// This function applies them as pixel left/top on each .fd-node element.
//
// Contrast with declarative types (architecture/hub-spoke) which store
// x/y in 0..100% space and use CSS percentage positioning via fgraph-base.css.
function positionFlowchartNodes(descriptor) {
  const nodes = descriptor.nodes || []
  for (const node of nodes) {
    const el = nodeEl[node.id]
    if (!el) continue
    // Pixel-space positioning — pre-computed by bun elk step (RD-1)
    el.style.left = `${node.x || 0}px`
    el.style.top = `${node.y || 0}px`
    // Clear CSS var percentage positioning set by cards.js (--x/--y from fgraph-base.css)
    el.style.removeProperty('--x')
    el.style.removeProperty('--y')
  }
}

// ── init ──────────────────────────────────────────────────────────────────────
//
// Called by the fd-engine bootstrap (generated HTML DOMContentLoaded handler)
// after parsing fd-data JSON. Returns the type contract object consumed by
// the engine orchestrator.
//
// The generated HTML bootstrap calls in order:
//   1. renderNodes(descriptor, typeDefault) — cards.js; uses FLOWCHART_CARD_DEFAULT='simple'
//   2. positionNodes(descriptor)            — pixel positioning from elk-injected x/y
//   3. applyShapes(descriptor)              — fd-shape-diamond / fd-shape-pill injection
//   4. draw()                               — edges.js DOM-measured bezier overlay
//   5. new ResizeObserver(redraw).observe(canvas) — edges.js wiring
function flowchartInit(descriptor) {
  const t = descriptor.type
  if (t !== 'flowchart') {
    console.warn('[fd] flowchart.js init() called with unexpected type:', t)
  }

  return {
    typeDefault: FLOWCHART_CARD_DEFAULT,
    // No zone placement for flowchart (auto-layout — no explicit zone descriptors)
    placeZones: null,
    // Post-render hooks: called by bootstrap after renderNodes()
    positionNodes: positionFlowchartNodes,
    applyShapes: applyFlowchartShapes,
    // Gen-time elk helpers (read by fd-layout.mjs bun step via window.__fdTypes)
    elkOptions: elkOptionsForType,
    nodeSizer: nodeSizeForType,
  }
}

// ── glob-discovery registration ───────────────────────────────────────────────
// bundler.js discovers fd/types/*.js and concatenates them into the inline
// <script>. At runtime each type module self-registers here so the bootstrap
// can dispatch to the correct init() without knowing type names at build time.
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[FLOWCHART_TYPE] = {
  CARD_DEFAULT: FLOWCHART_CARD_DEFAULT,
  placeZones: null,
  init: flowchartInit,
  elkOptions: elkOptionsForType,
  nodeSizer: nodeSizeForType,
}
