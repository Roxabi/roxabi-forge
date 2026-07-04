"""_og_common.py — shared helpers for OG image/tag scripts (single source of truth)."""


def _immediate_template_dir(rel, marker):
    """True when rel is graph-templates/foo.html (not examples/foo.html)."""
    if f'{marker}/' not in rel:
        return False
    tail = rel.split(f'{marker}/', 1)[1]
    return '/' not in tail


def should_exclude(rel):
    """Return True if the artifact at relative path rel should be skipped."""
    name = rel.rsplit('/', 1)[-1]
    if name == 'index.html' or '/tabs/' in rel or rel.startswith('tabs/') or rel.startswith('_dist/'):
        return True
    # Authoring scaffolds — copy-from templates with {Title} placeholders, not gallery artifacts.
    if rel == 'references/diagrams/craft-diagram-starter.html':
        return True
    # graph-templates/*.html and gallery-templates/*.html are build-time shells.
    # Goldens under */examples/ DO publish (deeper path) — mirrors rsync's '*' depth.
    if _immediate_template_dir(rel, 'graph-templates'):
        return True
    if _immediate_template_dir(rel, 'gallery-templates'):
        return True
    return False


def og_png_for(html):
    """Return the sibling .og.png Path for a given html Path."""
    return html.with_suffix('.og.png')
