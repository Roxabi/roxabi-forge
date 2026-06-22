# Graph Templates

Node-edge diagrams for the `forge-chart` and `forge-guide` skills. Companion to
`gallery-templates/` (image grids).

## fd-engine first (default for node-edge topology)

**Dense or interactive diagrams** (≥ 7 nodes, use-cases, zones, spotlight) → **do not copy templates here**.

1. Write a descriptor JSON (`type`: `architecture`, `hub-spoke`)
2. Generate: `python3 scripts/gen-fd.py --in descriptor.json --out diagram.html`
3. Validate: `python3 scripts/validate-fd.py --html diagram.html` (exit 0 required)

Quality bar: `examples/fd-architecture.html`, fixture `forge-chart/fixtures/lyra-stack-v2.json`. Shell: `fd-shell.html` + `fd-bootstrap.js` (assembled by `gen-fd.py` — **do not hand-copy** `examples/fd-*.html`).

| fd-engine type | Example | Layout |
|---|---|---|
| `architecture` / `hub-spoke` | `examples/fd-architecture.html` | declarative `x`/`y` 0..100 |

## fgraph static (legacy — ≤ 6 nodes, print-safe, no JS)

**Lift, don't rebuild** for small static diagrams only. Copy the template, fill
`{{PLACEHOLDERS}}`, assign `--x`/`--y`, inline `fgraph-base.css`. No runtime JS.
Do **not** use fgraph for Lyra-scale architecture — use fd-engine above.

> **⚠ Status — these are *propositions*, not the default path.** As of forge-chart 0.4.0
> the generator's **default** is the **fd-engine premium path** (`forge-chart/SKILL.md §
> fd-engine diagram types`): DOM-measured bezier edges, premium cards, glow / edge-flow /
> per-node icons. Most static templates below are **propositions to consider** — reach for
> them for **print / PDF / no-JS** output or an explicit static-look request, or as a *layout
> hint* you then render through an fd-engine descriptor.
>
> - **First-class engine types** (premium default): `architecture` · `hub-spoke`. Architecture absorbs radial-hub / system-architecture / layered / machine-clusters / linear-flow / dual-cluster / radial-ring. Other engine types (`flowchart`, `state`, `class`, `er`, `sequence`, `gantt`, `pie`, `xychart`) were retired 2026-06-22 (auto-layout elk + standalone chart types — premium-only purge) pending a premium-first rebuild.
> - **Kept native** (no engine equivalent): **`lane-swim`** (swimlane — preferred for multi-actor pipelines & lifecycle walkthroughs) · **`dep-graph`** (data-driven, `gen-deps.py`) · **`funnel`** (explainer component) · **`radial-hub`** · **`linear-flow`** · **`dual-cluster`** · **`radial-ring`** · **`layered`** · **`machine-clusters`** · **`deployment-tiers`** · **`system-architecture`** · **`scatter`** · **`bubble`** · **`radar`**.
> - **Retired — rebuild later**: `flowchart` · `state` · `class` (UML) · `er` · `sequence` · `gantt` · `pie`. For sequence/pipeline use cases use `lane-swim.html` instead.

## Showcase

### Radial Hub

> Center pivot + 5 satellites in a square container. 6 bubbles, 5 bidirectional
> labeled arrows. Use for message buses, gateways, hub services, any
> architecture where one component connects N peers.

```
┌───────── Machine 1 · host (dashed frame) ─────────┐
│                                                    │
│               ┌──────────────┐                     │
│               │   node-1     │   (primary / top)   │
│               │  wide amber  │                     │
│               └──────┬───────┘                     │
│                      │  ← inbound.*                │
│                      │    outbound.*               │
│                      ▼                             │
│  ┌────────┐      ╭───────────╮      ┌────────┐    │
│  │ node-2 │─────▶│  hub pill │◀─────│ node-3 │    │
│  │  cyan  │      │   amber   │      │ purple │    │
│  └────────┘      ╰─────┬─────╯      └────────┘    │
│                        │                           │
│                  ╱     │     ╲                     │
│                 ╱      │      ╲                    │
│  ┌────────┐◀─────      │      ─────▶┌────────┐    │
│  │ node-4 │      │     │     │      │ node-5 │    │
│  │ green  │                          │ green  │    │
│  └────────┘                          └────────┘    │
│                                                    │
└────────────────────────────────────────────────────┘
  ↔ bidirectional · pills = priority/port · ⚠ = fragility
```

Reference consumer: `~/.roxabi/forge/lyra/visuals/tabs/nats-roadmap/tab-current.html`
(2.1 Process Map — lyra's NATS hub-and-spoke).

### Linear Flow

> 3 stages in a horizontal pipe — source → middle → sink. Unidirectional
> arrows with labels above. Use for data flows, request/response paths,
> inbound/outbound pipelines, any left-to-right narrative.

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│       publish subject           subscribe queue               │
│       ─────────────             ────────────────              │
│                                                               │
│  ┌────────┐    ───▶    ╭────────╮    ───▶    ┌──────────┐   │
│  │ source │            │  bus   │             │   sink   │   │
│  │  cyan  │            │ amber  │             │  amber   │   │
│  │        │            │  pill  │             │   wide   │   │
│  └────────┘            ╰────────╯             └──────────┘   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
  one-way arrows · labels above · 16/6 aspect · middle can be pill or wide
```

Reference consumers:
- `tab-current.html` 2.3 Inbound Flow (adapter → NATS → hub)
- `tab-current.html` 2.4 Outbound Streaming (middle card holds 4-step publish sequence)

### Dual Cluster

> 2 peers at the top sharing 2 central resources. Wide-bulge arrow routing
> avoids center-crossing. Use for HA pairs, dual-replica workers, any
> cluster where 2 components share a session store + a message bus.

```
┌────── Machine 1 · dual hub cluster ──────┐
│                                            │
│  ┌────────┐              ┌────────┐       │
│  │ peer-1 │              │ peer-2 │       │
│  │ purple │              │ purple │       │
│  └─┬────┬─┘              └─┬────┬─┘       │
│    │    ╲                  ╱    │          │
│    │     ╲  SET/GET · ..  ╱     │          │
│    │      ╲───╭──────╮───╱      │          │
│    │          │res-a │          │          │
│    │          │ pill │          │          │
│    │          ╰──────╯          │          │
│    │                             │          │
│    ╲       HUB_INBOUND           ╱          │
│     ╲───────╭──────╮────────────╱           │
│             │res-b │                        │
│             │ pill │                        │
│             ╰──────╯                        │
└────────────────────────────────────────────┘
  4 bidirectional edges · bulge-routed · single centered labels
```

Reference consumer: `tab-target.html` M3 (dual-hub lyra_hub-1 + lyra_hub-2 sharing Redis + NATS).

### Radial Ring

> N satellites in a true ring (no center hub). Inter-peer edges connect
> neighbors around the circle. Use for peer-to-peer meshes, ring buffers,
> consensus rings (Raft participants), any topology where nodes talk to
> their neighbors.

```
        node-1 (top)
       ╱          ╲
  node-6            node-2
   │                  │
   │     ring ring    │
   │                  │
  node-5            node-3
       ╲          ╱
        node-4 (bottom)
```

Reference consumer: `~/.roxabi/forge/_shared/diagrams/roxabi-project-ring.html`
(6 active projects — voiceCLI, lyra, 2ndBrain, imageCLI, roxabi-plugins, roxabi-forge — as peers in a ring showing cross-consume dependencies).

### System Architecture

> Full-system architecture diagram — request lifecycle top-to-bottom, platform lanes
> left-to-right. Composes users → cloud APIs → adapter processes → NATS bus strip
> → nested hub interior (with security-group overlay) → data stores → optional
> Phase 2 / remote band. Ships a 3-card executive summary row below the diagram.
>
> Use when `radial-hub` is too small and `layered` is too thin — specifically when
> the diagram has ≥ 15 specific components across ≥ 4 lifecycle layers and the
> reader needs to follow a request end-to-end. Uses `.fg-bus-strip` for the bus
> (full-width pill band) and `.fgraph-group.{cluster,security-group}` for nested
> sub-regions. Pulsing `.fg-live-dot` in the header conveys "live system".

```
┌────────────────────────────────────────────────────────────────────┐
│   ┌──────┐         ┌──────┐         ┌──────┐   ← ROW 1 users       │
│   │user-1│         │user-2│         │user-3│                        │
│   └──┬───┘         └──┬───┘         └──┬───┘                        │
│   ┌──▼───┐         ┌──▼───┐         ┌──▼───┐   ← ROW 2 cloud APIs   │
│   │api-1 │         │api-2 │         │api-3 │    (amber)            │
│   └──┬───┘         └──┬───┘         └──┬───┘                        │
│┌─── Machine 1 ──────────────────────────────────────────────────┐  │
││  ┌──▼────┐        ┌──▼────┐        ┌──▼────┐   ← ROW 3 adapters││
││  │adpt-1 │        │adpt-2 │        │adpt-3 │    (green proc)   ││
││  └──┬────┘        └──┬────┘        └──┬────┘                   ││
││╔════════════════════ BUS STRIP ════════════════════════════════╗││
││║  NATS · lyra.inbound.*.<bot> · lyra.outbound.*.<bot>          ║││
││╚═══════════════════════════════════════════════════════════════╝││
││┌─── hub cluster ─────────────────────┐ ┌── side cluster ────┐  ││
│││ ┌───┐ ┌───┐ ┌───┐                    │ │ ┌──────────────┐   │  ││
│││ │p-1│ │p-2│ │p-3│  ← sub-row 4a      │ │ │  voice tts   │   │  ││
│││ └───┘ └───┘ └───┘                    │ │ └──────────────┘   │  ││
│││ ┌───┐ ┌───┐ ┌───┐                    │ │ ┌──────────────┐   │  ││
│││ │a  │ │mem│ │llm│  ← sub-row 4b      │ │ │  voice stt   │   │  ││
│││ └───┘ └───┘ └───┘                    │ │ └──────────────┘   │  ││
│││ ╭─── security overlay (rose dashed)──╮                       │  ││
│││ │ auth + guard      │                                        │  ││
│││ ╰────────────────────╯                                        │  ││
││└──────────────────────────────────────┘ └────────────────────┘  ││
││  ┌────┐        ┌────┐        ┌────┐       ← ROW 5 stores        ││
││  │s-1 │        │s-2 │        │s-3 │         (purple)            ││
││  └────┘        └────┘        └────┘                              ││
│└────────────────────────────────────────────────────────────────┘  │
│                                          ┌─────────────┐            │
│                                          │ phase-2 band│ (dashed)  │
│                                          └─────────────┘            │
└────────────────────────────────────────────────────────────────────┘

┌ Runtime ─────────┐  ┌ Data ──────────┐  ┌ Transport ────┐
│ • bullet 1       │  │ • bullet 1     │  │ • bullet 1    │
│ • bullet 2       │  │ • bullet 2     │  │ • bullet 2    │
└──────────────────┘  └────────────────┘  └───────────────┘
  3-card info row · .info-card-grid from base/components.css
```

