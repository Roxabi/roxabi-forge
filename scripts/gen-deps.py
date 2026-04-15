#!/usr/bin/env python3
"""
gen-deps.py — generate tab-dependencies.html from roadmap-deps.json.

Usage:
  python3 gen-deps.py [data.json] [--out path/to/tab-dependencies.html]
                      [--layout-overrides overrides.json]
  python3 gen-deps.py --github-sync   # pull closed dates from gh CLI, update JSON status

Renders per-phase dependency graphs via the native fgraph `dep-graph.html`
template (topological layer assignment in Python + elbow-routed SVG paths).
No runtime diagram library.
"""

import argparse
import html
import json
import os
import re
import sys
import subprocess
from collections import deque
from pathlib import Path

if 'DIAGRAMS_DIR' in os.environ and 'FORGE_DIR' not in os.environ:
    print('⚠ DIAGRAMS_DIR is deprecated — use FORGE_DIR', file=sys.stderr)
FORGE_DIR = Path(os.environ.get('FORGE_DIR', os.environ.get('DIAGRAMS_DIR', Path.home() / '.roxabi' / 'forge')))
DEFAULT_DATA = FORGE_DIR / "lyra/visuals/deps/roadmap-deps.json"
DEFAULT_OUT  = FORGE_DIR / "lyra/visuals/tabs/lyra-status/tab-dependencies.html"

CORRIDOR_WIDTH = 2  # horizontal corridor spacing for elbow routing (0..100 coord space)
TONE_CYCLE = ("amber", "cyan", "purple", "green")


# ── Helpers ──────────────────────────────────────────────────────────────────

def nid(issue_id: str) -> str:
    """Stable, HTML-id-safe node identifier."""
    return "N" + re.sub(r"[^a-zA-Z0-9]", "_", str(issue_id))


def node_label(issue: dict) -> str:
    label = issue.get("label", issue["id"])
    status = issue.get("status", "open")
    if status == "done_recent":
        return f"done {label}"
    if status == "deferred":
        return f"{label} (deferred)"
    return label


def phase_short(phase_id: str) -> str:
    """ph3a → Ph3a"""
    return phase_id.replace("ph", "Ph")


def domain_tone(domain: str, domain_tone_map: dict) -> str:
    """Pick a fgraph tone for a domain name (cached in domain_tone_map)."""
    if domain not in domain_tone_map:
        domain_tone_map[domain] = TONE_CYCLE[len(domain_tone_map) % len(TONE_CYCLE)]
    return domain_tone_map[domain]


def card_tone(issue: dict, domain_tone_map: dict) -> str:
    status = issue.get("status", "open")
    if status == "external":
        return "amber"  # warn tone
    if status == "virtual":
        return "purple"
    return domain_tone(issue.get("domain", ""), domain_tone_map)


def card_modifiers(issue: dict) -> str:
    """Extra class modifiers keyed off status. Done/deferred render as ghost (dashed, dimmed)."""
    status = issue.get("status", "open")
    if status in ("done_recent", "deferred"):
        return " ghost"
    return ""


# ── Layer assignment (Python-side topological sort) ──────────────────────────

def assign_layers(phase_issues: dict, all_issues: dict) -> dict:
    """Assign each intra-phase issue a layer index (0..L-1) via BFS.

    Roots: issues with no intra-phase blocker (blocked_by outside phase is ignored).
    Subsequent layers: max(layer of intra-phase blockers) + 1.
    Deterministic ordering via alphabetical id tie-break (input dicts are insertion-ordered).
    """
    # Build intra-phase parent lookup (blocked_by within the phase)
    parents = {iid: [bid for bid in iss.get("blocked_by", []) if bid in phase_issues]
               for iid, iss in phase_issues.items()}

    layer = {}
    queue = deque(sorted(iid for iid, p in parents.items() if not p))
    while queue:
        iid = queue.popleft()
        if iid in layer:
            continue
        blockers = parents[iid]
        if blockers and not all(b in layer for b in blockers):
            # Defer until all blockers are assigned.
            queue.append(iid)
            continue
        layer[iid] = max((layer[b] + 1 for b in blockers), default=0)
        # Enqueue children whose blockers are now satisfied.
        for child_id, child_parents in parents.items():
            if child_id not in layer and iid in child_parents:
                if all(b in layer for b in child_parents):
                    queue.append(child_id)

    # Any remaining (cycle safety) → drop at layer 0.
    for iid in phase_issues:
        layer.setdefault(iid, 0)
    return layer


