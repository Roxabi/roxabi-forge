// ⚠️ SUPERSEDED (2026-06-03) — targeted a Python engine. Direction changed to JS (lyra-grade,
//    #40+#58 merged). Use epic-40-58-wave.mjs + artifacts/specs/epic-40-58-js-engine-spec.md.
//    Kept for traceability only — do not run.
//
// Workflow: epic-40-wave — run ONE dependency-wave of epic #40 leaves, fully autonomous.
//
// Epic #40: forge-diagram — Python diagram engine (port of beautiful-mermaid), package at
// packages/forge-diagram/ (guard-safe: both mermaid-guards scope plugins/forge/ only).
//
// Per issue (size-adaptive):
//   S            : single impl agent → branch feat/N → gates → PR
//   F-lite/Ffull : PLAN (decompose into disjoint file-groups) → SUB-IMPL N× (parallel, sub-branches)
//                  → INTEGRATE (merge disjoint sub-branches → full gates → PR)
//   then ∀ size  : [REVIEW panel (lenses incl. visual+math) → VALIDATE (2 skeptics/finding)
//                   → FIX (fixer)] × ≤2 rounds → DEFER residual as sibling (parent=parent(N), blocked-by N)
// Does NOT merge. Orchestrator main loop: CI-green + PNG eyeball → +reviewed label →
// auto-merge.yml squashes & updates-behind & closes issue, then re-invoke this wf for the next wave.
//
// Invoke:  Workflow({ scriptPath: ".../epic-40-wave.mjs", args: [41] })            // W1
//          Workflow({ scriptPath: ".../epic-40-wave.mjs", args: [42,43,44,45] })   // W2  ... etc.

export const meta = {
  name: 'epic-40-wave',
  description: 'Autonomous per-wave dev of epic #40 (forge-diagram) leaves: size-adaptive decomposed impl + lens panel (correctness·security·tests·rules·visual·math) review/validate/fix loop + defer residual; merge handled by orchestrator',
  phases: [
    { title: 'Plan', detail: 'decompose F-lite/F-full into disjoint file-groups' },
    { title: 'Implement', detail: 'sub-impl per file-group → integrate → PR with decision trace' },
    { title: 'Review', detail: 'lens panel: correctness · security · tests · rules · visual (PNG) · math (coords)' },
    { title: 'Validate', detail: '2 skeptics/finding, refute-by-default' },
    { title: 'Fix', detail: 'apply confirmed findings; defer residual after 2 rounds' },
  ],
}

const REPO = 'Roxabi/roxabi-forge'
const BASE = 'staging'
const CAP = 3 // max issues in flight per batch (merge cadence; engine also caps total agents at min(16,cores-2))
const PKG = 'packages/forge-diagram'
const RENDER = '/home/mickael/projects/roxabi-forge/.claude/fc-loop/render.mjs'
const FRAMES = 'artifacts/frames/epic-40'
const TRIAGE = 'bun /home/mickael/.claude/plugins/cache/roxabi-marketplace/dev-core/0.5.0/skills/issue-triage/triage.ts'

const RULES = `RÈGLES (∀ P, verbatim) :
P:=problème · obs(P),Sym(P):=observable,symptômes · RC(P):=root cause(s)
Corr(P):={corrections} · Patch⊂Corr(local) · Archi⊂Corr(structurel) · Patch∩Archi=∅ · I:=input · trust(I):=confiance · C:=code · L:=niveau logique
1. RCA      : dériver RC(P). ¬fix sur obs/Sym. symptôme ≠ cause.
2. Corr     : énumérer; classer chaque ∈ Patch ⊻ Archi; CHOISIR explicitement (¬patch déguisé en archi).
3. fix@L    : appliquer F au niveau L = niveau(RC), ¬ au niveau où Sym apparaît.
4. trust(I) : ∀ I évaluer trust(I) AVANT usage; trust bas → valider/sanitize.
5. ✓        : tested(C) ∧ correct(C). vert ≠ correct. exiger les deux.
6. Doc(PR)  : tracer RC(P) + Corr choisie + classe(Patch|Archi) + niveau L.`

