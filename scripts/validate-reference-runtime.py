#!/usr/bin/env python3
"""Validate runnable reference artifacts — placeholders, craft-anchors boot, HTML safety."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "plugins" / "forge" / "references"

PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")
CRAFT_PATHS = [
    REFS / "diagrams/examples/craft-hub-spoke.html",
    REFS / "diagrams/examples/craft-deploy-flow.html",
    REFS / "diagrams/examples/craft-diagram-starter-preview.html",
]


def load_catalog() -> list[dict]:
    spec = importlib.util.spec_from_file_location(
        "build_reference_showcases", ROOT / "scripts" / "build-reference-showcases.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load SHOWCASE_CATALOG")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sections = mod._catalog_items_existing()
    return [item for section in sections for item in section["items"]]


def check_placeholders(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # Ignore placeholders inside HTML comments
    body = re.sub(r"<!--[\s\S]*?-->", "", text)
    found = PLACEHOLDER.findall(body)
    if found:
        return [f"unresolved placeholders: {', '.join(sorted(set(found))[:8])}"]
    return []


def check_craft_script_safety(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues = []
    for m in re.finditer(r"<script(?![^>]*application/json)[^>]*>([\s\S]*?)</script>", text):
        block = m.group(1)
        if "craft-anchors" in block and "</script>" in block:
            issues.append("craft-anchors script contains literal </script>")
    return issues


def check_craft_runtime(path: Path) -> list[str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []  # static checks only
    issues: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda e: issues.append(f"pageerror: {e}"))
        page.goto(path.as_uri(), wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)
        data = page.evaluate(
            """() => {
              const d = document.querySelector('.diagram');
              const w = d ? parseFloat(getComputedStyle(d).width) : 0;
              return {
                craft: typeof CraftAnchors !== 'undefined',
                paths: document.querySelectorAll('svg.craft-connections path').length,
                diagramWidth: w,
                bodyChildren: document.body.children.length
              };
            }"""
        )
        if not data.get("craft"):
            issues.append("CraftAnchors undefined")
        if data.get("paths", 0) < 1:
            issues.append(f"no craft connection paths (count={data.get('paths')})")
        if data.get("diagramWidth", 0) < 400:
            issues.append(f"diagram collapsed (width={data.get('diagramWidth')}px)")
        if data.get("bodyChildren", 0) > 2:
            issues.append(f"leaked body children (count={data.get('bodyChildren')})")
        browser.close()
    return issues


def main() -> int:
    errors: list[str] = []
    warns: list[str] = []

    items = load_catalog()
    for item in items:
        path = REFS / item["href"]
        if not path.exists():
            errors.append(f"missing: {item['href']}")
            continue
        errors.extend(f"{item['href']}: {m}" for m in check_placeholders(path))
        errors.extend(f"{item['href']}: {m}" for m in check_craft_script_safety(path))

    for path in CRAFT_PATHS:
        if not path.exists():
            errors.append(f"missing craft golden: {path.relative_to(REFS)}")
            continue
        errors.extend(f"{path.name}: {m}" for m in check_craft_script_safety(path))
        rt = check_craft_runtime(path)
        for m in rt:
            (errors if "undefined" in m or "pageerror" in m else warns).append(f"{path.name}: {m}")

    print(f"validate-reference-runtime — {len(items)} catalog artifacts")
    for w in warns:
        print(f"  WARN: {w}")
    for e in errors:
        print(f"  FAIL: {e}")

    if errors:
        print(f"validate-reference-runtime — FAILED ({len(errors)} errors)")
        return 1
    print(f"validate-reference-runtime — OK ({len(warns)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())