Reference example (standalone, fgraph-base.css inlined):
[`examples/system-architecture.html`](./examples/system-architecture.html)

Reference consumer (Mode B, links to `_shared/fgraph-base.css`):
`~/.roxabi/forge/lyra/visuals/architecture.html` (full Lyra system —
users · Telegram/Discord/Admin · Cloud APIs · adapters · NATS bus · hub
with nested MessagePipeline/Pool/Agent/Memory/LLM · voice daemons · data
stores · Machine 2 Phase 2 band).

**Layout Rules baked in:** the template (`system-architecture.html`)
ships as a correct worked example — all `--x`/`--y` coords, widths,
tones, and arrow paths follow the 7 Layout Rules in
`forge-chart/SKILL.md § Layout Rules (CRITICAL)`. Copy the file, then
replace **content only** (titles, sublabels, card bullets) — do not
touch coordinates unless you re-compute R1 (even stride) or R3 (row
clearance) for the new node count.

### Layered

> 4 horizontal layers stacked vertically — ingress → hub → workers → storage.
> Each layer has a dashed frame + label. Use for classic 3-tier / 4-tier
> architectures, request processing pipelines, clean architecture layers.

```
┌──────────── Ingress ────────────┐
│  ┌──────────────────────────┐   │
│  │      gateway / API       │   │
│  └──────────────────────────┘   │
└──────────────────────────────────┘
                │
                ▼
┌──────────── Router ────────────┐
│  ╭────────────────────────────╮ │
│  │      message bus pill      │ │
│  ╰────────────────────────────╯ │
└──────────────────────────────────┘
           ╱     ╲
          ▼       ▼
┌────── Workers ───────┐
│  ┌────┐    ┌────┐     │
│  │w-1 │    │w-2 │     │
│  └────┘    └────┘     │
└───────────────────────┘
           ╲     ╱
            ▼   ▼
┌──────── Storage ───────────────┐
│  ┌──────────────────────────┐  │
│  │    database / cache      │  │
│  └──────────────────────────┘  │
└────────────────────────────────┘
```

Reference consumer: `~/.roxabi/forge/_shared/diagrams/lyra-stack-layers.html`
(lyra 4-layer architecture: Adapters → Hub → Services → Infrastructure).

### Machine Clusters

> 3 machine frames side-by-side with cross-machine edges. Each frame has its
> own dashed border + label. Use for multi-host deployments, dev/staging/prod
> side-by-side, microservices distributed across machines.

```
┌────── Machine-1 ──────┐  ┌────── Machine-2 ──────┐  ┌────── Machine-3 ──────┐
│  ┌────┐               │  │  ┌────┐               │  │               ┌────┐ │
│  │hub │               │  │  │hub │               │  │               │ext │ │
│  └────┘               │  │  └────┘               │  │               └────┘ │
│    │                  │  │    │                  │  │                  │    │
│  ┌────┐               │  │  ┌────┐               │  │                  │    │
│  │adapter│            │  │  │shared│             │  │                  │    │
│  └────┘               │  │  └────┘               │  │                  │    │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
         │                            │                           │
         └────────────────────────────┴───────────────────────────┘
                    cross-machine edges (bulge routing)
```

Reference consumer: `~/.roxabi/forge/_shared/diagrams/roxabi-two-machine-deployment.html`
(ROXABITOWER dev + roxabituwer prod side-by-side with deploy + GitHub cross-machine edges).

### Deployment Tiers

> 3 deployment tiers stacked vertically — dev / staging / prod. Each tier
> has a colored stripe + label. Promotion arrows flow upward (dev → staging → prod).
> Data sync arrows flow between tiers. Use for CI/CD pipeline visualization.

```
┌────────────────── Production (green) ──────────────────┐
│  ┌──────────┐        ┌─────────┐                       │
│  │ service  │◀──────▶│   db    │   ← data sync        │
│  └──────────┘        └─────────┘                       │
│         ▲                                              │
│         │ promote                                      │
├────────────────── Staging (cyan) ─────────────────────┤
│  ┌──────────┐        ┌─────────┐                       │
│  │ service  │◀──────▶│   db    │                       │
│  └──────────┘        └─────────┘                       │
│         ▲                                              │
│         │ promote                                      │
├────────────────── Dev (amber) ────────────────────────┤
│  ┌─────────────────────────┐                          │
│  │    local dev env        │                          │
│  └─────────────────────────┘                          │
└───────────────────────────────────────────────────────┘
```

Reference consumer: `~/.roxabi/forge/_shared/diagrams/lyra-deployment-tiers.html`
(lyra dev → staging → prod promotion flow via `make deploy` + pytest gate).

### Retired types

The following types were removed as both static fgraph templates and fd-engine types.
Auto-layout (elk / `fd-layout.mjs`) and standalone chart renderers were deleted 2026-06-22
(premium-only purge) pending a premium-first rebuild.

| Former path | Status | Routing |
|---|---|---|
| `gantt.html` + fd-engine `type:"gantt"` | **retired** | no current replacement — rebuild later |
| `pie.html` + fd-engine `type:"pie"` | **retired** | no current replacement — rebuild later |
| `er.html` + fd-engine `type:"er"` | **retired** | no current replacement — rebuild later |
| `sequence.html` + fd-engine `type:"sequence"` | **retired** | use `lane-swim.html` for sequence/pipeline flows |
| `state.html` + fd-engine `type:"state"` | **retired** | no current replacement — rebuild later |
| fd-engine `type:"flowchart"` | **retired** | no current replacement — rebuild later |
| fd-engine `type:"class"` (UML) | **retired** | no current replacement — rebuild later |

The `fgraph-base.css` rules for `.fg-gantt-bar`, `.fg-lifeline`, `.fg-lifeline-activation`,
and `.mk-er-stroke` remain in `fgraph-base.css` but are **dormant** — the fd-engine output
HTML that consumed them no longer exists. They will be reactivated or removed when the
retired types are rebuilt.

### Dep-Graph

> Issue-dependency graph laid out as phase columns × issue cards. Cards
> positioned via `--x` / `--y` custom props (both injected by
> `scripts/gen-deps.py`; the template is pure scaffolding — no hand-coded
> coordinates). Edges are elbow-routed SVG paths with ≥ 2 segments;
> cross-phase edges are assigned corridors to avoid overlap.
>
> Use for roadmap / backlog visualization with visible parent / blocks /
> depends-on relationships. Ghost cards (dashed, translucent) represent
> cross-cycle or closed-as-superseded issues.

```
    Cycle 1 · P1         Cycle 2 · P2        Cycle 2 · P3+P4   Close
   ┌───────────┐        ┌───────────┐       ┌───────────┐    ┌──────┐
   │    #22    │──blocks▶│    #23    │──blocks▶│    #24   │───▶│ #19  │
   │  native   │        │ migrate   │       │ delete +  │    │super │
   │ templates │        │  SKILLs   │       │  guard    │    │seded │
   └───────────┘        └───────────┘       └───────────┘    └──────┘
         ▲                    ▲                    ▲
         └─────── parent #21 (ghost) ──────────────┘
```

