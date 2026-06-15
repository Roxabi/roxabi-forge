# Postmortem — Epic #40 (forge-diagram fd-engine)

> Date: 2026-06-03 · staging @ `b73b2f4` · 4 waves, 8 slices, ~16M tokens · author: orchestrator session

## Headline

**The implementation was never the problem. 100% of failures were in the harness's coordination/reporting layer, not the generated code.** Every diagram render passed visual QA at lyra-grade on first or second look. The impl subagents did excellent work; everything that broke was plumbing.

## What broke

| Slice | Harness verdict | Reality | Root cause |
|---|---|---|---|
| #60, #62, #63 | success | success | — |
| #61 | failed | **PR #71 was perfect** | post-PR review step threw → discarded a green PR |
| #64, #66 | failed | impl sat **uncommitted in worktree** | integrate threw before commit/push |
| #65 | failed→reviewIncomplete | PR fine | same as #61 (post-patch: survived) |
| #67 | failed | agent did the work, **truncated before PR** | output cap + spec under-scope |

Clean-through-harness rate: **3/8 (38%)**. Manual intervention: **5/8**.

## Root causes (ranked)

1. **StructuredOutput refusal → fatal throw** (dominant). Non-parallel `tryAgent` calls (diff/fix/defer/integrate) threw after agents ended in prose instead of calling the tool; the catch marked the whole slice failed — *even when its PR was already open*. The harness assumed clean-success xor clean-failure; the messy middle (work done, reporting step flaked) had no path.
2. **No idempotency / recovery in integrate.** No "does a PR already exist / is there committed worktree work?" check before declaring failure.
3. **auto-merge timing race.** Repo `allow_auto_merge:false` → `gh pr merge --auto` only immediate-merges when CLEAN; labeling `reviewed` before `ci` green tried to *enable* the (forbidden) feature → stranded #70.
4. **Spec under-scoped #67.** Scoped to forge-chart; deletion actually broke forge-guide/forge-slides routing. No "grep consumers" pre-flight.
5. **Agent output truncation.** The #67 recovery agent hit an output cap twice before its structured return — undetectable from the result; only the worktree state revealed the work was done.

## What went right

- **Worktree isolation = recoverability.** Failed slices left uncommitted work on disk → #64/#66 recovered for ~50–115k tokens each instead of ~3M reruns.
- **Disjoint footprints held** — zero merge conflicts across parallel slices; glob-bundler avoided shared-registry edits as designed.
- **Guard never violated**; ISOLATE-DEFER-CONTINUE kept failures from cascade-stalling waves.
- **The mid-flight patch worked** — W3 #65 survived the exact throw that killed W2 #61. Validated in-run.
- **Visual lens earned its keep** — but as confirmation, not defect-catching; impl quality was uniformly high.

## My mistakes

- **Burned ~3M tokens re-running [61,64] before diagnosing determinism.** Two identical `parallel[4]` failures should have triggered inspect-first immediately, not a blind retry. New rule (saved): 2 identical failures → stop & inspect, never a 3rd wave.
- **Over-trusted the "0 human gate" framing.** In practice the run needed continuous orchestrator judgment (recovery, merge mechanics, scope). The autonomy was in the *impl*, never the *coordination*.

## Fix list (if this harness runs again)

1. Make integrate/sub-impl best-effort like review now is: on throw, check for an open PR or committed worktree branch before failing.
2. Cut StructuredOutput refusals: shrink review/fix prompt payloads (diff already deferred; integrate prompts are the suspect), or detect prose-ending and re-prompt tool-only.
3. Pre-flight assert `allow_auto_merge` **or** bake "ci-green-then-label" into the runbook (done in memory).
4. Deletion slices: grep consumers across **all** skills during `/spec`, not at execution.
5. Treat a subagent that returns without its declared schema as "inspect the worktree," not "failed."

## Efficiency

~16M tokens / 8 slices ≈ 2M/slice. Recovery-by-agent (~50–115k) beat wave-rerun (~3M) by ~30×. The cheapest path on a flaked-but-PR-open slice was always *me reviewing the existing PR* — near zero.

## Execution trace

| Wave | Slices | Outcome |
|---|---|---|
| W1 | #60 | clean → PR #68 |
| W2 | #61,62,63,64 | #62/#63 clean (#69/#70); #61 PR-survived-review-throw (#71); #64 worktree-recovered (#72) |
| W3 | #65,66 | #65 reviewIncomplete→manual (#73); #66 worktree-recovered (#74) |
| W4 | #67 | scope-expanded → full cross-skill migration (#75) |

## Latent bugs found (off-epic)

- `issue-triage` `set --status Done` rejects a status it lists as valid (board option-mapping gap; same family as "forge board has no Size field").
- commit-msg hook enforces 100-char header; no pre-warn — first #67 commit bounced at 101.

**Net:** epic shipped, quality high, but the harness needs idempotent recovery before it's truly hands-off. The value/cost ratio came from worktree isolation + manual recovery, not from the autonomous loop completing cleanly.

## See also

- Spec: `artifacts/specs/epic-40-58-js-engine-spec.md`
- Handoff/runbook: `artifacts/plans/epic-40-58-RECAP.md`
- Harness (patched `b73b2f4`): `artifacts/plans/epic-40-58-wave.mjs`
- Memories: `epic-40-wave-harness-postpr-throw`, `epic-40-forge-auto-merge-timing`
