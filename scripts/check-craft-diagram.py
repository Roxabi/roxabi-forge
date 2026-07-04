#!/usr/bin/env python3
"""check-craft-diagram.py — structural QA for hand-authored craft diagrams.

Catches common craft errors before iframe embed: out-of-canvas CSS, hardcoded
paths without anchor engine, external icon sprites, missing title block.

Usage:
  python3 check-craft-diagram.py visuals/diagrams/*.html
  python3 check-craft-diagram.py --dir ~/.roxabi/forge/PROJ/visuals/diagrams --check
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CANVAS_RE = re.compile(
    r"\.diagram\s*\{[^}]*?(?:width:\s*(\d+(?:\.\d+)?)px)[^}]*?(?:height:\s*(\d+(?:\.\d+)?)px)",
    re.IGNORECASE | re.DOTALL,
)
DATA_CANVAS_RE = re.compile(
    r'data-canvas-width=["\'](\d+(?:\.\d+)?)["\'][^>]*data-canvas-height=["\'](\d+(?:\.\d+)?)["\']',
    re.IGNORECASE,
)
NEG_POS_RE = re.compile(
    r"(?:^|[;{\s])(?:left|right|top|bottom)\s*:\s*-\d",
    re.IGNORECASE | re.MULTILINE,
)
HARDCODED_PATH_RE = re.compile(
    r'<path[^>]+class="[^"]*connection[^"]*"[^>]+d="[^"]+"',
    re.IGNORECASE,
)
ANCHOR_ATTR_RE = re.compile(r"data-anchor=", re.IGNORECASE)
CRAFT_EDGES_RE = re.compile(r'id=["\']craft-edges["\']', re.IGNORECASE)
CRAFT_ANCHORS_JS_RE = re.compile(r"craft-anchors|CraftAnchors", re.IGNORECASE)
EXTERNAL_SPRITE_RE = re.compile(
    r'<use[^>]+(?:href|xlink:href)=["\'][^"\']*brand-icons\.svg',
    re.IGNORECASE,
)
TITLE_BLOCK_RE = re.compile(r"class=[\"']title-block[\"']", re.IGNORECASE)
TITLE_H1_RE = re.compile(r"<h1[^>]*>", re.IGNORECASE)
DIAGRAM_TITLE_META_RE = re.compile(r'name=["\']diagram:title["\']', re.IGNORECASE)
SPOKE_COUNT_RE = re.compile(r"data-anchor=", re.IGNORECASE)


def check_file(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")

    if not TITLE_BLOCK_RE.search(text):
        errors.append("missing .title-block (title must live inside diagram)")
    if not TITLE_H1_RE.search(text):
        errors.append("missing <h1> in diagram")
    if not DIAGRAM_TITLE_META_RE.search(text):
        warnings.append("missing diagram:title meta")

    if EXTERNAL_SPRITE_RE.search(text):
        errors.append("external brand-icons.svg <use> — inline symbols instead")

    if NEG_POS_RE.search(text):
        errors.append("negative absolute position (likely outside canvas)")

    has_anchors = bool(ANCHOR_ATTR_RE.search(text))
    has_edges_json = bool(CRAFT_EDGES_RE.search(text))
    has_anchor_js = bool(CRAFT_ANCHORS_JS_RE.search(text))
    has_hardcoded = bool(HARDCODED_PATH_RE.search(text))

    if has_hardcoded and not (has_anchors and has_edges_json and has_anchor_js):
        warnings.append(
            "hardcoded <path class=\"connection\" d=…> without craft-anchors "
            "(move spokes → data-anchor + craft-edges JSON)"
        )

    if has_anchors and not has_edges_json:
        errors.append("data-anchor nodes without #craft-edges JSON")

    if has_edges_json and not has_anchor_js:
        warnings.append("#craft-edges present but craft-anchors.js not inlined")

    anchor_count = len(SPOKE_COUNT_RE.findall(text))
    if anchor_count > 6:
        warnings.append(f"{anchor_count} data-anchor nodes — consider split diagram (>6 dense)")

    w, h = None, None
    m = DATA_CANVAS_RE.search(text)
    if m:
        w, h = float(m.group(1)), float(m.group(2))
    else:
        cm = CANVAS_RE.search(text)
        if cm:
            w, h = float(cm.group(1)), float(cm.group(2))

    if w is None:
        warnings.append("no explicit canvas size (.diagram width/height or data-canvas-*)")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="QA craft diagram HTML files")
    parser.add_argument("files", nargs="*", type=Path, help="diagram HTML paths")
    parser.add_argument("--dir", "-d", type=Path, help="scan directory for *.html")
    parser.add_argument("--check", action="store_true", help="exit 1 on errors")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    paths: list[Path] = list(args.files)
    if args.dir:
        paths.extend(sorted(args.dir.glob("*.html")))

    if not paths:
        parser.error("provide files or --dir")

    total_err = 0
    total_warn = 0
    for path in paths:
        if not path.exists():
            print(f"ERROR: {path}: file not found", file=sys.stderr)
            total_err += 1
            continue
        errors, warnings = check_file(path.resolve())
        for e in errors:
            print(f"ERROR: {path.name}: {e}", file=sys.stderr)
            total_err += 1
        for w in warnings:
            print(f"WARN: {path.name}: {w}", file=sys.stderr)
            total_warn += 1
        if not errors and not warnings:
            print(f"OK: {path.name}")

    if total_err or (args.strict and total_warn):
        return 1 if args.check or args.strict else 0
    print(f"check OK — {len(paths)} diagram(s), {total_warn} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())