# ── fgraph fragment generation ───────────────────────────────────────────────

def build_fgraph(phase_id, all_issues, domains, overrides=None, domain_tone_map=None):
    """Render the native dep-graph fgraph fragment for one phase.

    Shape: <div class="fgraph-wrap dep-graph green"> … </div> with phase-internal
    `.fg-dep-card` nodes positioned via --x/--y, elbow-routed SVG paths in
    <svg class="fgraph-edges">. No Mermaid, no runtime JS.
    """
    overrides = overrides or {}
    domain_tone_map = domain_tone_map if domain_tone_map is not None else {}

    phase_issues = {
        iid: iss for iid, iss in all_issues.items()
        if iss.get("phase") == phase_id and iss.get("status") != "done_old"
    }

    if not phase_issues:
        return (
            '<div class="fgraph-wrap dep-graph green" role="img" aria-label="no active issues">\n'
            '  <div class="fg-dep-card ghost" style="--x:50; --y:50;">'
            '<div class="issue-title">(no active issues)</div></div>\n'
            '</div>'
        )

    # 1. Topological layer assignment inside the phase.
    layer = assign_layers(phase_issues, all_issues)
    max_layer = max(layer.values())
    layer_count = max_layer + 1
    col_step = 100 / (layer_count + 1)

    # 2. Intra-layer ordering (alphabetical by id) → --y per card.
    buckets = {}  # layer_idx -> [iid, ...]
    for iid, lvl in sorted(layer.items()):
        buckets.setdefault(lvl, []).append(iid)

    positions = {}  # iid -> (x, y)
    for lvl, members in buckets.items():
        x = round(col_step * (lvl + 1), 2)
        row_step = 100 / (len(members) + 1)
        for i, iid in enumerate(members):
            y = round(row_step * (i + 1), 2)
            if iid in overrides:
                ov = overrides[iid]
                x = ov.get("x", x)
                y = ov.get("y", y)
            positions[iid] = (x, y)

    # 3. Ghost cards for cross-phase deps (one per unique (dir, blocker/blocked id)).
    ghost_in = {}   # gid -> (iid, blocker_issue)
    ghost_out = {}  # gid -> (iid, blocked_issue)
    for iid, issue in phase_issues.items():
        for blocker_id in issue.get("blocked_by", []):
            blocker = all_issues.get(blocker_id)
            if not blocker or blocker.get("status") == "done_old":
                continue
            if blocker.get("phase") != phase_id:
                ghost_in.setdefault(f"XI_{nid(blocker_id)}", (iid, blocker_id, blocker))
        for blocked_id in issue.get("blocks", []):
            blocked = all_issues.get(blocked_id)
            if not blocked or blocked.get("status") == "done_old":
                continue
            if blocked.get("phase") != phase_id:
                ghost_out.setdefault(f"XO_{nid(blocked_id)}", (iid, blocked_id, blocked))

    # Place ghost cards in reserved columns: incoming at --x=5 (left), outgoing at --x=95 (right).
    ghost_positions = {}
    for i, (gid, (iid, _blocker_id, _blocker)) in enumerate(ghost_in.items()):
        ghost_positions[gid] = (5.0, round(12 + i * 12, 2))
    for i, (gid, (iid, _blocked_id, _blocked)) in enumerate(ghost_out.items()):
        ghost_positions[gid] = (95.0, round(12 + i * 12, 2))

    # 4. Edges: intra-phase (straight vertical-ish) + cross-phase (elbow-routed).
    intra_edges = []   # (from_iid, to_iid)
    cross_edges = []   # (from_anchor, to_anchor)  — anchor is either iid or ghost gid
    for iid, issue in phase_issues.items():
        for blocked_id in issue.get("blocks", []):
            blocked = all_issues.get(blocked_id)
            if not blocked or blocked.get("status") == "done_old":
                continue
            if blocked.get("phase") == phase_id:
                intra_edges.append((iid, blocked_id))
            else:
                cross_edges.append((iid, f"XO_{nid(blocked_id)}"))
        for blocker_id in issue.get("blocked_by", []):
            blocker = all_issues.get(blocker_id)
            if not blocker or blocker.get("status") == "done_old":
                continue
            if blocker.get("phase") != phase_id:
                cross_edges.append((f"XI_{nid(blocker_id)}", iid))

    all_positions = {**positions, **ghost_positions}
    paths = route_elbows(intra_edges, cross_edges, all_positions)

    # 5. Emit HTML.
    out = [
        '<div class="fgraph-wrap dep-graph green" role="img" '
        f'aria-label="{html.escape(phase_id)} dependencies">',
        '  <svg class="fgraph-edges" viewBox="0 0 100 100" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">',
        '    <defs>',
        '      <marker id="fg-arr-amber"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="mk-amber"/></marker>',
        '      <marker id="fg-arr-cyan"   viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="mk-cyan"/></marker>',
        '      <marker id="fg-arr-purple" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="mk-purple"/></marker>',
        '    </defs>',
    ]
    out.extend(f'    {p}' for p in paths)
    out.append('  </svg>')

    # Issue cards
    for iid, issue in phase_issues.items():
        x, y = positions[iid]
        tone = card_tone(issue, domain_tone_map)
        mods = card_modifiers(issue)
        out.append(
            f'  <div class="fg-dep-card {tone}{mods}" style="--x:{x}; --y:{y};">'
            f'<div class="issue-num">#{html.escape(str(iid))}</div>'
            f'<div class="issue-title">{html.escape(node_label(issue))}</div></div>'
        )

    # Ghost cards (incoming + outgoing)
    for gid, (_iid, blocker_id, blocker) in ghost_in.items():
        x, y = ghost_positions[gid]
        ph = phase_short(blocker.get("phase", "?"))
        lbl = blocker.get("label", f"#{blocker_id}")
        out.append(
            f'  <div class="fg-dep-card cyan ghost" style="--x:{x}; --y:{y};" '
            f'data-gid="{gid}">'
            f'<div class="issue-num">← {html.escape(ph)}</div>'
            f'<div class="issue-title">{html.escape(lbl)}</div></div>'
        )
    for gid, (_iid, blocked_id, blocked) in ghost_out.items():
        x, y = ghost_positions[gid]
        ph = phase_short(blocked.get("phase", "?"))
        lbl = blocked.get("label", f"#{blocked_id}")
        out.append(
            f'  <div class="fg-dep-card purple ghost" style="--x:{x}; --y:{y};" '
            f'data-gid="{gid}">'
            f'<div class="issue-num">→ {html.escape(ph)}</div>'
            f'<div class="issue-title">{html.escape(lbl)}</div></div>'
        )

    out.append('</div>')
    return "\n".join(out)


