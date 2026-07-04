#!/usr/bin/env python3
"""Bake runnable preview HTML from authoring scaffolds (fgraph + gallery templates)."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "plugins" / "forge" / "references"
FG_TEMPLATES = REFS / "graph-templates"
FG_EXAMPLES = FG_TEMPLATES / "examples"
GAL_TEMPLATES = REFS / "gallery-templates"
GAL_EXAMPLES = GAL_TEMPLATES / "examples"
DIAG_EXAMPLES = REFS / "diagrams" / "examples"

FG_SLUGS = [
    "lane-swim", "radial-hub", "linear-flow", "layered", "deployment-tiers",
    "machine-clusters", "dual-cluster", "radial-ring", "dep-graph",
    "funnel", "scatter", "bubble", "radar",
]
GAL_SLUGS = [
    "simple-gallery", "pivot-gallery", "comparison-gallery",
    "multi-mode-gallery", "audio-gallery",
]

CHART_TEMPLATES = {"funnel", "scatter", "bubble", "radar"}
ARCH_FG_SLUGS = {
    "lane-swim", "radial-hub", "linear-flow", "layered", "deployment-tiers",
    "machine-clusters", "dual-cluster", "radial-ring", "dep-graph",
}

EMBED_HERO_SCRIPT = """  <script>
    (function () {
      if (/[?&]embed=hero/.test(location.search)) {
        document.documentElement.classList.add('embed-hero');
      }
    })();
  </script>"""

FG_PREVIEW_SHELL_CSS = """
/* fgraph preview shell — craft-like centered layout (baked) */
html.embed-hero, html.embed-hero body { background: transparent !important; }
body.fg-preview {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 100vh;
  padding: 32px 20px !important;
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
}
body.fg-preview header { display: none !important; }
body.fg-preview main {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  padding: 0 !important;
}
body.fg-preview .fg-preview-title {
  text-align: center;
  margin-bottom: 20px;
  width: 100%;
}
body.fg-preview .fg-preview-title h1 {
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 6px;
}
body.fg-preview .fg-preview-title h1 .accent { color: var(--accent); }
body.fg-preview .fg-preview-title p {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
}
body.fg-preview .fgraph-wrap {
  flex-shrink: 0;
  box-shadow: 0 0 48px rgba(240, 180, 41, 0.08);
}
html.embed-hero body.fg-preview { padding: 12px 8px !important; min-height: 0; }
"""

LANE_SWIM_DEMO_EDGES = """    <path class="fg-lane-curve cyan"
          d="M 12,10 L 12,16"
          marker-end="url(#arr-laneswim-teal)"/>
    <path class="fg-lane-curve cyan"
          d="M 12,16 C 12,23 38,23 38,30"
          marker-end="url(#arr-laneswim-accent)"/>
    <path class="fg-lane-curve amber"
          d="M 38,30 C 38,40 62,40 62,50"
          marker-end="url(#arr-laneswim-amber)"/>
    <path class="fg-lane-curve green"
          d="M 62,50 C 62,60 88,60 88,70"
          marker-end="url(#arr-laneswim-green)"/>"""

DEMO_SVG = (
    "data:image/svg+xml,"
    + "%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E"
    + "%3Crect fill='%23161922' width='200' height='200'/%3E"
    + "%3Ctext x='100' y='108' text-anchor='middle' fill='%23f0b429' "
    + "font-family='monospace' font-size='13'%3Edemo%3C/text%3E%3C/svg%3E"
)


def read_text(*parts: str) -> str:
    return "\n".join((REFS / p).read_text(encoding="utf-8") for p in parts)


def base_styles_block() -> str:
    return read_text(
        "base/reset.css",
        "base/layout.css",
        "base/typography.css",
        "base/components.css",
        "base/explainer-base.css",
    )


def aesthetic_block() -> str:
    return (REFS / "aesthetics/roxabi.css").read_text(encoding="utf-8")


def fgraph_base_block() -> str:
    return (FG_TEMPLATES / "fgraph-base.css").read_text(encoding="utf-8")


def inline_fgraph_css(html: str, slug: str) -> str:
    if slug in CHART_TEMPLATES:
        return html
    base = base_styles_block()
    aesthetic = aesthetic_block()
    fgraph = fgraph_base_block()
    html = re.sub(
        r"/\* \{\{BASE_STYLES\}\}[^*]*\*/",
        f"/* base + explainer — baked */\n{base}",
        html,
        count=1,
    )
    html = re.sub(
        r"/\* \{\{AESTHETIC_STYLES\}\}[^*]*\*/",
        f"/* roxabi aesthetic — baked */\n{aesthetic}",
        html,
        count=1,
    )
    html = re.sub(
        r"/\* \{\{FGRAPH_BASE\}\}[^*]*\*/",
        f"/* fgraph-base — baked */\n{fgraph}",
        html,
        count=1,
    )
    return html


def slug_title(slug: str) -> str:
    return "Forge · " + slug.replace("-", " ").title()


def common_meta(slug: str) -> dict[str, str]:
    title = slug_title(slug)
    plain, _, accent = title.partition(" · ")
    return {
        "TITLE": title,
        "DATE": "2026-07-04",
        "CATEGORY": "architecture",
        "CAT_LABEL": "Reference",
        "COLOR": "gold",
        "CATEGORY_LABEL": "FORGE REFERENCE",
        "TITLE_PLAIN": plain,
        "TITLE_ACCENT": accent or slug.replace("-", " ").title(),
        "SUBTITLE": "Baked preview — file:// safe · regenerate via bake-reference-previews.py",
        "DIAGRAM_ARIA": f"{title} diagram",
        "DIAGRAM_ARIA_LABEL": f"{title} diagram",
        "WRAP_TONE": "amber",
        "SLUG": slug.replace("-", ""),
        "LEGEND": "forge reference preview",
    }


def fallback_placeholder(name: str, slug: str) -> str:
    if name.endswith("_TONE"):
        tones = ["cyan", "amber", "green", "purple", "teal", "accent"]
        idx = sum(ord(c) for c in name) % len(tones)
        return tones[idx]
    if name.endswith("_X") or name.endswith("_LX"):
        return "50"
    if name.endswith("_Y") or name.endswith("_Y_LINE"):
        m = re.search(r"(\d+)", name)
        return str(12 + (int(m.group(1)) * 11 if m else 50))
    if name.endswith("_LABEL") or name.endswith("_LBL"):
        return "flow"
    if name.endswith("_NAME"):
        return "node"
    if name.endswith("_TAG"):
        return "svc"
    if name.endswith("_SIG") or name.endswith("_SUB") or name.endswith("_HINT"):
        return "preview"
    if name.startswith("STAGE_") and name.endswith("_LABEL"):
        return "Stage"
    if name.startswith("STAGE_") and name.endswith("_VALUE"):
        return "100"
    if name.endswith("_POINTS"):
        return "55,20 70,20 65,35 40,35"
    if name == "ACCENT_COLOR":
        return "#f0b429"
    if name == "ACCENT_DIM":
        return "rgba(240,180,41,0.12)"
    if name.startswith("CONV_"):
        return "25"
    if name in {"GRIDLINES", "TICK_MARKS", "SERIES", "LEGEND", "EDGES", "NODES"}:
        return ""
    return slug.replace("-", " ")


def funnel_geometry() -> dict[str, str]:
    values = [1000, 400, 120, 40]
    labels = ["Awareness", "Interest", "Trial", "Paid"]
    cx, y_top, y_bot = 55.0, 8.0, 96.0
    n = len(values)
    stage_h = (y_bot - y_top) / n
    max_hw, min_hw = 26.0, 5.0

    def hw(v: float) -> float:
        return max(max_hw * math.sqrt(v / values[0]), min_hw)

    out: dict[str, str] = {}
    for i, (lab, val) in enumerate(zip(labels, values)):
        hw_top = hw(values[i])
        hw_bot = hw(values[i + 1]) if i < n - 1 else min_hw
        y1 = y_top + i * stage_h
        y2 = y1 + stage_h
        pts = (
            f"{cx - hw_top:.1f},{y1:.1f} {cx + hw_top:.1f},{y1:.1f} "
            f"{cx + hw_bot:.1f},{y2:.1f} {cx - hw_bot:.1f},{y2:.1f}"
        )
        out[f"STAGE_{i}_POINTS"] = pts
        out[f"STAGE_{i}_LABEL"] = lab
        out[f"STAGE_{i}_VALUE"] = f"{val:,}"
        ly = (y1 + y2) / 2
        out[f"LABEL_{i}_Y"] = f"{ly:.1f}"
        out[f"VALUE_{i}_Y"] = f"{ly + 4.5:.1f}"
        out[f"CONNECTOR_{i}_X2"] = f"{cx - (hw_top + hw_bot) / 2:.1f}"
        if i > 0:
            sep_y = y1
            out[f"SEP_{i}_Y"] = f"{sep_y:.1f}"
            out[f"SEP_{i}_X1"] = f"{cx - hw(values[i]):.1f}"
            out[f"SEP_{i}_X2"] = f"{cx + hw(values[i]):.1f}"
            rate = round(100 * values[i] / values[i - 1])
            out[f"CONV_{i - 1}_{i}"] = str(rate)
            out[f"CONV_{i}_LX"] = f"{cx + hw(values[i]):.1f}"
    return out


def scatter_geometry() -> dict[str, str]:
    grid = "\n".join(
        f'    <line class="fg-grid-line" x1="10" y1="{y}" x2="90" y2="{y}"/>'
        for y in (28, 48, 68)
    )
    ticks = "\n".join(
        [
            '    <text class="fg-tick" x="10" y="92">0</text>',
            '    <text class="fg-tick" x="50" y="92">50</text>',
            '    <text class="fg-tick" x="90" y="92">100</text>',
            '    <text class="fg-tick" x="6" y="88">0</text>',
            '    <text class="fg-tick" x="6" y="48">50</text>',
            '    <text class="fg-tick" x="6" y="12">100</text>',
        ]
    )
    series = "\n".join(
        [
            '    <circle cx="22" cy="72" r="1.6" fill="var(--cyan)"/>',
            '    <circle cx="38" cy="58" r="1.6" fill="var(--cyan)"/>',
            '    <circle cx="55" cy="44" r="1.6" fill="var(--amber)"/>',
            '    <circle cx="72" cy="30" r="1.6" fill="var(--amber)"/>',
            '    <circle cx="82" cy="18" r="1.6" fill="var(--purple)"/>',
        ]
    )
    legend = (
        '    <circle cx="12" cy="10.5" r="1.2" fill="var(--cyan)"/>'
        '<text class="fg-legend-lbl" x="15" y="11.3">series A</text>'
    )
    return {
        "GRIDLINES": grid,
        "TICK_MARKS": ticks,
        "SERIES": series,
        "LEGEND": legend,
        "X_AXIS_TITLE": "latency",
        "Y_AXIS_TITLE": "throughput",
    }


def template_overrides(slug: str) -> dict[str, str]:
    o = common_meta(slug)
    if slug == "lane-swim":
        o.update({
            "LANE_1_LABEL": "Ingress", "LANE_1_TONE": "cyan", "LANE_1_X": "12",
            "LANE_2_LABEL": "Router", "LANE_2_TONE": "amber", "LANE_2_X": "38",
            "LANE_3_LABEL": "Kernel", "LANE_3_TONE": "green", "LANE_3_X": "62",
            "LANE_4_LABEL": "Infra", "LANE_4_TONE": "purple", "LANE_4_X": "88",
            "PHASE_1_LABEL": "① Receive", "PHASE_1_Y": "8", "PHASE_1_Y_LINE": "8",
            "PHASE_2_LABEL": "② Process", "PHASE_2_Y": "28", "PHASE_2_Y_LINE": "28",
            "PHASE_3_LABEL": "③ Emit", "PHASE_3_Y": "55", "PHASE_3_Y_LINE": "55",
            "PHASE_4_LABEL": "④ Store", "PHASE_4_Y": "78", "PHASE_4_Y_LINE": "78",
            "NODE_A_NAME": "Webhook", "NODE_A_TAG": "HTTP", "NODE_A_SIG": "ingress",
            "NODE_B_NAME": "Validate", "NODE_B_TAG": "opt", "NODE_B_SIG": "schema",
            "NODE_C_NAME": "Router", "NODE_C_TAG": "bus", "NODE_C_SIG": "nats",
            "NODE_D_NAME": "Worker", "NODE_D_TAG": "pure", "NODE_D_SIG": "handler",
            "NODE_E_NAME": "Postgres", "NODE_E_TAG": "db", "NODE_E_SIG": "persist",
            "EDGE_LBL_A": "dispatch",
        })
    elif slug == "linear-flow":
        o.update({
            "WRAP_TONE": "cyan",
            "SOURCE_TONE": "cyan", "SOURCE_NAME": "Client", "SOURCE_SUB": "browser",
            "SOURCE_SUB_MUTED": "request",
            "MIDDLE_TONE": "amber", "MIDDLE_NAME": "API Gateway", "MIDDLE_SUB": "route",
            "MIDDLE_SUB_MUTED": "auth",
            "SINK_TONE": "green", "SINK_NAME": "Service", "SINK_SUB_1": "handler",
            "SINK_SUB_2": "persist", "SINK_SUB_MUTED": "response",
            "EDGE_1_TONE": "cyan", "EDGE_1_LABEL": "HTTP", "EDGE_1_HINT": "443",
            "EDGE_2_TONE": "green", "EDGE_2_LABEL": "gRPC", "EDGE_2_HINT": "mtls",
        })
    elif slug == "radial-hub":
        o.update({
            "WRAP_TONE": "amber",
            "FRAME_LABEL": "Core", "FRAME_SUB": "hub",
            "HUB_NAME": "Hub", "HUB_SUB": "orchestrator", "HUB_SUB_MUTED": "message bus",
            "NODE_1_NAME": "Ingress", "NODE_1_PILL": "in", "NODE_1_SUB": "webhook",
            "NODE_1_WARN": "",
            "NODE_2_NAME": "Queue", "NODE_2_PILL": "bus", "NODE_2_SUB": "nats",
            "NODE_2_SUB_MUTED": "stream",
            "NODE_3_NAME": "Worker", "NODE_3_PILL": "svc", "NODE_3_SUB": "handler",
            "NODE_3_SUB_MUTED": "stateless",
            "NODE_4_NAME": "Cache", "NODE_4_PILL": "kv", "NODE_4_SUB": "redis",
            "NODE_4_SUB_MUTED": "hot",
            "NODE_5_NAME": "Store", "NODE_5_PILL": "db", "NODE_5_SUB": "postgres",
            "NODE_5_SUB_MUTED": "soT",
            "EDGE_1_LABEL": "push", "EDGE_1_LABEL_B": "", "EDGE_1_HINT": "async",
            "EDGE_2_LABEL": "pull", "EDGE_3_LABEL": "fan-out",
            "EDGE_4_LABEL": "read", "EDGE_5_LABEL": "write",
        })
    elif slug == "layered":
        o.update({
            "WRAP_TONE": "cyan",
            "LAYER_1_LABEL": "Presentation", "LAYER_2_LABEL": "Application",
            "LAYER_3_LABEL": "Domain", "LAYER_4_LABEL": "Infrastructure",
            "LAYER_1_NODE_TONE": "cyan", "LAYER_1_NODE_NAME": "UI Shell",
            "LAYER_1_NODE_SUB": "routes", "LAYER_1_NODE_SUB_MUTED": "SSR",
            "LAYER_2_NODE_TONE": "amber", "LAYER_2_NODE_NAME": "API Gateway",
            "LAYER_2_NODE_SUB": "auth", "LAYER_2_NODE_SUB_MUTED": "rate-limit",
            "LAYER_3A_TONE": "green", "LAYER_3A_NAME": "Worker",
            "LAYER_3A_SUB": "handler", "LAYER_3A_SUB_MUTED": "stateless",
            "LAYER_3B_TONE": "purple", "LAYER_3B_NAME": "Scheduler",
            "LAYER_3B_SUB": "cron", "LAYER_3B_SUB_MUTED": "jobs",
            "LAYER_4_NODE_TONE": "purple", "LAYER_4_NODE_NAME": "Postgres",
            "LAYER_4_NODE_SUB": "primary", "LAYER_4_NODE_SUB_MUTED": "replicated",
            "EDGE_1_TONE": "cyan", "EDGE_1_LABEL": "HTTP",
            "EDGE_2_TONE": "amber", "EDGE_2_LABEL": "dispatch",
            "EDGE_3_TONE": "green", "EDGE_3_LABEL": "persist",
        })
    elif slug == "deployment-tiers":
        o.update({
            "WRAP_TONE": "green",
            "TIER_1_LABEL": "Production", "TIER_1_SUB": "live traffic",
            "TIER_2_LABEL": "Staging", "TIER_2_SUB": "pre-release",
            "TIER_3_LABEL": "Preview", "TIER_3_SUB": "PR branches",
            "TIER_1_EDGE_LABEL": "serve", "TIER_2_EDGE_LABEL": "validate",
            "PROMOTE_1_LABEL": "promote", "PROMOTE_2_LABEL": "rollback",
            "SYNC_LABEL": "sync schema",
            "TIER_1_SERVICE_NAME": "api-prod", "TIER_1_SERVICE_SUB": "3 replicas",
            "TIER_1_DB_NAME": "db-prod", "TIER_1_DB_SUB": "primary",
            "TIER_2_SERVICE_NAME": "api-stg", "TIER_2_SERVICE_SUB": "1 replica",
            "TIER_2_DB_NAME": "db-stg", "TIER_2_DB_SUB": "snapshot",
            "TIER_3_SERVICE_NAME": "api-pr", "TIER_3_SERVICE_SUB": "ephemeral",
            "TIER_3_SERVICE_SUB_MUTED": "auto-delete",
        })
    elif slug == "machine-clusters":
        o.update({
            "WRAP_TONE": "amber",
            "MACHINE_1_LABEL": "Host A", "MACHINE_1_SUB": "edge",
            "MACHINE_2_LABEL": "Host B", "MACHINE_2_SUB": "core",
            "MACHINE_3_LABEL": "Host C", "MACHINE_3_SUB": "data",
            "MACHINE_1_EDGE_TONE": "amber", "MACHINE_1_EDGE_LABEL": "local",
            "MACHINE_2_EDGE_TONE": "cyan", "MACHINE_2_EDGE_LABEL": "local",
            "CROSS_1_TONE": "cyan", "CROSS_1_LABEL": "mesh",
            "CROSS_2_TONE": "purple", "CROSS_2_LABEL": "replicate",
            "M1_NODE_1_TONE": "amber", "M1_NODE_1_NAME": "ingress",
            "M1_NODE_1_SUB": ":443", "M1_NODE_2_TONE": "amber",
            "M1_NODE_2_NAME": "worker", "M1_NODE_2_SUB": "pool",
            "M2_NODE_1_TONE": "cyan", "M2_NODE_1_NAME": "router",
            "M2_NODE_1_SUB": "nats", "M2_NODE_2_TONE": "cyan",
            "M2_NODE_2_NAME": "cache", "M2_NODE_2_SUB": "redis",
            "M3_NODE_1_TONE": "purple", "M3_NODE_1_NAME": "postgres",
            "M3_NODE_1_SUB": "primary",
        })
    elif slug == "dual-cluster":
        o.update({
            "WRAP_TONE": "cyan",
            "FRAME_LABEL": "Dual cluster", "FRAME_SUB": "active / passive",
            "PEER_TONE": "cyan", "PEER_1_NAME": "Cluster A", "PEER_1_PILL": "active",
            "PEER_1_SUB": "us-east", "PEER_1_SUB_MUTED": "primary",
            "PEER_2_NAME": "Cluster B", "PEER_2_PILL": "standby",
            "PEER_2_SUB": "eu-west", "PEER_2_SUB_MUTED": "replica",
            "RESOURCE_A_TONE": "amber", "RESOURCE_A_NAME": "Control plane",
            "RESOURCE_A_SUB": "orchestrator", "RESOURCE_A_SUB_MUTED": "leader",
            "RESOURCE_A_LABEL": "failover", "RESOURCE_A_HINT": "health",
            "RESOURCE_B_TONE": "green", "RESOURCE_B_NAME": "Data plane",
            "RESOURCE_B_SUB": "synced", "RESOURCE_B_LABEL": "replicate",
            "RESOURCE_B_HINT": "async",
        })
    elif slug == "radial-ring":
        o.update({
            "WRAP_TONE": "purple",
            "EDGE_1_TONE": "amber", "EDGE_1_LABEL": "ingest",
            "EDGE_2_TONE": "cyan", "EDGE_2_LABEL": "route",
            "EDGE_3_TONE": "green", "EDGE_3_LABEL": "emit",
            "EDGE_4_TONE": "purple", "EDGE_4_LABEL": "store",
            "EDGE_5_TONE": "cyan", "EDGE_5_LABEL": "cache",
            "EDGE_6_TONE": "amber", "EDGE_6_LABEL": "observe",
            "NODE_1_TONE": "amber", "NODE_1_NAME": "Ingress", "NODE_1_PILL": "in",
            "NODE_1_SUB": "webhook", "NODE_1_SUB_MUTED": "HTTPS",
            "NODE_2_TONE": "cyan", "NODE_2_NAME": "Router", "NODE_2_PILL": "bus",
            "NODE_2_SUB": "nats", "NODE_2_SUB_MUTED": "stream",
            "NODE_3_TONE": "green", "NODE_3_NAME": "Worker", "NODE_3_PILL": "svc",
            "NODE_3_SUB": "handler", "NODE_3_SUB_MUTED": "stateless",
            "NODE_4_TONE": "purple", "NODE_4_NAME": "Store", "NODE_4_PILL": "db",
            "NODE_4_SUB": "postgres", "NODE_4_SUB_MUTED": "soT",
            "NODE_5_TONE": "cyan", "NODE_5_NAME": "Cache", "NODE_5_PILL": "kv",
            "NODE_5_SUB": "redis", "NODE_5_SUB_MUTED": "hot",
            "NODE_6_TONE": "amber", "NODE_6_NAME": "Metrics", "NODE_6_PILL": "obs",
            "NODE_6_SUB": "prometheus", "NODE_6_SUB_MUTED": "scrape",
        })
    elif slug == "dep-graph":
        o.update({
            "PHASE_1_LABEL": "Spec", "PHASE_2_LABEL": "Build",
            "PHASE_3_LABEL": "Test", "PHASE_4_LABEL": "Ship",
            "CARD_1_NUM": "#12", "CARD_1_TITLE": "Auth model",
            "CARD_2_NUM": "#18", "CARD_2_TITLE": "API routes",
            "CARD_3_NUM": "#24", "CARD_3_TITLE": "E2E suite",
            "CARD_4_NUM": "#31", "CARD_4_TITLE": "Release gate",
            "GHOST_NUM": "#—", "GHOST_TITLE": "Future epic",
        })
    elif slug == "funnel":
        o.update(funnel_geometry())
    elif slug == "scatter":
        o.update(scatter_geometry())
    elif slug == "bubble":
        o.update(scatter_geometry())
        o["SERIES"] = (
            '    <circle cx="30" cy="65" r="2.2" fill="var(--cyan)" opacity="0.85"/>'
            '    <circle cx="50" cy="45" r="3.5" fill="var(--amber)" opacity="0.85"/>'
            '    <circle cx="72" cy="28" r="4.8" fill="var(--purple)" opacity="0.85"/>'
        )
    elif slug == "radar":
        o.update({
            "AXIS_0_LABEL": "speed", "AXIS_1_LABEL": "quality", "AXIS_2_LABEL": "cost",
            "AXIS_3_LABEL": "ops", "AXIS_4_LABEL": "security",
            "AXIS_0_X": "50", "AXIS_0_Y": "8",
            "SERIES_0_POINTS": "50,35 62,42 58,55 45,58 38,45",
        })
    return o


def replace_craft_script_block(html: str) -> str:
    """Replace the craft-anchors script after craft-edges (last </script> before </body>)."""
    anchor = html.find('id="craft-edges"')
    if anchor < 0:
        return html
    start = html.find("  <script>", anchor)
    if start < 0:
        return html
    body_end = html.find("</body>")
    if body_end < 0:
        body_end = len(html)
    end = html.rfind("</script>", start, body_end)
    if end < 0:
        return html
    block = f"  <script>\n{craft_js_safe()}\n  </script>"
    return html[:start] + block + html[end + len("</script>") :]


def fix_lane_swim_edges(html: str) -> str:
    html = re.sub(
        r"<!-- EXAMPLE EDGES[\s\S]*?<!-- .*? add your edges here -->",
        f"<!-- demo edges (baked) -->\n{LANE_SWIM_DEMO_EDGES}",
        html,
        count=1,
    )
    html = re.sub(
        r'<!-- EXAMPLE: Router→LLM left-bulge[\s\S]*?<!-- lane swim — add your edge labels here -->',
        '  <div class="fg-edge-lbl amber" style="--x:25; --y:23">route</div>',
        html,
        count=1,
    )
    return html


def apply_fgraph_preview_shell(html: str) -> str:
    """Center architecture fgraph previews like craft diagrams (no explainer header chrome)."""
    html = re.sub(
        r'<link href="https://fonts\.googleapis\.com/css2\?[^"]+" rel="stylesheet">',
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">',
        html,
        count=1,
    )
    if "embed-hero" not in html:
        html = html.replace("<head>", f"<head>\n{EMBED_HERO_SCRIPT}", 1)
    html = html.replace("</style>", f"\n{FG_PREVIEW_SHELL_CSS}\n</style>", 1)
    m = re.search(
        r"<header>\s*"
        r'<div class="header-eyebrow">([^<]*)</div>\s*'
        r"<h1>([^<]*?)<span class=\"accent\">([^<]*)</span></h1>\s*"
        r'<p class="header-subtitle">([^<]*)</p>\s*'
        r"</header>",
        html,
    )
    if m:
        _eyebrow, plain, accent, sub = m.groups()
        title_block = (
            f'<div class="fg-preview-title">\n'
            f"  <h1>{plain.strip()} <span class=\"accent\">{accent.strip()}</span></h1>\n"
            f"  <p>{sub.strip()}</p>\n"
            f"</div>"
        )
        html = re.sub(r"<main>\s*", f"<main>\n{title_block}\n", html, count=1)
    html = re.sub(
        r"(</head>\s*)<body(\s[^>]*)?>",
        r'\1<body class="fg-preview"\2>',
        html,
        count=1,
    )
    return html


def apply_placeholders(html: str, slug: str) -> str:
    vars_map = template_overrides(slug)
    for key in sorted(vars_map, key=len, reverse=True):
        html = html.replace(f"{{{{{key}}}}}", str(vars_map[key]))
    html = re.sub(
        r"\{\{([A-Z0-9_]+)\}\}",
        lambda m: fallback_placeholder(m.group(1), slug),
        html,
    )
    return html


def bake_fgraph(slug: str) -> Path:
    src = FG_TEMPLATES / f"{slug}.html"
    out = FG_EXAMPLES / f"{slug}-preview.html"
    html = src.read_text(encoding="utf-8")
    html = inline_fgraph_css(html, slug)
    html = apply_placeholders(html, slug)
    if slug == "lane-swim":
        html = fix_lane_swim_edges(html)
    if slug in ARCH_FG_SLUGS:
        html = apply_fgraph_preview_shell(html)
    html = html.replace(
        "<title>{{TITLE}}</title>",
        f"<title>{slug_title(slug)}</title>",
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def inline_gallery_assets(html: str) -> str:
    css = (GAL_TEMPLATES / "gallery-base.css").read_text(encoding="utf-8")
    js = (GAL_TEMPLATES / "gallery-base.js").read_text(encoding="utf-8")
    html = re.sub(
        r'<link rel="stylesheet" href="\{\{GALLERY_BASE_CSS\}\}">',
        "",
        html,
    )
    html = html.replace(
        ":root {\n  --accent:{{ACCENT_COLOR}};",
        ":root {\n  --accent:#f0b429;",
    )
    html = html.replace(
        "  --accent-dim:{{ACCENT_DIM}};",
        "  --accent-dim:rgba(240,180,41,0.12);",
    )
    html = html.replace("<style>", f"<style>\n/* gallery-base — baked */\n{css}\n", 1)
    html = html.replace(
        '<script src="{{GALLERY_BASE_JS}}"></script>',
        "<script>\n" + js + "\n</script>",
    )
    return html


def demo_img_js() -> str:
    return json.dumps(DEMO_SVG)


def inject_simple_gallery(html: str) -> str:
    demo = demo_img_js()
    html = html.replace(
        "/* {{CATALOGUE_V1_ENTRIES}} */",
        """  'demo-01': { label: 'Alpha', tags: ['demo', 'craft'] },
  'demo-02': { label: 'Beta', tags: ['demo', 'chart'] },
  'demo-03': { label: 'Gamma', tags: ['demo', 'gallery'] },
  'demo-04': { label: 'Delta', tags: ['demo', 'fd-engine'] },""",
    )
    html = html.replace(
        """const BATCHES = [
  /* {{BATCHES_CONFIG}}
     Example:
     { id:'v1', label:'{{BATCH_1_LABEL}}', dir:'{{BATCH_1_DIR}}', ext:'.png', catalogue: CATALOGUE_V1 },
  */
];""",
        """const BATCHES = [
  { id: 'demo', label: 'Demo', dir: '', ext: '', catalogue: CATALOGUE_V1 },
];""",
    )
    html = html.replace(
        "/* {{DIMS_CONFIG}} — each dim.fn takes the full item object (e.g. fn: it => it.tags[0]) */",
        "kind: { label: 'Kind', fn: it => it.tags[1] || 'other', order: ['craft','chart','gallery','fd-engine'] },",
    )
    boot = f"""/* ── Boot ── */

