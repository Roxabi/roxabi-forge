// Workflow: epic-40-58-wave-v2 — run ONE dependency-wave of epic #40 (forge-diagram JS engine) slices.
//
// V2 — rewritten failure/recovery layer after the V1 postmortem
// (artifacts/postmortem/epic-40-58-fd-engine.md). Same args interface as V1, drop-in:
//   Workflow({ scriptPath: "artifacts/plans/epic-40-58-wave-v2.mjs", args: [60] })
//
// ─────────────────────────────────────────────────────────────────────────────
// WHY V2 (what V1 got wrong)
//   V1 trusted each big agent's self-reported StructuredOutput as the source of truth.
//   When that report flaked (agent ended in prose, not a tool call) a NON-PARALLEL
//   tryAgent threw → the whole slice was marked failed — EVEN WHEN its PR was already
//   open (W2 #61) or its work was committed (W2 #64, W3 #66). 5/8 slices needed manual
//   recovery; the impl itself was never wrong — only the reporting/coordination layer.
//
// V2 PRINCIPLE: separate DOING the work from REPORTING it. Never trust self-report.
//   After every work phase, a tiny read-only PROBE agent (3-field schema → ~never
//   refuses StructuredOutput) queries gh/git GROUND TRUTH. Each phase is idempotent
//   and resumable from that truth:
//     - impl/integrate threw but a PR exists      → adopt the probed PR (no rerun)
//     - branch pushed with commits but no PR      → finish-PR from the existing branch
//     - sub-branches pushed but integrate failed  → re-integrate from probed branches
//     - nothing on the remote                     → fail with a RECOVERABLE hint
//   Plus: diffs never travel in agent returns (they caused the prose-ending);
//   commit-header hygiene baked into every commit prompt (commitlint ≤100, lowercase);
//   deletion slices grep+migrate consumers and gate on zero dangling refs.
//
// Slices → issues:  S1=#60  S2=#61  S3=#65  S4=#66  S5=#62  S6=#63  S7=#64  S8=#67
// Waves: W1=[60] · W2=[61,62,63,64] · W3=[65,66] · W4=[67]. Merge between waves.
// Does NOT merge. Orchestrator applies `reviewed` AFTER ci is green (repo
// allow_auto_merge=false → labelling before green strands the PR — see orchestratorNotes).

export const meta = {
  name: 'epic-40-58-wave-v2',
  description: 'Autonomous per-wave dev of epic #40 (forge-diagram) slices — V2 with probe-based git-truth recovery: idempotent impl/integrate, finish-PR fallback, best-effort review/validate/fix, deletion consumer-migration gate; merge handled by orchestrator',
  phases: [
    { title: 'Plan', detail: 'decompose F-lite/F-full into disjoint file-groups (fd/ modules)' },
    { title: 'Implement', detail: 'sub-impl per file-group → integrate → PR' },
    { title: 'Reconcile', detail: 'probe gh/git ground truth; finish-PR or re-integrate as needed (no blind rerun)' },
    { title: 'Review', detail: 'lens panel: correctness · security · tests · rules · visual (PNG) · math (coords)' },
    { title: 'Validate', detail: '2 skeptics/finding, refute-by-default' },
    { title: 'Fix', detail: 'apply confirmed findings; defer residual after 2 rounds' },
  ],
}

const REPO = 'Roxabi/roxabi-forge'
const BASE = 'staging'
const CAP = 4
const FD = 'plugins/forge/references/graph-templates/fd'
const RENDER = '/home/mickael/projects/roxabi-forge/.claude/fc-loop/render.mjs'
const BROWSERS = '/home/mickael/.cache/ms-playwright'
const FRAMES = 'artifacts/frames/epic-40'
const BM = '/home/mickael/projects/external_repos/beautiful-mermaid'
const LYRA = '/home/mickael/.roxabi/forge/lyra-stack-v2.html'
const SPEC = 'artifacts/specs/epic-40-58-js-engine-spec.md'
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

// V2: commit hygiene — the two latent bugs that bounced commits in V1.
const COMMIT = `HYGIÈNE COMMIT (commitlint strict — sinon le commit-msg hook rejette) :
- Conventional Commits: <type>(<scope>): <desc>. Header ≤ 100 caractères. Description en minuscule après ':' (PAS de Sentence-case).
- Footer (Co-Authored-By: …) précédé d'une ligne vide.
- JAMAIS --amend / --force / --hard. Hook fail → corrige + NOUVEAU commit.
- IMPORTANT: COMMIT ton travail AVANT de t'arrêter, quoi qu'il arrive — ne laisse jamais de travail non-commité dans le worktree.`

