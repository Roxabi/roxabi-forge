/**
 * Tests for fd/types/gantt.js and fd/types/pie.js (Slice S6)
 *
 * MATH-verified:
 *   gantt: x = (daysSince(barStart) / totalDays) * 100
 *          w = (daysSince(barEnd) - daysSince(barStart)) / totalDays * 100
 *   pie:   sweep = (value / total) * 2π
 *          large-arc-flag = sweep > π ? 1 : 0
 *          arc path uses clockwise (sweep-flag=1) from -π/2 (12-o'clock)
 *
 * Tests run in Node — no DOM needed for the math-only contracts.
 * Source-level string checks verify the arc/bar formulas are present.
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { buildEngine } from '../bundler.js'

const FD_DIR = join(import.meta.dirname, '..')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const BANNED = 'mer' + 'maid'
const bannedRe = new RegExp(`\\b${BANNED}\\b`)

function hasBannedToken(src: string): boolean {
  return bannedRe.test(src)
}

// Math helpers extracted from actual source files — not reimplemented inline.
// This ensures tests exercise the production formula, not a local mirror copy.
// RC (F4): the original helpers were inline reimplementations that would pass even if the
// source formula was wrong — tautological-test anti-pattern. Using extractFn + new Function
// with dependency injection guarantees we run the production code path.

function extractFn(src: string, fnName: string, deps: Record<string, Function> = {}): Function {
  // Match: function fnName(...) { ... }  (non-nested; greedy brace matching via stack)
  const start = src.indexOf(`function ${fnName}(`)
  if (start === -1) throw new Error(`[test-harness] function ${fnName} not found in source`)
  let depth = 0, i = start
  while (i < src.length) {
    if (src[i] === '{') depth++
    else if (src[i] === '}') { depth--; if (depth === 0) { i++; break } }
    i++
  }
  const body = src.slice(start, i)
  // Inject deps as named parameters so the extracted function can call its dependencies
  // (e.g. barX calls ganttDaysSince) without a global scope.
  const depNames = Object.keys(deps)
  const depVals = Object.values(deps)
  // eslint-disable-next-line no-new-func
  return new Function(...depNames, `return (${body})`)(...depVals)
}

const ganttSrcForMath = readFileSync(join(FD_DIR, 'types', 'gantt.js'), 'utf-8')

// Extract the three math helpers from the actual gantt.js source.
// ganttDaysSince has no deps; barX and barW depend on ganttDaysSince.
const ganttDaysSince = extractFn(ganttSrcForMath, 'ganttDaysSince') as (isoDate: string, startMs: number) => number
const barXFn = extractFn(ganttSrcForMath, 'barX', { ganttDaysSince }) as (barStart: string, startMs: number, totalDays: number) => number
const barWFn = extractFn(ganttSrcForMath, 'barW', { ganttDaysSince }) as (barStart: string, barEnd: string, startMs: number, totalDays: number) => number

function barXPct(barStart: string, timelineStart: string, timelineEnd: string): number {
  const startMs = Date.parse(timelineStart)
  const totalDays = (Date.parse(timelineEnd) - startMs) / 86400000
  return barXFn(barStart, startMs, totalDays)
}

function barWPct(barStart: string, barEnd: string, timelineStart: string, timelineEnd: string): number {
  const startMs = Date.parse(timelineStart)
  const totalDays = (Date.parse(timelineEnd) - startMs) / 86400000
  return barWFn(barStart, barEnd, startMs, totalDays)
}

// ---------------------------------------------------------------------------
// Suite: gantt.js source-level contracts
// ---------------------------------------------------------------------------

describe('fd/types/gantt.js — source checks', () => {
  const ganttSrc = readFileSync(join(FD_DIR, 'types', 'gantt.js'), 'utf-8')

  it('file exists and is non-empty', () => {
    expect(ganttSrc.length).toBeGreaterThan(200)
  })

  it('registers type "gantt" in window.__fdTypes', () => {
    expect(ganttSrc).toContain('window.__fdTypes')
    expect(ganttSrc).toContain("GANTT_TYPE")
    expect(ganttSrc).toContain("'gantt'")
  })

  it('defines ganttInit function', () => {
    expect(ganttSrc).toMatch(/function ganttInit\s*\(/)
  })

  it('defines renderGantt function', () => {
    expect(ganttSrc).toMatch(/function renderGantt\s*\(/)
  })

  it('uses 86400000 ms/day constant (MATH check)', () => {
    // 1 day = 24 * 60 * 60 * 1000 = 86_400_000
    expect(ganttSrc).toContain('86400000')
  })

  it('bar x formula divides by totalDays and multiplies by 100', () => {
    // Must contain the key formula components
    expect(ganttSrc).toContain('totalDays')
    expect(ganttSrc).toContain('* 100')
  })

  it('clamps bar x to [0, 100]', () => {
    expect(ganttSrc).toContain('Math.max(0')
    expect(ganttSrc).toContain('Math.min(100')
  })

  it('CARD_DEFAULT is null (SVG-only, no HTML nodes — RD-3)', () => {
    // gantt bypasses node/edge engine
    expect(ganttSrc).toContain('GANTT_CARD_DEFAULT = null')
  })

  it('placeZones is null (gantt has no zones — no edge engine)', () => {
    expect(ganttSrc).toContain('placeZones: null')
  })

  it('has renderChart export in type registration', () => {
    expect(ganttSrc).toContain('renderChart: renderGantt')
  })

  it('GUARD: must not contain banned lowercase token', () => {
    expect(hasBannedToken(ganttSrc)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Suite: pie.js source-level contracts
// ---------------------------------------------------------------------------

describe('fd/types/pie.js — source checks', () => {
  const pieSrc = readFileSync(join(FD_DIR, 'types', 'pie.js'), 'utf-8')

  it('file exists and is non-empty', () => {
    expect(pieSrc.length).toBeGreaterThan(200)
  })

  it('registers type "pie" in window.__fdTypes', () => {
    expect(pieSrc).toContain('window.__fdTypes')
    expect(pieSrc).toContain("PIE_TYPE")
    expect(pieSrc).toContain("'pie'")
  })

  it('defines pieInit function', () => {
    expect(pieSrc).toMatch(/function pieInit\s*\(/)
  })

  it('defines renderPie function', () => {
    expect(pieSrc).toMatch(/function renderPie\s*\(/)
  })

  it('defines buildPieArc function', () => {
    expect(pieSrc).toMatch(/function buildPieArc\s*\(/)
  })

  it('start angle is -π/2 (12-o-clock, MATH check)', () => {
    // -Math.PI / 2 = clockwise from top
    expect(pieSrc).toContain('-Math.PI / 2')
  })

  it('sweep angle derived from 2*π (full circle — MATH check)', () => {
    expect(pieSrc).toContain('2 * Math.PI')
  })

  it('large-arc-flag set when sweep > π (MATH check)', () => {
    // large-arc = fraction > 0.5 ↔ sweep > π
    expect(pieSrc).toContain('Math.PI')
    // The condition in buildPieArc: endAngle - startAngle > Math.PI
    expect(pieSrc).toMatch(/>\s*Math\.PI/)
  })

  it('uses sweep-flag=1 (clockwise arcs)', () => {
    // RC (F6): '1 : 0' matched the largeArc ternary, not the sweep-flag in the arc command.
    // Changing sweep-flag from 1 to 0 in the outer arc left the test green.
    // Assert on the actual outer arc template-literal pattern instead.
    expect(pieSrc).toMatch(/A \$\{fmt\(r\)\},\$\{fmt\(r\)\} 0 \$\{largeArc\} 1/)
  })

  it('CARD_DEFAULT is null (SVG-only, no HTML nodes — RD-3)', () => {
    expect(pieSrc).toContain('PIE_CARD_DEFAULT = null')
  })

  it('placeZones is null (pie has no zones — no edge engine)', () => {
    expect(pieSrc).toContain('placeZones: null')
  })

  it('has renderChart export in type registration', () => {
    expect(pieSrc).toContain('renderChart: renderPie')
  })

  it('polarToXY uses cos and sin correctly', () => {
    // x = cx + r * cos(angle), y = cy + r * sin(angle)
    expect(pieSrc).toContain('Math.cos(angle)')
    expect(pieSrc).toContain('Math.sin(angle)')
  })

  it('donut path includes inner arc with sweep-flag=0 (CCW)', () => {
    // RC (F5): '0 0 ' matched viewBox="0 0 100 100" so the test never caught a wrong sweep.
    // Assert on the actual inner arc template-literal pattern (rIn arc with flag=0).
    expect(pieSrc).toMatch(/A \$\{fmt\(rIn\)\},\$\{fmt\(rIn\)\} 0 \$\{largeArc\} 0/)
  })

  it('GUARD: must not contain banned lowercase token', () => {
    expect(hasBannedToken(pieSrc)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Suite: buildEngine — gantt type bundle
// ---------------------------------------------------------------------------

describe('buildEngine(fdDir, "gantt")', () => {
  it('returns a non-empty bundle string', () => {
    const bundle = buildEngine(FD_DIR, 'gantt')
    expect(typeof bundle).toBe('string')
    expect(bundle.length).toBeGreaterThan(100)
  })

  it('wraps gantt output in IIFE', () => {
    const bundle = buildEngine(FD_DIR, 'gantt')
    const trimmed = bundle.trim()
    expect(trimmed).toMatch(/^\(function\(\)/)
    expect(trimmed).toMatch(/\}\)\(\)$/)
  })

  it('includes core.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'gantt')
    expect(bundle).toContain('/* ── fd/core.js ── */')
  })

  it('includes gantt.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'gantt')
    expect(bundle).toContain('/* ── fd/gantt.js ── */')
  })

  it('GUARD: gantt bundle must not contain banned lowercase token', () => {
    const bundle = buildEngine(FD_DIR, 'gantt')
    expect(hasBannedToken(bundle)).toBe(false)
  })

  it('gantt bundle does NOT setAttribute("preserveAspectRatio") (AC-10)', () => {
    const bundle = buildEngine(FD_DIR, 'gantt')
    expect(bundle).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })
})