def route_elbows(intra_edges, cross_edges, positions):
    """Return a list of <path> strings — elbow-routed cross-phase + straight intra-phase."""
    paths = []

    # Intra-phase: straight segment from source to target.
    for frm, to in intra_edges:
        if frm not in positions or to not in positions:
            continue
        sx, sy = positions[frm]
        tx, ty = positions[to]
        tone = "cyan"
        paths.append(
            f'<path class="fg-edge {tone}" d="M {sx},{sy} L {tx},{ty}" '
            f'marker-end="url(#fg-arr-{tone})" fill="none"/>'
        )

    # Cross-phase: sort by source --y so corridors don't overlap; assign corridor_x.
    valid_cross = [(a, b) for a, b in cross_edges
                   if a in positions and b in positions]
    valid_cross.sort(key=lambda ab: positions[ab[0]][1])

    for idx, (frm, to) in enumerate(valid_cross):
        sx, sy = positions[frm]
        tx, ty = positions[to]
        # Corridor mid-x between source and target, offset per edge index.
        base_corridor = (sx + tx) / 2
        corridor_x = round(base_corridor + (idx - len(valid_cross) / 2) * CORRIDOR_WIDTH, 2)
        # 3-segment elbow: M sx,sy H corridor_x V ty H tx
        tone = "amber" if frm.startswith("XI_") or to.startswith("XO_") else "purple"
        paths.append(
            f'<path class="fg-edge {tone}" '
            f'd="M {sx},{sy} H {corridor_x} V {ty} H {tx}" '
            f'marker-end="url(#fg-arr-{tone})" fill="none"/>'
        )

    return paths


