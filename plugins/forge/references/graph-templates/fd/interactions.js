// fd/interactions.js — Layer 5: spotlight, use-case step sequencer, sidebar
// Lifted from lyra-stack-v2.html lines 720-974 and adapted for the
// fd-engine descriptor-driven contract.
//
// Spotlight (hover): dimmed class on canvas, hot class on touched edges + neighbor nodes.
// Use-case animation: descriptor.useCases[] → step sequencer (play/pause/reset/replay).
// Sidebar: optional (descriptor.options.sidebar); falls back gracefully when absent.
//
// Concat order: core.js → edges.js → cards.js → particles.js → interactions.js → types/{type}.js
// Depends on: canvas, nodeEl, paths, pathByPair, pairKey, svg — core.js/edges.js scope.
//             spawnParticle, clearParticle — particles.js scope.
//             DESCRIPTOR — core.js scope.
//
// Guard: zero occurrences of the banned lowercase token in this file.

// ── spotlight (hover) ─────────────────────────────────────────────────────
// Adapted from lyra-stack-v2.html l.720-751.
// sidebar: optional; nodeData: the node descriptor object for the hovered node.

function spotlight(nodeData) {
  canvas.classList.add('dimmed')
  const id = nodeData.id
  const neigh = {}
  neigh[id] = true

  paths.forEach((p) => {
    const on = p.dataset.f === id || p.dataset.t === id
    p.classList.toggle('hot', on)
    if (on) {
      neigh[p.dataset.f] = true
      neigh[p.dataset.t] = true
    }
  })

  // edge labels follow their path
  svg.querySelectorAll('text[data-pk]').forEach((t) => {
    const pk = t.dataset.pk
    const p = pathByPair.get(pk)
    t.classList.toggle('hot', p?.classList.contains('hot') ?? false)
  })

  Object.keys(nodeEl).forEach((k) => {
    nodeEl[k].classList.toggle('hot', !!neigh[k])
  })

  // sidebar header: update if sidebar exists
  const sbHeader = document.getElementById('sbHeader')
  if (sbHeader) {
    const hostStr = !nodeData.h || nodeData.h === 'EX' ? 'external' : nodeData.h === 'M1' ? 'M&#x2081;' : 'M&#x2082;'
    sbHeader.innerHTML =
      `<h4>${nodeData.n}</h4>` +
      (nodeData.img ? `<div class="fd-img">${nodeData.img}</div>` : '') +
      `<dl><dt>plane</dt><dd>${nodeData.plane || '&#x2014;'}</dd>` +
      `<dt>host</dt><dd>${hostStr}</dd>` +
      `<dt>role</dt><dd>${nodeData.d || '&#x2014;'}</dd></dl>`
  }
}

function clearSpot() {
  canvas.classList.remove('dimmed')
  paths.forEach((p) => {
    p.classList.remove('hot')
  })
  svg.querySelectorAll('text').forEach((t) => {
    t.classList.remove('hot')
  })
  Object.values(nodeEl).forEach((el) => {
    el.classList.remove('hot')
  })

  // reset sidebar header to default hint
  const sbHeader = document.getElementById('sbHeader')
  if (sbHeader) {
    sbHeader.innerHTML =
      '<h4>Hover = detail</h4>' +
      '<div class="hint">Hover a node to isolate its edges and see image / host / role.<br>Select a use case to animate the flow.</div>'
  }
}

// ── use-case step sequencer ───────────────────────────────────────────────
// Adapted from lyra-stack-v2.html l.770-974.
// State machine: 'none' | 'ready' | 'playing' | 'paused' | 'done'
// Only wired when descriptor.useCases is present.

let _ucActiveIdx = null
let _ucState = 'none'
let _ucTimer = null
let _ucStepIdx = 0