Template: [`dep-graph.html`](./dep-graph.html) · demo: [`examples/dep-graph.html`](./examples/dep-graph.html).
Native, consumed by `scripts/gen-deps.py` (rewritten in #23).

### Lane-swim

> N vertical lanes (fixed x-positions) × N rows — **one node per row**, any
> lane. Flow runs top-to-bottom. Phases are visual groupings marked by faint
> horizontal separator lines, **not** by shared y-coordinates. Connectors are
> git-graph-style cubic bezier S-curves for cross-lane hops and straight
> verticals for same-lane hops. Parallel edges from the same source bend with
> a perpendicular offset so XOR splits read distinctly.
>
> Use for message-flow pipelines, request lifecycle diagrams, clean-arch layer
> traces, or any process that crosses multiple horizontal domains over several
> sequential phases. Container height is driven by `--fg-lane-min-height`
> (default 900px) — no aspect-ratio constraint.

```
  Presentation   Application     Kernel      Infrastructure
  ─────────────────────────────────────────────────────────── ← header strip
       │               │             │               │
  ① Receive  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  ← phase separator
  ●─ AdapterIn         │             │               │
  ● STT (opt)          │             │               │    ← dashed circle
  ●─ Normalize         │             │               │
       │               │             │               │
  ② Gate  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
       │               │         ● Guards             │
       │           ●─ RateLimit      │               │
       │           ●─ Session        │               │
  ③ Dispatch ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
       │           ●─ Router         │               │
       │         ╭─● Command[cmd]    │               │  ← right-bulge fork
       │         ╰─● LLM [llm]       │               │  ← left-bulge fork
       │               └────────────▶●─ StreamProc   │
       │                             ●─ RenderEvent  │
  ④ Respond ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
       │                             └──────────────▶●─ Persist
       │                             └─ ─ ─ ─ ─ ─ ─▶●─ TTS? (opt)
       │                                             ●─ AdapterOut
```

Template: [`lane-swim.html`](./lane-swim.html) · demo: [`examples/lane-swim.html`](./examples/lane-swim.html).
Native, no CDN, file://-safe. Height via `--fg-lane-min-height` (default 900px).

### Scatter

> Inline SVG data-chart plotting X↔Y pairs as circle marks in a
> labelled axis box. Each point maps to one observation; axis ticks
> and grid lines are pre-computed and emitted as `<line>` elements.
>
> Use when you need to visualise the correlation (or absence of it)
> between two continuous variables — e.g. latency vs payload size,
> score vs tokens, CPU vs memory. Cap at ~200 points before the SVG
> becomes illegible at normal viewport widths.

Template: [`scatter.html`](./scatter.html) · demo: [`examples/scatter.html`](./examples/scatter.html).
Native, no CDN, file://-safe.

### Bubble

> Extends scatter with a third dimension encoded as circle radius.
> Each datum has (x, y, size) — x and y map to the axis space, size
> maps to `r` on the rendered circle.
>
> Use when a third continuous variable (magnitude, volume, weight)
> needs to be visible alongside the two-axis correlation — e.g.
> request latency × error-rate × traffic volume. Keep bubbles
> non-overlapping or use low opacity to prevent occlusion.

Template: [`bubble.html`](./bubble.html) · demo: [`examples/bubble.html`](./examples/bubble.html).
Native, no CDN, file://-safe.

### Radar

> N-axis spider/radar chart in an inline SVG. Each axis radiates from
> a shared centre; a dataset is a polygon connecting one value per
> axis. Multiple datasets overlay as semi-transparent polygons for
> direct comparison.
>
> Use for multi-axis comparison where all metrics share a common
> scale — e.g. comparing agent capabilities, benchmark profiles,
> or feature coverage across N dimensions. Cap at 8 axes before
> label spacing collapses.

Template: [`radar.html`](./radar.html) · demo: [`examples/radar.html`](./examples/radar.html).
Native, no CDN, file://-safe.

### Funnel

> Decreasing-width horizontal bars stacked vertically, one per
> conversion stage. Each bar's width encodes the stage value as a
> proportion of the entry value; a right-hand label shows the absolute
> count and drop-off percentage.
>
> Use for pipeline / stage-conversion visualisation — e.g. marketing
> funnel (visits → signups → trials → paid), CI stages (triggered →
> built → tested → deployed), or any sequential process where tracking
> attrition between steps matters.

Template: [`funnel.html`](./funnel.html) · demo: [`examples/funnel.html`](./examples/funnel.html).
Native, no CDN, file://-safe.

---

## Templates

| Template | When to use | Size | Key features |
|----------|------------|------|--------------|
| `radial-hub.html` | Hub-and-spoke / message bus / gateway with 4–6 peers | ~4K | Center pill hub + 5 satellites, bidirectional labeled arrows, dashed machine frame, pills, fragility warn sub, hover glow |
| `linear-flow.html` | 3-stage pipeline (source → middle → sink) | ~3K | 3 horizontal cards, single-direction arrows, labels above, 16/6 aspect, middle pill or wide, any-tone edges |
| `dual-cluster.html` | 2 peers sharing 2 central resources (HA pair + session + bus) | ~4K | 2 top peers + center resource + bottom bus, 4 bidirectional arrows with wide-bulge routing, single centered labels, square aspect |
| `radial-ring.html` | Peer-to-peer mesh / ring buffer / consensus ring (no center hub) | ~4K | 6 nodes in a circle, clockwise inter-peer edges, labels outside ring, square aspect |
| `system-architecture.html` | Full-system architecture (≥ 15 components, ≥ 4 lifecycle layers, request-lifecycle view with bus + nested hub) | ~11K | Rows for users/cloud APIs/adapters/bus/hub-interior/stores/phase-2; full-width `.fg-bus-strip` between adapter row and hub; `.fgraph-group.cluster` wraps hub sub-components; `.fgraph-group.security-group` overlay for auth; `.fg-live-dot` in header; built-in 3-card `.info-card-grid` footer; wide aspect (14/10) |
| `layered.html` | 3–4 horizontal layers (ingress → hub → workers → storage) | ~5K | 4 stacked layers with dashed frames, vertical fan-out/fan-in arrows, tall aspect (3/4), optional 3-layer variant |
| `machine-clusters.html` | Multi-host deployment / distributed services across machines | ~5K | 3 machine frames side-by-side, cross-machine edge routing, wide aspect (16/9), per-machine labels |
| `deployment-tiers.html` | CI/CD pipeline / dev → staging → prod promotion | ~5K | 3 colored tier stripes, promotion arrows upward, data sync arrows, tall aspect (4/5), tier-specific tones |
| *(retired)* `gantt.html` | — | — | Retired 2026-06-22; no current replacement — rebuild later |
| *(retired)* `pie.html` | — | — | Retired 2026-06-22; no current replacement — rebuild later |
| *(retired)* `er.html` | — | — | Retired 2026-06-22; no current replacement — rebuild later |
| *(retired)* `sequence.html` | — | — | Retired 2026-06-22; use `lane-swim.html` for sequence/pipeline flows |
| *(retired)* `state.html` | — | — | Retired 2026-06-22; no current replacement — rebuild later |
| `dep-graph.html` | Issue dependency graph — phase-column × issue-card matrix | ~5K | Phase-column header row, `.fg-dep-card` positioned via `--x`/`--y` (Python-injected), elbow-routed SVG paths, `.ghost` cross-phase placeholders |
| `lane-swim.html` | Message flow / request lifecycle across N architectural lanes, one node per row | ~6K | Lane header strip (`.fg-lane-header`/`.fg-lane-title`), phase separator lines (`.fg-lane-phase-line`/`.fg-lane-phase-lbl`), 18 px circle nodes (`.fg-lane-node`), inline tag pills (`.fg-lane-tag`), S-curve + parallel-bend connectors (`.fg-lane-curve`), chip-on-wire edge labels (`.fg-edge-lbl`), `--fg-lane-min-height` knob |
| `scatter.html` | Scatter — X↔Y correlation between two continuous variables | ~3K | Inline SVG axis box, pre-computed tick marks and grid lines, labelled axes, circle marks per datum |
| `bubble.html` | Bubble — X, Y + magnitude encoded as bubble radius (3-variable) | ~3K | Extends Scatter; `r` attribute on circles encodes a third dimension; low-opacity fills prevent occlusion |
| `radar.html` | Radar — multi-axis comparison (N metrics, spider/spider chart) | ~3K | Inline SVG N-axis radials from shared centre, dataset polygons as semi-transparent overlays, axis labels |
| `funnel.html` | Funnel — pipeline / stage conversion, sequential attrition | ~3K | Decreasing-width bars per stage, right-hand count + drop-off % labels, single-file inline SVG |

All **14 native fgraph** templates (`radial-hub`, `linear-flow`,
`dual-cluster`, `radial-ring`, `layered`, `machine-clusters`,
`deployment-tiers`, `dep-graph`, `lane-swim`, `system-architecture`,
`scatter`, `bubble`, `radar`, `funnel`)
share **`fgraph-base.css`** — the CSS primitives for graphs. Distribution
model depends on the consumer (see "Inlined vs shared" below).

`gantt`, `pie`, `er`, `sequence`, `state` are retired. For sequence/pipeline flows use `lane-swim.html`. All other retired types have no current replacement — rebuild later.

### Primitives (`fgraph-base.css`)

| Primitive | Purpose |
|-----------|---------|
| `.fgraph-wrap` | Container — square / wide / tall aspect ratio, bordered, padded |
| `.fgraph-wrap.{amber,cyan,purple,green,red}` | Container border tone |
| `.fgraph-frame` + `.fgraph-frame-lbl` + `.fgraph-frame-sub` | Optional inner dashed border (machine / zone / deployment) |
| `.fgraph-edges` | SVG overlay layer (`viewBox="0 0 100 100" preserveAspectRatio="none"`, `pointer-events:none`, `overflow:visible`) |
| `.fg-edge.{tone}` | Colored path (`amber`, `cyan`, `purple`, `green`, `red`, `dim`) — uses `vector-effect: non-scaling-stroke` so strokes stay crisp regardless of container aspect |
| `.mk-{tone}` | Marker (arrowhead) fill classes — apply to `<path>` inside `<marker>` |
| `.fgraph-node` | Absolute-positioned HTML card via `--x` / `--y` / `--w` custom props (all in %) |
| `.fgraph-node.{tone}` | Node border + tint (amber/cyan/purple/green/red) |
| `.fgraph-node.wide` / `.narrow` | Width modifier (30% / 18%, default 22%) |
| `.fgraph-node.pill` | Pill-shaped — use for the central hub / bus / broker |
| `.fgraph-node.circle` | Circle — event, trigger, start/end (`border-radius: 50%; aspect-ratio: 1`) |
| `.fgraph-node.hexagon` | Hexagon — agent, worker, autonomous unit (`clip-path` polygon) |
| `.fgraph-node.diamond` | Diamond — decision, gate, conditional (`clip-path` polygon) |
| `.fgraph-node.cylinder` | Cylinder — database, storage, queue (ellipse caps via `::before`/`::after`) |
| `.fgraph-node.folded` | Folded corner — file, config, document (`clip-path` with corner notch) |
| `.fg-edge.dashed` | Dashed stroke — optional / async / planned path |
| `.fg-edge.thick` | Thick stroke (2.8px) — primary data flow / critical path |
| `.fg-edge.animated` | Animated dashes — live stream / active connection |
| `.fgraph-title.{tone}` | Colored node title with flex for inline pills |
| `.fgraph-pill.{tone}` | Inline badge (priority, port, status) |
| `.fgraph-sub` / `.muted` / `.warn` / `.ok` | Node subtitles (default / muted / red / green) |
| `.fgraph-lbl.{tone}` | Absolute HTML edge label via `--x` / `--y` |
| `.fgraph-legend` | Bottom legend strip |
| `.fg-bus-strip.{tone}` | Full-width horizontal pill band — use when a message bus / event bus spans the diagram between two node rows. Positioned via `--y` (top %) + `--h` (height %). Default tone is `.orange` (message-bus semantic); `.amber`/`.cyan`/`.purple`/`.green`/`.red` available. Contains `.fg-bus-strip__title` + `.fg-bus-strip__sub`. |
| `.fg-live-dot.{tone}` | Pulsing status indicator. Inline element; sits next to a title to signal "live system". Default green (healthy); `.amber` (warn), `.red` (down). Pure CSS animation, no JS. |

### Coordinate system

Both nodes and SVG paths use a **0..100 coordinate space**.

| Axis | Nodes | SVG |
|------|-------|-----|
| x | `style="--x:50"` → `50%` from left of container | `d="M 50,..."` |
| y | `style="--y:14"` → `14%` from top | `d="... 14 ..."` |

The SVG layer uses `viewBox="0 0 100 100" preserveAspectRatio="none"` so 1
viewBox unit = 1% of container (width or height). Strokes stay crisp via
`vector-effect: non-scaling-stroke`. Markers may render slightly stretched on
non-square containers — use `.fgraph-wrap.square` for pixel-perfect arrowheads.

### Shape vocabulary

Shapes are semantic — pick by **what the node is**, not how you want it to look.
Full reference: [`../shape-vocabulary.md`](../shape-vocabulary.md).

| Shape | Class | Use when node is... |
|-------|-------|---------------------|
| Rounded rect | *(default)* | A service, process, or generic component |
| Pill | `.pill` | A bus, broker, router, or relay |
| Circle | `.circle` | An event, trigger, signal, or lifecycle point |
| Hexagon | `.hexagon` | An agent, worker, or autonomous unit |
| Diamond | `.diamond` | A decision, gate, or conditional branch |
| Cylinder | `.cylinder` | A database, cache, queue, or data store |
| Folded | `.folded` | A file, config, document, or static asset |

Arrow modifiers compose with tones on `.fg-edge`:

| Modifier | Class | Use when path is... |
|----------|-------|---------------------|
| Dashed | `.dashed` | Optional, async, planned, or fallback |
| Thick | `.thick` | Critical path or primary data flow |
| Animated | `.animated` | Live stream or real-time connection |

Shapes compose with tones and sizes: `<div class="fgraph-node hexagon amber wide">`.
Arrow modifiers stack: `<path class="fg-edge cyan thick animated">`.

### Edge Flow Semantics

Prefer semantic classes over raw color tones on `.fg-edge`. They describe intent rather than appearance and let individual aesthetics remap meanings by declaring `--edge-{name}` tokens on `:root`.

| Class | Intent | Default color | Stroke style | When to use |
|-------|--------|---------------|--------------|-------------|
| `.control` | Command / signal / invocation — "A tells B what to do" | accent | solid | API call, RPC, trigger, action dispatch |
| `.write` | Mutating data flow — "A persists into B" | green | dashed (4 3) | DB insert/update, cache set, queue enqueue |
| `.read` | Non-mutating data flow — "A pulls from B" | cyan | solid | DB select, cache get, config load |
| `.data` | Bulk transfer / ingest / ETL payload | purple | solid | Batch pipeline, import job, stream replay |
| `.async` | Fire-and-forget / event bus / deferred work | text-muted | short-dashed (2 3) | Webhook, background job, pub/sub |
| `.feedback` | Reverse flow / ack / return signal / retry | amber | solid (curved paths read best) | Response, ack, error return, compensating action |

Example:

```html
<path class="fg-edge control"  d="..." />
<path class="fg-edge write"    d="..." />
<path class="fg-edge feedback" d="..." />
```

Override per aesthetic by declaring the token on the aesthetic's `:root`:

```css
:root { --edge-control: var(--cyan); }   /* terminal aesthetic: control flows in cyan */
```

### Legacy color-tone classes

The raw color classes (`.amber`, `.cyan`, `.purple`, `.green`, `.red`, `.dim`) remain fully supported — no existing template needs to change. Treat them as **legacy**: new work should reach for the semantic classes above so aesthetics can re-tint without editing markup. If both a semantic class and a color class are applied to the same path, the semantic rule is declared later in `fgraph-base.css` and therefore wins the cascade.

---

## Inlined vs shared — when to promote

`fgraph-base.css` has **two distribution modes** depending on the consumer.
Pick based on how the HTML is deployed and how many diagrams reuse the classes.

### Mode A — inlined (default for single-file HTML)

Paste the full content of `fgraph-base.css` into the output's `<style>` block.
The HTML is 100% self-contained — no external files, works with `file://`,
survives any move / rename.

**When to use:**
- `forge-chart` single-file output (`~/.roxabi/forge/<project>/<slug>.html`)
- One-off diagrams
- Anything that must work with `file://` (documentation that gets emailed, dropped into a ticket, etc.)
- Single tab in a multi-tab doc where only one diagram uses fgraph

**Rule:** the forge-chart skill directive "inline, never link" applies here.
This is the default.

### Mode B — shared (for multi-tab docs with ≥ 2 fgraph diagrams)

Deploy `fgraph-base.css` once to `~/.roxabi/forge/_shared/fgraph-base.css`
and reference it from the main shell `<head>` via a relative `<link>`:

```html
<link rel="stylesheet" href="../../_shared/fgraph-base.css">
```

**When to use:**
- Multi-tab roadmap / spec docs where ≥ 2 tabs use fgraph classes
- Any shell where you want one edit to `fgraph-base.css` to propagate across N diagrams
- Matches the existing `gallery-base.{css,js}` precedent

**Setup (one-time):**

```bash
# 1. Copy plugin source → runtime mirror
cp ~/projects/roxabi-plugins/plugins/forge/references/graph-templates/fgraph-base.css \
   ~/.roxabi/forge/_shared/fgraph-base.css

# 2. Add <link> to the shell <head> (path is relative to the .html file)
# For a file at ~/.roxabi/forge/lyra/visuals/my-doc.html:
#   <link rel="stylesheet" href="../../_shared/fgraph-base.css">

# 3. Remove the inline <style>.fgraph-*</style> block from any tab
#    fragments — they now inherit from the shell's linked stylesheet

# 4. Verify deploy — ~/.roxabi/forge/_shared/ must be included when you
#    `make forge deploy`. (It already is, via the gallery-base precedent.)
```

### Promotion checklist

When a second tab adopts fgraph in the same shell:

- [ ] `cp` plugin source → `~/.roxabi/forge/_shared/fgraph-base.css`
- [ ] Add `<link>` to the shell `<head>` (after Google Fonts, before design-tokens `<style>`)
- [ ] Delete every inline `<style>.fgraph-*</style>` block from tab fragments
- [ ] Verify all tabs still render (reload each one)
- [ ] When editing `fgraph-base.css`, remember: both the plugin source AND the `_shared/` mirror must stay in sync. Treat the `_shared/` copy as a deploy artifact, not an independent file.

### Precedent

This is the same pattern galleries already use:

```
~/projects/roxabi-plugins/plugins/forge/references/gallery-templates/
  gallery-base.css       ← plugin source of truth
  gallery-base.js
  pivot-gallery.html     ← template references ../../_shared/gallery-base.css

~/.roxabi/forge/_shared/
  gallery-base.css       ← runtime mirror, deployed alongside galleries
  gallery-base.js
  fgraph-base.css        ← runtime mirror, deployed alongside fgraph diagrams
```

---

## Edge/marker SSoT and drift gate

### Where the canonical block lives

`fgraph-base.css` is the single source of truth for the edge/marker config.
It contains two coupled sections:

- The SVG marker `<defs>` (arrow `<marker>` elements, each with
  `markerWidth="6" markerHeight="6"`, no `markerUnits` override).
- The `.fgraph-edges .fg-edge` CSS rule, which carries
  `vector-effect: non-scaling-stroke`.

### The `{{FGRAPH_BASE}}` placeholder contract

Raw templates carry **no inline `non-scaling-stroke`** and **no `<marker>`
defs** — these are injected at generation time by replacing the
`{{FGRAPH_BASE}}` placeholder with the full `fgraph-base.css` content.
The validator is placeholder-aware: a template that contains `{{FGRAPH_BASE}}`
is exempt from the missing-NSS check; a rendered output HTML is not.

### Enforcement gates

Two gates prevent drift from reaching the runtime artifacts:

1. **lefthook pre-commit** — runs `validate-svg` on every staged file under
   `graph-templates/**/*.html`. Commit is blocked if a rendered output is
   missing `vector-effect: non-scaling-stroke` or carries
   `markerUnits="userSpaceOnUse"`.

2. **CI "Validate fgraph SVG" step** — same check on the full tree, runs on
   every pull request. Fails the build on any violation.

---

## Shape picker — which template?

Pick by layout intent, not by domain. Any template can be re-tinted
(tones, pills) to match the domain.

> **Default first.** This picker is for *static* output. For on-screen diagrams,
> the two surviving fd-engine types route as follows: "1 center + 4–6 peers" →
> `type:"hub-spoke"`, "3–4 horizontal layers" / "machine frames" / "dev-staging-prod
> tiers" → `type:"architecture"`. Flowchart / state / class / er / sequence / gantt /
> pie types are retired — use the static templates listed here or wait for the
> premium-first rebuild. Use a static template for print / no-JS or an explicit static-look request.

| Your diagram shape | Template | Reference |
|--------------------|----------|-----------|
| 1 center + 4–6 peers radiating out | `radial-hub.html` | 2.1, M1, M2 |
| 3 stages in a horizontal pipe (source → middle → sink) | `linear-flow.html` | 2.3, 2.4 |
| 2 peers + 2 shared resources (HA pair cluster) | `dual-cluster.html` | M3 |
| N nodes in a ring, each talks to neighbors | `radial-ring.html` | consensus visualizer |
| 3–4 horizontal layers stacked vertically | `layered.html` | service architecture |
| 2–3 machine frames side-by-side | `machine-clusters.html` | distributed deployment |
| Dev / staging / prod tiers stacked | `deployment-tiers.html` | CI/CD pipeline |
| Timeline / schedule / roadmap with dated tasks | *(retired 2026-06-22 — no current replacement; rebuild later)* | release plan, multi-workstream project |
| Proportion / share / composition — 3–7 slices | *(retired 2026-06-22 — no current replacement; rebuild later)* | cost or traffic breakdown |
| Entity-relationship schema — tables + FK/cardinality | *(retired 2026-06-22 — no current replacement; rebuild later)* | DB schema, domain model |
| Protocol exchange / message flow / pipeline — ≤ 15 messages | `lane-swim.html` | `/dev` pipeline interaction, API handshake |
| Finite-state machine / lifecycle — ≤ 6 states | *(retired 2026-06-22 — no current replacement; rebuild later)* | issue lifecycle, review workflow, connection states |
| Issue dependency graph — phase columns × issue cards | `dep-graph.html` | roadmap backlog, blocks/depends-on visualisation (via `gen-deps.py` in #23) |
| Message flow / request lifecycle crossing N architectural layers over M phases | `lane-swim.html` | clean-arch layer trace, pipeline walkthrough, process with optional steps |
| Scatter — X↔Y correlation between two continuous variables | `scatter.html` | latency vs payload, score vs tokens, any 2-var correlation |
| Bubble — X, Y + third dimension as bubble size | `bubble.html` | traffic × latency × error-rate, 3-axis insight in one chart |
| Radar — N-axis comparison across entities on a common scale | `radar.html` | benchmark profiles, capability matrix, feature coverage spider |
| Funnel — sequential pipeline with per-stage conversion / drop-off | `funnel.html` | marketing funnel, CI pipeline attrition, onboarding steps |
| Something that doesn't fit | start from the closest template, reposition nodes via `--x`/`--y`, repaint arrow paths to match |

All 14 remaining native fgraph templates (`radial-hub`, `linear-flow`, `dual-cluster`,
`radial-ring`, `layered`, `machine-clusters`, `deployment-tiers`,
`dep-graph`, `lane-swim`, `system-architecture`,
`scatter`, `bubble`, `radar`, `funnel`) share the same
`fgraph-base.css` primitives — differences live only in layout coordinates
and a few shape-specific extensions (`.fg-axis-date`, `.fg-lane-*` swimlane primitives), so
mixing features (e.g. a linear-flow with a dashed machine frame borrowed from
radial-hub) is just copy-paste.

Note: `fgraph-base.css` still contains `.fg-gantt-bar`, `.fg-lifeline`, `.fg-lifeline-activation`,
and `.mk-er-stroke` — these are **dormant**; the fd-engine output that consumed them was retired
2026-06-22 (see "Retired types" section above). They will be reactivated or removed when those
types are rebuilt.

`gantt`, `pie`, `er`, `sequence`, `state` are retired — see the "Retired types" section above.

---

## How to customise `radial-hub.html`

### Step 1 — Fill placeholders

| Placeholder | Example | Where |
|-------------|---------|-------|
| `{{TITLE}}` | `Lyra — NATS Architecture Roadmap` | `<title>`, diagram-meta |
| `{{TITLE_PLAIN}}` / `{{TITLE_ACCENT}}` | `Current` / `Topology` | `<h1>` split for accent color |
| `{{DATE}}` | `2026-04-09` | diagram-meta |
| `{{CATEGORY}}` / `{{CAT_LABEL}}` / `{{COLOR}}` | `plan` / `Plan` / `amber` | diagram-meta |
| `{{CATEGORY_LABEL}}` | `CURRENT STATE` | header eyebrow |
| `{{SUBTITLE}}` | `Production state — verified @ staging` | header subtitle |
| `{{DIAGRAM_ARIA_LABEL}}` | `Lyra production process map` | `<div role="img">` aria-label |
| `{{FRAME_LABEL}}` | `Machine 1 · roxabituwer` | Dashed frame top-left caption |
| `{{FRAME_SUB}}` | `supervisord · lyra.service` | Dashed frame sub-caption |

### Step 2 — Node placeholders

Six nodes — one hub (pill, center) and five satellites (`node-1` through
`node-5`).

| Placeholder | Example |
|-------------|---------|
| `{{NODE_1_NAME}}` / `{{NODE_1_PILL}}` / `{{NODE_1_SUB}}` / `{{NODE_1_WARN}}` | `lyra_hub` / `p=100` / `PoolManager · Middleware` / `⚠ CliPool [C1]` |
| `{{NODE_2_NAME}}` / `{{NODE_2_PILL}}` / `{{NODE_2_SUB}}` / `{{NODE_2_SUB_MUTED}}` | `lyra_telegram` / `p=200` / `aiogram long-polling` / `adapter_standalone.py` |
| `{{NODE_3_NAME}}` / `{{NODE_3_PILL}}` / `{{NODE_3_SUB}}` / `{{NODE_3_SUB_MUTED}}` | `lyra_discord` / `p=200` / `discord.py websocket` / `adapter_standalone.py` |
| `{{HUB_NAME}}` / `{{HUB_SUB}}` / `{{HUB_SUB_MUTED}}` | `nats.container` / `Quadlet · single node` / `:4223 → :4222` |
| `{{NODE_4_NAME}}` / `{{NODE_4_PILL}}` / `{{NODE_4_SUB}}` / `{{NODE_4_SUB_MUTED}}` | `voicecli_tts` / `worker` / `NatsAdapterBase` / `Qwen3 · Chatterbox` |
| `{{NODE_5_NAME}}` / `{{NODE_5_PILL}}` / `{{NODE_5_SUB}}` / `{{NODE_5_SUB_MUTED}}` | `voicecli_stt` / `worker` / `NatsAdapterBase` / `Whisper` |

**Tone defaults:**
- node-1 (top): `amber wide` — primary process, bigger card
- node-2 (mid-left): `cyan`
- node-3 (mid-right): `purple`
- hub (center): `amber pill` — the bus / broker
- node-4 (bot-left): `green`
- node-5 (bot-right): `green`

Change the tone classes on the `<div class="fgraph-node …">` elements to match
your domain. Any of `amber`, `cyan`, `purple`, `green`, `red`.

### Step 3 — Edge labels

Each edge has an HTML label positioned via `--x` / `--y` in %.

| Placeholder | Default position | Example |
|-------------|------------------|---------|
| `{{EDGE_1_LABEL}}` / `{{EDGE_1_LABEL_B}}` / `{{EDGE_1_HINT}}` | `--x:50;--y:36` | `lyra.inbound.*` / `lyra.outbound.*` / `HUB_INBOUND` (dim) |
| `{{EDGE_2_LABEL}}` | `--x:30;--y:51` | `telegram.<bot_id>` |
| `{{EDGE_3_LABEL}}` | `--x:70;--y:51` | `discord.<bot_id>` |
| `{{EDGE_4_LABEL}}` | `--x:30;--y:68` | `tts.req/res` |
| `{{EDGE_5_LABEL}}` | `--x:70;--y:68` | `stt.req/res` |

Labels use `<br/>` for multi-line. Wrap dim hints in `<span class="dim">...</span>`.

### Step 4 — Tweak coordinates (optional)

The defaults place nodes on a symmetric radial layout:

| Node | x | y |
|------|---|---|
| node-1 (top) | 50 | 14 |
| node-2 (mid-left) | 13 | 34 |
| node-3 (mid-right) | 87 | 34 |
| hub (center) | 50 | 58 |
| node-4 (bot-left) | 13 | 80 |
| node-5 (bot-right) | 87 | 80 |

**If you move a node**, update the corresponding arrow path's endpoints too.
Arrow endpoints sit at the node's visible **edge**, not its center (so the
arrowhead isn't covered by the card).

### Edge endpoint calculation

For a node at `--y:Y` with height `--h:H` (default 22%, wide=30%, narrow=18%):

```
node_top_edge    = Y - (H / 2)
node_bottom_edge = Y + (H / 2)
node_left_edge   = X - (W / 2)
node_right_edge  = X + (W / 2)
```

**Example:** Node at `--x:50;--y:14` with `--w:30%` (wide):
- Height ≈ 16% of container (card padding + content)
- Top edge ≈ y=14 - 8 = **6** (but card extends, so visible top is ~y=10)
- Bottom edge ≈ y=14 + 8 = **22** (arrow starts here)
- Left edge ≈ x=50 - 15 = **35**
- Right edge ≈ x=50 + 15 = **65**

For the hub pill at `--y:58`:
- Top edge ≈ **50** (arrow from node-1 ends here)
- Bottom edge ≈ **66**

**Rule of thumb:** Add ~8 units padding from the edge to prevent arrowheads
from touching the card border. For curves, the control point should bulge
away from the center to route around intervening nodes.

For the default layout:

| Edge | Path | Calculation |
|------|------|-------------|
| node-1 ↔ hub (vertical) | `M 50,22 L 50,50` | node-1 bottom (14+8=22) → hub top (58-8=50) |
| node-2 ↔ hub (curve) | `M 25,38 Q 33,48 42,55` | node-2 bottom-right (13+12=25, 34+4=38) → hub top-left |
| node-3 ↔ hub (curve) | `M 75,38 Q 67,48 58,55` | node-3 bottom-left (87-12=75, 34+4=38) → hub top-right |
| node-4 ↔ hub (curve) | `M 25,75 Q 32,68 42,62` | node-4 top-right (13+12=25, 80-5=75) → hub bottom-left |
| node-5 ↔ hub (curve) | `M 75,75 Q 68,68 58,62` | node-5 top-left (87-12=75, 80-5=75) → hub bottom-right |

### Step 5 — Inline fgraph-base.css

Replace the `{{FGRAPH_BASE}}` placeholder in the template's `<style>` block
with the content of `fgraph-base.css`. Forge directive: inline, never link.

---

## How to customise `linear-flow.html`

3 nodes on a horizontal line. Much simpler than radial-hub — fewer
placeholders, fewer coordinate knobs.

### Step 1 — Placeholders

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{TITLE}}` / `{{DATE}}` / `{{CATEGORY}}` / etc. | standard diagram-meta | same as radial-hub |
| `{{WRAP_TONE}}` | `green` / `amber` / `cyan` | container border color |
| `{{SOURCE_NAME}}` / `{{SOURCE_SUB}}` / `{{SOURCE_SUB_MUTED}}` | `lyra_telegram` / `aiogram handler` / `NatsBus.put` | left card |
| `{{SOURCE_TONE}}` | `cyan` | left card tone |
| `{{MIDDLE_NAME}}` / `{{MIDDLE_SUB}}` / `{{MIDDLE_SUB_MUTED}}` | `nats.container` / `single-node broker` / `` | center card |
| `{{MIDDLE_TONE}}` | `amber` | center card tone |
| `{{SINK_NAME}}` / `{{SINK_SUB_1}}` / `{{SINK_SUB_2}}` / `{{SINK_SUB_MUTED}}` | `lyra_hub` / `staging.put_nowait` / `hub.run → middleware` / `→ Pool._inbox` | right card (wide by default, fits 4 lines) |
| `{{SINK_TONE}}` | `amber` | right card tone |
| `{{EDGE_1_TONE}}` / `{{EDGE_2_TONE}}` | `cyan` / `amber` | arrow + label colors |
| `{{EDGE_1_LABEL}}` / `{{EDGE_1_HINT}}` | `publish` / `lyra.inbound.telegram.<bot>` | label above first arrow, 2 lines |
| `{{EDGE_2_LABEL}}` / `{{EDGE_2_HINT}}` | `subscribe` / `HUB_INBOUND queue group` | label above second arrow |
| `{{LEGEND}}` | `one-way publish · all (platform, bot_id) pairs fan into single staging queue` | bottom strip |

### Step 2 — Middle card shape

Default is `pill` (for buses, brokers, routers). For an action node
that holds a numbered sequence of steps (like 2.4 Outbound with 4
publish steps), swap `pill` → `wide`:

```html
<!-- bus / broker -->
<div class="fgraph-node amber pill" style="--x:50;--y:55;">
  <div class="fgraph-title amber">nats.container</div>
  ...

<!-- action node with 4 numbered substeps -->
<div class="fgraph-node amber wide" style="--x:50;--y:55;">
  <div class="fgraph-title amber">NatsChannelProxy.send_streaming</div>
  <div class="fgraph-sub">1. publish stream_start</div>
  <div class="fgraph-sub">2. publish chunks</div>
  <div class="fgraph-sub">3. publish stream_end</div>
  <div class="fgraph-sub warn">4. on exception → stream_error</div>
</div>
```

When using `wide`, bump aspect-ratio from `16/6` → `16/7` so the taller
middle card doesn't push labels off-screen.

### Step 3 — Bidirectional arrows (optional)

Default is single-direction (marker-end only). For request/reply:

```html
<path class="fg-edge cyan" d="M 25,55 L 39,55"
      marker-start="url(#fg-arr-cyan-lf)"
      marker-end="url(#fg-arr-cyan-lf)"/>
```

### Step 4 — Coordinates (rarely need to touch)

Defaults assume 3 default-width cards at x = 14 / 50 / 85. If the middle
is `wide` (30% width vs 22%), it extends further left/right; nudge the
arrow endpoints from `39,55 → 35,55` and `61,55 → 65,55`.

---

## How to customise `dual-cluster.html`

2 peers sharing 2 central resources. Use for HA pairs, dual-replica
workers, any cluster with 2 shared dependencies.

### Step 1 — Placeholders

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{TITLE}}` / `{{DATE}}` / etc. | standard diagram-meta | |
| `{{WRAP_TONE}}` | `purple` | container border color |
| `{{FRAME_LABEL}}` / `{{FRAME_SUB}}` | `Machine 1 · dual hub cluster` / `stateless routers + shared state` | dashed frame caption |
| `{{PEER_TONE}}` | `purple` | both peers share the same tone |
| `{{PEER_1_NAME}}` / `{{PEER_1_PILL}}` / `{{PEER_1_SUB}}` / `{{PEER_1_SUB_MUTED}}` | `lyra_hub-1` / `p=100` / `stateless router` / `no Pool in-memory` | top-left peer |
| `{{PEER_2_NAME}}` / `{{PEER_2_PILL}}` / `{{PEER_2_SUB}}` / `{{PEER_2_SUB_MUTED}}` | `lyra_hub-2` / `p=100` / ... | top-right peer (symmetric) |
| `{{RESOURCE_A_TONE}}` | `purple` | center resource tone |
| `{{RESOURCE_A_NAME}}` / `{{RESOURCE_A_SUB}}` / `{{RESOURCE_A_SUB_MUTED}}` | `Redis` / `AOF persistence` / `lyra:session:*` | center resource (pill by default) |
| `{{RESOURCE_A_LABEL}}` / `{{RESOURCE_A_HINT}}` | `SET / GET` / `lyra:session:<pool_id>` | single centered label above resource-a |
| `{{RESOURCE_B_TONE}}` | `amber` | bottom bus tone |
| `{{RESOURCE_B_NAME}}` / `{{RESOURCE_B_SUB}}` | `nats.container` / `shared HUB_INBOUND` | bottom bus (pill by default) |
| `{{RESOURCE_B_LABEL}}` / `{{RESOURCE_B_HINT}}` | `HUB_INBOUND` / `shared queue group` | single centered label above resource-b |
| `{{LEGEND}}` | `any user → either hub · state in Redis · adapters unchanged` | bottom strip |

### Step 2 — When you only have 1 shared resource

Strip the bottom half: remove the `{{RESOURCE_B_*}}` node, the 2 bus
arrows (lines with `d="M 15,21 Q 15,55 42,81"` and its symmetric pair),
and the `{{RESOURCE_B_LABEL}}` line. Change container aspect to `16/10`
(wide) — the cluster + 1 resource doesn't need square.

### Step 3 — When you have different tones per peer

Swap `{{PEER_TONE}}` for explicit per-peer tones by duplicating the node
block with different classes. You'll lose the symmetric look but it's
useful for primary/standby patterns (e.g. amber + green).

### Step 4 — Coordinates (if peers move)

Default peer positions are `(20, 16)` and `(80, 16)`. If you move them
further apart or closer, update arrow endpoints:

| Arrow | Current | Rule of thumb |
|-------|---------|---------------|
| peer-1 ↔ resource-a | `M 25,21 Q 32,36 44,50` | start at peer-1 bottom-right, end at resource-a top-left |
| peer-2 ↔ resource-a | `M 75,21 Q 68,36 56,50` | symmetric |
| peer-1 ↔ resource-b | `M 15,21 Q 15,55 42,81` | start at peer-1 bottom-left, bulge far-left to route around resource-a, end at resource-b top-left |
| peer-2 ↔ resource-b | `M 85,21 Q 85,55 58,81` | symmetric, bulge far-right |

The bulge control points at `x=15` / `x=85` are what route the long
arrows around resource-a. Don't lower them toward the center or they'll
cross through the resource card.

---

## How to customise `radial-ring.html`

6 nodes arranged in a circle, each connected to its neighbors. No center
hub — the topology is a true ring. Use for peer-to-peer meshes, ring
buffers, consensus rings.

### Step 1 — Placeholders

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{TITLE}}` / `{{DATE}}` / etc. | standard diagram-meta | |
| `{{WRAP_TONE}}` | `amber` | container border color |
| `{{NODE_1_NAME}}` / `{{NODE_1_PILL}}` / `{{NODE_1_SUB}}` / `{{NODE_1_SUB_MUTED}}` | `node-alpha` / `leader` / `consensus participant` / `port:8001` | top node |
| `{{NODE_2_NAME}}` ... `{{NODE_6_NAME}}` | ... | clockwise around the ring |
| `{{NODE_1_TONE}}` ... `{{NODE_6_TONE}}` | `amber` / `cyan` / `purple` / `green` / `amber` / `cyan` | per-node border color |
| `{{EDGE_1_TONE}}` ... `{{EDGE_6_TONE}}` | `cyan` | edge colors (can match node tones) |
| `{{EDGE_1_LABEL}}` ... `{{EDGE_6_LABEL}}` | `gossip` / `replicate` / `vote` | labels outside ring near each edge |
| `{{LEGEND}}` | `clockwise message flow · each node talks to neighbors` | bottom strip |

### Step 2 — Ring coordinates

Nodes are positioned at ~35% radius from center:

| Node | x | y | Position |
|------|---|---|----------|
| node-1 | 50 | 15 | top |
| node-2 | 80 | 30 | top-right |
| node-3 | 80 | 70 | bot-right |
| node-4 | 50 | 85 | bottom |
| node-5 | 20 | 70 | bot-left |
| node-6 | 20 | 30 | top-left |

### Step 3 — Edge paths (clockwise)

Each edge curves from one node to the next:

| Edge | Path |
|------|------|
| node-1 → node-2 | `M 62,18 Q 72,22 75,30` |
| node-2 → node-3 | `M 82,42 Q 84,50 82,58` |
| node-3 → node-4 | `M 75,70 Q 68,80 58,82` |
| node-4 → node-5 | `M 42,82 Q 32,80 25,70` |
| node-5 → node-6 | `M 18,58 Q 16,50 18,42` |
| node-6 → node-1 | `M 25,30 Q 28,22 38,18` |

For **bidirectional** edges (full-duplex ring), add `marker-start` to each path.

### Step 4 — Cross-ring edges (optional)

For skip connections (e.g. leader → all followers), add straight or curved
paths that cross the center:

```html
<!-- Leader (node-1) broadcasts to node-4 (opposite) -->
<path class="fg-edge amber" d="M 50,22 L 50,78"
      marker-end="url(#fg-arr-amber-rr)"/>
