#!/usr/bin/env python3
"""Capture showcase-index card thumbnails for each catalog artifact.

Outputs PNGs to plugins/forge/references/thumbs/{slug}.png where slug is the
HTML filename stem (e.g. showcase-chart, craft-hub-spoke).

Run:
    uv run --with playwright python3 scripts/gen-showcase-thumbs.py [--force]

Graceful degradation: exits 0 if chromium is unavailable (cards fall back to slug).
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "plugins" / "forge" / "references"
THUMBS = REFS / "thumbs"
LEGACY_THUMBS = Path.home() / ".roxabi" / "forge" / "thumbs"

VIEWPORTS: dict[str, tuple[int, int]] = {
    "skill": (1440, 900),
    "craft": (960, 640),
    "fd-engine": (1200, 800),
    "fgraph": (1200, 800),
    "gallery": (1200, 800),
}

REVEAL_JS = """
() => {
  document.querySelectorAll('.reveal,[data-reveal]').forEach(el => {
    el.classList.add('revealed','in-view','visible','is-visible');
    el.style.opacity = '1';
    el.style.transform = 'none';
  });
  document.querySelectorAll('.slide').forEach((el, i) => {
    if (i === 0) el.classList.add('visible');
  });
  document.querySelectorAll('.panel').forEach((el, i) => {
    el.classList.toggle('active', i === 0);
  });
  document.querySelectorAll('.tab-btn').forEach((el, i) => {
    el.classList.toggle('active', i === 0);
    el.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
  });
}
"""


def load_catalog():
    script = ROOT / "scripts" / "build-reference-showcases.py"
    spec = importlib.util.spec_from_file_location("build_reference_showcases", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load catalog from {script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SHOWCASE_CATALOG, mod.REFS


def catalog_items(catalog: list[dict]) -> list[tuple[str, str, Path]]:
    """Return (section_filter, href, html_path) for existing artifacts."""
    items: list[tuple[str, str, Path]] = []
    for section in catalog:
        filt = section["filter"]
        for entry in section["items"]:
            href = entry["href"]
            html = REFS / href
            if html.exists():
                items.append((filt, href, html))
    return items


def is_stale(html: Path, png: Path) -> bool:
    if not png.exists():
        return True
    return png.stat().st_mtime < html.stat().st_mtime


def seed_legacy(slug: str, dest: Path) -> bool:
    legacy = LEGACY_THUMBS / f"{slug}.png"
    if legacy.exists() and (not dest.exists() or dest.stat().st_mtime < legacy.stat().st_mtime):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(legacy.read_bytes())
        return True
    return False


def capture(page, html: Path, png: Path, section_filter: str) -> None:
    w, h = VIEWPORTS.get(section_filter, (1200, 800))
    page.set_viewport_size({"width": w, "height": h})
    page.goto(html.resolve().as_uri(), wait_until="networkidle", timeout=45000)
    page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
    page.evaluate(REVEAL_JS)
    page.wait_for_timeout(500)

    tmp = png.parent / (png.stem + ".tmp.png")
    # Craft pages center a fixed 960×640 canvas — full viewport capture is reliable;
    # element screenshots collapse when children are absolutely positioned.
    page.screenshot(path=str(tmp), full_page=False)
    os.replace(tmp, png)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render showcase-index card thumbnails.")
    parser.add_argument("--force", action="store_true", help="re-render even if up-to-date")
    args = parser.parse_args()

    catalog, _ = load_catalog()
    items = catalog_items(catalog)
    THUMBS.mkdir(parents=True, exist_ok=True)

    seeded = 0
    worklist: list[tuple[str, Path, Path, str]] = []
    for section_filter, href, html in items:
        slug = Path(href).stem
        png = THUMBS / f"{slug}.png"
        if seed_legacy(slug, png):
            seeded += 1
        if args.force or is_stale(html, png):
            worklist.append((slug, html, png, section_filter))

    if not worklist:
        print(f"showcase-thumbs — 0 rendered, {seeded} seeded from legacy (all up-to-date).")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("⚠ playwright not installed — seeded legacy thumbs only; cards may use slug fallback")
        print(f"showcase-thumbs — 0 rendered, {seeded} seeded, {len(items) - seeded} missing.")
        return

    rendered = 0
    failed = 0

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:
            print(f"⚠ chromium launch failed ({exc}) — cards fall back to slug text")
            print(f"showcase-thumbs — 0 rendered, {seeded} seeded.")
            return

        page = browser.new_page()
        for slug, html, png, section_filter in worklist:
            try:
                capture(page, html, png, section_filter)
                rendered += 1
                print(f"  ✓ {slug}.png")
            except Exception as exc:
                print(f"  ⚠ {slug}: {exc}")
                (png.parent / (png.stem + ".tmp.png")).unlink(missing_ok=True)
                failed += 1
        browser.close()

    up_to_date = len(items) - len(worklist)
    print(
        f"showcase-thumbs — {rendered} rendered, {up_to_date} up-to-date, "
        f"{seeded} seeded, {failed} failed."
    )


if __name__ == "__main__":
    main()