function _syncUcButtons() {
  const ucPlay = document.getElementById('ucPlay')
  const ucReset = document.getElementById('ucReset')
  if (!ucPlay) return
  switch (_ucState) {
    case 'none':
      ucPlay.textContent = '▶ play'
      ucPlay.disabled = true
      if (ucReset) ucReset.classList.remove('visible')
      break
    case 'ready':
      ucPlay.textContent = '▶ play'
      ucPlay.disabled = false
      if (ucReset) ucReset.classList.remove('visible')
      break
    case 'playing':
      ucPlay.textContent = '⏸ pause'
      ucPlay.disabled = false
      if (ucReset) ucReset.classList.remove('visible')
      break
    case 'paused':
      ucPlay.textContent = '▶ resume'
      ucPlay.disabled = false
      if (ucReset) ucReset.classList.add('visible')
      break
    case 'done':
      ucPlay.textContent = '↺ replay'
      ucPlay.disabled = false
      if (ucReset) ucReset.classList.remove('visible')
      break
  }
}

function _resetUcVisuals() {
  Object.values(nodeEl).forEach((el) => {
    el.classList.remove('uc-active', 'uc-done')
  })
  paths.forEach((p) => {
    p.classList.remove('uc-active', 'uc-done')
  })
  canvas.classList.remove('dimmed')
  // clear particle (particles.js)
  if (typeof clearParticle === 'function') clearParticle()

  const ucStepsList = document.getElementById('ucStepsList')
  if (ucStepsList) {
    ucStepsList.querySelectorAll('li').forEach((li) => {
      li.classList.remove('step-active', 'step-done')
    })
  }
}

function _stopUcTimer() {
  if (_ucTimer) {
    clearTimeout(_ucTimer)
    _ucTimer = null
  }
}

function _selectUc(idx) {
  _stopUcTimer()
  _resetUcVisuals()
  _ucActiveIdx = idx
  _ucStepIdx = 0
  _ucState = 'ready'

  const uc = DESCRIPTOR.useCases[idx]
  const ucTitle = document.getElementById('ucTitle')
  const ucDesc = document.getElementById('ucDesc')
  const ucStepsList = document.getElementById('ucStepsList')
  const sbUc = document.getElementById('sbUc')

  if (ucTitle) ucTitle.textContent = uc.title
  if (ucDesc) ucDesc.innerHTML = uc.desc
  if (ucStepsList) {
    ucStepsList.innerHTML = ''
    uc.steps.forEach((s, i) => {
      const li = document.createElement('li')
      li.innerHTML = `<span class="sn">${String(i + 1).padStart(2, '0')}</span>${s.label}`
      ucStepsList.appendChild(li)
    })
  }
  if (sbUc) sbUc.classList.add('visible')

  document.querySelectorAll('.uc-btn').forEach((b) => {
    b.classList.toggle('active', Number(b.dataset.uc) === idx)
  })
  _syncUcButtons()
}

