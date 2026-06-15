// fd/core.js — geometry core: rect, pairKey, faceFor, portAnchor, stubLen
// Lifted verbatim from lyra-stack-v2.html lines 492-534 and generalized for
// descriptor-driven fd-engine contract.
// Concat order: core.js FIRST (edges.js depends on names defined here).
// NOTE: all vars/functions here are intentionally "unused" in isolation —
// they are consumed by edges.js and other fd/ modules via bundler concat.

var nodeEl = {} // id → DOM element map, populated by initEngine
var canvas = null // .fd-canvas element ref
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
var svg = null // .fd-edges SVG overlay element ref
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
var paths = [] // one SVG <path> per deduped pair
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
var pathByPair = new Map() // pairKey → SVG <path>
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
var DESCRIPTOR = null // full descriptor object set by initEngine
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
var NS = 'http://www.w3.org/2000/svg'

// ---- Geometry helpers (verbatim lift from lyra-stack-v2.html l.492-534) ----

// l.492-495: canvas-relative rect for a node by id
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
function rect(id) {
  var el = nodeEl[id]
  var cr = canvas.getBoundingClientRect()
  var b = el.getBoundingClientRect()
  return { cx: b.left - cr.left + b.width / 2, cy: b.top - cr.top + b.height / 2, w: b.width, h: b.height }
}

// l.498: canonical (unordered) key for a node pair
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
function pairKey(a, b) {
  return [a, b].sort().join('|')
}

// l.501-514: face selection — source exits toward target, target enters from opposite
// Keeps srcFace / dstFace per-edge overrides from descriptor
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
function faceFor(dx, dy, isSource, edge) {
  if (edge) {
    if (isSource && edge.srcFace) return edge.srcFace
    if (!isSource && edge.dstFace) return edge.dstFace
  }
  if (Math.abs(dy) >= Math.abs(dx)) {
    if (isSource) return dy > 0 ? 'bottom' : 'top'
    else return dy > 0 ? 'top' : 'bottom'
  } else {
    if (isSource) return dx > 0 ? 'right' : 'left'
    else return dx > 0 ? 'left' : 'right'
  }
}

// l.516-528: port anchor — spreads slots evenly across the chosen face
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
function portAnchor(r, face, slotIdx, slotCount) {
  var cx = r.cx,
    cy = r.cy,
    w = r.w,
    h = r.h
  var hw = w / 2,
    hh = h / 2
  var faceLen = face === 'top' || face === 'bottom' ? w : h
  var spread = Math.min(faceLen * 0.55, slotCount * 16)
  var step = slotCount > 1 ? spread / (slotCount - 1) : 0
  var offset = slotCount > 1 ? -spread / 2 + slotIdx * step : 0
  switch (face) {
    case 'top':
      return { x: cx + offset, y: cy - hh, nx: 0, ny: -1 }
    case 'bottom':
      return { x: cx + offset, y: cy + hh, nx: 0, ny: 1 }
    case 'left':
      return { x: cx - hw, y: cy + offset, nx: -1, ny: 0 }
    case 'right':
      return { x: cx + hw, y: cy + offset, nx: 1, ny: 0 }
  }
}

// l.531-534: proportional bezier offset — clamp(dist * 0.35, 30, 220)
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — consumed by edges.js */
function stubLen(dx, dy) {
  var dist = Math.sqrt(dx * dx + dy * dy)
  return Math.max(30, Math.min(220, dist * 0.35))
}

// ---- Engine initializer ----
// Called once at DOMContentLoaded by the generated output script.
// descriptor: parsed fd-data JSON
// canvasEl:   .fd-canvas DOM element
// svgEl:      .fd-edges SVG overlay element
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — entry point called by generated HTML */
function initEngine(descriptor, canvasEl, svgEl) {
  DESCRIPTOR = descriptor
  canvas = canvasEl
  svg = svgEl
  nodeEl = {}
  paths = []
  pathByPair = new Map()

  // Apply canvas height from descriptor (default 720px via CSS --fd-canvas-h)
  if (descriptor.canvas?.height) {
    canvasEl.style.setProperty('--fd-canvas-h', `${descriptor.canvas.height}px`)
  }
}
