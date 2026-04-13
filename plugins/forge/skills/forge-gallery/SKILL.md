---
name: forge-gallery
description: 'Create or update an image or audio gallery from HTML templates — pivot grouping, dynamic filtering, sorting, search, size controls, lightbox, multi-mode datasets, downloads dropdown. Triggers: "showcase" | "compare visually" | "gallery" | "side by side" | "create a gallery" | "show iterations" | "multi-mode gallery" | "sprite gallery".'
summary: 'image / audio gallery'
version: 0.4.0
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, ToolSearch, Agent
---

# Gallery — Image / Audio

Create a self-contained HTML gallery from a template. Galleries live at `~/.roxabi/forge/<project>/`.

**Read before generating:**

```
${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md                       — brand detection, output paths, deploy commands
${CLAUDE_PLUGIN_ROOT}/references/aesthetics/                        — lyra.css, roxabi.css (brand tokens)
${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md                    — meta tag format + categories
${CLAUDE_PLUGIN_ROOT}/references/gallery-templates/README.md        — template guide + customisation steps
${CLAUDE_PLUGIN_ROOT}/references/gallery-templates/pivot-gallery.html — full working template
```

---

## Design Phase — Frame → Structure → Style → Deliver

Decisions made across Phases 1–4 follow this lens. It is an overlay on the procedural phases, not a separate pre-phase: Frame runs in Phase 1 (context), Structure in Phase 2 (template pick), Style in Phase 3 (customize), Deliver in Phase 4 (report + verify).

### Track selection (Phase 1 start)

