#!/usr/bin/env python3
"""
gen-fd.py — data-driven generator for fd-engine diagram HTML.

Reads a descriptor JSON, optionally runs elk auto-layout (bun fd-layout.mjs),
bundles the fd-engine via bun + bundler.js, and emits a self-contained HTML file.

Usage:
  python3 scripts/gen-fd.py --in descriptor.json --out diagram.html
  python3 scripts/gen-fd.py --in descriptor.json --out diagram.html --theme lyra-v2
  python3 scripts/gen-fd.py --in descriptor.json --out diagram.html --title "My Diagram"

Descriptor schema: see plugins/forge/skills/forge-chart/SKILL.md § Descriptor JSON schema.
Legacy partial descriptors (nodes/edges/useCases only) are normalized automatically.
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))
from forge_paths import resolve_forge_ref, script_root  # noqa: E402

ROOT = script_root(__file__)
FORGE_REF = resolve_forge_ref(ROOT)
GRAPH_DIR = FORGE_REF / "graph-templates"
FD_DIR = GRAPH_DIR / "fd"
AESTHETICS_DIR = FORGE_REF / "aesthetics"
SHELL_PATH = GRAPH_DIR / "fd-shell.html"
PAGE_SHELL_CSS = GRAPH_DIR / "fd-page-shell.css"
FD_ENGINE_CSS = GRAPH_DIR / "fd-engine.css"
BOOTSTRAP_JS = GRAPH_DIR / "fd-bootstrap.js"
FD_LAYOUT = _SCRIPTS_DIR / "fd-layout.mjs"

AUTO_LAYOUT_TYPES = frozenset({"flowchart", "state", "class", "er", "sequence"})
CHART_ONLY_TYPES = frozenset({"gantt", "pie", "xychart"})
NODE_EDGE_TYPES = frozenset(
    {"architecture", "hub-spoke", "flowchart", "state", "class", "er", "sequence"}
)

PLANE_STROKE = {
    "control": "var(--cyan)",
    "write": "var(--green)",
    "read": "var(--purple)",
    "data": "var(--plum)",
    "async": "var(--amber)",
    "feedback": "var(--accent)",
    "message": "var(--cyan)",
    "media": "var(--amber)",
    "llm": "var(--purple)",
    "flow": "var(--cyan)",
    "error": "var(--red)",
    "success": "var(--green)",
    "decision": "var(--amber)",
}

THEME_COLORS = {
    "lyra-v2": "#22d3ee",
    "lyra": "#22d3ee",
    "cool-dark": "#38bdf8",
    "editorial": "#e85d04",
    "warm-light": "#d97706",
    "mono-slate": "#64748b",
    "roxabi": "#e85d04",
    "terminal": "#22d3ee",
    "blueprint": "#58a6ff",
    "caveman": "#f59e0b",
}


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_bun_build_engine(diagram_type: str) -> str:
    fd_dir = str(FD_DIR.resolve())
    script = (
        f"import {{ buildEngine }} from '{fd_dir}/bundler.js';\n"
        f"console.log(buildEngine('{fd_dir}', '{diagram_type}'));\n"
    )
    result = subprocess.run(
        ["bun", "-e", script],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        eprint("gen-fd: bundler.js failed:")
        eprint(result.stderr or result.stdout)
        sys.exit(1)
    return result.stdout


def run_fd_layout(descriptor_path: Path) -> dict:
    result = subprocess.run(
        ["bun", str(FD_LAYOUT), str(descriptor_path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        eprint("gen-fd: fd-layout.mjs failed:")
        eprint(result.stderr or result.stdout)
        sys.exit(1)
    return json.loads(result.stdout)


def normalize_descriptor(raw: dict, *, theme: str, title: str | None) -> dict:
    desc = dict(raw)

    if "nodes" not in desc:
        eprint("gen-fd: descriptor must contain a 'nodes' array")
        sys.exit(1)

    diagram_type = desc.get("type") or "architecture"
    desc["type"] = diagram_type
    desc.setdefault("theme", theme)
    desc.setdefault("layout", "auto" if diagram_type in AUTO_LAYOUT_TYPES else "declarative")
    desc.setdefault("title", title or desc.get("title") or "Diagram")
    desc.setdefault("canvas", {"height": 1040})
    if isinstance(desc["canvas"], (int, float)):
        desc["canvas"] = {"height": int(desc["canvas"])}

    options = dict(desc.get("options") or {})
    options.setdefault("particles", False)
    options.setdefault("spotlight", True)
    options.setdefault("sidebar", diagram_type in {"architecture", "hub-spoke"})
    desc["options"] = options

    if "edges" not in desc:
        desc["edges"] = []

    return desc


def unique_planes(edges: list[dict]) -> list[str]:
    seen: set[str] = set()
    planes: list[str] = []
    for edge in edges:
        plane = edge.get("plane")
        if plane and plane not in seen:
            seen.add(plane)
            planes.append(plane)
    return planes


def build_plane_legend(planes: list[str]) -> str:
    if not planes:
        return ""
    items = []
    for plane in planes:
        color = PLANE_STROKE.get(plane, "var(--text-muted)")
        items.append(
            f'<span class="lg"><span class="lln" style="border-color:{color}"></span>'
            f"{html.escape(plane)}</span>"
        )
    return f'<div class="legend">{"".join(items)}</div>'


def build_plane_filters(planes: list[str]) -> str:
    if not planes:
        return ""
    buttons = []
    for plane in planes:
        buttons.append(
            f'<span class="ctl" id="ctl-{html.escape(plane)}" data-plane="{html.escape(plane)}">'
            f"{html.escape(plane)}</span>"
        )
    return f'<div class="ctl-group">{"".join(buttons)}</div>'


def build_use_case_bar(use_cases: list[dict] | None) -> str:
    if not use_cases:
        return ""
    buttons = []
    for idx, uc in enumerate(use_cases):
        label = uc.get("title") or f"case {idx + 1}"
        buttons.append(
            f'<button class="uc-btn" data-uc="{idx}">{html.escape(label)}</button>'
        )
    return (
        '<div class="uc-bar">'
        '<span class="uc-label">use case:</span>'
        + "".join(buttons)
        + '<button class="uc-play" id="ucPlay" disabled>&#9654; play</button>'
        + '<button class="uc-reset" id="ucReset">&#8634; reset</button>'
        + "</div>"
    )


def build_zone_html(zones: list[dict] | None) -> str:
    if not zones:
        return ""
    parts = []
    for zone in zones:
        zone_id = html.escape(zone.get("id", ""))
        zone_class = html.escape(zone.get("class", ""))
        label = html.escape(zone.get("label", ""))
        parts.append(
            f'<div class="fd-zone {zone_class}" id="{zone_id}">'
            f'<span class="fd-zone-label">{label}</span></div>'
        )
    return "\n        ".join(parts)


def format_title_html(title: str) -> str:
    if " — " in title:
        left, right = title.split(" — ", 1)
        return f"<b>{html.escape(left)}</b> — {html.escape(right)}"
    if " - " in title:
        left, right = title.split(" - ", 1)
        return f"<b>{html.escape(left)}</b> - {html.escape(right)}"
    return f"<b>{html.escape(title)}</b>"


def build_subtitle(desc: dict) -> str:
    diagram_type = desc["type"]
    theme = desc.get("theme", "lyra-v2")
    layout = desc.get("layout", "declarative")
    node_count = len(desc.get("nodes") or [])
    edge_count = len(desc.get("edges") or [])
    uc_count = len(desc.get("useCases") or [])
    parts = [
        f"fd-engine · {diagram_type}",
        theme,
        layout,
        f"{node_count} nodes · {edge_count} edges",
    ]
    if uc_count:
        parts.append(f"{uc_count} use cases")
    parts.append("DOM-measured bezier edges")
    return html.escape(" · ".join(parts))


def resolve_aesthetic(theme: str) -> Path:
    path = AESTHETICS_DIR / f"{theme}.css"
    if path.exists():
        return path
    fallback = AESTHETICS_DIR / "lyra-v2.css"
    if not fallback.exists():
        eprint(f"gen-fd: aesthetic not found: {theme} (and no lyra-v2.css fallback)")
        sys.exit(1)
    eprint(f"gen-fd: aesthetic '{theme}' not found — falling back to lyra-v2")
    return fallback


def assemble_html(desc: dict) -> str:
    shell = read_text(SHELL_PATH)
    theme = desc.get("theme", "lyra-v2")
    aesthetic_css = read_text(resolve_aesthetic(theme))
    fd_engine_css = read_text(FD_ENGINE_CSS)
    page_shell_css = read_text(PAGE_SHELL_CSS)
    bootstrap_js = read_text(BOOTSTRAP_JS)
    bundle = run_bun_build_engine(desc["type"])

    planes = unique_planes(desc.get("edges") or [])
    use_cases = desc.get("useCases") or []
    show_sidebar = desc.get("options", {}).get("sidebar", True) and desc["type"] in {
        "architecture",
        "hub-spoke",
    }

    title = desc.get("title", "Diagram")
    category = "architecture" if desc["type"] in {"architecture", "hub-spoke"} else desc["type"]

    replacements = {
        "{LANG}": "en",
        "{TITLE_ESC}": html.escape(title),
        "{TITLE_HTML}": format_title_html(title),
        "{SUBTITLE}": build_subtitle(desc),
        "{CATEGORY}": html.escape(category),
        "{COLOR}": THEME_COLORS.get(theme, "#22d3ee"),
        "{TYPE}": html.escape(desc["type"]),
        "{THEME}": html.escape(theme),
        "{AESTHETIC_CSS}": aesthetic_css,
        "{FD_ENGINE_CSS}": fd_engine_css,
        "{PAGE_SHELL_CSS}": page_shell_css,
        "{PLANE_LEGEND}": build_plane_legend(planes),
        "{PLANE_FILTERS}": build_plane_filters(planes),
        "{USE_CASE_BAR}": build_use_case_bar(use_cases),
        "{NET_LABEL}": (
            f'<div class="fd-net-label">{html.escape(desc.get("netLabel", ""))}</div>'
            if desc.get("netLabel")
            else ""
        ),
        "{ZONE_HTML}": build_zone_html(desc.get("zones")),
        "{STAGE_CLASS}": "" if show_sidebar else " full-width",
        "{SIDEBAR_CLASS}": "" if show_sidebar else " hidden",
        "{FD_DATA_JSON}": json.dumps(desc, ensure_ascii=False, indent=2),
        "{FD_ENGINE_BUNDLE}": bundle,
        "{FD_BOOTSTRAP_JS}": bootstrap_js,
    }

    output = shell
    for key, value in replacements.items():
        output = output.replace(key, value)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fd-engine HTML from descriptor JSON")
    parser.add_argument("--in", dest="input_path", required=True, help="Input descriptor JSON")
    parser.add_argument("--out", dest="output_path", required=True, help="Output HTML file")
    parser.add_argument("--theme", default="lyra-v2", help="Aesthetic theme (default: lyra-v2)")
    parser.add_argument("--title", default=None, help="Override diagram title")
    args = parser.parse_args()

    input_path = Path(args.input_path).resolve()
    output_path = Path(args.output_path).resolve()

    if not input_path.exists():
        eprint(f"gen-fd: input not found: {input_path}")
        sys.exit(1)

    try:
        raw = json.loads(read_text(input_path))
    except json.JSONDecodeError as exc:
        eprint(f"gen-fd: invalid JSON: {exc}")
        sys.exit(1)

    desc = normalize_descriptor(raw, theme=args.theme, title=args.title)

    if desc["layout"] == "auto" and desc["type"] in AUTO_LAYOUT_TYPES:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(desc, tmp, ensure_ascii=False, indent=2)
            tmp_path = Path(tmp.name)
        try:
            desc = run_fd_layout(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    diagram_type = desc["type"]
    if diagram_type not in NODE_EDGE_TYPES and diagram_type not in CHART_ONLY_TYPES:
        eprint(
            f"gen-fd: unsupported type '{diagram_type}'. "
            f"Supported: {', '.join(sorted(NODE_EDGE_TYPES | CHART_ONLY_TYPES))}"
        )
        sys.exit(1)

    html_out = assemble_html(desc)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_out, encoding="utf-8")

    line_count = html_out.count("\n") + 1
    eprint(f"gen-fd: wrote {output_path} ({len(html_out):,} bytes, {line_count:,} lines)")
    eprint(f"gen-fd: type={diagram_type} nodes={len(desc.get('nodes', []))} edges={len(desc.get('edges', []))}")


if __name__ == "__main__":
    main()