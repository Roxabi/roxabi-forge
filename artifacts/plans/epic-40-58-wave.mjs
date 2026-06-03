// Workflow: epic-40-58-wave — run ONE dependency-wave of epic #40 (forge-diagram JS engine) slices.
//
// Epic #40 = forge-diagram, a JS runtime lyra-stack-grade diagram engine (merges #58).
// SSoT spec: artifacts/specs/epic-40-58-js-engine-spec.md
// Engine source lives under plugins/forge/references/graph-templates/fd/ (modular, glob-bundled at gen-time)
// → EVERY slice touches plugins/forge/ → the mermaid-guard applies to ALL slices (zero lowercase "mermaid").
//
// Slices → issues:  S1=#60  S2=#61  S3=#65  S4=#66  S5=#62  S6=#63  S7=#64  S8=#67
// Waves (orchestrator invokes one per call; merge between waves):
//   W1=[60]            S1 core (blocks everything)
//   W2=[61,62,63,64]   S2,S5,S6,S7  (need only S1; disjoint footprints) — parallel
//   W3=[65,66]         S3,S4        (need S2/elkjs; disjoint) — parallel
//   W4=[67]            S8 routing+cleanup (needs all) — guard-sensitive, last
//
// Per slice (size-adaptive):
//   F-lite/F-full : PLAN (disjoint file-groups) → SUB-IMPL N× parallel (worktree) → INTEGRATE → PR
//   ∀ size        : [REVIEW lens panel → VALIDATE (2 skeptics) → FIX] × ≤2 rounds → DEFER residual (sibling)
// Does NOT merge. Orchestrator main loop: /ci-watch + Read PNG → +reviewed label → auto-merge.yml
// (squash + update-behind + close issue), then re-invoke for the next wave. Full autonomy, 0 human gate.
//
// Invoke:  Workflow({ scriptPath: "artifacts/plans/epic-40-58-wave.mjs", args: [60] })            // W1
//          Workflow({ scriptPath: "artifacts/plans/epic-40-58-wave.mjs", args: [61,62,63,64] })   // W2 ...

export const meta = {
  name: 'epic-40-58-wave',
  description: 'Autonomous per-wave dev of epic #40 (forge-diagram JS engine) slices: size-adaptive decomposed impl + lens panel (correctness·security·tests·rules·visual·math) review/validate/fix loop + defer residual; merge handled by orchestrator',
  phases: [
    { title: 'Plan', detail: 'decompose F-lite/F-full into disjoint file-groups (fd/ modules)' },
    { title: 'Implement', detail: 'sub-impl per file-group → integrate → PR with decision trace' },
    { title: 'Review', detail: 'lens panel: correctness · security · tests · rules · visual (PNG) · math (coords)' },
    { title: 'Validate', detail: '2 skeptics/finding, refute-by-default' },
    { title: 'Fix', detail: 'apply confirmed findings; defer residual after 2 rounds' },
  ],
}

const REPO = 'Roxabi/roxabi-forge'
const BASE = 'staging'
const CAP = 4 // max slices in flight per batch (W2 has 4; engine also caps total agents at min(16,cores-2))
const FD = 'plugins/forge/references/graph-templates/fd'
const RENDER = '/home/mickael/projects/roxabi-forge/.claude/fc-loop/render.mjs'
const BROWSERS = '/home/mickael/.cache/ms-playwright'
const FRAMES = 'artifacts/frames/epic-40'
const BM = '/home/mickael/projects/external_repos/beautiful-mermaid' // absolute — NOT inside the forge repo
const LYRA = '/home/mickael/.roxabi/forge/lyra-stack-v2.html' // reference impl to lift the technique from
const SPEC = 'artifacts/specs/epic-40-58-js-engine-spec.md'
// version-proof triage path (resolve latest dev-core at runtime in-agent; do NOT hardcode a version)
const TRIAGE = 'bun "$(ls -d /home/mickael/.claude/plugins/cache/roxabi-marketplace/dev-core/*/skills/issue-triage/triage.ts | sort -V | tail -1)"'

