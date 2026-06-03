/**
 * Tests for fd/bundler.js — gen-time bundler for the fd-engine.
 *
 * bundler.js is an ES module (Node, not browser). We test it via direct import.
 * Covers: concat order, type module inclusion, missing type error,
 * IIFE wrapper, section comments, and guard: banned token absent from output.
 */

import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { buildEngine, buildEngineScript } from '../bundler.js'

// ---------------------------------------------------------------------------
// Locate the fd/ directory relative to this test file
// ---------------------------------------------------------------------------

const FD_DIR = join(import.meta.dirname, '..')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Guard check: does the output contain the banned lowercase token?
 * Built via concatenation so this file itself does not emit the token.
 */
const BANNED = 'mer' + 'maid'
const bannedRe = new RegExp(`\\b${BANNED}\\b`)
function hasBannedToken(src: string): boolean {
  return bannedRe.test(src)
}

// ---------------------------------------------------------------------------
// Suite: buildEngine — architecture type (S1)
// ---------------------------------------------------------------------------

describe('buildEngine(fdDir, "architecture")', () => {
  it('returns a non-empty string', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(typeof bundle).toBe('string')
    expect(bundle.length).toBeGreaterThan(100)
  })

  it('wraps output in IIFE', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    const trimmed = bundle.trim()
    expect(trimmed).toMatch(/^\(function\(\)/)
    expect(trimmed).toMatch(/\}\)\(\)$/)
  })

  it('includes core.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('/* ── fd/core.js ── */')
  })

  it('includes edges.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('/* ── fd/edges.js ── */')
  })

  it('includes cards.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('/* ── fd/cards.js ── */')
  })

  it('includes architecture.js type module section comment', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    // bundler.js uses basename() so the comment shows the filename only
    expect(bundle).toContain('/* ── fd/architecture.js ── */')
  })

  it('core.js precedes edges.js (concat order)', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    const coreIdx = bundle.indexOf('/* ── fd/core.js ── */')
    const edgesIdx = bundle.indexOf('/* ── fd/edges.js ── */')
    expect(coreIdx).toBeGreaterThanOrEqual(0)
    expect(edgesIdx).toBeGreaterThan(coreIdx)
  })

  it('edges.js precedes cards.js (concat order)', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    const edgesIdx = bundle.indexOf('/* ── fd/edges.js ── */')
    const cardsIdx = bundle.indexOf('/* ── fd/cards.js ── */')
    expect(edgesIdx).toBeGreaterThanOrEqual(0)
    expect(cardsIdx).toBeGreaterThan(edgesIdx)
  })

  it('cards.js precedes architecture.js type module (concat order)', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    const cardsIdx = bundle.indexOf('/* ── fd/cards.js ── */')
    // bundler.js uses basename() so type module comment is 'architecture.js'
    const typeIdx = bundle.indexOf('/* ── fd/architecture.js ── */')
    expect(cardsIdx).toBeGreaterThanOrEqual(0)
    expect(typeIdx).toBeGreaterThan(cardsIdx)
  })

  it('GUARD: output must NOT contain the banned lowercase token', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(hasBannedToken(bundle)).toBe(false)
  })

  it('includes "use strict" inside IIFE', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain("'use strict'")
  })

  it('includes initEngine symbol (core.js entry point)', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('initEngine')
  })

  it('includes __fdTypes registration (architecture.js)', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('window.__fdTypes')
  })
})

// ---------------------------------------------------------------------------
// Suite: buildEngine — hub-spoke type (S1 alias)
// ---------------------------------------------------------------------------

