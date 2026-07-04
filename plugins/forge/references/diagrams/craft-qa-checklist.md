# Craft Diagram QA Checklist

Run **before** embedding in a presentation. Order matters.

## 1. Standalone open

```bash
# file:// open diagrams/{slug}.html — full canvas visible, no parent CSS
```

## 2. Automated checks

```bash
python3 ~/.roxabi/forge/scripts/check-craft-diagram.py --dir visuals/diagrams --check
python3 ~/.roxabi/forge/scripts/check-composition.py -p visuals/{name}.html --check
```

## 3. Layout layers (top → bottom)

| Layer | z-index band | Must not overlap |
|-------|----------------|------------------|
| Title block | 20 | Hub, spokes |
| Zone labels / bandeaux | 8–16 | Hub center |
| SVG connections | 6 | — (under nodes) |
| Spokes / hub | 10–12 | — |
| Rule badge / legend | 20 | Each other (stack vertically) |

## 4. Geometry rules

- [ ] Canvas size explicit: `data-canvas-width` + `data-canvas-height` on `.diagram`
- [ ] All `[data-anchor]` nodes inside canvas (no negative `left`/`right`)
- [ ] **Paths via `craft-anchors.js`** — not hand-edited `d=` after moving spokes
- [ ] Promote flows (`hotfix → staging → prod`) use `curve: "h"` + shared `y`
- [ ] Max **6** `data-anchor` nodes per hub without splitting diagram

## 5. Icons & copy

- [ ] Third-party marks from inlined Simple Icons (not invented SVG)
- [ ] Title + subtitle **only** inside diagram (no duplicate in presentation)
- [ ] `diagram:title` meta present

## 6. Embed modes

- [ ] Full width: default padding
- [ ] Hero column: `?embed=hero` + scale on `.diagram`
- [ ] `html, body` transparent in embed mode (sync class in `<head>`)

## 7. Capture (optional gate)

Playwright screenshot at 1280×900 → compare to `_captures/{slug}.png` baseline.

---

## Anchor authoring (preferred)

1. Position spokes with CSS — add `data-anchor="id"` on each node
2. Define edges in `#craft-edges` JSON (see `craft-diagram-starter.html`)
3. Inline `craft-anchors.js` — paths regenerate on resize
4. Move a spoke → only CSS changes; paths follow automatically