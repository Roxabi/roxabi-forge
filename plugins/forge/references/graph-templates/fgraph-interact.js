;(() => {
  const liveWraps = Array.from(document.querySelectorAll('.fgraph-wrap[data-fgraph="live"][data-interactive="true"]'))
  if (!liveWraps.length) return

  function initWrap(wrap) {
    // idempotent guard: a legend means this wrap was already initialised — bail
    // to avoid a duplicate legend + double listeners if the script is inlined twice
    if (wrap.querySelector('.fgraph-legend--live')) return
    const nodes = Array.from(wrap.querySelectorAll('[data-node]'))
    if (!nodes.length) return

    // tabindex + accessible name for keyboard a11y (focus → spotlight)
    for (const node of nodes) {
      if (!node.hasAttribute('tabindex')) node.setAttribute('tabindex', '0')
      if (!node.hasAttribute('aria-label')) {
        const titleEl = node.querySelector('.fgraph-title')
        const name = (titleEl ? titleEl.textContent : '').trim() || node.dataset.node
        node.setAttribute('aria-label', name)
      }
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
    // restrict to the 7 reserved tones (mirror of fgraph-auto.js TONES); an unknown
    // tone has no CSS rule, so a chip for it would be a dead toggle
    const TONES = ['cyan', 'orange', 'purple', 'green', 'red', 'amber', 'dim']
    const tonesPresent = [...new Set(edgeDefs.map((e) => e.tone).filter((t) => TONES.includes(t)))]
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
      // aria-pressed = filter engaged = tone SHOWN. Tone starts visible → pressed.
      // classList.toggle returns true when the chip goes OFF (hidden) → pressed=!hidden.
      chip.setAttribute('aria-pressed', 'true')
      chip.setAttribute('aria-label', `Hide ${tone} edges`)
      chip.addEventListener('click', () => {
        const hidden = chip.classList.toggle('fg-legend-chip--off')
        chip.setAttribute('aria-pressed', String(!hidden))
        chip.setAttribute('aria-label', hidden ? `Show ${tone} edges` : `Hide ${tone} edges`)
        wrap.classList.toggle(`fg-hide-${tone}`, hidden)
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
