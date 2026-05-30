#!/usr/bin/env python3
"""
gen-fgraph.py — data-driven generator for the fgraph diagram engine.

Generalises gen-deps.py to arbitrary node/edge graphs. Reads a JSON
input spec and emits a self-contained HTML file with auto-placed nodes.

Supports two modes:
  live   (default) — nodes + JSON edge data + empty SVG; JS runtime draws edges.
  static           — nodes + Python-computed SVG paths; no JS required.

Usage:
  python3 gen-fgraph.py --in <data.json> --out <output.html> [--mode live|static] [--title "..."]

Input JSON schema:
  {
    "meta": {"title": "...", "accent": "cyan"},
    "nodes": [{"id":"hub","label":"lyra-hub","sub":"...","shape":"pill","tone":"orange","group":"core","x":null,"y":null}],
    "edges": [{"f":"hub","t":"nats","tone":"orange","mods":["thick"],"label":"lyra.*"}],
    "groups": [{"id":"core","label":"core services"}]
  }

Placement rules:
  R1 even-stride: N nodes in row → centers at (100/(2N)) * (2i+1) for i=0..N-1
  R2 min-gap: inter-center gap − nodeWidth ≥ 2% (warns if tight, never overlaps)
  Layers assigned via longest-path DAG depth (BFS from sources); cycles land at layer 0.
"""

import argparse
import html
import json
import math
import os
import sys
from collections import deque
from datetime import date
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "plugins" / "forge" / "references" / "graph-templates"
BASE_DIR = REPO_ROOT / "plugins" / "forge" / "references" / "base"
AESTHETICS_DIR = REPO_ROOT / "plugins" / "forge" / "references" / "aesthetics"

FGRAPH_AUTO_JS = TEMPLATES_DIR / "fgraph-auto.js"
FGRAPH_INTERACT_JS = TEMPLATES_DIR / "fgraph-interact.js"

VALID_TONES = {"cyan", "orange", "purple", "green", "red", "amber", "dim"}
VALID_SHAPES = {"pill", "hexagon", "cylinder", "diamond", "circle", "folded"}
VALID_MODS = {"dashed", "thick", "animated"}

# Node width assumption for R2 gap check (% of wrap width)
NODE_WIDTH_PCT = 18.0
# Minimum inter-center gap (% of wrap) required (R2)
MIN_GAP_PCT = 2.0
# Vertical stride between layers (% of wrap height)
LAYER_Y_STRIDE = 22.0
# First layer Y offset
LAYER_Y_FIRST = 15.0
# Elbow corridor width for static mode
CORRIDOR_WIDTH = 2.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_css_file(path: Path) -> str:
    """Read a CSS file, return its content or empty string if missing."""
    if path.exists():
        return path.read_text()
    return ""


# ── Layer assignment ───────────────────────────────────────────────────────────

