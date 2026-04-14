---
name: forge-epic
description: >-
  Create an issue/epic-linked visual analysis — overview, scope breakdown,
  dependency graph, acceptance criteria. Filename always includes the issue
  number. Triggers: "visualize #N" | "preview #N" | "illustrate issue" |
  "map issue" | "epic preview" | "show epic".
summary: 'issue-linked visual analysis'
version: 0.2.0
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, ToolSearch, Agent
---

# Epic — Issue-Linked Visual Analysis

Create a visual analysis document tied to a specific GitHub issue or epic (`#N`).

Output: `~/.roxabi/forge/<project>/visuals/{N}-{slug}.html` (split-file).

**Read before generating:**

```
${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md        — brand detection, output paths, deploy commands
${CLAUDE_PLUGIN_ROOT}/references/base/reset.css      — concatenate first
${CLAUDE_PLUGIN_ROOT}/references/base/layout.css     — concatenate second
${CLAUDE_PLUGIN_ROOT}/references/base/typography.css — concatenate third
${CLAUDE_PLUGIN_ROOT}/references/base/components.css — concatenate fourth
${CLAUDE_PLUGIN_ROOT}/references/base/explainer-base.css — concatenate fifth (visual explainer components)
${CLAUDE_PLUGIN_ROOT}/references/aesthetics/         — select one based on detection logic
${CLAUDE_PLUGIN_ROOT}/references/shells/split.html   — HTML template with placeholders
${CLAUDE_PLUGIN_ROOT}/references/base/tab-loader.js    — substitute {NAME}, then inline via {TAB_LOADER_JS}
${CLAUDE_PLUGIN_ROOT}/references/base/theme-toggle.js — substitute {NAME}, then inline via {THEME_TOGGLE_JS}
${CLAUDE_PLUGIN_ROOT}/references/diagram-meta.md     — meta tag format + categories
${CLAUDE_PLUGIN_ROOT}/references/mermaid-guide.md    — dependency/breakdown diagrams
```

**Directive: inline, never link** — `base/` and `aesthetics/` files are generation source, not runtime dependencies. Read → inline into output `<style>` block.

---

## Design Phase — Frame → Structure → Style → Deliver

Decisions made across Phases 1–4 follow this lens. It is an overlay on the procedural phases, not a separate pre-phase: Frame runs in Phase 1 (context), Structure in Phase 2 (epic structure / tab set), Style in Phase 3 (generate), Deliver in Phase 4 (report + verify).

### Track selection (Phase 1 start)

