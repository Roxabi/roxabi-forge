@.claude/stack.yml

# Roxabi Forge

HTML visual artifacts for Claude Code — diagrams, galleries, guides, epics.

## TL;DR

- **Project:** roxabi-forge (marketplace with 1 plugin: forge)
- **Before work:** Use `/dev #N` as the single entry point
- **Decisions:** summarize context → numbered options + recommendation → wait for reply
- **Never** use `--force`/`--hard`/`--amend`
- **Always** use appropriate skill even without slash command

### Git

Format: `<type>(<scope>): <desc>` + `Co-Authored-By: Claude <model> <noreply@anthropic.com>`
Types: feat|fix|refactor|docs|style|test|chore|ci|perf
Never force/hard/amend. Hook fail → fix + NEW commit.

## Structure

```
roxabi-forge/
├── .claude-plugin/
│   ├── marketplace.json         # marketplace manifest (forge plugin)
│   └── plugin.json              # plugin metadata (version, author)
├── plugins/
│   └── forge/
│       ├── skills/              # 6 skills: forge-init, forge-guide, forge-epic, forge-chart, forge-gallery, forge-slides
│       ├── references/          # HTML/CSS/JS templates, design docs, aesthetics
│       │   ├── slide-templates/ # scroll-snap deck engine (generation source, always inlined)
│       ├── runtime/             # Makefile + .env.example for ~/.roxabi/forge/
│       ├── supervisor/          # supervisord config + wrapper script
│       └── Makefile             # deploy + register targets
├── scripts/                     # Build scripts (build.sh, gen-manifest.py, etc.)
├── sync-plugins.sh              # Sync to local/remote plugin caches
└── CLAUDE.md                    # this file
```

## Runtime

Forge generates HTML artifacts into `~/.roxabi/forge/<project>/`. A dev server (`serve.py`) watches for changes and pushes SSE live-reload events.

```bash
# From ~/projects/ (supervisor hub)
make forge start     # start dev server
make forge logs      # tail stdout
make forge stop      # stop server

# Deploy plugin files → ~/.roxabi/forge/
make -C plugins/forge deploy

# Build + deploy to Cloudflare Pages
make -C ~/.roxabi/forge deploy
```

## Editing & Syncing

Source of truth: `plugins/forge/` in this repo.

```bash
# After editing, sync to all local cache dirs
./sync-plugins.sh --local

# Sync local + remote (Machine 1)
./sync-plugins.sh
```

## Distribution rule (inline vs linked)

Each `references/` sub-tree has a distribution profile. Skills inline or link its contents per the rule below — do not deviate without updating this table.

| Sub-tree | Distribution | Rationale |
|---|---|---|
| `base/`, `aesthetics/` | **inline** into output `<style>` | generation source, not runtime |
| `graph-templates/` (fgraph) | **inline** for single-file OR **link** `_shared/fgraph-base.css` for multi-tab docs with ≥ 2 fgraph diagrams | matches gallery-base precedent |
| `gallery-templates/` | **link** `_shared/gallery-base.{css,js}` | runtime-shared across gallery outputs |
| `slide-templates/` | **always inline** into single-file `<style>`/`<script type="module">` | `forge-slides` produces `file://`-safe offline decks; no `_shared/slide-templates/` mirror |

When generating a new skill, pick the profile above for each `references/` sub-tree it consumes. Adding a new sub-tree? Add a row here.

## Style

- Single quotes, no semicolons (JS)
- Markdown: ATX headings, tables for structured data, code blocks for commands
