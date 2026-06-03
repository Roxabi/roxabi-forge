// fd/types/architecture.js — declarative layout handler + zone placement
// Glob-discovery: bundler.js discovers this file via glob('fd/types/*.js').
// Exports TYPE so bundler can key it: window.__fdTypes[TYPE] = { CARD_DEFAULT, placeZones, init }

const TYPE = 'architecture'
const CARD_DEFAULT = 'premium' // RD-3: architecture/hub-spoke default is premium

// ── placeZones ────────────────────────────────────────────────────────
// Generalised from lyra-stack-v2.html placeZone() lines 693–718.
// Parametric over descriptor.zones[] instead of hardcoded ids.
//
// For each zone:
//   1. Collect rect() measurements for all member nodes.
//   2. Compute union bounding box (min/max of cx±w/2, cy±h/2) + padding.
//   3. Apply left/top/width/height to zone div#fd-zone-{zone.id}.
//   4. Create the zone div if absent (class: fd-zone + zone.class).
//
// rect() is declared in core.js scope (concat order: core.js, cards.js, architecture.js).
function placeZones(descriptor) {
  const zones = descriptor.zones
  if (!zones || zones.length === 0) return

  for (const zone of zones) {
    // resolve or create zone div
    let zEl = document.getElementById(`fd-zone-${zone.id}`)
    if (!zEl) {
      zEl = document.createElement('div')
      zEl.id = `fd-zone-${zone.id}`
      let cls = 'fd-zone'
      if (zone.class) cls += ` ${zone.class}`
      zEl.className = cls

      // inject zone label if provided
      if (zone.label) {
        const lbl = document.createElement('span')
        lbl.className = 'fd-zone-label'
        lbl.textContent = zone.label
        zEl.appendChild(lbl)
      }

      canvas.insertBefore(zEl, canvas.firstChild)
    }

    // measure member nodes
    const memberIds = zone.nodes || []
    if (memberIds.length === 0) continue

    const rects = memberIds.map((id) => rect(id)).filter(Boolean)
    if (rects.length === 0) continue

    // union bounding box
    const xMin = Math.min(...rects.map((r) => r.cx - r.w / 2))
    const xMax = Math.max(...rects.map((r) => r.cx + r.w / 2))
    const yMin = Math.min(...rects.map((r) => r.cy - r.h / 2))
    const yMax = Math.max(...rects.map((r) => r.cy + r.h / 2))

    // padding: horizontal 16px, vertical top 20px / bottom 12px (from lyra-stack-v2 reference)
    const padX = 16
    const padYT = 20
    const padYB = 12

    const left = xMin - padX
    const top = yMin - padYT
    const width = xMax + padX - left
    const height = yMax + padYB - top

    zEl.style.left = `${left}px`
    zEl.style.top = `${top}px`
    zEl.style.width = `${width}px`
    zEl.style.height = `${height}px`
  }
}

// ── init ──────────────────────────────────────────────────────────────
// Called by the fd-engine bootstrap after parsing fd-data.
// Returns { typeDefault, placeZones } consumed by the engine orchestrator.
function init(descriptor) {
  const t = descriptor.type
  if (t !== 'architecture' && t !== 'hub-spoke') {
    console.warn('[fd] architecture.js init() called with unexpected type:', t)
  }
  // layout is declarative — no elk step; x/y already in descriptor
  return {
    typeDefault: CARD_DEFAULT,
    placeZones,
  }
}

// ── glob-discovery registration ───────────────────────────────────────
// bundler.js discovers fd/types/*.js and concatenates them into the
// inline <script>. At runtime each type module self-registers here.
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[TYPE] = { CARD_DEFAULT, placeZones, init }
// 'hub-spoke' is an alias for 'architecture'
window.__fdTypes['hub-spoke'] = window.__fdTypes[TYPE]
