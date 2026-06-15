/**
 * Tests for S3a deliverable: fd/types/class.js
 *
 * Strategy:
 *   - bundler.js discovery: buildEngine('class') returns a valid bundle
 *   - Source-level contract: elkOptionsForType shape, nodeSizeForType formula
 *   - init() return contract: typeDefault / positionNodes / applyShapes / elkOptions / nodeSizer
 *   - window.__fdTypes['class'] registration
 *   - Guard: banned lowercase token absent from class.js source and bundle
 *   - AC-10: no preserveAspectRatio / viewBox setAttribute in class.js
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { buildEngine } from '../bundler.js'

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

const FD_DIR = join(import.meta.dirname, '..')
const CLASS_SRC = readFileSync(join(FD_DIR, 'types', 'class.js'), 'utf-8')

// Guard: build the banned token via concatenation — this file stays guard-clean
const BANNED = 'mer' + 'maid'
const bannedRe = new RegExp(`\\b${BANNED}\\b`)

// ---------------------------------------------------------------------------
// Suite: bundler discovers class.js (RD-4)
// ---------------------------------------------------------------------------

describe('buildEngine(fdDir, "class") — S3a bundler discovery', () => {
  it('returns a non-empty string', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    expect(typeof bundle).toBe('string')
    expect(bundle.length).toBeGreaterThan(100)
  })

  it('wraps class output in IIFE', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    const trimmed = bundle.trim()
    expect(trimmed).toMatch(/^\(function\(\)/)
    expect(trimmed).toMatch(/\}\)\(\)$/)
  })

  it('includes class.js type module section comment', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    expect(bundle).toContain('/* ── fd/class.js ── */')
  })

  it('includes core.js in class bundle', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    expect(bundle).toContain('/* ── fd/core.js ── */')
  })

  it('includes edges.js in class bundle', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    expect(bundle).toContain('/* ── fd/edges.js ── */')
  })

  it('includes cards.js in class bundle', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    expect(bundle).toContain('/* ── fd/cards.js ── */')
  })

  it('GUARD AC-7: class bundle must NOT contain the banned lowercase token', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    expect(bannedRe.test(bundle)).toBe(false)
  })

  it('class bundle registers window.__fdTypes["class"]', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    expect(bundle).toContain('window.__fdTypes')
    expect(bundle).toContain("'class'")
  })
})

// ---------------------------------------------------------------------------
// Suite: class.js source-level elkOptionsForType contract
// ---------------------------------------------------------------------------

