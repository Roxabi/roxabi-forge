# Epic #40 + #58 — `forge-diagram` JS Engine — Execution Recap & Handoff

> **Single entry point.** A fresh Claude Code session reads THIS first, then executes §5. Everything
> needed is linked below; nothing depends on prior conversation. Repo root:
> `/home/mickael/projects/roxabi-forge`. Date prepared: 2026-06-03.

---

## 0. TL;DR

- **What:** build **`forge-diagram`** — a **JS runtime, lyra-stack-grade** diagram engine. Output =
  single self-contained `file://`-safe HTML (HTML/CSS card nodes + DOM-measured pixel-space SVG edges
  + opt-in rAF particles). Quality bar = `forge.roxabi.dev/lyra-stack`.
- **How:** an **autonomous per-wave dev harness** (`epic-40-58-wave.mjs`) fans out subagents per slice
  (plan → impl → 6-lens review → 2-skeptic validate → fix → defer), opens PRs, **does not merge**. The
  orchestrator (you) watches CI, reads the rendered PNG, applies `reviewed` → `auto-merge.yml` squashes.
- **State:** spec + harness **committed to `staging`** (`0e223ab`). 8 slices created as issues **#60–#67**.
  Nothing built yet. **Ready to run W1 (`args:[60]`).**
- **Autonomy:** **0 human gate** — the orchestrator applies `reviewed` itself after reading the PNG.

---

## 1. Decision history (why this shape — so a fresh session doesn't relitigate)

1. Epic #40 was originally a **Python port** of `beautiful-mermaid` (igraph + Pillow, compile-time
   static SVG). **Dropped.**
2. **Pivot to JS.** The quality bar `lyra-stack` (`/home/mickael/.roxabi/forge/lyra-stack-v2.html`,
   977 lines / 581 JS) gets its beauty from **runtime JS**: edges measured in real pixel space
   (`getBoundingClientRect` + `ResizeObserver`, no stretched grid), HTML/CSS rich cards, rAF particles.
   Python/igraph static SVG cannot reach that (BM itself uses **elkjs**, not igraph; a port = 5500-LOC
   fork). `bun` is already first-class in forge → JS is no new runtime.
3. **#58** ("opt-in JS edge engine — lyra-grade arrows + particle flow") **folded into #40** as the
   core. **#57/#59** (uniform-aspect) merged separately — context only, not part of this build.