```

---

## How to customise `layered.html`

4 horizontal layers stacked vertically. Each layer has a dashed frame +
label. Use for classic tiered architectures.

### Step 1 — Placeholders

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{WRAP_TONE}}` | `amber` | container border color |
| `{{LAYER_1_LABEL}}` | `INGRESS` | top layer label |
| `{{LAYER_2_LABEL}}` | `ROUTER` | second layer |
| `{{LAYER_3_LABEL}}` | `WORKERS` | third layer |
| `{{LAYER_4_LABEL}}` | `STORAGE` | bottom layer |
| `{{LAYER_1_NODE_NAME}}` / `{{LAYER_1_NODE_SUB}}` | `gateway` / `nginx · TLS termination` | top node |
| `{{LAYER_2_NODE_NAME}}` / `{{LAYER_2_NODE_SUB}}` | `message-bus` / `NATS · subject routing` | center hub (pill) |
| `{{LAYER_3A_NAME}}` / `{{LAYER_3B_NAME}}` | `worker-a` / `worker-b` | side-by-side workers |
| `{{LAYER_4_NODE_NAME}}` / `{{LAYER_4_NODE_SUB}}` | `postgres` / `primary + replica` | bottom storage |
| `{{EDGE_1_TONE}}` / `{{EDGE_2_TONE}}` / `{{EDGE_3_TONE}}` | `cyan` / `amber` / `green` | vertical arrow colors |
| `{{EDGE_1_LABEL}}` / `{{EDGE_2_LABEL}}` / `{{EDGE_3_LABEL}}` | `request` / `dispatch` / `persist` | edge annotations |
| `{{LEGEND}}` | `request → router → workers → db` | bottom strip |

