// fd/types/sequence.js — sequence diagram type module (S4)
// Glob-discovery: bundler.js discovers this file via glob('fd/types/*.js').
//
// Layout strategy: pure timeline math (no elkjs — sequence diagrams are NOT graphs).
// Adapted from the layout strategy in the upstream diagram library sequence/layout.ts.
// (The upstream library explicitly says "Custom timeline-based layout (no ELK — sequence
// diagrams aren't graphs)" in layout.ts lines 7-8.)
//
// Rendering: dedicated SVG renderer (bypasses edges.js / cards.js — same pattern
// as gantt.js and pie.js which also own their own SVG rendering).
//
// Descriptor schema (participants-based, not nodes-based):
//   type: "sequence"
//   title: string
//   participants: [{ id, label, kind? }]
//     kind: "actor" (default, highlighted border) | "system" (standard box)
//   messages: [{ from, to, label?, lineStyle?, arrowHead?, activate?, deactivate? }]
//     lineStyle: "solid" (default) | "dashed" (return/response arrows)
//     arrowHead: "filled" (default) | "open" (async / create)
//
// Layout constants (adapted from upstream layout.ts SEQ constants):
//   actorGap: 160px — min horizontal gap between participant centers
//   actorHeight: 40px — participant box height
//   headerGap: 24px — space from actor bottom to first message row
//   messageRowHeight: 44px — vertical step per message
//   selfMessageHeight: 32px — extra height for self-directed messages
//   activationWidth: 10px — activation box width (narrow rect on lifeline)
//   padding: 30px — outer margin
//
// RD-3: sequence is an auto-layout type → CARD_DEFAULT = null (SVG-only renderer).
// Guard-safety: no diagram-tool token under plugins/forge/ (AC-7, §10).

const SEQ_TYPE = 'sequence'
// RD-3: sequence uses its own SVG renderer, not the HTML node/edge engine
const SEQ_CARD_DEFAULT = null

// ── Layout constants (adapted from upstream layout.ts SEQ object) ─────────────
const SEQ_PAD = 30
const SEQ_ACTOR_H = 40
const SEQ_ACTOR_PAD_X = 16
const SEQ_ACTOR_GAP = 160
const SEQ_HEADER_GAP = 24
const SEQ_MSG_ROW_H = 44
const SEQ_SELF_MSG_H = 32
const SEQ_ACTIVATION_W = 10
const SEQ_NESTING_OFFSET = 4 // px offset per nesting depth level

// ── Text width estimator (approximate at gen-time, no DOM needed) ─────────────
// Rough estimate: 7px per character at 12px font, minimum width 80px.
// Used for participant box sizing (Risk R-1 option b from spec §9).
function seqEstimateTextWidth(text) {
  return Math.max(80, (text || '').length * 7 + SEQ_ACTOR_PAD_X * 2)
}

// ── Participant x-layout ──────────────────────────────────────────────────────
// Returns { actorCenterX[], actorWidths[], actorIndex Map }
// Adapted from upstream layout.ts lines 64-82.
function seqLayoutActors(participants) {
  const actorWidths = participants.map((p) => seqEstimateTextWidth(p.label || p.id))

  const actorCenterX = []
  let currentX = SEQ_PAD + actorWidths[0] / 2
  for (let i = 0; i < participants.length; i++) {
    if (i > 0) {
      const minGap = Math.max(SEQ_ACTOR_GAP, (actorWidths[i - 1] + actorWidths[i]) / 2 + 40)
      currentX += minGap
    }
    actorCenterX.push(currentX)
  }

  const actorIndex = new Map()
  for (let j = 0; j < participants.length; j++) {
    actorIndex.set(participants[j].id, j)
  }

  return { actorCenterX, actorWidths, actorIndex }
}

