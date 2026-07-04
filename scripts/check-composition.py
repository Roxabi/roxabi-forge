#!/usr/bin/env python3
"""check-composition.py — structural contract for presentation × diagram composition.

Validates that presentations use iframe SSoT (not inline craft diagram CSS) and that
registered diagram files exist.

Usage:
  python3 check-composition.py --presentation ~/.roxabi/forge/PROJ/visuals/doc.html
  python3 check-composition.py --presentation doc.html --check
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INLINE_CRAFT_MARKERS = (".craft-embed",)
DIAGRAM_SRC_RE = re.compile(
    r'<iframe[^>]+class="[^"]*diagram-frame[^"]*"[^>]+src="(?:\.\./)?diagrams/(?:examples/)?([^"]+)"',
    re.IGNORECASE,
)
NESTED_REVEAL_RE = re.compile(
    r'<(?:div|section)[^>]*class="[^"]*(?:arch-wrap|panel-wrap)[^"]*reveal[^"]*"[^>]*>'
    r'[\s\S]*?<figure[^>]*class="[^"]*diagram-embed[^"]*reveal[^"]*"',
    re.IGNORECASE,
)
FIGCAPTION_RE = re.compile(r"<figure[^>]*diagram-embed[^>]*>[\s\S]*?<figcaption", re.IGNORECASE)


def check(presentation: Path, diagrams_dir: Path | None) -> list[str]:
    errors: list[str] = []
    if not presentation.exists():
        return [f"presentation not found: {presentation}"]

    html = presentation.read_text(encoding="utf-8")
    visuals = presentation.parent
    ddir = diagrams_dir or visuals / "diagrams"

    for marker in INLINE_CRAFT_MARKERS:
        if marker in html:
            errors.append(f"inline {marker} detected — use diagrams/*.html + iframe")
            break

    if NESTED_REVEAL_RE.search(html):
        errors.append("diagram-embed has nested .reveal — reveal on wrapper only")

    if FIGCAPTION_RE.search(html):
        errors.append("figcaption on diagram-embed — title belongs inside diagram SSoT")

    if "diagram-frame" not in html and "diagram-embed" in html:
        errors.append("diagram-embed without .diagram-frame iframe")

    slugs = [s.split("?")[0] for s in DIAGRAM_SRC_RE.findall(html)]
    if "diagram-embed" in html and not slugs:
        errors.append('diagram-embed present but no craft diagram iframe src found')

    for slug in slugs:
        slug = slug.split("?")[0]
        candidates = [ddir / slug]
        if diagrams_dir is None:
            # Plugin showcase layout: showcases/ → ../diagrams/examples/
            candidates.append(visuals.parent / "diagrams" / "examples" / slug)
            candidates.append(visuals / "diagrams" / slug)
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            errors.append(f"missing diagram SSoT: {ddir / slug}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check presentation composition contract")
    parser.add_argument("--presentation", "-p", required=True, type=Path)
    parser.add_argument("--diagrams-dir", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="exit 1 on violations")
    args = parser.parse_args()

    errors = check(args.presentation.resolve(), args.diagrams_dir)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1 if args.check else 0

    n = len([s.split("?")[0] for s in DIAGRAM_SRC_RE.findall(args.presentation.read_text(encoding="utf-8"))])
    print(f"check OK — presentation {args.presentation.name}, {n} diagram iframe(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())