### Step 2 — 3-layer variant

Remove layer-4 (storage) for a simpler 3-tier:

1. Delete the layer-4 frame + label HTML
2. Delete the layer-4 node + fan-in arrows
3. Change container aspect from `tall` (4/5) → `square` (1/1)

### Step 3 — Fan-out / fan-in

Default layout has 1 → 1 → 2 → 1 nodes (fan-out to workers, fan-in to storage).
To change:

- **All layers single-node**: remove `{{LAYER_3B_*}}` node and one arrow from
  each fan-out/fan-in pair.
- **More workers**: add additional nodes at y=56 with x spaced evenly (20, 40,
  60, 80 for 4 workers).

---

## How to customise `machine-clusters.html`

3 machine frames side-by-side with cross-machine edges. Each frame has its
own dashed border + label.

### Step 1 — Placeholders

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{WRAP_TONE}}` | `amber` | container border color |
| `{{MACHINE_1_LABEL}}` / `{{MACHINE_1_SUB}}` | `Machine-1` / `192.168.1.10` | left frame |
| `{{MACHINE_2_LABEL}}` / `{{MACHINE_2_SUB}}` | `Machine-2` / `192.168.1.11` | center frame |
| `{{MACHINE_3_LABEL}}` / `{{MACHINE_3_SUB}}` | `Machine-3` / `192.168.1.12` | right frame |
| `{{M1_NODE_1_NAME}}` / `{{M1_NODE_1_SUB}}` | `hub` / `pool manager` | machine-1 node |
| `{{M1_NODE_2_NAME}}` / `{{M1_NODE_2_SUB}}` | `adapter` / `telegram` | machine-1 second node |
| `{{M2_NODE_1_NAME}}` ... `{{M3_NODE_1_NAME}}` | ... | per-machine nodes |
| `{{MACHINE_1_EDGE_TONE}}` / `{{MACHINE_1_EDGE_LABEL}}` | `amber` / `internal` | intra-machine edge |
| `{{CROSS_1_TONE}}` / `{{CROSS_1_LABEL}}` | `cyan` / `replicate` | cross-machine edge 1 |
| `{{CROSS_2_TONE}}` / `{{CROSS_2_LABEL}}` | `purple` / `sync` | cross-machine edge 2 |
| `{{LEGEND}}` | `each machine runs hub + adapter · cross-machine sync via NATS` | bottom strip |

### Step 2 — 2-machine variant

Remove machine-3 for a simpler side-by-side:

1. Delete the machine-3 frame + nodes
2. Delete the `CROSS_2_*` edge + label
3. Adjust container width / frame positions

### Step 3 — Cross-machine edge routing

Edges bulge into the gaps between frames to avoid crossing nodes:

| Edge | Path | Bulge point |
|------|------|-------------|
| Machine-1 → Machine-2 | `M 22,50 Q 32,45 40,50` | x=32 (gap between frames) |
| Machine-2 → Machine-3 | `M 60,50 Q 67,45 75,50` | x=67 (gap between frames) |

The control point y=45 lifts the curve slightly above center for visual clarity.

---

## How to customise `deployment-tiers.html`

3 deployment tiers stacked vertically with colored stripes. Promotion arrows
flow upward; data sync arrows flow between tiers.

### Step 1 — Placeholders

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{WRAP_TONE}}` | `amber` | container border color |
| `{{TIER_1_LABEL}}` / `{{TIER_1_SUB}}` | `PRODUCTION` / `live · users online` | top tier (green) |
| `{{TIER_2_LABEL}}` / `{{TIER_2_SUB}}` | `STAGING` / `pre-prod · QA testing` | middle tier (cyan) |
| `{{TIER_3_LABEL}}` / `{{TIER_3_SUB}}` | `DEV` / `local · development` | bottom tier (amber) |
| `{{TIER_1_SERVICE_NAME}}` / `{{TIER_1_SERVICE_SUB}}` | `lyra-hub-prod` / `p=100 · primary` | prod service |
| `{{TIER_1_DB_NAME}}` / `{{TIER_1_DB_SUB}}` | `postgres-prod` / `primary + replica` | prod database (pill) |
| `{{TIER_2_*}}` / `{{TIER_3_*}}` | ... | staging + dev nodes |
| `{{TIER_1_EDGE_LABEL}}` | `req ↔ db` | intra-tier edge label |
| `{{PROMOTE_1_LABEL}}` | `promote` | dev → staging arrow |
| `{{PROMOTE_2_LABEL}}` | `promote` | staging → prod arrow |
| `{{SYNC_LABEL}}` | `seed data` | prod → staging sync arrow |
| `{{LEGEND}}` | `promote upward · seed data downward · each tier isolated` | bottom strip |

