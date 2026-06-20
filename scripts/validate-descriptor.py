#!/usr/bin/env python3
"""
validate-descriptor.py — pre-generation layout checks on fd-engine descriptor JSON.

Estimates node bounding boxes from % coordinates + premium card metrics, then
verifies horizontal pair gaps and zone-label spacing before running gen-fd.py.

Usage:
  python3 scripts/validate-descriptor.py --in descriptor.json
  python3 scripts/validate-descriptor.py --in descriptor.json --expect fixtures/lyra-stack-v2.expect.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forge_paths import default_expect_path, script_root

PREMIUM_CARD_WIDTH = 154
PREMIUM_CARD_HEIGHT = 72
ZONE_LABEL_HEIGHT = 18

ZONE_PADDING = {
    "zone-hub": {"x": 14, "top": 36, "bottom": 12},
    "zone-stores": {"x": 14, "top": 20, "bottom": 10},
    "zone-m2": {"x": 16, "top": 20, "bottom": 12},
}
DEFAULT_ZONE_PADDING = {"x": 16, "top": 20, "bottom": 12}


@dataclass
class Finding:
    level: str
    code: str
    message: str
    detail: Any = None

    def format(self) -> str:
        line = f"[{self.level.upper()}] {self.code}: {self.message}"
        if self.detail is not None:
            line += f" — {self.detail}"
        return line


def zone_padding(zone: dict) -> dict[str, int]:
    base = ZONE_PADDING.get(zone.get("class", ""), DEFAULT_ZONE_PADDING)
    custom = zone.get("padding") or {}
    return {
        "x": custom.get("x", base["x"]),
        "top": custom.get("top", base["top"]),
        "bottom": custom.get("bottom", base["bottom"]),
    }


def canvas_height(descriptor: dict) -> int:
    canvas = descriptor.get("canvas") or {}
    if isinstance(canvas, (int, float)):
        return int(canvas)
    return int(canvas.get("height") or 1040)


def node_by_id(descriptor: dict) -> dict[str, dict]:
    nodes = descriptor.get("nodes") or []
    return {n["id"]: n for n in nodes if n.get("id")}


def estimate_rect(
    node: dict,
    *,
    canvas_w: int,
    canvas_h: int,
    card_style: str = "premium",
) -> dict[str, float]:
    x_pct = float(node.get("x", 50))
    y_pct = float(node.get("y", 50))
    cx = x_pct / 100 * canvas_w
    cy = y_pct / 100 * canvas_h

    style = node.get("cardStyle") or card_style
    if style == "premium":
        w, h = PREMIUM_CARD_WIDTH, PREMIUM_CARD_HEIGHT
        if node.get("d"):
            h = max(h, 88)
    else:
        w, h = 120, 48

    return {
        "cx": cx,
        "cy": cy,
        "w": w,
        "h": h,
        "left": cx - w / 2,
        "right": cx + w / 2,
        "top": cy - h / 2,
        "bottom": cy + h / 2,
    }


def schema_checks(descriptor: dict) -> list[Finding]:
    findings: list[Finding] = []
    nodes = descriptor.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        findings.append(Finding("error", "nodes", "descriptor must contain a non-empty nodes array"))
        return findings

    seen: set[str] = set()
    for node in nodes:
        node_id = node.get("id")
        if not node_id:
            findings.append(Finding("error", "node-id", "node missing id"))
            continue
        if node_id in seen:
            findings.append(Finding("error", "duplicate-id", f"duplicate node id: {node_id}"))
        seen.add(node_id)
        if "x" not in node or "y" not in node:
            findings.append(
                Finding("warn", "node-coords", f"node '{node_id}' missing x/y (declarative layout)")
            )

    for edge in descriptor.get("edges") or []:
        for end in ("f", "t"):
            ref = edge.get(end)
            if ref and ref not in seen:
                findings.append(Finding("error", "edge-ref", f"edge references unknown node: {ref}"))

    for zone in descriptor.get("zones") or []:
        zone_id = zone.get("id")
        if not zone_id:
            findings.append(Finding("error", "zone-id", "zone missing id"))
        for member in zone.get("nodes") or []:
            if member not in seen:
                findings.append(
                    Finding("error", "zone-member", f"zone '{zone_id}' references unknown node: {member}")
                )

    return findings


def pair_gap_checks(
    descriptor: dict,
    expect: dict[str, Any],
    *,
    viewport_w: int,
    viewport_h: int,
    strict: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    layout = expect.get("layout") or {}
    pairs = layout.get("pairs") or []
    if not pairs:
        return findings

    canvas_h = canvas_height(descriptor)
    nodes = node_by_id(descriptor)
    diagram_type = descriptor.get("type") or "architecture"
    default_style = "premium" if diagram_type in {"architecture", "hub-spoke"} else "simple"

    rects = {
        node_id: estimate_rect(
            node,
            canvas_w=viewport_w,
            canvas_h=canvas_h,
            card_style=default_style,
        )
        for node_id, node in nodes.items()
    }

    for pair in pairs:
        left_id = pair.get("left")
        right_id = pair.get("right")
        if left_id and right_id:
            a = rects.get(left_id)
            b = rects.get(right_id)
            if not a or not b:
                findings.append(
                    Finding("error", "pair-missing", f"cannot measure {left_id}->{right_id}")
                )
                continue
            gap = round(b["left"] - a["right"])
            needed = pair.get("min_gap_px", 0)
            if gap < needed:
                level = "error" if strict else "warn"
                code = "min-gap" if strict else "min-gap-narrow"
                findings.append(
                    Finding(
                        level,
                        code,
                        f"{left_id}->{right_id}: estimated gap {gap}px < {needed}px at {viewport_w}px width",
                        {"gap": gap, "viewport_w": viewport_w},
                    )
                )

        zone_id = pair.get("zone")
        node_id = pair.get("label_to_node")
        if zone_id and node_id:
            zone = next((z for z in descriptor.get("zones") or [] if z.get("id") == zone_id), None)
            node_rect = rects.get(node_id)
            if not zone or not node_rect:
                findings.append(
                    Finding("error", "zone-pair-missing", f"cannot measure {zone_id}->{node_id}")
                )
                continue

            member_ids = zone.get("nodes") or []
            member_rects = [rects[mid] for mid in member_ids if mid in rects]
            if not member_rects:
                continue

            pad = zone_padding(zone)
            y_min = min(r["top"] for r in member_rects)
            zone_top = y_min - pad["top"]
            label_bottom = zone_top + ZONE_LABEL_HEIGHT
            gap = round(node_rect["top"] - label_bottom)
            needed = pair.get("min_gap_px", layout.get("min_zone_label_gap_px", 8))
            if gap < needed:
                level = "error" if strict else "warn"
                findings.append(
                    Finding(
                        level,
                        "zone-label-gap" if strict else "zone-label-gap-narrow",
                        f"{zone_id}->{node_id}: estimated label gap {gap}px < {needed}px at {viewport_w}px width",
                        {"gap": gap, "viewport_w": viewport_w},
                    )
                )

    return findings


def validate(descriptor: dict, expect: dict[str, Any]) -> list[Finding]:
    findings = schema_checks(descriptor)
    if any(f.level == "error" for f in findings):
        return findings

    viewport = expect.get("viewport") or {"width": 1600, "height": 1200}
    primary_w = int(viewport.get("width", 1600))
    viewport_h = int(viewport.get("height", 1200))
    widths = [(primary_w, True), (900, False), (1200, False)]

    for width, strict in widths:
        if width == primary_w or width < primary_w:
            findings.extend(
                pair_gap_checks(
                    descriptor,
                    expect,
                    viewport_w=width,
                    viewport_h=viewport_h,
                    strict=strict,
                )
            )

    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate fd-engine descriptor JSON before gen-fd.py")
    parser.add_argument("--in", dest="input_path", required=True, help="Descriptor JSON")
    parser.add_argument("--expect", type=Path, default=None, help="Expectations JSON (layout pairs)")
    args = parser.parse_args()

    root = script_root(__file__)
    input_path = Path(args.input_path).resolve()
    if not input_path.exists():
        print(f"validate-descriptor: file not found: {input_path}", file=sys.stderr)
        sys.exit(2)

    expect_path = args.expect.resolve() if args.expect else None
    if expect_path is None:
        sibling = input_path.with_suffix(".expect.json")
        if sibling.exists():
            expect_path = sibling
    if expect_path is None:
        default = default_expect_path(root)
        if default:
            expect_path = default

    expect = json.loads(expect_path.read_text(encoding="utf-8")) if expect_path else {}
    descriptor = json.loads(input_path.read_text(encoding="utf-8"))

    findings = validate(descriptor, expect)
    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warn"]

    for finding in findings:
        print(finding.format(), file=sys.stderr)

    if errors:
        print(
            f"\nvalidate-descriptor: FAIL — {len(errors)} error(s), {len(warns)} warning(s)",
            file=sys.stderr,
        )
        sys.exit(1)

    msg = "validate-descriptor: PASS — descriptor layout ok"
    if warns:
        msg += f" ({len(warns)} warning(s))"
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()