def incoming_banner(phase_id, all_issues, phases_by_id):
    """Auto-derive the incoming dep banner text from cross-phase blocked_by."""
    seen = {}
    for iss in all_issues.values():
        if iss.get("phase") != phase_id or iss.get("status") == "done_old":
            continue
        for blocker_id in iss.get("blocked_by", []):
            blocker = all_issues.get(blocker_id)
            if not blocker or blocker.get("phase") == phase_id or blocker.get("status") == "done_old":
                continue
            ph = phase_short(blocker["phase"])
            lbl = blocker.get("label", f"#{blocker_id}")
            key = (blocker["phase"], blocker_id)
            if key not in seen:
                seen[key] = f"<strong>{lbl}</strong> ({ph})"

    if not seen:
        return "&#8649; no hard blockers &#8212; can start immediately"
    return "&#8592; " + " &middot; ".join(seen.values())


# ── Progress cards ────────────────────────────────────────────────────────────

def render_chain_card(chain, all_issues, domains):
    cid     = chain["id"]
    label   = chain["label"]
    color   = chain.get("color", "#6366f1")
    issues  = chain.get("issues", [])

    # Complete card
    if chain.get("complete"):
        return f"""
  <div class="card" style="border-left:3px solid var(--green)">
    <div class="card-header">
      <span class="card-title" style="color:var(--green)">{label}</span>
      <span class="card-version">&#10003; complete</span>
    </div>
    <div class="card-body" style="font-size:13px">
      <div style="margin-bottom:8px">
        <div style="background:var(--surface2);border-radius:99px;height:8px;overflow:hidden">
          <div style="background:var(--green);height:100%;width:100%;border-radius:99px"></div>
        </div>
      </div>
      <ul style="list-style:none;padding:0">
        <li style="color:var(--green)">&#10003; {chain.get('complete_note','')}</li>
      </ul>
      <div style="margin-top:8px;font-size:11px;color:var(--text-dim)">{chain.get('note','')}</div>
    </div>
  </div>"""

    # Count done vs open
    done_ids = [i for i in issues if all_issues.get(i, {}).get("status") == "done_recent"]
    open_ids = [i for i in issues if all_issues.get(i, {}).get("status") not in ("done_recent", "done_old")]
    total = len(issues)
    done_count = len(done_ids)
    pct = int(done_count / total * 100) if total else 0

    # Done list display
    done_labels = [all_issues[i]["label"] for i in done_ids if i in all_issues]
    open_labels = [all_issues[i]["label"] for i in open_ids if i in all_issues]

    done_row = ""
    if done_labels:
        done_row = f'<li style="color:var(--green)">&#10003; {", ".join(done_labels)}</li>'
    open_row = ""
    if open_labels:
        open_row = f'<li style="color:var(--text-dim)">&#9675; {", ".join(open_labels[:6])}{"&hellip;" if len(open_labels)>6 else ""}</li>'

    # Footer note
    if chain.get("blocked_note"):
        footer = f"""
      <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11px;font-family:var(--font-mono);display:flex;flex-wrap:wrap;align-items:center;gap:5px">
        <span style="color:#6366f1;margin-right:2px">&#8592; waiting on:</span>
        {_ghost_badges(chain['blocked_note'])}
      </div>"""
    elif chain.get("next_note"):
        footer = f'<div style="margin-top:8px;font-size:11px;color:var(--text-dim)"><strong>Next:</strong> {chain["next_note"]}</div>'
    else:
        footer = ""

    # Unlock row: find cross-phase outgoing deps for issues in this chain
    unlocks = _compute_unlocks(issues, all_issues, set(issues))
    unlock_row = ""
    if unlocks:
        badges = "".join(_badge_span(lbl) for lbl in unlocks)
        # Describe "when X done" trigger
        trigger = _unlock_trigger(chain, all_issues)
        unlock_row = f"""
      <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11px;font-family:var(--font-mono);display:flex;flex-wrap:wrap;align-items:center;gap:5px">
        <span style="color:#6366f1;margin-right:2px">&#8680; {trigger}:</span>
        {badges}
      </div>"""

    # Done recent closed items (ops-style)
    done_recent_rows = ""
    for d in chain.get("done_recent", []):
        done_recent_rows += f'<li style="color:var(--green)">&#10003; {d} &#8212; closed recently</li>'

    open_count_label = f"{done_count}/{total} done" if total else "0 open"

    return f"""
  <div class="card{'  card--active' if pct > 0 and pct < 100 else ''}" style="border-left:3px solid {color}">
    <div class="card-header">
      <span class="card-title" style="color:{color}">{label}</span>
      <span class="card-version">{open_count_label}</span>
    </div>
    <div class="card-body" style="font-size:13px">
      <div style="margin-bottom:8px">
        <div style="background:var(--surface2);border-radius:99px;height:8px;overflow:hidden">
          <div style="background:{color};height:100%;width:{pct}%;border-radius:99px"></div>
        </div>
      </div>
      <ul style="list-style:none;padding:0">
        {done_row}
        {open_row}
        {done_recent_rows}
      </ul>
      {footer}
      {unlock_row}
    </div>
  </div>"""


