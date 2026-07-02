---
title: "UI/UX Consolidation — best-of-5 into a Roxabi-owned capability"
status: decision-locked
date: 2026-06-14
supersedes_section: "§3 Forge-home argument superseded 2026-06-15 by dedicated roxabi-ui repo — see roxabi-ui-repo-brief.md"
---

# UI/UX Consolidation — best-of-5 into a Roxabi-owned capability

> Analysis 2026-06-14. Sources mined: `pbakaus/impeccable` (v3.6), `nutlope/hallmark`, `leonxlnx/taste-skill`, `GlamgarOnDiscord/uxui-AI-Prompt`, + Roxabi's own surface (Forge refs + `dev-core:frontend-dev`).
> Method: 2 multi-agent workflows (extraction ×6 + synthesis ×3), plus direct ground-truth reads of the highest-value files.
> Decision locked by Mickael: **absorb the best of all five into ONE Roxabi-owned capability; disable the third-party skills at cutover.** "Le meilleur de tous dans le nôtre."

---

## 1. Verdict

Two deliverables, one shared core:

1. **A consolidated `ui-design` skill** (single-skill / multi-verb, modeled on impeccable's architecture) — Roxabi-owned, invoked both standalone and by the `frontend-dev` agent. Replaces impeccable + the inert external skill refs.
2. **Forge reference upgrades** — OKLCH tokens, hardened anti-patterns, motion doctrine, +10 aesthetic presets, an emit-time slop gate.

Both consume **one shared `design-doctrine.md` SSoT** (bans + slop-test + OKLCH color strategy + typography + motion + dials). No rule lives in two places.

**Home: REOPENED 2026-06-15 — leaning toward a dedicated `roxabi-ui` repo/plugin** (see §3bis Overlap analysis). The design capability serves real React apps (via `frontend-dev`), not only Forge artifacts, so binding it to the artifact-generator is the wrong coupling. Forge's `references/` overlaps the doctrine ~40-50% — but that's overlap to EXTRACT into a shared home, not to co-locate. Forge becomes a CONSUMER of the doctrine, same as the agent.

---

## 2. The five sources — what each owns, what we take

| Source | Core thesis | What we absorb | Verdict |
|---|---|---|---|
| **impeccable** (pbakaus, v3.6) | Production-grade craft skill: 1 skill, 23 verbs, register routing, machine-enforced anti-slop | Architecture (1-skill-N-verbs), **absolute-bans**, **2-altitude slop test**, **OKLCH color-strategy** (Restrained/Committed/Full/Drenched), cream/sand-2026 ban, typography/motion doctrine, brand-vs-product register, **`detect` CLI engine** (40 rules), prose denylist | **Backbone.** Take the most. |
| **hallmark** (Nutlope) | Anti-AI-slop, single-file HTML; *structural* variety not just visual | 21 **macrostructures** + diversification log, **58-gate slop test**, **6-axis pre-emit self-critique**, OKLCH `tokens.css` vocabulary (12 roles), 8-state component discipline, GPU-only motion | **Closest Forge analog.** High. |
| **taste-skill** (leonxlnx) | Anti-default discipline + "AI laziness" research | **3 Dials** (variance/motion/density), Design Read protocol, **concrete banned hex/font families**, per-style aesthetics (brutalist/minimalist/soft), anti-laziness prompt patterns | Medium-high. Dials + bans. |
| **uxui-AI-Prompt** (Glamgar) | Vague brief → verifiable contract before code | **7 brand presets** (linear/vercel/raycast/stripe/notion/superhuman/vs-code), **Style Auto-Router** (7 moods), **Evidence Gate** (7-field pre-code JSON), Self-Check, motion DNA schema | Presets → Forge. Gate → skill. |
| **design** (knowledge-work-plugins, Anthropic) | Design **ops/review** skills (Cowork/CC), standalone + optional Figma MCP | **WCAG 2.1 AA checklist** (criterion IDs + contrast/keyboard/SR output tables) → `audit` verb; **design-critique** 5-dim framework + output template → `critique` verb; **ux-copy** patterns (CTA/error/empty/confirm) + alt-table → copywriting; **design-handoff** → NEW verb; design-system audit; (research-synthesis/user-research = P2) | Review/ops layer. Absorb the frameworks, drop MCP scaffolding. |
| **Roxabi existing** | Forge refs + frontend-dev agent | Keep: **Glance/Scan/Deep IA**, anti-patterns codex w/ named exceptions, lane/diagram tokens, junior-designer 4-pass, brand-book schema, aesthetic CSS presets | Foundation to build on. |

### Real gaps the externals fill (from the map agent)
- No OKLCH anywhere (all hex/rgba) · `roxabi.css` is the warm-amber AI-default impeccable warns against
- No two-altitude slop test, no color-strategy commitment axis
- No positive **motion doctrine** (anti-patterns.md bans entrance animation outright; no easing/duration/reduced-motion system)
- No typography constraints in the **agent** path; `frontend-dev` skills= refs are **inert** (neither `frontend-design` nor `ui-ux-pro-max` is enabled)
- No copy/UX-copy doctrine · no machine-enforced output gate

---

## 3. Recommended architecture

```
roxabi-forge/plugins/forge/
├── references/
│   ├── design-doctrine.md        ← NEW · the SSoT (§ below) · read on-demand
│   ├── tokens.md                 ← EDIT · OKLCH migration + easing/duration tokens
│   ├── anti-patterns.md          ← EDIT · + slop gates, cream/sand ban, prose denylist
│   ├── design-workflow.md        ← EDIT · + macrostructure pass-0 + pre-emit critique + detect gate
│   ├── design-styles.md          ← EDIT · + Style Auto-Router + register + dials
│   ├── motion.md                 ← NEW · GPU-only, 3 easings, 3 durations, reduced-motion
│   └── aesthetics/               ← +10 presets (7 uxui brand + 3 taste styles), fix lyra-v2 Inter
├── skills/
│   └── ui-design/                ← NEW · single-skill, multi-verb (the consolidated capability)
│       ├── SKILL.md              ← setup · register · dials · auto-router · evidence-gate · verb dispatch
│       └── references/<verb>.md  ← craft/audit/critique/palette/typeset/animate/harden/...
└── scripts/
    └── detect-slop.{sh,py}       ← NEW · wraps `npx impeccable detect` (advisory gate)

roxabi-plugins/plugins/dev-core/agents/
└── frontend-dev.md               ← EDIT line 19 · skills: forge:ui-design, context7-plugin:docs
```

**Why Forge-home, not a new `roxabi-ui` plugin or a dev-core skill:**
- The doctrine SSoT must be readable by both the skill and the Forge skills *at runtime*. Independently-installed plugins don't share a `CLAUDE_PLUGIN_ROOT`, so a dev-core skill reading a forge file (`../../references/...`) is fragile. Same root = robust.
- Forge already IS the design repo. Adding a `ui-design` skill there is natural; it just isn't Forge-artifact-specific.
- Cross-plugin skill references work (`context7-plugin:docs` proves it), so the dev-core agent wiring is clean.

---

## 4. The shared `design-doctrine.md` SSoT (12 sections)

| § | Section | Distilled from |
|---|---|---|
| 1 | OKLCH color science + 12 roles + strategy axis (Restrained/Committed/Full/Drenched) + cream/sand-2026 ban | impeccable + hallmark tokens.css |
| 2 | Slop detection — machine gates (40 detect rules) + 6-axis pre-emit self-critique (1–5, ≥3.5) | impeccable detect + hallmark 58-gate |
| 3 | Typography — banned fonts (Inter/Roboto/…), 2+1 rule, 65–75ch, clamp ≤6rem, ≥-0.04em, no italic headings, no Google `@import` in Forge | impeccable + hallmark base.css |
| 4 | Motion — GPU-only, 3 easings, 3 durations, reduced-motion mandatory, reveal-on-already-visible, no entrance-on-load | hallmark motion + impeccable animate |
| 5 | 3 Dials — variance/motion/density (baseline 8/6/4) | taste-skill |
| 6 | Style Auto-Router (7 moods) + 21 macrostructures + diversification | uxui + hallmark |
| 7 | Design Contract / Evidence Gate (pre-code JSON) + merged preflight | uxui + taste |
| 8 | 4-pass workflow (assumptions→build→polish→verify) | Roxabi (keep) |
| 9 | Register routing (brand IS product / product SERVES product) | impeccable |
| 10 | **A11y isolation** — WCAG lives ONLY in the `audit` verb, never in craft prompts (mixing it triggers safe/underdesigned output) | impeccable |
| 11 | Anti-laziness — no-placeholder/full-output protocol, AI-preamble ban | taste-skill research |
| 12 | 3-layer IA (Glance/Scan/Deep) + `overflow-x:clip` | Roxabi (keep) |

---

## 5. Cutover plan (corrected ground truth)

**What's actually enabled:**
- `impeccable@impeccable: true` in **`~/projects/.claude/settings.json`** (project scope) — THIS enables impeccable.
- `ui-ux-pro-max-skill` is **only a known marketplace** (global `extraKnownMarketplaces`), **not enabled** anywhere → its skills aren't even loaded this session. Nothing to disable as a plugin.
- `design@knowledge-work-plugins` IS enabled (the `design:*` skills) — decide separately whether to keep.

**Disable sequence (P0 — only after the capability checklist is green):**
1. `design-doctrine.md` SSoT written + committed
2. `ui-design` skill SKILL.md written, committed, plugin updated/cache-synced
3. `frontend-dev.md` rewired to `forge:ui-design`
4. `detect-slop` gate wired
5. No remaining `skills=` line references impeccable
6. **Then** disable: prefer `claude plugin` CLI (or `/plugin`) over hand-editing — set `impeccable@impeccable` false / remove from `~/projects/.claude/settings.json` enabledPlugins. Verify via the available-skills list, not the file.
7. Optional cleanup: remove `impeccable` + `ui-ux-pro-max-skill` from global `extraKnownMarketplaces`.

**Lost by disabling impeccable (decide retention):**
- `npx impeccable detect` CLI → **retain standalone** as the Forge gate (npm pkg stays installable; node required, M₁/M₂ have it).
- `live` browser variant mode (pick elements in browser → variants) → no Roxabi equivalent. Lost unless we keep the CLI's `live` too.
- PostToolUse auto-detect hook (fires on UI edits) → replaced by emit-time / pre-commit gate (commit-time, not edit-time).

---

## 6. Decisions

1. **Skill home** — ✅ **dedicated repo `Roxabi/roxabi-ui`** (the design brain). Forge + `frontend-dev` consume it. See `roxabi-ui-repo-brief.md`.
2. **Scope of v1** — ✅ **complete** verb set (MVP-P0 = craft/palette/critique/audit/detect, then P1/P2).
3. **`detect` engine** — ⏳ open: port to Python (no node dep) vs `npx`/node as-is. Decide at P0.
4. **`design` knowledge-work plugin** — ✅ **absorb** (WCAG checklist → `audit`, critique framework → `critique`, ux-copy → `clarify`, handoff → new verb); **disable `design@knowledge-work-plugins`** at cutover (keep brand-voice/marketing/product-management).
5. **Forge OKLCH migration** — ⏳ reco: migrate **with hex fallback** (CSS), keep old presets until artifacts regenerated. Confirm.

---

## 7. Phasing (this is an epic, not a one-shot)

- **P0 (foundation)**: `design-doctrine.md` SSoT · OKLCH `tokens.md` · hardened `anti-patterns.md` · `ui-design` SKILL.md core · rewire `frontend-dev`
- **P1 (depth)**: verb reference files · `motion.md` · 10 presets · macrostructure pass-0 + pre-emit critique in workflow · `detect-slop` gate
- **P2 (cutover + polish)**: disable impeccable · marketplace cleanup · lyra-v2 Inter fix · doc-sync

**Full per-file action manifest + risks**: in the two synthesis dossiers (workflow `wdtpqz2xv` output).
