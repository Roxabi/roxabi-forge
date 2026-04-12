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
│       ├── skills/              # 5 skills: forge-init, forge-guide, forge-epic, forge-chart, forge-gallery
│       ├── references/          # HTML/CSS/JS templates, design docs, aesthetics
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

## Style

- Single quotes, no semicolons (JS)
- Markdown: ATX headings, tables for structured data, code blocks for commands