def _badge_span(lbl: str) -> str:
    return f'<span style="background:#0f172a;color:#94a3b8;border:1px dashed #6366f1;border-radius:4px;padding:2px 6px">{lbl}</span>'


def _ghost_badges(note_str):
    """Convert a plain text note into ghost badge spans."""
    return "".join(_badge_span(p.strip()) for p in note_str.split("+"))


def _compute_unlocks(chain_issue_ids, all_issues, chain_set):
    """Return ghost badge labels for cross-chain/cross-phase unlocks."""
    seen = set()
    for iid in chain_issue_ids:
        issue = all_issues.get(iid)
        if not issue:
            continue
        for blocked_id in issue.get("blocks", []):
            if blocked_id in chain_set:
                continue  # intra-chain, skip
            blocked = all_issues.get(blocked_id)
            if not blocked or blocked.get("status") == "done_old":
                continue
            ph = phase_short(blocked.get("phase", "?"))
            lbl = f"{ph} {blocked.get('label', blocked_id)}"
            seen.add(lbl)
    return list(seen)


def _unlock_trigger(chain, all_issues):
    """Describe the trigger condition for the unlock row."""
    # Find the last terminal node of the chain (most downstream)
    issues = chain.get("issues", [])
    for iid in reversed(issues):
        iss = all_issues.get(iid)
        if iss and iss.get("status") not in ("done_recent", "done_old"):
            return f"when {iss.get('label', iid)} done"
    return "when complete"


# ── Critical paths ────────────────────────────────────────────────────────────

def render_critical_paths(critical_paths, all_issues):
    html = ""
    for path in critical_paths:
        badges = ""
        for step in path["steps"]:
            sid = step.get("id")
            iss = all_issues.get(sid) if sid else None
            lbl = step.get("label") or (iss["label"] if iss else sid)
            st  = step.get("status", iss.get("status","planned") if iss else "planned")
            if st in ("done", "done_recent"):
                badges += f'<span class="badge badge--done" style="opacity:0.6">{lbl} &#10003;</span>\n'
            elif st == "north-star":
                badges += f'<span style="color:var(--green);font-weight:600">{lbl}</span>\n'
            else:
                badges += f'<span class="badge badge--planned">{lbl}</span>\n'
            if step != path["steps"][-1]:
                badges += '<span class="flow-arrow">&#8594;</span>\n'

        html += f"""    <div style="font-family:var(--font-mono);font-size:12px;color:var(--text-dim);margin-bottom:8px">{path['label']}</div>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:12px;font-family:var(--font-mono);margin-bottom:12px">
      {badges}
    </div>\n"""
    return html


