# Craft diagram golden examples

Pixel-correct references for hand-authored craft canvases. **Read before** copying `craft-diagram-starter.html`.

| File | Bar demonstrated |
|------|------------------|
| `craft-hub-spoke.html` | Zone labels, legend, edge labels, 6 spokes, `craft-anchors` |
| `craft-deploy-flow.html` | Promote flow, `curve: "h"` + `y` in `#craft-edges` |

```bash
python3 ~/.roxabi/forge/scripts/check-craft-diagram.py --dir references/diagrams/examples --check
```

Integration target: `references/showcases/showcase-presentation.html` (2 iframes).

Regenerate with plugin sources: `python3 ~/.roxabi/forge/scripts/build-reference-showcases.py`