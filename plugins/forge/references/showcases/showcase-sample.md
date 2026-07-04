# Forge References

HQ golden examples shipped with the forge plugin.

## Craft diagrams

- `diagrams/examples/craft-hub-spoke.html` — hub-spoke golden
- `diagrams/examples/craft-deploy-flow.html` — promote flow (`curve: h`)

## Showcases

| Skill | File |
|-------|------|
| forge-chart | `showcases/showcase-chart.html` |
| forge-presentation | `showcases/showcase-presentation.html` |
| forge-epic | `showcases/showcase-epic.html` |
| forge-guide | `showcases/showcase-guide.html` |
| forge-slides | `showcases/showcase-slides.html` |
| forge-gallery | `showcases/showcase-gallery.html` |

## Validation

```bash
python3 ~/.roxabi/forge/scripts/check-craft-diagram.py --dir references/diagrams/examples --check
python3 ~/.roxabi/forge/scripts/check-composition.py -p references/showcases/showcase-presentation.html --check
```

> Blockquote: render-as-is — forge-md does not rewrite content.
