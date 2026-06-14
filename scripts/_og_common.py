"""_og_common.py — shared helpers for OG image/tag scripts (single source of truth)."""


def should_exclude(rel):
    """Return True if the artifact at relative path rel should be skipped."""
    name = rel.rsplit('/', 1)[-1]
    return name == 'index.html' or '/tabs/' in rel or rel.startswith('tabs/') or rel.startswith('_dist/')


def og_png_for(html):
    """Return the sibling .og.png Path for a given html Path."""
    return html.with_suffix('.og.png')