Run the brand book loader (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`) before any other decision:

- **Track A (branded)** — `forge.yml` found in project `brand/` → aesthetic/palette/typography locked; `deliver_must_match` rules enforced at Deliver. Template selection is content-driven in both tracks (gallery templates serve reader-action, not brand).
- **Track B (exploration)** — no brand book → full Frame judgment.

Full track-by-track behavior: `${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md`.

Report the loaded brand book (or its absence) before starting Frame. Track is fixed at Phase 1 and does not change.

### Frame — What's this visual for?

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md` — three Frame signals, reader-action matrix, tone dimensions, example trace.

**For forge-gallery specifically, Signal 1 (reader-action) is the most critical to infer.** A gallery is consumed differently depending on whether the viewer is *deciding* (pick one concept) or *exploring* (browse the space). Deciding → `comparison-gallery.html` with verdict badges. Exploring → `pivot-gallery.html` or `simple-gallery.html` with filters. The same 20 images need different templates for different reader actions.

- **Track A:** infer Signal 1 (reader-action) and Signal 2 (takeaway) from the prompt. Tone is pre-constrained by brand voice rules — no tone inference needed. Template is still content-driven.
- **Track B:** infer Signal 1, Signal 2, and full Signal 3 from the prompt and content.

Aesthetic is never chosen by Frame — it's mechanical (see `forge-ops.md § Aesthetic Detection`). Frame produces purpose, not CSS.

### Structure — Which template?

See **Phase 2 — Pick Template** below for the full template table (single source of truth). Frame's reader-action output (decide vs. explore vs. audit) maps to templates as follows:

- Deciding between spec-rich options → `comparison-gallery.html`
- Exploring 1 dimension → `simple-gallery.html`
- Exploring 2+ dimensions → `pivot-gallery.html`
- Comparing audio clips → `audio-gallery.html`
- Browsing multiple datasets → `multi-mode-gallery.html`

### Style — Which components?

| Gallery type | Toolbar | Filters | Cards |
|---|---|---|---|
| Pivot | Col/Row segs + score input | Dynamic from DIMS (auto-built) | Thumbnail + metadata |
| Simple | Batch tabs + search + size | Optional | Thumbnail |
| Comparison | Sort dropdown | None (flat) | Card with spec table |
| Audio | Engine groups | Dynamic | `<audio>` player + metadata |
| Multi-mode | Mode tabs + segs + downloads | Per-mode DIMS | Mode-specific cards |

**Rendering wrappers** — orthogonal to gallery type. Apply these to whatever template the Structure phase chose:

| Rendering | Wrapper / component |
|---|---|
| Progressive disclosure | `details.disclosure` for secondary info in cards, `.has-tip` for term definitions |
| Metadata strip | `.kv-strip` for inline key-value pairs in gallery header or card details |
| Section anchor | `.summary-card` at start of each mode tab (not filter groups) |

**Signal:** Is the viewer DECIDING or EXPLORING (from Frame Signal 1)? Deciding needs spec tables + verdict badges + a single clear recommendation. Exploring needs filters + sort + size controls + low-friction browse. If the same gallery has to serve both, build two views, not one.

### Deliver — Generate + verify

**Always** (both tracks):
- Walk `references/anti-patterns.md` before emitting HTML — confirm no rule is violated, or invoke a named exception.
- DIMS object defines all grouping dimensions.
- Filter buttons auto-built from data (not hardcoded — use `buildDimFilters`).
- Lightbox works (click → overlay, Escape to close).
- Lazy loading on all images (`loading="lazy"`).
- All images have meaningful `alt` text (fallback to filename if nothing better).
- Size controls (±) work for thumbnails (image galleries).
- Search filters visible items.
- `diagram-meta` tags present.
- Stats counter shows "visible / total".
- Interactive controls (tabs, segs, size buttons) have visible `:focus-visible` styling.
- Gallery layout reflows without horizontal scroll below 375px viewport.
- **Body copy (card labels, metadata rows) uses `var(--text)` for dark-mode readability.** `var(--text-muted)` for subtitles; `var(--text-dim)` for metadata only.
- Verify Frame Signal 2 takeaway is surfaced — the viewer should know what this gallery is for within 5 seconds (title, subtitle, or stat counter).

- Every tab/section starts with a `.summary-card` or `.stat-grid` (glance layer present).
- No visible text block exceeds 4 sentences without a break or disclosure wrapper.
- Metadata uses `.kv-strip` or structured table, not inline prose.

**Track A additionally:**
- Run every `brand.deliver_must_match` rule against the generated gallery HTML. Report pass/fail per rule. Do not write the file until all rules pass or the user overrides.
- If `brand.examples` list is non-empty, offer to visually compare the generated gallery against one canonical brand gallery before writing.

---

## Output UX — Schema Over Prose

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/output-ux.md` — three-layer information architecture, 10 mandatory rules, anti-patterns.

**For forge-gallery specifically:** galleries are visual-first — the thumbnail grid IS the Glance layer. Progressive disclosure applies to card metadata (collapse rare spec details into `details.disclosure`). Summary-card (Rule 9) applies to mode tabs only, not filter groups. The 4-sentence rule (Rule 7) applies to card descriptions, not to filter/toolbar UI.

---

## Context Isolation — Sub-Agent Generation

Heavy HTML/CSS/JS generation runs in a **sub-agent** to keep the main conversation context clean. The main skill thread handles decisions (Phase 1–2); the sub-agent handles file generation (Phase 3).

### When to delegate

| Condition | Action |
|---|---|
| Gallery from template (copy + customize) | Generate inline (template-driven) |
| Complex multi-mode gallery with many DIMS + custom logic | **Delegate Phase 3 to sub-agent** |
| Any output > ~300 lines total | **Delegate to sub-agent** |

Galleries are mostly template copy + customize — inline is usually fine. Delegate only for complex multi-mode galleries.

### How to delegate

1. Complete Phase 1 (context) and Phase 2 (template pick + DIMS plan) in the main thread
2. Spawn a sub-agent with a self-contained prompt that includes:
   - The resolved decisions: template, aesthetic, DIMS definition, output path, slug
   - The content to render (image/audio paths, data JSON location, batch structure)
   - All file paths for gallery-base.css, gallery-base.js, chosen template
   - The exact placeholder values and DIMS object to inline
3. The sub-agent generates the gallery file and returns the file path
4. Main thread runs Phase 4 (report) with the returned path

### Sub-agent prompt template

```
Generate forge-gallery output file.

Decisions (from Phase 1-2):
- Track: {A|B}
- Aesthetic: {file}
- Template: {template filename}
- DIMS: {full DIMS object definition}
- Output path: {path}/{slug}.html
- Slug: {slug}

Read these reference files:
- {gallery-base.css path}
- {gallery-base.js path}
- {chosen template path}

Then generate:
- {output file path}

Content to render:
- Image/audio root: {path}
- Data JSON: {path or null}
- Batches: {list}

Rules:
- Fill all {{PLACEHOLDERS}} in the template
- Wire DIMS object exactly as specified
- Use buildDimFilters / applyDimFilters from gallery-base.js
- Brand tokens from aesthetic file (Track A: skip rewrite; Track B: inline :root block)
```

The sub-agent has access to Read, Write, Edit, Bash, Glob, Grep tools — it can read all reference files and write the output file independently.

---

## Phase 1 — Context

1. **Ensure shared assets exist:**
   ```bash
   ls ~/.roxabi/forge/_shared/gallery-base.css ~/.roxabi/forge/_shared/gallery-base.js 2>/dev/null
   ```
   Missing → create `~/.roxabi/forge/_shared/` and copy from `${CLAUDE_PLUGIN_ROOT}/references/gallery-templates/gallery-base.{css,js}`. Continue silently.

2. **Detect project** from ARGS or cwd.
3. **Detect gallery type** from ARGS: image or audio.
4. **Gallery slug** (kebab-case) from ARGS.
5. **Check existing:** offer to add batch or start fresh.
6. **Run the brand book loader** (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`): Discovery → Parse → Apply. Determine Track A or Track B. Report the result before continuing.
7. **Check for data JSON** (`face-scores.json` etc.) — enables score/cluster filtering.

---

### Frame Trace

After inferring all signals, emit a one-line summary before proceeding to Phase 2. This is not a question — it is a statement the user can interrupt if the inference is wrong:

```
Frame: reader={signal1_reader}, action={signal1_action}, takeaway={signal2}, tone={signal3_summary}. Generating...
```

Example: `Frame: reader=designer, action=deciding, takeaway=V12 concept best matches brand direction, tone=warm+reflective. Generating...`

---

## Phase 2 — Pick Template

Read `${CLAUDE_PLUGIN_ROOT}/references/gallery-templates/README.md` for the full list.

| Need | Template | Key features |
|------|----------|-------------|
| Image comparison with scoring | `pivot-gallery.html` | Pivot matrix, dynamic filters, sort, search, size, lightbox |
| Basic batch comparison | `simple-gallery.html` | Batch tabs, lightbox, search, size |
| Side-by-side with specs | `comparison-gallery.html` | Cards with metadata tables |
| Audio/voice comparison | `audio-gallery.html` | Audio players, engine grouping |
| **Multi-dataset / multi-mode** | **`multi-mode-gallery.html`** | **Mode tabs, per-mode DIMS, dynamic pivot segs, downloads dropdown, sprite/pixel support** |

Copy the chosen template to `~/.roxabi/forge/{PROJ}/{SLUG}.html`.

### When to use items-as-objects vs filename-strings

`buildDimFilters` and `applyDimFilters` are **dual-API** — each element of the `items` array is passed verbatim to `dim.fn`. You pick the representation:

- **Filename-strings** — each item is a string, `dim.fn` parses substrings. Fast to set up, no item-building pipeline. Used by `pivot-gallery.html`. Good when filenames already encode all metadata and there's one dataset.
- **Items-as-objects** — each item is `{file, dir, label, ...custom fields}`, `dim.fn` reads fields directly (e.g. `it => it.rarity`). Cleaner for multiple dimensions, multiple modes, or data composed from multiple sources. Used by `comparison-gallery.html`, `audio-gallery.html`, `multi-mode-gallery.html`.

For multi-mode galleries, always use items-as-objects — each mode's dims read different fields from the same item shape. See the gallery-templates README § "Items-as-objects vs filename-strings" for worked examples.

---

## Phase 3 — Customise

Follow the steps in the template's README:

### 1. Fill `{{PLACEHOLDERS}}`

Replace all `{{...}}` in the HTML: title, date, subtitle, image directory, data JSON path, reference image, `{{GALLERY_BASE_CSS}}` → `../../_shared/gallery-base.css`, `{{GALLERY_BASE_JS}}` → `../../_shared/gallery-base.js`.

### 2. Define dimensions (`DIMS` object)

Each dimension = a way to classify images. Add one entry per grouping axis:

```javascript
const DIMS = {
  batch: {
    label: 'Batch',
    fn: f => f[0],              // how to extract category from filename
    order: ['A','B','C','D'],   // sort order (optional)
  },
  // Add more: score, shot, cluster, etc.
};
```

Values are **auto-discovered** from data — the template creates filter buttons with counts automatically. No hardcoded button lists.

### 3. Pivot seg buttons — prefer dynamic construction

**Modern approach** (`pivot-gallery.html`, `multi-mode-gallery.html`): leave the Col/Row `<div class="segs">` containers empty and call `buildPivotSegsFromDims(DIMS, 'colSegs', 'rowSegs', onChange, initial?)` at boot. The helper iterates `Object.entries(dims)` and builds the buttons automatically. Add a new DIMS key and the button appears — no HTML sync needed.

**Legacy approach** (other templates): for each DIMS key, add a `<button class="seg" data-v="KEY">Label</button>` in both the Col and Row segmented controls manually. Kept for compat with existing galleries — new templates should use the helper.

### 4. Remove unused features

- No reference image → delete `<div class="ref">`
- No score data → set `DATA_URL = null`, remove score dim
- No pivot → remove Col/Row controls (defaults to flat grid)

### 5. Brand tokens

- **Track A** — skip. The loader already resolved `brand.aesthetic` at Phase 1 and the aesthetic file (e.g. `lyra.css`) owns `:root`. Do not rewrite tokens; `deliver_must_match` will flag any accent or palette drift at Deliver.
- **Track B** — inline the chosen aesthetic's `:root` block into the gallery template's `<style>` (reference: `${CLAUDE_PLUGIN_ROOT}/references/aesthetics/*.css`). Override `--accent` / `--accent-dim` only if the gallery is a cross-project showcase that needs its own accent.

---

## Phase 4 — Report

```
Created: ~/.roxabi/forge/{PROJ}/{SLUG}.html
Template: {template name}

View:    make forge → http://localhost:8080/{PROJ}/{SLUG}.html
         (or: cd ~/.roxabi/forge && python3 -m http.server 8080)
Deploy:  make forge deploy
```

---

## Key patterns (reference)

These are implemented in the templates. Read the template source for details.

**Filter logic:** All buttons OFF = filter inactive = show everything. Clicking a button activates that dimension. This is opt-in filtering, not opt-out.

**Three rendering modes:**
- Both Col/Row = None → flat grid
- One axis set → grouped list with section headers
- Both axes set → pivot matrix table with sticky headers

**Dynamic filter builder:** At load time, scans all files through each DIMS function, discovers unique values, creates toggle buttons with counts. No hardcoded values.

**Data-driven enrichment:** When a JSON file exists (scores, clusters), the template loads it and enables score sorting/filtering and cluster grouping as additional dimensions.

**Image discovery:** img-manifest.json (Cloudflare) → /api/list/ fallback (local dev) → data JSON keys fallback.

---

## Feature checklist

Every gallery MUST include:

| Feature | Required | Notes |
|---------|----------|-------|
| Image discovery | ✅ | img-manifest.json + API fallback |
| Lightbox | ✅ | Click → full-size overlay, Escape to close |
| Lazy loading | ✅ | `loading="lazy"` on all images |
| diagram-meta | ✅ | Standard meta tags |
| Brand tokens | ✅ | From tokens.md |
| **Sort controls** | ✅ | Score ↓/↑, Name |
| **Search** | ✅ | Text filter on filenames |
| **Size +/−** | ✅ (image) | 40–200px thumbnail adjustment |
| **Stats counter** | ✅ | "visible / total" |
| **Dynamic filters** | ✅ | Auto-built from DIMS, OFF by default |
| Pivot grouping | When ≥2 dimensions | Col/Row segmented controls |
| Score filtering | When data JSON exists | Min score input |
| Starring | Optional | localStorage persistence |

$ARGUMENTS