const RULES = `RÈGLES (∀ P, verbatim) :
P:=problème · obs(P),Sym(P):=observable,symptômes · RC(P):=root cause(s)
Corr(P):={corrections} · Patch⊂Corr(local) · Archi⊂Corr(structurel) · Patch∩Archi=∅ · I:=input · trust(I):=confiance · C:=code · L:=niveau logique
1. RCA      : dériver RC(P). ¬fix sur obs/Sym. symptôme ≠ cause.
2. Corr     : énumérer; classer chaque ∈ Patch ⊻ Archi; CHOISIR explicitement (¬patch déguisé en archi).
3. fix@L    : appliquer F au niveau L = niveau(RC), ¬ au niveau où Sym apparaît.
4. trust(I) : ∀ I évaluer trust(I) AVANT usage; trust bas → valider/sanitize.
5. ✓        : tested(C) ∧ correct(C). vert ≠ correct. exiger les deux.
6. Doc(PR)  : tracer RC(P) + Corr choisie + classe(Patch|Archi) + niveau L.`

// Guard-safety: the mermaid purge (#21) — applies to ALL slices (engine lives under plugins/forge/).
const GUARD = `GUARD-SAFETY (mermaid purge #21 — non négociable, s'applique à TOUTES les slices):
- Tout le moteur fd/ vit sous plugins/forge/ → le mermaid-guard (lefthook glob plugins/forge/**/* + CI grep) s'applique.
- Identifiants/valeurs: forge-diagram, fd-engine, type:"flowchart"|"state"|"sequence"|"class"|"er"|"xychart"|"gantt"|"pie"|"architecture"|"hub-spoke". JAMAIS "mermaid"/"mermaid-*" minuscule.
- "Mermaid" (majuscule) est exempt du guard → OK en docstrings/prose ("Mermaid-compatible").
- Le LLM émet un descriptor JSON : AUCUN parsing de syntaxe mermaid → le token est évitable partout.
- Self-check OBLIGATOIRE avant PR: grep -rn '\\bmermaid\\b' plugins/forge/ DOIT être vide.`

// Gates — forge JS reality (no root pyproject/pytest; bun is first-class).
const GATES = `GATES (verts avant PR):
- Lint:  bun lint  (biome) — tout JS ajouté sous plugins/forge/ doit passer.
- Guard: grep -rn '\\bmermaid\\b' plugins/forge/ DOIT être vide.
- Tests: si un runner est configuré / des *.test.* existent → bun test. (Ajoute des tests pour ta slice.)
- Gen-time elk (slices à layout): bun scripts/fd-layout.mjs doit tourner sans erreur sur un descriptor sample (lancé depuis la racine du repo/worktree).
- Rendu smoke: produis un exemple self-contained ${FD}/examples/<type>.html (engine bundlé inline + descriptor sample) qui s'ouvre en file:// sans erreur console — le reviewer visuel le rend en PNG.
- Si tu modifies un .github/workflows/*.yml: python -c "import yaml; yaml.safe_load(open('<f>'))" + job 'ci' présent + QUOTER tout name: contenant ':'.`

// Visual render recipe — reuses the proven fc-loop Playwright harness. Particles OFF by default (AC-9).
const VISUAL = `RENDU VISUEL (réutilise le harness QA prouvé; particules OFF par défaut):
1. Pour chaque type produit par cette slice, charge/produit ${FD}/examples/<type>.html (engine bundlé inline + descriptor sample, particules désactivées).
2. mkdir -p ${FRAMES}/<N>
3. Rends: PLAYWRIGHT_BROWSERS_PATH=${BROWSERS} node ${RENDER} ${FD}/examples/<type>.html ${FRAMES}/<N>/<type>.png 1280 dark
   (le render.mjs ne crée pas le dossier → le mkdir -p ci-dessus est obligatoire).
4. Read le PNG et juge: arrowheads géants, overlap nodes/edges, clipping, texte illisible/débordant,
   hors-canvas, arêtes détachées, frames pâles. (Mémoire forge-chart-qa: mental gate ≠ pixels — TOUJOURS lire le PNG.)
5. AC-1/AC-10: les edges sont mesurées en pixel (overlay position:absolute inset:0), PAS de viewBox 0-100 stretché,
   PAS de preserveAspectRatio="none". Vérifie-le dans le HTML.
6. Référence qualité: ${LYRA} (la technique liftée). Cross-check elk: ${BM} (examples/{bar,line,mixed}-interactive.svg) via bun si utile.`