// Guard-safety contract (replaces factory's AXIAL mandate). Forge has the zero-Mermaid guards.
const GUARD = `GUARD-SAFETY (mermaid purge #21 — non négociable):
- Identifiants code: forge_diagram / forge-diagram. JAMAIS "mermaid"/"forge_mermaid".
- Le token "mermaid" minuscule n'est toléré QUE dans ${PKG}/ (hors scope des guards) et seulement
  si nommer la langue d'entrée est inévitable; préférer "Mermaid" (majuscule = exempt du guard) en docstrings.
- ZÉRO "mermaid" minuscule sous plugins/forge/. Dire "diagram syntax" / "Mermaid-compatible". ".mmd" est OK.
- Self-check avant PR si tu touches plugins/forge/: grep -rn '\\bmermaid\\b' plugins/forge/ DOIT être vide.`

// Gates — forge reality. Package-local pytest/ruff (forge root has none); repo guard greps.
const GATES = `GATES (tous verts avant PR):
- Package: cd ${PKG} && uv run ruff format . && uv run ruff check --fix . ; uv run pytest
- Repo:    bun lint ; si scripts/ touché → python3 -m py_compile scripts/*.py
- Guard:   si plugins/forge/ touché → grep -rn '\\bmermaid\\b' plugins/forge/ DOIT être vide
- Si tu modifies un .github/workflows/*.yml: valider python -c "import yaml; yaml.safe_load(open('<f>'))"
  ET confirmer que le job requis "ci" existe; QUOTER toute valeur name: contenant un ':' (un ':' non quoté
  invalide tout le workflow et fait disparaître silencieusement le check ci).
- Déterminisme (P7/snapshots): aucun ID random, aucun timestamp dans le SVG.`

// Visual render recipe — reuses the proven fc-loop Playwright harness.
const VISUAL = `RENDU VISUEL (réutilise le harness QA prouvé):
1. Pour chaque type de diagramme de cette phase, génère/charge ${PKG}/examples/<type>.svg.
2. Enveloppe le SVG dans un HTML minimal sombre: <!doctype html><html><body style="margin:0;background:#0b0b0c">{SVG}</body></html>
   → écris-le dans /tmp/fd-<type>.html
3. Rends en PNG: PLAYWRIGHT_BROWSERS_PATH=/home/mickael/.cache/ms-playwright \\
   node ${RENDER} /tmp/fd-<type>.html ${FRAMES}/<N>/<type>.png 1280 dark
4. Read le PNG et juge contre la grille: arrowheads géants, overlap, clipping, texte illisible,
   hors-canvas, arêtes détachées, frames trop pâles. (Mémoire: mental gate ≠ pixels — TOUJOURS lire le PNG.)
5. Quand beautiful-mermaid couvre le type, rends aussi sa sortie (cd external_repos/beautiful-mermaid && bun run …)
   pour un side-by-side. external_repos/beautiful-mermaid/examples/ contient bar/line/mixed-interactive.svg.`

const SIZE = {
  41: 'F-lite', 42: 'F-lite', 43: 'F-full', 44: 'F-lite',
  45: 'F-lite', 46: 'F-lite', 47: 'F-full', 48: 'F-lite',
}

