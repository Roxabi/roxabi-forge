/**
 * Tests for fd/types/er.js (Slice S3b)
 *
 * Coverage per task specification:
 *   1. elkOptionsForType shape — wider spacing than class (nodeSpacing=40, layerSpacing=64)
 *   2. nodeSizeForType height formula: 48 + attributes.length * 20px, width = 180px
 *   3. init() contract — returns required fields
 *   4. window.__fdTypes['er'] registration — CARD_DEFAULT, init, elkOptions, nodeSizer
 *   5. Crow's-foot marker names present in er.js source
 *   6. Guard-clean check — no banned lowercase token
 *
 * Tests run in Node via vitest — no DOM needed for source-level checks.
 * buildEngine(FD_DIR, 'er') verifies glob-discovery + bundle integration.
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { buildEngine } from '../bundler.js'

const FD_DIR = join(import.meta.dirname, '..')

// ---------------------------------------------------------------------------
// Guard helpers
// ---------------------------------------------------------------------------

// Assemble the banned token via concatenation so this test file itself is guard-clean
const BANNED = 'mer' + 'maid'
const bannedRe = new RegExp(`\\b${BANNED}\\b`)

function hasBannedToken(src: string): boolean {
  return bannedRe.test(src)
}

// ---------------------------------------------------------------------------
// Source extraction helpers
// ---------------------------------------------------------------------------

/**
 * Extract a named function body from source text using brace-depth tracking.
 * Returns the raw function source string (including signature).
 */
function extractFnSrc(src: string, fnName: string): string {
  const start = src.indexOf(`function ${fnName}(`)
  if (start === -1) throw new Error(`[test] function ${fnName} not found in source`)
  let depth = 0
  let i = start
  while (i < src.length) {
    if (src[i] === '{') depth++
    else if (src[i] === '}') {
      depth--
      if (depth === 0) { i++; break }
    }
    i++
  }
  return src.slice(start, i)
}

/**
 * Instantiate a function extracted from source, injecting named dependencies.
 * This ensures tests exercise the production formula, not a mirrored copy.
 */
function extractFn(src: string, fnName: string, deps: Record<string, unknown> = {}): (...args: unknown[]) => unknown {
  const body = extractFnSrc(src, fnName)
  const depNames = Object.keys(deps)
  const depVals = Object.values(deps)
  // biome-ignore lint/security/noGlobalEval: test-only, local source file
  return new Function(...depNames, `return (${body})`)(...depVals) as (...args: unknown[]) => unknown
}

// ---------------------------------------------------------------------------
// Load source
// ---------------------------------------------------------------------------

const erSrc = readFileSync(join(FD_DIR, 'types', 'er.js'), 'utf-8')

// ---------------------------------------------------------------------------
// Suite 1: Source-level guard and existence checks
// ---------------------------------------------------------------------------

