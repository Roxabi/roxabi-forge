/**
 * craft-anchors.js — data-driven SVG edges for hand-authored craft diagrams.
 * Inline into diagrams/*.html (file:// safe). Recomputes paths from DOM positions.
 *
 * Markup:
 *   <div class="diagram" data-canvas-width="960" data-canvas-height="640">
 *     <div class="spoke" data-anchor="feedback">…</div>
 *     <div class="hub" data-anchor="hub">…</div>
 *     <svg class="craft-connections" aria-hidden="true"></svg>
 *   </div>
 *   craft-edges JSON in a separate script[type=application/json] block
 *
 * Edge JSON:
 *   {
 *     "viewBox": "0 0 960 640",
 *     "edges": [
 *       { "from": "feedback", "to": "hub", "class": "connection active", "curve": "q" },
 *       { "from": "hub", "to": "github", "class": "connection active", "curve": "q" },
 *       { "from": "prod", "to": "staging", "class": "connection green", "curve": "h", "y": 478 }
 *     ]
 *   }
 *
 * curve: "l" straight | "q" quadratic bezier toward target | "h" horizontal at y (use edge.y)
 */
;((global) => {
  function parseEdges() {
    var el = document.getElementById('craft-edges')
    if (!el) return null
    try {
      return JSON.parse(el.textContent)
    } catch (e) {
      console.warn('[craft-anchors] invalid craft-edges JSON', e)
      return null
    }
  }

  function canvasSize(diagram) {
    var w = parseFloat(diagram.dataset.canvasWidth || '960')
    var h = parseFloat(diagram.dataset.canvasHeight || '640')
    return { w: w, h: h }
  }

  function centerInCanvas(el, diagram) {
    var d = diagram.getBoundingClientRect()
    var r = el.getBoundingClientRect()
    var size = canvasSize(diagram)
    var sx = size.w / d.width
    var sy = size.h / d.height
    return {
      x: ((r.left + r.right) / 2 - d.left) * sx,
      y: ((r.top + r.bottom) / 2 - d.top) * sy,
    }
  }

  /** Rim point on card rect toward target — lines attach to edges, not centers */
  function rimPoint(el, diagram, toward) {
    var c = centerInCanvas(el, diagram)
    var d = diagram.getBoundingClientRect()
    var r = el.getBoundingClientRect()
    var size = canvasSize(diagram)
    var sx = size.w / d.width
    var sy = size.h / d.height
    var hw = (r.width * sx) / 2
    var hh = (r.height * sy) / 2
    var dx = toward.x - c.x
    var dy = toward.y - c.y
    if (dx === 0 && dy === 0) return c
    var t = Math.min(dx !== 0 ? hw / Math.abs(dx) : Infinity, dy !== 0 ? hh / Math.abs(dy) : Infinity)
    return { x: c.x + dx * t, y: c.y + dy * t }
  }

  function pathForEdge(from, to, edge) {
    var curve = edge.curve || 'q'
    if (curve === 'h') {
      var y = edge.y != null ? edge.y : (from.y + to.y) / 2
      return (
        'M ' + from.x + ' ' + from.y + ' L ' + from.x + ' ' + y + ' L ' + to.x + ' ' + y + ' L ' + to.x + ' ' + to.y
      )
    }
    if (curve === 'l') {
      return 'M ' + from.x + ' ' + from.y + ' L ' + to.x + ' ' + to.y
    }
    var mx = (from.x + to.x) / 2
    var my = (from.y + to.y) / 2
    var cx = mx + (from.y - to.y) * 0.12
    var cy = my + (to.x - from.x) * 0.12
    return 'M ' + from.x + ' ' + from.y + ' Q ' + cx + ' ' + cy + ' ' + to.x + ' ' + to.y
  }

  function render(diagram) {
    var spec = parseEdges()
    if (!spec || !spec.edges) return
    var svg = diagram.querySelector('svg.craft-connections')
    if (!svg) return

    var size = canvasSize(diagram)
    var vb = spec.viewBox || '0 0 ' + size.w + ' ' + size.h
    svg.setAttribute('viewBox', vb)
    svg.innerHTML = ''

    var anchors = {}
    diagram.querySelectorAll('[data-anchor]').forEach((node) => {
      anchors[node.dataset.anchor] = node
    })

    spec.edges.forEach((edge) => {
      var a = anchors[edge.from]
      var b = anchors[edge.to]
      if (!a || !b) {
        console.warn('[craft-anchors] missing anchor', edge.from, edge.to)
        return
      }
      var bc = centerInCanvas(b, diagram)
      var ac = centerInCanvas(a, diagram)
      var from = rimPoint(a, diagram, bc)
      var to = rimPoint(b, diagram, ac)
      var path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
      path.setAttribute('d', pathForEdge(from, to, edge))
      path.setAttribute('class', edge.class || 'connection')
      svg.appendChild(path)
    })
  }

  function validateBounds(diagram) {
    var size = canvasSize(diagram)
    var issues = []
    diagram.querySelectorAll('[data-anchor]').forEach((node) => {
      var c = centerInCanvas(node, diagram)
      var pad = 8
      if (c.x < pad || c.y < pad || c.x > size.w - pad || c.y > size.h - pad) {
        issues.push('anchor "' + node.dataset.anchor + '" near/outside canvas')
      }
    })
    if (issues.length) console.warn('[craft-anchors] bounds:', issues.join('; '))
    return issues
  }

  function notifyResize(diagram, slug) {
    if (!slug || global.parent === global) return
    var h = Math.max(document.body.scrollHeight, diagram.offsetHeight + 80)
    global.parent.postMessage({ type: 'forge-diagram-resize', id: slug, height: h }, '*')
  }

  function boot() {
    var diagram = document.querySelector('.diagram[data-canvas-width]') || document.querySelector('.diagram')
    if (!diagram) return
    var slug = diagram.dataset.slug || ''

    function redraw() {
      render(diagram)
      validateBounds(diagram)
      notifyResize(diagram, slug)
    }

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(redraw)
    } else {
      redraw()
    }
    global.addEventListener('resize', redraw)
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot)
  } else {
    boot()
  }

  global.CraftAnchors = { render: render, validateBounds: validateBounds }
})(typeof window !== 'undefined' ? window : globalThis)
