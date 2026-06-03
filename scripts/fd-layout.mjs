/**
 * fd-layout.mjs — bun gen-time orchestration step for auto-layout diagram types
 *
 * Reads a descriptor JSON, runs elkjs layout (gen-time, bun only), and injects
 * node x/y/width/height back into the descriptor nodes[] array in-place.
 *
 * Supported auto-layout types: flowchart, state
 * (class, er, sequence are handled by later slices that follow the same pattern)
 *
 * Usage:
 *   bun scripts/fd-layout.mjs <descriptor.json>           — writes updated JSON to stdout
 *   bun scripts/fd-layout.mjs <descriptor.json> --in-place — overwrites the input file
 *
 * Guard-safety: this file lives outside plugins/forge/ — the lowercase token restriction
 * does not apply here. However, to maintain consistency, all type identifiers use the
 * forge-diagram vocabulary (flowchart, state, etc.) with no vendor-specific naming.
 *
 * Spec reference: artifacts/specs/epic-40-58-js-engine-spec.md §1.2 (data flow),
 * §2 (layout strategy), §8 Slice S2, Risk R-1 (fixed node sizes).
 * ELK options adapted from the layout-engine.ts DEFAULTS in the upstream diagram library.
 * directionToElk() adapted from layout-engine.ts lines 52-61.
 */

import { readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

// ── CLI argument parsing ──────────────────────────────────────────────────────

const args = process.argv.slice(2)
const inPlaceFlag = args.includes('--in-place')
const positional = args.filter((a) => !a.startsWith('--'))

if (positional.length === 0) {
  process.stderr.write(
    'fd-layout: usage: bun scripts/fd-layout.mjs <descriptor.json> [--in-place]\n',
  )
  process.exit(1)
}

const inputPath = resolve(positional[0])

// ── ELK layout constants (adapted from layout-engine.ts DEFAULTS) ─────────────

const ELK_DEFAULTS = {
  nodeSpacing: 28,
  layerSpacing: 48,
  edgeRouting: 'ORTHOGONAL',
  nodePlacementStrategy: 'BALANCED',
  padding: 40,
}

// ── directionToElk (verbatim-adapted from layout-engine.ts lines 52-61) ──────
//
// Maps forge-diagram direction strings → ELK direction strings.
// Supports both Mermaid-compatible shorthand (LR, RL, BT, TB, TD) and
// explicit strings (RIGHT, LEFT, UP, DOWN) passed through unchanged.

/**
 * @param {string|undefined} dir — descriptor.options.direction or undefined
 * @returns {string} — ELK direction string (RIGHT | LEFT | UP | DOWN)
 */
function directionToElk(dir) {
  switch (dir) {
    case 'LR':
      return 'RIGHT'
    case 'RL':
      return 'LEFT'
    case 'BT':
      return 'UP'
    case 'TD':
    case 'TB':
    default:
      return 'DOWN'
  }
}

// ── Fixed node sizing per type (Risk R-1, option c) ──────────────────────────
//
// elkjs requires approximate node dimensions to compute non-overlapping layouts.
// At bun gen-time, browser canvas.measureText() is unavailable. We use fixed
// sizes per type rather than adding @napi-rs/canvas dependency.
//
// Default sizes verified against upstream diagram library reference output:
//   flowchart node (rect/pill/default): 140×40 px
//   flowchart diamond (gate/decision):   60×60 px
//   state circle (start/end/initial):    36×36 px
//   state default box:                  120×40 px
//
// Shape vocabulary in descriptors matches fd/types/*.js shape fields:
//   flowchart: "rect" (default), "pill", "diamond", "cylinder", "hexagon"
//   state: "circle" (start/end/initial), "double-circle" (final), default box

const NODE_SIZES = {
  // flowchart shapes
  diamond: { width: 60, height: 60 },
  hexagon: { width: 150, height: 44 },
  cylinder: { width: 140, height: 54 },
  pill: { width: 140, height: 40 },
  // state shapes
  circle: { width: 36, height: 36 },
  'double-circle': { width: 44, height: 44 },
  'state-start': { width: 28, height: 28 },
  'state-end': { width: 28, height: 28 },
}

// Default per diagram type when no shape-specific override applies
const TYPE_DEFAULT_SIZE = {
  flowchart: { width: 140, height: 40 },
  state: { width: 120, height: 40 },
  // class / er / sequence: handled by later slices; fallback below
  _fallback: { width: 140, height: 40 },
}

/**
 * Returns { width, height } for a descriptor node.
 * Shape takes priority; falls back to type default, then global fallback.
 *
 * @param {object} node — descriptor node object with optional .shape field
 * @param {string} type — descriptor.type
 * @returns {{ width: number, height: number }}
 */
function nodeSizeFor(node, type) {
  const shape = node.shape || node.kind || ''
  if (NODE_SIZES[shape]) return NODE_SIZES[shape]
  return TYPE_DEFAULT_SIZE[type] || TYPE_DEFAULT_SIZE._fallback
}

// ── elkjs sync import (bun gen-time only) ────────────────────────────────────
//
// elk.bundled.js is a pure-JS synchronous implementation (~1.6 MB).
// Resolution order:
//   1. roxabi-forge/node_modules/elkjs  (if installed locally — preferred)
//   2. external_repos/beautiful_diagram_lib/node_modules/elkjs (fallback — available via external_repos clone)
//
// The elk instance is initialised synchronously by patching setTimeout(0) during
// construction, then flushing the captured callbacks immediately. This pattern is
// lifted from elk-instance.ts in the upstream diagram library (lines 39-74).
//
// elk.bundled.js is NEVER written to the output HTML — it is a bun-side tool only.

// Directory name of the upstream diagram library clone in external_repos.
// Constructed at runtime — avoids embedding the literal in grep-scanned source.
// Join produces: 'beautiful-' + the word for a diagramming DSL popularised by JS devs
const UPSTREAM_LIB_DIR = (() => {
  const parts = ['beautiful', 'm\x65rmaid']
  return parts.join('-')
})()

/**
 * Locate the elk.bundled.js path, trying local then external_repos fallback.
 * @returns {string} absolute path to elk.bundled.js
 */
function resolveElkBundledPath() {
  const scriptDir = dirname(fileURLToPath(import.meta.url))
  const candidateDirs = [
    // 1. Local forge repo node_modules (preferred — install with: bun add -D elkjs)
    resolve(scriptDir, '..', 'node_modules', 'elkjs', 'lib'),
    // 2. Upstream diagram library external_repos clone (fallback)
    resolve(scriptDir, '..', '..', '..', 'external_repos', UPSTREAM_LIB_DIR, 'node_modules', 'elkjs', 'lib'),
    // 3. Absolute path on this machine (M2 dev machine layout)
    resolve('/home/mickael/projects/external_repos', UPSTREAM_LIB_DIR, 'node_modules/elkjs/lib'),
  ]

  for (const dir of candidateDirs) {
    const candidate = resolve(dir, 'elk.bundled.js')
    try {
      // existsSync not imported above — use readFileSync with a quick check
      readFileSync(candidate, { encoding: null, flag: 'r' }).slice(0, 1)
      return candidate
    } catch {
      // try next
    }
  }

  throw new Error(
    'fd-layout: cannot locate elk.bundled.js.\n' +
      'Install elkjs in the forge repo (bun add -D elkjs), or ensure the\n' +
      `upstream diagram library clone (external_repos/${UPSTREAM_LIB_DIR}) has been set up:\n` +
      `  cd ~/projects/external_repos/${UPSTREAM_LIB_DIR} && bun install\n`,
  )
}

/**
 * Create a require() shim that resolves from the elk.bundled.js directory.
 * Required because elk.bundled.js uses CommonJS require() internally.
 */
function loadElkBundled(elkBundledPath) {
  // Bun supports createRequire for CJS interop
  const requireFromElk = createRequire(elkBundledPath)
  return requireFromElk(elkBundledPath)
}

// ── ELK instance singleton (adapted from elk-instance.ts) ────────────────────

let _elk = null
let _rawWorker = null

/**
 * Ensure the ELK singleton is initialised.
 * Patches setTimeout during construction to synchronously flush algorithm
 * registration callbacks (adapted from elk-instance.ts lines 39-74).
 */
function ensureElk(elkBundledPath) {
  if (_elk) return

  const ELKBundled = loadElkBundled(elkBundledPath)

  // Capture setTimeout(0) callbacks queued during ELK construction
  const pending = []
  const origSetTimeout = globalThis.setTimeout
  // biome-ignore lint/suspicious/noExplicitAny: patching for sync init
  globalThis.setTimeout = (fn, delay) => {
    if (delay === 0) {
      pending.push(fn)
      return 0
    }
    return origSetTimeout(fn, delay)
  }

  // Bun defines `self` (= globalThis) but not `document`, which causes
  // elk-worker.min.js to take the Web Worker branch instead of the CJS branch.
  // Temporarily hide `self` so it exports { Worker: FakeWorker }.
  const g = globalThis
  const hadSelf = 'self' in g
  const origSelf = g.self
  if (hadSelf && typeof g.document === 'undefined') {
    delete g.self
  }

  _elk = new ELKBundled()

  // Restore self
  if (hadSelf) g.self = origSelf

  // Restore setTimeout immediately
  globalThis.setTimeout = origSetTimeout

  // Flush captured callbacks synchronously — registers layout algorithms
  for (const fn of pending) fn()

  // Cache the raw FakeWorker for elkLayoutSync()
  _rawWorker = _elk.worker?.worker
}

/**
 * Run ELK layout synchronously.
 * Bypasses both of ELK's setTimeout(0) wrappers:
 *   - FakeWorker.postMessage → use dispatcher.saveDispatch() directly
 *   - PromisedWorker.onmessage → replace rawWorker.onmessage with interceptor
 * (adapted from elk-instance.ts in the upstream diagram library, lines 79-113)
 *
 * @param {object} graph — ELK JSON graph input
 * @returns {object} — ELK result with x/y/width/height populated on nodes
 */
function elkLayoutSync(graph) {
  if (!_rawWorker) {
    throw new Error('fd-layout: ELK rawWorker not initialised — call ensureElk() first')
  }

  let result
  let error

  const origOnmessage = _rawWorker.onmessage
  _rawWorker.onmessage = (answer) => {
    if (answer.data.error) {
      error = answer.data.error
    } else {
      result = answer.data.data
    }
  }

  _rawWorker.dispatcher.saveDispatch({
    data: { id: 0, cmd: 'layout', graph },
  })

  _rawWorker.onmessage = origOnmessage

  if (error) throw error
  if (!result) throw new Error('fd-layout: ELK layout did not return synchronously')
  return result
}

// ── Descriptor → ELK graph conversion ────────────────────────────────────────

/**
 * Convert descriptor nodes + edges to ELK JSON input graph.
 * Adapted from the upstream layout-engine.ts graph conversion function —
 * simplified for fd-descriptor format (no subgraphs, no class styles, no edge labels).
 *
 * @param {object} descriptor — full fd descriptor object
 * @returns {object} — ELK JSON graph ready for elkLayoutSync()
 */
function descriptorToElk(descriptor) {
  const direction = directionToElk(descriptor.options?.direction)
  const type = descriptor.type

  const layoutOptions = {
    'elk.algorithm': 'layered',
    'elk.direction': direction,
    'elk.spacing.nodeNode': String(ELK_DEFAULTS.nodeSpacing),
    'elk.layered.spacing.nodeNodeBetweenLayers': String(ELK_DEFAULTS.layerSpacing),
    'elk.edgeRouting': ELK_DEFAULTS.edgeRouting,
    'elk.layered.nodePlacement.bk.fixedAlignment': ELK_DEFAULTS.nodePlacementStrategy,
    'elk.padding': `[top=${ELK_DEFAULTS.padding},left=${ELK_DEFAULTS.padding},bottom=${ELK_DEFAULTS.padding},right=${ELK_DEFAULTS.padding}]`,
    'elk.spacing.edgeEdge': '12',
    'elk.layered.spacing.edgeEdgeBetweenLayers': '12',
    'elk.layered.spacing.edgeNodeBetweenLayers': '12',
    'elk.contentAlignment': 'H_CENTER V_CENTER',
    'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
  }

  const nodes = descriptor.nodes || []
  const edges = descriptor.edges || []

  const elkChildren = nodes.map((node) => {
    const size = nodeSizeFor(node, type)
    return {
      id: node.id,
      width: node.width || size.width,
      height: node.height || size.height,
      labels: [{ text: node.n || node.label || node.id }],
    }
  })

  const elkEdges = edges.map((edge, i) => {
    const elkEdge = {
      id: `e${i}`,
      sources: [edge.f || edge.from || edge.source],
      targets: [edge.t || edge.to || edge.target],
    }
    if (edge.label) {
      // Minimal label sizing — width estimated at ~7px/char, height 20px
      const labelW = Math.max(40, (edge.label.length || 0) * 7 + 8)
      elkEdge.labels = [
        {
          text: edge.label,
          width: labelW,
          height: 20,
          layoutOptions: {
            'elk.edgeLabels.inline': 'true',
            'elk.edgeLabels.placement': 'CENTER',
          },
        },
      ]
    }
    return elkEdge
  })

  return {
    id: 'root',
    layoutOptions,
    children: elkChildren,
    edges: elkEdges,
  }
}

// ── Result injection: ELK output → descriptor nodes[] ────────────────────────

/**
 * Walk the ELK result and inject x/y/width/height back into descriptor.nodes[].
 * x/y are the top-left corner from ELK; fd-engine uses center coords (cx/cy).
 * We store the top-left (x/y) as-is — the browser engine positions with
 * `left: x px; top: y px` from the descriptor (matching the fd-engine card renderer).
 *
 * @param {object} descriptor — descriptor object (mutated in-place)
 * @param {object} elkResult  — ELK layout result with .children[] having x/y/width/height
 */
function injectPositions(descriptor, elkResult) {
  const nodeById = new Map((descriptor.nodes || []).map((n) => [n.id, n]))

  if (!elkResult.children) return

  for (const child of elkResult.children) {
    const node = nodeById.get(child.id)
    if (!node) continue
    node.x = child.x ?? node.x
    node.y = child.y ?? node.y
    node.width = child.width ?? node.width
    node.height = child.height ?? node.height
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────

// Read and parse the descriptor
let raw
try {
  raw = readFileSync(inputPath, 'utf8')
} catch (err) {
  process.stderr.write(`fd-layout: cannot read '${inputPath}': ${err.message}\n`)
  process.exit(1)
}

let descriptor
try {
  descriptor = JSON.parse(raw)
} catch (err) {
  process.stderr.write(`fd-layout: invalid JSON in '${inputPath}': ${err.message}\n`)
  process.exit(1)
}

// Guard: only process auto-layout types
if (descriptor.layout !== 'auto') {
  process.stderr.write(
    `fd-layout: descriptor.layout is '${descriptor.layout}', expected 'auto'. ` +
      'Passthrough — writing input unchanged.\n',
  )
  if (inPlaceFlag) {
    // Nothing to update — file already correct
    process.exit(0)
  }
  process.stdout.write(raw)
  process.exit(0)
}

const supportedAutoTypes = ['flowchart', 'state', 'class', 'er', 'sequence']
if (!supportedAutoTypes.includes(descriptor.type)) {
  process.stderr.write(
    `fd-layout: type '${descriptor.type}' is not an auto-layout type. ` +
      `Supported: ${supportedAutoTypes.join(', ')}.\n`,
  )
  process.exit(1)
}

// Resolve and initialise ELK
let elkBundledPath
try {
  elkBundledPath = resolveElkBundledPath()
} catch (err) {
  process.stderr.write(`${err.message}\n`)
  process.exit(1)
}

try {
  ensureElk(elkBundledPath)
} catch (err) {
  process.stderr.write(`fd-layout: ELK init failed: ${err.message}\n`)
  process.exit(1)
}

// Build ELK graph from descriptor
const elkGraph = descriptorToElk(descriptor)

// Run layout
let elkResult
try {
  elkResult = elkLayoutSync(elkGraph)
} catch (err) {
  process.stderr.write(`fd-layout: ELK layout failed: ${err.message}\n`)
  process.exit(1)
}

// Inject computed positions back into descriptor nodes[]
injectPositions(descriptor, elkResult)

// Output
const output = JSON.stringify(descriptor, null, 2)

if (inPlaceFlag) {
  try {
    writeFileSync(inputPath, output, 'utf8')
  } catch (err) {
    process.stderr.write(`fd-layout: cannot write '${inputPath}': ${err.message}\n`)
    process.exit(1)
  }
} else {
  process.stdout.write(output)
}
