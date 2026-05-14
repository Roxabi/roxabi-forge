#!/usr/bin/env python3
"""gen-og-tags.py — inject/normalize Open Graph + Twitter Card meta tags into HTML artifacts.

Reads diagram:title (or <title>) and description meta from each file, then
writes a canonical OG block right after <meta name="viewport" ...>.
Idempotent — strips any existing OG/Twitter meta before injecting.

Run during build:
    python3 gen-og-tags.py
"""
import glob as globmod
import os, re
from html import escape, unescape
from pathlib import Path

if 'DIAGRAMS_DIR' in os.environ and 'FORGE_DIR' not in os.environ:
    print('⚠ DIAGRAMS_DIR is deprecated — use FORGE_DIR')
DIR = Path(os.environ.get('FORGE_DIR', os.environ.get('DIAGRAMS_DIR', Path.home() / '.roxabi' / 'forge')))

BASE_URL = 'https://forge.roxabi.dev'
OG_IMAGE_URL = f'{BASE_URL}/og-image.png'

META_RE = re.compile(r'<meta\s+name="diagram:([\w-]+)"\s+content="([^"]*)"', re.IGNORECASE)
TITLE_RE = re.compile(r'<title>([^<]+)</title>', re.IGNORECASE)
DESC_RE = re.compile(r'<meta\s+name="description"\s+content="([^"]*)"', re.IGNORECASE)

# Matches existing OG / Twitter meta lines (to strip before re-injecting)
OG_LINE_RE = re.compile(
    r'^[ \t]*<meta\s+(?:property="og:|name="twitter:)[^>]*>\s*\n?',
    re.IGNORECASE | re.MULTILINE,
)
# Anchor: inject right after the viewport meta
VIEWPORT_RE = re.compile(
    r'(<meta\s+name="viewport"[^>]*>)\s*\n?',
    re.IGNORECASE,
)


def build_og_block(title, description, url):
    t = escape(title, quote=True)
    d = escape(description, quote=True)
    u = escape(url, quote=True)
    img = escape(OG_IMAGE_URL, quote=True)
    return (
        f'<meta property="og:title" content="{t}">\n'
        f'<meta property="og:description" content="{d}">\n'
        f'<meta property="og:type" content="article">\n'
        f'<meta property="og:url" content="{u}">\n'
        f'<meta property="og:image" content="{img}">\n'
        f'<meta property="og:image:width" content="1200">\n'
        f'<meta property="og:image:height" content="630">\n'
        f'<meta property="og:site_name" content="Roxabi Forge">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:title" content="{t}">\n'
        f'<meta name="twitter:description" content="{d}">\n'
        f'<meta name="twitter:image" content="{img}">\n'
    )


SKIP_NO_HEAD = 'no_head'
SKIP_NO_TITLE = 'no_title'
SKIP_NO_VIEWPORT = 'no_viewport'
SKIP_UP_TO_DATE = 'up_to_date'


def process(filepath, rel):
    text = filepath.read_text(encoding='utf-8', errors='ignore')

    head_end = text.lower().find('</head>')
    if head_end == -1:
        return SKIP_NO_HEAD
    head = text[:head_end]

    # Extract title: prefer diagram:title, fall back to <title>
    # unescape() prevents double-encoding (content attrs are already HTML-escaped)
    metas = {k: unescape(v) for k, v in META_RE.findall(head)}
    title = metas.get('title', '')
    if not title:
        m = TITLE_RE.search(head)
        if not m:
            return SKIP_NO_TITLE
        title = unescape(m.group(1).strip())

    dm = DESC_RE.search(head)
    description = unescape(dm.group(1).strip()) if dm else title

    url = f'{BASE_URL}/{rel}'

    cleaned = OG_LINE_RE.sub('', text)

    vm = VIEWPORT_RE.search(cleaned)
    if not vm:
        return SKIP_NO_VIEWPORT

    og_block = build_og_block(title, description, url)
    insert_at = vm.end()
    new_text = cleaned[:insert_at] + og_block + cleaned[insert_at:]

    if new_text != text:
        filepath.write_text(new_text, encoding='utf-8')
        return None  # updated
    return SKIP_UP_TO_DATE


injected = 0
skipped: dict[str, list[str]] = {SKIP_NO_TITLE: [], SKIP_NO_VIEWPORT: [], SKIP_NO_HEAD: []}
up_to_date = 0
for match in sorted(globmod.glob(str(DIR / '**/*.html'), recursive=True)):
    fp = Path(match)
    rel = str(fp.relative_to(DIR))
    if fp.name == 'index.html' or '/tabs/' in rel or rel.startswith('tabs/') or rel.startswith('_dist/'):
        continue
    result = process(fp, rel)
    if result is None:
        injected += 1
    elif result == SKIP_UP_TO_DATE:
        up_to_date += 1
    else:
        skipped[result].append(rel)

parts = [f'og-tags — {injected} updated, {up_to_date} already up-to-date.']
for reason, files in skipped.items():
    if files:
        label = reason.replace('_', ' ')
        parts.append(f'  ⚠ skipped ({label}) — {len(files)} files:')
        parts.extend(f'      {f}' for f in files)
print('\n'.join(parts))
