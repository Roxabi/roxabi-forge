;(() => {
  const liveWraps = Array.from(document.querySelectorAll('.fgraph-wrap[data-fgraph="live"][data-interactive="true"]'))
  if (!liveWraps.length) return

  function initWrap(wrap) {
    const nodes = Array.from(wrap.querySelectorAll('[data-node]'))
    if (!nodes.length) return

    // add tabindex for keyboard a11y
    for (const node of nodes) {
      if (!node.hasAttribute('tabindex')) node.setAttribute('tabindex', '0')
    }

    // build adjacency for spotlight: which nodes are neighbors of id
    function neighbors(id) {
      const neigh = new Set([id])
      wrap.querySelectorAll('svg.fgraph-edges path.fg-edge').forEach((p) => {
        if (p.dataset.f === id || p.dataset.t === id) {
          neigh.add(p.dataset.f)
          neigh.add(p.dataset.t)
        }
      })
      return neigh
    }

    function spotlight(id) {
      wrap.classList.add('fg-dim')
      const neigh = neighbors(id)

      nodes.forEach((n) => {
        n.classList.toggle('fg-hot', neigh.has(n.dataset.node))
      })
      wrap.querySelectorAll('svg.fgraph-edges path.fg-edge').forEach((p) => {
        const hot = p.dataset.f === id || p.dataset.t === id
        p.classList.toggle('fg-hot', hot)
      })
      wrap.querySelectorAll('svg.fgraph-edges text.fg-edge-lbl').forEach((t) => {
        const hot = t.dataset.f === id || t.dataset.t === id
        t.classList.toggle('fg-hot', hot)
      })
    }

    function clearSpot() {
      wrap.classList.remove('fg-dim')
      nodes.forEach((n) => {
        n.classList.remove('fg-hot')
      })
      wrap.querySelectorAll('svg.fgraph-edges .fg-hot').forEach((el) => {
        el.classList.remove('fg-hot')
      })
    }

    for (const node of nodes) {
      node.addEventListener('mouseenter', () => spotlight(node.dataset.node))
      node.addEventListener('mouseleave', clearSpot)
      node.addEventListener('focus', () => spotlight(node.dataset.node))
      node.addEventListener('blur', clearSpot)
    }

    // ── legend ──────────────────────────────────────────────────────
    const edgeScript = wrap.querySelector('script.fgraph-edge-data')
    if (!edgeScript) return

    let edgeDefs
    try {
      edgeDefs = JSON.parse(edgeScript.textContent)
    } catch (e) {
      console.warn('[fgraph-interact] invalid edge JSON', e)
      return
    }
    if (!Array.isArray(edgeDefs)) {
      console.warn('[fgraph-interact] edge data must be a JSON array')
      return
    }

    // collect tones present in edges + groups from nodes' data-group
    const tonesPresent = [...new Set(edgeDefs.map((e) => e.tone).filter(Boolean))]
    const groups = [...new Set(nodes.map((n) => n.dataset.group).filter(Boolean))]

    if (!tonesPresent.length) return

    const legend = document.createElement('div')
    legend.className = 'fgraph-legend fgraph-legend--live'

    for (const tone of tonesPresent) {
      const chip = document.createElement('button')
      chip.type = 'button'
      chip.className = `fg-legend-chip ${tone}`
      chip.textContent = tone
      chip.dataset.tone = tone
      chip.setAttribute('aria-pressed', 'false')
      chip.addEventListener('click', () => {
        const active = chip.classList.toggle('fg-legend-chip--off')
        chip.setAttribute('aria-pressed', String(active))
        wrap.classList.toggle(`fg-hide-${tone}`, active)
      })
      legend.appendChild(chip)
    }

    // track hidden groups for re-apply after redraw
    if (!wrap.__fgHiddenGroups) wrap.__fgHiddenGroups = new Set()

    wrap.__fgReapplyHidden = () => {
      wrap.querySelectorAll('svg.fgraph-edges path.fg-edge, svg.fgraph-edges text.fg-edge-lbl').forEach((el) => {
        const inHiddenGroup = wrap.__fgHiddenGroups.has(el.dataset.f) || wrap.__fgHiddenGroups.has(el.dataset.t)
        el.classList.toggle('fg-edge-hidden', inHiddenGroup)
      })
    }

    for (const group of groups) {
      const chip = document.createElement('button')
      chip.type = 'button'
      chip.className = 'fg-legend-chip fg-legend-chip--group'
      chip.textContent = group
      chip.dataset.group = group
      chip.setAttribute('aria-pressed', 'false')
      const groupIds = new Set(nodes.filter((n) => n.dataset.group === group).map((n) => n.dataset.node))
      chip.addEventListener('click', () => {
        const hidden = chip.classList.toggle('fg-legend-chip--off')
        chip.setAttribute('aria-pressed', String(hidden))
        nodes.forEach((n) => {
          if (groupIds.has(n.dataset.node)) n.classList.toggle('fg-group-hidden', hidden)
        })
        // update hidden-group tracking set and re-apply
        groupIds.forEach((id) => {
          if (hidden) wrap.__fgHiddenGroups.add(id)
          else wrap.__fgHiddenGroups.delete(id)
        })
        wrap.__fgReapplyHidden()
      })
      legend.appendChild(chip)
    }

    wrap.appendChild(legend)
  }

  function init() {
    for (const wrap of liveWraps) initWrap(wrap)
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init)
  } else {
    init()
  }
})()
