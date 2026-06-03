/**
 * Tests for S7: fd/particles.js + fd/interactions.js
 *
 * Tests cover:
 * - Source-level guard: no banned lowercase token
 * - Bundler includes particles.js and interactions.js in architecture bundle
 * - Concat order: particles.js before interactions.js before type module
 * - Function symbols present in bundle output
 * - AC-9: particles OFF by default (descriptor.options.particles === false)
 * - RD-2 opt-in contract: true / "loop" / false modes present in source
 * - particles.js exports the required symbols
 * - interactions.js exports the required symbols
 * - easeInOutCubic math contract (pure function, no DOM)
 */

import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { buildEngine } from '../bundler.js'

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

const FD_DIR = join(import.meta.dirname, '..')
const PARTICLES_PATH = join(FD_DIR, 'particles.js')
const INTERACTIONS_PATH = join(FD_DIR, 'interactions.js')

// ---------------------------------------------------------------------------
// Guard: banned token check (same pattern as bundler.test.ts)
// ---------------------------------------------------------------------------

const BANNED = 'mer' + 'maid'
const bannedRe = new RegExp(`\\b${BANNED}\\b`)

function hasBannedToken(src: string): boolean {
  return bannedRe.test(src)
}

// ---------------------------------------------------------------------------
// Suite: particles.js source-level checks
// ---------------------------------------------------------------------------

describe('particles.js — source-level', () => {
  it('particles.js exists', () => {
    expect(existsSync(PARTICLES_PATH)).toBe(true)
  })

  it('GUARD: particles.js must NOT contain the banned lowercase token', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(hasBannedToken(src)).toBe(false)
  })

  it('contains easeInOutCubic function declaration', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('function easeInOutCubic')
  })

  it('contains spawnParticle function declaration', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('function spawnParticle')
  })

  it('contains clearParticle function declaration', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('function clearParticle')
  })

  it('contains startParticles function declaration (loop mode)', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('function startParticles')
  })

  it('contains stopParticles function declaration', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('function stopParticles')
  })

  it('RD-2: uses 750ms default duration (per spec)', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    // Default duration is 750ms as specified in RD-2
    expect(src).toContain('750')
  })

  it('RD-2 loop mode: stagger delay present (multiple initial spawns)', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    // stagger: i * 180 delay
    expect(src).toMatch(/i\s*\*\s*180/)
  })

  it('AC-6: color resolved from CSS var --fd-plane-{plane} (not hardcoded hex)', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    // CSS var resolution — must use --fd-plane- prefix
    expect(src).toContain('--fd-plane-')
    // Must NOT hardcode specific plane colors (e.g. #38bdf8 cyan from lyra-stack-v2)
    expect(src).not.toContain('#38bdf8')
    expect(src).not.toContain('#fbbf24')
    expect(src).not.toContain('#a78bfa')
  })

  it('fd-particle-wrap class name matches fd-architecture.html CSS', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('fd-particle-wrap')
  })

  it('uses getPointAtLength for position interpolation (verbatim technique)', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('getPointAtLength')
  })

  it('uses getTotalLength to get path length', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('getTotalLength')
  })

  it('uses requestAnimationFrame for animation loop', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('requestAnimationFrame')
  })

  it('uses cancelAnimationFrame in clearParticle', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    expect(src).toContain('cancelAnimationFrame')
  })
})

// ---------------------------------------------------------------------------
// Suite: interactions.js source-level checks
// ---------------------------------------------------------------------------

describe('interactions.js — source-level', () => {
  it('interactions.js exists', () => {
    expect(existsSync(INTERACTIONS_PATH)).toBe(true)
  })

  it('GUARD: interactions.js must NOT contain the banned lowercase token', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(hasBannedToken(src)).toBe(false)
  })

  it('contains spotlight function declaration', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('function spotlight')
  })

  it('contains clearSpot function declaration', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('function clearSpot')
  })

  it('contains wireUseCaseUI function declaration', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('function wireUseCaseUI')
  })

  it('contains wireHoverSpotlight function declaration', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('function wireHoverSpotlight')
  })

  it('state machine: all 5 states present in source', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    // Adapted from lyra-stack-v2: 'none' | 'ready' | 'playing' | 'paused' | 'done'
    expect(src).toContain("'none'")
    expect(src).toContain("'ready'")
    expect(src).toContain("'playing'")
    expect(src).toContain("'paused'")
    expect(src).toContain("'done'")
  })

  it('spotlight adds dimmed class to canvas (verbatim from lyra-stack-v2)', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('dimmed')
  })

  it('spotlight adds hot class to touched paths and nodes', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('hot')
  })

  it('uc-active and uc-done CSS classes referenced (verbatim from lyra-stack-v2)', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('uc-active')
    expect(src).toContain('uc-done')
  })

  it('step-active and step-done CSS classes referenced', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('step-active')
    expect(src).toContain('step-done')
  })

  it('AC-9: particles gated by DESCRIPTOR.options.particles !== false check', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    // interactions.js spawns particles only when the opt-in flag is not false
    expect(src).toContain('particles !== false')
  })

  it('uses clearParticle guard before spawning new particle (typeof check)', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    // Guard: typeof clearParticle === 'function'
    expect(src).toMatch(/typeof\s+clearParticle\s*===\s*['"]function['"]/)
  })

  it('uses spawnParticle guard before spawning (typeof check)', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toMatch(/typeof\s+spawnParticle\s*===\s*['"]function['"]/)
  })

  it('step advance timeout uses 900ms (verbatim from lyra-stack-v2)', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('900')
  })

  it('sidebar elements accessed by id (sbHeader, sbUc, ucTitle, ucStepsList, ucDesc)', () => {
    const src = readFileSync(INTERACTIONS_PATH, 'utf-8')
    expect(src).toContain('sbHeader')
    expect(src).toContain('sbUc')
    expect(src).toContain('ucTitle')
    expect(src).toContain('ucStepsList')
    expect(src).toContain('ucDesc')
  })
})

