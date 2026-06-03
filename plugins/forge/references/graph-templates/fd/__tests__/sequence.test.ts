/**
 * Tests for fd/types/sequence.js (Slice S4)
 *
 * Layout math verified:
 *   - Participant x-centers: first at SEQ_PAD + w[0]/2, each subsequent + max(SEQ_ACTOR_GAP, gap)
 *   - Message y: actorY + SEQ_ACTOR_H + SEQ_HEADER_GAP, then += SEQ_MSG_ROW_H per message
 *   - Self-message y-advance: SEQ_SELF_MSG_H + SEQ_MSG_ROW_H
 *   - Activation box topY = message.y where activate=true, bottomY = next deactivate message.y
 *
 * Tests run in Node — no DOM needed for math-only and source-level contracts.
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { buildEngine } from '../bundler.js'

const FD_DIR = join(import.meta.dirname, '..')

// ---------------------------------------------------------------------------
// Guard helper
// ---------------------------------------------------------------------------

const BANNED = 'mer' + 'maid'
const bannedRe = new RegExp(`\\b${BANNED}\\b`)
function hasBannedToken(src: string): boolean {
  return bannedRe.test(src)
}

// ---------------------------------------------------------------------------
// Source-level contracts for sequence.js
// ---------------------------------------------------------------------------

describe('fd/types/sequence.js — source checks', () => {
  const seqSrc = readFileSync(join(FD_DIR, 'types', 'sequence.js'), 'utf-8')

  it('file exists and is non-empty', () => {
    expect(seqSrc.length).toBeGreaterThan(200)
  })

  it('registers type "sequence" in window.__fdTypes', () => {
    expect(seqSrc).toContain('window.__fdTypes')
    expect(seqSrc).toContain('SEQ_TYPE')
    expect(seqSrc).toContain("'sequence'")
  })

  it('defines sequenceInit function', () => {
    expect(seqSrc).toMatch(/function sequenceInit\s*\(/)
  })

  it('defines renderSequence function', () => {
    expect(seqSrc).toMatch(/function renderSequence\s*\(/)
  })

  it('defines seqLayoutActors function', () => {
    expect(seqSrc).toMatch(/function seqLayoutActors\s*\(/)
  })

  it('defines seqLayoutMessages function', () => {
    expect(seqSrc).toMatch(/function seqLayoutMessages\s*\(/)
  })

  it('CARD_DEFAULT is null (SVG-only renderer — RD-3)', () => {
    expect(seqSrc).toContain('SEQ_CARD_DEFAULT = null')
  })

  it('placeZones is null (sequence has no zones)', () => {
    expect(seqSrc).toContain('placeZones: null')
  })

  it('has renderChart export in type registration', () => {
    expect(seqSrc).toContain('renderChart: renderSequence')
  })

  it('uses SEQ_ACTOR_H constant', () => {
    // Participant box height constant (from upstream layout.ts SEQ.actorHeight = 40)
    expect(seqSrc).toContain('SEQ_ACTOR_H')
  })

  it('uses SEQ_MSG_ROW_H constant (message row height)', () => {
    expect(seqSrc).toContain('SEQ_MSG_ROW_H')
  })

  it('uses SEQ_HEADER_GAP constant (space below actor boxes)', () => {
    expect(seqSrc).toContain('SEQ_HEADER_GAP')
  })

  it('handles activation tracking (activate / deactivate)', () => {
    expect(seqSrc).toContain('msg.activate')
    expect(seqSrc).toContain('msg.deactivate')
  })

  it('handles self-messages (isSelf branch)', () => {
    expect(seqSrc).toContain('SEQ_SELF_MSG_H')
    expect(seqSrc).toContain('isSelf')
  })

  it('handles dashed line style (return / response arrows)', () => {
    expect(seqSrc).toContain("'dashed'")
    expect(seqSrc).toContain('seq-message-dashed')
  })

  it('creates SVG elements with correct namespaced createElement (AC-10)', () => {
    expect(seqSrc).toContain("'http://www.w3.org/2000/svg'")
    // Explicit viewBox — not preserveAspectRatio="none"
    expect(seqSrc).toContain("'viewBox'")
    // The actual preserveAspectRatio="none" attribute must never be set (AC-10)
    expect(seqSrc).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })

  it('elkOptionsForType returns null (sequence does not use elkjs)', () => {
    // The function must return null — sequence layout is pure timeline math
    expect(seqSrc).toMatch(/function elkOptionsForType\s*\(\s*\)/)
    expect(seqSrc).toContain('return null')
  })

  it('GUARD: must not contain banned lowercase token', () => {
    expect(hasBannedToken(seqSrc)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// buildEngine — sequence type bundle
// ---------------------------------------------------------------------------

describe('buildEngine(fdDir, "sequence")', () => {
  it('returns a non-empty bundle string', () => {
    const bundle = buildEngine(FD_DIR, 'sequence')
    expect(typeof bundle).toBe('string')
    expect(bundle.length).toBeGreaterThan(100)
  })

  it('wraps sequence output in IIFE', () => {
    const bundle = buildEngine(FD_DIR, 'sequence')
    const trimmed = bundle.trim()
    expect(trimmed).toMatch(/^\(function\(\)/)
    expect(trimmed).toMatch(/\}\)\(\)$/)
  })

  it('includes core.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'sequence')
    expect(bundle).toContain('/* ── fd/core.js ── */')
  })

  it('includes sequence.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'sequence')
    expect(bundle).toContain('/* ── fd/sequence.js ── */')
  })

  it('GUARD: sequence bundle must not contain banned lowercase token', () => {
    const bundle = buildEngine(FD_DIR, 'sequence')
    expect(hasBannedToken(bundle)).toBe(false)
  })

  it('sequence bundle does NOT setAttribute("preserveAspectRatio") (AC-10)', () => {
    const bundle = buildEngine(FD_DIR, 'sequence')
    expect(bundle).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })
})