# ── Full tab render ──────────────────────────────────────────────────────────

def render_tab(data, overrides=None):
    all_issues  = {i["id"]: i for i in data["issues"]}
    phases      = data["phases"]
    phases_by_id= {p["id"]: p for p in phases}
    domains     = data["domains"]
    chains      = data.get("chains", [])
    cp          = data.get("critical_paths", [])
    meta        = data.get("_meta", {})
    updated     = meta.get("updated", "")
    total       = meta.get("total_tracked", "?")
    done_days   = meta.get("done_visible_days", 7)

    # ── Legend ──
    domain_legend = ""
    for dom, cfg in domains.items():
        domain_legend += (
            f'<div style="display:flex;align-items:center;gap:6px">'
            f'<div style="width:12px;height:12px;border-radius:3px;background:{cfg["fill"]}"></div>'
            f' {dom.capitalize()}</div>\n'
        )

    # ── Phase blocks ──
    # Shared domain → fgraph tone map so colours stay consistent across phases.
    domain_tone_map = {}
    phase_blocks = ""
    for phase in phases:
        pid   = phase["id"]
        pname = phase["name"]
        pcolor= phase["color"]
        pnote = phase.get("note", "")
        note_span = f' <span style="font-size:11px;color:var(--green);font-weight:400;margin-left:8px">{pnote}</span>' if pnote else ""

        banner = incoming_banner(pid, all_issues, phases_by_id)
        fgraph_fragment = build_fgraph(
            pid, all_issues, domains,
            overrides=overrides,
            domain_tone_map=domain_tone_map,
        )

        phase_blocks += f"""
  <!-- ── {pname} ── -->
  <div class="dep-phase" style="--phase-color:{pcolor}">
    <div class="dep-phase__incoming">{banner}</div>
    <div class="dep-phase__header">{pname}{note_span}</div>
    <div class="dep-phase__viewer">{fgraph_fragment}</div>
  </div>
"""

    # ── Progress cards ──
    cards_html = ""
    for chain in chains:
        cards_html += render_chain_card(chain, all_issues, domains)

    # ── Critical paths ──
    cp_html = render_critical_paths(cp, all_issues)

    # ── Footer ──
    n_done = sum(1 for i in all_issues.values() if i.get("status") == "done_recent")
    n_chains = len(chains)

    return f"""<!-- Tab: Dependencies — auto-generated by gen-deps.py from roadmap-deps.json -->
<!-- DO NOT EDIT BY HAND — edit roadmap-deps.json then run gen-deps.py -->

<h2 class="sec-title"><span class="icon">&#9670;</span> Issue Dependencies</h2>
<p class="sec-desc">Each phase is a horizontal band with its own dependency tree. <span style="color:#6366f1">Indigo dashed</span> = cross-phase dep. <span style="color:#fbbf24">Amber dashed</span> = deferred.</p>

<!-- ── Legend ── -->
<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:var(--space-xl);font-size:12px;font-family:var(--font-mono);color:var(--text-dim)">
  {domain_legend}
  <div style="display:flex;align-items:center;gap:6px"><div style="width:12px;height:12px;border-radius:3px;background:#374151;border:2px dashed #6b7280"></div> Done</div>
  <div style="display:flex;align-items:center;gap:6px"><div style="width:12px;height:12px;border-radius:3px;background:#0f172a;border:2px dashed #6366f1"></div> Cross-phase dep</div>
  <div style="display:flex;align-items:center;gap:6px"><div style="width:12px;height:12px;border-radius:3px;background:#1a1000;border:2px dashed #ca8a04"></div> Deferred</div>
  <div style="display:flex;align-items:center;gap:6px"><div style="width:12px;height:12px;border-radius:3px;background:#1e1a2e;border:2px dashed #6d28d9"></div> No issue yet</div>
</div>

<!-- ── Phase bands ── -->
<div id="dep-board">
{phase_blocks}
</div>

<!-- ── Progress by Chain ── -->
<h3 class="sec-subtitle">Progress by Chain</h3>
<div class="card-grid" style="margin-bottom:var(--space-xl)">
{cards_html}
</div>

<!-- ── Critical Paths ── -->
<h3 class="sec-subtitle">Critical Paths</h3>
<div class="card" style="border-color:var(--accent);margin-bottom:var(--space-lg)">
  <div class="card-body">
{cp_html}  </div>
</div>

<p style="font-size:12px;color:var(--text-dim);font-family:var(--font-mono);text-align:center">
  ~{total} tracked issues &middot; {n_done} done recently &middot; {n_chains} chains &middot; generated {updated}
</p>
"""


