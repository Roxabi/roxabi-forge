# forge

Generate HTML visual artifacts for the `~/.roxabi/forge/` ecosystem — diagrams, galleries, guides, epics, slide decks, long-form presentations, rendered markdown. Brand-aware, manifest-indexed, Cloudflare Pages ready.

## Install

```bash
claude plugin marketplace add Roxabi/roxabi-forge
claude plugin install forge
```

## Skills

| Skill | Trigger | What it creates |
|-------|---------|-----------------|
| `forge-init` | "init forge", "setup forge" | Set up `~/.roxabi/forge/` with server, shared assets, directory structure |
| `forge-chart` | "draw", "diagram", "visualize", "quick visual" | fd-engine premium diagrams via `gen-fd.py` (architecture, hub-spoke) or fgraph static templates (topology, flow, timeline, proportion, comparison); validated with `validate-fd.py` — `file://` safe |
| `forge-epic` | "visualize #N", "epic preview", "illustrate issue" | Issue-linked analysis: overview, scope breakdown, dependency graph, acceptance criteria |
| `forge-gallery` | "gallery", "showcase", "compare visually", "sprite gallery" | Image or audio gallery with pivot grouping, dynamic filters, search, lightbox, multi-mode datasets |
| `forge-guide` | "write a guide", "multi-tab doc", "architecture doc", "recap" | Split-file multi-tab HTML document (shell + CSS + JS + tab fragments) |
| `forge-md` | "render md", "md to html", "tabbed docs" | Themed self-contained HTML from existing markdown — single-file or multi-tab |
| `forge-presentation` | "create presentation", "scroll presentation", "visual article" | Single-file long-form scroll presentation — hero + numbered sections, reveal animations |
| `forge-slides` | "create deck", "slide deck", "pitch deck", "slides from #N" | Magazine-quality scroll-snap deck — 10 slide types, 6 aesthetic presets, keyboard + touch nav |

## When to use each

**`forge-chart`** — quick single diagram: **fd-engine** (descriptor JSON → `gen-fd.py` → `validate-fd.py`) for dense/interactive topology; fgraph static for ≤6-node print-safe diagrams; CSS Grid for text-heavy explainers. Self-contained, `file://` safe.

**`forge-epic`** — always tied to a GitHub issue `#N`. Filename always includes the issue number (e.g. `477-tool-registry.html`).

**`forge-gallery`** — comparing brand iterations, avatar batches, TTS engine outputs, voice clones, sprite datasets.

**`forge-guide`** — rich multi-section docs: user guide, architecture overview, project recap, analysis/comparison, roadmap. Split-file, lazy-loaded tabs.

**`forge-md`** — when markdown is already written and you just want it rendered as-is (no tab planning, no rewriting).

**`forge-presentation`** — long-form visual article with a hero and numbered scroll sections; continuous scroll with reveal animations. Craft diagrams embed via `visuals/diagrams/*.html` + iframe (`composition-contract.md`); tables use `panel-wrap`.

**`forge-slides`** — magazine-style pitch deck, scroll-snap navigated, 10 slide types × 6 aesthetic presets (including `lyra-v2`, `cool-dark`).

### Gallery templates

5 ready-to-use templates in `references/gallery-templates/`:

<table>
<tr>
<td width="50%">

**Pivot Gallery** — `pivot-gallery.html`

Matrix view with col×row grouping. Dynamic filters, score-based sorting, search, size +/−. Best for: image comparison with scoring/clustering data.

</td>
<td width="50%">

**Simple Gallery** — `simple-gallery.html`

Batch tabs with starring. Tag-based filtering, lightbox with prev/next. Best for: iterative exploration (V1 → V2 → V3 batches).

</td>
</tr>
<tr>
<td>

**Comparison Gallery** — `comparison-gallery.html`

Cards with spec tables and verdict badges. Best for: pipeline comparison with detailed metadata per image.

</td>
<td>

**Audio Gallery** — `audio-gallery.html`

Audio players with engine/quality badges. Card and list views. Best for: TTS engine comparison, voice cloning A/B tests.

</td>
</tr>
<tr>
<td colspan="2">

**Multi-Mode Gallery** — `multi-mode-gallery.html`

Mode tab bar with per-mode DIMS, atomic mode switching, downloads dropdown, pixel-art rendering. Best for: multi-dataset visualizations where each mode has its own dimensions (sprite browsers, A/B/C dataset comparisons).

</td>
</tr>
</table>

All templates share `gallery-base.css` + `gallery-base.js` (tokens, toolbar, controls, filters, starring, lightbox, downloads dropdown, toasts). See `references/gallery-templates/README.md` for the customisation guide.

### Showcases