### Step 2 — Tier tones (fixed)

Tiers use consistent colors for immediate recognition:

| Tier | Tone | CSS class |
|------|------|-----------|
| Production | green | `.fgraph-node.green` |
| Staging | cyan | `.fgraph-node.cyan` |
| Dev | amber | `.fgraph-node.amber` |

Data sync arrows use `purple` to distinguish from promotion flow.

### Step 3 — 2-tier variant

Remove the dev tier for a staging → prod view:

1. Delete tier-3 stripe + nodes
2. Delete `PROMOTE_1_*` placeholder and arrow
3. Adjust tier positions: prod at 20%, staging at 60%

---

## When NOT to use radial-hub

| If your diagram is… | Use instead |
|--------------------|-------------|
| Linear flow / pipeline | `linear-flow.html` — 3-stage horizontal |
| Sequence / message exchange | `lane-swim.html` — participant strips + phase swimlanes |
| State machine | *(retired 2026-06-22 — no current replacement; rebuild later)* |
| Dependency graph > 8 nodes | `dep-graph.html` — phase columns + issue cards (via `gen-deps.py`) |
| Tree / hierarchy | Start from `layered.html` and adapt |
| Rich cards stacked vertically (no hub) | `architecture.html` pattern from visual-explainer — CSS Grid cards + tiny inline SVG connectors |