Run the brand book loader (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`) before any other decision:

- **Track A (branded)** — `forge.yml` found in project `brand/` → aesthetic/palette/typography locked; `deliver_must_match` rules enforced at Deliver.
- **Track B (exploration)** — no brand book → full Frame judgment.

Full track-by-track behavior: `${CLAUDE_PLUGIN_ROOT}/references/design-phase-two-track.md`.

Report the loaded brand book (or its absence) before starting Frame. Track is fixed at Phase 1 and does not change.

### Frame — What's this visual for?

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/frame-phase.md` — three Frame signals, reader-action matrix, tone dimensions, example trace.

**For forge-epic specifically, Signal 1 (reader-action) is the most critical to infer.** An epic preview is read by contributors (who need scope + dependencies) OR by stakeholders (who need status + next milestone) OR by reviewers during acceptance (who need criteria). The same issue produces different tab sets for different readers. Infer which reader the prompt targets before picking tabs.

- **Track A:** infer Signal 1 (reader-action) and Signal 2 (takeaway) from the prompt. Tone is pre-constrained by brand voice rules — no tone inference needed.
- **Track B:** infer Signal 1, Signal 2, and full Signal 3 from the prompt and content.

Aesthetic is never chosen by Frame — it's mechanical (see `forge-ops.md § Aesthetic Detection`). Frame produces purpose, not CSS.

### Structure — Which tabs?

> **Tab IDs are fixed:** only `overview`, `breakdown`, `deps`, `criteria` are supported. Do not invent new IDs without adding the matching tab fragment pattern in Phase 3.

| Epic scope | Tabs | Rationale |
|---|---|---|
| Large feature (spec + impl) | `overview`, `breakdown`, `deps`, `criteria` | Full context needed |
| Medium feature | `overview`, `deps`, `criteria` | Skip breakdown if ≤3 tasks |
| Small fix / refactor | `overview`, `criteria` | Minimal, focused |

**Check:** How complex is the issue? Multi-milestone → all tabs. Simple fix → overview + criteria only.

The four tab IDs above (`overview`, `breakdown`, `deps`, `criteria`) are the only ones the epic shell supports today. Do not invent new tab IDs without adding the matching tab fragment pattern in Phase 3.

### Style — Which components?

All classes below exist in `base/components.css` + `base/explainer-base.css`, or are defined inline in Phase 3 under `{EXTRA_STYLES}`.

| Tab | Components |
|---|---|
| Overview | `.epic-hero` (inline — see Phase 3) + `.cards` grid with `.card.accent` |
| Breakdown | `.cards` grid or `.table-wrap > table` with `.status.done/wip/todo` badges (inline styles — see Phase 3) |
| Deps | Mermaid flowchart in `.diagram-shell` with zoom controls |
| Criteria | `.table-wrap > table` — checklist with status column |

**Rendering wrappers** — orthogonal to tab identity. Apply these to whatever rendering the Structure phase chose per tab:

| Rendering | Wrapper / component |
|---|---|
| Mermaid dependency diagram | `.diagram-shell` with `.zoom-controls` (never bare `<pre class="mermaid">`) |
| HTML table (breakdown / criteria) | `.table-wrap > table` with `<thead>` (enables sticky header + horizontal scroll) |
| CSS Grid cards | `.cards` container + `.card.accent` per row |
| Epic hero (Overview tab) | `.epic-hero > .epic-number + h1 + .epic-goal` (defined inline in Phase 3 `{EXTRA_STYLES}`) |
| Status badges | `.status.done` / `.status.wip` / `.status.todo` (defined inline in Phase 3 `{EXTRA_STYLES}`) |
| Progressive disclosure | `details.disclosure` for secondary info, `.has-tip` for term definitions |
| Metadata strip | `.kv-strip` for inline key-value pairs |
| Section anchor | `.summary-card` at start of each tab/section |

Cross-tab: use `.card.info` / `.card.warning` / `.card.critical` for inline tonal callouts.

**Check:** What visual signals does the reader need (inferred from Frame Signal 1)? Progress → status badges. Dependencies → Mermaid. Acceptance → checklist.

### Deliver — Generate + verify

**Always** (both tracks):
- Walk `references/anti-patterns.md` before emitting HTML — confirm no rule is violated, or invoke a named exception.
- `.epic-hero` shows issue number prominently.
- Status badges use correct colors (green `done`, amber `wip`, cyan `todo`) via the inline `.status` styles in Phase 3.
- Mermaid dep diagram wrapped in `.diagram-shell` — never bare `<pre class="mermaid">`.
- **Body copy uses `var(--text)` for maximum readability on dark backgrounds.** `var(--text-muted)` is for intermediate emphasis only (subtitles, label rows); `var(--text-dim)` is for metadata only.
- `diagram:issue` meta tag present and matches filename.
- No ASCII art, no emoji in headers.
- Tab buttons have `role="tab"` + `aria-selected` semantics.
- Interactive controls (theme toggle, zoom, tab buttons) have visible `:focus-visible` styling.
- Verify Frame Q2 takeaway is visible in the Overview tab — the reader should know the epic's one goal within 10 seconds.

- Every tab/section starts with a `.summary-card` or `.stat-grid` (glance layer present).
- No visible text block exceeds 4 sentences without a break or disclosure wrapper.
- Metadata uses `.kv-strip` or structured table, not inline prose.

**Track A additionally:**
- Run every `brand.deliver_must_match` rule against the generated tab fragments and shell. Report pass/fail per rule with the tab/line location. Do not write any file until all rules pass or the user overrides.
- If `brand.examples` list is non-empty, offer to visually diff the generated output against one canonical example.

---

## Output UX — Schema Over Prose

Full reference: `${CLAUDE_PLUGIN_ROOT}/references/output-ux.md` — three-layer information architecture, 10 mandatory rules, anti-patterns.

**For forge-epic specifically:** the Overview tab IS the Glance layer. `.epic-hero` with issue number + one-sentence goal + scope/status cards must communicate the epic's purpose in 5 seconds. Breakdown and Deps tabs use tables and diagrams (Scan layer). Acceptance criteria is the Deep layer — use `.table-wrap > table` with status column.

---

## Shell Processing

Follow `${CLAUDE_PLUGIN_ROOT}/references/shell-processing.md` — the shared split-file pipeline.

**Epic-specific overrides:**

| Placeholder | Value |
|---|---|
| `{NAME}` | `{ISSUE}-{slug}` |
| `{TITLE}` | `{PROJ} #{ISSUE} — {Short Title}` (e.g. "Lyra #477 — Tool Registry") |
| `{EXTRA_STYLES}` | epic-hero + status badge CSS (see Phase 3) |

Let:
  ARGS   := $ARGUMENTS
  ISSUE  := GitHub issue number (required — extract from ARGS or ask)
  AG     := `~/.roxabi/forge/`

---

## Context Isolation — Sub-Agent Generation

Heavy HTML/CSS/JS generation runs in a **sub-agent** to keep the main conversation context clean. The main skill thread handles decisions (Phase 1–2); the sub-agent handles file generation (Phase 3).

### When to delegate

| Condition | Action |
|---|---|
| Small single-tab epic (overview only, ≤ 200 lines) | Generate inline (rare) |
| Multi-tab epic (shell + CSS + JS + tabs) | **Always delegate Phase 3 to sub-agent** |
| Any output > ~300 lines total | **Delegate to sub-agent** |

Multi-tab epics produce shell + CSS + JS + tab fragments. Always delegate Phase 3.

### How to delegate

1. Complete Phase 1 (context + issue read) and Phase 2 (tab plan) in the main thread
2. Spawn a sub-agent with a self-contained prompt that includes:
   - The resolved decisions: aesthetic, tab plan, issue number, output paths, slug
   - The content to render (issue title, scope, tasks, deps, acceptance criteria)
   - All file paths for base CSS, aesthetic CSS, shell template, JS files
   - The exact placeholder values for shell substitution
3. The sub-agent generates all files and returns the file paths
4. Main thread runs Phase 4 (report) with the returned paths

### Sub-agent prompt template

```
Generate forge-epic output files.

Decisions (from Phase 1-2):
- Track: {A|B}
- Aesthetic: {file}
- Issue: #{ISSUE}
- Tab plan: {tab IDs and labels}
- Output root: {path}
- Slug: {ISSUE}-{slug}

Read these reference files:
- {list of base CSS, aesthetic CSS, shell template, JS files}

Then generate:
- ~/.roxabi/forge/{PROJ}/visuals/{ISSUE}-{slug}.html
- ~/.roxabi/forge/{PROJ}/visuals/css/{ISSUE}-{slug}.css
- ~/.roxabi/forge/{PROJ}/visuals/js/{ISSUE}-{slug}.js
- ~/.roxabi/forge/{PROJ}/visuals/tabs/{ISSUE}-{slug}/tab-{ID}.html (one per tab)

Content to render:
- Issue title: {title}
- Problem statement: {problem}
- Goal: {one-sentence goal}
- Scope / tasks: {list}
- Dependencies: {blocked-by / blocking}
- Acceptance criteria: {list}

Rules:
- Inline all CSS (base + aesthetic) into css/{ISSUE}-{slug}.css
- Follow shell-processing.md substitution pipeline
- Use semantic tokens from components.css
- Mermaid dep diagram wrapped in .diagram-shell — never bare <pre class="mermaid">
- diagram:issue meta tag must match filename issue number
```

The sub-agent has access to Read, Write, Edit, Bash, Glob, Grep tools — it can read all reference files and write all output files independently.

---

## Phase 1 — Context

1. **Extract issue number** from ARGS (e.g. `#477`, `477`, "issue 477"). Not found → DP(B): "Which issue number is this epic for?"

2. **Detect project** from ARGS or cwd.

3. **Run the brand book loader** (`${CLAUDE_PLUGIN_ROOT}/references/brand-book-loader.md`): Discovery → Parse → Apply. Determine Track A or Track B. Report the result before continuing.

4. **Slug** from ARGS title or issue title (kebab-case). Filename: `{ISSUE}-{slug}.html`.
   Check: `ls ~/.roxabi/forge/{PROJ}/visuals/{ISSUE}-*.html 2>/dev/null`
   ∃ → offer to update or create a new version.

5. **Read issue context** if accessible:
   - Check `~/projects/{PROJ}/` for relevant CLAUDE.md, specs, or any `docs/` referencing `#{ISSUE}`
   - Check git log: `cd ~/projects/{PROJ} && git log --oneline --grep="#{ISSUE}" 2>/dev/null | head -10`

6. **Apply the Aesthetic Detection precedence algorithm** (see `${CLAUDE_PLUGIN_ROOT}/references/forge-ops.md` § Aesthetic Detection) to select the correct aesthetic file.

---

### Frame Trace

After inferring all signals, emit a one-line summary before proceeding to Phase 2. This is not a question — it is a statement the user can interrupt if the inference is wrong:

```
Frame: reader={signal1_reader}, action={signal1_action}, takeaway={signal2}, tone={signal3_summary}. Generating...
```

Example: `Frame: reader=contributor, action=scope review, takeaway=tool registry enables plugin discovery, tone=technical+formal. Generating...`

---

## Phase 2 — Epic Structure

Determine tabs based on issue scope. Standard epic layout:

| Tab ID | Label | Content |
|--------|-------|---------|
| `overview` | Overview | What + Why + Scope — hero section with issue title, problem statement, goal |
| `breakdown` | Breakdown | Sub-tasks / milestones as cards or table; status badges |
| `deps` | Dependencies | Mermaid dependency/flow diagram (issues blocked by / blocking) |
| `criteria` | Acceptance | Checklist-style acceptance criteria table |

Adjust tabs to what the issue actually contains — simpler epics may need only `overview` + `deps`.

**Choose meta values:**
- `diagram:category` → `spec` for a feature spec, `plan` for implementation plan, `analysis` for research
- `diagram:issue` → ISSUE number (no `#`)
- `diagram:color` → match project (amber=Lyra, gold=Roxabi, etc.)

---

## Phase 3 — Generate

**File paths:**
```
~/.roxabi/forge/{PROJ}/visuals/{ISSUE}-{slug}.html
~/.roxabi/forge/{PROJ}/visuals/css/{ISSUE}-{slug}.css
~/.roxabi/forge/{PROJ}/visuals/js/{ISSUE}-{slug}.js
~/.roxabi/forge/{PROJ}/visuals/tabs/{ISSUE}-{slug}/tab-{ID}.html
```

Read `shells/split.html` → substitute placeholders. The shell contains all structure.

**Shell HTML** — include `diagram:issue` meta:
```html
<!-- diagram-meta:start -->
<meta name="diagram:title"     content="{PROJ} #{ISSUE} — {Title}">
<meta name="diagram:date"      content="{YYYY-MM-DD}">
<meta name="diagram:category"  content="{category}">
<meta name="diagram:cat-label" content="{Label}">
<meta name="diagram:color"     content="{color}">
<meta name="diagram:badges"    content="latest">
<meta name="diagram:issue"     content="{ISSUE}">
<!-- diagram-meta:end -->
```

**Overview tab** — hero section with context:
```html
<div class="epic-hero">
  <div class="epic-number">#{ISSUE}</div>
  <h1>{Title}</h1>
  <p class="epic-goal">{one-sentence goal}</p>
</div>
<div class="cards">
  <div class="card accent"><div class="card-label">Scope</div><div class="card-body">…</div></div>
  <div class="card accent"><div class="card-label">Status</div><div class="card-body">…</div></div>
  <div class="card accent"><div class="card-label">Blocked by</div><div class="card-body">…</div></div>
</div>
```

CSS for epic-hero (add to `{EXTRA_STYLES}`):
```css
.epic-hero { margin-bottom: 2rem; }
.epic-number { font-family: 'IBM Plex Mono', monospace; font-size: 0.875rem; color: var(--accent); font-weight: 600; margin-bottom: 0.5rem; }
.epic-goal { font-size: 1.125rem; color: var(--text-muted); margin-top: 0.5rem; }
```

**Breakdown tab** — use `.cards` grid or a `.table-wrap > table` with status column:
```html
<span class="status done">done</span>
<span class="status wip">in progress</span>
<span class="status todo">todo</span>
```
```css
.status { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 3px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.status.done { background: var(--success-dim); color: var(--success); }
.status.wip  { background: var(--warning-dim); color: var(--warning); }
.status.todo { background: var(--info-dim); color: var(--info); }
```

**Deps tab** — Mermaid dependency diagram. Follow `${CLAUDE_PLUGIN_ROOT}/references/mermaid-guide.md` checklist exactly (dynamic tab pitfalls).

**Acceptance criteria tab** — table: | Criterion | Type | Status |

Dark mode text rules always apply — use semantic tokens from `base/components.css`.

---

## Phase 4 — Report

```
Created:
  ~/.roxabi/forge/{PROJ}/visuals/{ISSUE}-{slug}.html
  ~/.roxabi/forge/{PROJ}/visuals/css/{ISSUE}-{slug}.css
  ~/.roxabi/forge/{PROJ}/visuals/js/{ISSUE}-{slug}.js
  ~/.roxabi/forge/{PROJ}/visuals/tabs/{ISSUE}-{slug}/tab-*.html

View:    make forge → http://localhost:8080/{PROJ}/visuals/{ISSUE}-{slug}.html
         (or: cd ~/.roxabi/forge && python3 -m http.server 8080)
Deploy:  make forge deploy
```

$ARGUMENTS
