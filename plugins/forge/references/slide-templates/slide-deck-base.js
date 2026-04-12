/* ══════════════════════════════════════════════════════════════════
   slide-deck-base.js — scroll-snap slide engine + Mermaid init
   Runtime for forge-slides decks. Inline as <script type="module">.

   Init sequence (load-bearing — order matters):
     1. initSlideMermaid()   render .slide--diagram [data-mermaid]
                        with auto-generated IDs mermaid-slide-${i}
     2. autoFit()       fix Mermaid SVG overflow + KPI/quote scale
                        (runs AFTER Mermaid render — SVG intrinsic
                        dimensions only exist once rendered)
     3. new SlideEngine(deck)   wire keyboard, touch, IntersectionObserver

   Why a lean built-in Mermaid init (not base/mermaid-init.js reuse):
     base/mermaid-init.js binds window.__postLoad for the tab-loader
     system. Scroll-snap decks have no tab-loader, no panel arg, and
     need per-slide unique IDs. Reusing that init would silently fail
     on the second diagram slide (duplicate 'mermaid-${id}' collision).
   ══════════════════════════════════════════════════════════════════ */

import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs'

// ── Mermaid initialize ─────────────────────────────────────────────
// Pulls theme colors from the aesthetic's CSS custom properties so a
// single init respects whichever aesthetic is inlined.
const css = getComputedStyle(document.documentElement)
const token = (name) => css.getPropertyValue(name).trim()
const isDark = (document.documentElement.getAttribute('data-theme') || 'dark') !== 'light'

mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  look: 'classic',
  themeVariables: {
    primaryColor: token('--surface') || (isDark ? '#1d2b52' : '#fef3e0'),
    primaryBorderColor: token('--accent') || (isDark ? '#d4a73a' : '#b8860b'),
    primaryTextColor: token('--text') || (isDark ? '#e8e4d8' : '#1a1814'),
    secondaryColor: token('--surface2') || (isDark ? '#162040' : '#eff6ff'),
    secondaryBorderColor: token('--accent') || (isDark ? '#60a5fa' : '#2563eb'),
    secondaryTextColor: token('--text') || (isDark ? '#e8e4d8' : '#1a1814'),
    tertiaryColor: token('--surface') || (isDark ? '#0f2620' : '#f0fdf4'),
    tertiaryBorderColor: token('--accent') || (isDark ? '#4ade80' : '#16a34a'),
    tertiaryTextColor: token('--text') || (isDark ? '#e8e4d8' : '#1a1814'),
    lineColor: token('--text-dim') || '#9a9484',
    fontSize: '18px',
    fontFamily: 'var(--font-body, IBM Plex Sans, system-ui, sans-serif)',
  },
})

// ── initSlideMermaid ────────────────────────────────────────────────────
// Scoped to .slide--diagram [data-mermaid] only — won't touch other
// .mermaid blocks on the page. Unique IDs prevent collision when a
// deck has multiple diagram slides.
async function initSlideMermaid() {
  const nodes = document.querySelectorAll('.slide--diagram [data-mermaid]')
  if (!nodes.length) return
  let i = 0
  for (const node of nodes) {
    const id = `mermaid-slide-${i++}`
    const src = node.textContent.trim()
    if (!src) continue
    try {
      const { svg } = await mermaid.render(id, src)
      node.innerHTML = svg
      node.setAttribute('data-rendered', 'true')
    } catch (err) {
      node.innerHTML = `<pre style="color:var(--error,#f87171);">Mermaid render error: ${err.message}</pre>`
    }
  }
}

// ── autoFit ────────────────────────────────────────────────────────
// Post-render pass that: (1) stretches Mermaid SVGs to fill their
// slide body without intrinsic-size overflow, (2) scales any KPI
// numbers that overflow their container width, (3) shrinks long
// blockquotes to fit. Idempotent — safe to call more than once.
function autoFit() {
  // 1. Mermaid SVGs — remove fixed height, fit to container width
  document.querySelectorAll('.slide--diagram svg').forEach((svg) => {
    svg.removeAttribute('height')
    svg.style.width = '100%'
    svg.style.maxWidth = '100%'
    svg.style.height = 'auto'
    svg.style.maxHeight = '80vh'
    if (svg.parentElement) svg.parentElement.style.width = '100%'
  })

  // 2. KPI values — shrink if overflowing their container
  document.querySelectorAll('.slide__kpi-val').forEach((el) => {
    if (el.scrollWidth > el.clientWidth) {
      const s = el.clientWidth / el.scrollWidth
      el.style.transform = `scale(${s})`
      el.style.transformOrigin = 'left top'
    }
  })

  // 3. Long blockquotes — shrink font-size proportionally
  document.querySelectorAll('.slide--quote blockquote').forEach((el) => {
    const len = el.textContent.trim().length
    if (len > 100) {
      const scale = Math.max(0.5, 100 / len)
      const fs = parseFloat(getComputedStyle(el).fontSize)
      el.style.fontSize = `${Math.max(16, Math.round(fs * scale))}px`
    }
  })
}