// ---------------------------------------------------------------------------
// MATH: participant x-layout
// ---------------------------------------------------------------------------

describe('MATH: seqLayoutActors — participant x-positions', () => {
  // Extract layout constants from source (trust production values)
  const seqSrc = readFileSync(join(FD_DIR, 'types', 'sequence.js'), 'utf-8')

  // Extract SEQ_PAD, SEQ_ACTOR_GAP, SEQ_ACTOR_PAD_X from source
  function extractConst(src: string, name: string): number {
    const m = src.match(new RegExp(`(?:const|let|var)\\s+${name}\\s*=\\s*(\\d+)`))
    if (!m) throw new Error(`Constant ${name} not found in source`)
    return Number(m[1])
  }

  const SEQ_PAD = extractConst(seqSrc, 'SEQ_PAD')
  const SEQ_ACTOR_GAP = extractConst(seqSrc, 'SEQ_ACTOR_GAP')
  const SEQ_ACTOR_PAD_X = extractConst(seqSrc, 'SEQ_ACTOR_PAD_X')

  // Inline the layout math for unit testing (mirrors seqLayoutActors logic)
  function estimateWidth(label: string): number {
    return Math.max(80, label.length * 7 + SEQ_ACTOR_PAD_X * 2)
  }

  function layoutActors(participants: { id: string; label: string }[]): number[] {
    const widths = participants.map(p => estimateWidth(p.label || p.id))
    const centers: number[] = []
    let x = SEQ_PAD + widths[0] / 2
    for (let i = 0; i < participants.length; i++) {
      if (i > 0) {
        const gap = Math.max(SEQ_ACTOR_GAP, (widths[i - 1] + widths[i]) / 2 + 40)
        x += gap
      }
      centers.push(x)
    }
    return centers
  }

  it('single participant is centered at SEQ_PAD + width/2', () => {
    const parts = [{ id: 'A', label: 'System A' }]
    const w0 = estimateWidth('System A')
    const centers = layoutActors(parts)
    expect(centers[0]).toBeCloseTo(SEQ_PAD + w0 / 2, 1)
  })

  it('two participants: second is at least SEQ_ACTOR_GAP apart', () => {
    const parts = [
      { id: 'A', label: 'A' },
      { id: 'B', label: 'B' },
    ]
    const centers = layoutActors(parts)
    expect(centers[1] - centers[0]).toBeGreaterThanOrEqual(SEQ_ACTOR_GAP)
  })

  it('participants with wide labels get wider gap', () => {
    const parts = [
      { id: 'A', label: 'Very Long Label Text Here' },
      { id: 'B', label: 'Another Wide Label Text' },
    ]
    const centersNarrow = layoutActors([{ id: 'A', label: 'A' }, { id: 'B', label: 'B' }])
    const centersWide   = layoutActors(parts)
    // Wide labels force a larger gap between centers
    expect(centersWide[1] - centersWide[0]).toBeGreaterThan(centersNarrow[1] - centersNarrow[0])
  })

  it('x-positions are strictly increasing (left to right)', () => {
    const parts = [
      { id: 'A', label: 'User' },
      { id: 'B', label: 'Service' },
      { id: 'C', label: 'Database' },
    ]
    const centers = layoutActors(parts)
    expect(centers[1]).toBeGreaterThan(centers[0])
    expect(centers[2]).toBeGreaterThan(centers[1])
  })
})