const GUARD = `GUARD-SAFETY (mermaid purge #21 — non négociable, s'applique à TOUTES les slices):
- Tout le moteur fd/ vit sous plugins/forge/ → le mermaid-guard (lefthook glob plugins/forge/**/* + CI grep) s'applique.
- Identifiants/valeurs: forge-diagram, fd-engine, type:"flowchart"|"state"|"sequence"|"class"|"er"|"xychart"|"gantt"|"pie"|"architecture"|"hub-spoke". JAMAIS "mermaid"/"mermaid-*" minuscule.
- "Mermaid" (majuscule) est exempt du guard → OK en docstrings/prose ("Mermaid-compatible").
- Le LLM émet un descriptor JSON : AUCUN parsing de syntaxe mermaid → le token est évitable partout.
- Self-check OBLIGATOIRE avant PR: grep -rn '\\bmermaid\\b' plugins/forge/ DOIT être vide.`

const GATES = `GATES (verts avant PR):
- Lint:  bun lint  (biome) — tout JS ajouté sous plugins/forge/ doit passer.
- Guard: grep -rn '\\bmermaid\\b' plugins/forge/ DOIT être vide.
- Tests: si un runner est configuré / des *.test.* existent → bun test. (Ajoute des tests pour ta slice.)
- Gen-time elk (slices à layout): bun scripts/fd-layout.mjs doit tourner sans erreur sur un descriptor sample (depuis la racine du repo/worktree).
- Rendu smoke: produis ${FD}/examples/<type>.html (engine bundlé inline + descriptor sample, particules OFF) qui s'ouvre en file:// sans erreur console.
- DANGLING-REF (si ta slice SUPPRIME un fichier référencé): grep -rn le nom du fichier supprimé dans TOUT plugins/forge/ et migre CHAQUE consommateur (autres skills inclus: forge-guide, forge-slides, references/*.md, README, *.css) AVANT de supprimer. Gate final: zéro lien/route actif vers un fichier supprimé.
- Si tu modifies un .github/workflows/*.yml: python -c "import yaml; yaml.safe_load(open('<f>'))" + job 'ci' présent + QUOTER tout name: contenant ':'.`

const VISUAL = `RENDU VISUEL (réutilise le harness QA prouvé; particules OFF par défaut):
1. Pour chaque type produit par cette slice, charge/produit ${FD}/examples/<type>.html (engine bundlé inline + descriptor sample, particules désactivées).
2. mkdir -p ${FRAMES}/<N>
3. Rends: PLAYWRIGHT_BROWSERS_PATH=${BROWSERS} node ${RENDER} ${FD}/examples/<type>.html ${FRAMES}/<N>/<type>.png 1280 dark
   (le render.mjs ne crée pas le dossier → le mkdir -p ci-dessus est obligatoire).
4. Read le PNG et juge: arrowheads géants, overlap nodes/edges, clipping, texte illisible/débordant,
   hors-canvas, arêtes détachées, frames pâles. (Mémoire forge-chart-qa: mental gate ≠ pixels — TOUJOURS lire le PNG.)
5. AC-1/AC-10: edges mesurées en pixel (overlay position:absolute inset:0), PAS de viewBox 0-100 stretché, PAS de preserveAspectRatio="none". Vérifie-le dans le HTML.
6. Référence qualité: ${LYRA}. Cross-check elk: ${BM} si utile.`

const SIZE = {
  60: 'F-full', 61: 'F-full', 62: 'F-lite', 63: 'F-lite',
  64: 'F-lite', 65: 'F-lite', 66: 'F-lite', 67: 'F-lite',
}

