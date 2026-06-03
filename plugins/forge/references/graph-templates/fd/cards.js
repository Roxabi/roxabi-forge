// fd/cards.js — Layer 1: node renderer
// Concat order: core.js → cards.js → architecture.js
// Depends on: nodeEl (map), canvas (element) — declared in core.js scope

// ── kind → fgraph-base.css shape class mapping ────────────────────────
const KIND_SHAPE = {
  bus: 'pill',
  broker: 'pill',
  router: 'pill',
  agent: 'hexagon',
  worker: 'hexagon',
  trigger: 'circle',
  event: 'circle',
  database: 'cylinder',
  storage: 'cylinder',
  store: 'cylinder',
  queue: 'cylinder',
  decision: 'diamond',
  gate: 'diamond',
  file: 'folded',
  config: 'folded',
  document: 'folded',
}

// ── kind → tone class mapping (fgraph-base.css tone modifiers) ────────
const KIND_TONE = {
  bus: 'cyan',
  broker: 'cyan',
  router: 'cyan',
  agent: 'amber',
  worker: 'amber',
  trigger: 'green',
  event: 'green',
  database: 'purple',
  storage: 'purple',
  store: 'purple',
  queue: 'purple',
  decision: 'red',
  gate: 'red',
}

// ── host badge label normalisation ────────────────────────────────────
function hostLabel(raw) {
  if (!raw) return null
  if (raw === 'M1') return 'M₁'
  if (raw === 'M2') return 'M₂'
  if (raw === 'EX') return 'External'
  return raw
}

// ── premium card HTML ──────────────────────────────────────────────────
// .fd-card-premium structure:
//   .fd-accent  — left accent bar (color via --fd-plane-{plane} or --fd-tone-{kind})
//   .fd-title   — node.n
//   .fd-sub     — node.d  (subtitle / description, optional)
//   .fd-tag     — node.img (image path / tag badge, optional)
//   .fd-host    — node.h  (host badge, optional)
function buildPremiumCard(node) {
  const accentVar = node.plane
    ? `var(--fd-plane-${node.plane}, var(--fd-tone-${node.kind || 'default'}, var(--text-dim)))`
    : `var(--fd-tone-${node.kind || 'default'}, var(--text-dim))`

  const sub = node.d ? `<div class="fd-sub">${node.d}</div>` : ''
  const tag = node.img ? `<div class="fd-tag">${node.img}</div>` : ''
  const hb = node.h ? `<div class="fd-host ${node.h}">${hostLabel(node.h)}</div>` : ''

  return (
    `<span class="fd-accent" style="background:${accentVar}"></span>` +
    `<div class="fd-title">${node.n}</div>` +
    sub +
    tag +
    hb
  )
}

// ── simple card HTML ───────────────────────────────────────────────────
function buildSimpleCard(node) {
  const sub = node.d ? `<div class="fd-sub">${node.d}</div>` : ''
  return `<div class="fd-title">${node.n}</div>${sub}`
}

// ── renderNode ────────────────────────────────────────────────────────
// node        — descriptor node object
// typeDefault — 'premium' | 'simple' | undefined (from types/{type}.js CARD_DEFAULT)
// Returns the created element (also populates nodeEl[node.id]).
function renderNode(node, typeDefault) {
  const el = document.createElement('div')

  // base classes
  let cls = 'fgraph-node fd-node'

  // fd-kind-{kind} class — used by fd-engine.css kind-variant rules
  if (node.kind) cls += ` fd-kind-${node.kind}`

  // shape class from kind
  const shape = KIND_SHAPE[node.kind]
  if (shape) cls += ` ${shape}`

  // tone class from kind
  const tone = KIND_TONE[node.kind]
  if (tone) cls += ` ${tone}`

  el.className = cls
  el.dataset.id = node.id

  // position: CSS var convention matching fgraph-base.css (--x, --y in 0..100 % space)
  el.style.setProperty('--x', node.x)
  el.style.setProperty('--y', node.y)

  // card style resolution: per-node override (highest) → typeDefault → 'simple' fallback (RD-3)
  const style = node.cardStyle || typeDefault || 'simple'

  if (style === 'premium') {
    el.classList.add('fd-card-premium')
    el.innerHTML = buildPremiumCard(node)
  } else {
    el.innerHTML = buildSimpleCard(node)
  }

  // register in shared nodeEl map (declared in core.js scope)
  nodeEl[node.id] = el

  return el
}

// ── renderNodes ───────────────────────────────────────────────────────
// descriptor — full fd-data descriptor object
// typeDefault comes from types/{type}.js via the init() call
// biome-ignore lint/correctness/noUnusedVariables: called by core.js in concat bundle
function renderNodes(descriptor, typeDefault) {
  const nodes = descriptor.nodes || []
  for (const node of nodes) {
    const el = renderNode(node, typeDefault)
    canvas.appendChild(el)
  }
}
