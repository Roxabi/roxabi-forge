---
title: "roxabi-ui — repo brief"
status: brief
date: 2026-06-15
migration: "Move to Roxabi/roxabi-ui on P0 bootstrap"
companion: uiux-consolidation.md
---

# roxabi-ui — repo brief

> Decided 2026-06-15: dedicated repo `Roxabi/roxabi-ui` = the design BRAIN. Owns the doctrine SSoT + the consolidated `ui` skill + preset sources + the slop-detect gate. Forge and the `frontend-dev` agent consume it. Companion: `uiux-consolidation.md` (the why).
> This is a BRIEF — no code yet. Open naming/scope sub-decisions flagged inline.

---

## 1. Repo shape

New repo `Roxabi/roxabi-ui` (private, Roxabi org), bootstrapped like every Roxabi plugin repo (dev-core `stack.yml`, lefthook, release-please, marketplace manifest). One marketplace, one plugin.

```
roxabi-ui/
├── .claude-plugin/
│   ├── marketplace.json          # marketplace: roxabi-ui-marketplace · lists plugin "ui"
│   └── plugin.json               # (mirrored version, like roxabi-forge)
├── plugins/
│   └── ui/
│       ├── .claude-plugin/plugin.json     # name: ui · version
│       ├── skills/
│       │   └── ui/
│       │       ├── SKILL.md                # single skill · verb router (impeccable model)
│       │       └── references/
│       │           ├── design-doctrine.md  # ★ THE SSoT (12 §) — the vendored-to-Forge file
│       │           ├── <verb>.md ×N         # one per verb (craft, audit, critique, …)
│       │           ├── style-recipes.md     # 7 moods + dial defaults
│       │           ├── macrostructures.md   # 21 page-shapes + diversification
│       │           ├── typography.md · motion.md · copywriting.md · palette.md
│       │           └── aesthetics/          # preset CSS — 2 target variants (see §5)
│       ├── scripts/
│       │   ├── detect-slop.{mjs|py}        # the slop scanner (decision #3)
│       │   └── palette.{mjs|py}            # OKLCH seed→palette (port of impeccable)
│       └── README.md
├── docs/ · CLAUDE.md · .claude/stack.yml · lefthook.yml · LICENSE
```

**Naming (confirm):** plugin `ui`, skill `ui` → invocation `/ui craft`, `/ui audit`. Agent ref `ui:ui`. Alt: `/design` (collides w/ knowledge-work `design`) or `/ux`. **Reco: `/ui`.**

**Sub-decision — standalone repo vs new plugin in `roxabi-plugins`:** you said dedicated repo → standalone. Lower-overhead alt = a `ui` plugin inside the existing `roxabi-plugins` monorepo (shares CI/marketplace, co-located with the `frontend-dev` agent it feeds). Plugin structure is identical either way; only the repo/marketplace wrapper differs. Flagging once; default = standalone per your call.

---

## 2. The `ui` skill — verbs (complete set)

