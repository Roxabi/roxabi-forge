# gmdiagram Delta Analysis — Forge Gaps

**Date:** 2026-04-14
**Author:** Mickael + Claude
**Status:** Analysis complete → 3 issues opened (A/B/C)
**Scope:** Delta only — gmdiagram findings not covered by the 2026-04-12 competitor audit.

## Context

Three repos re-scanned vs `plugins/forge/`:

| Repo | New vs 2026-04-12? | Outcome |
|---|---|---|
| `ZeroZ-lab/gmdiagram` | **yes** — not in prior audit | this document |
| `Cocoon-AI/architecture-diagram-generator` | no — already audited | referenced only |
| `yizhiyanhua-ai/fireworks-tech-graph` | no — already audited, tracked in #10 | referenced only |

The 2026-04-12 audit ([`2026-04-12-competitor-skills-analysis.md`](./2026-04-12-competitor-skills-analysis.md)) + issue [#10](https://github.com/Roxabi/roxabi-forge/issues/10) cover architecture-diagram-generator + fireworks-tech-graph. Auto-layout + JSON IR were evaluated and deferred in closed issue [#7](https://github.com/Roxabi/roxabi-forge/issues/7).

## gmdiagram in one paragraph

Claude Code skill pair (`gm-architecture` + `gm-data-chart`) producing single-file HTML diagrams. 17 diagram/chart types (8 architecture, 9 data-chart), 12 visual styles, mandatory two-step pipeline (JSON schema extract → HTML render), explicit per-skill Quality Checklist (14 items), pixel-exact layout constants (`LAYER_H_BADGE=116`, `LAYER_H_SIMPLE=101`, `gap=50`), `export.sh` for PNG/PDF via `resvg`, and audit reports (`SKILL_OPTIMIZATION_REPORT.md`, `EXAMPLES_AUDIT_REPORT.md`) as repeatable QA artifacts.

## Delta findings (not covered elsewhere)

### D1 — Quality Checklist per skill

**Source:** `external_repos/gmdiagram/gm-architecture/skills/gm-architecture/SKILL.md:456-473`

14 pre-flight items run at Deliver time (foreignObject xmlns, layer gaps, CSS class names, JSON schema conformance, connection routing, viewBox fit, legend/title accuracy, escaping). Explicit, checkable, bounded.

**Forge gap:** anti-patterns exist scattered; no consolidated Deliver-phase checklist. Sub-agents ship without pre-flight verification.

**Lift target:** append to `forge-chart/SKILL.md` § Deliver as a mandatory gate.

### D2 — Pixel-exact layout constants

**Source:** `external_repos/gmdiagram/gm-architecture/CLAUDE.md:108`

`LAYER_H_BADGE=116px`, `LAYER_H_SIMPLE=101px`, `gap=50px`. Prevents silent drift (overlap, misalignment).

**Forge gap:** `shape-vocabulary.md` has no pixel constants; fgraph uses 0..100 relative coords but layered/deployment-tiers templates have no enforced row heights.

**Lift target:** new `references/graph-layout-rules.md` or extend `shape-vocabulary.md`.

### D3 — Missing diagram types

**Source:** `external_repos/gmdiagram/gm-architecture/skills/gm-architecture/assets/schema-*.json`, `gm-data-chart/skills/gm-data-chart/assets/schema-*.json`

gmdiagram covers 17 types; forge covers ~6 fgraph + Mermaid. Missing:

- **Architecture:** Gantt, UML class, ER
- **Data-chart:** pie, radar, funnel, bubble, scatter

**Forge gap:** `forge-chart` is topology-centric, not data-centric.

**Lift target:** new templates + schemas in `references/graph-templates/` or a data-chart sub-tree.

### D4 — PNG/PDF export

**Source:** `external_repos/gmdiagram/gm-architecture/skills/gm-architecture/scripts/export.sh`

Node-based `@resvg/resvg-js` + `rsvg-convert` → PNG/PDF from HTML output.

**Forge gap:** forge outputs are HTML only. Embed in slides / docs requires manual screenshot.

**Lift target:** `plugins/forge/scripts/export.sh` as optional post-generation step.

### D5 — Audit report template

**Source:** `external_repos/gmdiagram/SKILL_OPTIMIZATION_REPORT.md`, `EXAMPLES_AUDIT_REPORT.md`

Systematic QA artifact: coverage (all types represented?), metadata consistency (version sync?), file naming (kebab-case?), P0/P1/P2 issue list.

**Forge gap:** no audit template; quality reviews are ad-hoc.

**Lift target:** `artifacts/analyses/AUDIT-TEMPLATE.md` for periodic forge health checks.

## Already-covered items (reference)

| Item | Tracked in |
|---|---|
| `>-` block scalar frontmatter | [#10](https://github.com/Roxabi/roxabi-forge/issues/10) |
| Fixtures + regression | [#10](https://github.com/Roxabi/roxabi-forge/issues/10) |
| SKILL.md compression | [#10](https://github.com/Roxabi/roxabi-forge/issues/10) |
| Semantic color palette | `2026-04-12-competitor-skills-analysis.md` |
| Summary info cards | `2026-04-12-competitor-skills-analysis.md` |
| Boundary/cluster groups | `2026-04-12-competitor-skills-analysis.md` |
| AI domain patterns | `2026-04-12-competitor-skills-analysis.md` |
| SVG validator | `2026-04-12-competitor-skills-analysis.md` |
| Auto-layout (Python generator) | [#7 CLOSED — DEFER](https://github.com/Roxabi/roxabi-forge/issues/7) |
| JSON IR two-step | [#7 CLOSED — DEFER](https://github.com/Roxabi/roxabi-forge/issues/7) |

gmdiagram's two-step JSON → render pattern **reinforces** the #7 DEFER rationale with a new data point: gmdiagram built it, and the SKILL.md is 500+ lines heavy. Keep deferred unless multi-agent composition becomes a real need.

## Proposed issues

| Issue | Scope | Items |
|---|---|---|
| **A** | Tier-1 lift bundle (gmdiagram + architecture-diagram-generator + fireworks validator) — small, safe, one sprint | D1 + D2 + remaining Tier-1 from 2026-04-12 analysis (semantic palette, summary cards, boundary groups, SVG validator, domain patterns) |
| **B** | Missing diagram types | D3 |
| **C** | PNG/PDF export | D4 |

D5 (audit report template) deferred — write it lazily first time we run a real audit.