// Footprints — package phases additive (packages/ only); P6 owns ALL plugins/forge/ changes.
const FOOTPRINT = {
  41: `${PKG}/{pyproject.toml,README.md} + src/forge_diagram/{__init__,types,theme,svg,text_metrics}.py + assets/fonts/Inter-Regular.ttf + tests/ scaffold + ADD a CI pytest+ruff job for ${PKG} to .github/workflows/ci.yml (quote any name: with a colon)`,
  42: `${PKG}/src/forge_diagram/{parsers,layout,renderers}/sequence.py + Sequence dataclasses in types.py + examples/sequence.{mmd,svg} + tests/test_sequence.py. Read external_repos/beautiful-mermaid/src/sequence/layout.ts IN FULL first (200+ LOC, many edge cases).`,
  43: `${PKG}/src/forge_diagram/parsers/{flowchart,state}.py + layout/{graph,edge_routing}.py (igraph Sugiyama + orthogonal routing) + renderers/{shapes,flowchart,state}.py + examples + tests. Reuse roxabi-live edge_path()/_resolve_cells() patterns.`,
  44: `${PKG}/src/forge_diagram/{parsers,layout,renderers}/xychart.py + manual natural-cubic-spline util (~50 LOC, no scipy) + examples/{bar,line,mixed}.{mmd,svg} + tests`,
  45: `${PKG}/src/forge_diagram/{parsers,layout,renderers}/{gantt,pie}.py + examples + tests. NB: do NOT delete plugins/forge graph-templates here — deferred to P6.`,
  46: `${PKG}/src/forge_diagram/{parsers,renderers}/{er,class}.py (reuse layout/graph.py from P3) + 6 UML arrow markers + examples + tests`,
  47: `scripts/render-diagram.py (returns SVG string only) + plugins/forge/skills/forge-chart/SKILL.md routing (Mermaid-compatible types → forge-diagram) + plugins/forge/references/shells/single.html wrap + DELETE graph-templates/{sequence,state,er,gantt,pie}.html + aesthetic→theme mapping. GUARD-SENSITIVE: zero lowercase mermaid under plugins/forge/.`,
  48: `${PKG}: finalize 8 themes + anti-pattern asserts (R1,R2,R4,R5,R7) + 24 syrupy snapshots (8 types × 3 themes, deterministic) + README.md + examples completion`,
}

const LENS = {
  correctness: { agent: 'dev-core:backend-dev', focus: 'logic bugs, parser edge cases, behavioural drift, off-by-one in layout math' },
  security: { agent: 'dev-core:security-auditor', focus: 'untrusted .mmd input: ReDoS in regex parsers, unbounded recursion/nesting, path traversal in font/asset loading, resource exhaustion' },
  tests: { agent: 'dev-core:tester', focus: 'do tests prove behaviour (not just pass)? acceptance coverage? determinism (no random IDs/timestamps in SVG)? snapshot stability' },
  rules: { agent: 'dev-core:backend-dev', focus: 'RULES compliance: fix@root-cause-level L; honest Patch⊻Archi; GUARD-safety contract respected (no lowercase mermaid under plugins/forge/)' },
  visual: { agent: 'dev-core:frontend-dev', focus: 'PNG eyeball: giant arrowheads, node/edge overlap, clipping, illegible/overflowing text, off-canvas content, detached edges, faint frames. ' + VISUAL },
  math: { agent: 'dev-core:frontend-dev', focus: 'pixels ≠ data: recompute every coordinate from raw data + the renderer\'s OWN stated formula and diff against the SVG (axes ticks, bar heights, pie arc angles, gantt bar x/width, spline control points). A chart can look plausible yet encode wrong numbers.' },
}
// Which lenses run per issue (a foundation phase has no diagram to look at).
function lensesFor(n) {
  const base = ['correctness', 'security', 'tests', 'rules']
  if (n === 41) return base
  if (n === 44 || n === 45 || n === 48) return [...base, 'visual', 'math']
  return [...base, 'visual']
}

let _raw = args
if (typeof _raw === 'string') { try { _raw = JSON.parse(_raw) } catch (e) { /* leave as string */ } }
const wave = Array.isArray(_raw)
  ? _raw.map(Number).filter((x) => Number.isFinite(x))
  : (_raw && Array.isArray(_raw.issues) ? _raw.issues.map(Number).filter((x) => Number.isFinite(x)) : [])
if (!wave.length) throw new Error(`args resolved empty. typeof args=${typeof args}; value=${JSON.stringify(args)?.slice(0, 200)}. Expected array of issue numbers, e.g. [41] or [42,43,44,45]`)