// Slice → issue:  S1=60 S2=61 S3=65 S4=66 S5=62 S6=63 S7=64 S8=67
const SIZE = {
  60: 'F-full', // S1 core: core.js+edges.js+cards.js+bundler.js+architecture.js+css → decompose
  61: 'F-full', // S2 elk gen-time + flowchart + state
  62: 'F-lite', // S5 xychart
  63: 'F-lite', // S6 gantt+pie
  64: 'F-lite', // S7 particles+interactions
  65: 'F-lite', // S3 class+ER
  66: 'F-lite', // S4 sequence
  67: 'F-lite', // S8 routing+cleanup
}

// Disjoint footprints (from spec §8). All under plugins/forge/ except scripts/fd-layout.mjs (S2).
const FOOTPRINT = {
  60: `${FD}/{core.js,edges.js,cards.js,bundler.js,types/architecture.js} + plugins/forge/references/graph-templates/fd-engine.css + ${FD}/examples/architecture.html. Core engine: descriptor reader, HTML/CSS card renderer (premium for architecture/hub-spoke per OQ-3), DOM-measured pixel-space SVG edge engine (getBoundingClientRect + ResizeObserver, lift from ${LYRA} l.492-960), glob-discovery bundler. Read ${LYRA} + ${SPEC} §1-§5 first.`,
  61: `${FD}/types/{flowchart.js,state.js} + scripts/fd-layout.mjs (bun gen-time elkjs: import elk.bundled.js from ${BM}, compute node x/y, inject into descriptor) + ${FD}/examples/{flowchart,state}.html. Simple-box cards (OQ-3). Adapt elk layout options from ${BM}/src/layout-engine.ts.`,
  62: `${FD}/types/xychart.js + ${FD}/examples/xychart.html. Bar + line, SVG axes/scales/series math, no elkjs. MATH-verify coords vs raw data.`,
  63: `${FD}/types/{gantt.js,pie.js} + ${FD}/examples/{gantt,pie}.html. Declarative layout, no elkjs. MATH-verify (gantt bar x/width from dates; pie arc angles from values).`,
  64: `${FD}/{particles.js,interactions.js} + ${FD}/examples/architecture-live.html. Opt-in rAF particles (one-shot on hover/trigger; loop via options.particles:"loop") + spotlight/use-case animation, lift from ${LYRA}. OFF by default.`,
  65: `${FD}/types/{class.js,er.js} + ${FD}/examples/{class,er}.html. elkjs layout (uses scripts/fd-layout.mjs from S2), crow's-foot markers, attribute rows. 6 UML arrows for class.`,
  66: `${FD}/types/sequence.js + ${FD}/examples/sequence.html. elkjs x-layout + lifeline y-layout + activation blocks. Read ${BM}/src/sequence/layout.ts in full first (200+ LOC, many edge cases).`,
  67: `plugins/forge/skills/forge-chart/SKILL.md (routing table: diagram types → forge-diagram engine) + DELETE plugins/forge/references/graph-templates/{sequence,state,er,gantt,pie}.html + aesthetic→theme mapping. GUARD-SENSITIVE: end with grep -rn '\\bmermaid\\b' plugins/forge/ = empty. Runs last.`,
}

