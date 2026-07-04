# Forge plugin references

Golden examples, authoring scaffolds, and baked previews ship **inside the plugin** at `${CLAUDE_PLUGIN_ROOT}/references/`.

## Entry point

Open **`showcase-index.html`** — searchable catalog of every skill output, craft diagram, fd-engine golden, fgraph template preview, and gallery shell:

```
file://${CLAUDE_PLUGIN_ROOT}/references/showcase-index.html
```

After `make -C plugins/forge deploy`:

```
file://~/.roxabi/forge/references/showcase-index.html
```

Legacy root `reference-gallery.html` redirects to the showcase index.

## Layout

| Path | Role |
|------|------|
| `showcase-index.html` | Generated catalog (search + filters) |
| `showcases/` | Golden output per skill (7 HTML + sample MD) |
| `thumbs/` | Card thumbnails for the showcase index |
| `diagrams/examples/` | Golden **craft** diagrams (`craft-hub-spoke`, `craft-deploy-flow`, …) |
| `diagrams/craft-diagram-starter.html` | **Authoring scaffold** — copy base; not indexed in gallery |
| `diagrams/craft-anchors.js` | SSoT for craft edge runtime (inline into craft HTML) |
| `graph-templates/examples/` | Baked fgraph/fd previews + goldens (`system-architecture`, …) |
| `graph-templates/*.html` | fgraph topology **scaffolds** (placeholders — not gallery artifacts) |
| `gallery-templates/examples/` | Baked gallery previews |
| `gallery-templates/*.html` | Gallery UI **scaffolds** (not gallery artifacts) |
| `base/` | reset, layout, typography, components, explainer-base, composition, presentation-shell |
| `aesthetics/` | Brand CSS presets (roxabi, lyra, …) |

### Craft vs fgraph previews

| System | Golden | Preview / scaffold |
|--------|--------|-------------------|
| **craft** | `diagrams/examples/craft-hub-spoke.html` | `craft-diagram-starter.html` (copy) · `craft-diagram-starter-preview.html` (baked demo) |
| **fgraph** | `graph-templates/examples/system-architecture.html` | `graph-templates/examples/*-preview.html` (baked from `graph-templates/*.html`) |
| **gallery** | skill outputs under `showcases/showcase-gallery.html` | `gallery-templates/examples/*-preview.html` |

Craft = pixel canvas + `craft-anchors.js`. fgraph = 0..100 coordinate cards + inline SVG (forge-chart).

## Regenerate (full pipeline)

From the **roxabi-forge** repo root:

```bash
# 1 — showcases, craft goldens, showcase-index, thumbs, bake previews
python3 scripts/build-reference-showcases.py

# 2 — static gates (placeholders, craft script safety, catalog paths)
python3 scripts/validate-reference-runtime.py

# 3 — optional: force all showcase card thumbs
uv run --with playwright python3 scripts/gen-showcase-thumbs.py --force

# 4 — sync plugin → ~/.roxabi/forge runtime
make -C plugins/forge deploy
```

### Scripts

| Script | Output |
|--------|--------|
| `build-reference-showcases.py` | `showcase-index.html`, craft goldens, skill showcases, calls bake |
| `bake-reference-previews.py` | `graph-templates/examples/*-preview.html`, `gallery-templates/examples/*-preview.html`, `craft-diagram-starter-preview.html` |
| `gen-showcase-thumbs.py` | `references/thumbs/*.png` (Playwright card crops) |
| `validate-reference-runtime.py` | Exit 0 when catalog artifacts have no `{{PLACEHOLDER}}`, safe craft scripts |
| `check-craft-diagram.py` | Craft authoring QA (anchors, edges, inlined JS) |
| `check-composition.py` | Presentation iframe + composition contract |

`build-reference-showcases.py` also runs `sync_craft_starter_inline_js()` so `craft-diagram-starter.html` stays aligned with `craft-anchors.js`.

## Gallery deploy (`~/.roxabi/forge`)

```bash
# Build _dist + OG images + manifest (from runtime tree)
make -C ~/.roxabi/forge build

# Cloudflare Pages (credentials via Bitwarden)
source ~/projects/security/vaultwarden/scripts/bw-forge-deploy-env.sh
make -C ~/.roxabi/forge deploy
```

Or from repo wrapper:

```bash
source ~/projects/security/vaultwarden/scripts/bw-forge-deploy-env.sh
make deploy   # repo Makefile → ~/.roxabi/forge deploy
```

### OG card thumbnails

Build order in `scripts/build.sh`:

1. `gen-og-tags.py` — inject meta (mutates HTML)
2. `gen-og-images.py` — Playwright screenshot → sibling `<name>.og.png`
3. `gen-manifest.py` — sets `p: true` when `.og.png` exists

Excluded from manifest + OG (authoring scaffolds only):

- `references/diagrams/craft-diagram-starter.html`
- `graph-templates/*.html` (immediate level)
- `gallery-templates/*.html` (immediate level)

Craft diagram captures use `?embed=hero` for consistent framing.

## CI

Repo CI runs `validate-reference-runtime.py` and `gen-og-images.py --self-test` alongside existing fd-engine and SVG gates.