// fd-bootstrap.js — universal runtime bootstrap for gen-fd.py output
// Inlined after the fd-engine IIFE bundle. Expects window.__fd + window.__fdTypes.

;(() => {
  function run() {
    var dataEl = document.getElementById('fd-data')
    if (!dataEl || !window.__fd) return

    var descriptor = JSON.parse(dataEl.textContent)
    var canvasEl = document.getElementById('fd-canvas')
    var svgEl = document.getElementById('fd-edges')
    if (!canvasEl || !svgEl) return

    var type = descriptor.type || 'architecture'
    var typeReg = window.__fdTypes && window.__fdTypes[type]
    var typeInit = typeReg && typeof typeReg.init === 'function' ? typeReg.init(descriptor) : null
    var typeDefault = (typeInit && typeInit.typeDefault) || (typeReg && typeReg.CARD_DEFAULT) || 'premium'

    if (descriptor.canvas && descriptor.canvas.height) {
      canvasEl.style.setProperty('--fd-canvas-h', descriptor.canvas.height + 'px')
      canvasEl.style.height = descriptor.canvas.height + 'px'
    }

    window.__fd.initEngine(descriptor, canvasEl, svgEl)

    // Chart-only types (gantt, pie, xychart) bypass node/edge engine
    if (typeReg && typeof typeReg.renderChart === 'function') {
      typeReg.renderChart(descriptor)
      return
    }

    window.__fd.renderNodes(descriptor, typeDefault)

    if (typeInit && typeof typeInit.positionNodes === 'function') {
      typeInit.positionNodes(descriptor)
    } else if (typeReg && typeof typeReg.positionNodes === 'function') {
      typeReg.positionNodes(descriptor)
    }

    if (typeInit && typeof typeInit.applyShapes === 'function') {
      typeInit.applyShapes(descriptor)
    } else if (typeReg && typeof typeReg.applyShapes === 'function') {
      typeReg.applyShapes(descriptor)
    }

    if (window.__fd.initMarkers && window.__fd.uniquePlanes) {
      window.__fd.initMarkers(window.__fd.uniquePlanes())
    }

    window.__fd.draw()

    var placeZonesFn = (typeInit && typeInit.placeZones) || (typeReg && typeReg.placeZones) || null
    if (typeof placeZonesFn === 'function') {
      placeZonesFn(descriptor)
    }

    window.__fd.wireResize()

    if (typeof wireHoverSpotlight === 'function' && descriptor.options && descriptor.options.spotlight !== false) {
      wireHoverSpotlight()
    }

    if (typeof wireUseCaseUI === 'function' && descriptor.useCases && descriptor.useCases.length) {
      wireUseCaseUI()
    }

    document.querySelectorAll('.ctl[data-plane]').forEach((ctl) => {
      ctl.addEventListener('click', () => {
        ctl.classList.toggle('off')
        canvasEl.classList.toggle('hide-' + ctl.dataset.plane, ctl.classList.contains('off'))
      })
    })
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(run, 80)
    })
  } else {
    setTimeout(run, 80)
  }
})()