const FOOTPRINT = {
  60: `${FD}/{core.js,edges.js,cards.js,bundler.js,types/architecture.js} + plugins/forge/references/graph-templates/fd-engine.css + ${FD}/examples/architecture.html. Core engine: descriptor reader, HTML/CSS card renderer (premium for architecture/hub-spoke per OQ-3), DOM-measured pixel-space SVG edge engine (getBoundingClientRect + ResizeObserver, lift from ${LYRA} l.492-960), glob-discovery bundler. Read ${LYRA} + ${SPEC} §1-§5 first.`,
  61: `${FD}/types/{flowchart.js,state.js} + scripts/fd-layout.mjs (bun gen-time elkjs: import elk.bundled.js from ${BM}, compute node x/y, inject into descriptor) + ${FD}/examples/{flowchart,state}.html. Simple-box cards (OQ-3). Adapt elk layout options from ${BM}/src/layout-engine.ts.`,
  62: `${FD}/types/xychart.js + ${FD}/examples/xychart.html. Bar + line, SVG axes/scales/series math, no elkjs. MATH-verify coords vs raw data.`,
  63: `${FD}/types/{gantt.js,pie.js} + ${FD}/examples/{gantt,pie}.html. Declarative layout, no elkjs. MATH-verify (gantt bar x/width from dates; pie arc angles from values).`,
  64: `${FD}/{particles.js,interactions.js} + ${FD}/examples/architecture-live.html. Opt-in rAF particles (one-shot on hover/trigger; loop via options.particles:"loop") + spotlight/use-case animation, lift from ${LYRA}. OFF by default.`,
  65: `${FD}/types/{class.js,er.js} + ${FD}/examples/{class,er}.html. elkjs layout (uses scripts/fd-layout.mjs from S2), crow's-foot markers, attribute rows. 6 UML arrows for class.`,
  66: `${FD}/types/sequence.js + ${FD}/examples/sequence.html. elkjs x-layout + lifeline y-layout + activation blocks. Read ${BM}/src/sequence/layout.ts in full first.`,
  67: `forge-chart routing → fd-engine + RETIRE legacy static templates. SCOPE ÉLARGI (postmortem V1): ces templates sont consommés AUSSI par forge-guide & forge-slides. Étapes: (a) grep -rn les 5 noms dans TOUT plugins/forge/ pour lister les consommateurs; (b) migre forge-chart/SKILL.md (table de routing 10 types + aesthetic→theme), forge-guide/SKILL.md, forge-slides/SKILL.md, forge-chart/references/phase-3-generate.md vers le path descriptor fd-engine; (c) nettoie README.md / fgraph-base.css / examples/system-architecture.html (commentaires); (d) DELETE plugins/forge/references/graph-templates/{sequence,state,er,gantt,pie}.html + leurs examples/ démos (vérifie qu'un examples/fd-<type>.html existe avant de supprimer la démo legacy). GUARD-SENSITIVE: termine avec grep -rn '\\bmermaid\\b' plugins/forge/ = vide ET zéro lien/route actif vers un template supprimé. Runs last.`,
}

