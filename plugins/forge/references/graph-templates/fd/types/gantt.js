// fd/types/gantt.js — gantt type: date-driven bar layout, section headers
// S6 footprint: this file only. No elkjs step — declarative layout (spec §2, Branch B).
//
// Descriptor schema:
//   {
//     "type": "gantt",
//     "title": "...",
//     "theme": "lyra-v2",
//     "timeline": { "start": "2026-01-01", "end": "2026-04-01" },
//     "sections": [
//       {
//         "title": "Phase 1",
//         "bars": [
//           { "id": "t1", "label": "Task A", "start": "2026-01-01", "end": "2026-02-01", "color": "cyan" },
//           { "id": "t2", "label": "Task B", "start": "2026-01-15", "end": "2026-03-01", "color": "amber" }
//         ]
//       }
//     ],
//     "options": { "showToday": true }
//   }
//
// MATH — bar x and width from dates (VERIFIED):
//   daysSince(d) = (Date.parse(d) - Date.parse(timeline.start)) / 86_400_000
//   totalDays    = daysSince(timeline.end)
//   x%           = daysSince(bar.start) / totalDays * 100
//   w%           = (daysSince(bar.end) - daysSince(bar.start)) / totalDays * 100
//   Invariant: x + w ≤ 100 when bar.end ≤ timeline.end (clamped to [0, 100])
//
// Layout: HTML divs (.fg-gantt-bar) positioned via CSS custom properties --x, --w.
// Section labels: .fg-gantt-section-lbl positioned at their section's row band.
// No edge engine — gantt has no edges (spec §2 table).
// biome-ignore: all functions are injected into the concat bundle scope

const GANTT_TYPE = 'gantt'
// gantt uses SVG-only rendering (no HTML fd-node cards) — RD-3 table
const GANTT_CARD_DEFAULT = null

// ── date helpers ────────────────────────────────────────────────────────────

// daysSince: days elapsed since timeline.start (can be fractional; negative clamped to 0)
function ganttDaysSince(isoDate, startMs) {
  return (Date.parse(isoDate) - startMs) / 86400000
}

// barX: left offset in % within the chart area
function barX(barStart, timelineStartMs, totalDays) {
  const raw = (ganttDaysSince(barStart, timelineStartMs) / totalDays) * 100
  return Math.max(0, Math.min(100, raw))
}

// barW: width in % within the chart area
function barW(barStart, barEnd, timelineStartMs, totalDays) {
  const startPct = (ganttDaysSince(barStart, timelineStartMs) / totalDays) * 100
  const endPct = (ganttDaysSince(barEnd, timelineStartMs) / totalDays) * 100
  const raw = endPct - startPct
  return Math.max(0, Math.min(100 - startPct, raw))
}

// ── tick label generator ────────────────────────────────────────────────────

// Returns an array of { label, x } for month boundary ticks between start and end.
function ganttTicks(timelineStart, timelineEnd, totalDays) {
  const ticks = []
  const startMs = Date.parse(timelineStart)

  // Walk month boundaries from the first full month after start
  const d = new Date(Date.parse(timelineStart))
  d.setUTCDate(1)
  d.setUTCMonth(d.getUTCMonth() + 1) // first boundary after start

  const endMs = Date.parse(timelineEnd)

  const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

  while (d.getTime() <= endMs) {
    const pct = ((d.getTime() - startMs) / 86400000 / totalDays) * 100
    ticks.push({ label: MONTH_ABBR[d.getUTCMonth()], x: pct })
    d.setUTCMonth(d.getUTCMonth() + 1)
  }
  return ticks
}

// ── main renderer ───────────────────────────────────────────────────────────

