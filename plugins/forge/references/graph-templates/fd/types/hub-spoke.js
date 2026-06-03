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
// Delegates to the same placeZones declared in architecture.js
// (architecture.js must be bundled before hub-spoke.js when used together,
// but hub-spoke.js is the type module — architecture.js is NOT included in
// a hub-spoke bundle; placeZones is defined here to be self-contained).
//
// For zones placement in hub-spoke descriptors, placeZones is referenced
// from the shared scope; if architecture.js is also bundled as a peer
// dependency, its placeZones wins. In the typical single-type bundle,
// hub-spoke.js IS architecture.js with a different TYPE constant.
function hubSpokeInit(descriptor) {
  const t = descriptor.type
  if (t !== 'hub-spoke') {
    console.warn('[fd] hub-spoke.js init() called with unexpected type:', t)
  }
  return {
    typeDefault: HUB_SPOKE_CARD_DEFAULT,
    // placeZones is defined inline here as a copy of the architecture implementation
    // to keep hub-spoke.js self-contained (bundler loads only one type module)
    placeZones: hubSpokePlaceZones,
  }
}

// ── placeZones (copy of architecture placeZones) ──────────────────────
// Zone descriptor id == HTML element id: zone.id = "zone-hub" → getElementById("zone-hub").
function hubSpokePlaceZones(descriptor) {
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
  placeZones: hubSpokePlaceZones,
  init: hubSpokeInit,
}