Single-skill / multi-verb (impeccable's anti-`/`-menu-pollution model). Setup runs once (read PRODUCT.md/DESIGN.md, register brand|product, dials, load verb ref).

| Verb | Cat | MVP | Distilled from |
|---|---|---|---|
| `craft` | build | **P0** | impeccable craft + uxui evidence-gate + taste design-read/dials + hallmark macrostructure |
| `shape` | build | P1 | impeccable shape (plan UX before code) |
| `palette` | build | **P0** | impeccable palette.mjs (OKLCH seed→palette) + hallmark tokens |
| `init` / `document` | setup | P1 | impeccable (PRODUCT.md/DESIGN.md capture) |
| `critique` | eval | **P0** | impeccable critique + hallmark 6-axis self-critique + **design `critique` 5-dim framework + output template** |
| `audit` | eval | **P0** | impeccable audit + **`accessibility-review` WCAG 2.1 AA checklist** + `detect-slop` gate · a11y ISOLATED here (doctrine §10) |
| `typeset` | enhance | P1 | impeccable typeset + doctrine typography |
| `animate` | enhance | P1 | impeccable animate + hallmark motion + uxui motion-DNA |
| `colorize` / `layout` | enhance | P1 | impeccable |
| `bolder` / `quieter` | refine | P1 | impeccable |
| `polish` | refine | P1 | impeccable polish |
| `harden` | refine | P1 | impeccable harden (errors/i18n/edge) |
| `clarify` | fix | P1 | impeccable clarify + **`ux-copy` patterns** + doctrine copywriting/prose-denylist |
| `adapt` | fix | P1 | impeccable adapt (responsive) |
| `handoff` | output | P1 | **`design-handoff`** (NEW — none of the other sources have it) |
| `detect` | gate | **P0** | the slop scanner (objective gate) |
| `research` / `synthesize` | research | P2 | design `user-research` / `research-synthesis` |

MVP-P0 = `craft · palette · critique · audit · detect`. Rest = P1/P2.

---

## 3. Doctrine SSoT — `design-doctrine.md` (12 §)

The single shared file. Both the skill (same root) and Forge (vendored copy) consume it.

| § | Section | Source |
|---|---|---|
|1| OKLCH color science · 12 roles · strategy axis (Restrained/Committed/Full/Drenched) · cream/sand-2026 ban | impeccable + hallmark |
|2| Slop detection — 40 machine gates + 6-axis pre-emit self-critique (≥3.5) | impeccable detect + hallmark |
|3| Typography — banned fonts · 2+1 · 65-75ch · clamp ≤6rem · ≥-0.04em · no italic headings | impeccable + hallmark |
|4| Motion — GPU-only · 3 easings · 3 durations · reduced-motion · no entrance-on-load | hallmark + impeccable |
|5| 3 Dials — variance/motion/density (8/6/4) | taste-skill |
|6| Style Auto-Router (7 moods) + 21 macrostructures + diversification | uxui + hallmark |
|7| Design Contract / Evidence Gate (pre-code JSON) + merged preflight | uxui + taste |
|8| 4-pass workflow | Roxabi (keep) |
|9| Register routing (brand IS product / product SERVES product) | impeccable |
|10| **A11y isolation** — WCAG only in `audit`, never in craft prompts | impeccable |
|11| Anti-laziness — no-placeholder / full-output / AI-preamble ban | taste-skill |
|12| 3-layer IA (Glance/Scan/Deep) + `overflow-x:clip` | Roxabi (keep) |

---

## 4. What moves out of Forge, what stays

| Forge `references/` today | Disposition |
|---|---|
| `design-styles.md`, `anti-patterns.md`, `design-workflow.md` | → **extract** into doctrine (roxabi-ui); Forge keeps a thin Forge-mode addendum |
| `tokens.md`, `output-ux.md` | **split** — base color/type/IA → doctrine; `--lane-*`/`--diag-*`/`--arch-*` diagram tokens stay Forge |
| `design-phase-two-track.md`, `brand-book-schema.md` | stay Forge (forge.yml mechanism is Forge-specific) |
| `aesthetics/*.css` | stay Forge (file://-safe inline format) — but generated from roxabi-ui preset sources (§5) |
| `slide-templates/`, `gallery-templates/`, `shells/`, `device-frames/`, `showcases/` | stay Forge (artifact machinery) |
| 8 `forge-*` skills, `serve.py`, Makefile, runtime | stay Forge |

Forge becomes: **artifact factory that consumes the doctrine + adds file://-safe templating.** Its design-workflow Pass-4 runs `detect-slop`.

---

## 5. Two preset target-variants (the format split)

The 7 brand presets (linear/vercel/raycast/stripe/notion/superhuman/vs-code) + 3 taste styles (brutalist/minimalist/soft) exist as ONE source-of-truth in roxabi-ui, emitted to two targets:

- **`forge` target** — plain CSS custom props, system-font stacks, zero CDN, inline-safe → Forge `aesthetics/*.css`.
- **`app` target** — Tailwind `@theme` / token JSON for real React apps via `frontend-dev`.

Source = OKLCH token definitions per preset; a small generator emits both. (Avoids the Tailwind-class-in-Forge problem the synthesis flagged.)

---

## 6. Vendor-sync — how Forge reads the doctrine

Cross-plugin runtime file access is not reliable (each plugin has its own `CLAUDE_PLUGIN_ROOT`). So:

- **MVP (reco): vendor-sync.** `roxabi-forge/scripts/sync-doctrine.sh` fetches the pinned `design-doctrine.md` (+ preset sources) from `roxabi-ui@<sha>` into `roxabi-forge/plugins/forge/references/design-doctrine.vendored.md` with a `GENERATED — synced from roxabi-ui@<sha>` header. A lefthook/CI check fails on drift. Proven pattern (impeccable syncs its engine to 5 places).
- **Later option:** Forge skills invoke `ui:ui` for the design pass (skill-to-skill), dropping the vendored copy.

The `frontend-dev` agent has no such problem — it references the skill directly (`skills: ui:ui`), which resolves at runtime.

---

## 7. Cutover (updated — corrected ground truth)

Disable AFTER the capability checklist is green (doctrine written · `ui` skill shipped · `frontend-dev` rewired · `detect-slop` wired · no `skills=` references impeccable).

| Plugin | Enabled where | Action |
|---|---|---|
| `impeccable@impeccable` | `~/projects/.claude/settings.json` (project scope) `enabledPlugins` | disable (after absorb) |
| `design@knowledge-work-plugins` | same file, project scope `enabledPlugins` | disable (after absorbing critique/a11y/ux-copy/handoff frameworks) — **keep** brand-voice/marketing/product-management |
| `ui-ux-pro-max-skill` | not enabled anywhere (marketplace-only) | nothing to disable; optional global marketplace cleanup |
| `ui@roxabi-ui-marketplace` | — | **enable** (+ register marketplace in `extraKnownMarketplaces`) |

Disable via `claude plugin` / `/plugin`, verify by the available-skills list (not by hand-editing JSON blindly).

**Lost by disabling impeccable:** `npx impeccable detect` → retained standalone as our gate; `live` browser variant mode → no replacement (accept); PostToolUse auto-detect hook → replaced by emit/pre-commit gate.

Rewire `frontend-dev.md` line 19: `skills: ui:ui, context7-plugin:docs` (drops the already-inert `frontend-design` + `ui-ux-pro-max`).

---

## 8. Phasing

- **P0** — bootstrap repo · `design-doctrine.md` · `palette` + `detect-slop` scripts · `ui` SKILL.md with `craft/palette/critique/audit/detect` · OKLCH preset sources (forge target) · rewire `frontend-dev`
- **P1** — remaining verbs (typeset/animate/colorize/layout/bolder/quieter/polish/harden/clarify/adapt/handoff/shape/init/document) · macrostructures · app-target presets · Forge vendor-sync + Pass-4 gate · Forge `references/` split
- **P2** — disable impeccable + design plugins · `research/synthesize` verbs · marketplace cleanup · doc-sync

Build via multi-agent workflow (worktree-isolated per-file groups), one phase at a time.