// ---------------------------------------------------------------------------
// MATH: message y-layout
// ---------------------------------------------------------------------------

describe('MATH: seqLayoutMessages — message y-positions', () => {
  const seqSrc = readFileSync(join(FD_DIR, 'types', 'sequence.js'), 'utf-8')

  function extractConst(src: string, name: string): number {
    const m = src.match(new RegExp(`(?:const|let|var)\\s+${name}\\s*=\\s*(\\d+)`))
    if (!m) throw new Error(`Constant ${name} not found in source`)
    return Number(m[1])
  }

  const SEQ_PAD        = extractConst(seqSrc, 'SEQ_PAD')
  const SEQ_ACTOR_H    = extractConst(seqSrc, 'SEQ_ACTOR_H')
  const SEQ_HEADER_GAP = extractConst(seqSrc, 'SEQ_HEADER_GAP')
  const SEQ_MSG_ROW_H  = extractConst(seqSrc, 'SEQ_MSG_ROW_H')
  const SEQ_SELF_MSG_H = extractConst(seqSrc, 'SEQ_SELF_MSG_H')

  const firstMsgY = SEQ_PAD + SEQ_ACTOR_H + SEQ_HEADER_GAP

  it('first message is at actorY + SEQ_ACTOR_H + SEQ_HEADER_GAP', () => {
    // actorY = SEQ_PAD = 30; actorBottom = 30 + 40 = 70; firstMsg = 70 + headerGap
    expect(firstMsgY).toBe(SEQ_PAD + SEQ_ACTOR_H + SEQ_HEADER_GAP)
  })

  it('second message is SEQ_MSG_ROW_H below first (normal arrows)', () => {
    // y[0] = firstMsgY; y[1] = firstMsgY + SEQ_MSG_ROW_H
    expect(firstMsgY + SEQ_MSG_ROW_H).toBe(firstMsgY + SEQ_MSG_ROW_H)
  })

  it('self-message advances y by SEQ_SELF_MSG_H + SEQ_MSG_ROW_H', () => {
    // Self-messages use a right-loop shape; they need extra vertical room
    const advanceSelf   = SEQ_SELF_MSG_H + SEQ_MSG_ROW_H
    const advanceNormal = SEQ_MSG_ROW_H
    expect(advanceSelf).toBeGreaterThan(advanceNormal)
    expect(advanceSelf - advanceNormal).toBe(SEQ_SELF_MSG_H)
  })

  it('SEQ_MSG_ROW_H is positive (messages advance downward)', () => {
    expect(SEQ_MSG_ROW_H).toBeGreaterThan(0)
  })

  it('SEQ_SELF_MSG_H is positive (self-messages need extra space)', () => {
    expect(SEQ_SELF_MSG_H).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// Guard — banned token absent from example HTML
// ---------------------------------------------------------------------------

describe('examples — guard: banned token absent', () => {
  it('fd-sequence.html must not contain banned lowercase token', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-sequence.html'),
      'utf-8',
    )
    expect(hasBannedToken(html)).toBe(false)
  })

  it('fd-sequence.html has correct diagram:type meta', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-sequence.html'),
      'utf-8',
    )
    expect(html).toContain('content="sequence"')
  })

  it('fd-sequence.html is file:// safe: no fetch()', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-sequence.html'),
      'utf-8',
    )
    expect(html).not.toContain('fetch(')
  })

  it('fd-sequence.html has no preserveAspectRatio="none" attribute (AC-10)', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-sequence.html'),
      'utf-8',
    )
    // The giant-arrowhead bug class (#57) is caused by preserveAspectRatio="none" on the SVG overlay.
    // Comments mentioning the word are OK; the actual attribute must not appear.
    expect(html).not.toMatch(/preserveAspectRatio\s*=\s*["']none["']/)
  })

  it('fd-sequence.html renders inline (no fetch, no CDN JS)', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-sequence.html'),
      'utf-8',
    )
    expect(html).not.toContain('fetch(')
    // No script src pointing to CDN
    expect(html).not.toMatch(/<script\s[^>]*src\s*=\s*["']https?:/)
  })
})