// ---------- schemas ----------
const PLAN_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['tasks'],
  properties: {
    cohesive: { type: 'boolean' },
    tasks: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['id', 'title', 'fileGroup', 'detail'],
        properties: {
          id: { type: 'string' }, title: { type: 'string' },
          fileGroup: { type: 'array', items: { type: 'string' } }, detail: { type: 'string' },
        },
      },
    },
  },
}
const SUBIMPL_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['taskId', 'branch', 'status'],
  properties: {
    taskId: { type: 'string' }, branch: { type: 'string' },
    status: { type: 'string', enum: ['pushed', 'failed'] },
    files: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' },
  },
}
const IMPL_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['issue', 'status', 'branch', 'prUrl', 'classification', 'rootCause'],
  properties: {
    issue: { type: 'number' }, status: { type: 'string', enum: ['pr-opened', 'failed', 'partial'] },
    branch: { type: 'string' }, prUrl: { type: 'string' },
    classification: { type: 'string', enum: ['Patch', 'Archi', 'Mixed'] },
    rootCause: { type: 'string' }, filesChanged: { type: 'array', items: { type: 'string' } },
    gates: { type: 'object', properties: { pytest: { type: 'boolean' }, ruff: { type: 'boolean' }, guard: { type: 'boolean' }, bunlint: { type: 'boolean' } } },
    diff: { type: 'string' }, notes: { type: 'string' },
  },
}
const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['lens', 'findings'],
  properties: {
    lens: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['id', 'severity', 'title', 'detail'],
        properties: {
          id: { type: 'string' }, severity: { type: 'string', enum: ['blocking', 'major', 'minor', 'nit'] },
          file: { type: 'string' }, line: { type: 'string' }, title: { type: 'string' },
          detail: { type: 'string' }, suggestion: { type: 'string' },
        },
      },
    },
  },
}
const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['real', 'reason'],
  properties: { real: { type: 'boolean' }, reason: { type: 'string' } },
}
const FIX_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['round', 'fixed', 'residual', 'diff'],
  properties: {
    round: { type: 'number' },
    fixed: { type: 'array', items: { type: 'string' } },
    residual: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['title', 'detail'], properties: { id: { type: 'string' }, title: { type: 'string' }, detail: { type: 'string' } } } },
    diff: { type: 'string' }, gatesPass: { type: 'boolean' },
  },
}
const DEFER_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['issueUrl'],
  properties: { issueUrl: { type: 'string' }, parent: { type: 'number' } },
}
const DIFF_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['diff'],
  properties: { diff: { type: 'string' } },
}

// ---------- prompts ----------
const planPrompt = (n) => `Decompose GitHub issue #${n} (${REPO}) into INDEPENDENT implementation tasks with DISJOINT file groups, so each can be implemented by a separate agent without merge conflicts.
Read: gh issue view ${n} --json title,body. Footprint hint: ${FOOTPRINT[n] || '(read the issue)'}.
Explore the repo (Read/Grep) enough to map files. Rules:
- Each task.fileGroup must be a set of files NO other task touches (strict disjointness — guarantees conflict-free integration).
- If the issue is cohesive (one tight unit, or a shared file that can't be split), return a SINGLE task with cohesive=true.
- Prefer 2-4 tasks for F-lite, 3-6 for F-full. Never split so fine that tasks share files.
- Shared seams (pyproject.toml, src/forge_diagram/__init__.py, types.py) belong to ONE task only — assign deliberately.
Return ONLY the structured plan.`

const subImplPrompt = (n, t) => `You are ONE of several agents implementing GitHub issue #${n} (${REPO}) in parallel. Your slice ONLY:
TASK ${t.id}: ${t.title}
FILE GROUP (touch ONLY these — another agent owns the rest): ${JSON.stringify(t.fileGroup)}
DETAIL: ${t.detail}

You are in a fresh isolated worktree off origin/${BASE}. Steps:
1. git checkout -B wf/${n}/${t.id} origin/${BASE}   (-B resets the local branch if a prior attempt left one)
2. Implement ONLY your file group per the issue's acceptance + RULES. Do NOT edit files outside your group.
3. Package format: cd ${PKG} && uv run ruff format <your files> && uv run ruff check --fix <your files>. (Full pytest runs at integration — but no obvious breakage.)
4. Commit (Conventional Commits; NEVER --amend/--force/--hard) and: git push -u origin wf/${n}/${t.id}
5. STOP. Return the structured result (status='pushed').

${GUARD}

${RULES}`

