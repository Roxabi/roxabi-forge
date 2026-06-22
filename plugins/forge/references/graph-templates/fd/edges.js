// fd/edges.js — edge drawing layer: draw(), redraw(), initMarkers(), ResizeObserver
// Lifted verbatim and generalized from lyra-stack-v2.html lines 537-626 + l.960.
// Depends on names from core.js (concat order: core.js MUST precede this file).
// Plane colors: derived from descriptor.edges[i].plane via CSS vars --fd-plane-{name},
// never hardcoded hex.

// ---- Marker injection ----
// Creates one <marker id="fd-arr-{plane}"> per unique semantic plane.
// fill uses an injected SVG <style> rule binding CSS var per plane.
// planes: array of unique plane name strings (e.g. ['message','llm','media'])
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — called by generated HTML */
function initMarkers(planes) {
  var defs = svg.querySelector('defs')
  if (!defs) {
    defs = document.createElementNS(NS, 'defs')
    svg.insertBefore(defs, svg.firstChild)
  }
  // Inject a <style> block into the SVG for plane fill vars (one per plane)
  var styleEl = document.createElementNS(NS, 'style')
  var cssRules = planes.map((pl) => `#fd-arr-${pl} path { fill: var(--fd-plane-${pl}, #8aa0bd); }`).join('\n')
  styleEl.textContent = cssRules
  defs.appendChild(styleEl)

  planes.forEach((pl) => {
    // Skip if marker already exists (idempotent re-init guard)
    if (svg.querySelector(`#fd-arr-${pl}`)) return
    var marker = document.createElementNS(NS, 'marker')
    marker.setAttribute('id', `fd-arr-${pl}`)
    marker.setAttribute('markerWidth', '9')
    marker.setAttribute('markerHeight', '9')
    marker.setAttribute('refX', '7')
    marker.setAttribute('refY', '3')
    marker.setAttribute('orient', 'auto')
    // NO preserveAspectRatio — AC-10 compliance (no viewBox either)
    var arrow = document.createElementNS(NS, 'path')
    arrow.setAttribute('d', 'M0,0 L7,3 L0,6 Z')
    // fill resolved via the injected CSS var rule above
    marker.appendChild(arrow)
    defs.appendChild(marker)
  })
}