(async () => {{
  allItems = Object.entries(CATALOGUE_V1).map(([stem, meta], i) => ({{
    stem,
    label: meta.label,
    tags: meta.tags,
    batch: 'demo',
    dir: '',
    file: {demo},
    idx: i,
  }}));
  buildBatchBar({{ barId:'batchBar', batches:BATCHES, counts:{{ demo: allItems.length }}, total: allItems.length,
    onSelect: id => {{ currentBatch = id; render(); }} }});
  buildDimFilters(allItems, DIMS, filters, 'filterBar', render);
  render();
  const sub = document.getElementById('subtitle');
  if (sub) sub.textContent = allItems.length + ' demo tiles · baked preview';
}})();"""
    html = re.sub(
        r"/\* ── Boot ── \*/\s*\(async \(\) => \{[\s\S]*?\}\)\(\);",
        boot,
        html,
        count=1,
    )
    return html


def inject_comparison_gallery(html: str) -> str:
    demo = demo_img_js()
    html = html.replace(
        "const SECTIONS = [\n  /* {{SECTIONS_CONFIG}} */\n];",
        """const SECTIONS = [
  { id: 'demo', title: 'Demo Comparisons', subtitle: 'Baked preview — forge reference' },
];""",
    )
    html = html.replace(
        "const CARDS = [\n  /* {{CARDS_CONFIG}} */\n];",
        f"""const CARDS = [
  {{
    section: 'demo',
    image: {demo},
    title: 'Baseline — Default',
    badges: [{{ text: 'REF', type: 'ref' }}, {{ text: 'CLEAN', type: 'clean' }}],
    specs: {{ 'Engine': 'Forge', 'Steps': '28' }},
    verdict: {{ text: 'Reference output.', type: 'clean' }},
    tags: ['baseline','clean'],
  }},
  {{
    section: 'demo',
    image: {demo},
    title: 'Variant A',
    badges: [{{ text: 'CHECK', type: 'mid' }}],
    specs: {{ 'Strength': '0.8' }},
    verdict: {{ text: 'Reduced artifacts.', type: 'mid' }},
    tags: ['variant','mid'],
  }},
  {{
    section: 'demo',
    image: {demo},
    title: 'Variant B',
    badges: [{{ text: 'WARN', type: 'bad' }}],
    specs: {{ 'Strength': '1.0' }},
    verdict: {{ text: 'Some banding visible.', type: 'bad' }},
    tags: ['variant','bad'],
  }},
  {{
    section: 'demo',
    image: {demo},
    title: 'Variant C',
    badges: [{{ text: 'CLEAN', type: 'clean' }}],
    specs: {{ 'Model': 'Demo' }},
    tags: ['variant','clean'],
  }},
];""",
    )
    html = html.replace(
        "const FILTERS_DIMS = {\n  /* {{FILTERS_DIMS_CONFIG}} */\n};",
        """const FILTERS_DIMS = {
  verdict: { label: 'Verdict', fn: card => card.verdict?.type || 'none', order: ['clean','mid','bad'] },
};""",
    )
    return html


def inject_pivot_gallery(html: str) -> str:
    demo = demo_img_js()
    html = re.sub(r"const DATA_URL = [^;]+;", "const DATA_URL = null;", html, count=1)
    html = html.replace("const EXT = '.png';", "const EXT = '';")
    boot = f"""// ── Boot ──