const implWholePrompt = (n) => `Implement GitHub issue #${n} (${REPO}) end-to-end. You are in a fresh isolated worktree off origin/${BASE}. Footprint: ${FOOTPRINT[n] || '(read issue)'}.
1. gh issue view ${n} --json title,body — acceptance criteria = contract. Reference clone: external_repos/beautiful-mermaid/.
2. git checkout -B feat/${n}-impl origin/${BASE}   (-B resets the local branch if a prior attempt left one)
3. Implement per RULES.
4. ${GATES}
5. Commit, push, open PR (gh pr create --base ${BASE}). PR body MUST include "## Decision trace": RC(P) · candidate Corr · chosen Corr + classe Patch|Archi|Mixed (justify) · logic level L. Add "Closes #${n}".
6. Return the structured result with status='pr-opened', branch, prUrl, classification, rootCause. diff is OPTIONAL: include (gh pr diff <branch>) truncated ~10000 chars ONLY if your response stays short; if large, set diff='' and STILL emit the StructuredOutput call — a separate step fetches the diff. Emitting StructuredOutput is mandatory; never end in prose.

${GUARD}

${RULES}`

const integratePrompt = (n, subBranches) => `Integrate the parallel sub-implementations of issue #${n} (${REPO}) into one PR. Sub-branches (disjoint file groups, already pushed): ${JSON.stringify(subBranches)}.
You are in a fresh isolated worktree. Steps:
1. git fetch origin
2. git checkout -B feat/${n} origin/${BASE}   (-B resets the local branch if a prior attempt left one)
3. Merge each sub-branch (disjoint files → conflict-free): for B in sub-branches: git merge --no-edit origin/B. If an unexpected conflict appears, resolve minimally and note it.
4. FULL GATES green: ${GATES}
   Fix integration seams (imports, wiring, __init__ exports) until green.
5. git push -u origin feat/${n}. Open PR: gh pr create --base ${BASE}. PR body MUST include "## Decision trace": RC(P) · candidate Corr · chosen Corr + classe Patch|Archi|Mixed (justify) · logic level L. Add "Closes #${n}".
6. Return structured result: status='pr-opened', branch='feat/${n}', prUrl, classification, rootCause. diff OPTIONAL — set diff='' if large; ALWAYS emit the StructuredOutput call, never end in prose.

${GUARD}

${RULES}`

const reviewPrompt = (n, key, L, diff) => `Review the PR for issue #${n} (${REPO}) through the **${key}** lens ONLY.
Lens focus: ${L.focus}
Acceptance contract: run/recall gh issue view ${n}. The PR branch is checked out-able via: gh pr checkout (or read files on the branch). Be specific and skeptical; report only real, actionable findings (file + line + why + concrete suggestion). Severity ∈ {blocking,major,minor,nit}.
${(key === 'visual' || key === 'math') ? 'You MUST actually render/recompute — do not judge from the diff alone.' : ''}

----- DIFF (truncated; may be empty for large PRs — then read the branch files directly) -----
${(diff || '').slice(0, 12000)}
----------------------------

${RULES}
Return ONLY structured findings (empty array if clean).`

const validatePrompt = (n, f, diff, k) => `SKEPTIC #${k}. A reviewer claims this finding on issue #${n}'s PR. Your job is to REFUTE it. Default real=false unless the evidence is incontrovertible. (Note: visual/math reviewers over-flag and hallucinate — demand concrete proof: a pixel observation or a recomputed number, not a vibe.)
FINDING [${f.severity}] ${f.title}
${f.detail}${f.file ? '\nat ' + f.file + (f.line ? ':' + f.line : '') : ''}

----- DIFF (truncated) -----
${(diff || '').slice(0, 9000)}
----------------------------
Is it a REAL, must-fix problem (not noise/style/false-positive)? Return ONLY the verdict.`

const fixPrompt = (n, branch, confirmed, round) => `Apply confirmed review findings to PR branch ${branch} of issue #${n} (${REPO}), round ${round}/2. You are in a fresh isolated worktree.
1. git fetch origin && git checkout ${branch} && git reset --hard origin/${branch}
2. Apply ONLY these confirmed findings (do not refactor beyond them):
${confirmed.map((f, i) => `  ${i + 1}. [${f.severity}] ${f.title} — ${f.detail}${f.file ? ' @' + f.file : ''}`).join('\n')}
3. ${GATES}
4. Commit (Conventional; NEVER --amend/--force) and git push origin ${branch}.
5. Return: which finding ids you 'fixed', which remain 'residual' (could not safely fix), and diff = (gh pr diff ${branch}) truncated ~12000 chars.

${GUARD}

${RULES}`