const LENS = {
  correctness: { agent: 'dev-core:frontend-dev', focus: 'logic bugs in descriptor handling, edge-measurement math, layout adapter, type rendering; behavioural drift' },
  security: { agent: 'dev-core:security-auditor', focus: 'untrusted descriptor JSON: prototype pollution, unbounded recursion/nesting, XSS via unescaped labels injected into HTML/SVG, path issues in the bun gen-time layout step' },
  tests: { agent: 'dev-core:tester', focus: 'do tests prove behaviour (not just pass)? coverage of the slice acceptance? determinism (no random IDs/timestamps in output)?' },
  rules: { agent: 'dev-core:frontend-dev', focus: 'RULES compliance: fix@root-cause-level L; honest Patch⊻Archi; GUARD-safety (no lowercase mermaid under plugins/forge/); modular fd/ source stays glob-discoverable (no edit to a shared registry)' },
  visual: { agent: 'dev-core:frontend-dev', focus: 'PNG eyeball: giant arrowheads, node/edge overlap, clipping, illegible/overflowing text, off-canvas, detached edges, faint frames; AC-1 lyra-grade edges; AC-10 no preserveAspectRatio="none". ' + VISUAL },
  math: { agent: 'dev-core:frontend-dev', focus: 'pixels ≠ data: recompute each coordinate from raw data + the renderer\'s OWN formula and diff vs output (xychart ticks/bar heights, gantt bar x/width, pie arc angles). A chart can look plausible yet encode wrong numbers (cf. PR #55 bubble bug).' },
}
// Lenses per slice (issue number). A non-diagram slice has no visual/math.
function lensesFor(n) {
  const base = ['correctness', 'security', 'tests', 'rules']
  if (n === 62 || n === 63) return [...base, 'visual', 'math'] // xychart, gantt+pie → quantitative
  return [...base, 'visual'] // all others render a diagram; S8 renders an end-to-end smoke
}

let _raw = args
if (typeof _raw === 'string') { try { _raw = JSON.parse(_raw) } catch (e) { /* leave as string */ } }
const wave = Array.isArray(_raw)
  ? _raw.map(Number).filter((x) => Number.isFinite(x))
  : (_raw && Array.isArray(_raw.issues) ? _raw.issues.map(Number).filter((x) => Number.isFinite(x)) : [])
if (!wave.length) throw new Error(`args resolved empty. typeof args=${typeof args}; value=${JSON.stringify(args)?.slice(0, 200)}. Expected array of issue numbers, e.g. [60] or [61,62,63,64]`)

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
    gates: { type: 'object', properties: { lint: { type: 'boolean' }, test: { type: 'boolean' }, guard: { type: 'boolean' }, render: { type: 'boolean' } } },
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
Read ${SPEC} for the engine architecture. Explore the repo (Read/Grep) enough to map files. Rules:
- Each task.fileGroup must be a set of files NO other task touches (strict disjointness).
- The fd/ engine is glob-bundled: a new module file is discovered automatically, so tasks must NOT edit a shared registry/manifest. If a shared seam seems needed, flag it.
- If the issue is cohesive (one tight unit), return a SINGLE task with cohesive=true.
- Prefer 2-4 tasks for F-lite, 3-6 for F-full.
Return ONLY the structured plan.`

const subImplPrompt = (n, t) => `You are ONE of several agents implementing GitHub issue #${n} (${REPO}) in parallel. Your slice ONLY:
TASK ${t.id}: ${t.title}
FILE GROUP (touch ONLY these — another agent owns the rest): ${JSON.stringify(t.fileGroup)}
DETAIL: ${t.detail}

You are in a fresh isolated worktree off origin/${BASE}. Steps:
1. git checkout -B wf/${n}/${t.id} origin/${BASE}
2. Implement ONLY your file group per the issue's acceptance + ${SPEC} + RULES. Do NOT edit files outside your group.
3. Lint your files: bun lint (biome). Guard self-check if under plugins/forge/: grep -rn '\\bmermaid\\b' <your files> must be empty.
4. Commit (Conventional Commits; NEVER --amend/--force/--hard) and: git push -u origin wf/${n}/${t.id}
5. STOP. Return the structured result (status='pushed').