# ── GitHub sync ───────────────────────────────────────────────────────────────

def github_sync(data_file: Path):
    """Pull closed dates from gh CLI and update issue statuses in JSON."""
    from datetime import datetime, timezone

    data = json.loads(data_file.read_text())
    all_issues = {i["id"]: i for i in data["issues"]}
    done_days  = data.get("_meta", {}).get("done_visible_days", 7)

    # Collect numeric IDs
    numeric_ids = [iid for iid in all_issues if iid.isdigit()]
    if not numeric_ids:
        print("No numeric issue IDs found.")
        return

    print(f"Syncing {len(numeric_ids)} issues from GitHub...")
    result = subprocess.run(
        ["gh", "issue", "list", "--state", "all",
         "--json", "number,state,closedAt", "--limit", "500"],
        capture_output=True, text=True, cwd=Path.home() / "projects/lyra"
    )
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
        return

    gh_issues = {str(i["number"]): i for i in json.loads(result.stdout)}
    today = datetime.now(timezone.utc)

    changed = 0
    for iid, issue in all_issues.items():
        if not iid.isdigit():
            continue
        gh = gh_issues.get(iid)
        if not gh:
            continue
        if gh["state"] == "OPEN":
            new_status = issue.get("status", "open")
            if new_status in ("done_recent", "done_old"):
                issue["status"] = "open"
                changed += 1
        elif gh["state"] == "CLOSED":
            closed_at = datetime.fromisoformat(gh["closedAt"].replace("Z", "+00:00"))
            days_ago = (today - closed_at).days
            new_status = "done_recent" if days_ago <= done_days else "done_old"
            if issue.get("status") != new_status:
                issue["status"] = new_status
                issue["closed_days_ago"] = days_ago
                changed += 1

    if changed:
        data_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"Updated {changed} issue statuses in {data_file}")
    else:
        print("No status changes.")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="gen-deps.py",
        description="Generate tab-dependencies.html from roadmap-deps.json using the native fgraph dep-graph template.",
    )
    parser.add_argument("data", nargs="?", default=str(DEFAULT_DATA),
                        help="Path to roadmap-deps.json (default: $FORGE_DIR/lyra/visuals/deps/roadmap-deps.json)")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="Path to output tab-dependencies.html")
    parser.add_argument("--github-sync", action="store_true",
                        help="Pull closed dates from gh CLI and update JSON status before rendering")
    parser.add_argument("--layout-overrides", default=None, metavar="PATH",
                        help="Optional JSON file mapping {issue_id: {x, y}} to pin node positions (0..100 space); escape hatch for unreadable elbow-routed output")
    args = parser.parse_args()

    data_file = Path(args.data)
    out_file = Path(args.out)

    if args.github_sync:
        github_sync(data_file)

    overrides = None
    if args.layout_overrides:
        overrides = json.loads(Path(args.layout_overrides).read_text())

    data = json.loads(data_file.read_text())
    rendered = render_tab(data, overrides=overrides)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(rendered)
    print(f"Generated {out_file} ({len(rendered):,} bytes)")


if __name__ == "__main__":
    main()