const diffPrompt = (n, branch) => `Output ONLY the unified diff of PR branch ${branch} (issue #${n}, ${REPO}). Run: gh pr diff ${branch}. Return it verbatim in the 'diff' field, truncated to ~10000 chars. Do nothing else — no analysis, no edits.`

const deferPrompt = (n, residual) => `Create a DEFERRED follow-up issue for unresolved review findings on issue #${n} (${REPO}), as a SIBLING (shared parent), blocked-by #${n}. Run from the roxabi-forge repo working dir (NEVER cd into the plugin-cache dir).
1. Resolve parent: P=$(gh api graphql -f query='query{repository(owner:"Roxabi",name:"roxabi-forge"){issue(number:${n}){parent{number}}}}' --jq '.data.repository.issue.parent.number // empty')
2. Create via triage CLI (sibling rule; forge board has no size field — omit --size):
   ${TRIAGE} create --title "review residual: from #${n}" --body "**Origin:** #${n} (deferred after 2 fix rounds)\\n\\n${residual.map((r) => '- ' + r.title + ': ' + r.detail).join('\\n')}" --blocked-by "#${n}" ${'${P:+--parent "#$P"}'}
3. Return the new issue URL (and parent number if any).`

// ---------- resilience: retry agent() on transient failures (API 529, no-structured-output) ----------
const sleep = (ms) => new Promise((r) => { try { setTimeout(r, ms) } catch (_) { r() } })
async function tryAgent(prompt, opts, tries = 3) {
  let lastErr
  for (let attempt = 1; attempt <= tries; attempt++) {
    try {
      return await agent(prompt, opts)
    } catch (e) {
      lastErr = e
      if (attempt < tries) {
        log(`↻ ${opts.label || 'agent'} attempt ${attempt}/${tries} failed (${String((e && e.message) || e).slice(0, 90)}) → backoff`)
        await sleep(attempt * 20000)
      }
    }
  }
  throw lastErr
}

