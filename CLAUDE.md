@.claude/stack.yml

# Roxabi Forge

HTML visual artifacts for Claude Code — diagrams, galleries, guides, epics.

## TL;DR

- **Project:** roxabi-forge (marketplace with 1 plugin: forge)
- **Before work:** Use `/dev #N` as the single entry point
- **Never** use `--force`/`--hard`/`--amend`
- **Always** use appropriate skill even without slash command

## Structure

```
roxabi-forge/
├── .claude-plugin/
│   ├── marketplace.json         # marketplace manifest (forge plugin)
│   └── plugin.json              # plugin metadata (version, author)
├── plugins/
│   └── forge/
│       ├── skills/              # 8 skills: forge-init, forge-chart, forge-epic, forge-gallery, forge-guide, forge-md, forge-presentation, forge-slides
│       ├── references/          # HTML/CSS/JS templates, design docs, aesthetics
│       │   ├── slide-templates/ # scroll-snap deck engine (generation source, always inlined)
│       │   ├── showcases/       # reference demo (showcase-chart — fd-engine premium pipeline)
│       │   ├── device-frames/   # iOS/Android device frame CSS for mobile mockups
│       │   ├── aesthetics/      # brand presets (lyra-v2, cool-dark, …) — inlined into output
│       ├── runtime/             # Makefile + run.sh + .env.example for ~/.roxabi/forge/
│       └── Makefile             # deploy target (copies runtime → ~/.roxabi/forge/)
├── scripts/                     # Build scripts (build.sh, gen-manifest.py, gen-plugin-manifest.py, render-md{,-tabs}.py, etc.)
└── CLAUDE.md                    # this file
```

## Runtime

Forge generates HTML artifacts into `~/.roxabi/forge/<project>/`. A dev server (`serve.py`) watches for changes and pushes SSE live-reload events.

```bash
# From ~/.roxabi/forge/ (after plugin deploy)
make serve           # local gallery :8080 (foreground, Ctrl+C)

# Deploy plugin files → ~/.roxabi/forge/
make -C plugins/forge deploy

# Build + deploy to Cloudflare Pages
make -C ~/.roxabi/forge deploy
```

## Editing & Syncing

Source of truth: `plugins/forge/` in this repo.

Workflow to ship plugin changes to users:

1. Edit under `plugins/forge/`.
2. Bump `version` in `.claude-plugin/plugin.json` (run `scripts/gen-plugin-manifest.py` to mirror it into `marketplace.json`).
3. Push to `staging` → merge to `main`.
4. Users run `claude plugin update forge` (or `claude plugin install forge` on first install via `claude plugin marketplace add Roxabi/roxabi-forge`). Claude Code's marketplace updater fetches the new version from GitHub keyed on `plugin.json` → `version`.

## Plugin manifests (generated)

`.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` are partially generated from SKILL.md frontmatter. Do not hand-edit the skill enumeration in either `description` field.

**Source of truth**

| Field | Where |
|---|---|
| plugin version | `.claude-plugin/plugin.json` → `version` (bump manually) |
| skill list | each `plugins/forge/skills/*/SKILL.md` frontmatter `name` + `summary` |
| marketplace plugin version | mirrored from `plugin.json.version` |

**Workflow**

```bash
# Add/rename/remove a skill, or bump plugin.json.version
scripts/gen-plugin-manifest.py        # regenerate both manifests
scripts/gen-plugin-manifest.py --check # what pre-commit runs
```

The `manifest` pre-commit hook (`lefthook.yml`) runs `--check` when SKILL.md or `.claude-plugin/*.json` change; commit fails on drift. Every SKILL.md must declare a `summary:` field.

## Distribution rule (inline vs linked)

Each `references/` sub-tree has a distribution profile. Skills inline or link its contents per the rule below — do not deviate without updating this table.

| Sub-tree | Distribution | Rationale |
|---|---|---|
| `base/`, `aesthetics/` | **inline** into output `<style>` | generation source, not runtime |
| `graph-templates/` (fgraph) | **inline** for single-file OR **link** `_shared/fgraph-base.css` for multi-tab docs with ≥ 2 fgraph diagrams | matches gallery-base precedent |
| `graph-templates/*.js` (fgraph-auto, fgraph-interact) | **inline** into output `<script>` — live mode only | runtime, file://-safe, strict no-op without a `data-fgraph="live"` wrap |
| `gallery-templates/` | **link** `_shared/gallery-base.{css,js}` | runtime-shared across gallery outputs |
| `slide-templates/` | **always inline** into single-file `<style>`/`<script type="module">` | `forge-slides` produces `file://`-safe offline decks; no `_shared/slide-templates/` mirror |
| `plugins/forge/skills/<name>/references/` (per-skill) | **Read on-demand** via `Read ${CLAUDE_PLUGIN_ROOT}/skills/<name>/references/<file>.md before <action>.` directive in the skill body | skill-scoped prose offloaded to cut SKILL.md bulk; not inlined into output, not linked at runtime |

When generating a new skill, pick the profile above for each `references/` sub-tree it consumes. Adding a new sub-tree? Add a row here.

## Style

- Single quotes, no semicolons (JS)
- Markdown: ATX headings, tables for structured data, code blocks for commands