${GUARD}

${RULES}`

const implWholePrompt = (n) => `Implement GitHub issue #${n} (${REPO}) end-to-end. You are in a fresh isolated worktree off origin/${BASE}. Footprint: ${FOOTPRINT[n] || '(read issue)'}.
1. gh issue view ${n} --json title,body — acceptance = contract. Read ${SPEC} (engine architecture) + ${LYRA} (technique to lift).
2. git checkout -B feat/${n}-impl origin/${BASE}
3. Implement per ${SPEC} + RULES.
4. ${GATES}
5. Commit, push, open PR (gh pr create --base ${BASE}). PR body MUST include "## Decision trace": RC(P) · candidate Corr · chosen Corr + classe Patch|Archi|Mixed (justify) · logic level L. Add "Closes #${n}".
6. Return structured result: status='pr-opened', branch, prUrl, classification, rootCause. diff OPTIONAL: include (gh pr diff <branch>) truncated ~10000 chars ONLY if your response stays short; else diff='' and STILL emit the StructuredOutput call (a separate step fetches it). Emitting StructuredOutput is mandatory; never end in prose.

${GUARD}

${RULES}`

const integratePrompt = (n, subBranches) => `Integrate the parallel sub-implementations of issue #${n} (${REPO}) into one PR. Sub-branches (disjoint file groups, pushed): ${JSON.stringify(subBranches)}.
You are in a fresh isolated worktree. Steps:
1. git fetch origin
2. git checkout -B feat/${n} origin/${BASE}
3. Merge each sub-branch (disjoint files → conflict-free): for B in sub-branches: git merge --no-edit origin/B. Resolve any unexpected conflict minimally + note it.
4. FULL GATES green: ${GATES}
   Fix integration seams (bundler discovery, imports) until green.
5. git push -u origin feat/${n}. Open PR: gh pr create --base ${BASE}. PR body MUST include "## Decision trace". Add "Closes #${n}".
6. Return structured result: status='pr-opened', branch='feat/${n}', prUrl, classification, rootCause. diff OPTIONAL — set diff='' if large; ALWAYS emit StructuredOutput, never end in prose.

${GUARD}

${RULES}`

const reviewPrompt = (n, key, L, diff) => `Review the PR for issue #${n} (${REPO}) through the **${key}** lens ONLY.
Lens focus: ${L.focus}
Acceptance contract: recall gh issue view ${n} + ${SPEC}. The PR branch is checkout-able (gh pr checkout) or read branch files. Be specific and skeptical; report only real, actionable findings (file + line + why + concrete suggestion). Severity ∈ {blocking,major,minor,nit}.
${(key === 'visual' || key === 'math') ? 'You MUST actually render/recompute — do not judge from the diff alone.' : ''}

----- DIFF (truncated; may be empty for large PRs — then read the branch files directly) -----
${(diff || '').slice(0, 12000)}
----------------------------

${RULES}
Return ONLY structured findings (empty array if clean).`

const validatePrompt = (n, f, diff, k) => `SKEPTIC #${k}. A reviewer claims this finding on issue #${n}'s PR. Your job is to REFUTE it. Default real=false unless evidence is incontrovertible. (Visual/math reviewers over-flag and hallucinate — demand a concrete pixel observation or a recomputed number, not a vibe.)
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
5. Return: which finding ids you 'fixed', which remain 'residual', and diff = (gh pr diff ${branch}) truncated ~12000 chars.

${GUARD}