// ── Message y-layout ──────────────────────────────────────────────────────────
// Returns { positionedMessages[], activations[], diagramBottom }
// Adapted from upstream layout.ts lines 99-258.
function seqLayoutMessages(messages, actorCenterX, actorIndex) {
  const actorY = SEQ_PAD
  let messageY = actorY + SEQ_ACTOR_H + SEQ_HEADER_GAP

  const positionedMessages = []
  // Track activation stack per actor: [{ startY, depth }]
  const activationStacks = new Map()
  const activations = []

  for (let msgIdx = 0; msgIdx < messages.length; msgIdx++) {
    const msg = messages[msgIdx]
    const fromIdx = actorIndex.has(msg.from) ? actorIndex.get(msg.from) : 0
    const toIdx = actorIndex.has(msg.to) ? actorIndex.get(msg.to) : 0
    const isSelf = msg.from === msg.to

    positionedMessages.push({
      from: msg.from,
      to: msg.to,
      label: msg.label || '',
      lineStyle: msg.lineStyle || 'solid',
      arrowHead: msg.arrowHead || 'filled',
      x1: actorCenterX[fromIdx],
      x2: actorCenterX[toIdx],
      y: messageY,
      isSelf,
    })

    // Activation tracking (adapted from upstream lines 160-184)
    if (msg.activate) {
      if (!activationStacks.has(msg.to)) activationStacks.set(msg.to, [])
      const stackA = activationStacks.get(msg.to)
      const depth = stackA.length
      stackA.push({ startY: messageY, depth })
    }

    if (msg.deactivate) {
      const stackD = activationStacks.get(msg.from)
      if (stackD && stackD.length > 0) {
        const entry = stackD.pop()
        const idx = actorIndex.has(msg.from) ? actorIndex.get(msg.from) : 0
        const xOffset = entry.depth * SEQ_NESTING_OFFSET
        activations.push({
          actorId: msg.from,
          x: actorCenterX[idx] - SEQ_ACTIVATION_W / 2 + xOffset,
          topY: entry.startY,
          bottomY: messageY,
          width: SEQ_ACTIVATION_W,
        })
      }
    }

    // Advance y (adapted from upstream line 187)
    messageY += isSelf ? SEQ_SELF_MSG_H + SEQ_MSG_ROW_H : SEQ_MSG_ROW_H
  }

  // Close any unclosed activations (adapted from upstream lines 246-258)
  activationStacks.forEach((stack, actorId) => {
    for (let k = 0; k < stack.length; k++) {
      const act = stack[k]
      const aIdx = actorIndex.has(actorId) ? actorIndex.get(actorId) : 0
      activations.push({
        actorId,
        x: actorCenterX[aIdx] - SEQ_ACTIVATION_W / 2 + act.depth * SEQ_NESTING_OFFSET,
        topY: act.startY,
        bottomY: messageY - SEQ_MSG_ROW_H / 2,
        width: SEQ_ACTIVATION_W,
      })
    }
  })

  return {
    positionedMessages,
    activations,
    diagramBottom: messageY + SEQ_PAD,
  }
}

// ── SVG helper ────────────────────────────────────────────────────────────────
function seqFmt(n) {
  return n.toFixed(1)
}