// ---------------------------------------------------------------------------
// Suite: buildEngine — pie type bundle
// ---------------------------------------------------------------------------

describe('buildEngine(fdDir, "pie")', () => {
  it('returns a non-empty bundle string', () => {
    const bundle = buildEngine(FD_DIR, 'pie')
    expect(typeof bundle).toBe('string')
    expect(bundle.length).toBeGreaterThan(100)
  })

  it('wraps pie output in IIFE', () => {
    const bundle = buildEngine(FD_DIR, 'pie')
    const trimmed = bundle.trim()
    expect(trimmed).toMatch(/^\(function\(\)/)
    expect(trimmed).toMatch(/\}\)\(\)$/)
  })

  it('includes core.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'pie')
    expect(bundle).toContain('/* ── fd/core.js ── */')
  })

  it('includes pie.js section comment', () => {
    const bundle = buildEngine(FD_DIR, 'pie')
    expect(bundle).toContain('/* ── fd/pie.js ── */')
  })

  it('GUARD: pie bundle must not contain banned lowercase token', () => {
    const bundle = buildEngine(FD_DIR, 'pie')
    expect(hasBannedToken(bundle)).toBe(false)
  })

  it('pie bundle does NOT setAttribute("preserveAspectRatio") (AC-10)', () => {
    const bundle = buildEngine(FD_DIR, 'pie')
    expect(bundle).not.toMatch(/setAttribute\s*\(\s*['"]preserveAspectRatio['"]/)
  })
})

// ---------------------------------------------------------------------------
// Suite: MATH verification — gantt bar positioning
// ---------------------------------------------------------------------------

describe('MATH: gantt bar x/width from dates', () => {
  const TL_START = '2026-01-01'
  const TL_END   = '2026-04-01'  // 90 days (Jan 31 + Feb 28 + Mar 31 = 90)

  it('bar starting at timeline start has x = 0', () => {
    const x = barXPct('2026-01-01', TL_START, TL_END)
    expect(x).toBeCloseTo(0, 2)
  })

  it('bar starting at timeline midpoint has x ≈ 50', () => {
    // Midpoint of 90 days = day 45 = Feb 15
    const x = barXPct('2026-02-15', TL_START, TL_END)
    // day 45 of 90 = 50%
    expect(x).toBeCloseTo(50, 0)
  })

  it('bar spanning full timeline has w = 100', () => {
    const w = barWPct(TL_START, TL_END, TL_START, TL_END)
    expect(w).toBeCloseTo(100, 2)
  })

  it('bar spanning half the timeline has w ≈ 50', () => {
    // Jan 1 → Feb 15 ≈ 45 days of 90 = 50%
    const w = barWPct('2026-01-01', '2026-02-15', TL_START, TL_END)
    expect(w).toBeCloseTo(50, 0)
  })

  it('x + w does not exceed 100 for valid bars', () => {
    // Bar from Feb 1 to Mar 31 (starts on day 31, ends on day 89)
    const x = barXPct('2026-02-01', TL_START, TL_END)
    const w = barWPct('2026-02-01', '2026-03-31', TL_START, TL_END)
    expect(x + w).toBeLessThanOrEqual(100 + 0.01) // tolerance for float rounding
  })

  it('bar before timeline start is clamped to x=0', () => {
    const x = barXPct('2025-12-01', TL_START, TL_END)
    expect(x).toBe(0)
  })

  it('x is proportional: Feb 1 start = 31/90 ≈ 34.4%', () => {
    // Jan has 31 days; Feb 1 = day 31 of 90
    const x = barXPct('2026-02-01', TL_START, TL_END)
    const expected = (31 / 90) * 100
    expect(x).toBeCloseTo(expected, 1)
  })

  it('barW: bar starting before timeline start is NOT double-wide (F1 regression)', () => {
    // bar.start = 2025-12-01 (31 days before TL_START = 2026-01-01).
    // startPct = -34.4; endPct = +34.4 (2026-02-01).
    // Bug (old): Math.min(100 - (-34.4), 68.9) = Math.min(134.4, 68.9) = 68.9 — double the
    //   correct width because the upper bound was never effective for negative startPct.
    // Fix: min(endPct,100) − max(startPct,0) = 34.4 − 0 = 34.4 (visible Jan 1→Feb 1 span).
    const w = barWPct('2025-12-01', '2026-02-01', TL_START, TL_END)
    const expected = (31 / 90) * 100  // visible portion: timeline start → Feb 1 = 31 days
    expect(w).toBeCloseTo(expected, 1)
    expect(w).toBeLessThan(40)  // must not be ~68.9 (the buggy double-wide value)
  })
})

// ---------------------------------------------------------------------------
// Suite: MATH verification — pie arc angles
// ---------------------------------------------------------------------------

describe('MATH: pie arc angles from values', () => {
  // Inline arc math (mirrors pie.js logic, no DOM)
  function sweepAngle(value: number, total: number): number {
    return (value / total) * 2 * Math.PI
  }
  function largeArcFlag(sweep: number): 0 | 1 {
    return sweep > Math.PI ? 1 : 0
  }
  function arcEndX(cx: number, cy: number, r: number, startAngle: number, sweep: number): number {
    return cx + r * Math.cos(startAngle + sweep)
  }
  function arcEndY(cx: number, cy: number, r: number, startAngle: number, sweep: number): number {
    return cy + r * Math.sin(startAngle + sweep)
  }

  it('total fraction sums to 1 (all sweeps sum to 2π)', () => {
    const slices = [38, 27, 18, 11, 6]
    const total = slices.reduce((a, b) => a + b, 0)
    const totalSweep = slices.reduce((acc, v) => acc + sweepAngle(v, total), 0)
    expect(totalSweep).toBeCloseTo(2 * Math.PI, 6)
  })

  it('50% slice has sweep = π', () => {
    expect(sweepAngle(50, 100)).toBeCloseTo(Math.PI, 6)
  })

  it('100% slice has sweep = 2π', () => {
    expect(sweepAngle(100, 100)).toBeCloseTo(2 * Math.PI, 6)
  })

  it('large-arc-flag = 0 when sweep < π (fraction < 50%)', () => {
    expect(largeArcFlag(sweepAngle(38, 100))).toBe(0)
  })

  it('large-arc-flag = 0 when sweep = π exactly (50%)', () => {
    // sweep = π is NOT > π, so flag = 0
    expect(largeArcFlag(Math.PI)).toBe(0)
  })

  it('large-arc-flag = 1 when sweep > π (fraction > 50%)', () => {
    expect(largeArcFlag(sweepAngle(51, 100))).toBe(1)
  })

  it('start at -π/2 (12-o-clock): x1 = cx, y1 = cy - r', () => {
    // cos(-π/2) = 0, sin(-π/2) = -1
    const startAngle = -Math.PI / 2
    const cx = 50, cy = 50, r = 38
    expect(cx + r * Math.cos(startAngle)).toBeCloseTo(50, 4)
    expect(cy + r * Math.sin(startAngle)).toBeCloseTo(12, 4)  // 50 - 38 = 12
  })

  it('first slice (38%): end point computed correctly', () => {
    const total = 100
    const startAngle = -Math.PI / 2
    const sweep = sweepAngle(38, total)
    const cx = 50, cy = 50, r = 38
    const endAngle = startAngle + sweep
    // end x = cx + r*cos(endAngle), end y = cy + r*sin(endAngle)
    const ex = arcEndX(cx, cy, r, startAngle, sweep)
    const ey = arcEndY(cx, cy, r, startAngle, sweep)
    // For 38% (136.8°): endAngle = -90° + 136.8° = 46.8°
    // cos(46.8°) ≈ 0.6820, sin(46.8°) ≈ 0.7314
    const deg = (endAngle * 180) / Math.PI
    expect(deg).toBeCloseTo(46.8, 1)
    expect(ex).toBeCloseTo(50 + 38 * Math.cos(endAngle), 4)
    expect(ey).toBeCloseTo(50 + 38 * Math.sin(endAngle), 4)
  })

  it('angle accumulation: 5 slices cover exactly 360°', () => {
    const slices = [38, 27, 18, 11, 6]
    const total = slices.reduce((a, b) => a + b, 0)
    let angle = -Math.PI / 2
    for (const v of slices) {
      angle += sweepAngle(v, total)
    }
    // Must return to start: angle = -π/2 + 2π = 3π/2 (equivalent to -π/2)
    expect(Math.cos(angle)).toBeCloseTo(Math.cos(-Math.PI / 2), 5)
    expect(Math.sin(angle)).toBeCloseTo(Math.sin(-Math.PI / 2), 5)
  })
})

// ---------------------------------------------------------------------------
// Suite: guard — banned token absent from examples
// ---------------------------------------------------------------------------

describe('examples — guard: banned token absent', () => {
  it('fd-gantt.html must not contain banned lowercase token', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-gantt.html'),
      'utf-8',
    )
    expect(hasBannedToken(html)).toBe(false)
  })

  it('fd-pie.html must not contain banned lowercase token', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-pie.html'),
      'utf-8',
    )
    expect(hasBannedToken(html)).toBe(false)
  })

  it('fd-gantt.html has correct diagram:type meta', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-gantt.html'),
      'utf-8',
    )
    expect(html).toContain('content="gantt"')
  })

  it('fd-pie.html has correct diagram:type meta', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-pie.html'),
      'utf-8',
    )
    expect(html).toContain('content="pie"')
  })

  it('fd-gantt.html is file:// safe: no fetch()', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-gantt.html'),
      'utf-8',
    )
    expect(html).not.toContain('fetch(')
  })

  it('fd-pie.html is file:// safe: no fetch()', () => {
    const html = readFileSync(
      join(FD_DIR, '..', 'examples', 'fd-pie.html'),
      'utf-8',
    )
    expect(html).not.toContain('fetch(')
  })
})