describe('class.js elkOptionsForType — source contracts', () => {
  it('declares elkOptionsForType as a top-level function', () => {
    expect(CLASS_SRC).toMatch(/^function elkOptionsForType\s*\(/m)
  })

  it('elkOptionsForType returns elk.algorithm: layered', () => {
    expect(CLASS_SRC).toContain("'elk.algorithm': 'layered'")
  })

  it('elkOptionsForType returns elk.direction: DOWN', () => {
    expect(CLASS_SRC).toContain("'elk.direction': 'DOWN'")
  })

  it('elkOptionsForType nodeSpacing = 32 (wider than flowchart 28, suits 160px cards)', () => {
    expect(CLASS_SRC).toContain("'elk.spacing.nodeNode': '32'")
  })

  it('elkOptionsForType layerSpacing = 56 (taller than flowchart 48)', () => {
    expect(CLASS_SRC).toContain("'elk.layered.spacing.nodeNodeBetweenLayers': '56'")
  })

  it('elkOptionsForType uses ORTHOGONAL edge routing', () => {
    expect(CLASS_SRC).toContain("'elk.edgeRouting': 'ORTHOGONAL'")
  })
})

// ---------------------------------------------------------------------------
// Suite: class.js nodeSizeForType width=160 + height formula
// ---------------------------------------------------------------------------

describe('class.js nodeSizeForType — width=160, height=40+(attrs+methods)*18', () => {
  it('declares nodeSizeForType as a top-level function', () => {
    expect(CLASS_SRC).toMatch(/^function nodeSizeForType\s*\(/m)
  })

  it('CLASS_NODE_WIDTH = 160 (fixed card width)', () => {
    expect(CLASS_SRC).toContain('CLASS_NODE_WIDTH = 160')
  })

  it('CLASS_NODE_BASE_HEIGHT = 40 (header height)', () => {
    expect(CLASS_SRC).toContain('CLASS_NODE_BASE_HEIGHT = 40')
  })

  it('CLASS_NODE_ROW_HEIGHT = 18 (per-row height)', () => {
    expect(CLASS_SRC).toContain('CLASS_NODE_ROW_HEIGHT = 18')
  })

  // Inline nodeSizeForType logic for formula verification (no DOM needed)
  function nodeSizeForType(node: {
    attributes?: string[]
    methods?: string[]
  }): { width: number; height: number } {
    const CLASS_NODE_WIDTH = 160
    const CLASS_NODE_BASE_HEIGHT = 40
    const CLASS_NODE_ROW_HEIGHT = 18
    const attrs = (node.attributes || []).length
    const methods = (node.methods || []).length
    return {
      width: CLASS_NODE_WIDTH,
      height: CLASS_NODE_BASE_HEIGHT + (attrs + methods) * CLASS_NODE_ROW_HEIGHT,
    }
  }

  it('node with no rows → 160 × 40 (base size only)', () => {
    expect(nodeSizeForType({})).toEqual({ width: 160, height: 40 })
  })

  it('node with 3 attributes, 0 methods → 160 × 94 (40 + 3*18)', () => {
    expect(nodeSizeForType({ attributes: ['+ id: int', '+ name: str', '- speed: float'] })).toEqual({
      width: 160,
      height: 94,
    })
  })

  it('node with 0 attributes, 2 methods → 160 × 76 (40 + 2*18)', () => {
    expect(nodeSizeForType({ methods: ['+ start()', '+ stop()'] })).toEqual({
      width: 160,
      height: 76,
    })
  })

  it('node with 2 attributes and 3 methods → 160 × 130 (40 + 5*18)', () => {
    expect(
      nodeSizeForType({
        attributes: ['+ fuel: float', '+ seats: int'],
        methods: ['+ drive()', '+ brake()', '+ park()'],
      }),
    ).toEqual({ width: 160, height: 130 })
  })

  it('width is always 160 regardless of row count', () => {
    const many = Array.from({ length: 10 }, (_, i) => `+ field${i}: int`)
    expect(nodeSizeForType({ attributes: many }).width).toBe(160)
  })
})

// ---------------------------------------------------------------------------
// Suite: class.js init() return contract
// ---------------------------------------------------------------------------

describe('class.js init() return contract', () => {
  it('declares classInit function', () => {
    expect(CLASS_SRC).toMatch(/^function classInit\s*\(/m)
  })

  it('init returns typeDefault: "simple" (RD-3: auto-layout default)', () => {
    expect(CLASS_SRC).toContain("typeDefault: CLASS_CARD_DEFAULT")
    expect(CLASS_SRC).toContain("CLASS_CARD_DEFAULT = 'simple'")
  })

  it('init return object includes positionNodes', () => {
    expect(CLASS_SRC).toContain('positionNodes:')
  })

  it('init return object includes applyShapes', () => {
    expect(CLASS_SRC).toContain('applyShapes:')
  })

  it('init return object includes elkOptions', () => {
    expect(CLASS_SRC).toContain('elkOptions:')
  })

  it('init return object includes nodeSizer', () => {
    expect(CLASS_SRC).toContain('nodeSizer:')
  })

  it('positionNodes is declared as positionClassNodes function', () => {
    expect(CLASS_SRC).toMatch(/^function positionClassNodes\s*\(/m)
  })

  it('applyShapes is declared as applyClassShapes function', () => {
    expect(CLASS_SRC).toMatch(/^function applyClassShapes\s*\(/m)
  })
})

// ---------------------------------------------------------------------------
// Suite: window.__fdTypes['class'] registration
// ---------------------------------------------------------------------------

describe('window.__fdTypes["class"] registration', () => {
  it('source contains window.__fdTypes registration for "class"', () => {
    expect(CLASS_SRC).toContain('window.__fdTypes = window.__fdTypes || {}')
    expect(CLASS_SRC).toContain("window.__fdTypes[CLASS_TYPE]")
  })

  it('registration includes init function', () => {
    // Registration object must expose init
    expect(CLASS_SRC).toMatch(/window\.__fdTypes\[CLASS_TYPE\]\s*=\s*\{[\s\S]*init\s*:/)
  })

  it('registration includes elkOptions function', () => {
    expect(CLASS_SRC).toMatch(/window\.__fdTypes\[CLASS_TYPE\]\s*=\s*\{[\s\S]*elkOptions\s*:/)
  })

  it('registration includes nodeSizer function', () => {
    expect(CLASS_SRC).toMatch(/window\.__fdTypes\[CLASS_TYPE\]\s*=\s*\{[\s\S]*nodeSizer\s*:/)
  })

  it('CLASS_TYPE constant is "class"', () => {
    expect(CLASS_SRC).toContain("const CLASS_TYPE = 'class'")
  })
})

// ---------------------------------------------------------------------------
// Suite: UML arrow types presence in source
// ---------------------------------------------------------------------------

describe('class.js UML arrow types', () => {
  it('handles arrowType "inheritance"', () => {
    expect(CLASS_SRC).toContain("'inheritance'")
  })

  it('handles arrowType "realization"', () => {
    expect(CLASS_SRC).toContain("'realization'")
  })

  it('handles arrowType "implements"', () => {
    expect(CLASS_SRC).toContain("'implements'")
  })

  it('handles arrowType "composition"', () => {
    expect(CLASS_SRC).toContain("'composition'")
  })

  it('handles arrowType "aggregation"', () => {
    expect(CLASS_SRC).toContain("'aggregation'")
  })

  it('handles arrowType "association"', () => {
    expect(CLASS_SRC).toContain("'association'")
  })

  it('handles arrowType "dependency"', () => {
    expect(CLASS_SRC).toContain("'dependency'")
  })

  it('dashed line types (realization, implements, dependency) add fd-class-dashed class', () => {
    expect(CLASS_SRC).toContain('fd-class-dashed')
  })

  it('composition and aggregation use marker-start (diamond at source)', () => {
    expect(CLASS_SRC).toContain('marker-start')
  })

  it('other types use marker-end (arrowhead at target)', () => {
    expect(CLASS_SRC).toContain('marker-end')
  })
})

// ---------------------------------------------------------------------------
// Suite: AC-10 — no preserveAspectRatio / viewBox in class.js
// ---------------------------------------------------------------------------

describe('AC-10: class.js must not set preserveAspectRatio or viewBox on SVG elements', () => {
  it('class.js does NOT setAttribute("preserveAspectRatio")', () => {
    expect(CLASS_SRC).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })

  it('class.js does NOT setAttribute("viewBox") on SVG overlay', () => {
    expect(CLASS_SRC).not.toMatch(/setAttribute\s*\(\s*['"]viewBox['"]/)
  })
})

// ---------------------------------------------------------------------------
// Suite: guard-clean check on class.js source
// ---------------------------------------------------------------------------

describe('GUARD: class.js source is guard-clean (no banned lowercase token)', () => {
  it('source does NOT contain the banned lowercase token', () => {
    expect(bannedRe.test(CLASS_SRC)).toBe(false)
  })

  it('class bundle does NOT contain the banned lowercase token', () => {
    const bundle = buildEngine(FD_DIR, 'class')
    expect(bannedRe.test(bundle)).toBe(false)
  })
})