const LENS = {
  correctness: { agent: 'dev-core:frontend-dev', focus: 'logic bugs in descriptor handling, edge-measurement math, layout adapter, type rendering; behavioural drift' },
  security: { agent: 'dev-core:security-auditor', focus: 'untrusted descriptor JSON: prototype pollution, unbounded recursion/nesting, XSS via unescaped labels injected into HTML/SVG, path issues in the bun gen-time layout step' },
  tests: { agent: 'dev-core:tester', focus: 'do tests prove behaviour (not just pass)? coverage of the slice acceptance? determinism (no random IDs/timestamps in output)?' },
  rules: { agent: 'dev-core:frontend-dev', focus: 'RULES compliance: fix@root-cause-level L; honest Patch⊻Archi; GUARD-safety (no lowercase mermaid under plugins/forge/); modular fd/ source stays glob-discoverable (no edit to a shared registry); dangling refs to deleted files' },
  visual: { agent: 'dev-core:frontend-dev', focus: 'PNG eyeball: giant arrowheads, node/edge overlap, clipping, illegible/overflowing text, off-canvas, detached edges, faint frames; AC-1 lyra-grade edges; AC-10 no preserveAspectRatio="none". ' + VISUAL },
  math: { agent: 'dev-core:frontend-dev', focus: 'pixels ≠ data: recompute each coordinate from raw data + the renderer\'s OWN formula and diff vs output (xychart ticks/bar heights, gantt bar x/width, pie arc angles). A chart can look plausible yet encode wrong numbers (cf. PR #55 bubble bug).' },
}
function lensesFor(n) {
  const base = ['correctness', 'security', 'tests', 'rules']
  if (n === 62 || n === 63) return [...base, 'visual', 'math']
  return [...base, 'visual']
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
    tasks: { type: 'array', items: {
      type: 'object', additionalProperties: false, required: ['id', 'title', 'fileGroup', 'detail'],
      properties: { id: { type: 'string' }, title: { type: 'string' }, fileGroup: { type: 'array', items: { type: 'string' } }, detail: { type: 'string' } },
    } },
  },
}
// V2: impl/integrate return is SHORT — no diff field (the diff is what made agents end in prose).
const IMPL_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['status'],
  properties: {
    status: { type: 'string', enum: ['pr-opened', 'pushed-no-pr', 'failed'] },
    branch: { type: 'string' }, prUrl: { type: 'string' },
    classification: { type: 'string', enum: ['Patch', 'Archi', 'Mixed'] },
    rootCause: { type: 'string' }, notes: { type: 'string' },
  },
}
// V2: the recovery keystone — tiny, read-only, ~never refuses StructuredOutput.
const PROBE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['prExists', 'branchExists'],
  properties: {
    prExists: { type: 'boolean' }, prNumber: { type: 'number' }, prUrl: { type: 'string' },
    prState: { type: 'string' }, // OPEN | MERGED | CLOSED
    branchExists: { type: 'boolean' }, branchAhead: { type: 'number' },
    subBranches: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
}
const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['lens', 'findings'],
  properties: {
    lens: { type: 'string' },
    findings: { type: 'array', items: {
      type: 'object', additionalProperties: false, required: ['id', 'severity', 'title', 'detail'],
      properties: {
        id: { type: 'string' }, severity: { type: 'string', enum: ['blocking', 'major', 'minor', 'nit'] },
        file: { type: 'string' }, line: { type: 'string' }, title: { type: 'string' }, detail: { type: 'string' }, suggestion: { type: 'string' },
      },
    } },
  },
}
const VERDICT_SCHEMA = { type: 'object', additionalProperties: false, required: ['real', 'reason'], properties: { real: { type: 'boolean' }, reason: { type: 'string' } } }
const FIX_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['round', 'fixed', 'residual'],
  properties: {
    round: { type: 'number' }, fixed: { type: 'array', items: { type: 'string' } },
    residual: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['title', 'detail'], properties: { id: { type: 'string' }, title: { type: 'string' }, detail: { type: 'string' } } } },
    gatesPass: { type: 'boolean' },
  },
}
const DEFER_SCHEMA = { type: 'object', additionalProperties: false, required: ['issueUrl'], properties: { issueUrl: { type: 'string' }, parent: { type: 'number' } } }
const DIFF_SCHEMA = { type: 'object', additionalProperties: false, required: ['diff'], properties: { diff: { type: 'string' } } }

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
4. Commit then PUSH: git push -u origin wf/${n}/${t.id}  (pushing is REQUIRED — a probe step later discovers your branch by name on origin, not from your reply).
5. STOP. Return the SHORT structured result (status='pushed', branch='wf/${n}/${t.id}').

${COMMIT}

${GUARD}

${RULES}`

const implWholePrompt = (n) => `Implement GitHub issue #${n} (${REPO}) end-to-end. Fresh isolated worktree off origin/${BASE}. Footprint: ${FOOTPRINT[n] || '(read issue)'}.
1. gh issue view ${n} --json title,body — acceptance = contract. Read ${SPEC} + ${LYRA}.
2. git checkout -B feat/${n} origin/${BASE}   (use EXACTLY this branch name — the probe/finish-PR steps key on feat/${n}).
3. Implement per ${SPEC} + RULES.
4. ${GATES}
5. Commit, PUSH (git push -u origin feat/${n}), open PR (gh pr create --base ${BASE}). PR body MUST include "## Decision trace" (RC · candidate Corr · chosen Corr + classe Patch|Archi|Mixed · level L) AND the line "Closes #${n}".
6. Return the SHORT structured result: status='pr-opened', branch='feat/${n}', prUrl, classification, rootCause. DO NOT put a diff or file contents in your reply — keep it tiny so the StructuredOutput call always lands. If you pushed feat/${n} but could not open the PR, return status='pushed-no-pr' (a fallback step opens it). Emitting StructuredOutput is mandatory; never end in prose.

${COMMIT}

${GUARD}

