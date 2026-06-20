#!/usr/bin/env python3
"""Playwright layout checks for validate-fd.py — run via uv run --with playwright."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

EVALUATE_JS = """
(layout) => {
  const canvas = document.getElementById('fd-canvas');
  if (!canvas) return { error: 'missing-fd-canvas' };
  const cr = canvas.getBoundingClientRect();

  function nodeRect(id) {
    const el = document.querySelector('[data-id="' + id + '"]');
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      id,
      position: cs.position,
      relTop: Math.round(r.top - cr.top),
      relBottom: Math.round(r.bottom - cr.top),
      top: Math.round(r.top),
      left: Math.round(r.left),
      right: Math.round(r.right),
      premium: el.classList.contains('fd-card-premium'),
    };
  }

  const nodes = [...document.querySelectorAll('.fd-node')].map((el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      id: el.dataset.id || '',
      position: cs.position,
      relTop: Math.round(r.top - cr.top),
      relBottom: Math.round(r.bottom - cr.top),
      premium: el.classList.contains('fd-card-premium'),
    };
  });

  const inCanvas = nodes.filter(
    (n) => n.relTop >= -2 && n.relBottom <= Math.round(cr.height) + 2
  ).length;

  const zones = [...document.querySelectorAll('.fd-zone')].length;
  const paths = document.querySelectorAll('#fd-edges path, .fd-edges path').length;

  const pairs = {};
  for (const pair of layout.pairs || []) {
    if (pair.left && pair.right) {
      const a = nodeRect(pair.left);
      const b = nodeRect(pair.right);
      if (!a || !b) {
        pairs[pair.left + '->' + pair.right] = { error: 'missing-node' };
      } else {
        pairs[pair.left + '->' + pair.right] = { gap: b.left - a.right, a, b };
      }
    }
    if (pair.zone && pair.label_to_node) {
      const z = document.getElementById(pair.zone);
      const n = nodeRect(pair.label_to_node);
      if (!z || !n) {
        pairs[pair.zone + '->' + pair.label_to_node] = { error: 'missing-zone-or-node' };
      } else {
        const lbl = z.querySelector('.fd-zone-label, .zl');
        const lr = lbl ? lbl.getBoundingClientRect() : null;
        pairs[pair.zone + '->' + pair.label_to_node] = {
          gap: lr ? Math.round(n.top - lr.bottom) : null,
        };
      }
    }
  }

  return {
    canvasH: Math.round(cr.height),
    nodes,
    inCanvas,
    zones,
    paths,
    pairs,
  };
}
"""


def fail(findings: list, code: str, message: str, detail=None) -> None:
    findings.append({"level": "error", "code": code, "message": message, "detail": detail})


def main() -> None:
    html_path = Path(sys.argv[1]).resolve()
    expect = json.loads(sys.argv[2])
    url = html_path.as_uri()

    findings: list[dict] = []
    layout = expect.get("layout", {})
    viewport = expect.get("viewport", {"width": 1600, "height": 1200})
    counts = expect.get("counts", {})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport)
        page.goto(url, wait_until="load")
        time.sleep(1.2)
        stats = page.evaluate(EVALUATE_JS, layout)
        browser.close()

    if stats.get("error"):
        fail(findings, stats["error"], "fd-canvas missing from rendered page")
    else:
        expected_nodes = counts.get("nodes")
        if expected_nodes is not None and len(stats["nodes"]) != expected_nodes:
            fail(
                findings,
                "node-count",
                f"expected {expected_nodes} .fd-node elements, got {len(stats['nodes'])}",
            )

        expected_zones = counts.get("zones")
        if expected_zones is not None and stats["zones"] != expected_zones:
            fail(findings, "zone-count", f"expected {expected_zones} zones, got {stats['zones']}")

        paths_min = counts.get("paths_min")
        if paths_min is not None and stats["paths"] < paths_min:
            fail(
                findings,
                "path-count",
                f"expected at least {paths_min} SVG paths, got {stats['paths']}",
            )

        if layout.get("all_nodes_absolute"):
            bad = [n for n in stats["nodes"] if n["position"] != "absolute"]
            if bad:
                fail(
                    findings,
                    "node-position",
                    f"{len(bad)} node(s) are not position:absolute",
                    bad[:6],
                )

        if layout.get("all_nodes_in_canvas"):
            if stats["inCanvas"] != len(stats["nodes"]):
                fail(
                    findings,
                    "node-in-canvas",
                    f"{stats['inCanvas']}/{len(stats['nodes'])} nodes inside canvas height {stats['canvasH']}px",
                )

        pair_min: dict[str, int] = {}
        for pair in layout.get("pairs", []):
            if pair.get("left") and pair.get("right"):
                pair_min[f"{pair['left']}->{pair['right']}"] = pair.get("min_gap_px", 0)
            if pair.get("zone") and pair.get("label_to_node"):
                pair_min[f"{pair['zone']}->{pair['label_to_node']}"] = pair.get(
                    "min_gap_px", layout.get("min_zone_label_gap_px", 8)
                )

        for key, data in stats["pairs"].items():
            if data.get("error"):
                fail(findings, "pair-missing", f"layout pair check failed for {key}", data)
                continue
            if data.get("gap") is None:
                fail(findings, "pair-gap", f"could not measure gap for {key}", data)
                continue
            needed = pair_min.get(key)
            if needed is not None and data["gap"] < needed:
                fail(
                    findings,
                    "min-gap",
                    f"{key}: gap {data['gap']}px < required {needed}px",
                    data,
                )

    print(json.dumps(findings, ensure_ascii=False))
    sys.exit(1 if any(f["level"] == "error" for f in findings) else 0)


if __name__ == "__main__":
    main()