async function boot() {{
  colDim = 'none';
  rowDim = 'none';
  allFiles = [{demo}, {demo}, {demo}, {demo}];
  buildDimFilters(allFiles, DIMS, filters, 'filterBar', render);
  render();
  const sub = document.getElementById('subtitle');
  if (sub) sub.textContent = allFiles.length + ' demo tiles · baked preview';
}}
boot();"""
    html = re.sub(
        r"// ── Boot ──\s*async function boot\(\) \{[\s\S]*?\}\s*boot\(\);",
        boot,
        html,
        count=1,
    )
    return html


def inject_multi_mode_gallery(html: str) -> str:
    demo = demo_img_js()
    modes = f"""const MODES = [
  {{
    id: 'demo',
    label: 'Demo',
    countLabel: 'preview',
    dir: '',
    pixelated: false,
    dims: {{
      category: {{ label: 'Category', fn: it => it.category, order: ['alpha','beta','gamma'] }},
      tier:     {{ label: 'Tier',     fn: it => it.tier,     order: ['S','A','B','C'] }},
    }},
    buildItems: () => [
      {{ file: {demo}, dir: '', label: 'Alpha', category: 'alpha', tier: 'S' }},
      {{ file: {demo}, dir: '', label: 'Beta',  category: 'beta',  tier: 'A' }},
      {{ file: {demo}, dir: '', label: 'Gamma', category: 'gamma', tier: 'B' }},
      {{ file: {demo}, dir: '', label: 'Delta', category: 'alpha', tier: 'C' }},
    ],
  }},
];"""
    html = re.sub(r"const MODES = \[[\s\S]*?\];", modes, html, count=1)
    html = re.sub(
        r"const STORE_KEY = 'forge-gallery-preview'\.includes\('\{\{'\) \? 'multi-mode-gallery' : 'forge-gallery-preview'",
        "const STORE_KEY = 'forge-gallery-preview'",
        html,
        count=1,
    )
    return html


def inject_audio_gallery(html: str) -> str:
    html = html.replace(
        "const ENGINE_META = {\n  /* {{ENGINE_META_CONFIG}} */\n};",
        """const ENGINE_META = {
  demo: { color: 'amber', label: 'Demo Engine', order: 0 },
};""",
    )
    html = html.replace(
        "const QUALITY_META = {\n  /* {{QUALITY_META_CONFIG}} */\n};",
        """const QUALITY_META = {
  default: { color: 'neutral', label: 'Default', order: 0 },
};""",
    )
    html = html.replace(
        "const BATCHES = [\n  /* {{BATCHES_CONFIG}} */\n];",
        "const BATCHES = [{ id: 'demo', label: 'Demo', dir: '', manifest: 'img-manifest.json' }];",
    )
    html = html.replace(
        "const FILTERS_DIMS = {\n  /* {{FILTERS_DIMS_CONFIG}} */\n};",
        """const FILTERS_DIMS = {
  engine: { label: 'Engine', fn: item => item.engine || 'unknown' },
};""",
    )
    boot = """(async () => {
  DATA = [
    { file: 'demo-01.wav', label: 'Alpha Sample', engine: 'demo', quality: 'default', batch: 'demo', phrase_text: 'Hello forge' },
    { file: 'demo-02.wav', label: 'Beta Sample', engine: 'demo', quality: 'default', batch: 'demo', phrase_text: 'Preview tile' },
    { file: 'demo-03.wav', label: 'Gamma Sample', engine: 'demo', quality: 'default', batch: 'demo', phrase_text: 'Gallery demo' },
    { file: 'demo-04.wav', label: 'Delta Sample', engine: 'demo', quality: 'default', batch: 'demo', phrase_text: 'Baked preview' },
  ];
  buildDimFilters(DATA, FILTERS_DIMS, filters, 'filterBar', render);
  document.getElementById('subtitle').textContent = '4 demo samples · baked preview';
  render();
})();"""
    html = re.sub(
        r"/\* ── Init ── \*/\s*initTheme\(STORE_KEY\);[\s\S]*?\(async \(\) => \{[\s\S]*?\}\)\(\);",
        f"""/* ── Init ── */