// renderGantt: builds the gantt chart inside the fd-canvas element.
// Called by ganttInit (which is called by the bootstrap via window.__fdTypes).
function renderGantt(descriptor) {
  const timeline = descriptor.timeline || {}
  const sections = descriptor.sections || []
  const opts = descriptor.options || {}

  const timelineStart = timeline.start || '2026-01-01'
  const timelineEnd = timeline.end || '2026-12-31'
  const timelineStartMs = Date.parse(timelineStart)
  const totalDays = (Date.parse(timelineEnd) - timelineStartMs) / 86400000

  // Guard against invalid timeline
  if (totalDays <= 0) {
    console.warn('[fd/gantt] invalid timeline: totalDays =', totalDays)
    return
  }

  // ── layout constants ──────────────────────────────────────────────────────
  const ROW_H = 28 // px per bar row
  const SECTION_H = 22 // px for section label row
  const BAR_GUTTER = 4 // px gap between bar rows
  const CHART_LEFT_PCT = 12 // % left reserved for section labels
  const AXIS_H = 30 // px for date axis at bottom
  const TOP_PAD = 10 // px top padding

  // ── compute total height ──────────────────────────────────────────────────
  let rowCount = 0
  for (const sec of sections) {
    rowCount += 1 // section label row
    rowCount += (sec.bars || []).length
  }
  const chartH = TOP_PAD + rowCount * (ROW_H + BAR_GUTTER) + AXIS_H + 20

  // Apply computed height to the canvas (overrides descriptor.canvas.height if set)
  if (canvas) {
    canvas.style.setProperty('--fd-canvas-h', `${chartH}px`)
    canvas.style.height = `${chartH}px`
  }

  // ── render sections + bars ────────────────────────────────────────────────
  let yPx = TOP_PAD

  for (const sec of sections) {
    // Section label
    if (sec.title) {
      const lbl = document.createElement('div')
      lbl.className = 'fg-gantt-section-lbl'
      lbl.textContent = sec.title
      lbl.style.top = `${yPx + 4}px`
      lbl.style.left = '1%'
      if (canvas) canvas.appendChild(lbl)
      yPx += SECTION_H
    }

    // Bars for this section
    for (const bar of sec.bars || []) {
      const x = barX(bar.start, timelineStartMs, totalDays)
      const w = barW(bar.start, bar.end, timelineStartMs, totalDays)

      // Map to chart area (CHART_LEFT_PCT..100% column)
      // x and w are in 0..100% of totalDays; remap to the visual chart lane
      const chartW = 100 - CHART_LEFT_PCT
      const finalX = CHART_LEFT_PCT + x * (chartW / 100)
      const finalW = w * (chartW / 100)

      const el = document.createElement('div')
      el.className = `fg-gantt-bar${bar.color ? ` ${bar.color}` : ''}`
      el.id = bar.id || ''
      el.textContent = bar.label || ''
      el.title = `${bar.label}: ${bar.start} → ${bar.end}`

      // Position via inline styles (matches fgraph-base.css .fg-gantt-bar CSS var contract)
      el.style.setProperty('--x', finalX.toFixed(2))
      el.style.setProperty('--w', finalW.toFixed(2))
      el.style.top = `${yPx}px`
      // Override height to match layout constant
      el.style.height = `${ROW_H - 4}px`
      el.style.lineHeight = `${ROW_H - 4}px`

      if (canvas) canvas.appendChild(el)
      yPx += ROW_H + BAR_GUTTER
    }
  }

  // ── date axis ─────────────────────────────────────────────────────────────
  const chartW = 100 - CHART_LEFT_PCT
  const axisPct = CHART_LEFT_PCT // axis starts where chart lane starts

  const axis = document.createElement('div')
  axis.className = 'fg-gantt-axis'
  axis.style.position = 'absolute'
  axis.style.left = `${axisPct}%`
  axis.style.right = '0'
  axis.style.top = `${yPx}px`
  axis.style.height = `${AXIS_H}px`

  const baseline = document.createElement('div')
  baseline.className = 'fg-axis-date-baseline'
  axis.appendChild(baseline)

  const ticks = ganttTicks(timelineStart, timelineEnd, totalDays)
  for (const tick of ticks) {
    const tickPct = tick.x * (chartW / 100) // remap tick position to chart lane

    const tickEl = document.createElement('div')
    tickEl.className = 'fg-axis-date-tick'
    tickEl.style.left = `${tickPct.toFixed(2)}%`
    axis.appendChild(tickEl)

    const lblEl = document.createElement('div')
    lblEl.className = 'fg-axis-date-label'
    lblEl.style.left = `${tickPct.toFixed(2)}%`
    lblEl.textContent = tick.label
    axis.appendChild(lblEl)
  }

  if (canvas) canvas.appendChild(axis)

  // ── today marker ──────────────────────────────────────────────────────────
  if (opts.showToday) {
    const todayMs = Date.now()
    if (todayMs > timelineStartMs && todayMs < Date.parse(timelineEnd)) {
      const todayPct = ((todayMs - timelineStartMs) / 86400000 / totalDays) * 100
      const finalTodayX = CHART_LEFT_PCT + todayPct * (chartW / 100)

      const todayLine = document.createElement('div')
      todayLine.className = 'fg-gantt-today'
      todayLine.style.cssText = `
        position:absolute;
        left:${finalTodayX.toFixed(2)}%;
        top:0;
        bottom:0;
        width:1px;
        background:rgba(239,68,68,0.55);
        pointer-events:none;
        z-index:3;
      `
      const todayLbl = document.createElement('span')
      todayLbl.textContent = 'today'
      todayLbl.style.cssText = `
        position:absolute;
        top:2px;
        left:3px;
        font-size:8px;
        font-family:var(--mono,monospace);
        color:rgba(239,68,68,0.7);
        white-space:nowrap;
      `
      todayLine.appendChild(todayLbl)
      if (canvas) canvas.appendChild(todayLine)
    }
  }
}

// ── init ────────────────────────────────────────────────────────────────────

function ganttInit(descriptor) {
  const t = descriptor.type
  if (t !== 'gantt') {
    console.warn('[fd] gantt.js init() called with unexpected type:', t)
  }
  // Gantt bypasses node/edge engine entirely (spec RD-3 table: SVG-only / HTML divs)
  // No typeDefault card style needed
  return {
    typeDefault: GANTT_CARD_DEFAULT,
    placeZones: null,
    renderChart: renderGantt,
  }
}

// ── glob-discovery registration ──────────────────────────────────────────────
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[GANTT_TYPE] = {
  CARD_DEFAULT: GANTT_CARD_DEFAULT,
  placeZones: null,
  init: ganttInit,
  renderChart: renderGantt,
}