`references/showcases/` — one reference demo per skill (`showcase-chart`, `showcase-epic`, `showcase-gallery`, `showcase-guide`, `showcase-md`, `showcase-presentation`, `showcase-slides`). Use as canonical style + structure examples when authoring new outputs.

`references/diagrams/examples/` — golden craft diagrams (`craft-hub-spoke.html`, `craft-deploy-flow.html`). `showcase-presentation.html` demonstrates iframe integration.

**Catalog:** `references/showcase-index.html` — every skill output, craft diagram, fd-engine golden, fgraph template preview, and gallery shell (search + filter). See **`references/README.md`** for the full regenerate pipeline (`build-reference-showcases.py` → `validate-reference-runtime.py` → `make -C plugins/forge deploy`).

## How it works

### Brand-aware

Checks `~/.roxabi/forge/<project>/brand/forge.yml` (full schema) and `~/.roxabi/forge/<project>/brand/BRAND-BOOK.md` (legacy palette-only) before choosing a palette. Aesthetic presets live under `references/aesthetics/` (e.g. `lyra-v2`, `cool-dark`) and are inlined into output. A `scripts/check-brand-drift.sh` pre-commit guard keeps `gallery-base.css` defaults aligned to the Roxabi palette.

### Manifest-indexed

Every HTML file includes `diagram:*` meta tags parsed by `serve.py` and `gen-manifest.py` into `manifest.json` (diagram registry) — powers the gallery UI at `http://localhost:8080/`. Image directories use separate `img-manifest.json` files (generated by `gen-image-manifests.py`).

### Cloudflare Pages

#### One-time setup

**1. Prerequisites** — Node.js available (`npx` is used to invoke `wrangler`; no global install required).

**2. Create an API token** at <https://dash.cloudflare.com/profile/api-tokens> with scopes:

| Scope | Permission |
|---|---|
| Account → Cloudflare Pages | Edit |
| Account → Account Settings | Read |
| User → User Details | Read |

**3. Get your Account ID** — Cloudflare dashboard → any domain → right sidebar → **Account ID**.

**4. Login + create the Pages project** (once per account):

```bash
npx wrangler login                                # browser OAuth
npx wrangler pages project create forge \
  --production-branch=main                        # project name must match Makefile (--project-name=forge)
```

**5. Configure `.env`** — `runtime/.env.example` is deployed to `~/.roxabi/forge/.env` by `make -C plugins/forge deploy`. Fill it in:

```bash
# ~/.roxabi/forge/.env
CLOUDFLARE_ACCOUNT_ID=<account-id-from-step-3>
CLOUDFLARE_API_TOKEN=<token-from-step-2>
DEPLOY_HOST=forge.roxabi.com                      # optional — custom domain for Pages
```

The Makefile auto-loads `.env` and exports the Cloudflare vars so `wrangler` picks them up.

#### Deploy

```bash
make forge deploy       # from the supervisor hub directory (~/projects/)
# or
make -C ~/.roxabi/forge deploy
```

`deploy` runs `build` (regenerates manifest + syncs to `_dist/`) then `npx wrangler pages deploy _dist --project-name=forge --branch=main`. It refuses to run on a dirty git tree.

`make -C plugins/forge deploy` also copies diagram scripts to `~/.roxabi/forge/scripts/`: `gen-fd.py`, `validate-fd.py`, `validate-fd-browser.py` (plus `render-md`, `build.sh`, OG helpers).

#### Size limits

Cloudflare Pages caps individual files at **25 MB**. The build excludes `*.mp4` and any file >25 MB from `_dist/` (warning printed), and purges existing oversize files on each run. Host large media elsewhere (R2, S3, etc.) and link in.

### BATCHES pattern (galleries)

Single `BATCHES` array = source of truth. Adding a new batch = one line. Everything else derives automatically.

### Dynamic filters (galleries)

All filter buttons start **OFF** — filter is inactive, all images shown. Clicking a button activates that filter dimension. Values auto-discovered from data at load time.

## Output paths

| Context | Path |
|---------|------|
| Guide / epic / chart / presentation / slides (exploration) | `~/.roxabi/forge/<project>/visuals/` |
| Guide (final / canonical) | `~/projects/<project>/docs/visuals/` |
| Gallery | `~/.roxabi/forge/<project>/` |
| Cross-project chart | `~/.roxabi/forge/_shared/diagrams/` |

## Serving

```bash
# Full gallery — forge supervisord on :8080
http://localhost:8080/

# Standalone (split-file guide or epic)
cd ~/.roxabi/forge/<project>/visuals && python3 -m http.server 8080

# Single-file artifact (chart, slides, presentation, md) — no server needed
file://~/.roxabi/forge/<project>/visuals/<name>.html
```