4. **Guard collision resolved.** Forge purged Mermaid (#21) with two guards (lefthook + CI) scoping
   `plugins/forge/`. Resolution: package = **`forge-diagram`**; the **LLM emits a descriptor JSON**
   (no Mermaid-syntax parser → the lowercase `mermaid` token is avoidable everywhere); capital
   `Mermaid` is guard-exempt. See §7.
5. **3 open questions resolved** (OQ-1 hybrid elk, OQ-2 particles, OQ-3 cards) — see §9.

---

## 2. Document map — every file a fresh session needs

| File | Purpose | Status |
|---|---|---|
| **`artifacts/plans/epic-40-58-RECAP.md`** | THIS — handoff entry point | committed |
| **`artifacts/specs/epic-40-58-js-engine-spec.md`** | **SSoT** — architecture, layers, type matrix, reuse table, AC-1..10, slices, descriptor JSON schema, runbook §6 | committed |
| **`artifacts/plans/epic-40-58-wave.mjs`** | autonomous per-wave dev harness (Workflow script) | committed |
| `/home/mickael/.roxabi/forge/lyra-stack-v2.html` | reference impl — the technique to lift (edges, particles, cards) | on disk (not in repo) |
| `/home/mickael/projects/external_repos/beautiful-mermaid/` | elkjs source + layout options to adapt (S2) | clone on disk |
| `.claude/fc-loop/render.mjs` | Playwright PNG render harness (visual QA) | in repo |
| `artifacts/frames/epic-40/<issue>/` | per-wave PNG review surface (orchestrator reads these) | created |
| `artifacts/plans/epic-40-wave{,-plan}.*` | **SUPERSEDED** Python plan/harness — do NOT run | committed (banner) |

---

## 3. Issue structure (live on GitHub)

Epic **#40** `feat(forge-diagram): JS runtime diagram engine (lyra-stack-grade, merges #58)` — OPEN.
Python sub-issues #41–#48 + sibling #58 = **CLOSED** (superseded/folded).

| Slice | Issue | Owns (disjoint footprint) | Size | Blocked-by |
|---|---|---|---|---|
| S1 | **#60** | `fd/{core,edges,cards,bundler}.js` · `fd/types/architecture.js` · `fd-engine.css` | F-full | — |
| S2 | **#61** | `fd/types/{flowchart,state}.js` · `scripts/fd-layout.mjs` (bun gen-time elk) | F-full | #60 |
| S5 | **#62** | `fd/types/xychart.js` | F-lite | #60 |
| S6 | **#63** | `fd/types/{gantt,pie}.js` | F-lite | #60 |
| S7 | **#64** | `fd/particles.js` · `fd/interactions.js` | F-lite | #60 |
| S3 | **#65** | `fd/types/{class,er}.js` | F-lite | #61 |
| S4 | **#66** | `fd/types/sequence.js` | F-lite | #61 |
| S8 | **#67** | forge-chart `SKILL.md` routing · DELETE `graph-templates/{sequence,state,er,gantt,pie}.html` | F-lite | #60–#66 |

`fd/` = `plugins/forge/references/graph-templates/fd/` (all guard-scoped). `scripts/fd-layout.mjs` is
the only file outside `plugins/forge/`.

**DAG / waves:**
```
W1 = [60]            S1 core — blocks everything
W2 = [61,62,63,64]   S2,S5,S6,S7  (need only S1; disjoint footprints) — parallel
W3 = [65,66]         S3,S4        (need S2/elkjs; disjoint) — parallel
W4 = [67]            S8 routing+cleanup (needs all) — guard-sensitive, last
```

---

## 4. Architecture (one screen — full detail in the spec)

```
forge-chart skill (LLM) writes a descriptor JSON   ← NO Mermaid syntax, NO parser
   │  (auto-layout types) → bun scripts/fd-layout.mjs imports elk.bundled.js,
   │                        computes node x/y, injects into the descriptor   [GEN-TIME]
   ▼
single .html: <script type="application/json" id="fd-data">{descriptor}</script>
              + inline fd-engine (core+edges+cards+particles+types/*, glob-bundled) + fd-engine.css
   ▼  [RUNTIME, browser]
renderNodes (HTML/CSS cards) → getBoundingClientRect(all nodes) → bezier edge paths on SVG overlay
   → ResizeObserver redraws edges on resize → opt-in rAF particles
```
- **elk = gen-time only** (bun tool); NOT inlined → every output ~80 KB regardless of type.
- **Edges = runtime, pixel-space** (overlay `position:absolute;inset:0`, NO `preserveAspectRatio="none"`).
- Engine source is **modular** (`fd/core.js` + `fd/types/*.js`), bundled via filename-glob discovery
  (no shared registry edit) → slices stay disjoint → parallel-safe.

---

## 5. ▶ COLD-SESSION RUNBOOK (the thing to execute)

**Preconditions:** `cwd=/home/mickael/projects/roxabi-forge` · `gh auth status` OK · `git fetch origin` ·
set the turn token budget to **`+3M`** (the harness has no internal budget guard).

**Loop — one wave at a time, do NOT start the next until all current PRs are MERGED:**

```
∀ wave W in [ [60], [61,62,63,64], [65,66], [67] ]:
  1. git checkout staging && git merge --ff-only origin/staging
  2. Workflow({ scriptPath: "artifacts/plans/epic-40-58-wave.mjs", args: W })   → { results[], failed[] }
  3. ∀ result r with status 'pr-opened':
       a. gh pr checks <PR> --watch                          # required check 'ci' must go green
       b. Read artifacts/frames/epic-40/<r.issue>/*.png       # YOU are the visual reviewer (no human)
       c. ci green ∧ PNG acceptable (lyra-grade edges, no clipping/overlap/giant arrows):
            gh pr edit <PR> --add-label reviewed              # → auto-merge.yml squashes + closes issue
          else:
            re-invoke step 2 for [r.issue] alone (one more cycle), or leave blocked + skip dependents
  4. poll until every wave PR is MERGED:  gh pr view <PR> --json state -q .state   (expect "MERGED")
  5. ∀ issue in failed[]: skip its dependents in later waves; note for manual follow-up
```

**Dependency-skip rule:** `#60 fail → ABORT (everything depends on it)` · `#61 fail → skip #65,#66 and
block #67` · `any of #61/#62/#63/#64/#65/#66 fail → #67 blocked (needs all)`.

**First command (after setting budget +3M):**
```
Workflow({ scriptPath: "artifacts/plans/epic-40-58-wave.mjs", args: [60] })
```
**Recommended:** stop after **W1** and eyeball S1's PNG (the core = the visual foundation) before W2–W4.

**Closeout (after W4 merged):** epic #40 auto-closes (each PR has `Closes #N`); verify
`gh issue view 40 --json state`. Optional: post-merge audit (1 frontend-dev reads `staging`, confirms
all types render via forge-chart) + a remediation recap under `artifacts/audits/`.

---

## 6. Autonomy & merge model

- **0 human gate.** The orchestrator (the running session) applies `reviewed` itself.
- Forge merge mechanics (verified): `staging` is protected (strict=true, required check `ci`, no
  required reviews). The `reviewed` label triggers **`auto-merge.yml`** → `gh pr merge --auto --squash`
  + `update-behind-prs` (no manual rebase watcher needed) + closes the linked issue (PR body must
  contain `Closes #N` — the harness enforces this).
- The harness **never merges**; it only opens PRs + runs the in-flight 6-lens review/validate/fix loop.

---

## 7. Key facts & gotchas a fresh session MUST know

- **Guard:** `mermaid-guard` = lefthook (glob `plugins/forge/**/*`) + CI (`grep -rn '\bmermaid\b'
  plugins/forge/`). All `fd/*` are under `plugins/forge/` → **every slice must keep
  `grep -rn '\bmermaid\b' plugins/forge/` empty**. Capital `Mermaid` is exempt (docstrings OK).
- **Render (visual lens):** `PLAYWRIGHT_BROWSERS_PATH=/home/mickael/.cache/ms-playwright node
  /home/mickael/projects/roxabi-forge/.claude/fc-loop/render.mjs <in.html> <out.png> 1280 dark`.
  **`render.mjs` does NOT create the output dir** → always `mkdir -p artifacts/frames/epic-40/<n>` first.
- **Pixels ≠ data:** for xychart (#62) and gantt/pie (#63) there is a **math lens** — recompute every
  coord from raw data + the renderer's own formula and diff vs output (a chart can look right yet
  encode wrong numbers; cf. PR #55). Distinct from the visual pass.
- **Mental gates ≠ pixels:** always Read the PNG; visual/math reviewers over-flag/hallucinate, so every
  finding passes a 2-skeptic refute-by-default validate before fix.
- **Particles OFF by default** (AC-9) — render with particles off so Playwright captures aren't blurred.
- **Worktree base hygiene:** every isolated agent does `git checkout -B <branch> origin/staging` (pin to
  remote, never branch off a stale local).
- **Absolute paths** (not in the forge repo): BM = `/home/mickael/projects/external_repos/beautiful-mermaid`;
  lyra ref = `/home/mickael/.roxabi/forge/lyra-stack-v2.html`.
- **Triage CLI** (defer step) resolves its version at runtime; run from the forge repo CWD, never `cd`
  into the plugin-cache; forge board has no Size field (omit `--size`).
- **Resilience:** `tryAgent` retries 3× w/ backoff (529 storms); `ISOLATE-DEFER-CONTINUE` (a failed
  slice never stalls the wave).

---

## 8. Validation status (3 agents, pre-handoff)

- **Harness logic:** SOUND — no blocking bugs; all control-flow paths terminate (validated against the
  factory original `epic-1662-wave.mjs`).
- **Forge facts:** verified — guard globs, `ci.yml`, `auto-merge.yml`, branch protection, `reviewed`
  label, greenfield package path, DAG vs issue bodies — all confirmed.
- **Cold-session self-sufficiency:** the 3 blocking gaps found (frames mkdir, abs BM path, triage
  version) are **fixed** in the JS harness.
- **Known caveats:** (a) CI does **not** run JS unit tests today — slices should add tests; in-agent
  gates + the review panel enforce correctness pre-PR. (b) `bun lint` scopes 7 files (artifacts/ &
  `fd/` linting depends on `biome.json` includes — confirm during S1). (c) elk gen-time means the
  forge-chart skill must invoke `scripts/fd-layout.mjs` — wired in S2/S8.

---

## 9. Resolved decisions

- **OQ-1 (elk) → HYBRID:** elkjs runs **gen-time via bun** (`scripts/fd-layout.mjs`), injects node x/y
  into the descriptor; elk is NOT inlined (no 1.6 MB/file). Edges stay DOM-measured at runtime
  (resize re-measures edges; node positions are static). Rationale: Cloudflare bandwidth; bun in stack.
- **OQ-2 (particles) → opt-in**, one-shot on hover/trigger; loop via `options.particles:"loop"`. Off by default.
- **OQ-3 (cards) → by type:** premium card for architecture/hub-spoke; simple box for
  flowchart/state/class/ER; per-node override `nodes[i].cardStyle`.
- **Modular-source constraint:** `fd/` = core + per-type modules, glob-bundled at gen-time → slices
  disjoint, parallel-safe, no shared registry edits.

---

## 10. What to expect on first run (W1 = S1, #60)

S1 is F-full → the harness PLANs it into disjoint file-groups (`core.js`, `edges.js`, `cards.js`,
`bundler.js`, `types/architecture.js`, `fd-engine.css`), builds them in parallel worktrees, integrates
to one PR, runs the 5-lens panel (correctness/security/tests/rules/**visual**), and opens the PR. You
then `/ci-watch`, read `artifacts/frames/epic-40/60/architecture.png` (the lyra-grade core proof), and
on green apply `reviewed`. **Stop and review S1 before launching W2.**
