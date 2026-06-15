/**
 * S8 — forge-chart routing + template deletions + guard-clean.
 *
 * Verifies:
 *  1. forge-chart SKILL.md routing table covers all fd-engine types.
 *  2. Legacy static templates (sequence, state, er, gantt, pie) are DELETED.
 *  3. fd-engine examples exist for all types.
 *  4. Guard: SKILL.md contains zero instances of the banned lowercase token.
 *  5. Routing section structure integrity.
 *
 * Spec ref: artifacts/specs/epic-40-58-js-engine-spec.md §8 Slice S8.
 */

import { existsSync, readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

// Resolve from this test file's location: fd/__tests__/ → graph-templates/
const GRAPH_TEMPLATES_DIR = resolve(import.meta.dirname, '../..')

// SKILL.md lives at: plugins/forge/skills/forge-chart/SKILL.md
// graph-templates/ is under plugins/forge/references/graph-templates/
// Two levels up from graph-templates/ reaches plugins/forge/
const SKILL_MD_PATH = resolve(GRAPH_TEMPLATES_DIR, '../../skills/forge-chart/SKILL.md')

// examples/ is inside graph-templates/
const EXAMPLES_DIR = join(GRAPH_TEMPLATES_DIR, 'examples')

// ---------------------------------------------------------------------------
// Guard token (built via concatenation so this file itself is guard-clean)
// ---------------------------------------------------------------------------

const BANNED = 'mer' + 'maid'
const bannedRe = new RegExp(`\\b${BANNED}\\b`)

// ---------------------------------------------------------------------------
// Suite 1 — SKILL.md routing table covers all fd-engine types
// ---------------------------------------------------------------------------

describe('S8: SKILL.md routing table covers all fd-engine types', () => {
  it('SKILL.md exists', () => {
    expect(existsSync(SKILL_MD_PATH)).toBe(true)
  })

  const FD_TYPES = [
    'architecture',
    'hub-spoke',
    'flowchart',
    'state',
    'class',
    'er',
    'sequence',
    'xychart',
    'gantt',
    'pie',
  ]

  for (const type of FD_TYPES) {
    it(`routing table references fd-engine type "${type}"`, () => {
      const src = readFileSync(SKILL_MD_PATH, 'utf-8')
      // The routing table uses backtick-quoted type values like `type:"flowchart"`
      // or plain type names in table rows — both patterns should be present
      const hasType =
        src.includes(`type:"${type}"`) ||
        src.includes(`"${type}"`) ||
        src.includes(`\`${type}\``)
      expect(hasType).toBe(true)
    })
  }
})

// ---------------------------------------------------------------------------
// Suite 2 — Legacy templates are deleted
// ---------------------------------------------------------------------------

describe('S8: deleted legacy templates are absent', () => {
  const DELETED_TEMPLATES = [
    'sequence.html',
    'state.html',
    'er.html',
    'gantt.html',
    'pie.html',
  ]

  for (const tpl of DELETED_TEMPLATES) {
    it(`${tpl} must NOT exist in graph-templates/ (deleted — replaced by fd-engine)`, () => {
      const p = join(GRAPH_TEMPLATES_DIR, tpl)
      expect(existsSync(p)).toBe(false)
    })
  }

  it('legacy example demos must NOT exist in examples/', () => {
    const deletedExamples = [
      'sequence.html',
      'state.html',
      'er.html',
      'gantt.html',
      'pie.html',
    ]
    for (const ex of deletedExamples) {
      const p = join(EXAMPLES_DIR, ex)
      expect(existsSync(p), `examples/${ex} should have been deleted`).toBe(false)
    }
  })
})

// ---------------------------------------------------------------------------
// Suite 3 — fd-engine example files exist for all types
// ---------------------------------------------------------------------------

describe('S8: fd-engine examples exist', () => {
  const FD_EXAMPLES = [
    'fd-architecture.html',
    'fd-flowchart.html',
    'fd-state.html',
    'fd-class.html',
    'fd-er.html',
    'fd-sequence.html',
    'fd-xychart.html',
    'fd-gantt.html',
    'fd-pie.html',
  ]

  for (const ex of FD_EXAMPLES) {
    it(`${ex} exists in examples/`, () => {
      expect(existsSync(join(EXAMPLES_DIR, ex))).toBe(true)
    })
  }
})

// ---------------------------------------------------------------------------
// Suite 4 — Guard: SKILL.md must not contain the banned lowercase token
// ---------------------------------------------------------------------------

describe('S8: GUARD — SKILL.md is guard-clean (zero banned token)', () => {
  it('SKILL.md does NOT contain the banned lowercase token', () => {
    const src = readFileSync(SKILL_MD_PATH, 'utf-8')
    const matches = src.match(bannedRe)
    if (matches) {
      const idx = src.search(bannedRe)
      const ctx = src.slice(Math.max(0, idx - 40), idx + 60)
      expect(matches, `GUARD VIOLATION — found banned token near: "${ctx}"`).toBeNull()
    }
    expect(bannedRe.test(src)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Suite 5 — SKILL.md routing section structure
// ---------------------------------------------------------------------------

describe('S8: SKILL.md routing section structure', () => {
  it('contains "Type routing table" heading', () => {
    const src = readFileSync(SKILL_MD_PATH, 'utf-8')
    expect(src).toContain('### Type routing table')
  })

  it('contains "Aesthetic → theme mapping" section', () => {
    const src = readFileSync(SKILL_MD_PATH, 'utf-8')
    expect(src).toContain('Aesthetic → theme mapping')
  })

  it('routing table lists bun elk step column', () => {
    const src = readFileSync(SKILL_MD_PATH, 'utf-8')
    expect(src).toContain('bun elk step')
  })

  it('routing section no longer says "Do not route those types to fd-engine yet"', () => {
    const src = readFileSync(SKILL_MD_PATH, 'utf-8')
    expect(src).not.toContain('Do not route those types to fd-engine yet')
  })

  it('AC-10 guard section is present', () => {
    const src = readFileSync(SKILL_MD_PATH, 'utf-8')
    expect(src).toContain('AC-10 guard')
  })
})
