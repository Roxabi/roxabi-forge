// fd/types/hub-spoke.js — hub-spoke type (alias for architecture)
// The hub-spoke diagram type uses the same layout engine as architecture.
// This file satisfies the bundler's filename-based type resolution (RD-4):
//   buildEngine(fdDir, 'hub-spoke') → includes fd/types/hub-spoke.js
// The runtime type registration at the end of architecture.js also registers
// window.__fdTypes['hub-spoke'] = window.__fdTypes['architecture'], but
// that registration only exists after architecture.js is concatenated —
// this file must be the type module loaded when type='hub-spoke' is requested.

const HUB_SPOKE_TYPE = 'hub-spoke'
const HUB_SPOKE_CARD_DEFAULT = 'premium' // RD-3: hub-spoke default is premium

// ── init ──────────────────────────────────────────────────────────────
// Called by the fd-engine bootstrap after parsing fd-data.
// hub-spoke.js is the sole type module in a hub-spoke bundle (RD-4 disjoint
// footprints — architecture.js is NOT included). placeZones is defined here
// at the top level so edges.js `typeof placeZones === 'function'` resolves.
function hubSpokeInit(descriptor) {
  const t = descriptor.type
  if (t !== 'hub-spoke') {
    console.warn('[fd] hub-spoke.js init() called with unexpected type:', t)
  }
  return {
    typeDefault: HUB_SPOKE_CARD_DEFAULT,
    placeZones,
  }
}

// ── placeZones ────────────────────────────────────────────────────────
// Top-level name required by the edges.js seam contract:
//   if (typeof placeZones === 'function') placeZones(DESCRIPTOR)
// Zone descriptor id == HTML element id: zone.id = "zone-hub" → getElementById("zone-hub").
function placeZones(descriptor) {
  const zones = descriptor.zones
  if (!zones || zones.length === 0) return

  for (const zone of zones) {
    let zEl = document.getElementById(zone.id)
    if (!zEl) {
      zEl = document.createElement('div')
      zEl.id = zone.id
      let cls = 'fd-zone'
      if (zone.class) cls += ` ${zone.class}`
      zEl.className = cls

      if (zone.label) {
        const lbl = document.createElement('span')
        lbl.className = 'fd-zone-label'
        lbl.textContent = zone.label
        zEl.appendChild(lbl)
      }

      canvas.insertBefore(zEl, canvas.firstChild)
    }

    const memberIds = zone.nodes || []
    if (memberIds.length === 0) continue

    const rects = memberIds.map((id) => (nodeEl[id] ? rect(id) : null)).filter(Boolean)
    if (rects.length === 0) continue

    const padX = 16
    const padYT = 20
    const padYB = 12

    const xMin = Math.min(...rects.map((r) => r.cx - r.w / 2))
    const xMax = Math.max(...rects.map((r) => r.cx + r.w / 2))
    const yMin = Math.min(...rects.map((r) => r.cy - r.h / 2))
    const yMax = Math.max(...rects.map((r) => r.cy + r.h / 2))

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

// ── glob-discovery registration ───────────────────────────────────────
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[HUB_SPOKE_TYPE] = {
  CARD_DEFAULT: HUB_SPOKE_CARD_DEFAULT,
  placeZones,
  init: hubSpokeInit,
}