describe('fd/types/er.js — source existence and guard', () => {
  it('file exists and is non-empty', () => {
    expect(erSrc.length).toBeGreaterThan(500)
  })

  it('GUARD: source must not contain the banned lowercase token', () => {
    expect(hasBannedToken(erSrc)).toBe(false)
  })

  it('defines elkOptionsForType function', () => {
    expect(erSrc).toMatch(/function elkOptionsForType\s*\(/)
  })

  it('defines nodeSizeForType function', () => {
    expect(erSrc).toMatch(/function nodeSizeForType\s*\(/)
  })

  it('defines erInit function', () => {
    expect(erSrc).toMatch(/function erInit\s*\(/)
  })

  it('registers window.__fdTypes["er"]', () => {
    expect(erSrc).toContain('window.__fdTypes')
    expect(erSrc).toContain("ER_TYPE")
    expect(erSrc).toContain("'er'")
  })

  it('TYPE constant is "er"', () => {
    expect(erSrc).toContain("const ER_TYPE = 'er'")
  })

  it('ER_CARD_DEFAULT is "simple" (RD-3: auto-layout types default to simple card)', () => {
    expect(erSrc).toContain("const ER_CARD_DEFAULT = 'simple'")
  })
})

// ---------------------------------------------------------------------------
// Suite 2: elkOptionsForType — wider spacing than flowchart and class
// ---------------------------------------------------------------------------

describe('elkOptionsForType — ER has wider spacing than flowchart/class', () => {
  const elkOptionsFn = extractFn(erSrc, 'elkOptionsForType') as () => Record<string, string>

  it('elkOptionsForType returns an object', () => {
    const opts = elkOptionsFn()
    expect(typeof opts).toBe('object')
    expect(opts).not.toBeNull()
  })

  it('algorithm is "layered" (Sugiyama)', () => {
    const opts = elkOptionsFn()
    expect(opts['elk.algorithm']).toBe('layered')
  })

  it('direction is "DOWN"', () => {
    const opts = elkOptionsFn()
    expect(opts['elk.direction']).toBe('DOWN')
  })

  it('nodeSpacing = 40 (wider than flowchart=28, class=32 per spec)', () => {
    const opts = elkOptionsFn()
    expect(Number(opts['elk.spacing.nodeNode'])).toBe(40)
  })

  it('layerSpacing = 64 (wider than flowchart=48, class=56 per spec)', () => {
    const opts = elkOptionsFn()
    expect(Number(opts['elk.layered.spacing.nodeNodeBetweenLayers'])).toBe(64)
  })

  it('edgeRouting is ORTHOGONAL', () => {
    const opts = elkOptionsFn()
    expect(opts['elk.edgeRouting']).toBe('ORTHOGONAL')
  })

  it('ER nodeSpacing (40) > flowchart nodeSpacing (28)', () => {
    // Confirms the spec requirement: wider than flowchart
    const opts = elkOptionsFn()
    expect(Number(opts['elk.spacing.nodeNode'])).toBeGreaterThan(28)
  })

  it('ER layerSpacing (64) > flowchart layerSpacing (48)', () => {
    const opts = elkOptionsFn()
    expect(Number(opts['elk.layered.spacing.nodeNodeBetweenLayers'])).toBeGreaterThan(48)
  })
})

// ---------------------------------------------------------------------------
// Suite 3: nodeSizeForType — height formula 48 + N*20, width=180
// ---------------------------------------------------------------------------

describe('nodeSizeForType — height formula and fixed width', () => {
  const nodeSizeFn = extractFn(erSrc, 'nodeSizeForType') as (node: unknown) => { width: number; height: number }

  it('width is always 180px (fixed per spec)', () => {
    expect(nodeSizeFn({ id: 'a', attributes: [] }).width).toBe(180)
    expect(nodeSizeFn({ id: 'b', attributes: [{ name: 'id', type: 'INT' }] }).width).toBe(180)
    expect(nodeSizeFn({ id: 'c' }).width).toBe(180)
  })

  it('height = 48 when attributes is empty (base header only)', () => {
    const size = nodeSizeFn({ id: 'x', attributes: [] })
    expect(size.height).toBe(48)
  })

  it('height = 48 when attributes is absent (no attributes field)', () => {
    const size = nodeSizeFn({ id: 'x' })
    expect(size.height).toBe(48)
  })

  it('height = 48 + 1*20 = 68 for 1 attribute', () => {
    const size = nodeSizeFn({ id: 'x', attributes: [{ name: 'id', type: 'INT' }] })
    expect(size.height).toBe(68)
  })

  it('height = 48 + 3*20 = 108 for 3 attributes', () => {
    const size = nodeSizeFn({
      id: 'x',
      attributes: [
        { name: 'id', type: 'INT', pk: true },
        { name: 'name', type: 'VARCHAR' },
        { name: 'email', type: 'VARCHAR' },
      ],
    })
    expect(size.height).toBe(108)
  })

  it('height = 48 + 5*20 = 148 for 5 attributes (typical ER entity)', () => {
    const attrs = Array.from({ length: 5 }, (_, i) => ({ name: `col${i}`, type: 'INT' }))
    const size = nodeSizeFn({ id: 'x', attributes: attrs })
    expect(size.height).toBe(148)
  })

  it('height formula is linear: each attribute adds exactly 20px', () => {
    const base = nodeSizeFn({ id: 'x', attributes: [] }).height
    for (let n = 1; n <= 8; n++) {
      const attrs = Array.from({ length: n }, (_, i) => ({ name: `c${i}`, type: 'INT' }))
      const size = nodeSizeFn({ id: 'x', attributes: attrs })
      expect(size.height).toBe(base + n * 20)
    }
  })
})

// ---------------------------------------------------------------------------
// Suite 4: init() contract
// ---------------------------------------------------------------------------

describe('erInit() contract', () => {
  it('erInit function is defined in source', () => {
    // erInit calls injectErCss() (a module-scope free variable) which requires a real DOM.
    // We verify the function definition exists rather than executing it in Node — the
    // function's returned shape is covered by the source-level checks below.
    expect(erSrc).toMatch(/function erInit\s*\(/)
  })

  it('erInit source returns typeDefault: ER_CARD_DEFAULT', () => {
    // Source-level: ensure the return statement includes typeDefault
    const initBody = extractFnSrc(erSrc, 'erInit')
    expect(initBody).toContain('typeDefault: ER_CARD_DEFAULT')
  })

  it('erInit source returns placeZones: null (no zone descriptors for ER)', () => {
    const initBody = extractFnSrc(erSrc, 'erInit')
    expect(initBody).toContain('placeZones: null')
  })

  it('erInit source returns positionNodes handler', () => {
    const initBody = extractFnSrc(erSrc, 'erInit')
    expect(initBody).toContain('positionNodes:')
  })

  it('erInit source returns applyShapes handler', () => {
    const initBody = extractFnSrc(erSrc, 'erInit')
    expect(initBody).toContain('applyShapes:')
  })

  it('erInit source returns injectMarkers handler', () => {
    const initBody = extractFnSrc(erSrc, 'erInit')
    expect(initBody).toContain('injectMarkers:')
  })

  it('erInit source returns applyEdgeHooks handler for crow\'s-foot markers', () => {
    const initBody = extractFnSrc(erSrc, 'erInit')
    expect(initBody).toContain('applyEdgeHooks:')
  })

  it('erInit source returns elkOptions for gen-time bun step', () => {
    const initBody = extractFnSrc(erSrc, 'erInit')
    expect(initBody).toContain('elkOptions:')
  })

  it('erInit source returns nodeSizer for gen-time bun step', () => {
    const initBody = extractFnSrc(erSrc, 'erInit')
    expect(initBody).toContain('nodeSizer:')
  })
})

// ---------------------------------------------------------------------------
// Suite 5: window.__fdTypes['er'] registration
// ---------------------------------------------------------------------------

describe('window.__fdTypes["er"] registration', () => {
  it('registration block is present in source', () => {
    expect(erSrc).toContain('window.__fdTypes = window.__fdTypes || {}')
    expect(erSrc).toContain('window.__fdTypes[ER_TYPE]')
  })

  it('registration includes CARD_DEFAULT field', () => {
    // Find the registration block and verify CARD_DEFAULT is included
    const regIdx = erSrc.lastIndexOf('window.__fdTypes[ER_TYPE]')
    const regBlock = erSrc.slice(regIdx, erSrc.length)
    expect(regBlock).toContain('CARD_DEFAULT')
  })

  it('registration includes init field', () => {
    const regIdx = erSrc.lastIndexOf('window.__fdTypes[ER_TYPE]')
    const regBlock = erSrc.slice(regIdx, erSrc.length)
    expect(regBlock).toContain('init: erInit')
  })

  it('registration includes elkOptions field', () => {
    const regIdx = erSrc.lastIndexOf('window.__fdTypes[ER_TYPE]')
    const regBlock = erSrc.slice(regIdx, erSrc.length)
    expect(regBlock).toContain('elkOptions')
  })

  it('registration includes nodeSizer field', () => {
    const regIdx = erSrc.lastIndexOf('window.__fdTypes[ER_TYPE]')
    const regBlock = erSrc.slice(regIdx, erSrc.length)
    expect(regBlock).toContain('nodeSizer')
  })

  it('registration exposes injectMarkers helper', () => {
    const regIdx = erSrc.lastIndexOf('window.__fdTypes[ER_TYPE]')
    const regBlock = erSrc.slice(regIdx, erSrc.length)
    expect(regBlock).toContain('injectMarkers')
  })

  it('registration exposes markerFor helper', () => {
    const regIdx = erSrc.lastIndexOf('window.__fdTypes[ER_TYPE]')
    const regBlock = erSrc.slice(regIdx, erSrc.length)
    expect(regBlock).toContain('markerFor')
  })
})

// ---------------------------------------------------------------------------
// Suite 6: Crow's-foot marker names in source
// ---------------------------------------------------------------------------

describe('crow\'s-foot marker IDs present in er.js source', () => {
  it('fd-arr-er-one marker id is present', () => {
    expect(erSrc).toContain('fd-arr-er-one')
  })

  it('fd-arr-er-many marker id is present', () => {
    expect(erSrc).toContain('fd-arr-er-many')
  })

  it('fd-arr-er-zero-or-one marker id is present', () => {
    expect(erSrc).toContain('fd-arr-er-zero-or-one')
  })

  it('fd-arr-er-zero-or-many marker id is present', () => {
    expect(erSrc).toContain('fd-arr-er-zero-or-many')
  })

  it('fd-arr-er-one-or-many marker id is present', () => {
    expect(erSrc).toContain('fd-arr-er-one-or-many')
  })

  it('erMarkerFor maps "one" → fd-arr-er-one', () => {
    // Extract erMarkerFor and verify the mapping works
    const markerForFn = extractFn(erSrc, 'erMarkerFor') as (c: string) => string | null
    expect(markerForFn('one')).toBe('fd-arr-er-one')
  })

  it('erMarkerFor maps "many" → fd-arr-er-many', () => {
    const markerForFn = extractFn(erSrc, 'erMarkerFor') as (c: string) => string | null
    expect(markerForFn('many')).toBe('fd-arr-er-many')
  })

  it('erMarkerFor maps "zero-or-one" → fd-arr-er-zero-or-one', () => {
    const markerForFn = extractFn(erSrc, 'erMarkerFor') as (c: string) => string | null
    expect(markerForFn('zero-or-one')).toBe('fd-arr-er-zero-or-one')
  })

  it('erMarkerFor maps "zero-or-many" → fd-arr-er-zero-or-many', () => {
    const markerForFn = extractFn(erSrc, 'erMarkerFor') as (c: string) => string | null
    expect(markerForFn('zero-or-many')).toBe('fd-arr-er-zero-or-many')
  })

  it('erMarkerFor maps "one-or-many" → fd-arr-er-one-or-many', () => {
    const markerForFn = extractFn(erSrc, 'erMarkerFor') as (c: string) => string | null
    expect(markerForFn('one-or-many')).toBe('fd-arr-er-one-or-many')
  })

  it('erMarkerFor returns null for unrecognised cardinality', () => {
    const markerForFn = extractFn(erSrc, 'erMarkerFor') as (c: string) => string | null
    expect(markerForFn('unknown')).toBeNull()
  })

  it('erMarkerFor returns null for empty string', () => {
    const markerForFn = extractFn(erSrc, 'erMarkerFor') as (c: string) => string | null
    expect(markerForFn('')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Suite 7: buildEngine(FD_DIR, 'er') — glob-discovery and bundle integration
// ---------------------------------------------------------------------------

describe('buildEngine(FD_DIR, "er")', () => {
  it('returns a non-empty bundle string', () => {
    const bundle = buildEngine(FD_DIR, 'er')
    expect(typeof bundle).toBe('string')
    expect(bundle.length).toBeGreaterThan(200)
  })

  it('wraps er output in IIFE', () => {
    const bundle = buildEngine(FD_DIR, 'er')
    const trimmed = bundle.trim()
    expect(trimmed).toMatch(/^\(function\(\)/)
    expect(trimmed).toMatch(/\}\)\(\)$/)
  })

  it('includes core.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'er')
    expect(bundle).toContain('/* ── fd/core.js ── */')
  })

  it('includes er.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'er')
    expect(bundle).toContain('/* ── fd/er.js ── */')
  })

  it('GUARD: er bundle must not contain the banned lowercase token', () => {
    const bundle = buildEngine(FD_DIR, 'er')
    expect(hasBannedToken(bundle)).toBe(false)
  })

  it('er bundle does NOT setAttribute("preserveAspectRatio") (AC-10)', () => {
    const bundle = buildEngine(FD_DIR, 'er')
    expect(bundle).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })

  it('er bundle does NOT contain fetch() (AC-4 file:// safe)', () => {
    const bundle = buildEngine(FD_DIR, 'er')
    expect(bundle).not.toMatch(/\bfetch\s*\(/)
  })
})

// ---------------------------------------------------------------------------
// Suite 8: er.js source — additional AC checks
// ---------------------------------------------------------------------------

describe('er.js source — acceptance criteria checks', () => {
  it('no preserveAspectRatio in source (AC-10)', () => {
    expect(erSrc).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
    expect(erSrc).not.toContain('preserveAspectRatio')
  })

  it('no fetch() calls (AC-4 file:// safe)', () => {
    expect(erSrc).not.toMatch(/\bfetch\s*\(/)
  })

  it('no dynamic import() calls (AC-5 single-file)', () => {
    expect(erSrc).not.toMatch(/\bdynamic import\b/)
    expect(erSrc).not.toMatch(/import\s*\(/)
  })

  it('no elk.bundled reference (elk is gen-time only, never inlined — RD-1)', () => {
    expect(erSrc).not.toContain('elk.bundled')
  })

  it('PK row class fd-er-pk is defined in CSS injection', () => {
    expect(erSrc).toContain('.fd-er-pk')
  })

  it('FK row class fd-er-fk is defined in CSS injection', () => {
    expect(erSrc).toContain('.fd-er-fk')
  })

  it('entity name class fd-er-entity-name is defined', () => {
    expect(erSrc).toContain('.fd-er-entity-name')
  })

  it('attribute row class fd-er-attr is defined', () => {
    expect(erSrc).toContain('.fd-er-attr')
  })

  it('marker stroke class fd-er-mk is defined in CSS injection', () => {
    expect(erSrc).toContain('.fd-er-mk')
  })

  it('fd-er-node width override class is defined (180px per spec)', () => {
    expect(erSrc).toContain('.fd-node.fd-er-node')
    expect(erSrc).toContain('width: 180px')
  })

  it('renderErEntity function is defined', () => {
    expect(erSrc).toMatch(/function renderErEntity\s*\(/)
  })

  it('injectErMarkers function is defined', () => {
    expect(erSrc).toMatch(/function injectErMarkers\s*\(/)
  })

  it('applyErEdgeMarkers function is defined', () => {
    expect(erSrc).toMatch(/function applyErEdgeMarkers\s*\(/)
  })
})
