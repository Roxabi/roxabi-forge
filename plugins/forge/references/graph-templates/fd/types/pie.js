// fd/types/pie.js — pie type: SVG arc path math, legend column
// S6 footprint: this file only. No elkjs step — declarative SVG math (spec §2, Branch B).
//
// Descriptor schema:
//   {
//     "type": "pie",
//     "title": "...",
//     "theme": "lyra-v2",
//     "slices": [
//       { "label": "References", "value": 38, "color": "cyan"   },
//       { "label": "Skills",     "value": 27, "color": "amber"  },
//       { "label": "Scripts",    "value": 18, "color": "purple" },
//       { "label": "Runtime",    "value": 11, "color": "green"  },
//       { "label": "Other",      "value":  6, "color": "red"    }
//     ],
//     "options": { "donut": false, "showPercent": true }
//   }
//
// MATH — arc angles from values (VERIFIED):
//   total = sum(slice.value for slice in slices)
//   fraction_i = slice_i.value / total
//   angle_i    = fraction_i * 2π radians  (full circle)
//   Coordinate system: SVG viewBox="0 0 100 100", center=(50,50), radius=38
//   Start angle: -π/2 (12-o'clock, pointing up)
//   For each slice with startAngle θ₀ and sweepAngle Δθ:
//     endAngle = θ₀ + Δθ
//     x1 = 50 + 38·cos(θ₀)     y1 = 50 + 38·sin(θ₀)
//     x2 = 50 + 38·cos(θ₀+Δθ)  y2 = 50 + 38·sin(θ₀+Δθ)
//     large-arc-flag = fraction_i > 0.5 ? 1 : 0
//     Path: M 50,50 L x1,y1 A 38,38 0 large-arc-flag 1 x2,y2 Z
//   Invariant: Σ Δθ = 2π  (all slices close the circle exactly)
//   Donut variant: inner radius r_in = 22; path uses two arcs + lineTo.
//
// Rendering: inline SVG inside .fd-canvas + HTML legend column beside it.
// No edge engine — pie has no edges (spec §2 table).
// biome-ignore: all functions are injected into the concat bundle scope

const PIE_TYPE = 'pie'
// pie uses SVG-only rendering (no HTML fd-node cards) — RD-3 table
const PIE_CARD_DEFAULT = null

// ── color palette (maps descriptor color names to CSS vars) ─────────────────
const PIE_COLOR_MAP = {
  cyan: 'var(--cyan,   #22d3ee)',
  amber: 'var(--amber,  #f59e0b)',
  purple: 'var(--purple, #c084fc)',
  green: 'var(--green,  #10b981)',
  red: 'var(--red,    #ef4444)',
  plum: 'var(--plum,   #a855f7)',
  teal: 'var(--teal,   #06b6d4)',
  accent: 'var(--accent, #e85d04)',
  blue: '#3b82f6',
  pink: '#ec4899',
  orange: '#f97316',
  yellow: '#eab308',
  slate: 'var(--text-dim, #6b7280)',
}

// ── arc path helpers ─────────────────────────────────────────────────────────

// polarToXY: convert polar (cx, cy, r, angleRad) to Cartesian (x, y)
function polarToXY(cx, cy, r, angle) {
  return {
    x: cx + r * Math.cos(angle),
    y: cy + r * Math.sin(angle),
  }
}

// buildPieArc: SVG path string for one pie slice
//   cx, cy: center point; r: outer radius; r_in: inner radius (0 for solid)
//   startAngle, endAngle: radians (clockwise from -π/2 = top)
function buildPieArc(cx, cy, r, rIn, startAngle, endAngle) {
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0
  const p1 = polarToXY(cx, cy, r, startAngle)
  const p2 = polarToXY(cx, cy, r, endAngle)
  const fmt = (n) => n.toFixed(4)

  if (rIn > 0) {
    // Donut arc: outer arc CW + inner arc CCW
    const p3 = polarToXY(cx, cy, rIn, endAngle)
    const p4 = polarToXY(cx, cy, rIn, startAngle)
    return [
      `M ${fmt(p1.x)},${fmt(p1.y)}`,
      `A ${fmt(r)},${fmt(r)} 0 ${largeArc} 1 ${fmt(p2.x)},${fmt(p2.y)}`,
      `L ${fmt(p3.x)},${fmt(p3.y)}`,
      `A ${fmt(rIn)},${fmt(rIn)} 0 ${largeArc} 0 ${fmt(p4.x)},${fmt(p4.y)}`,
      'Z',
    ].join(' ')
  }

  // Solid slice: center → arc → close
  return [
    `M ${fmt(cx)},${fmt(cy)}`,
    `L ${fmt(p1.x)},${fmt(p1.y)}`,
    `A ${fmt(r)},${fmt(r)} 0 ${largeArc} 1 ${fmt(p2.x)},${fmt(p2.y)}`,
    'Z',
  ].join(' ')
}