describe('buildEngine(fdDir, "hub-spoke")', () => {
  it('returns a non-empty string (hub-spoke type module exists)', () => {
    const bundle = buildEngine(FD_DIR, 'hub-spoke')
    expect(typeof bundle).toBe('string')
    expect(bundle.length).toBeGreaterThan(100)
  })

  it('wraps hub-spoke output in IIFE', () => {
    const bundle = buildEngine(FD_DIR, 'hub-spoke')
    const trimmed = bundle.trim()
    expect(trimmed).toMatch(/^\(function\(\)/)
    expect(trimmed).toMatch(/\}\)\(\)$/)
  })

  it('includes hub-spoke.js type module section comment', () => {
    const bundle = buildEngine(FD_DIR, 'hub-spoke')
    expect(bundle).toContain('/* ── fd/hub-spoke.js ── */')
  })

  it('includes core.js in hub-spoke bundle', () => {
    const bundle = buildEngine(FD_DIR, 'hub-spoke')
    expect(bundle).toContain('/* ── fd/core.js ── */')
  })

  it('GUARD: hub-spoke output must NOT contain the banned lowercase token', () => {
    const bundle = buildEngine(FD_DIR, 'hub-spoke')
    expect(hasBannedToken(bundle)).toBe(false)
  })

  it('does NOT include architecture.js when type is hub-spoke', () => {
    const bundle = buildEngine(FD_DIR, 'hub-spoke')
    // bundler loads only the requested type module — architecture.js is not included
    expect(bundle).not.toContain('/* ── fd/architecture.js ── */')
  })
})

// ---------------------------------------------------------------------------
// Suite: buildEngine — missing type → throws
// ---------------------------------------------------------------------------

describe('buildEngine — missing type', () => {
  it('throws with a descriptive error for an unknown type', () => {
    expect(() => buildEngine(FD_DIR, 'nonexistent-type-xyz')).toThrowError(
      /no type module found for type 'nonexistent-type-xyz'/,
    )
  })
})

// ---------------------------------------------------------------------------
// Suite: buildEngineScript — wraps in <script> tag
// ---------------------------------------------------------------------------

describe('buildEngineScript', () => {
  it('wraps output in <script> tag', () => {
    const tag = buildEngineScript(FD_DIR, 'architecture')
    expect(tag.startsWith('<script>')).toBe(true)
    expect(tag.endsWith('</script>')).toBe(true)
  })

  it('contains the IIFE bundle inside the script tag', () => {
    const tag = buildEngineScript(FD_DIR, 'architecture')
    expect(tag).toContain('(function()')
  })
})

// ---------------------------------------------------------------------------
// Suite: opt-in modules (particles.js, interactions.js) — absent is fine
// ---------------------------------------------------------------------------

describe('optional modules (absent)', () => {
  it('bundle succeeds even when particles.js and interactions.js are absent', () => {
    // These optional modules do not exist yet in fd/ — bundler must not throw
    expect(() => buildEngine(FD_DIR, 'architecture')).not.toThrow()
  })

  it('bundle does not contain particles.js comment when file absent', () => {
    // Guard removed: assertion must always run regardless of particles.js presence.
    // When particles.js is absent the bundler's existsSync guard skips it,
    // so its section comment must never appear.
    // When particles.js is present the comment WILL appear — test remains truthful.
    const bundle = buildEngine(FD_DIR, 'architecture')
    if (existsSync(join(FD_DIR, 'particles.js'))) {
      expect(bundle).toContain('/* ── fd/particles.js ── */')
    } else {
      expect(bundle).not.toContain('/* ── fd/particles.js ── */')
    }
  })
})

// ---------------------------------------------------------------------------
// Suite: placeZones seam — edges.js guard: typeof check + correct call site
// ---------------------------------------------------------------------------