`fgraph` is optimized for the specific case where **one center node connects
N peers** and the peers deserve **rich HTML card content** (pills, pill shapes,
warn lines, wrapped text).

---

## Authoring checklist

- [ ] Copied `radial-hub.html` to the output path
- [ ] Inlined `fgraph-base.css` into `{{FGRAPH_BASE}}` placeholder
- [ ] Filled all `{{TITLE}}`, `{{DATE}}`, `{{CATEGORY}}`, `{{COLOR}}` diagram-meta
- [ ] Filled all 6 node placeholders (`NODE_1_*` through `NODE_5_*` + `HUB_*`)
- [ ] Filled all 5 edge labels (`EDGE_1_*` through `EDGE_5_LABEL`)
- [ ] Verified tone classes match the domain (amber = hub, cyan = X, …)
- [ ] If a node moved: arrow path endpoints updated to match
- [ ] Container uses `square` aspect unless you tested `wide`/`tall` coordinates
- [ ] All labels fit within their assigned region (no overlap with nodes or other labels)
- [ ] Tested hover glow works (card lifts + box-shadow)
- [ ] Tested dark + light theme toggle (if shell includes one)

### Live mode (`gen-fgraph.py` / `data-fgraph="live"`)

- [ ] Wrap carries `data-fgraph="live"` **and** `data-interactive="true"` (interact.js needs the latter for spotlight + legend)
- [ ] Each node is `.fgraph-node` with a unique `data-node` (+ `data-group` to enable group filtering)
- [ ] Edges live in one `<script type="application/json" class="fgraph-edge-data">[{f,t,tone,mods,label}]</script>`; every `f`/`t` references an existing `data-node` id
- [ ] `<svg class="fgraph-edges" data-coord="px">` left **empty** — the runtime fills it (px coords, no `preserveAspectRatio`)
- [ ] `fgraph-auto.js` + `fgraph-interact.js` inlined into `<script>` (file://-safe, no CDN); they no-op without a live wrap
- [ ] Tones limited to the 7 reserved (`cyan/orange/purple/green/amber/red/dim`); unknown tones fall back to `dim`
- [ ] For print / PDF / JS-less embed: regenerate the same JSON with `--mode static`

---

## How to customise `lane-swim.html`

N vertical lanes (fixed x) × N rows — one node per row, any lane.
Phases are visual separators, not y-coordinate constraints.

### Step 1 — Diagram-meta placeholders

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{TITLE}}` / `{{DATE}}` / `{{CATEGORY}}` / `{{CAT_LABEL}}` / `{{COLOR}}` | standard diagram-meta | |
| `{{WRAP_TONE}}` | `teal` / `amber` / `green` | container border tone |
| `{{SLUG}}` | `lyra-flow` | unique suffix for arrowhead marker IDs — prevents collisions when multiple diagrams share a page |
| `{{CATEGORY_LABEL}}` | `ARCHITECTURE` | header eyebrow |
| `{{TITLE_PLAIN}}` / `{{TITLE_ACCENT}}` | `Lyra` / `Message Flow` | h1 split for accent color |
| `{{SUBTITLE}}` | `4 lanes · 14 rows · dashed = optional` | header sub |
| `{{DIAGRAM_ARIA}}` | `Lyra message flow swimlane` | `role="img"` aria-label |

### Step 2 — Lane placeholders

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{LANE_N_LABEL}}` | `Presentation` / `Application` / `Kernel` / `Infrastructure` | title in header strip |
| `{{LANE_N_TONE}}` | `teal` / `amber` / `accent` / `green` | tone class on `.fg-lane-title` |
| `{{LANE_N_X}}` | `22` / `41` / `62` / `82` | x-position as a bare integer (no `%`) |

