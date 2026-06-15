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
    if (!Array.isArray(edgeDefs)) {
      console.warn('[fgraph-auto] edge data must be a JSON array')
      return
    }

    // size svg to wrap px
    const wrapW = wrap.offsetWidth
    const wrapH = wrap.offsetHeight
    svg.setAttribute('viewBox', `0 0 ${wrapW} ${wrapH}`)
    svg.removeAttribute('preserveAspectRatio')
    // decorative edge layer — node cards carry the semantic content; hide the SVG
    // (and its <text> labels) from the a11y tree so labels aren't announced out of
    // reading-order context
    svg.setAttribute('aria-hidden', 'true')

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

    // Pass 1: draw all paths + create all label <text> at naive midpoints.
    // Labels must be in the DOM before getBBox() is valid (below in Pass 2).
    const labelEntries = []

    for (const edge of edgeDefs) {
      const fEl = nodeMap[edge.f]
      const tEl = nodeMap[edge.t]
      if (!fEl || !tEl) continue
      if (edge.f === edge.t) continue

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

      const tone = TONES.includes(edge.tone) ? edge.tone : 'dim'
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
        labelEntries.push({ textEl: tx, x1, y1, x2, y2, lx, ly })
      }
    }

    // Pass 2: nudge labels that straddle a .fgraph-group border line.
    // For each label, we check if its bounding box overlaps any group's border band
    // (the 4 thin edge regions of the group rect). If so, nudge the label along the
    // border-perpendicular axis (x for left/right borders, y for top/bottom) to the
    // closer side — either fully inside or fully outside the group.
    if (labelEntries.length > 0) {
      const MARGIN = 6 // px clearance applied past the border after a nudge
      const BAND = 4 // ≈ half the ~9.5px label font-size; defines the straddle half-zone on each side of a border
      const wb = wrap.getBoundingClientRect()
      // F2 guard: skip pass-2 entirely when the wrap has no layout yet (zero geometry
      // from getBoundingClientRect means the DOM hasn't been sized — labels stay at
      // their naive midpoints, which is correct for an unsized wrap).
      if (wb.width !== 0 && wb.height !== 0) {
        // collect group rects in wrap-relative px (same coordinate space as SVG user units)
        const groupRects = []
        wrap.querySelectorAll('.fgraph-group').forEach((g) => {
          const gb = g.getBoundingClientRect()
          groupRects.push({
            left: gb.left - wb.left,
            top: gb.top - wb.top,
            right: gb.right - wb.left,
            bottom: gb.bottom - wb.top,
          })
        })

        if (groupRects.length > 0) {
          for (const entry of labelEntries) {
            const { textEl } = entry
            let { lx, ly } = entry

            const bb = textEl.getBBox()
            // F2 guard: skip this label when getBBox() returns zero (text not yet laid out).
            if (bb.width === 0 && bb.height === 0) continue
            const lblLeft = bb.x
            const lblTop = bb.y
            const lblRight = bb.x + bb.width
            const lblBottom = bb.y + bb.height
            const lblCx = (lblLeft + lblRight) / 2
            const lblCy = (lblTop + lblBottom) / 2

            let nudgeX = 0
            let nudgeY = 0

            for (const gr of groupRects) {
              // Quick overlap check: label must overlap the group rect at all
              if (lblRight < gr.left || lblLeft > gr.right) continue
              if (lblBottom < gr.top || lblTop > gr.bottom) continue

              // Evaluate BOTH axes independently so corner labels (near two borders of
              // the same group) get nudged on both axes. Break after this group so we
              // don't double-nudge from a different group (F3).

              // ── right border ──────────────────────────────────────────────
              // straddles if label's own half-extent crosses gr.right (F4)
              if (Math.abs(lblCx - gr.right) < BAND + bb.width / 2) {
                // Move label center to the side that needs LESS displacement.
                // Option A: push right (outside group)  → target cx = gr.right + MARGIN + bb.width/2
                // Option B: push left  (inside group)   → target cx = gr.right - MARGIN - bb.width/2
                const toRight = gr.right + MARGIN + bb.width / 2 - lblCx
                const toLeft = gr.right - MARGIN - bb.width / 2 - lblCx
                nudgeX = Math.abs(toRight) <= Math.abs(toLeft) ? toRight : toLeft
              }

              // ── left border ───────────────────────────────────────────────
              if (nudgeX === 0 && Math.abs(lblCx - gr.left) < BAND + bb.width / 2) {
                const toRight = gr.left + MARGIN + bb.width / 2 - lblCx
                const toLeft = gr.left - MARGIN - bb.width / 2 - lblCx
                nudgeX = Math.abs(toRight) <= Math.abs(toLeft) ? toRight : toLeft
              }

              // ── bottom border ─────────────────────────────────────────────
              if (Math.abs(lblCy - gr.bottom) < BAND + bb.height / 2) {
                const toDown = gr.bottom + MARGIN + bb.height / 2 - lblCy
                const toUp = gr.bottom - MARGIN - bb.height / 2 - lblCy
                nudgeY = Math.abs(toDown) <= Math.abs(toUp) ? toDown : toUp
              }

              // ── top border ────────────────────────────────────────────────
              if (nudgeY === 0 && Math.abs(lblCy - gr.top) < BAND + bb.height / 2) {
                const toDown = gr.top + MARGIN + bb.height / 2 - lblCy
                const toUp = gr.top - MARGIN - bb.height / 2 - lblCy
                nudgeY = Math.abs(toDown) <= Math.abs(toUp) ? toDown : toUp
              }

              // Break after the first matching group (both axes evaluated — F3).
              if (nudgeX !== 0 || nudgeY !== 0) break
            }

            if (nudgeX !== 0 || nudgeY !== 0) {
              lx += nudgeX
              ly += nudgeY
              textEl.setAttribute('x', lx)
              textEl.setAttribute('y', ly)
            }
          }
        }
      } // end F2 degenerate-geometry guard (wb.width !== 0 && wb.height !== 0)
    }

    if (typeof wrap.__fgReapplyHidden === 'function') wrap.__fgReapplyHidden()
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
    // ResizeObserver fires once synchronously on observe(); the eager draw above
    // already covered that, so skip the first callback to avoid a redundant draw
    let firstResize = true
    new ResizeObserver(() => {
      if (firstResize) {
        firstResize = false
        return
      }
      scheduleRedraw(wrap)
    }).observe(wrap)
  }
})()