describe('edges.js placeZones seam', () => {
  it('edges.js typeof guard is present and calls placeZones(DESCRIPTOR)', () => {
    const edgesSrc = readFileSync(join(FD_DIR, 'edges.js'), 'utf-8')
    // Guard must check typeof before calling — not just a bare call
    expect(edgesSrc).toMatch(/typeof\s+placeZones\s*===\s*['"]function['"]/)
    // The guarded call must pass DESCRIPTOR, not empty args
    expect(edgesSrc).toContain('placeZones(DESCRIPTOR)')
    expect(edgesSrc).not.toMatch(/placeZones\(\s*\)/)
  })

  it('hub-spoke.js declares a top-level placeZones function (satisfies edges.js seam)', () => {
    const hubSpokeSrc = readFileSync(join(FD_DIR, 'types', 'hub-spoke.js'), 'utf-8')
    // Must export top-scope `function placeZones(` — not hubSpokePlaceZones
    expect(hubSpokeSrc).toMatch(/^function placeZones\s*\(/m)
    // Old mismatched name must be gone
    expect(hubSpokeSrc).not.toContain('hubSpokePlaceZones')
  })
})

// ---------------------------------------------------------------------------
// Suite: AC-10 — no preserveAspectRatio / viewBox in SVG overlay (regression guard)
// ---------------------------------------------------------------------------

describe('AC-10: SVG overlay uses pixel canvas (no viewBox stretch)', () => {
  it('edges.js must NOT setAttribute("preserveAspectRatio") on any element', () => {
    const edgesSrc = readFileSync(join(FD_DIR, 'edges.js'), 'utf-8')
    // The attribute must not be set — the comment mentioning the word is allowed
    expect(edgesSrc).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })

  it('edges.js must NOT set viewBox on the SVG overlay', () => {
    const edgesSrc = readFileSync(join(FD_DIR, 'edges.js'), 'utf-8')
    // viewBox on the overlay element is banned (giant-arrowhead bug class, #57)
    expect(edgesSrc).not.toMatch(/setAttribute\s*\(\s*['"]viewBox['"]/)
  })

  it('architecture bundle must NOT setAttribute("preserveAspectRatio")', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })

  it('hub-spoke bundle must NOT setAttribute("preserveAspectRatio")', () => {
    const bundle = buildEngine(FD_DIR, 'hub-spoke')
    expect(bundle).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })
})

// ---------------------------------------------------------------------------
// Suite: faceFor — srcFace / dstFace descriptor override guards
// ---------------------------------------------------------------------------

describe('faceFor srcFace/dstFace override guards', () => {
  it('core.js contains isSource && edge.srcFace early-return guard', () => {
    const coreSrc = readFileSync(join(FD_DIR, 'core.js'), 'utf-8')
    // Guard: if (isSource && edge.srcFace) return edge.srcFace
    expect(coreSrc).toMatch(/isSource\s*&&\s*edge\.srcFace/)
    expect(coreSrc).toMatch(/return\s+edge\.srcFace/)
  })

  it('core.js contains !isSource && edge.dstFace early-return guard', () => {
    const coreSrc = readFileSync(join(FD_DIR, 'core.js'), 'utf-8')
    // Guard: if (!isSource && edge.dstFace) return edge.dstFace
    expect(coreSrc).toMatch(/!\s*isSource\s*&&\s*edge\.dstFace/)
    expect(coreSrc).toMatch(/return\s+edge\.dstFace/)
  })

  it('faceFor returns edge.srcFace when isSource=true and edge.srcFace is set', () => {
    // Inline faceFor logic from core.js (source-level contract test, no DOM needed)
    function faceFor(dx: number, dy: number, isSource: boolean, edge: { srcFace?: string; dstFace?: string } | null): string {
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
    // srcFace override: returns descriptor value regardless of geometry
    expect(faceFor(100, 0, true, { srcFace: 'top' })).toBe('top')
    // Without override: geometry takes over (dx>0, isSource → 'right')
    expect(faceFor(100, 0, true, {})).toBe('right')
  })

  it('faceFor returns edge.dstFace when isSource=false and edge.dstFace is set', () => {
    function faceFor(dx: number, dy: number, isSource: boolean, edge: { srcFace?: string; dstFace?: string } | null): string {
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
    // dstFace override: returns descriptor value regardless of geometry
    expect(faceFor(100, 0, false, { dstFace: 'bottom' })).toBe('bottom')
    // Without override: geometry takes over (dx>0, !isSource → 'left')
    expect(faceFor(100, 0, false, {})).toBe('left')
  })
})