// ---------- per-issue pipeline ----------
async function devIssue(n) {
  const size = SIZE[n] || 'S'
  // 1. PLAN / 2. SUB-IMPL / 3. INTEGRATE → impl (has prUrl + diff)
  let impl
  if (size === 'S') {
    impl = await tryAgent(implWholePrompt(n), { label: `impl:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:backend-dev', schema: IMPL_SCHEMA })
  } else {
    const plan = await tryAgent(planPrompt(n), { label: `plan:${n}`, phase: 'Plan', agentType: 'dev-core:backend-dev', schema: PLAN_SCHEMA })
    const tasks = plan && plan.tasks && plan.tasks.length ? plan.tasks : null
    if (!tasks || tasks.length <= 1) {
      impl = await tryAgent(implWholePrompt(n), { label: `impl:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:backend-dev', schema: IMPL_SCHEMA })
    } else {
      log(`#${n}: ${tasks.length} disjoint tasks → parallel sub-impl`)
      const subs = await parallel(tasks.map((t) => () =>
        tryAgent(subImplPrompt(n, t), { label: `impl:${n}:${t.id}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:backend-dev', schema: SUBIMPL_SCHEMA })))
      const subBranches = subs.filter(Boolean).filter((s) => s.status === 'pushed').map((s) => s.branch)
      if (!subBranches.length) return { issue: n, status: 'failed', stage: 'sub-impl' }
      impl = await tryAgent(integratePrompt(n, subBranches), { label: `integrate:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:backend-dev', schema: IMPL_SCHEMA })
    }
  }
  if (!impl || impl.status !== 'pr-opened') return { issue: n, status: 'failed', stage: 'impl', impl }

  // diff fetch fallback: impl may omit diff (large work) → fetch out-of-band
  let diff = impl.diff
  if (!diff || diff.length < 40) {
    const df = await tryAgent(diffPrompt(n, impl.branch), { label: `diff:${n}`, phase: 'Implement', agentType: 'dev-core:backend-dev', schema: DIFF_SCHEMA })
    diff = (df && df.diff) || ''
  }

  // 4-6. REVIEW → VALIDATE → FIX, ≤2 rounds
  const lensKeys = lensesFor(n)
  let residual = []
  for (let round = 1; round <= 2; round++) {
    const reviews = await parallel(lensKeys.map((key) => () =>
      tryAgent(reviewPrompt(n, key, LENS[key], diff), { label: `review:${n}:${key}:r${round}`, phase: 'Review', agentType: LENS[key].agent, schema: FINDINGS_SCHEMA })))
    const findings = reviews.filter(Boolean).flatMap((r) => (r.findings || []).map((f, i) => ({ ...f, id: `${r.lens}-${f.id || i}` })))
      .filter((f) => f.severity === 'blocking' || f.severity === 'major')
    if (!findings.length) { residual = []; break }

    const verdicts = await parallel(findings.map((f) => () =>
      parallel([1, 2].map((k) => () => tryAgent(validatePrompt(n, f, diff, k), { label: `validate:${n}:${f.id}:${k}`, phase: 'Validate', schema: VERDICT_SCHEMA })))
        .then((votes) => ({ f, real: votes.filter(Boolean).some((v) => v.real) }))))
    const confirmed = verdicts.filter((v) => v.real).map((v) => v.f)
    if (!confirmed.length) { residual = []; break }

    log(`#${n} round ${round}: ${confirmed.length} confirmed finding(s) → fix`)
    const fix = await tryAgent(fixPrompt(n, impl.branch, confirmed, round), { label: `fix:${n}:r${round}`, phase: 'Fix', isolation: 'worktree', agentType: 'dev-core:fixer', schema: FIX_SCHEMA })
    diff = (fix && fix.diff) || diff
    residual = (fix && fix.residual) || confirmed.map((f) => ({ title: f.title, detail: f.detail }))
    if (!residual.length) break
  }

  // 7. DEFER residual
  let deferred = null
  if (residual.length) {
    deferred = await tryAgent(deferPrompt(n, residual), { label: `defer:${n}`, phase: 'Fix', agentType: 'dev-core:backend-dev', schema: DEFER_SCHEMA })
  }
  return { issue: n, status: 'pr-opened', prUrl: impl.prUrl, classification: impl.classification, rootCause: impl.rootCause, gates: impl.gates, residual, deferred }
}

// ---------- failure policy: ISOLATE-DEFER-CONTINUE ----------
async function runIssue(n) {
  try {
    const r = await devIssue(n)
    if (!r || r.status === 'failed') {
      log(`⛔ #${n} FAILED at stage=${(r && r.stage) || 'unknown'} → isolated, deferred, wave continues`)
      return { issue: n, status: 'failed', stage: (r && r.stage) || 'unknown' }
    }
    return r
  } catch (e) {
    log(`⛔ #${n} THREW (${String(e && e.message || e).slice(0, 200)}) → isolated, deferred, wave continues`)
    return { issue: n, status: 'failed', stage: 'exception', error: String(e && e.message || e).slice(0, 500) }
  }
}

// ---------- wave driver (≤CAP issues per batch for merge cadence) ----------
const out = []
for (let i = 0; i < wave.length; i += CAP) {
  const batch = wave.slice(i, i + CAP)
  log(`batch → #${batch.join(' #')}`)
  const res = await parallel(batch.map((n) => () => runIssue(n)))
  out.push(...res.filter(Boolean))
}

const failed = out.filter((r) => r.status === 'failed').map((r) => ({ issue: r.issue, stage: r.stage, error: r.error }))
const shipped = out.filter((r) => r.status === 'pr-opened')
if (failed.length) log(`wave done: ${shipped.length} PR(s) opened, ${failed.length} isolated/deferred → #${failed.map((f) => f.issue).join(' #')}`)
else log(`wave done: ${shipped.length} PR(s) opened, 0 failures`)

return {
  wave,
  failed, // orchestrator: skip these issues' dependents in subsequent waves
  results: out.map((r) => ({
    issue: r.issue, status: r.status, stage: r.stage, prUrl: r.prUrl, classification: r.classification,
    residualCount: (r.residual || []).length, deferredUrl: r.deferred && r.deferred.issueUrl,
  })),
}