// ── SlideEngine ────────────────────────────────────────────────────
// Owns: keyboard nav, touch swipe, IntersectionObserver, chrome
// construction (progress bar, dots, counter, hints).
class SlideEngine {
  constructor(deck) {
    this.deck = deck || document.querySelector('.deck')
    this.slides = [...this.deck.querySelectorAll('.slide')]
    this.total = this.slides.length
    this.current = 0

    this.buildChrome()
    this.bindEvents()
    this.observe()
    this.update()
  }

  buildChrome() {
    // Progress bar
    this.bar = Object.assign(document.createElement('div'), { className: 'deck-progress' })
    document.body.appendChild(this.bar)

    // Dot indicator (click to jump)
    const dots = Object.assign(document.createElement('div'), { className: 'deck-dots' })
    this.slides.forEach((_, i) => {
      const d = Object.assign(document.createElement('button'), { className: 'deck-dot' })
      d.type = 'button'
      d.title = `Slide ${i + 1}`
      d.setAttribute('aria-label', `Go to slide ${i + 1}`)
      d.addEventListener('click', () => this.goTo(i))
      dots.appendChild(d)
    })
    document.body.appendChild(dots)
    this.dots = [...dots.children]

    // Counter
    this.counter = Object.assign(document.createElement('div'), { className: 'deck-counter' })
    document.body.appendChild(this.counter)

    // Hints
    this.hints = Object.assign(document.createElement('div'), { className: 'deck-hints' })
    this.hints.textContent = '← → or scroll to navigate'
    document.body.appendChild(this.hints)
    this.hintTimer = setTimeout(() => this.hints.classList.add('faded'), 4000)
  }

  bindEvents() {
    document.addEventListener('keydown', (e) => {
      // Don't hijack keys inside inputs or scrollable regions
      if (e.target.closest('input,textarea,[contenteditable],.table-scroll,.code-scroll')) return

      const k = e.key
      if (['ArrowDown', 'ArrowRight', ' ', 'PageDown'].includes(k)) {
        e.preventDefault()
        this.next()
      } else if (['ArrowUp', 'ArrowLeft', 'PageUp'].includes(k)) {
        e.preventDefault()
        this.prev()
      } else if (k === 'Home') {
        e.preventDefault()
        this.goTo(0)
      } else if (k === 'End') {
        e.preventDefault()
        this.goTo(this.total - 1)
      } else return
      this.fadeHints()
    })

    // Touch swipe (vertical)
    let tY = 0
    this.deck.addEventListener(
      'touchstart',
      (e) => {
        tY = e.touches[0].clientY
      },
      { passive: true },
    )
    this.deck.addEventListener('touchend', (e) => {
      const dy = tY - e.changedTouches[0].clientY
      if (Math.abs(dy) > 50) dy > 0 ? this.next() : this.prev()
    })
  }

  observe() {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible')
            this.current = this.slides.indexOf(entry.target)
            this.update()
          }
        })
      },
      { threshold: 0.5 },
    )
    this.slides.forEach((s) => {
      obs.observe(s)
    })
  }

  goTo(i) {
    const clamped = Math.max(0, Math.min(i, this.total - 1))
    this.slides[clamped].scrollIntoView({ behavior: 'smooth' })
  }
  next() {
    if (this.current < this.total - 1) this.goTo(this.current + 1)
  }
  prev() {
    if (this.current > 0) this.goTo(this.current - 1)
  }

  update() {
    this.bar.style.width = `${((this.current + 1) / this.total) * 100}%`
    this.dots.forEach((d, i) => {
      d.classList.toggle('active', i === this.current)
    })
    this.counter.textContent = `${this.current + 1} / ${this.total}`
  }

  fadeHints() {
    clearTimeout(this.hintTimer)
    this.hints.classList.add('faded')
  }
}

// ── Bootstrap ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await initSlideMermaid() // render first (SVG intrinsic dims needed for autoFit)
  autoFit() // then fit
  new SlideEngine() // then wire nav
})

export { autoFit, initSlideMermaid, SlideEngine }