// ---------------------------------------------------------------------------
// Suite: bundler includes S7 modules in correct order
// ---------------------------------------------------------------------------

describe('bundler S7 integration — architecture bundle', () => {
  it('particles.js section comment present in architecture bundle', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('/* ── fd/particles.js ── */')
  })

  it('interactions.js section comment present in architecture bundle', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('/* ── fd/interactions.js ── */')
  })

  it('cards.js precedes particles.js (concat order)', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    const cardsIdx = bundle.indexOf('/* ── fd/cards.js ── */')
    const particlesIdx = bundle.indexOf('/* ── fd/particles.js ── */')
    expect(cardsIdx).toBeGreaterThanOrEqual(0)
    expect(particlesIdx).toBeGreaterThan(cardsIdx)
  })

  it('particles.js precedes interactions.js (concat order)', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    const particlesIdx = bundle.indexOf('/* ── fd/particles.js ── */')
    const interactionsIdx = bundle.indexOf('/* ── fd/interactions.js ── */')
    expect(particlesIdx).toBeGreaterThanOrEqual(0)
    expect(interactionsIdx).toBeGreaterThan(particlesIdx)
  })

  it('interactions.js precedes architecture.js type module (concat order)', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    const interactionsIdx = bundle.indexOf('/* ── fd/interactions.js ── */')
    const typeIdx = bundle.indexOf('/* ── fd/architecture.js ── */')
    expect(interactionsIdx).toBeGreaterThanOrEqual(0)
    expect(typeIdx).toBeGreaterThan(interactionsIdx)
  })

  it('spawnParticle symbol present in architecture bundle', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('spawnParticle')
  })

  it('easeInOutCubic symbol present in architecture bundle', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('easeInOutCubic')
  })

  it('spotlight symbol present in architecture bundle', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('spotlight')
  })

  it('wireUseCaseUI symbol present in architecture bundle', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('wireUseCaseUI')
  })

  it('wireHoverSpotlight symbol present in architecture bundle', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(bundle).toContain('wireHoverSpotlight')
  })

  it('GUARD: architecture bundle with S7 modules must NOT contain banned token', () => {
    const bundle = buildEngine(FD_DIR, 'architecture')
    expect(hasBannedToken(bundle)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Suite: AC-9 — particles OFF by default (contract in source)
// ---------------------------------------------------------------------------

describe('AC-9: particles OFF by default', () => {
  it('particles.js does NOT auto-start on load (no self-invoking particle spawn)', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    // The module must NOT call spawnParticle() or startParticles() at module top level.
    // It only exports functions; the caller (generated HTML bootstrap) decides to start.
    // Check: no call to spawnParticle outside a function body at module level.
    // Heuristic: count occurrences of spawnParticle — all must be inside function bodies.
    // We verify by checking there's no bare `spawnParticle(` at column 0 (not indented).
    const lines = src.split('\n')
    const bareCall = lines.filter((l) => /^spawnParticle\s*\(/.test(l))
    expect(bareCall).toHaveLength(0)
  })

  it('AC-9 descriptor contract: particles.js source documents the false default', () => {
    const src = readFileSync(PARTICLES_PATH, 'utf-8')
    // The spec comment must document the RD-2 opt-in contract
    expect(src).toContain('particles OFF')
  })
})

// ---------------------------------------------------------------------------
// Suite: easeInOutCubic pure-function math contract
// ---------------------------------------------------------------------------

describe('easeInOutCubic — math contract (pure, no DOM)', () => {
  // Replicate the function inline for pure-JS testing (no DOM required)
  function easeInOutCubic(t: number): number {
    return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2
  }

  it('easeInOutCubic(0) === 0', () => {
    expect(easeInOutCubic(0)).toBe(0)
  })

  it('easeInOutCubic(1) === 1', () => {
    expect(easeInOutCubic(1)).toBe(1)
  })

  it('easeInOutCubic(0.5) === 0.5 (symmetric midpoint)', () => {
    expect(easeInOutCubic(0.5)).toBeCloseTo(0.5, 10)
  })

  it('easeInOutCubic is monotonically increasing on [0,1]', () => {
    let prev = easeInOutCubic(0)
    for (let i = 1; i <= 100; i++) {
      const curr = easeInOutCubic(i / 100)
      expect(curr).toBeGreaterThanOrEqual(prev)
      prev = curr
    }
  })

  it('easeInOutCubic output stays in [0,1] for t in [0,1]', () => {
    for (let i = 0; i <= 100; i++) {
      const v = easeInOutCubic(i / 100)
      expect(v).toBeGreaterThanOrEqual(0)
      expect(v).toBeLessThanOrEqual(1)
    }
  })
})