// ---- Full edge pass ----
// Verbatim-adapted from lyra-stack-v2.html l.537-626.
// Reads DESCRIPTOR.edges (set by initEngine). Uses nodeEl, canvas, svg, paths,
// pathByPair from core.js module scope.
function draw() {
  // Clear all existing paths, labels, circles from the SVG overlay
  svg.querySelectorAll(':scope > path, :scope > text, :scope > circle, :scope > g').forEach((n) => {
    n.remove()
  })
  paths = []
  pathByPair.clear()

  var EDGES = DESCRIPTOR.edges || []

  // --- Step 1: deduplicate EDGES into unique pairs -------------------------
  // For each unordered pair keep: plane of first occurrence, label if any,
  // canonical source (f), for slot allocation.
  var seenPairs = new Map() // pairKey → {f, t, plane, lab, edge, edgeIndices:[]}
  var i, e, k
  for (i = 0; i < EDGES.length; i++) {
    e = EDGES[i]
    k = pairKey(e.f, e.t)
    if (!seenPairs.has(k)) {
      seenPairs.set(k, { f: e.f, t: e.t, plane: e.plane, lab: e.label || null, edge: e, flow: !!e.flow, edgeIndices: [i] })
    } else {
      seenPairs.get(k).edgeIndices.push(i)
      // upgrade label if this occurrence has one and first didn't
      if (e.label && !seenPairs.get(k).lab) seenPairs.get(k).lab = e.label
      // upgrade flow if ANY occurrence of the pair requests it (dedup keeps the first edge only)
      if (e.flow) seenPairs.get(k).flow = true
    }
  }
  var dedupedEdges = Array.from(seenPairs.values()) // array of unique pairs

  // --- Step 2: build port maps over deduped edges -------------------------
  // Key: "nodeId:face" → [pairIdx in dedupedEdges]
  var portMap = new Map()
  var ref, f, t, edge, rf, rt, dx, dy, fFace, tFace, fk, tk
  for (i = 0; i < dedupedEdges.length; i++) {
    ref = dedupedEdges[i]
    f = ref.f
    t = ref.t
    edge = ref.edge
    rf = rect(f)
    rt = rect(t)
    dx = rt.cx - rf.cx
    dy = rt.cy - rf.cy
    fFace = faceFor(dx, dy, true, edge)
    tFace = faceFor(dx, dy, false, edge)
    fk = `${f}:${fFace}`
    tk = `${t}:${tFace}`
    if (!portMap.has(fk)) portMap.set(fk, [])
    if (!portMap.has(tk)) portMap.set(tk, [])
    portMap.get(fk).push(i)
    portMap.get(tk).push(i)
  }

  // --- Step 3: draw one path per deduplicated pair ------------------------
  var plane, lab, fSlots, tSlots, fi, ti, pu1, pu2, stb, c1x, c1y, c2x, c2y, dStr, p, tx2, mx, my
  for (i = 0; i < dedupedEdges.length; i++) {
    ref = dedupedEdges[i]
    f = ref.f
    t = ref.t
    plane = ref.plane
    lab = ref.lab
    edge = ref.edge
    rf = rect(f)
    rt = rect(t)
    dx = rt.cx - rf.cx
    dy = rt.cy - rf.cy

    fFace = faceFor(dx, dy, true, edge)
    tFace = faceFor(dx, dy, false, edge)
    fk = `${f}:${fFace}`
    tk = `${t}:${tFace}`

    fSlots = portMap.get(fk)
    tSlots = portMap.get(tk)
    fi = fSlots.indexOf(i)
    ti = tSlots.indexOf(i)

    pu1 = portAnchor(rf, fFace, fi, fSlots.length)
    pu2 = portAnchor(rt, tFace, ti, tSlots.length)

    // Proportional stub: longer links curve more (verbatim l.592-598)
    stb = stubLen(dx, dy)
    c1x = pu1.x + pu1.nx * stb
    c1y = pu1.y + pu1.ny * stb
    c2x = pu2.x + pu2.nx * stb
    c2y = pu2.y + pu2.ny * stb

    dStr =
      `M${pu1.x.toFixed(1)},${pu1.y.toFixed(1)}` +
      ` C${c1x.toFixed(1)},${c1y.toFixed(1)}` +
      ` ${c2x.toFixed(1)},${c2y.toFixed(1)}` +
      ` ${pu2.x.toFixed(1)},${pu2.y.toFixed(1)}`

    p = document.createElementNS(NS, 'path')
    p.setAttribute('d', dStr)
    // CSS class = plane name → stroke resolved via .fd-edges path.{plane} in fd-engine.css
    // edge.flow → append .flow for the ambient marching-dash animation (craft bar).
    // ref.flow is set if ANY occurrence of the deduped pair requested flow.
    p.setAttribute('class', ref.flow ? `${plane} flow` : plane)
    // Arrowhead marker per plane — no hardcoded hex, color via CSS var in marker's injected style
    p.setAttribute('marker-end', `url(#fd-arr-${plane})`)
    // Data attributes for spotlight + particle matching
    p.dataset.f = f
    p.dataset.t = t
    p.dataset.pk = pairKey(f, t)
    svg.appendChild(p)
    paths.push(p)
    pathByPair.set(pairKey(f, t), p)

    // Edge label (de Casteljau midpoint — verbatim l.613-624)
    if (lab) {
      tx2 = document.createElementNS(NS, 'text')
      mx = 0.125 * pu1.x + 0.375 * c1x + 0.375 * c2x + 0.125 * pu2.x
      my = 0.125 * pu1.y + 0.375 * c1y + 0.375 * c2y + 0.125 * pu2.y
      tx2.setAttribute('x', mx.toFixed(1))
      tx2.setAttribute('y', (my - 4).toFixed(1))
      tx2.setAttribute('text-anchor', 'middle')
      tx2.setAttribute('class', 'fd-elabel')
      tx2.dataset.pk = pairKey(f, t)
      tx2.textContent = lab
      svg.appendChild(tx2)
    }
  }
}

// ---- Redraw: re-runs full edge pass + optional zone placement ----
// Called by ResizeObserver and any layout-changing event.
function redraw() {
  draw()
  // If a placeZones function is defined (by architecture.js type module), call it
  if (typeof placeZones === 'function') placeZones(DESCRIPTOR)
}

// ---- ResizeObserver wiring ----
// Called from initEngine after DOM is ready.
// Verbatim from lyra-stack-v2.html l.960 — adapted to fd-engine naming.
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — called by generated HTML */
function wireResize() {
  new ResizeObserver(redraw).observe(canvas)
}

// ---- Unique plane list helper ----
// Derives the set of plane names from descriptor.edges for initMarkers call.
/* biome-ignore lint/correctness/noUnusedVariables: cross-file concat — called by generated HTML */
function uniquePlanes() {
  var planes = []
  var seen = {}
  var EDGES = DESCRIPTOR?.edges || []
  var i, pl
  for (i = 0; i < EDGES.length; i++) {
    pl = EDGES[i].plane
    if (pl && !seen[pl]) {
      seen[pl] = true
      planes.push(pl)
    }
  }
  return planes
}
