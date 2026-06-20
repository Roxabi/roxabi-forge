#!/usr/bin/env python3
"""
audit-forge-diagrams.py — scan ~/.roxabi/forge for fd-engine vs legacy diagram HTML.

Outputs JSON manifest: engine type, fd-data presence, sibling JSON descriptor, action hint.

Usage:
  python3 scripts/audit-forge-diagrams.py
  python3 scripts/audit-forge-diagrams.py --forge-dir ~/.roxabi/forge --out /tmp/forge-audit.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FD_DATA_RE = re.compile(r'<script[^>]+id="fd-data"', re.IGNORECASE)
ENGINE_RE = re.compile(r'name="diagram:engine"\s+content="([^"]+)"', re.IGNORECASE)
SKIP_DIRS = {"_dist", "scripts", "__pycache__", ".git"}


def classify_html(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    engine_match = ENGINE_RE.search(text)
    engine = engine_match.group(1) if engine_match else None
    has_fd_data = bool(FD_DATA_RE.search(text))

    json_sibling = path.with_suffix(".json")
    has_json = json_sibling.exists()

    if engine == "fd-engine" or has_fd_data:
        category = "fd-engine"
        action = "validate" if has_fd_data else "needs-fd-data"
    elif "fgraph-node" in text or "fg-render" in text:
        category = "fgraph-legacy"
        action = "migrate-if-json" if has_json else "manual-review"
    else:
        category = "other"
        action = "skip"

    return {
        "path": str(path),
        "engine": engine,
        "has_fd_data": has_fd_data,
        "has_json": has_json,
        "json_path": str(json_sibling) if has_json else None,
        "category": category,
        "action": action,
    }


def walk_forge(forge_dir: Path) -> list[dict]:
    results: list[dict] = []
    for path in sorted(forge_dir.rglob("*.html")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in {"index.html", "fd-shell.html"}:
            continue
        results.append(classify_html(path))
    return results


def summarize(entries: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
    migrate_candidates = [
        e for e in entries if e["action"] in {"migrate-if-json", "validate"} and e.get("json_path")
    ]
    return {
        "total_html": len(entries),
        "by_category": counts,
        "migrate_candidates": len(migrate_candidates),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit forge HTML diagrams")
    parser.add_argument("--forge-dir", type=Path, default=Path.home() / ".roxabi" / "forge")
    parser.add_argument("--out", type=Path, default=None, help="Write JSON manifest")
    args = parser.parse_args()

    forge_dir = args.forge_dir.expanduser().resolve()
    if not forge_dir.is_dir():
        print(f"audit-forge-diagrams: not a directory: {forge_dir}", file=sys.stderr)
        sys.exit(2)

    entries = walk_forge(forge_dir)
    report = {"forge_dir": str(forge_dir), "summary": summarize(entries), "entries": entries}
    payload = json.dumps(report, indent=2, ensure_ascii=False)

    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"audit-forge-diagrams: wrote {args.out} ({report['summary']['total_html']} files)", file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()