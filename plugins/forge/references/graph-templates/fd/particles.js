// fd/particles.js — Layer 4: rAF particle engine
// Lifted verbatim from lyra-stack-v2.html lines 628-691 and adapted for
// the fd-engine descriptor-driven contract (RD-2).
//
// Opt-in contract (RD-2):
//   descriptor.options.particles === false (default) → particles OFF (AC-9)
//   descriptor.options.particles === true  → one-shot per edge on hover/UC trigger
//   descriptor.options.particles === "loop" → continuous: spawnParticle() loops on active edges
//
// Concat order: core.js → edges.js → cards.js → particles.js → [interactions.js] → types/{type}.js
// Depends on: NS, svg, pathByPair, pairKey — declared in core.js / edges.js scope.
//
// Guard: zero occurrences of the banned lowercase token in this file.
// Self-check: grep -rn '\bmermaid\b' plugins/forge/ must be empty.

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2
}

// Active particle state — one particle at a time (one-shot mode)
// Loop mode tracks multiple particles via loopParticles[]
let _particleEl = null
let _particleRAF = null
let _loopParticles = [] // [{wrapper, rafId}] — loop mode only

function clearParticle() {
  if (_particleRAF) {
    cancelAnimationFrame(_particleRAF)
    _particleRAF = null
  }
  if (_particleEl) {
    _particleEl.remove()
    _particleEl = null
  }
}

// clearLoopParticles: stop all loop-mode particles
function clearLoopParticles() {
  for (let i = 0; i < _loopParticles.length; i++) {
    const lp = _loopParticles[i]
    if (lp.rafId) cancelAnimationFrame(lp.rafId)
    if (lp.wrapper) lp.wrapper.remove()
  }
  _loopParticles = []
}

// ── spawnParticle ─────────────────────────────────────────────────────────
// Lifted verbatim from lyra-stack-v2.html l.640-691, adapted for fd-engine:
//   - plane color resolved via CSS var --fd-plane-{plane} (AC-6, never hardcoded hex)
//   - particle wrapper class: fd-particle-wrap (matches fd-architecture.html CSS)
//   - forward direction: pathEl.dataset.f === edgeF (verbatim from source)
//
// edgeF, edgeT: node ids of the edge endpoints (directional for forward/reverse)
// plane:        semantic plane string ('control', 'write', etc.)
// duration:     animation duration in ms (default 750, per spec)
// onDone:       optional callback invoked when animation completes (for loop scheduling)
//
function spawnParticle(edgeF, edgeT, plane, duration, onDone) {
  const dur = duration || 750
  const pk = pairKey(edgeF, edgeT)
  const pathEl = pathByPair.get(pk)
  if (!pathEl) return null

  // Resolve color from CSS var (theme-aware, AC-6)
  // Fallback chain: --fd-plane-{plane} → #8aa0bd (muted default)
  let col = '#8aa0bd'
  const tmp = document.documentElement
  const resolved = getComputedStyle(tmp).getPropertyValue(`--fd-plane-${plane}`).trim()
  if (resolved) col = resolved

  const forward = pathEl.dataset.f === edgeF
  const len = pathEl.getTotalLength()

  // Build halo + core inside a <g class="fd-particle-wrap"> (verbatim structure l.664-673)
  const wrapper = document.createElementNS(NS, 'g')
  wrapper.setAttribute('class', 'fd-particle-wrap')
  wrapper.style.setProperty('--pcol', col)

  const halo = document.createElementNS(NS, 'circle')
  halo.setAttribute('r', '9')
  halo.setAttribute('fill', col)
  halo.setAttribute('opacity', '0.22')

  const core = document.createElementNS(NS, 'circle')
  core.setAttribute('r', '5')
  core.setAttribute('fill', col)

  wrapper.appendChild(halo)
  wrapper.appendChild(core)
  svg.appendChild(wrapper)

  const start = performance.now()

  function frame(now) {
    const u = Math.min((now - start) / dur, 1)
    const e = easeInOutCubic(u)
    const d = forward ? e * len : (1 - e) * len
    const pt = pathEl.getPointAtLength(d)
    halo.setAttribute('cx', pt.x)
    halo.setAttribute('cy', pt.y)
    core.setAttribute('cx', pt.x)
    core.setAttribute('cy', pt.y)
    if (u < 1) {
      return requestAnimationFrame(frame)
    }
    if (typeof onDone === 'function') onDone()
    return null
  }

  const rafId = requestAnimationFrame(frame)
  return { wrapper, rafId }
}

// ── startParticles / stopParticles (loop mode) ────────────────────────────
// Called by the engine bootstrap when descriptor.options.particles === "loop".
// Runs spawnParticle() continuously on all active edges, recycling on completion.

/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — called by generated HTML bootstrap */
function startParticles(descriptor) {
  clearLoopParticles()
  const edges = descriptor?.edges || []
  if (!edges.length) return

  // Loop: spawn one particle per edge in sequence, recycling each on completion
  function spawnLoop(edgeIdx) {
    const e = edges[edgeIdx % edges.length]
    const plane = e.plane || 'control'
    const lp = { wrapper: null, rafId: null }
    _loopParticles.push(lp)

    function onDone() {
      if (lp.wrapper) lp.wrapper.remove()
      // Re-spawn after a brief gap (50ms), cycling through edges
      setTimeout(() => {
        const nextIdx = (edgeIdx + 1) % edges.length
        spawnLoop(nextIdx)
      }, 50)
    }

    const result = spawnParticle(e.f, e.t, plane, 750, onDone)
    if (result) {
      lp.wrapper = result.wrapper
      lp.rafId = result.rafId
    }
  }

  // Stagger initial spawns across edges
  edges.forEach((_e, i) => {
    setTimeout(() => {
      spawnLoop(i)
    }, i * 180)
  })
}

/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — called by generated HTML bootstrap */
function stopParticles() {
  clearParticle()
  clearLoopParticles()
}