// ── main renderer ────────────────────────────────────────────────────────────

// renderPie: builds the pie chart inside the fd-canvas element.
// Called by pieInit (via window.__fdTypes bootstrap).
function renderPie(descriptor) {
  const slices = descriptor.slices || []
  const opts = descriptor.options || {}
  const donut = Boolean(opts.donut)
  const showPercent = opts.showPercent !== false // default true
  const title = descriptor.title || ''

  if (slices.length === 0) {
    console.warn('[fd/pie] no slices defined')
    return
  }

  // ── compute total ─────────────────────────────────────────────────────────
  const total = slices.reduce((s, sl) => s + (sl.value || 0), 0)
  if (total <= 0) {
    console.warn('[fd/pie] total is zero or negative:', total)
    return
  }

  // ── layout constants (SVG viewBox 0 0 100 100) ────────────────────────────
  const CX = 50,
    CY = 50,
    R = 38,
    R_IN = donut ? 22 : 0
  const VB_SIZE = 100 // viewBox width and height

  // ── build SVG ─────────────────────────────────────────────────────────────
  const NS_SVG = 'http://www.w3.org/2000/svg'
  const svgWrap = document.createElementNS(NS_SVG, 'svg')
  svgWrap.setAttribute('viewBox', `0 0 ${VB_SIZE} ${VB_SIZE}`)
  svgWrap.setAttribute('aria-label', title || 'pie chart')
  svgWrap.setAttribute('role', 'img')
  svgWrap.style.cssText = `
    display:block;
    width:min(340px,50%);
    flex-shrink:0;
    overflow:visible;
  `

  // Inject per-slice color CSS vars into a <defs><style> block
  // Color names reference aesthetic vars (AC-6) with a hex fallback
  const defs = document.createElementNS(NS_SVG, 'defs')
  const styleEl = document.createElementNS(NS_SVG, 'style')
  let sliceCss = ''
  slices.forEach((sl, i) => {
    const colorVal = sl.color
      ? PIE_COLOR_MAP[sl.color] || sl.color
      : `hsl(${((i * 360) / slices.length).toFixed(0)},60%,55%)`
    sliceCss += `.fg-pie-slice-${i} { fill: ${colorVal}; }\n`
  })
  styleEl.textContent = sliceCss
  defs.appendChild(styleEl)
  svgWrap.appendChild(defs)

  // Draw slices
  let angleStart = -Math.PI / 2 // start at 12-o'clock

  slices.forEach((sl, i) => {
    const fraction = sl.value / total
    const sweep = fraction * 2 * Math.PI
    const angleEnd = angleStart + sweep

    const d = buildPieArc(CX, CY, R, R_IN, angleStart, angleEnd)

    const path = document.createElementNS(NS_SVG, 'path')
    path.setAttribute('d', d)
    path.setAttribute('class', `fg-pie-slice fg-pie-slice-${i}`)
    path.setAttribute('data-label', sl.label || '')
    path.setAttribute('data-value', String(sl.value))
    path.setAttribute('stroke', 'var(--bg, #0d1117)')
    path.setAttribute('stroke-width', '0.5')
    // Accessibility
    const titleEl = document.createElementNS(NS_SVG, 'title')
    titleEl.textContent = `${sl.label}: ${sl.value} (${(fraction * 100).toFixed(1)}%)`
    path.appendChild(titleEl)

    svgWrap.appendChild(path)

    // Percent label at slice midpoint (skip very small slices < 4%)
    if (showPercent && fraction >= 0.04) {
      const midAngle = angleStart + sweep / 2
      const labelR = donut ? (R + R_IN) / 2 : R * 0.6
      const lx = CX + labelR * Math.cos(midAngle)
      const ly = CY + labelR * Math.sin(midAngle)

      const txt = document.createElementNS(NS_SVG, 'text')
      txt.setAttribute('x', lx.toFixed(2))
      txt.setAttribute('y', (ly + 1.2).toFixed(2)) // +1.2 for visual vertical center
      txt.setAttribute('text-anchor', 'middle')
      txt.setAttribute('dominant-baseline', 'middle')
      txt.setAttribute('font-size', '4.5')
      txt.setAttribute('font-family', 'var(--mono, monospace)')
      txt.setAttribute('fill', 'var(--bg, #0d1117)')
      txt.setAttribute('font-weight', '700')
      txt.textContent = `${(fraction * 100).toFixed(0)}%`
      svgWrap.appendChild(txt)
    }

    angleStart = angleEnd
  })

  // Donut center label
  if (donut && title) {
    const centerText = document.createElementNS(NS_SVG, 'text')
    centerText.setAttribute('x', '50')
    centerText.setAttribute('y', '49')
    centerText.setAttribute('text-anchor', 'middle')
    centerText.setAttribute('dominant-baseline', 'middle')
    centerText.setAttribute('font-size', '5.5')
    centerText.setAttribute('font-family', 'var(--mono, monospace)')
    centerText.setAttribute('fill', 'var(--text-muted, #8b93a1)')
    // Wrap long titles to two lines (split at space near midpoint)
    // RC (F9): threshold was words.length > 3, but 3-word titles like 'fd-engine S slices'
    // (18 chars at font-size 5.5) are wider than the inner donut hole (44 SVG units diameter).
    // Lowering to >= 3 ensures any 3+ word title is split across two lines.
    const words = title.split(' ')
    if (words.length >= 3) {
      const mid = Math.floor(words.length / 2)
      const line1 = words.slice(0, mid).join(' ')
      const line2 = words.slice(mid).join(' ')
      const t1 = document.createElementNS(NS_SVG, 'tspan')
      t1.setAttribute('x', '50')
      t1.setAttribute('dy', '-3.5')
      t1.textContent = line1
      const t2 = document.createElementNS(NS_SVG, 'tspan')
      t2.setAttribute('x', '50')
      t2.setAttribute('dy', '5.5')
      t2.textContent = line2
      centerText.appendChild(t1)
      centerText.appendChild(t2)
    } else {
      centerText.textContent = title
    }
    svgWrap.appendChild(centerText)
  }

  // ── build legend ──────────────────────────────────────────────────────────
  const legend = document.createElement('div')
  legend.className = 'fg-pie-legend'
  legend.style.cssText = `
    display:flex;
    flex-direction:column;
    justify-content:center;
    gap:4px;
    padding:0 16px;
    flex:1;
    min-width:0;
  `

  slices.forEach((sl, i) => {
    const fraction = sl.value / total
    // RC (F3/SEC-002): PIE_COLOR_MAP[sl.color] || sl.color passes raw descriptor string
    // into style via innerHTML — XSS vector when color is not a known key.
    // Fix: whitelist-only; unknown color falls back to safe HSL. Never interpolate raw input.
    const colorVal =
      sl.color && PIE_COLOR_MAP[sl.color]
        ? PIE_COLOR_MAP[sl.color]
        : `hsl(${((i * 360) / slices.length).toFixed(0)},60%,55%)`

    const row = document.createElement('div')
    row.className = 'fg-pie-legend-row'

    // SEC-001/SEC-002 (F3): use createElement+style.background — no innerHTML sink.
    const swatch = document.createElement('span')
    swatch.className = 'swatch'
    swatch.style.background = colorVal

    const lbl = document.createElement('span')
    lbl.className = 'lbl'
    lbl.textContent = sl.label || ''

    const val = document.createElement('span')
    val.className = 'value'
    val.textContent = `${sl.value}${showPercent ? ` (${(fraction * 100).toFixed(1)}%)` : ''}`

    row.appendChild(swatch)
    row.appendChild(lbl)
    row.appendChild(val)
    legend.appendChild(row)
  })

  // ── assemble into canvas ──────────────────────────────────────────────────
  const wrapper = document.createElement('div')
  wrapper.className = 'fd-pie-wrap'
  wrapper.style.cssText = `
    display:flex;
    align-items:center;
    justify-content:center;
    gap:16px;
    padding:24px 16px;
    width:100%;
    box-sizing:border-box;
  `
  wrapper.appendChild(svgWrap)
  wrapper.appendChild(legend)

  if (canvas) canvas.appendChild(wrapper)

  // Fit canvas to content height
  if (canvas) {
    canvas.style.setProperty('--fd-canvas-h', 'auto')
    canvas.style.height = 'auto'
    canvas.style.minHeight = '340px'
  }
}

// ── init ────────────────────────────────────────────────────────────────────

function pieInit(descriptor) {
  const t = descriptor.type
  if (t !== 'pie') {
    console.warn('[fd] pie.js init() called with unexpected type:', t)
  }
  // Pie bypasses node/edge engine entirely (spec RD-3 table)
  return {
    typeDefault: PIE_CARD_DEFAULT,
    placeZones: null,
    renderChart: renderPie,
  }
}

// ── glob-discovery registration ──────────────────────────────────────────────
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[PIE_TYPE] = {
  CARD_DEFAULT: PIE_CARD_DEFAULT,
  placeZones: null,
  init: pieInit,
  renderChart: renderPie,
}