// ── renderSequence: draw the full sequence diagram as inline SVG ──────────────
// Appended directly to canvas (no HTML nodes — SVG-only like pie/gantt).
// AC-10: no preserveAspectRatio=none attribute. SVG uses explicit viewBox sized
// to computed diagram dimensions; canvas wrapper handles overflow via CSS.
function renderSequence(descriptor) {
  const participants = descriptor.participants || []
  const messages = descriptor.messages || []

  if (participants.length === 0) return

  // ── 1. Lay out participants (x-axis) ──────────────────────────────────────
  const actorLayout = seqLayoutActors(participants)
  const { actorCenterX, actorWidths, actorIndex } = actorLayout

  // ── 2. Lay out messages (y-axis) ─────────────────────────────────────────
  const msgLayout = seqLayoutMessages(messages, actorCenterX, actorIndex)
  const { positionedMessages, activations, diagramBottom } = msgLayout

  // ── 3. Compute diagram dimensions ────────────────────────────────────────
  const lastIdx = actorCenterX.length - 1
  const svgW = actorCenterX[lastIdx] + actorWidths[lastIdx] / 2 + SEQ_PAD
  const svgH = diagramBottom
  const actorY = SEQ_PAD

  // ── 4. Build SVG markup ───────────────────────────────────────────────────
  const NS_SVG = 'http://www.w3.org/2000/svg'
  const svgEl = document.createElementNS(NS_SVG, 'svg')
  svgEl.setAttribute('class', 'fd-seq-svg')
  // Explicit viewBox: pixel-space, sized to diagram (AC-10: no preserveAspectRatio=none)
  svgEl.setAttribute('viewBox', `0 0 ${seqFmt(svgW)} ${seqFmt(svgH)}`)
  svgEl.setAttribute('width', '100%')
  svgEl.setAttribute('height', `${seqFmt(svgH)}px`)
  svgEl.setAttribute('aria-hidden', 'true')
  svgEl.style.display = 'block'
  svgEl.style.maxWidth = `${seqFmt(svgW)}px`

  // ── 4a. Defs: arrowhead markers ───────────────────────────────────────────
  const defs = document.createElementNS(NS_SVG, 'defs')

  const mFilled = document.createElementNS(NS_SVG, 'marker')
  mFilled.setAttribute('id', 'seq-arr-filled')
  mFilled.setAttribute('markerWidth', '9')
  mFilled.setAttribute('markerHeight', '9')
  mFilled.setAttribute('refX', '7')
  mFilled.setAttribute('refY', '3')
  mFilled.setAttribute('orient', 'auto')
  const pFilled = document.createElementNS(NS_SVG, 'path')
  pFilled.setAttribute('d', 'M0,0 L7,3 L0,6 Z')
  pFilled.setAttribute('class', 'seq-marker-filled')
  mFilled.appendChild(pFilled)
  defs.appendChild(mFilled)

  const mOpen = document.createElementNS(NS_SVG, 'marker')
  mOpen.setAttribute('id', 'seq-arr-open')
  mOpen.setAttribute('markerWidth', '9')
  mOpen.setAttribute('markerHeight', '9')
  mOpen.setAttribute('refX', '7')
  mOpen.setAttribute('refY', '3')
  mOpen.setAttribute('orient', 'auto')
  const pOpen = document.createElementNS(NS_SVG, 'path')
  pOpen.setAttribute('d', 'M0,0 L7,3 L0,6')
  pOpen.setAttribute('fill', 'none')
  pOpen.setAttribute('class', 'seq-marker-open')
  mOpen.appendChild(pOpen)
  defs.appendChild(mOpen)

  svgEl.appendChild(defs)

  // ── 4b. Lifelines (vertical dashed lines behind actors) ───────────────────
  for (let li = 0; li < participants.length; li++) {
    const lx = actorCenterX[li]
    const ll = document.createElementNS(NS_SVG, 'line')
    ll.setAttribute('x1', seqFmt(lx))
    ll.setAttribute('y1', seqFmt(actorY + SEQ_ACTOR_H))
    ll.setAttribute('x2', seqFmt(lx))
    ll.setAttribute('y2', seqFmt(diagramBottom - SEQ_PAD))
    ll.setAttribute('class', 'seq-lifeline')
    svgEl.appendChild(ll)
  }

  // ── 4c. Activation boxes ─────────────────────────────────────────────────
  for (let ai = 0; ai < activations.length; ai++) {
    const act = activations[ai]
    const ar = document.createElementNS(NS_SVG, 'rect')
    ar.setAttribute('x', seqFmt(act.x))
    ar.setAttribute('y', seqFmt(act.topY))
    ar.setAttribute('width', seqFmt(act.width))
    ar.setAttribute('height', seqFmt(act.bottomY - act.topY))
    ar.setAttribute('class', 'seq-activation')
    svgEl.appendChild(ar)
  }

  // ── 4d. Participant boxes (drawn on top of lifelines) ─────────────────────
  for (let pi = 0; pi < participants.length; pi++) {
    const part = participants[pi]
    const cx = actorCenterX[pi]
    const aw = actorWidths[pi]

    const boxRect = document.createElementNS(NS_SVG, 'rect')
    boxRect.setAttribute('x', seqFmt(cx - aw / 2))
    boxRect.setAttribute('y', seqFmt(actorY))
    boxRect.setAttribute('width', seqFmt(aw))
    boxRect.setAttribute('height', seqFmt(SEQ_ACTOR_H))
    boxRect.setAttribute('class', part.kind === 'actor' ? 'seq-participant seq-participant-actor' : 'seq-participant')
    boxRect.setAttribute('rx', '6')
    svgEl.appendChild(boxRect)

    const lt = document.createElementNS(NS_SVG, 'text')
    lt.setAttribute('x', seqFmt(cx))
    lt.setAttribute('y', seqFmt(actorY + SEQ_ACTOR_H / 2 + 4))
    lt.setAttribute('text-anchor', 'middle')
    lt.setAttribute('class', 'seq-participant-label')
    lt.textContent = part.label || part.id
    svgEl.appendChild(lt)
  }

  // ── 4e. Message arrows ────────────────────────────────────────────────────
  for (let mi = 0; mi < positionedMessages.length; mi++) {
    const msg = positionedMessages[mi]
    const isDashed = msg.lineStyle === 'dashed'
    const markerId = msg.arrowHead === 'open' ? 'seq-arr-open' : 'seq-arr-filled'
    const cls = `seq-message${isDashed ? ' seq-message-dashed' : ''}`

    if (msg.isSelf) {
      // Self-message: right loop (adapted from upstream renderer loopW=30 pattern)
      const loopW = 36
      const loopX = msg.x1 + loopW
      const loopTop = msg.y
      const loopBot = msg.y + SEQ_SELF_MSG_H

      const sp = document.createElementNS(NS_SVG, 'path')
      sp.setAttribute(
        'd',
        'M ' +
          seqFmt(msg.x1) +
          ',' +
          seqFmt(loopTop) +
          ' L ' +
          seqFmt(loopX) +
          ',' +
          seqFmt(loopTop) +
          ' L ' +
          seqFmt(loopX) +
          ',' +
          seqFmt(loopBot) +
          ' L ' +
          seqFmt(msg.x1) +
          ',' +
          seqFmt(loopBot),
      )
      sp.setAttribute('fill', 'none')
      sp.setAttribute('class', cls)
      sp.setAttribute('marker-end', `url(#${markerId})`)
      svgEl.appendChild(sp)

      if (msg.label) {
        const sl = document.createElementNS(NS_SVG, 'text')
        sl.setAttribute('x', seqFmt(loopX + 6))
        sl.setAttribute('y', seqFmt(loopTop + SEQ_SELF_MSG_H / 2 + 4))
        sl.setAttribute('class', 'seq-msg-label')
        sl.textContent = msg.label
        svgEl.appendChild(sl)
      }
    } else {
      // Normal message arrow (horizontal line between two lifelines)
      const dir = msg.x2 > msg.x1 ? 1 : -1
      const ml = document.createElementNS(NS_SVG, 'line')
      ml.setAttribute('x1', seqFmt(msg.x1))
      ml.setAttribute('y1', seqFmt(msg.y))
      // Slightly short on receiver side so arrowhead has visual clearance
      ml.setAttribute('x2', seqFmt(msg.x2 - dir * 2))
      ml.setAttribute('y2', seqFmt(msg.y))
      ml.setAttribute('class', cls)
      ml.setAttribute('marker-end', `url(#${markerId})`)
      svgEl.appendChild(ml)

      if (msg.label) {
        const lbl = document.createElementNS(NS_SVG, 'text')
        lbl.setAttribute('x', seqFmt((msg.x1 + msg.x2) / 2))
        lbl.setAttribute('y', seqFmt(msg.y - 6))
        lbl.setAttribute('text-anchor', 'middle')
        lbl.setAttribute('class', 'seq-msg-label')
        lbl.textContent = msg.label
        svgEl.appendChild(lbl)
      }
    }
  }

  canvas.appendChild(svgEl)

  // Resize canvas to fit computed diagram height
  canvas.style.setProperty('--fd-canvas-h', `${seqFmt(svgH)}px`)
  canvas.style.height = `${seqFmt(svgH)}px`
}

