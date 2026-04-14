---
name: forge-md
description: >-
  Render existing markdown files to themed self-contained HTML — single-file
  preview or multi-tab combined doc. Use when the user has finished markdown
  and just wants it rendered as-is (no tab planning, no rewriting). Triggers:
  "render md" | "render markdown" | "md to html" | "tabbed docs" | "combine
  markdown" | "preview md" | "forge md" | "render this folder" | "make a
  tabbed doc from these md files".
summary: 'render .md as-is to themed HTML'
version: 0.1.0
allowed-tools: Read, Bash, Glob
---

# Forge MD — Render Markdown As-Is

Thin wrapper around `render-md.py` (single file) and `render-md-tabs.py` (multi-file tabbed). Use when the user has already authored markdown and wants it rendered — **do not rewrite, restructure, or plan tabs**. The scripts handle sorting, tab labels, mermaid, tables, task lists, roxabi dark aesthetic.

## When to use this skill vs. others

| User has | Use |
|---|---|
| Finished `.md` files, wants HTML preview | **forge-md** (this) |
| Idea/topic, wants a multi-tab HTML doc designed from scratch | `forge-guide` |
| Slide deck from markdown | `forge-slides` |
| Single chart/diagram | `forge-chart` |

If unsure: existing markdown on disk → this skill; "write me a guide about X" → `forge-guide`.

## Scripts

Located in this repo at `~/projects/roxabi-forge/scripts/` and deployed to `$FORGE_DIR/scripts/` via `make -C plugins/forge deploy`.

```
scripts/render-md.py        single .md → <input>.preview.html (self-contained)
scripts/render-md-tabs.py   N × .md → one tabbed HTML with URL-hash deep links
```

Both are `uv run --script` shebangs — no venv needed, deps auto-resolve.

## Usage

### Single file preview

```bash
~/projects/roxabi-forge/scripts/render-md.py <input.md>
# → <input>.preview.html next to the source
```

Or explicit output:

```bash
~/projects/roxabi-forge/scripts/render-md.py <input.md> -o <output.html>
```

### Multi-file tabbed doc

```bash
# all *.md in a directory
~/projects/roxabi-forge/scripts/render-md-tabs.py <dir> -o <out.html> -t "<title>"

# explicit files (order is re-sorted by the script's sort_key)
~/projects/roxabi-forge/scripts/render-md-tabs.py f1.md f2.md f3.md -o <out.html> -t "<title>"
```

**Tab sorting (hardcoded in `render-md-tabs.py`):**

1. `README.md` → "Overview" (always first)
2. Numeric-prefixed: `07-priority-sequencing.md` → "07 · Priority sequencing"
3. `action-*`
4. `*-review`
5. `validation-*`
6. Everything else, alphabetical

Deep links: `<out.html>#doc-<stem>` (e.g. `#doc-README`, `#doc-07-priority-sequencing`).

## Output path convention

| Scope | Path |
|---|---|
| Exploration / scratch | `~/.roxabi/forge/<project>/` |
| Final, versioned with code | `~/projects/<project>/docs/visuals/` or next to the source `.md` |

Mirrors `forge-guide` conventions — see `${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md`.

## Flow

1. Confirm the user has markdown files ready (ask for path if not provided)
2. Single file → `render-md.py`; directory or ≥ 2 files → `render-md-tabs.py`
3. Pick output path per convention above
4. Run the script via `Bash`
5. Report absolute path + `file://` URL so the user can open it

Do **not** edit the source markdown. Do **not** inline CSS manually — the scripts already embed the roxabi dark aesthetic.

## Do not

- Rewrite or reorganize the markdown
- Plan tab structure (the script sorts by filename)
- Re-implement rendering — always shell out to the scripts
- Pass non-`.md` files (scripts skip them with a warning)