initTheme(STORE_KEY);
['view','group'].forEach(k => {{
  document.querySelectorAll(`[data-k="${{k}}"]`).forEach(b => b.classList.toggle('on', b.dataset.v === S[k]));
}});

{boot}""",
        html,
        count=1,
    )
    return html


GALLERY_INJECTORS = {
    "simple-gallery": inject_simple_gallery,
    "comparison-gallery": inject_comparison_gallery,
    "pivot-gallery": inject_pivot_gallery,
    "multi-mode-gallery": inject_multi_mode_gallery,
    "audio-gallery": inject_audio_gallery,
}


def bake_gallery(slug: str) -> Path:
    src = GAL_TEMPLATES / f"{slug}.html"
    out = GAL_EXAMPLES / f"{slug}-preview.html"
    html = src.read_text(encoding="utf-8")
    html = inline_gallery_assets(html)
    title = slug_title(slug)
    plain, _, accent = title.partition(" · ")
    reps = {
        "{{TITLE}}": title,
        "{{TITLE_PLAIN}}": plain,
        "{{TITLE_ACCENT}}": accent,
        "{{SUBTITLE}}": "Baked gallery template preview",
        "{{DATE}}": "2026-07-04",
        "{{CATEGORY}}": "gallery",
        "{{CAT_LABEL}}": "Gallery",
        "{{COLOR}}": "#f0b429",
        "{{STORE_KEY_PREFIX}}": "forge-gallery-preview",
        "{{IMAGE_DIR}}": "",
        "{{DATA_JSON_PATH}}": "",
        "{{REF_IMAGE_PATH}}": DEMO_SVG,
        "{{ACCENT_COLOR}}": "#f0b429",
        "{{ACCENT_DIM}}": "rgba(240,180,41,0.12)",
    }
    for k, v in reps.items():
        html = html.replace(k, v)
    html = GALLERY_INJECTORS[slug](html)
    html = re.sub(r"\{\{[A-Z0-9_]+\}\}", "", html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def craft_js_safe() -> str:
    js = (REFS / "diagrams" / "craft-anchors.js").read_text(encoding="utf-8")
    return js.replace("</script>", "<\\/script>")


def bake_craft_starter_preview() -> Path:
    src = REFS / "diagrams/craft-diagram-starter.html"
    out = DIAG_EXAMPLES / "craft-diagram-starter-preview.html"
    html = src.read_text(encoding="utf-8")
    html = html.replace("{Title}", "Craft Diagram Starter")
    html = html.replace("{Subtitle}", "Baked preview — copy scaffold from craft-diagram-starter.html")
    html = html.replace("{slug}", "craft-starter-preview")
    html = replace_craft_script_block(html)
    out.write_text(html, encoding="utf-8")
    return out


def main() -> None:
    baked = []
    for slug in FG_SLUGS:
        path = bake_fgraph(slug)
        baked.append(path)
        print(f"  ✓ {path.relative_to(REFS)}")
    for slug in GAL_SLUGS:
        path = bake_gallery(slug)
        baked.append(path)
        print(f"  ✓ {path.relative_to(REFS)}")
    p = bake_craft_starter_preview()
    baked.append(p)
    print(f"  ✓ {p.relative_to(REFS)}")
    print(f"bake-reference-previews — {len(baked)} files")


if __name__ == "__main__":
    main()