// ── elkOptionsForType ─────────────────────────────────────────────────────────
// Sequence diagrams do NOT use elkjs (pure timeline math — no graph algorithm).
// Returning null signals fd-layout.mjs to skip elk for this type.
// The upstream diagram library also explicitly does NOT use ELK for sequence
// ("no ELK — sequence diagrams aren't graphs" — layout.ts line 8).
function elkOptionsForType() {
  return null
}

// ── nodeSizeForType ───────────────────────────────────────────────────────────
// Sequence uses participants[], not nodes[]. Returns null.
function nodeSizeForType() {
  return null
}

// ── sequenceInit ─────────────────────────────────────────────────────────────
// Called by the fd-engine bootstrap after parsing fd-data.
// Returns the type contract consumed by the engine orchestrator.
function sequenceInit(descriptor) {
  const t = descriptor.type
  if (t !== SEQ_TYPE) {
    console.warn('[fd] sequence.js init() called with unexpected type:', t)
  }

  return {
    // null: sequence bypasses the HTML node/edge engine entirely (SVG-only)
    typeDefault: SEQ_CARD_DEFAULT,
    placeZones: null,
    positionNodes: null,
    applyShapes: null,
    // renderChart: full SVG renderer (called instead of renderNodes + draw)
    renderChart: renderSequence,
    elkOptions: elkOptionsForType,
    nodeSizer: nodeSizeForType,
  }
}

// ── glob-discovery registration ───────────────────────────────────────────────
// bundler.js discovers fd/types/*.js and concatenates them into the inline <script>.
// At runtime each type module self-registers here so the bootstrap can dispatch.
window.__fdTypes = window.__fdTypes || {}
window.__fdTypes[SEQ_TYPE] = {
  CARD_DEFAULT: SEQ_CARD_DEFAULT,
  placeZones: null,
  renderChart: renderSequence,
  elkOptions: elkOptionsForType,
  nodeSizer: nodeSizeForType,
  init: sequenceInit,
}
