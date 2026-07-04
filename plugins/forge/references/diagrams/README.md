# Craft Diagram SSoT — `visuals/diagrams/`

Standalone HTML for **premium craft** hub-spoke / swimlane canvases, embedded in presentations via iframe.

---

## Authoring pipeline (mandatory order)

```
1. Copy craft-diagram-starter.html → visuals/diagrams/{slug}.html
2. Position nodes — add data-anchor="id" on hub + spokes (CSS only)
3. Define edges in #craft-edges JSON (from → to, curve, class)
4. craft-anchors.js already inlined in starter — paths auto-regenerate
5. Inline brand icons from brand-icons.svg (no external <use href>)
6. check-craft-diagram.py --check
7. Open file:// standalone → visual pass (craft-qa-checklist.md)
8. Embed iframe in presentation → check-composition.py --check
```

**Do not** hand-edit `<path d="…">` after moving spokes — move CSS, edges follow via `craft-anchors.js`.

---

## craft-anchors.js

| Piece | Role |
|-------|------|
| `data-anchor="id"` | On hub, spokes, env nodes |
| `data-canvas-width/height` | On `.diagram` — viewBox scale |
| `#craft-edges` JSON | Edge list: from, to, class, curve (`l`\|`q`\|`h`), optional `y` for horizontal promote |
| `svg.craft-connections` | Empty — paths injected at runtime |
| `craft-anchors.js` | **Inline** from `references/diagrams/craft-anchors.js` |

### Edge curves

| curve | Use |
|-------|-----|
| `q` | Default hub-spoke bezier |
| `l` | Straight (short links) |
| `h` | Horizontal promote line at fixed `y` (deploy §03 style) |

---

## When to author here vs forge-chart

| Signal | Tool |
|--------|------|
| ≤8 nodes, descriptor, validate-fd exit 0 | `forge-chart` fd-engine |
| Custom paths, 6+ spokes, craft legend, zone labels | `diagrams/{slug}.html` + craft-anchors |
| Simple pipeline in prose | `arch-pipeline` in presentation |

---

## QA

```bash
python3 ~/.roxabi/forge/scripts/check-craft-diagram.py --dir visuals/diagrams --check
```

See `craft-qa-checklist.md` for visual layers (title → bandeau → hub → legend).

---

## Embed modes

| Query | Behavior |
|-------|----------|
| (none) | Full canvas, `--bg` body |
| `?embed=hero` | Transparent html/body + responsive scale |

### iframe resize (`postMessage`)

Diagrams with `data-slug="{slug}.html"` notify the parent presentation:

```js
{ type: 'forge-diagram-resize', id: '{slug}.html', height: N }
```

Presentation listener (in `forge-presentation` template):

```js
window.addEventListener('message', function (e) {
  if (!e.data || e.data.type !== 'forge-diagram-resize') return;
  document.querySelectorAll('.diagram-frame').forEach(function (iframe) {
    if (iframe.src && iframe.src.includes(e.data.id)) {
      iframe.style.height = Math.max(e.data.height, parseInt(iframe.dataset.height || '200', 10)) + 'px';
    }
  });
});
```

Legacy `lyra-diagram-resize` is retired — use `forge-diagram-resize` everywhere.

---

## Golden examples (`examples/`)

Read these **before** authoring — pixel + structure targets (stronger than the starter).

| File | Demonstrates |
|------|----------------|
| `examples/craft-hub-spoke.html` | 6-spoke hub, zone labels, legend, edge labels, craft-anchors |
| `examples/craft-deploy-flow.html` | Promote flow, `curve: "h"` + shared `y` |

```bash
python3 ~/.roxabi/forge/scripts/check-craft-diagram.py --dir references/diagrams/examples --check
```

Showcase integration: `references/showcases/showcase-presentation.html` embeds both via iframe.

Full catalog: `references/showcase-index.html`. Regenerate: `python3 ~/.roxabi/forge/scripts/build-reference-showcases.py`

## Files

| File | Purpose |
|------|---------|
| `craft-diagram-starter.html` | Copy source (anchors + edges example) |
| `examples/craft-hub-spoke.html` | **Golden** hub-spoke reference |
| `examples/craft-deploy-flow.html` | **Golden** deploy promote reference |
| `craft-anchors.js` | Path engine — inline into each diagram |
| `craft-qa-checklist.md` | Pre-embed visual gate |
| `brand-icons.svg` | Official marks — copy symbols inline |

---

## See also

- `../composition-contract.md` — presentation × diagram layers
- `../base/composition.css` — iframe consumer styles