"""_og_common.py — shared helpers for OG image/tag scripts (single source of truth)."""


def should_exclude(rel):
    """Return True if the artifact at relative path rel should be skipped."""
    name = rel.rsplit('/', 1)[-1]
    if name == 'index.html' or '/tabs/' in rel or rel.startswith('tabs/') or rel.startswith('_dist/'):
        return True
    # graph-templates/*.html are build-time shells/templates (e.g. fd-shell.html),
    # excluded from _dist by build.sh (--exclude='graph-templates/*.html'). Don't
    # generate/ship their OG either. Goldens under graph-templates/examples/ DO
    # publish (deeper path), so match only the immediate level — mirrors rsync's
    # '*' not crossing '/'.
    if 'graph-templates/' in rel:
        tail = rel.split('graph-templates/', 1)[1]
        if '/' not in tail:
            return True
    return False


def og_png_for(html):
    """Return the sibling .og.png Path for a given html Path."""
    return html.with_suffix('.og.png')
