// fd/types/state.js — state machine diagram type module (S2)
// Glob-discovery: bundler.js discovers this file via glob('fd/types/*.js').
// Exports TYPE so bundler can key it: window.__fdTypes[TYPE] = { CARD_DEFAULT, elkOptionsForType, nodeSizeForType, init }
//
// Layout branch: elkjs gen-time (RD-1).
//   bun step runs elkjs.layout() with options from elkOptionsForType().
//   Node x/y/width/height injected into descriptor by scripts/fd-layout.mjs before HTML assembly.
//   Browser receives pre-positioned descriptor; no elk at runtime.
//
// RD-3: auto-layout types (state included) default to simple card (plain box).
// Shape mapping:
//   kind='start'  → .fd-shape-circle fd-state-start (solid filled circle, 32×32px)
//   kind='end'    → .fd-shape-circle fd-state-end   (double-ring circle, 32×32px)
//   kind='choice' → .fd-shape-diamond               (diamond / decision node, 56×56px)
//   default       → plain box                        (120×36px)
// Edge style:
//   edge.style='dashed' → dashed stroke (for internal / self-transitions)
//   edge.label          → rendered as SVG text label at bezier midpoint
// Guard-clean: descriptor uses forge-diagram / fd-engine identifiers (AC-7).

const TYPE = 'state'
const CARD_DEFAULT = 'simple' // RD-3: auto-layout types default to simple

// ── elkOptionsForType ─────────────────────────────────────────────────────
// Returns the elkjs options object for state machine diagrams.
// Used by scripts/fd-layout.mjs at generation time.
// Spec: layered algorithm, DOWN direction, nodeSpacing=24, layerSpacing=44,
//       ORTHOGONAL edge routing.
function elkOptionsForType() {
  return {
    'elk.algorithm': 'layered',
    'elk.direction': 'DOWN',
    'elk.spacing.nodeNode': '24',
    'elk.layered.spacing.nodeNodeBetweenLayers': '44',
    'elk.edgeRouting': 'ORTHOGONAL',
  }
}

// ── nodeSizeForType ───────────────────────────────────────────────────────
// Returns { width, height } for a descriptor node.
// Used by scripts/fd-layout.mjs to populate elkjs graph node dimensions.
// Spec:
//   start / end (circles) → 32×32px
//   choice (diamond)      → 56×56px
//   default (box)         → 120×36px
function nodeSizeForType(node) {
  const kind = node.kind
  if (kind === 'start' || kind === 'end') {
    return { width: 32, height: 32 }
  }
  if (kind === 'choice') {
    return { width: 56, height: 56 }
  }
  return { width: 120, height: 36 }
}

// ── State-specific renderNode extension ──────────────────────────────────
// Augments the base renderNode output with state-machine shape classes.
// Called during renderNodes() pass after the base fd-node element is created.
// Handles circle nodes (start/end) and diamond nodes (choice/fork).
function applyStateShape(el, node) {
  const kind = node.kind
  if (kind === 'start') {
    el.classList.add('fd-shape-circle', 'fd-state-start')
    // Solid-fill start state: inner content is empty (shape communicates meaning)
    el.innerHTML = ''
  } else if (kind === 'end') {
    el.classList.add('fd-shape-circle', 'fd-state-end')
    // Double-ring end state: inner filled circle for the double-ring effect
    el.innerHTML = '<span class="fd-state-end-inner"></span>'
  } else if (kind === 'choice' || kind === 'fork') {
    el.classList.add('fd-shape-diamond')
    // Choice/fork diamond: show a label if provided
    if (node.n) {
      el.innerHTML = `<span class="fd-state-diamond-label">${node.n}</span>`
    } else {
      el.innerHTML = ''
    }
  }
  // plain states keep the default simple card rendered by cards.js
}

// ── State-specific edge post-processing ──────────────────────────────────
// Called after draw() to apply dashed style to internal/self-transition edges.
// edge.style='dashed' → adds .fd-edge-dashed class → CSS stroke-dasharray
// Guard labels are rendered by edges.js as edge.label → fd-elabel SVG text.
function applyStateEdgeStyles() {
  if (!DESCRIPTOR?.edges) return
  DESCRIPTOR.edges.forEach((edge) => {
    if (edge.style === 'dashed') {
      // Find the SVG path with matching data-f / data-t attributes
      const pk = [edge.f, edge.t].sort().join('|')
      const pathEl = svg.querySelector(`path[data-pk="${pk}"]`)
      if (pathEl) {
        pathEl.classList.add('fd-edge-dashed')
      }
    }
  })
}

// ── init ─────────────────────────────────────────────────────────────────
// Called by the fd-engine bootstrap after parsing fd-data.
// Returns { typeDefault, elkOptionsForType, nodeSizeForType, applyStateShape, applyStateEdgeStyles }
// consumed by the engine orchestrator.
function init(descriptor) {
  const t = descriptor.type
  if (t !== 'state') {
    console.warn('[fd] state.js init() called with unexpected type:', t)
  }
  // Auto-layout: x/y are already injected into descriptor by bun elk step (RD-1).
  // No declarative zone placement needed for state diagrams.
  return {
    typeDefault: CARD_DEFAULT,
    elkOptionsForType,
    nodeSizeForType,
    applyStateShape,
    applyStateEdgeStyles,
  }
}

// ── glob-discovery registration ───────────────────────────────────────────
// bundler.js discovers fd/types/*.js and concatenates them into the
// inline <script>. At runtime each type module self-registers here.
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[TYPE] = {
  CARD_DEFAULT,
  elkOptionsForType,
  nodeSizeForType,
  applyStateShape,
  applyStateEdgeStyles,
  init,
}