${RULES}`

const diffPrompt = (n, branch) => `Output ONLY the unified diff of PR branch ${branch} (issue #${n}, ${REPO}). Run: gh pr diff ${branch}. Return it verbatim in 'diff', truncated ~10000 chars. Do nothing else — no analysis, no edits.`

const deferPrompt = (n, residual) => `Create a DEFERRED follow-up issue for unresolved review findings on issue #${n} (${REPO}), as a SIBLING (shared parent), blocked-by #${n}. Run from the roxabi-forge repo working dir (NEVER cd into the plugin-cache dir; forge board has no size field — omit --size).
1. Resolve parent: P=$(gh api graphql -f query='query{repository(owner:"Roxabi",name:"roxabi-forge"){issue(number:${n}){parent{number}}}}' --jq '.data.repository.issue.parent.number // empty')
2. Create via triage CLI (version-resolved at runtime):
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

// ---------- per-slice pipeline ----------
async function devIssue(n) {
  const size = SIZE[n] || 'S'
  let impl
  if (size === 'S') {
    impl = await tryAgent(implWholePrompt(n), { label: `impl:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })
  } else {
    const plan = await tryAgent(planPrompt(n), { label: `plan:${n}`, phase: 'Plan', agentType: 'dev-core:frontend-dev', schema: PLAN_SCHEMA })
    const tasks = plan && plan.tasks && plan.tasks.length ? plan.tasks : null
    if (!tasks || tasks.length <= 1) {
      impl = await tryAgent(implWholePrompt(n), { label: `impl:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })
    } else {
      log(`#${n}: ${tasks.length} disjoint tasks → parallel sub-impl`)
      const subs = await parallel(tasks.map((t) => () =>
        tryAgent(subImplPrompt(n, t), { label: `impl:${n}:${t.id}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: SUBIMPL_SCHEMA })))
      const subBranches = subs.filter(Boolean).filter((s) => s.status === 'pushed').map((s) => s.branch)
      if (!subBranches.length) return { issue: n, status: 'failed', stage: 'sub-impl' }
      impl = await tryAgent(integratePrompt(n, subBranches), { label: `integrate:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })
    }
  }
  if (!impl || impl.status !== 'pr-opened') return { issue: n, status: 'failed', stage: 'impl', impl }

  // Post-PR review/validate/fix/defer is BEST-EFFORT. The PR is ALREADY OPEN, so a thrown agent
  // step (StructuredOutput refusal after retries, etc.) must NEVER discard it. On throw → fall back
  // to manual review (orchestrator reads the PNG/CI). Fixes the W2 #61 class: PR fine, review threw.
  let residual = []
  let deferred = null
  let reviewIncomplete = false
  try {
    let diff = impl.diff
    if (!diff || diff.length < 40) {
      const df = await tryAgent(diffPrompt(n, impl.branch), { label: `diff:${n}`, phase: 'Implement', agentType: 'dev-core:frontend-dev', schema: DIFF_SCHEMA })
      diff = (df && df.diff) || ''
    }

    const lensKeys = lensesFor(n)
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

    if (residual.length) {
      deferred = await tryAgent(deferPrompt(n, residual), { label: `defer:${n}`, phase: 'Fix', agentType: 'dev-core:frontend-dev', schema: DEFER_SCHEMA })
    }
  } catch (e) {
    reviewIncomplete = true
    log(`⚠ #${n}: PR ${impl.prUrl} is OPEN but post-PR review threw (${String((e && e.message) || e).slice(0, 120)}) → manual review required`)
  }
  return { issue: n, status: 'pr-opened', prUrl: impl.prUrl, classification: impl.classification, rootCause: impl.rootCause, gates: impl.gates, residual, deferred, reviewIncomplete }
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

// ---------- wave driver (≤CAP slices per batch) ----------
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
  failed,
  results: out.map((r) => ({
    issue: r.issue, status: r.status, stage: r.stage, prUrl: r.prUrl, classification: r.classification,
    residualCount: (r.residual || []).length, deferredUrl: r.deferred && r.deferred.issueUrl,
    reviewIncomplete: r.reviewIncomplete || false,
  })),
}