function _applyUcStep(stepIdx) {
  const uc = DESCRIPTOR.useCases[_ucActiveIdx]
  if (stepIdx >= uc.steps.length) {
    _ucState = 'done'
    _syncUcButtons()
    return
  }
  _ucStepIdx = stepIdx
  const step = uc.steps[stepIdx]
  canvas.classList.add('dimmed')

  // mark previous steps done (verbatim from lyra-stack-v2)
  for (let i = 0; i < stepIdx; i++) {
    uc.steps[i].nodes.forEach((id) => {
      if (nodeEl[id]) {
        nodeEl[id].classList.remove('uc-active')
        nodeEl[id].classList.add('uc-done')
      }
    })
    if (uc.steps[i].edge) {
      const prevEf = uc.steps[i].edge[0]
      const prevEt = uc.steps[i].edge[1]
      const prevPp = pathByPair.get(pairKey(prevEf, prevEt))
      if (prevPp) {
        prevPp.classList.remove('uc-active')
        prevPp.classList.add('uc-done')
      }
    }
  }

  // activate current step nodes
  step.nodes.forEach((id) => {
    if (nodeEl[id]) nodeEl[id].classList.add('uc-active', 'hot')
  })

  // activate edge + spawn particle if particles opt-in
  if (typeof clearParticle === 'function') clearParticle()
  if (step.edge) {
    const ef = step.edge[0]
    const et = step.edge[1]
    const pp = pathByPair.get(pairKey(ef, et))
    if (pp) {
      pp.classList.add('uc-active', 'hot')
      // spawn particle if particles enabled and spawnParticle available
      if (typeof spawnParticle === 'function' && DESCRIPTOR.options && DESCRIPTOR.options.particles !== false) {
        // Find plane from edges
        const edges = DESCRIPTOR.edges || []
        let edgeDef = null
        for (let j = 0; j < edges.length; j++) {
          const ed = edges[j]
          if ((ed.f === ef && ed.t === et) || (ed.f === et && ed.t === ef)) {
            edgeDef = ed
            break
          }
        }
        const plane = edgeDef ? edgeDef.plane : 'control'
        spawnParticle(ef, et, plane, 750, null)
      }
    }
  }

  // update step list
  const ucStepsList = document.getElementById('ucStepsList')
  if (ucStepsList) {
    const items = ucStepsList.querySelectorAll('li')
    items.forEach((li, i) => {
      li.classList.remove('step-active', 'step-done')
      if (i < stepIdx) li.classList.add('step-done')
      if (i === stepIdx) li.classList.add('step-active')
    })
  }

  // sidebar header: show step label
  const sbHeader = document.getElementById('sbHeader')
  const firstId = step.nodes[0]
  if (firstId && nodeEl[firstId] && sbHeader) {
    const nodes = DESCRIPTOR.nodes || []
    let nd = null
    for (let k = 0; k < nodes.length; k++) {
      if (nodes[k].id === firstId) {
        nd = nodes[k]
        break
      }
    }
    if (nd && _ucState !== 'playing') {
      spotlight(nd)
    } else {
      sbHeader.innerHTML = `<h4>${step.label}</h4>`
    }
  } else if (sbHeader) {
    sbHeader.innerHTML = `<h4>${step.label}</h4>`
  }

  _ucTimer = setTimeout(() => {
    _applyUcStep(stepIdx + 1)
  }, 900)
}

// ── wireUseCaseUI ─────────────────────────────────────────────────────────
// Called from the engine bootstrap when descriptor.useCases is present.
// Wires up .uc-btn, #ucPlay, #ucReset DOM controls.
// Safe to call even when some controls are absent (sidebar-less mode).

/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — called by generated HTML bootstrap */
function wireUseCaseUI() {
  document.querySelectorAll('.uc-btn').forEach((b) => {
    b.addEventListener('click', () => {
      _selectUc(Number(b.dataset.uc))
    })
  })

  const ucPlay = document.getElementById('ucPlay')
  const ucReset = document.getElementById('ucReset')

  if (ucPlay) {
    ucPlay.addEventListener('click', () => {
      if (_ucActiveIdx === null) return
      if (_ucState === 'playing') {
        _stopUcTimer()
        _ucState = 'paused'
        _syncUcButtons()
      } else if (_ucState === 'done' || _ucState === 'ready') {
        _resetUcVisuals()
        _ucStepIdx = 0
        _ucState = 'playing'
        _syncUcButtons()
        _applyUcStep(0)
      } else if (_ucState === 'paused') {
        _ucState = 'playing'
        _syncUcButtons()
        _applyUcStep(_ucStepIdx)
      }
    })
  }

  if (ucReset) {
    ucReset.addEventListener('click', () => {
      _stopUcTimer()
      _resetUcVisuals()
      _ucStepIdx = 0
      _ucState = 'ready'
      _syncUcButtons()
    })
  }
}

// ── wireHoverSpotlight ────────────────────────────────────────────────────
// Adds mouseenter/mouseleave listeners to all rendered .fd-node elements.
// Called once after renderNodes(), before draw().
// Skips spotlight during playing state (verbatim from lyra-stack-v2 l.480-482).

/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — called by generated HTML bootstrap */
function wireHoverSpotlight() {
  const nodes = DESCRIPTOR.nodes || []
  nodes.forEach((nd) => {
    const el = nodeEl[nd.id]
    if (!el) return
    el.addEventListener('mouseenter', () => {
      if (_ucState !== 'playing') spotlight(nd)
    })
    el.addEventListener('mouseleave', () => {
      if (_ucState !== 'playing') clearSpot()
    })
  })
}
