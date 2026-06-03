// fd/types/xychart.js — S5: pure SVG math xychart renderer (bar + line + combined)
// Slice ownership: S5 (issue #62). Disjoint footprint — owns this file only.
// No node/edge engine needed: xychart bypasses layers 1-3 entirely.
// No elkjs gen-time step (type: xychart, layout: "none" — pure SVG math).
//
// Descriptor schema (xychart subset):
// {
//   "type": "xychart",
//   "title": "Chart Title",
//   "theme": "lyra-v2",
//   "canvas": { "width": 800, "height": 420 },
//   "chart": {
//     "xTitle": "X axis label",      // optional
//     "yTitle": "Y axis label",       // optional
//     "yMin": 0,                      // optional, default 0
//     "yMax": 100,                    // optional, derived from data if absent
//     "gridLines": 5,                 // optional, default 5
//     "series": [
//       {
//         "name": "Series A",
//         "type": "bar",              // "bar" | "line"
//         "color": "var(--fd-xy-c0)", // optional, defaults to palette
//         "values": [10, 20, 30, ...]
//       },
//       {
//         "name": "Series B",
//         "type": "line",
//         "color": "var(--fd-xy-c1)",
//         "values": [15, 25, 35, ...]
//       }
//     ]
//   },
//   "categories": ["Cat A", "Cat B", "Cat C", ...]
// }
//
// MATH VERIFICATION:
//   plotW   = chartW - PAD_L - PAD_R
//   plotH   = chartH - PAD_T - PAD_B
//   catStep = plotW / N                           (width per category slot)
//   catX(i) = PAD_L + i * catStep + catStep / 2  (center of slot i)
//   scaleY(v) = PAD_T + plotH * (1 - (v - yMin) / (yMax - yMin))
//     → v=yMin  → PAD_T + plotH = bottom of plot = y-axis baseline  ✓
//     → v=yMax  → PAD_T + 0    = top of plot area                    ✓
//   barH(v)  = plotH * (v - yMin) / (yMax - yMin)
//     → barH + scaleY(v) = PAD_T + plotH = baseline                   ✓ (bars sit on baseline)
//   barX(i)  = PAD_L + i * catStep + BAR_PAD          (left edge of bar)
//   barWidth = catStep - 2 * BAR_PAD - (nBarSeries - 1) * BAR_GAP     (single bar series)
//   barWidth = (catStep - 2 * BAR_PAD - (nBarSeries - 1) * BAR_GAP) / nBarSeries  (grouped)
//   barXGrouped(i, si) = PAD_L + i * catStep + BAR_PAD + si * (barWidth + BAR_GAP)
//
// Guard-safe: type name is "xychart" — no banned tokens under plugins/forge/.

const TYPE = 'xychart'

// ── Palette: CSS vars for series colors (overridden by descriptor.chart.series[i].color)
// Color indices cycle if more series than palette entries.
const XY_PALETTE = [
  'var(--fd-xy-c0, var(--fd-plane-control,  #38bdf8))',
  'var(--fd-xy-c1, var(--fd-plane-async,    #fb923c))',
  'var(--fd-xy-c2, var(--fd-plane-write,    #34d399))',
  'var(--fd-xy-c3, var(--fd-plane-data,     #a78bfa))',
  'var(--fd-xy-c4, var(--fd-plane-feedback, #fb7185))',
  'var(--fd-xy-c5, var(--fd-plane-media,    #fbbf24))',
]

// ── Layout constants (pixel margins around the plot area)
const PAD_L = 62 // left  — room for y-axis tick labels (up to 5–6 chars)
const PAD_R = 24 // right — small breathing room
const PAD_T = 28 // top   — grid top + breathing room
const PAD_B = 54 // bottom — x-axis labels + axis title

const BAR_PAD = 6 // padding inside each category slot (left and right of bar group)
const BAR_GAP = 4 // gap between bars in a grouped-bar scenario
const LINE_SW = 2.5 // line series stroke-width
const DOT_R = 4 // dot radius on line series

// ── SVG namespace
const XY_NS = 'http://www.w3.org/2000/svg'

