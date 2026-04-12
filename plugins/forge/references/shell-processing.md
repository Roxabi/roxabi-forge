# Shell Processing — Split-File Pipeline

Shared pipeline for all split-file skills (forge-guide, forge-epic). Each skill defines `{NAME}` and skill-specific placeholder values; the pipeline steps are identical.

See also: `split-file.md` for the file layout pattern (version isolation, tab fragments, serving).

## Steps

1. Read `shells/split.html` template
2. Concatenate base CSS files in order: `reset → layout → typography → components → explainer-base`
3. Read selected aesthetic CSS
4. Read `base/theme-toggle.js`, substitute `{NAME}` with the skill-defined name value
5. Read `base/tab-loader.js`, substitute `{NAME}` with the skill-defined name value
6. Substitute placeholders:
   - `{NAME}` → skill-defined, must match `/^[a-z0-9-]+$/` (kebab-case only — used inside `<script>` string literals)
   - `{BASE_STYLES}` → concatenated base CSS
   - `{AESTHETIC_STYLES}` → selected aesthetic CSS
   - `{TITLE}` → skill-defined
   - `{DATE}`, `{CATEGORY}`, `{CAT_LABEL}`, `{COLOR}`, `{BADGES}` → diagram metadata
   - `{HEADER}` → styled header block (eyebrow, title, subtitle, verdict badges)
   - `{TABS}` → tab button elements (one per tab)
   - `{PANELS}` → panel container elements (one per tab)
   - `{MAIN_WRAP_START}` / `{MAIN_WRAP_END}` → content area wrapper (standard or with TOC sidebar)
   - `{THEME_TOGGLE_JS}` → theme-toggle.js with `{NAME}` substituted
   - `{TAB_LOADER_JS}` → tab-loader.js with `{NAME}` substituted
   - `{HEAD_EXTRAS}` → optional (e.g., svg-pan-zoom CDN for Mermaid)
   - `{EXTRA_STYLES}` → skill-specific CSS additions
   - `{EXTRA_SCRIPTS}` → optional (e.g., mermaid-init.js)
7. Output: split-file HTML (requires HTTP serve)

## fgraph Integration

If any tab fragment uses fgraph diagrams (`.fgraph-wrap`, `.fgraph-node`, `.fgraph-edges`):

1. **Link `fgraph-base.css`** in the shell `<head>`, after the guide CSS link:
   ```html
   <link rel="stylesheet" href="css/{NAME}.css">
   <link rel="stylesheet" href="../../_shared/fgraph-base.css">
   ```
   fgraph-base.css is linked (Mode B), not inlined — it is a shared runtime dependency at `~/.roxabi/forge/_shared/fgraph-base.css`. This follows the same pattern as `gallery-base.css`.

2. **Add fgraph color tokens** to the guide CSS (in the guide-specific section) if the aesthetic file does not define them. fgraph-base.css consumes these tokens:
   - `--amber`, `--amber-dim`, `--cyan`, `--cyan-dim`, `--green`, `--green-dim`, `--purple`, `--purple-dim`, `--red`, `--red-dim`
   - `--border-bright`, `--surface2`, `--bg-panel`, `--bg-card`, `--accent-glow`

   Aesthetic files that already define these tokens (check by reading the aesthetic CSS): no additional tokens needed. Aesthetic files that only define the base 8 tokens (`--bg`, `--surface`, `--border`, `--text`, `--text-muted`, `--text-dim`, `--accent`, `--accent-dim`): add the missing fgraph tokens in the guide CSS.

3. **Add Google Fonts** used by fgraph: `Space Mono:wght@400;700` (used in `.fgraph-sub`, `.fgraph-pill`, `.fgraph-lbl`, `.fgraph-legend`). Append to the existing Google Fonts `<link>` in `<head>`.

---

## Skill-Specific Overrides

| Placeholder | forge-guide | forge-epic |
|---|---|---|
| `{NAME}` | diagram slug | `{ISSUE}-{slug}` |
| `{TITLE}` | free-form title | `{PROJ} #{ISSUE} — {Short Title}` |
| `{EXTRA_STYLES}` | guide-specific CSS (if any) | epic-hero + status badge CSS |
