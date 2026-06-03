/**
 * bundler.js — gen-time bundler for the fd-engine (forge-diagram JS engine, S1)
 *
 * Concatenates fd/ module sources into a single inline <script> string at
 * generation time. Invoked by forge-chart skill before assembling HTML output.
 *
 * Glob order:
 *   1. fd/core.js         (canvas setup, rect, pairKey, faceFor, portAnchor, stubLen)
 *   2. fd/edges.js        (draw, redraw, ResizeObserver wiring, marker defs)
 *   3. fd/cards.js        (renderNode, premium/simple card dispatch)
 *   4. fd/particles.js    (opt-in — included when present)
 *   5. fd/interactions.js (opt-in — included when present)
 *   6. fd/types/{type}.js (declarative handler for the requested diagram type)
 *
 * All source files are plain JS sharing one scope (no ES import/export).
 * The bundle is wrapped in an IIFE: (function(){ ... })()
 *
 * API:
 *   import { buildEngine } from './bundler.js'
 *   const scriptContent = buildEngine('/path/to/fd', 'architecture')
 *   // embed as <script>{scriptContent}</script> in the output HTML
 *
 * RD-4 compliance: type registry is filename-based — adding a new type means
 * dropping fd/types/{type}.js. bundler.js itself never needs editing per new type.
 *
 * AC-4 / AC-5: output is inlined as a single string, no fetch, no dynamic import.
 */

import { existsSync, readFileSync } from 'node:fs'
import { basename, join } from 'node:path'

/**
 * Resolve the ordered list of source files for a given fd/ dir + type.
 *
 * Core modules are loaded in a fixed order that guarantees the shared scope
 * is set up before type-specific code runs.
 *
 * @param {string} fdDir  — absolute path to the fd/ directory
 * @param {string} type   — diagram type string (e.g. 'architecture', 'hub-spoke')
 * @returns {string[]}    — ordered list of absolute file paths
 */
function resolveSourceFiles(fdDir, type) {
  const ordered = []

  // 1. Core modules: fixed load order (scope setup must precede edge/card/type code)
  const coreModules = ['core.js', 'edges.js', 'cards.js']
  for (const mod of coreModules) {
    const p = join(fdDir, mod)
    if (existsSync(p)) {
      ordered.push(p)
    }
  }

  // 2. Optional layer-4/5 modules (particles, interactions) — included when present
  const optionalModules = ['particles.js', 'interactions.js']
  for (const mod of optionalModules) {
    const p = join(fdDir, mod)
    if (existsSync(p)) {
      ordered.push(p)
    }
  }

  // 3. Type module — fd/types/{type}.js — appended last so it can call core helpers.
  //    Filename-based discovery: no manifest file needed.
  //    Adding a new type = drop a fd/types/{type}.js file; bundler.js is never edited.
  const typeFile = join(fdDir, 'types', `${type}.js`)
  if (!existsSync(typeFile)) {
    throw new Error(
      `fd-engine: no type module found for type '${type}' at ${typeFile}.\n` +
        `Add fd/types/${type}.js to register this diagram type (RD-4).`,
    )
  }
  ordered.push(typeFile)

  return ordered
}

/**
 * Build the engine bundle for a given fd/ directory and diagram type.
 *
 * @param {string} fdDir  — absolute path to the fd/ source directory
 * @param {string} type   — diagram type string (e.g. 'architecture', 'hub-spoke')
 * @returns {string}      — IIFE-wrapped bundle string, ready to embed as <script>…</script>
 */
export function buildEngine(fdDir, type) {
  const files = resolveSourceFiles(fdDir, type)

  const parts = files.map((filePath) => {
    const src = readFileSync(filePath, 'utf8')
    const name = basename(filePath)
    // Lightweight section comment so browser DevTools source shows module boundaries
    return `/* ── fd/${name} ── */\n${src}`
  })

  const body = parts.join('\n\n')

  // Wrap in IIFE to avoid polluting the global scope
  return `(function(){\n'use strict'\n\n${body}\n})()`
}

/**
 * Convenience: return a full <script> tag embedding the bundle.
 *
 * @param {string} fdDir  — absolute path to the fd/ source directory
 * @param {string} type   — diagram type string
 * @returns {string}      — '<script>(function(){...})()</script>'
 */
export function buildEngineScript(fdDir, type) {
  return `<script>\n${buildEngine(fdDir, type)}\n</script>`
}
