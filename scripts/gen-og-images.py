#!/usr/bin/env python3
"""gen-og-images.py — screenshot each eligible artifact into a sibling <name>.og.png.

Run during build (playwright must be installed in the uv environment):
    uv run --with playwright python3 gen-og-images.py [--force]

Idempotency: a PNG is (re-)rendered only when it is missing or older than its
source HTML.  Pass --force to bypass the mtime check and re-render everything.

Graceful degradation: if chromium is unavailable the script exits 0 and OG
cards fall back to the global banner image (no build failure).
"""
import argparse
import glob as globmod
import os
import sys
import tempfile
from pathlib import Path

from _og_common import og_png_for, should_exclude

if 'DIAGRAMS_DIR' in os.environ and 'FORGE_DIR' not in os.environ:
    print('⚠ DIAGRAMS_DIR is deprecated — use FORGE_DIR')
DIR = Path(os.environ.get('FORGE_DIR', os.environ.get('DIAGRAMS_DIR', Path.home() / '.roxabi' / 'forge')))

BASE_URL = 'https://forge.roxabi.dev'


def is_stale(html, png):
    if not png.exists():
        return True
    return png.stat().st_mtime < html.stat().st_mtime


def run_self_test():
    # should_exclude assertions
    assert should_exclude('index.html'), 'index.html must be excluded'
    assert should_exclude('sub/index.html'), 'sub/index.html must be excluded'
    assert should_exclude('a/tabs/x.html'), 'tabs path must be excluded'
    assert should_exclude('tabs/x.html'), 'tabs/ prefix must be excluded'
    assert should_exclude('_dist/y.html'), '_dist/ prefix must be excluded'
    assert should_exclude('references/graph-templates/fd-shell.html'), \
        'graph-templates/*.html build templates must be excluded'
    assert should_exclude('references/graph-templates/dep-graph.html'), \
        'immediate-level graph-templates shells must be excluded'
    assert should_exclude('references/gallery-templates/simple-gallery.html'), \
        'immediate-level gallery-templates shells must be excluded'
    assert should_exclude('references/diagrams/craft-diagram-starter.html'), \
        'craft-diagram-starter scaffold must be excluded'
    assert not should_exclude('references/graph-templates/examples/fd-architecture.html'), \
        'graph-templates/examples/ goldens must NOT be excluded'
    assert not should_exclude('references/graph-templates/examples/fd-architecture-uc.html'), \
        'graph-templates/examples/ goldens must NOT be excluded'
    assert not should_exclude('roxabi-factory/visuals/factory-workflow.html'), \
        'factory-workflow.html must NOT be excluded'

    # is_stale assertions
    with tempfile.TemporaryDirectory() as td:
        html = Path(td) / 'a.html'
        png = Path(td) / 'a.og.png'
        html.write_text('<html></html>')

        # missing png → stale
        assert is_stale(html, png), 'missing png must be stale'

        png.write_bytes(b'x')
        # set png mtime older than html
        os.utime(html, (1_000_000, 1_000_000))
        os.utime(png, (999_999, 999_999))
        assert is_stale(html, png), 'older png must be stale'

        # set png mtime newer than html
        os.utime(png, (1_000_001, 1_000_001))
        assert not is_stale(html, png), 'newer png must NOT be stale'

    print('self-test OK')
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Render per-artifact OG preview images.')
    parser.add_argument('--force', action='store_true', help='re-render even if up-to-date')
    parser.add_argument('--self-test', action='store_true', dest='self_test',
                        help='run assertions and exit (no playwright required)')
    args = parser.parse_args()

    if args.self_test:
        run_self_test()

    candidates = []
    for match in sorted(globmod.glob(str(DIR / '**/*.html'), recursive=True)):
        html = Path(match)
        rel = str(html.relative_to(DIR))
        if should_exclude(rel):
            continue
        candidates.append((html, rel))

    worklist = []
    for html, rel in candidates:
        png = og_png_for(html)
        if args.force or is_stale(html, png):
            worklist.append((html, png, rel))

    # Prune orphan .og.png files (no matching .html, or excluded) — runs every invocation
    # Candidates are already filtered by should_exclude, so no worklist entry is pruned here.
    pruned = 0
    for png in sorted(DIR.glob('**/*.og.png')):
        rel_png = str(png.relative_to(DIR))
        if rel_png.startswith('_dist/'):
            continue
        stem = png.name.removesuffix('.og.png')
        html = png.parent / (stem + '.html')
        html_rel = str(html.relative_to(DIR))
        if not html.exists() or should_exclude(html_rel):
            png.unlink()
            pruned += 1

    if not worklist:
        print(f'og-images — 0 rendered, 0 failed, {pruned} pruned (all up-to-date).')
        sys.exit(0)

    from playwright.sync_api import sync_playwright

    rendered = 0
    failed = 0

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as e:
            print(f'⚠ chromium launch failed ({e}) — skipping OG images; cards fall back to banner')
            sys.exit(0)

        context = browser.new_context(
            viewport={'width': 1200, 'height': 630},
            device_scale_factor=2,
        )
        page = context.new_page()

        for html, png, rel in worklist:
            tmp = png.parent / (png.stem + '.tmp.png')
            try:
                url = html.resolve().as_uri()
                if '/references/diagrams/' in rel:
                    url += '?embed=hero' if '?' not in url else '&embed=hero'
                page.goto(url, wait_until='networkidle', timeout=30000)
                page.evaluate('document.fonts ? document.fonts.ready.then(() => true) : true')
                page.evaluate(
                    "() => { document.querySelectorAll('.reveal,[data-reveal]').forEach(el => {"
                    " el.classList.add('revealed','in-view','visible','is-visible');"
                    " el.style.opacity='1'; el.style.transform='none' }) }"
                )
                page.wait_for_timeout(400)
                page.screenshot(path=str(tmp), full_page=False)
                os.replace(tmp, png)
                rendered += 1
            except Exception as e:
                print(f'  ⚠ render failed for {rel}: {e}')
                tmp.unlink(missing_ok=True)
                failed += 1

        browser.close()

    up_to_date = len(candidates) - len(worklist)
    print(f'og-images — {rendered} rendered, {up_to_date} up-to-date, {failed} failed, {pruned} pruned.')


if __name__ == '__main__':
    main()
