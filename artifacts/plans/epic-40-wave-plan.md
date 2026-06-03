# Epic #40 — Autonomous Wave Dev Plan (`forge-diagram`)

> ⚠️ **SUPERSEDED (2026-06-03).** This plan targeted a **Python** static-SVG engine. Direction
> changed to a **JS runtime lyra-stack-grade** engine (#40 + #58 merged). Use
> `artifacts/specs/epic-40-58-js-engine-spec.md` and the JS harness `epic-40-58-wave.mjs` instead.
> Kept for traceability only — do not execute.

> Port of the `roxabi-factory` `epic-1662-wave.mjs` harness to drive **epic #40**
> (`feat: forge-mermaid → forge-diagram` — Python diagram engine) to merged PRs on
> `staging`, autonomously, with a **visual review gate** (PNG via Playwright).
>
> **Status:** prepared for validation — nothing has run. Pairs with `epic-40-wave.mjs`.
> **Date:** 2026-06-02 · **Repo:** `Roxabi/roxabi-forge` · **Target:** `staging`

---

## 0. Decision actée — the guard collision

Epic #40 was authored as **`forge-mermaid`**, which collides with forge's deliberate
zero-Mermaid policy (#21), enforced by two guards:

| Guard | Source | Scope |
|---|---|---|
| lefthook `mermaid-guard` (pre-commit) | `lefthook.yml` | glob `plugins/forge/**/*` |
| CI `Mermaid guard` (required check `ci`) | `ci.yml` | `grep -rn '\bmermaid\b' plugins/forge/` |

**Resolution (Option 1 — chosen):** rename package → **`forge-diagram`** (`forge_diagram`),
neutral public API. Two facts make this clean:

1. **Both guards scope `plugins/forge/` only.** The package lives at
   `packages/forge-diagram/` — **outside** both. Package-internal code is guard-free.
2. **The guard matches `\bmermaid\b` lowercase only.** Capitalized **`Mermaid`** is exempt
   → docstrings/prose may say "Mermaid-compatible syntax" freely.

### Guard-safety contract (injected into every impl agent)

- Code identifiers: `forge_diagram`, `forge-diagram` — **never** `mermaid`/`forge_mermaid`.
- The word `mermaid` (lowercase) may appear **only** inside `packages/forge-diagram/`
  (guard-free) and only where naming the input language is unavoidable; prefer the
  capitalized `Mermaid` (guard-exempt) in docstrings.
- **Zero** lowercase `mermaid` in any file under `plugins/forge/` (P6). Use
  "diagram syntax" / "Mermaid-compatible". `.mmd` extension is fine (no `mermaid` substring).
- Post-edit self-check in every agent touching `plugins/forge/`:
  `grep -rn '\bmermaid\b' plugins/forge/` **must be empty** before PR.

---

## 0.5 Why Python — and when the engine runs

The engine runs at **artifact-generation time** (locally, on the dev box, when the `forge-chart`
skill produces an HTML artifact) — **never on Cloudflare**.

```
forge-chart skill → scripts/render-diagram.py → SVG string
                  → substituted into plugins/forge/references/shells/single.html
                  → self-contained static HTML (zero JS runtime, zero CDN, file://-safe)
                  → deployed to Cloudflare Pages (serves static HTML only)
```

- **Root cause it fixes:** today the LLM computes node coordinates + arrow paths (it does geometry
  poorly → the 7 R1–R7 rules + recurring layout bugs). The engine moves geometry **out of the LLM**
  into a deterministic layout pass (igraph Sugiyama + Pillow text metrics).
- **Why Python (not the TS original):** forge's entire `scripts/` layer is already Python
  (`gen-deps.py`, `render-md.py`, `gen-fgraph.py`; uv + hatchling). `igraph` (Sugiyama layout) and
  `Pillow` (text metrics) are Python libs. One generation runtime, consistent with `scripts/`.
- **Cloudflare never executes Python** — it only serves the pre-rendered static HTML. This is a
  compile-time step on the dev machine, not a Cloudflare build step. (`bun` is used only for
  lint/CI and for cross-validating against the `beautiful-mermaid` reference clone.)

## 1. Scope — the DAG

8 sub-issues, critical path **P1→P3→P4→P6→P7**:

```
#41 P1 foundation (scaffold + theme + svg + text_metrics)        [no deps]
 ├─> #42 P2  sequence ─────────────┐
 ├─> #43 P3  flowchart+state ──────┼─> #46 P4 ER+class ─┐
 ├─> #44 P5  xychart ──────────────┤                    │
 └─> #45 P5.5 gantt+pie ───────────┤                    ├─> #47 P6 integration ─> #48 P7 polish
                                   └────────────────────┘
```

### Waves (execution units = leaves, merge between waves)

| Wave | Issues | Strategy | Rationale |
|---|---|---|---|
| **W1** | #41 (P1) | solo | foundation — everything depends on it; merge before W2 |
| **W2** | #42 #43 #44 #45 | parallel (CAP=3) | all blocked-by #41 only; disjoint footprints (per-type subdirs) |
| **W3** | #46 (P4) | solo | blocked-by #43 (reuses igraph + shapes infra from P3) |
| **W4** | #47 (P6) | solo | blocked-by W2+W3; **touches `plugins/forge/`** → guard-sensitive |
| **W5** | #48 (P7) | solo | blocked-by #47 |

CAP=3 caps concurrent leaves; only W2 has >1. Critical path dominates wall-clock.

---

## 2. Deliberate deviation from the epic's phase→file mapping

The epic body assigns the deletion of `plugins/forge/references/graph-templates/{sequence,state,er,gantt,pie}.html`
to the **package phases** (P2/P3/P4/P5.5). We **defer all `plugins/forge/` changes to P6**:

- **Package phases P1–P5.5 are additive, `packages/forge-diagram/` only.** No guarded-path churn,
  no risk of breaking `forge-chart` mid-epic, footprints trivially disjoint.
- **P6 makes every `plugins/forge/` change atomically**: routing in the skill, shell wrap,
  *and* the 5 template deletions, in one PR. `forge-chart` stays working until P6 flips it.

This is the single intentional schedule change vs the epic text — recorded here so the
post-merge audit doesn't flag it as drift.

---

## 3. Per-issue size + footprint (forge-diagram paths)

| # | Phase | Size | Footprint (disjoint set) |
|---|---|---|---|
| 41 | P1 foundation | F-lite | `packages/forge-diagram/{pyproject.toml,README.md}`, `src/forge_diagram/{__init__,types,theme,svg,text_metrics}.py`, `assets/fonts/Inter-Regular.ttf`, `tests/` scaffold, **+ CI test job** in `.github/workflows/ci.yml` |
| 42 | P2 sequence | F-lite | `src/forge_diagram/{parsers,layout,renderers}/sequence.py`, types additions, `examples/sequence.{mmd,svg}`, `tests/test_sequence.py` |
| 43 | P3 flowchart+state | **F-full** | `src/forge_diagram/parsers/{flowchart,state}.py`, `layout/{graph,edge_routing}.py`, `renderers/{shapes,flowchart,state}.py`, examples, tests |
| 44 | P5 xychart | F-lite | `src/forge_diagram/{parsers,layout,renderers}/xychart.py`, cubic-spline util, examples, tests |
| 45 | P5.5 gantt+pie | F-lite | `src/forge_diagram/{parsers,layout,renderers}/{gantt,pie}.py`, examples, tests |
| 46 | P4 ER+class | F-lite | `src/forge_diagram/{parsers,renderers}/{er,class}.py` (reuses `layout/graph.py`), examples, tests |
| 47 | P6 integration | **F-full** | `scripts/render-diagram.py`, `plugins/forge/skills/forge-chart/SKILL.md` (routing), `plugins/forge/references/shells/single.html` wrap, **DELETE** `graph-templates/{sequence,state,er,gantt,pie}.html`, aesthetic mapping — **guard-sensitive** |
| 48 | P7 polish | F-lite | themes finalize, anti-pattern asserts, **24 syrupy snapshots** (8 types × 3 themes), `packages/forge-diagram/README.md`, examples completion |

`F-full/F-lite` → harness runs PLAN (decompose into disjoint file-groups) → parallel SUB-IMPL → INTEGRATE.
`S` → single impl agent. (No phase is `S` here.)

---

## 4. Per-leaf pipeline (the inner loop — ported verbatim from factory)

```
size-adaptive impl:
  F-lite/F-full : PLAN (disjoint file-groups) → SUB-IMPL ×N parallel (worktree each)
                  → INTEGRATE (merge disjoint branches → full gates → PR w/ decision trace)
  ∀ size        : [ REVIEW (lens panel) → VALIDATE (2 skeptics/finding, refute-by-default)
                    → FIX (fixer) ] × ≤2 rounds → DEFER residual as sibling (blocked-by N)
```

Workflow **does NOT merge.** Merge is the orchestrator's main loop (§7).

### RCA contract (injected verbatim into every impl/fix agent + PR body)

Derive root cause (¬fix on symptom) · enumerate corrections, classify each **Patch ⊻ Archi**
(choose explicitly) · fix at the level of the cause · evaluate `trust(input)` ·
require `tested ∧ correct` (green ≠ correct) · **trace the decision in the PR body**.

---

## 5. Gates (forge reality — replaces factory's pytest/pyright/importlinter/snapshot)

Forge root has **no** `pyproject.toml`/`pytest`/`pyright`/`importlinter`. The package brings its own.

### Package-local gates (run in-agent before every PR)

```bash
cd packages/forge-diagram
uv run ruff format . && uv run ruff check --fix .
uv run pytest            # + syrupy snapshots from P7
```

### Repo gates (what the required `ci` check enforces — `ci.yml`)

```bash
bun lint                              # biome (JS only)
python3 -m py_compile scripts/*.py    # if scripts/ touched (P6: render-diagram.py)
grep -rn '\bmermaid\b' plugins/forge/ # MUST be empty (guard) — P6 critical
```

### CI test-coverage gap → fixed in P1

`ci.yml` currently does **not** run the package's pytest → merged package code is unprotected.
**P1 adds a CI step** (`uv run --project packages/forge-diagram pytest` + `ruff check`) so W2…W5
land under test enforcement. Until that step merges, package correctness rests on the in-agent
gates + the review panel.

---

## 6. Review lenses (drop `axial`, add `visual` + `math`)

Forge has **no `axial: true` ADR** → the factory `axial` lens is dropped. Two visual lenses added,
applied per phase (a foundation phase has no diagram to look at):

| Lens | Agent | Applies to | Focus |
|---|---|---|---|
| `correctness` | `dev-core:backend-dev` | all | logic bugs, parser edge cases, behavioural drift |
| `security` | `dev-core:security-auditor` | all | untrusted `.mmd` input: ReDoS, path traversal (font load), unbounded recursion |
| `tests` | `dev-core:tester` | all | do snapshots prove behaviour? acceptance coverage? determinism (no random IDs/timestamps) |
| `rules` | `dev-core:backend-dev` | all | RCA: fix@root-cause-level; honest Patch⊻Archi; guard-safety contract respected |
| `visual` | `dev-core:frontend-dev` | 42,43,44,45,46,47,48 | render example → PNG → eyeball: clipping, overlap, **giant arrowheads** (see memory), illegible text, off-canvas, detached edges |
| `math` | `dev-core:frontend-dev` | 44,45,48 | **pixels ≠ data**: recompute coords from raw data + the renderer's own formula, diff vs SVG (caught a 9/9 bubble-coord bug on PR #55) |

### Visual lens mechanism (reuses `.claude/fc-loop/render.mjs`)

```bash
# wrap the phase's example SVG into a minimal dark HTML, then:
PLAYWRIGHT_BROWSERS_PATH=/home/mickael/.cache/ms-playwright \
  node /home/mickael/projects/roxabi-forge/.claude/fc-loop/render.mjs \
  <example.html> artifacts/frames/epic-40/<n>/<type>.png 1280 dark
# Read the PNG, verdict against rubric. When BM has an equivalent, render its SVG too
# (cd external_repos/beautiful-mermaid && bun run …) for side-by-side.
```

PNGs are saved to **`artifacts/frames/epic-40/<issue>/`** — these are the orchestrator's
review surface at each wave boundary (§7).

Visual/math findings flow through the **same VALIDATE (2-skeptic) → FIX** loop as code findings —
important because the QA memory notes agents **over-flag and hallucinate** visual defects.

---

## 7. Autonomy + merge (orchestrator main loop, between waves)

**Zero human gate.** The orchestrator (the Claude session running this plan) applies the `reviewed`
label itself — there is no human approval anywhere in the loop. The visual review is done by the
orchestrator reading the PNGs (it *is* the reviewer), not by a person.

```
per wave:
  Workflow({ scriptPath: epic-40-wave.mjs, args: [<wave issues>] })   → opens PRs (no merge)
  ∀ PR (status 'pr-opened'):
     /ci-watch until check 'ci' green
     Read artifacts/frames/epic-40/<n>/*.png   ← orchestrator IS the visual reviewer (no human)
     CI green ∧ PNGs acceptable ∧ in-run lens panel passed (residual handled/deferred)
        → gh pr edit <PR> --add-label reviewed
          → auto-merge.yml: gh pr merge --auto --squash + auto-update-behind-PRs + close issue
     else → leave unlabeled, record blocked; skip its dependents
  wait all wave PRs MERGED → invoke next wave (dependents branch from updated staging)
```

**The orchestrator's PNG read replaces the human, it does not add one.** The pipeline is
autonomous to PR; the orchestrator then reads the rendered diagrams (not the diff), and on
CI-green + acceptable pixels applies `reviewed` → auto-merge. Memory rule: *mental gates ≠ pixels;
always read the PNG.* A bad render → re-enter FIX (re-invoke the wave for that single issue) or defer.
The exact command sequence is in **§12 (orchestrator runbook)** — written so a cold session can
execute the whole epic with no prior context.

Forge merge mechanics are **simpler than factory**: the `reviewed` label alone triggers
`auto-merge.yml`, which also runs `update-behind-prs` on every push — no manual `update-branch`
watcher needed (factory blocker #4 is a non-issue here).

### Failure policy — ISOLATE-DEFER-CONTINUE

Any thrown error / `status:'failed'` is caught, logged, recorded in `failed[]`; the wave continues.
The orchestrator skips a failed leaf's dependents in later waves. Residual review findings after
2 fix rounds → deferred as a **sibling** issue (shared parent, blocked-by N) — not a child.

---

## 8. Resilience (carried from factory retro)

| Risk (factory blocker) | Mitigation in harness |
|---|---|
| API 529 storm wipes run #1 (#1) | `tryAgent()` — 3 tries, 20s×attempt backoff, **from line 1** |
| Heavy agent ends in prose, no StructuredOutput (#2) | `diff` optional + out-of-band `diffPrompt` fetch; decompose F-full via PLAN |
| Worktree agent branches off **stale** local staging (#10) | every isolated agent does `git checkout -B <branch> origin/staging` (pin to remote) |
| Shared-file merge conflicts (#5) | footprint-disjoint PLAN; package phases additive; P6 alone owns `plugins/forge/` |
| Strict-base behind-deadlock (#4) | **N/A** — `auto-merge.yml` `update-behind-prs` handles it natively |
| YAML colon kills `ci` silently (#6) | P1/P6 touch `ci.yml` → agent validates `yaml.safe_load` + `ci` job present, quotes colons |

---

## 9. Cost (order-of-magnitude, from factory calibration)

Factory: 19 leaves, ~+4.6k/−1.5k LOC, ~30 agents, ~1.5–2.5M tokens, 4.5h wall-clock.
Epic #40: 8 leaves but **~5500 LOC** + visual passes + F-full decomposition on P3/P6.

| Metric | Estimate | Confidence |
|---|---|---|
| Agent invocations | ~40–60 (8 leaves × [plan + N sub-impl + diff + 4–6 lenses × ≤2 rounds + validate + fix]) | medium |
| Tokens | **~2–3.5M** | low (factory only instrumented 2 agents) |
| Wall-clock | 5 waves, critical path serial → **~6–9 h** | low |

Recommend setting a token budget directive (e.g. `+3M`) at run time; the harness has no
internal budget guard (it relies on the wave/CAP structure + the 1000-agent backstop).

---

## 10. Validation checklist — RESOLVED (2026-06-02)

- [x] Package name **`forge-diagram`** (`forge_diagram` import path). — confirmed
- [x] **Deviation §2** (defer all `plugins/forge/` changes to P6). — approved
- [x] **P1 adds the CI pytest job** for `packages/forge-diagram`. — approved
- [x] Autonomy: **0 human gate** — the orchestrator applies `reviewed` itself after reading PNGs +
      CI green. No per-PR human sign-off. — confirmed
- [x] `/recheck #40` — **skipped** by decision (epic accepted as-is).
- [ ] **Set a token budget at run time** (recommend `+3M`) — the harness has no internal budget guard.
- [ ] Default flow is **direct-to-`reviewed`** (not draft). Change only if a dry-run is wanted.

---

## 11. Files

- Harness: `artifacts/plans/epic-40-wave.mjs`
- This plan: `artifacts/plans/epic-40-wave-plan.md`
- Visual harness (reused): `.claude/fc-loop/render.mjs` (Playwright; browsers cached at
  `/home/mickael/.cache/ms-playwright`)
- BM reference clone: `/home/mickael/projects/external_repos/beautiful-mermaid/`
- Per-wave PNG review surface: `artifacts/frames/epic-40/<issue>/`

---

## 12. Orchestrator runbook (cold-session, copy-paste)

> This section makes the plan **self-carrying**: a fresh Claude session with no prior context can
> execute the entire epic from here. Run from repo root `/home/mickael/projects/roxabi-forge`.

**Preconditions**
- `cwd = /home/mickael/projects/roxabi-forge`, `gh auth status` OK, `git fetch origin` clean.
- Set the turn token budget to **`+3M`** (so the Workflow tool's `budget` reflects it).
- Waves (issue → wave): `W1=[41]` · `W2=[42,43,44,45]` · `W3=[46]` · `W4=[47]` · `W5=[48]`.

**Loop — for each wave `W` in order, do NOT start the next until all PRs of the current are MERGED:**

```
1. git fetch origin && git checkout staging && git merge --ff-only origin/staging
2. Workflow({ scriptPath: "artifacts/plans/epic-40-wave.mjs", args: W })
     → returns { wave, failed[], results[] }  (results[i].prUrl, .status, .residualCount)
3. ∀ result r with r.status === 'pr-opened':
     a. PR=<number from r.prUrl>
     b. gh pr checks $PR --watch        # wait for required check 'ci' to pass
     c. Read artifacts/frames/epic-40/<r.issue>/*.png   # orchestrator visual gate (no human)
     d. if ci==green AND pngs acceptable:
          gh pr edit $PR --add-label reviewed           # → auto-merge.yml does the rest
        else:
          re-invoke step 2 for [r.issue] alone (one FIX cycle), or leave blocked + skip dependents
4. Poll until every wave PR is MERGED:
     gh pr view $PR --json state -q .state   # expect "MERGED"
5. ∀ issue in failed[]: skip its dependents in later waves; note for manual follow-up.
```

**Dependency skip rule (if a leaf fails):** `#43 fail → skip #46`; `any of #42/#43/#44/#45/#46 fail
→ #47 cannot run (needs all)`; `#47 fail → skip #48`; `#41 fail → abort (everything depends on it)`.

**Closeout (after W5 merged):**
- Epic #40 auto-closes when all leaves merge (each PR has `Closes #N`); verify with
  `gh issue view 40 --json state`.
- Optional post-merge audit: spawn 1 `backend-dev` + 1 `frontend-dev` to read `staging` and confirm
  all 8 diagram types render via `scripts/render-diagram.py` + the shared shell (mirrors the factory
  §10 second-layer audit).
- Write a remediation-style recap to `artifacts/audits/2026-XX-epic-40/RECAP.md`.

**Re-running a single issue:** `Workflow({ scriptPath: "...epic-40-wave.mjs", args: [<issue>] })`
— the harness is idempotent per issue (`git checkout -B` resets stale branches).