${RULES}`

const integratePrompt = (n, subBranches) => `Integrate the parallel sub-implementations of issue #${n} (${REPO}) into one PR. Sub-branches (disjoint, pushed to origin): ${JSON.stringify(subBranches)}.
Fresh isolated worktree. Steps:
1. git fetch origin
2. git checkout -B feat/${n} origin/${BASE}   (EXACTLY feat/${n})
3. Merge each sub-branch (disjoint files → conflict-free): for B in sub-branches: git merge --no-edit origin/B. Resolve any unexpected conflict minimally + note it. (Idempotent: if feat/${n} already contains a sub-branch's commits, skip it.)
4. FULL GATES green: ${GATES}  — fix integration seams (bundler discovery, imports) until green.
5. git push -u origin feat/${n}. Open PR (gh pr create --base ${BASE}) — UNLESS one already exists for feat/${n} (then reuse it). PR body MUST include "## Decision trace" + "Closes #${n}".
6. Return SHORT result: status='pr-opened' (or 'pushed-no-pr' if push OK but PR failed), branch='feat/${n}', prUrl, classification, rootCause. NO diff in the reply.

${COMMIT}

${GUARD}

${RULES}`

// V2 keystone: read-only ground-truth probe. Tiny schema → reliable StructuredOutput.
const probePrompt = (n) => `READ-ONLY probe. Report the TRUE state of issue #${n}'s (${REPO}) PR/branch on origin. Edit NOTHING. Run from the repo working dir (do NOT cd into any plugin-cache).
1. PR: gh pr list --repo ${REPO} --state all --search "${n} in:title" --json number,url,state,headRefName,baseRefName  → pick the one whose headRefName == "feat/${n}" (else whose title references #${n}). prExists/prNumber/prUrl/prState from it (prExists = a PR whose head is feat/${n} exists in ANY state).
2. git fetch origin -q; git ls-remote --heads origin "feat/${n}" "wf/${n}/*"  → branchExists = origin/feat/${n} present; subBranches = the wf/${n}/* names found.
3. branchAhead = commits feat/${n} is ahead of base: git rev-list --count origin/${BASE}..origin/feat/${n} 2>/dev/null || echo 0.
Return ONLY the structured probe. This schema is tiny — ALWAYS emit it, never prose.`

// V2: finish a PR from an already-pushed branch (idempotent). Recovers the W2 #61 class.
const finishPrPrompt = (n) => `Branch feat/${n} for issue #${n} (${REPO}) is pushed to origin but has NO open PR yet. Idempotently ensure one exists. Fresh worktree.
1. gh pr list --repo ${REPO} --head feat/${n} --state open --json url → if one exists, return it (status='pr-opened').
2. Else: git fetch origin; git checkout feat/${n}; verify FULL GATES are green (${GATES}); fix only what blocks the gates.
3. gh pr create --base ${BASE} --head feat/${n}. PR body MUST include "## Decision trace" + "Closes #${n}".
4. Return SHORT result: status='pr-opened', branch='feat/${n}', prUrl, classification, rootCause. NO diff in the reply.

${COMMIT}

${GUARD}

${RULES}`

const reviewPrompt = (n, key, L, diff) => `Review the PR for issue #${n} (${REPO}) through the **${key}** lens ONLY.
Lens focus: ${L.focus}
Acceptance contract: recall gh issue view ${n} + ${SPEC}. The PR branch is feat/${n} — gh pr checkout ${n} or read the branch files. Be specific and skeptical; report only real, actionable findings (file + line + why + concrete suggestion). Severity ∈ {blocking,major,minor,nit}.
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

const fixPrompt = (n, confirmed, round) => `Apply confirmed review findings to PR branch feat/${n} of issue #${n} (${REPO}), round ${round}/2. Fresh isolated worktree.
1. git fetch origin && git checkout feat/${n} && git reset --hard origin/feat/${n}
2. Apply ONLY these confirmed findings (do not refactor beyond them):
${confirmed.map((f, i) => `  ${i + 1}. [${f.severity}] ${f.title} — ${f.detail}${f.file ? ' @' + f.file : ''}`).join('\n')}
3. ${GATES}
4. Commit and git push origin feat/${n}.
5. Return SHORT result: which finding ids you 'fixed', which remain 'residual', gatesPass. NO diff in the reply.

${COMMIT}

${GUARD}

${RULES}`

const diffPrompt = (n) => `Output ONLY the unified diff of PR branch feat/${n} (issue #${n}, ${REPO}). Run: gh pr diff ${n}. Return it verbatim in 'diff', truncated ~10000 chars. Do nothing else — no analysis, no edits.`

const deferPrompt = (n, residual) => `Create a DEFERRED follow-up issue for unresolved review findings on issue #${n} (${REPO}), as a SIBLING (shared parent), blocked-by #${n}. Run from the roxabi-forge repo working dir (NEVER cd into the plugin-cache dir; forge board has no size field — omit --size).
1. Resolve parent: P=$(gh api graphql -f query='query{repository(owner:"Roxabi",name:"roxabi-forge"){issue(number:${n}){parent{number}}}}' --jq '.data.repository.issue.parent.number // empty')
2. Create via triage CLI (version-resolved at runtime):
   ${TRIAGE} create --title "review residual: from #${n}" --body "**Origin:** #${n} (deferred after 2 fix rounds)\\n\\n${residual.map((r) => '- ' + r.title + ': ' + r.detail).join('\\n')}" --blocked-by "#${n}" ${'${P:+--parent "#$P"}'}
3. Return the new issue URL (and parent number if any).`

// ---------- resilience: retry agent() on transient failures ----------
const sleep = (ms) => new Promise((r) => { try { setTimeout(r, ms) } catch (_) { r() } })
async function tryAgent(prompt, opts, tries = 3) {
  let lastErr
  for (let attempt = 1; attempt <= tries; attempt++) {
    try { return await agent(prompt, opts) }
    catch (e) {
      lastErr = e
      if (attempt < tries) { log(`↻ ${opts.label || 'agent'} attempt ${attempt}/${tries} failed (${String((e && e.message) || e).slice(0, 90)}) → backoff`); await sleep(attempt * 20000) }
    }
  }
  throw lastErr
}
// V2: like tryAgent but NEVER throws — returns null on exhaustion. Use where a throw must not kill the slice.
async function softAgent(prompt, opts, tries = 3) {
  try { return await tryAgent(prompt, opts, tries) }
  catch (e) { log(`⤬ ${opts.label || 'agent'} gave up after ${tries} (${String((e && e.message) || e).slice(0, 90)}) → continue, will reconcile from git`); return null }
}
const probe = (n) => softAgent(probePrompt(n), { label: `probe:${n}`, phase: 'Reconcile', agentType: 'dev-core:frontend-dev', schema: PROBE_SCHEMA }, 4)

// ---------- impl + reconcile (the V2 heart) ----------
// Goal: end with a real PR for #n if one is achievable from ground truth, WITHOUT trusting self-report.
async function ensureImpl(n) {
  const size = SIZE[n] || 'S'
  let implMeta = null // {classification, rootCause} captured opportunistically
  let recovered = false

  // Phase 1 — DO the work. A throw here is non-fatal; we reconcile from git afterwards.
  try {
    if (size === 'S') {
      implMeta = await softAgent(implWholePrompt(n), { label: `impl:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })
    } else {
      const plan = await softAgent(planPrompt(n), { label: `plan:${n}`, phase: 'Plan', agentType: 'dev-core:frontend-dev', schema: PLAN_SCHEMA })
      const tasks = plan && plan.tasks && plan.tasks.length ? plan.tasks : null
      if (!tasks || tasks.length <= 1) {
        implMeta = await softAgent(implWholePrompt(n), { label: `impl:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })
      } else {
        log(`#${n}: ${tasks.length} disjoint tasks → parallel sub-impl`)
        await parallel(tasks.map((t) => () =>
          softAgent(subImplPrompt(n, t), { label: `impl:${n}:${t.id}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: { type: 'object', additionalProperties: false, required: ['status'], properties: { status: { type: 'string', enum: ['pushed', 'failed'] }, branch: { type: 'string' }, notes: { type: 'string' } } } })))
        // Trust git, not self-report: probe which wf/${n}/* actually landed on origin.
        const ps = await probe(n)
        const subBranches = (ps && ps.subBranches) || []
        if (subBranches.length) {
          implMeta = await softAgent(integratePrompt(n, subBranches), { label: `integrate:${n}`, phase: 'Implement', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })
        } else {
          log(`#${n}: no sub-branches reached origin after sub-impl`)
        }
      }
    }
  } catch (e) {
    log(`⚠ #${n} impl phase threw (${String((e && e.message) || e).slice(0, 120)}) → reconciling from git state`)
  }

  // Phase 2 — RECONCILE from ground truth (idempotent, no blind rerun).
  let p = await probe(n) || { prExists: false, branchExists: false }

  // (a) branch pushed with commits but no PR → finish the PR (W2 #61 class).
  if (!p.prExists && p.branchExists && (p.branchAhead || 0) > 0) {
    log(`#${n}: feat/${n} ahead ${p.branchAhead} but no PR → finish-PR`)
    implMeta = (await softAgent(finishPrPrompt(n), { label: `finish-pr:${n}`, phase: 'Reconcile', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })) || implMeta
    recovered = true
    p = await probe(n) || p
  }
  // (b) no branch but sub-branches exist → integrate was never completed → run it (W2 #64 / W3 #66 class).
  if (!p.prExists && !p.branchExists && (p.subBranches || []).length) {
    log(`#${n}: ${p.subBranches.length} sub-branch(es), no feat/${n} → integrate`)
    implMeta = (await softAgent(integratePrompt(n, p.subBranches), { label: `integrate-recover:${n}`, phase: 'Reconcile', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })) || implMeta
    recovered = true
    p = await probe(n) || p
    // a freshly-pushed feat/${n} may still lack its PR → one more finish-PR pass
    if (!p.prExists && p.branchExists && (p.branchAhead || 0) > 0) {
      implMeta = (await softAgent(finishPrPrompt(n), { label: `finish-pr2:${n}`, phase: 'Reconcile', isolation: 'worktree', agentType: 'dev-core:frontend-dev', schema: IMPL_SCHEMA })) || implMeta
      p = await probe(n) || p
    }
  }

  return { probe: p, implMeta: implMeta || {}, recovered }
}

// ---------- per-slice pipeline ----------
async function devIssue(n) {
  const { probe: p, implMeta, recovered } = await ensureImpl(n)

  if (!p.prExists) {
    // Could not reach a PR from ground truth — fail with a RECOVERABLE hint (no work silently lost).
    const hint = p.branchExists
      ? `origin/feat/${n} exists (ahead ${p.branchAhead || 0}) — run finish-PR / open the PR manually`
      : ((p.subBranches || []).length
        ? `sub-branches pushed: ${p.subBranches.join(', ')} — integrate them into feat/${n} manually`
        : `no remote artifacts for #${n}; inspect .claude/worktrees/*${n}* for uncommitted work, then commit/push`)
    return { issue: n, status: 'failed', stage: 'no-pr', recoverable: p.branchExists || (p.subBranches || []).length > 0, hint }
  }
  if (p.prState && p.prState !== 'OPEN') {
    return { issue: n, status: 'already-' + p.prState.toLowerCase(), prUrl: p.prUrl, recovered }
  }

  // Best-effort review/validate/fix — the PR EXISTS, so nothing here may discard it.
  let residual = []
  let deferred = null
  let reviewIncomplete = false
  try {
    let diff = ''
    const df = await softAgent(diffPrompt(n), { label: `diff:${n}`, phase: 'Implement', agentType: 'dev-core:frontend-dev', schema: DIFF_SCHEMA })
    diff = (df && df.diff) || ''

    const lensKeys = lensesFor(n)
    for (let round = 1; round <= 2; round++) {
      const reviews = await parallel(lensKeys.map((key) => () =>
        softAgent(reviewPrompt(n, key, LENS[key], diff), { label: `review:${n}:${key}:r${round}`, phase: 'Review', agentType: LENS[key].agent, schema: FINDINGS_SCHEMA })))
      const findings = reviews.filter(Boolean).flatMap((r) => (r.findings || []).map((f, i) => ({ ...f, id: `${r.lens}-${f.id || i}` })))
        .filter((f) => f.severity === 'blocking' || f.severity === 'major')
      if (!findings.length) { residual = []; break }

      const verdicts = await parallel(findings.map((f) => () =>
        parallel([1, 2].map((k) => () => softAgent(validatePrompt(n, f, diff, k), { label: `validate:${n}:${f.id}:${k}`, phase: 'Validate', schema: VERDICT_SCHEMA })))
          .then((votes) => ({ f, real: votes.filter(Boolean).some((v) => v.real) }))))
      const confirmed = verdicts.filter((v) => v.real).map((v) => v.f)
      if (!confirmed.length) { residual = []; break }

      log(`#${n} round ${round}: ${confirmed.length} confirmed finding(s) → fix`)
      const fix = await softAgent(fixPrompt(n, confirmed, round), { label: `fix:${n}:r${round}`, phase: 'Fix', isolation: 'worktree', agentType: 'dev-core:fixer', schema: FIX_SCHEMA })
      residual = (fix && fix.residual) || confirmed.map((f) => ({ title: f.title, detail: f.detail }))
      // refresh diff for the next round (best-effort)
      const df2 = await softAgent(diffPrompt(n), { label: `diff:${n}:r${round}`, phase: 'Fix', agentType: 'dev-core:frontend-dev', schema: DIFF_SCHEMA })
      diff = (df2 && df2.diff) || diff
      if (!residual.length) break
    }

    if (residual.length) {
      deferred = await softAgent(deferPrompt(n, residual), { label: `defer:${n}`, phase: 'Fix', agentType: 'dev-core:frontend-dev', schema: DEFER_SCHEMA })
    }
  } catch (e) {
    reviewIncomplete = true
    log(`⚠ #${n}: PR ${p.prUrl} is OPEN but review threw (${String((e && e.message) || e).slice(0, 120)}) → manual review`)
  }

  // If review couldn't complete OR we recovered the PR, flag it for the orchestrator's eyes.
  if (recovered) reviewIncomplete = true

  return {
    issue: n, status: 'pr-opened', prUrl: p.prUrl, prNumber: p.prNumber, branch: `feat/${n}`,
    classification: implMeta.classification, rootCause: implMeta.rootCause,
    residual, deferred, reviewIncomplete, recovered,
  }
}

// ---------- failure policy: ISOLATE-DEFER-CONTINUE (V2: failure carries a recovery hint) ----------
async function runIssue(n) {
  try {
    const r = await devIssue(n)
    if (!r || r.status === 'failed') {
      log(`⛔ #${n} FAILED stage=${(r && r.stage) || 'unknown'} recoverable=${(r && r.recoverable) || false} → ${(r && r.hint) || 'no hint'}`)
      return r || { issue: n, status: 'failed', stage: 'unknown' }
    }
    return r
  } catch (e) {
    log(`⛔ #${n} THREW (${String(e && e.message || e).slice(0, 200)}) → isolated, wave continues`)
    return { issue: n, status: 'failed', stage: 'exception', error: String(e && e.message || e).slice(0, 500) }
  }
}

// ---------- wave driver ----------
const out = []
for (let i = 0; i < wave.length; i += CAP) {
  const batch = wave.slice(i, i + CAP)
  log(`batch → #${batch.join(' #')}`)
  const res = await parallel(batch.map((n) => () => runIssue(n)))
  out.push(...res.filter(Boolean))
}

const failed = out.filter((r) => r.status === 'failed').map((r) => ({ issue: r.issue, stage: r.stage, recoverable: r.recoverable || false, hint: r.hint || null, error: r.error || null }))
const shipped = out.filter((r) => r.status === 'pr-opened')
const needsManualReview = shipped.filter((r) => r.reviewIncomplete).map((r) => ({ issue: r.issue, prUrl: r.prUrl, reason: r.recovered ? 'recovered from git — harness review did not run; read the PNG/diff yourself' : 'review loop incomplete — read the PNG/diff yourself' }))
log(failed.length ? `wave done: ${shipped.length} PR(s), ${failed.length} failed → #${failed.map((f) => f.issue).join(' #')}` : `wave done: ${shipped.length} PR(s), 0 failures`)
if (needsManualReview.length) log(`manual review needed: #${needsManualReview.map((m) => m.issue).join(' #')}`)

return {
  wave, version: 'v2',
  failed,
  needsManualReview,
  results: out.map((r) => ({
    issue: r.issue, status: r.status, prUrl: r.prUrl, classification: r.classification,
    residualCount: (r.residual || []).length, deferredUrl: r.deferred && r.deferred.issueUrl,
    reviewIncomplete: r.reviewIncomplete || false, recovered: r.recovered || false,
    stage: r.stage, recoverable: r.recoverable, hint: r.hint,
  })),
  orchestratorNotes: [
    'Apply the `reviewed` label ONLY after the `ci` check is green — repo allow_auto_merge=false, so labelling while ci is pending makes auto-merge.yml try to ENABLE the (forbidden) feature and strands the PR. If a green PR is stranded: gh pr merge <n> --squash (the Close-linked-issues job still fires).',
    'Every result with reviewIncomplete:true or recovered:true needs YOUR eyes: read artifacts/frames/epic-40/<n>/*.png + the diff before applying `reviewed`.',
    'A `failed` result carries {recoverable, hint} — follow the hint (finish-PR / integrate / inspect worktree); do NOT blind-rerun the wave. Two identical failures = inspect, never a third run.',
  ],
}
