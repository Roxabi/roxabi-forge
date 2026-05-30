;(() => {
  const NS = 'http://www.w3.org/2000/svg'
  const TONES = ['cyan', 'orange', 'purple', 'green', 'red', 'amber', 'dim']

  // rect of [data-node] relative to wrap element
  function rect(el, wrap) {
    const wb = wrap.getBoundingClientRect()
    const b = el.getBoundingClientRect()
    return {
      cx: b.left - wb.left + b.width / 2,
      cy: b.top - wb.top + b.height / 2,
      w: b.width,
      h: b.height,
    }
  }

  // ray-rectangle intersection: exit point from r toward (tx,ty)
  function anchor(r, tx, ty) {
    const dx = tx - r.cx,
      dy = ty - r.cy
    const hw = r.w / 2,
      hh = r.h / 2
    const sx = dx === 0 ? 1e9 : hw / Math.abs(dx)
    const sy = dy === 0 ? 1e9 : hh / Math.abs(dy)
    const s = Math.min(sx, sy)
    return [r.cx + dx * s, r.cy + dy * s]
  }

  // ensure <defs> in svg contains all needed markers
  function ensureMarkers(svg) {
    let defs = svg.querySelector('defs')
    if (!defs) {
      defs = document.createElementNS(NS, 'defs')
      svg.prepend(defs)
    }
    for (const tone of TONES) {
      const id = `fg-arr-${tone}--live`
      if (defs.querySelector(`#${id}`)) continue
      const mk = document.createElementNS(NS, 'marker')
      mk.setAttribute('id', id)
      mk.setAttribute('viewBox', '0 0 10 10')
      mk.setAttribute('refX', '9')
      mk.setAttribute('refY', '5')
      mk.setAttribute('markerUnits', 'userSpaceOnUse')
      mk.setAttribute('markerWidth', '8')
      mk.setAttribute('markerHeight', '8')
      mk.setAttribute('orient', 'auto')
      const path = document.createElementNS(NS, 'path')
      path.setAttribute('d', 'M0,0 L10,5 L0,10 z')
      path.setAttribute('class', `mk-${tone}`)
      mk.appendChild(path)
      defs.appendChild(mk)
    }
  }

  function drawWrap(wrap) {
    const svg = wrap.querySelector('svg.fgraph-edges[data-coord="px"]')
    if (!svg) return

    const edgeScript = wrap.querySelector('script.fgraph-edge-data')
    if (!edgeScript) return

    let edgeDefs
    try {
      edgeDefs = JSON.parse(edgeScript.textContent)
    } catch (e) {
      console.warn('[fgraph-auto] invalid edge JSON', e)
      return
    }

    // size svg to wrap px
    const wrapW = wrap.offsetWidth
    const wrapH = wrap.offsetHeight
    svg.setAttribute('viewBox', `0 0 ${wrapW} ${wrapH}`)
    svg.removeAttribute('preserveAspectRatio')

    ensureMarkers(svg)

    // clear previously generated paths/text (keep defs)
    svg.querySelectorAll('path.fg-edge, text.fg-edge-lbl').forEach((n) => {
      n.remove()
    })

    // index nodes
    const nodeMap = {}
    wrap.querySelectorAll('[data-node]').forEach((el) => {
      nodeMap[el.dataset.node] = el
    })

    for (const edge of edgeDefs) {
      const fEl = nodeMap[edge.f]
      const tEl = nodeMap[edge.t]
      if (!fEl || !tEl) continue

      const rf = rect(fEl, wrap)
      const rt = rect(tEl, wrap)
      const [x1, y1] = anchor(rf, rt.cx, rt.cy)
      const [x2, y2] = anchor(rt, rf.cx, rf.cy)

      // axis-aware cubic bezier
      const vert = Math.abs(y2 - y1) > Math.abs(x2 - x1)
      let d
      if (vert) {
        const my = (y1 + y2) / 2
        d = `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`
      } else {
        const mx = (x1 + x2) / 2
        d = `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`
      }

      const tone = edge.tone || 'dim'
      const mods = Array.isArray(edge.mods) ? edge.mods : []
      const cls = ['fg-edge', tone, ...mods].join(' ')
      const mid = `fg-arr-${tone}--live`

      const p = document.createElementNS(NS, 'path')
      p.setAttribute('d', d)
      p.setAttribute('class', cls)
      p.setAttribute('marker-end', `url(#${mid})`)
      p.dataset.f = edge.f
      p.dataset.t = edge.t
      p.dataset.tone = tone
      svg.appendChild(p)

      if (edge.label) {
        const lx = (x1 + x2) / 2
        const ly = (y1 + y2) / 2 - 6
        const tx = document.createElementNS(NS, 'text')
        tx.setAttribute('x', lx)
        tx.setAttribute('y', ly)
        tx.setAttribute('text-anchor', 'middle')
        tx.setAttribute('class', `fg-edge-lbl ${tone}`)
        tx.dataset.f = edge.f
        tx.dataset.t = edge.t
        tx.textContent = edge.label
        svg.appendChild(tx)
      }
    }
  }

  // collect all live wraps; return early if none
  const liveWraps = Array.from(document.querySelectorAll('.fgraph-wrap[data-fgraph="live"]'))
  if (!liveWraps.length) return

  // per-wrap RAF slot — multiple live diagrams on one page each debounce independently
  const rafByWrap = new Map()
  function scheduleRedraw(wrap) {
    if (rafByWrap.has(wrap)) cancelAnimationFrame(rafByWrap.get(wrap))
    rafByWrap.set(
      wrap,
      requestAnimationFrame(() => {
        rafByWrap.delete(wrap)
        drawWrap(wrap)
      }),
    )
  }

  // initial draw + resize observer per wrap
  for (const wrap of liveWraps) {
    window.addEventListener('load', () => drawWrap(wrap))
    drawWrap(wrap) // also attempt eagerly (after script eval)
    new ResizeObserver(() => scheduleRedraw(wrap)).observe(wrap)
  }
})()