// ── Helper: create SVG element with attributes
function svgEl(tag, attrs) {
  const el = document.createElementNS(XY_NS, tag)
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, v)
  }
  return el
}

// ── Helper: nice round number for Y axis ticks
// Given raw max, returns a rounded-up value that divides cleanly into nTicks.
function niceMax(rawMax, nTicks) {
  if (rawMax <= 0) return nTicks // fallback: 1 per tick
  const rawStep = rawMax / nTicks
  const magnitude = 10 ** Math.floor(Math.log10(rawStep))
  const niceStep = Math.ceil(rawStep / magnitude) * magnitude
  return niceStep * nTicks
}

// ── Helper: format tick label (no trailing zeros for integers)
function fmtTick(v) {
  if (Number.isInteger(v)) return String(v)
  return v.toFixed(1)
}

// ── renderXychart: main render function
// Clears and replaces any existing .fd-xy-svg in the canvas element.
// descriptor: full fd-data JSON object
function renderXychart(descriptor) {
  // Remove any existing chart SVG
  const existing = canvas.querySelector('.fd-xy-svg')
  if (existing) existing.remove()

  const chart = descriptor.chart || {}
  const categories = descriptor.categories || []
  const series = chart.series || []
  const N = categories.length

  if (N === 0 || series.length === 0) {
    // Nothing to render — emit a placeholder text
    const placeholder = svgEl('svg', {
      class: 'fd-xy-svg',
      width: '100%',
      height: '100%',
    })
    const msg = svgEl('text', { x: '50%', y: '50%', 'text-anchor': 'middle', fill: '#8b93a1', 'font-size': '14' })
    msg.textContent = 'No data'
    placeholder.appendChild(msg)
    canvas.appendChild(placeholder)
    return
  }

  // ── Resolve chart dimensions from canvas style or descriptor
  const canvasCfg = descriptor.canvas || {}
  const chartW = canvasCfg.width || canvas.offsetWidth || 800
  const chartH = canvasCfg.height || canvas.offsetHeight || 420

  // ── Derive Y range
  const allValues = series.flatMap((s) => s.values || []).filter((v) => typeof v === 'number')
  const rawMax = allValues.length > 0 ? Math.max(...allValues) : 100
  const rawMin = allValues.length > 0 ? Math.min(...allValues) : 0

  const nGridLines = typeof chart.gridLines === 'number' ? chart.gridLines : 5
  const yMinCfg = typeof chart.yMin === 'number' ? chart.yMin : Math.min(0, rawMin)
  // yMax: either explicit or computed as nice round number above rawMax
  const yMaxCfg = typeof chart.yMax === 'number' ? chart.yMax : niceMax(rawMax - yMinCfg, nGridLines) + yMinCfg

  const yMin = yMinCfg
  const yMax = yMaxCfg
  const yRange = yMax - yMin || 1 // guard division by zero

  // ── Plot area geometry (pixel coords)
  const plotW = chartW - PAD_L - PAD_R
  const plotH = chartH - PAD_T - PAD_B

  // MATH: catStep = plotW / N  → each category occupies exactly this horizontal width
  const catStep = plotW / N

  // MATH: catX(i) = PAD_L + i * catStep + catStep / 2  → SVG x at center of slot i
  const catX = (i) => PAD_L + i * catStep + catStep / 2

  // MATH: scaleY(v) = PAD_T + plotH * (1 - (v - yMin) / yRange)
  // Verification: scaleY(yMin) = PAD_T + plotH ✓ (bottom), scaleY(yMax) = PAD_T ✓ (top)
  const scaleY = (v) => PAD_T + plotH * (1 - (v - yMin) / yRange)

  // MATH: barH(v) = plotH * (v - yMin) / yRange
  // Verification: scaleY(v) + barH(v) = PAD_T + plotH ✓ (bars sit on baseline)
  const barH = (v) => plotH * Math.max(0, (v - yMin) / yRange)

  // ── Count bar series for grouped layout
  const barSeries = series.filter((s) => (s.type || 'bar') === 'bar')
  const nBarSeries = barSeries.length

  // ── Bar geometry per grouped slot
  // barGroupW = total width allocated to bars inside one catStep slot
  const barGroupW = catStep - 2 * BAR_PAD
  // singleBarW = width of one bar within the group
  const singleBarW = nBarSeries > 0 ? Math.max(2, (barGroupW - (nBarSeries - 1) * BAR_GAP) / nBarSeries) : barGroupW

  // MATH: barGroupLeft(i) = PAD_L + i * catStep + BAR_PAD  → left edge of bar group in slot i
  // MATH: barX(i, si) = barGroupLeft(i) + si * (singleBarW + BAR_GAP) → left edge of bar si in group
  const barGroupLeft = (i) => PAD_L + i * catStep + BAR_PAD
  const barX = (i, si) => barGroupLeft(i) + si * (singleBarW + BAR_GAP)

  // ── Create the SVG
  const svg = svgEl('svg', {
    class: 'fd-xy-svg',
    width: chartW,
    height: chartH,
    'aria-label': descriptor.title || 'XY chart',
    role: 'img',
  })

  // ── Injected CSS: vars + element rules (AC-6: derive from aesthetic tokens)
  const style = document.createElementNS(XY_NS, 'style')
  style.textContent = `
    .fd-xy-grid line { stroke: var(--fd-xy-grid, rgba(255,255,255,0.07)); stroke-dasharray: 4 3; }
    .fd-xy-axis line, .fd-xy-axis path { stroke: var(--fd-xy-axis, rgba(255,255,255,0.18)); fill: none; }
    .fd-xy-tick-label { font-family: var(--mono, monospace); font-size: 10px; fill: var(--fd-xy-label, #8b93a1); }
    .fd-xy-axis-title { font-family: var(--sans, sans-serif); font-size: 11px; fill: var(--fd-xy-label, #8b93a1); }
    .fd-xy-chart-title { font-family: var(--sans, sans-serif); font-size: 14px; font-weight: 700; fill: var(--text, #fafafa); }
    .fd-xy-legend { font-family: var(--mono, monospace); font-size: 10px; fill: var(--fd-xy-label, #8b93a1); }
    .fd-xy-bar { opacity: 0.82; transition: opacity 0.12s; }
    .fd-xy-bar:hover { opacity: 1; }
    .fd-xy-line { fill: none; stroke-width: ${LINE_SW}; opacity: 0.9; }
    .fd-xy-dot { opacity: 0.9; }
    .fd-xy-dot:hover { opacity: 1; r: ${DOT_R + 2}; }
  `
  svg.appendChild(style)

  // ── Chart title
  if (descriptor.title) {
    const titleEl = svgEl('text', {
      class: 'fd-xy-chart-title',
      x: PAD_L + plotW / 2,
      y: 18,
      'text-anchor': 'middle',
    })
    titleEl.textContent = descriptor.title
    svg.appendChild(titleEl)
  }

  // ── Y-axis grid lines + tick labels
  const gridG = svgEl('g', { class: 'fd-xy-grid', 'aria-hidden': 'true' })
  const yTickG = svgEl('g', { class: 'fd-xy-axis', 'aria-hidden': 'true' })

  for (let ti = 0; ti <= nGridLines; ti++) {
    // MATH: yVal(ti) = yMin + (yMax - yMin) * ti / nGridLines
    // → ti=0 → yMin (bottom), ti=nGridLines → yMax (top)  ✓
    const yVal = yMin + yRange * (ti / nGridLines)
    const yPx = scaleY(yVal)

    // Grid line: spans full plot width
    const gridLine = svgEl('line', {
      x1: PAD_L,
      y1: yPx,
      x2: PAD_L + plotW,
      y2: yPx,
    })
    gridG.appendChild(gridLine)

    // Y tick label: right-aligned just left of plot area
    const tickLabel = svgEl('text', {
      class: 'fd-xy-tick-label',
      x: PAD_L - 8,
      y: yPx + 4, // +4 to visually center on the line (10px font → ~5px cap height)
      'text-anchor': 'end',
    })
    tickLabel.textContent = fmtTick(yVal)
    yTickG.appendChild(tickLabel)
  }

  svg.appendChild(gridG)

  // ── Axes (L-shape: left vertical + bottom horizontal)
  const axisG = svgEl('g', { class: 'fd-xy-axis', 'aria-hidden': 'true' })

  // Y axis (left vertical): from top of plot to baseline
  const yAxisLine = svgEl('line', {
    x1: PAD_L,
    y1: PAD_T,
    x2: PAD_L,
    y2: PAD_T + plotH,
  })
  axisG.appendChild(yAxisLine)

  // X axis (baseline): from left to right of plot
  // MATH: baseline y = scaleY(yMin) = PAD_T + plotH  ✓
  const xAxisLine = svgEl('line', {
    x1: PAD_L,
    y1: PAD_T + plotH,
    x2: PAD_L + plotW,
    y2: PAD_T + plotH,
  })
  axisG.appendChild(xAxisLine)

  svg.appendChild(axisG)
  svg.appendChild(yTickG)

  // ── X-axis tick marks + category labels
  const xLabelG = svgEl('g', { class: 'fd-xy-axis', 'aria-hidden': 'true' })
  for (let i = 0; i < N; i++) {
    // MATH: tick x = catX(i) = PAD_L + i*catStep + catStep/2  ✓ (center of slot)
    const cx = catX(i)

    // Tick mark (small notch below baseline)
    const tick = svgEl('line', {
      x1: cx,
      y1: PAD_T + plotH,
      x2: cx,
      y2: PAD_T + plotH + 5,
    })
    xLabelG.appendChild(tick)

    // Category label — rotate for readability on many categories
    const catLabel = svgEl('text', {
      class: 'fd-xy-tick-label',
      x: cx,
      y: PAD_T + plotH + 16,
      'text-anchor': 'middle',
    })
    catLabel.textContent = categories[i] || ''
    xLabelG.appendChild(catLabel)
  }
  svg.appendChild(xLabelG)

  // ── Axis titles
  if (chart.xTitle) {
    const xTitle = svgEl('text', {
      class: 'fd-xy-axis-title',
      x: PAD_L + plotW / 2,
      y: chartH - 4,
      'text-anchor': 'middle',
    })
    xTitle.textContent = chart.xTitle
    svg.appendChild(xTitle)
  }

  if (chart.yTitle) {
    // Rotated Y-axis title: rotate around the label midpoint
    const yTitle = svgEl('text', {
      class: 'fd-xy-axis-title',
      x: 0,
      y: 0,
      'text-anchor': 'middle',
      transform: `rotate(-90) translate(${-(PAD_T + plotH / 2)}, ${14})`,
    })
    yTitle.textContent = chart.yTitle
    svg.appendChild(yTitle)
  }

  // ── Bar series rendering
  // Track which bar series index each series is (for grouped positioning)
  let barSeriesIdx = 0
  for (const s of series) {
    const sType = s.type || 'bar'
    if (sType !== 'bar') continue

    const color = s.color || XY_PALETTE[series.indexOf(s) % XY_PALETTE.length]
    const si = barSeriesIdx

    const barG = svgEl('g', {
      class: 'fd-xy-bar',
      'aria-label': s.name || `Series ${si + 1}`,
      style: `fill: ${color}`,
    })

    for (let i = 0; i < N; i++) {
      const v = (s.values || [])[i]
      if (typeof v !== 'number') continue

      // MATH bar coords:
      // x = barX(i, si) = barGroupLeft(i) + si*(singleBarW + BAR_GAP)
      //   = PAD_L + i*catStep + BAR_PAD + si*(singleBarW + BAR_GAP)
      // y = scaleY(v) = PAD_T + plotH*(1 - (v-yMin)/yRange)
      // width = singleBarW
      // height = barH(v) = plotH*(v-yMin)/yRange
      // Verification: y + height = scaleY(v) + barH(v)
      //   = PAD_T + plotH - plotH*(v-yMin)/yRange + plotH*(v-yMin)/yRange
      //   = PAD_T + plotH  ← baseline  ✓
      const rectEl = svgEl('rect', {
        x: barX(i, si).toFixed(2),
        y: scaleY(v).toFixed(2),
        width: singleBarW.toFixed(2),
        height: barH(v).toFixed(2),
        rx: 2,
      })
      barG.appendChild(rectEl)
    }

    svg.appendChild(barG)
    barSeriesIdx++
  }

  // ── Line series rendering
  for (const s of series) {
    const sType = s.type || 'bar'
    if (sType !== 'line') continue

    const color = s.color || XY_PALETTE[series.indexOf(s) % XY_PALETTE.length]

    // Build polyline points: "x0,y0 x1,y1 ..."
    // MATH: point(i) = (catX(i), scaleY(values[i]))
    // catX(i)  = PAD_L + i*catStep + catStep/2  ← center of slot  ✓
    // scaleY(v) = PAD_T + plotH*(1-(v-yMin)/yRange)                ✓
    const points = (s.values || [])
      .map((v, i) => {
        if (typeof v !== 'number') return null
        return `${catX(i).toFixed(2)},${scaleY(v).toFixed(2)}`
      })
      .filter(Boolean)
      .join(' ')

    if (points.length === 0) continue

    // Polyline stroke
    const lineEl = svgEl('polyline', {
      class: 'fd-xy-line',
      points,
      stroke: color,
    })
    svg.appendChild(lineEl)

    // Dots at each data point
    const dotG = svgEl('g', { class: 'fd-xy-dot', style: `fill: ${color}` })
    ;(s.values || []).forEach((v, i) => {
      if (typeof v !== 'number') return
      const dot = svgEl('circle', {
        cx: catX(i).toFixed(2),
        cy: scaleY(v).toFixed(2),
        r: DOT_R,
      })
      dotG.appendChild(dot)
    })
    svg.appendChild(dotG)
  }

  // ── Legend
  const legendItems = series.filter((s) => s.name)
  if (legendItems.length > 0) {
    const legendG = svgEl('g', { class: 'fd-xy-legend', 'aria-label': 'Legend' })
    const legendY = chartH - (chart.xTitle ? 22 : 10)
    const itemW = 90
    const totalW = legendItems.length * itemW
    const startX = PAD_L + (plotW - totalW) / 2

    legendItems.forEach((s, li) => {
      const color = s.color || XY_PALETTE[series.indexOf(s) % XY_PALETTE.length]
      const lx = startX + li * itemW
      const sType = s.type || 'bar'

      if (sType === 'bar') {
        // Color swatch (small rect)
        const swatch = svgEl('rect', {
          x: lx,
          y: legendY - 8,
          width: 12,
          height: 10,
          rx: 2,
          style: `fill: ${color}; opacity: 0.82`,
        })
        legendG.appendChild(swatch)
      } else {
        // Line + dot indicator
        const ln = svgEl('line', {
          x1: lx,
          y1: legendY - 3,
          x2: lx + 12,
          y2: legendY - 3,
          stroke: color,
          'stroke-width': LINE_SW,
        })
        const dot = svgEl('circle', {
          cx: lx + 6,
          cy: legendY - 3,
          r: 3,
          style: `fill: ${color}`,
        })
        legendG.appendChild(ln)
        legendG.appendChild(dot)
      }

      const lbl = svgEl('text', {
        class: 'fd-xy-legend',
        x: lx + 16,
        y: legendY,
        'text-anchor': 'start',
      })
      lbl.textContent = s.name
      legendG.appendChild(lbl)
    })

    svg.appendChild(legendG)
  }

  // ── Append to canvas
  canvas.appendChild(svg)
}

// ── init — called by the fd-engine bootstrap after parsing fd-data
// Returns { typeDefault: null } — xychart has no HTML nodes/edges.
function init(descriptor) {
  const t = descriptor.type
  if (t !== 'xychart') {
    console.warn('[fd] xychart.js init() called with unexpected type:', t)
  }
  // Render immediately (DOM is ready at DOMContentLoaded)
  renderXychart(descriptor)

  // ResizeObserver re-render: canvas width may change on container resize
  new ResizeObserver(() => renderXychart(descriptor)).observe(canvas)

  // xychart does not use node/edge engine — return null typeDefault
  return { typeDefault: null }
}

// ── glob-discovery registration (RD-4)
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[TYPE] = { init }