Default x-positions for 4 lanes: `22, 41, 62, 82`.
Add/remove lane entries in the header strip, lane rules, and all node/label positions.

### Step 3 — Phase separators (visual only)

Each phase gets a `.fg-lane-phase-line` (horizontal rule) and a `.fg-lane-phase-lbl` (name):

```html
<div class="fg-lane-phase-lbl"  style="top:10%">① Receive</div>
<div class="fg-lane-phase-line" style="top:8%"></div>
```

The label `top` is the y of the first row in the phase. The line `top` is 2% above it.
Phases are purely decorative — they do not constrain node y-coordinates.

| Placeholder | Example | Notes |
|-------------|---------|-------|
| `{{PHASE_N_LABEL}}` | `① Receive` | text of the phase label |
| `{{PHASE_N_Y}}` | `10` | top% for the label (first row y) |
| `{{PHASE_N_Y_LINE}}` | `8` | top% for the horizontal rule (2 below label) |

### Step 4 — Rows (one node per row)

**Row-per-node layout rule:** every node gets its own y. Never place two nodes at
the same `top` value, even if they belong to the same phase.

Each row is two elements — node circle + label block — kept in sync on the same `top`:

```html
<!-- Row N — NodeName (lane x=41%) -->
<div class="fg-lane-node amber"
     style="left:41%; top:36%;"
     title="Rate Limit"></div>
<div class="fg-lane-label" style="left:calc(41% + 12px); top:36%;">
  <div class="fg-lane-title amber">
    Rate Limit <span class="fg-lane-tag">state</span>
  </div>
  <div class="fg-lane-sig">hub state read</div>
</div>
```

Tag variants:

| Class | Use for |
|-------|---------|
| *(none)* | generic tag |
| `.pure` | pure / kernel (orange) |
| `.opt` | optional / dashed |

Optional node: add `.optional` to `.fg-lane-node` — dashed border, 72% opacity.

**Row spacing:** 6 units per row (e.g. 10, 16, 22, 30...). Typical 14-row diagram
fits in `--fg-lane-min-height: 900px`. Scale: `≈ 60px × row_count + 120px`.

### Step 5 — Connector paths

**Same-lane vertical:**

```
M x,y1  L x,y2
```

**Cross-lane S-curve:**

```
M x1,y1  C x1,ymid  x2,ymid  x2,y2    where ymid = (y1 + y2) / 2
```

The control points share the same y (ymid). The curve departs x1 heading straight
down, crosses the lane gap smoothly at mid-height, and arrives at x2 heading straight
down — no kink. Classic git-graph rounding.

**Worked example** — Normalize (x=22, y=16) → Guards (x=62, y=30):

```
ymid = (16 + 30) / 2 = 23
path: M 22,16  C 22,23  62,23  62,30
```

### Step 6 — Parallel edges in the same lane (XOR / fork bend rule)

**Never draw two branches from the same source as coincident straight lines.**
Bend one with a perpendicular offset of ±2–3 units at the apex so both branches
read as distinct paths:

```
Branch A (right bulge, apex x+2):  M x,y1 C (x+2),cy1 (x+2),cy2 x,y2
Branch B (left bulge,  apex x−3):  M x,y1 C (x-3),cy1 (x-3),cy2 x,y2
```

**Worked example** — Router (x=41, y=50) splits to Command (y=56) and LLM (y=62):

```
Branch A → Command:  M 41,50 C 43,52 43,54 41,56    (right bulge, apex x=43)
Branch B → LLM:      M 41,50 C 38,54 38,58 41,62    (left bulge, apex x=38)
```

Edge labels sit at the apex of each branch (see next step).

### Step 7 — Edge labels (bulge-apex rule)

**Labels sit at the visible midpoint of the curve — for a bezier that is the BULGE
APEX, not the straight-line midpoint between endpoints.**

For a cubic `M x1,y1 C cx,cy1 cx,cy2 x2,y2`:

```
label --x = cx
label --y = (cy1 + cy2) / 2
```

**Worked example** — Branch B (Router→LLM): `M 41,50 C 38,54 38,58 41,62`

```
cx = 38,  cy1 = 54,  cy2 = 58
label: --x:38;  --y:56   (= (54+58)/2)
```

HTML:

```html
<div class="fg-edge-lbl amber" style="--x:38; --y:56">llm</div>
```

The `currentColor` border trick: the caller sets the tone class (e.g. `amber`), and
both the text color and the `border:1px solid currentColor` follow it automatically —
no extra per-tone rule is needed.

### Step 8 — Min-height knob

```html
<div class="fgraph-wrap lane-swim teal"
     style="--fg-lane-min-height: 900px;">
```

Default 900px suits 14 rows. Scale: `≈ 60px × row_count + 120px`.

### Step 9 — Add / remove lanes

To remove lane 4 (x=82): delete its `.fg-lane-title`, `.fg-lane-rule`, all nodes at `left:82%`, all connector paths ending at x=82. Spread remaining lanes: e.g. 3 lanes at 22, 50, 78.

To add lane 5: insert a title at `left:88%`, a rule at `left:88%`, and nodes/paths as needed. Compress existing lanes: e.g. 5 lanes at 18, 34, 50, 66, 82.

### Step 10 — Inline fgraph-base.css

Replace `{{FGRAPH_BASE}}` with the full content of `fgraph-base.css`.
Forge directive: inline, never link (Mode A).

---

## Live mode (JS-routed edges, opt-in)

Static templates hand-author every `<path>` and lean on layout rules R1–R7 to avoid overlap. **Live mode** keeps nodes declarative (`--x`/`--y`) but lets a small inlined runtime route the edges from the rendered node rectangles — anchors land on borders by construction (R4 / arrow-routing / R6 become automatic), it is resize-safe (no `preserveAspectRatio` stretch), and it adds hover-spotlight + tone/group filtering.

- **Runtime:** `fgraph-auto.js` (edge router) + `fgraph-interact.js` (spotlight + legend), inlined into the output `<script>` like `theme-toggle.js`. Live styling ships inside `fgraph-base.css`. The runtime is a strict no-op without a `data-fgraph="live"` wrap, so the static templates are unaffected.
- **Data-driven:** `scripts/gen-fgraph.py --in <graph>.json --out <file>.html [--mode live|static]` generalizes `gen-deps.py` to any node/edge graph (DAG-layered rows, R1 even-stride). `--mode static` emits Python-routed paths (print/PDF-safe); `--mode live` emits the contract below.
- **Contract:** wrap carries `data-fgraph="live"` and `data-interactive="true"` (interact.js requires it for spotlight/legend); nodes are `.fgraph-node` with `data-node` (+ optional `data-group`); edges are a `<script type="application/json" class="fgraph-edge-data">[{f,t,tone,mods,label}]</script>`; the `<svg class="fgraph-edges" data-coord="px">` is left empty for the runtime to fill.
- **When:** dense architecture (> 8 nodes) that must stay one diagram AND be explorable. For print / PDF / embed, use static mode (live needs JS).

> **`file://`-safety.** The inlined runtime (`fgraph-auto.js`, `fgraph-interact.js`) and every diagram style are CDN-free — a generated file renders fully offline by double-click. Web fonts (Inter / Outfit / Space Mono) still load from Google Fonts via `<link>`, exactly like every other forge template and `render-md.py`; with no network they degrade to the `system-ui` / `monospace` fallbacks declared in each `font-family` stack. Layout, tones, and edge routing are unaffected — only the typeface changes. Embedding the fonts is an ecosystem-wide decision (every template + the renderers), out of scope for a single generator.

## Extending the template set

All static topologies are documented here. For on-screen / interactive output two fd-engine types are available: `architecture` and `hub-spoke` (see the status banner at the top). Other fd-engine types (`flowchart`, `state`, `class`, `er`, `sequence`, `gantt`, `pie`) were retired 2026-06-22 — rebuild later. If you need a new static shape:

1. Start from the closest template
2. Reposition nodes via `--x`/`--y`
3. Adjust arrow paths to match
4. Add new CSS primitives to `fgraph-base.css` if needed (e.g. new tones, shapes)

Contributions welcome — mirror the `radial-hub.html` + README pattern.