def assign_layers(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    """Assign each node a DAG depth layer (longest-path from sources).

    Sources = nodes with no incoming edges (layer 0).
    Subsequent layers = max(layer of parents) + 1.
    Cycles: back-edges are ignored for layering; cycle members that remain
    unreachable from any root fall back to layer 0 with a stderr warning.

    Shares the BFS longest-path skeleton with gen-deps.py::assign_layers but is
    deliberately NOT extracted to a shared module. The two differ in data model
    (generic nodes/edges here vs. issue dicts keyed on `blocked_by` there) and
    this variant adds explicit cycle-edge detection. Both scripts are standalone
    stdlib CLIs with hyphenated, non-importable names by convention; a shared
    layout module would be the first cross-script import and would pull the
    production gen-deps.py into this change's blast radius. DRY-ing the core
    layering across both generators is left as a separate, dedicated refactor.
    """
    node_ids = {n["id"] for n in nodes}

    # Build adjacency: parents[id] = set of nodes that point TO id
    parents: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    children: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    for e in edges:
        f, t = e["f"], e["t"]
        if f in node_ids and t in node_ids:
            parents[t].add(f)
            children[f].add(t)

    # Detect and break cycles: iterative DFS to find back-edges, remove them
    # from parents (used only for layering, not emitted edges).
    visited: set[str] = set()
    cycle_edges: set[tuple[str, str]] = set()

    for start in sorted(node_ids):
        if start in visited:
            continue
        # stack entries: (node, iterator-over-children, current-path-set)
        path: list[str] = []
        path_set: set[str] = set()
        stack: list[tuple[str, bool]] = [(start, True)]
        while stack:
            nid, entering = stack.pop()
            if entering:
                if nid in visited:
                    continue
                visited.add(nid)
                path.append(nid)
                path_set.add(nid)
                # push exit marker first, then children
                stack.append((nid, False))
                for child in sorted(children.get(nid, [])):
                    if child not in visited:
                        stack.append((child, True))
                    elif child in path_set:
                        cycle_edges.add((nid, child))
            else:
                # leaving nid: pop from current path
                if path and path[-1] == nid:
                    path.pop()
                    path_set.discard(nid)

    # Remove back-edges from parents for layering only
    parents_dag: dict[str, set[str]] = {
        nid: {p for p in pset if (p, nid) not in cycle_edges}
        for nid, pset in parents.items()
    }

    layer: dict[str, int] = {}
    queue: deque[str] = deque(
        sorted(nid for nid, pset in parents_dag.items() if not pset)
    )

    while queue:
        nid = queue.popleft()
        if nid in layer:
            continue
        pset = parents_dag[nid]
        layer[nid] = max((layer[p] + 1 for p in pset if p in layer), default=0)
        for child in sorted(children.get(nid, [])):
            if child not in layer:
                if all(p in layer for p in parents_dag.get(child, set())):
                    queue.append(child)

    # Cycle fallback
    unassigned = [nid for nid in node_ids if nid not in layer]
    if unassigned:
        print(
            f"WARNING assign_layers: {len(unassigned)} node(s) in a cycle or "
            f"unreachable from roots — assigned to layer 0: {sorted(unassigned)}",
            file=sys.stderr,
        )
        for nid in unassigned:
            layer[nid] = 0

    return layer


# ── Auto-placement ─────────────────────────────────────────────────────────────

def auto_place(nodes: list[dict], edges: list[dict]) -> dict[str, tuple[float, float]]:
    """Compute --x / --y for each node (0..100 space).

    - Nodes with explicit x/y in input keep their values.
    - Others: layer-based rows (top→bottom), R1 even-stride within each row.
    - R2 min-gap check: warns when a row is too tight; the layout is still
      emitted and may overlap at N>=6 nodes per row.

    Returns dict[node_id → (x, y)].
    Also prints the placement verification table to stderr.
    """
    # Separate explicit vs auto nodes
    explicit: dict[str, tuple[float, float]] = {}
    auto_nodes: list[dict] = []
    for n in nodes:
        if n.get("x") is not None and n.get("y") is not None:
            explicit[n["id"]] = (float(n["x"]), float(n["y"]))
        else:
            auto_nodes.append(n)

    if not auto_nodes:
        return explicit

    layer = assign_layers(auto_nodes, edges)
    max_layer = max(layer.values()) if layer else 0
    layer_count = max_layer + 1

    # Bucket by layer, sort within layer: group then id for determinism
    buckets: dict[int, list[dict]] = {}
    for n in auto_nodes:
        lvl = layer[n["id"]]
        buckets.setdefault(lvl, []).append(n)
    for lvl in buckets:
        buckets[lvl].sort(key=lambda n: (n.get("group", ""), n["id"]))

    positions: dict[str, tuple[float, float]] = {}

    print("\n── Placement verification table ─────────────────────────────────────", file=sys.stderr)
    print(f"{'Layer':>5}  {'N':>3}  {'Node ID':<20}  {'x':>7}  {'y':>7}  {'Gap check'}", file=sys.stderr)
    print(f"{'─'*5}  {'─'*3}  {'─'*20}  {'─'*7}  {'─'*7}  {'─'*30}", file=sys.stderr)

    for lvl in range(layer_count):
        members = buckets.get(lvl, [])
        if not members:
            continue
        n_nodes = len(members)
        y = round(LAYER_Y_FIRST + lvl * LAYER_Y_STRIDE, 2)

        # R1 formula: centers at (100 / (2N)) * (2i+1)
        stride = 100.0 / (2 * n_nodes)
        centers = [round(stride * (2 * i + 1), 2) for i in range(n_nodes)]

        # R2 gap check: inter-center gap = stride * 2; usable gap = gap - node_width
        inter_center_gap = stride * 2  # distance between adjacent centers
        usable_gap = inter_center_gap - NODE_WIDTH_PCT

        gap_status = "OK"
        if usable_gap < MIN_GAP_PCT:
            gap_status = f"WARN tight ({usable_gap:.1f}% < {MIN_GAP_PCT}%)"
            print(
                f"WARNING R2 gap violation in layer {lvl}: {n_nodes} nodes, "
                f"usable_gap={usable_gap:.1f}% < {MIN_GAP_PCT}% min. "
                f"Consider reducing NODE_WIDTH_PCT or splitting the row.",
                file=sys.stderr,
            )

        for i, node in enumerate(members):
            x = centers[i]
            positions[node["id"]] = (x, y)
            # R1 verification: assert center == (100/(2N)) * (2i+1)
            expected = round((100.0 / (2 * n_nodes)) * (2 * i + 1), 2)
            assert abs(x - expected) < 0.01, (
                f"R1 violation: node {node['id']} x={x} expected={expected}"
            )
            row_gap_info = f"inter={inter_center_gap:.1f}% usable={usable_gap:.1f}% {gap_status}" if i == 0 else ""
            print(f"{lvl:>5}  {n_nodes:>3}  {node['id']:<20}  {x:>7.2f}  {y:>7.2f}  {row_gap_info}", file=sys.stderr)

    print(f"{'─'*80}", file=sys.stderr)
    print(f"Total auto-placed: {len(positions)} nodes | Explicit: {len(explicit)} nodes", file=sys.stderr)
    print(file=sys.stderr)

    positions.update(explicit)
    return positions


# ── Static mode: edge routing ──────────────────────────────────────────────────

def route_static_edges(
    edges: list[dict],
    positions: dict[str, tuple[float, float]],
) -> list[str]:
    """Compute SVG <path> elements for static mode.

    - Straight segment when endpoints share x or y (within tolerance).
    - 2-segment elbow (M sx,sy H mid_x V ty / M sx,sy V mid_y H tx) otherwise.
    Sort by source-y for corridor assignments (prevent overlap on shared mid).
    """
    valid = [(e, positions[e["f"]], positions[e["t"]])
             for e in edges
             if e["f"] in positions and e["t"] in positions]

    # Sort by source-y for corridor ordering
    valid.sort(key=lambda t: t[1][1])

    paths = []
    corridor_offsets: dict[tuple, int] = {}  # (f,t) → offset index (for bundles)

    for edge, (sx, sy), (tx, ty) in valid:
        tone = edge.get("tone", "dim")
        tone = tone if tone in VALID_TONES else "dim"
        mods = edge.get("mods") or []
        mod_str = " ".join(m for m in mods if m in VALID_MODS)
        cls = f"fg-edge {tone}" + (f" {mod_str}" if mod_str else "")
        marker = f"url(#fg-arr-{tone})"

        dx = abs(tx - sx)
        dy = abs(ty - sy)
        tol = 0.5  # treat as aligned if diff < 0.5 units

        if dx < tol:
            # Same column — straight vertical
            d = f"M {sx},{sy} L {tx},{ty}"
        elif dy < tol:
            # Same row — straight horizontal
            d = f"M {sx},{sy} L {tx},{ty}"
        else:
            # Elbow: go vertical first then horizontal (matches dep-graph convention)
            # Use mid-y slightly offset for readability (avoids bunching at exact mid)
            key = (round(sx), round(tx))
            idx = corridor_offsets.get(key, 0)
            corridor_offsets[key] = idx + 1
            mid_y = round((sy + ty) / 2 + idx * CORRIDOR_WIDTH, 2)
            d = f"M {sx},{sy} L {sx},{mid_y} L {tx},{mid_y} L {tx},{ty}"

        paths.append(
            f'    <path class="{cls}" d="{d}" '
            f'marker-end="{marker}" fill="none"/>'
        )

    return paths


# ── CSS inlining ───────────────────────────────────────────────────────────────

def inline_base_css() -> str:
    """Inline the base token layer for a self-contained file.

    Only `reset.css` is pulled from `base/`: it is the *sole* token-defining
    file (the full `:root` palette — --bg/--text/--accent/--border plus the tone
    tokens --cyan/--amber/--green/--purple/--red, in both dark + light themes).
    Everything the diagram draws resolves from this plus `fgraph-base.css`
    (inline_fgraph_css — which self-defines --fg-orange and maps tone `dim` to
    --text-muted) and `page_chrome_css`.

    The other `base/` files are excluded by design, not oversight: they style
    artifact types a diagram does not contain — typography.css (prose + IBM-Plex
    `code` blocks), components.css (cards), explainer-base.css (~36 KB explainer
    chrome), layout.css (doc grid). Inlining them would add dead rules and
    references to fonts this page never loads, not robustness. Add a file here
    only if the diagram itself starts consuming a token it defines.
    """
    parts = []
    for name in ("reset.css",):
        f = BASE_DIR / name
        if f.exists():
            parts.append(f"/* ── {name} ── */\n" + f.read_text())
    return "\n\n".join(parts)


def inline_fgraph_css() -> str:
    """Inline fgraph-base.css."""
    f = TEMPLATES_DIR / "fgraph-base.css"
    if f.exists():
        return f.read_text()
    return "/* fgraph-base.css not found */"


def page_chrome_css() -> str:
    """Minimal page-level styling for the generated HTML."""
    return """
/* ── gen-fgraph.py page chrome ── */
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', system-ui, sans-serif;
  padding: 32px 24px 48px;
  min-height: 100vh;
  font-size: 13px;
  line-height: 1.5;
}
header {
  margin-bottom: 28px;
}
.header-eyebrow {
  font-family: 'Space Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 8px;
}
h1 {
  font-family: 'Outfit', sans-serif;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text);
  margin-bottom: 6px;
}
h1 .accent { color: var(--accent); }
.header-subtitle {
  font-family: 'Space Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
}
main {
  max-width: 1100px;
  margin: 0 auto;
}
/* fgraph-wrap wide variant for the generator */
.fgraph-wrap.fgraph-gen {
  aspect-ratio: 16 / 9;
  max-width: 1060px;
}
"""


# ── Marker defs for static mode ────────────────────────────────────────────────

# Static-mode arrowhead markers. markerWidth/Height=6 in the DEFAULT (strokeWidth)
# marker units — NOT userSpaceOnUse — matching the proven gen-deps.py convention
# for an SVG with viewBox="0 0 100 100" preserveAspectRatio="none". userSpaceOnUse
# here would anisotropically stretch arrowheads with the 16:9 wrap (x and y scale
# differ). Live mode (fgraph-auto.js) DOES use userSpaceOnUse=8 because its SVG is
# px-space with no preserveAspectRatio — different context, different convention.
STATIC_MARKER_DEFS = """    <defs>
      <marker id="fg-arr-cyan"    viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="mk-cyan"/></marker>
      <marker id="fg-arr-orange"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="mk-orange"/></marker>
      <marker id="fg-arr-purple"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="mk-purple"/></marker>
      <marker id="fg-arr-green"   viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="mk-green"/></marker>
      <marker id="fg-arr-amber"   viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="mk-amber"/></marker>
      <marker id="fg-arr-red"     viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="mk-red"/></marker>
      <marker id="fg-arr-dim"     viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="mk-dim"/></marker>
    </defs>"""


# ── HTML rendering ─────────────────────────────────────────────────────────────

def render_node(node: dict, x: float, y: float) -> str:
    """Emit a single .fgraph-node div."""
    nid = html.escape(node["id"])
    label = html.escape(node.get("label", node["id"]))
    sub = html.escape(node.get("sub", ""))
    shape = node.get("shape", "")
    tone = node.get("tone", "")
    group = node.get("group", "")

    classes = ["fgraph-node"]
    if shape and shape in VALID_SHAPES:
        classes.append(shape)
    if tone and tone in VALID_TONES:
        classes.append(tone)

    cls_str = " ".join(classes)
    style = f"--x:{x:.2f};--y:{y:.2f}"

    group_attr = f' data-group="{html.escape(group)}"' if group else ""

    safe_tone = tone if tone in VALID_TONES else ""
    title_tone = f' {safe_tone}' if safe_tone else ""
    sub_html = f'\n    <div class="fgraph-sub">{sub}</div>' if sub else ""

    return (
        f'  <div class="{cls_str}" data-node="{nid}"{group_attr} style="{style}">\n'
        f'    <div class="fgraph-title{title_tone}">{label}</div>{sub_html}\n'
        f'  </div>'
    )


def render_live(data: dict, positions: dict, title: str) -> str:
    """Render live-mode fgraph wrap: nodes + JSON edge data + empty SVG."""
    meta = data.get("meta", {})
    accent = meta.get("accent", "cyan")
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    node_divs = []
    for node in nodes:
        nid = node["id"]
        if nid in positions:
            x, y = positions[nid]
            node_divs.append(render_node(node, x, y))

    # Sanitise edge data: only include valid mods and tones
    clean_edges = []
    for e in edges:
        ce = {
            "f": e["f"],
            "t": e["t"],
            "tone": e.get("tone", "dim") if e.get("tone") in VALID_TONES else "dim",
        }
        mods = [m for m in (e.get("mods") or []) if m in VALID_MODS]
        if mods:
            ce["mods"] = mods
        if e.get("label"):
            ce["label"] = e["label"]
        clean_edges.append(ce)

    edge_json = json.dumps(clean_edges, separators=(",", ":"), ensure_ascii=False)
    edge_json = edge_json.replace("</", "<\\/")

    nodes_html = "\n".join(node_divs)
    return f"""\
<div class="fgraph-wrap fgraph-gen {html.escape(accent)}" data-fgraph="live" data-interactive="true" role="region" aria-label="{html.escape(title)}">
  <div class="fgraph-frame"></div>
  <div class="fgraph-frame-lbl">{html.escape(title)}</div>
{nodes_html}
  <script type="application/json" class="fgraph-edge-data">
{edge_json}
  </script>
  <!-- runtime draws here; empty + px coords in live mode -->
  <svg class="fgraph-edges" data-coord="px"></svg>
</div>"""


def render_static(data: dict, positions: dict, title: str) -> str:
    """Render static-mode fgraph wrap: nodes + computed SVG paths."""
    meta = data.get("meta", {})
    accent = meta.get("accent", "cyan")
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # Compute paths in 0..100 coordinate space (SVG viewBox 0 0 100 100)
    paths = route_static_edges(edges, positions)

    node_divs = []
    for node in nodes:
        nid = node["id"]
        if nid in positions:
            x, y = positions[nid]
            node_divs.append(render_node(node, x, y))

    paths_html = "\n".join(paths) if paths else "    <!-- no edges -->"
    nodes_html = "\n".join(node_divs)

    return f"""\
<div class="fgraph-wrap fgraph-gen {html.escape(accent)}"
     role="img" aria-label="{html.escape(title)}">
  <div class="fgraph-frame"></div>
  <div class="fgraph-frame-lbl">{html.escape(title)}</div>
  <svg class="fgraph-edges" viewBox="0 0 100 100" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
{STATIC_MARKER_DEFS}
{paths_html}
  </svg>
{nodes_html}
</div>"""


# ── JS inlining / fallback ─────────────────────────────────────────────────────

FALLBACK_STUB_JS = """\
/* gen-fgraph.py fallback stub router — fgraph-auto.js not found at generation time.
   This 15-line stub reads .fgraph-edge-data JSON and draws straight lines so the
   file renders standalone. Replace with the real fgraph-auto.js for full routing. */
(function(){
  var wraps = document.querySelectorAll('.fgraph-wrap[data-fgraph="live"]')
  wraps.forEach(function(wrap){
    var script = wrap.querySelector('script.fgraph-edge-data')
    var svg = wrap.querySelector('svg.fgraph-edges[data-coord="px"]')
    if(!script||!svg) return
    var edges; try{edges=JSON.parse(script.textContent)}catch(e){return}
    var NS='http://www.w3.org/2000/svg'
    var W=wrap.offsetWidth, H=wrap.offsetHeight
    svg.setAttribute('viewBox','0 0 '+W+' '+H)
    var nodeMap={}; wrap.querySelectorAll('[data-node]').forEach(function(el){nodeMap[el.dataset.node]=el})
    edges.forEach(function(e){
      var fEl=nodeMap[e.f], tEl=nodeMap[e.t]; if(!fEl||!tEl) return
      var wb=wrap.getBoundingClientRect()
      var fb=fEl.getBoundingClientRect(), tb=tEl.getBoundingClientRect()
      var x1=fb.left-wb.left+fb.width/2, y1=fb.top-wb.top+fb.height/2
      var x2=tb.left-wb.left+tb.width/2, y2=tb.top-wb.top+tb.height/2
      var p=document.createElementNS(NS,'path')
      p.setAttribute('d','M'+x1+','+y1+' L'+x2+','+y2)
      p.setAttribute('class','fg-edge '+(e.tone||'dim')+' '+(e.mods||[]).join(' '))
      svg.appendChild(p)
    })
  })
  window.addEventListener('load', function(){ wraps.forEach(function(w){ w.dispatchEvent(new Event('resize')) }) })
})()"""


def get_js_block(mode: str) -> str:
    """Return the JS block for live mode: real file if available, else stub."""
    if mode != "live":
        return ""

    parts = []
    found_any = False

    for js_path in [FGRAPH_AUTO_JS, FGRAPH_INTERACT_JS]:
        if js_path.exists():
            parts.append(
                f"<!-- {js_path.name} — inlined by gen-fgraph.py -->\n"
                f"<script>\n{js_path.read_text()}\n</script>"
            )
            found_any = True

    if not found_any:
        parts.append(
            "<!-- RUNTIME_JS — fgraph-auto.js / fgraph-interact.js not found at "
            f"{TEMPLATES_DIR}; using 15-line fallback stub -->\n"
            f"<script>\n{FALLBACK_STUB_JS}\n</script>"
        )
    elif not FGRAPH_AUTO_JS.exists():
        # fgraph-interact.js exists but fgraph-auto.js missing — prepend stub
        parts.insert(
            0,
            f"<!-- RUNTIME_JS fgraph-auto.js not found — using fallback stub -->\n"
            f"<script>\n{FALLBACK_STUB_JS}\n</script>",
        )

    return "\n\n".join(parts)


# ── Full document render ────────────────────────────────────────────────────────

def render_document(data: dict, mode: str, title_override: str | None) -> str:
    """Render the complete self-contained HTML document."""
    meta = data.get("meta", {})
    title = title_override or meta.get("title", "fgraph diagram")
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    positions = auto_place(nodes, edges)

    # Warn on duplicate node ids
    node_ids = [n["id"] for n in nodes]
    if len(set(node_ids)) < len(node_ids):
        print(
            f"WARNING: duplicate node ids detected ({len(node_ids) - len(set(node_ids))} duplicate(s))",
            file=sys.stderr,
        )

    # Warn on edges referencing unknown node ids
    known_ids = set(node_ids)
    for e in edges:
        if e.get("f") not in known_ids:
            print(f"WARNING: edge references unknown source node id '{e.get('f')}'", file=sys.stderr)
        if e.get("t") not in known_ids:
            print(f"WARNING: edge references unknown target node id '{e.get('t')}'", file=sys.stderr)

    if mode == "live":
        diagram_html = render_live(data, positions, title)
    else:
        diagram_html = render_static(data, positions, title)

    js_block = get_js_block(mode)
    mode_badge = "live · JS-routed" if mode == "live" else "static · Python-routed"

    base_css = inline_base_css()
    fgraph_css = inline_fgraph_css()
    page_css = page_chrome_css()

    gen_date = date.today().isoformat()

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- diagram-meta:start -->
<meta name="diagram:title"     content="{html.escape(title)}">
<meta name="diagram:date"      content="{gen_date}">
<meta name="diagram:generator" content="gen-fgraph.py">
<meta name="diagram:mode"      content="{mode}">
<!-- diagram-meta:end -->
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ══════════════════════════════════════════════════════
   gen-fgraph.py — auto-generated, {gen_date}, mode={mode}
   ══════════════════════════════════════════════════════ */

/* ── base/reset.css ── */
{base_css}

/* ── graph-templates/fgraph-base.css ── */
{fgraph_css}

/* ── page chrome ── */
{page_css}
</style>
</head>
<body>

<header>
  <div class="header-eyebrow">fgraph · {html.escape(mode_badge)}</div>
  <h1>{html.escape(title)}</h1>
  <p class="header-subtitle">generated by gen-fgraph.py · {gen_date}</p>
</header>

<main>
{diagram_html}
</main>

{js_block}
</body>
</html>"""


# ── Self-verify ────────────────────────────────────────────────────────────────

def verify_html(html_content: str, mode: str) -> bool:
    """Parse the emitted HTML for basic well-formedness and edge-data JSON validity.

    Returns True if all checks pass, False otherwise.
    """
    import re as _re
    ok = True

    # Check fgraph-edge-data JSON block (live mode)
    if mode == "live":
        m = _re.search(
            r'<script[^>]+class="fgraph-edge-data"[^>]*>\s*(.*?)\s*</script>',
            html_content, _re.DOTALL
        )
        if not m:
            print("VERIFY FAIL: no .fgraph-edge-data <script> block found", file=sys.stderr)
            ok = False
        else:
            try:
                json.loads(m.group(1))
                print("VERIFY OK: .fgraph-edge-data is valid JSON")
            except json.JSONDecodeError as e:
                print(f"VERIFY FAIL: .fgraph-edge-data is invalid JSON: {e}", file=sys.stderr)
                ok = False

        # Check SVG with data-coord="px"
        if 'data-coord="px"' not in html_content:
            print("VERIFY FAIL: live mode missing <svg data-coord='px'>", file=sys.stderr)
            ok = False
        else:
            print("VERIFY OK: <svg class='fgraph-edges' data-coord='px'> present")

        # Check data-fgraph="live"
        if 'data-fgraph="live"' not in html_content:
            print("VERIFY FAIL: live mode missing data-fgraph='live' on wrap", file=sys.stderr)
            ok = False
        else:
            print("VERIFY OK: data-fgraph='live' present on wrap")

    else:  # static
        # Check no edge-data script in static mode
        if 'fgraph-edge-data' in html_content:
            print("VERIFY WARN: static mode contains fgraph-edge-data (unexpected)", file=sys.stderr)
        else:
            print("VERIFY OK: static mode — no JSON edge-data block (correct)")

        # Check defs block present
        if '<defs>' not in html_content:
            print("VERIFY FAIL: static mode missing SVG <defs>", file=sys.stderr)
            ok = False
        else:
            print("VERIFY OK: static mode SVG <defs> present")

    # Check node divs exist
    import re as _re2
    nodes_found = len(_re2.findall(r'data-node="[^"]+"', html_content))
    print(f"VERIFY: {nodes_found} data-node elements found in output")

    return ok


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="gen-fgraph.py",
        description=(
            "Generate a self-contained fgraph diagram HTML from a JSON node/edge spec. "
            "Mirrors gen-deps.py conventions: stdlib-only, argparse CLI, R1 auto-placement."
        ),
    )
    parser.add_argument("--in",  dest="input",  required=True, metavar="JSON",
                        help="Path to input JSON file (see schema in docstring)")
    parser.add_argument("--out", dest="output", required=True, metavar="HTML",
                        help="Path to output HTML file")
    parser.add_argument("--mode", choices=("live", "static"), default="static",
                        help="Output mode: 'static' (Python-routed SVG, default) or 'live' (JS-routed edges)")
    parser.add_argument("--title", default=None,
                        help="Override diagram title (default: meta.title from JSON)")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(in_path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in {in_path}: {e}", file=sys.stderr)
        sys.exit(1)

    rendered = render_document(data, args.mode, args.title)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered)
    print(f"Generated {out_path} ({len(rendered):,} bytes) [mode={args.mode}]")

    # Self-verify
    print()
    all_ok = verify_html(rendered, args.mode)
    if not all_ok:
        print("VERIFY: one or more checks failed — inspect output", file=sys.stderr)
        sys.exit(2)
    print("VERIFY: all checks passed")


if __name__ == "__main__":
    main()
