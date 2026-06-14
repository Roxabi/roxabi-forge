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

if 'DIAGRAMS_DIR' in os.environ and 'FORGE_DIR' not in os.environ:
    print('⚠ DIAGRAMS_DIR is deprecated — use FORGE_DIR')
DIR = Path(os.environ.get('FORGE_DIR', os.environ.get('DIAGRAMS_DIR', Path.home() / '.roxabi' / 'forge')))

BASE_URL = 'https://forge.roxabi.dev'


def should_exclude(rel):
    name = rel.rsplit('/', 1)[-1]
    return name == 'index.html' or '/tabs/' in rel or rel.startswith('tabs/') or rel.startswith('_dist/')


def og_png_for(html):
    return html.with_suffix('.og.png')


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

    if not worklist:
        print('og-images — 0 rendered (all up-to-date).')
        sys.exit(0)

    from playwright.sync_api import sync_playwright

    rendered = 0

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
                page.goto(html.resolve().as_uri(), wait_until='networkidle', timeout=30000)
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

        browser.close()

    up_to_date = len(candidates) - len(worklist)
    print(f'og-images — {rendered} rendered, {up_to_date} up-to-date.')


if __name__ == '__main__':
    main()
