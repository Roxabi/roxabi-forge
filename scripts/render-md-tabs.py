#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "markdown>=3.5",
#     "pymdown-extensions>=10.0",
# ]
# ///
"""render-md-tabs.py — render multiple markdown files into one tabbed HTML.

Uses the same roxabi dark aesthetic as render-md.py, but combines N markdown
files into a single self-contained HTML with a tab bar. Tab selection is
persisted in the URL hash so deep links work.

Usage:
  render-md-tabs.py <dir> -o <out.html>           # all *.md in dir
  render-md-tabs.py <f1.md> <f2.md> -o <out.html> # explicit files
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import markdown


SHELL = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<style>
:root {{
  --bg:      #111210;
  --surface: #1a1b18;
  --border:  #2e3028;
  --text:    #f0ede6;
  --muted:   #c9c4b8;
  --dim:     #8a8577;
  --accent:  #f0b429;
  --info:    #60a5fa;
  --success: #34d399;
  --error:   #f87171;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', system-ui, sans-serif;
  line-height: 1.65;
  font-size: 16px;
}}
.tabbar {{
  position: sticky; top: 0; z-index: 100;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  padding: 0.35rem 0.75rem 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  overflow-x: auto;
}}
.tabbar-title {{
  align-self: center;
  margin-right: 1rem;
  color: var(--accent);
  font-weight: 700;
  text-transform: uppercase;
  padding: 0.45rem 0.25rem;
  white-space: nowrap;
}}
.tab {{
  background: transparent;
  border: 1px solid transparent;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  color: var(--dim);
  padding: 0.5rem 0.85rem;
  cursor: pointer;
  font-family: inherit;
  font-size: inherit;
  letter-spacing: inherit;
  white-space: nowrap;
  margin-bottom: -1px;
  transition: color 0.15s, background 0.15s;
}}
.tab:hover {{ color: var(--text); background: rgba(240,180,41,0.06); }}
.tab.active {{
  color: var(--accent);
  background: var(--bg);
  border-color: var(--border);
  border-bottom-color: var(--bg);
}}
main {{
  max-width: 920px;
  margin: 0 auto;
  padding: 2.5rem 1.75rem 5rem;
}}
.doc {{ display: none; }}
.doc.active {{ display: block; animation: fade 0.2s ease-out; }}
@keyframes fade {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
h1, h2, h3, h4 {{
  color: var(--text);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
}}
h1 {{
  font-size: 2.1rem;
  font-weight: 900;
  letter-spacing: -0.035em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.5rem;
  margin: 0 0 1.25rem;
}}
h2 {{
  font-size: 1.5rem;
  margin: 2.75rem 0 1rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
  color: var(--accent);
}}
h3 {{ font-size: 1.15rem; margin: 2rem 0 0.75rem; }}
h4 {{ font-size: 1rem; margin: 1.5rem 0 0.5rem; color: var(--muted); }}
p {{ color: var(--text); margin: 0 0 1rem; }}
p em, li em {{ color: var(--muted); font-style: italic; }}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
ul, ol {{ padding-left: 1.5rem; margin: 0 0 1rem; }}
li {{ margin-bottom: 0.3rem; }}
code {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.88em;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 0.1em 0.35em;
  color: var(--text);
}}
pre {{
  background: #0c0d0b;
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 1rem 1.25rem;
  overflow-x: auto;
  margin: 0 0 1.25rem;
  line-height: 1.5;
}}
pre code {{ background: transparent; border: none; padding: 0; font-size: 0.82rem; color: var(--text); }}
blockquote {{
  border-left: 3px solid var(--accent);
  background: var(--surface);
  margin: 1.25rem 0;
  padding: 0.875rem 1.25rem;
  color: var(--muted);
  font-style: italic;
  border-radius: 0 6px 6px 0;
}}
blockquote strong {{ color: var(--accent); font-style: normal; }}
blockquote p:last-child {{ margin-bottom: 0; }}
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 1.5rem;
  font-size: 0.88rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}}
thead th {{
  background: var(--surface);
  color: var(--dim);
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.7rem;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid var(--border);
}}
tbody td {{
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  vertical-align: top;
}}
tbody tr:last-child td {{ border-bottom: none; }}
tbody tr:hover td {{ background: var(--surface); }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 2.25rem 0; }}
.mermaid {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem;
  margin: 1.25rem 0;
  text-align: center;
}}
.task-list-item {{ list-style: none; margin-left: -1.25rem; }}
.task-list-item input[type="checkbox"] {{ margin-right: 0.5rem; accent-color: var(--accent); }}
ol > li > a, ul > li > a {{ color: var(--accent); }}
</style>
</head>
<body>
<nav class="tabbar">
  <span class="tabbar-title">{title}</span>
  {tabs}
</nav>
<main>
{docs}
</main>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'base',
    themeVariables: {{
      darkMode: true,
      background: '#1a1b18',
      primaryColor: '#1a1b18',
      primaryTextColor: '#f0ede6',
      primaryBorderColor: '#f0b429',
      lineColor: '#f0b429',
      secondaryColor: '#2e3028',
      tertiaryColor: '#111210',
      mainBkg: '#1a1b18',
      nodeBorder: '#f0b429',
      clusterBkg: '#111210',
      clusterBorder: '#2e3028',
      edgeLabelBackground: '#1a1b18',
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize: '14px'
    }}
  }});

  const tabs = Array.from(document.querySelectorAll('.tab'));
  const docs = Array.from(document.querySelectorAll('.doc'));
  function activate(id) {{
    tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === id));
    docs.forEach(d => d.classList.toggle('active', d.id === id));
    window.scrollTo({{ top: 0, behavior: 'instant' }});
  }}
  tabs.forEach(t => t.addEventListener('click', () => {{
    history.replaceState(null, '', '#' + t.dataset.tab);
    activate(t.dataset.tab);
  }}));
  const initial = location.hash.slice(1);
  activate(initial && document.getElementById(initial) ? initial : tabs[0].dataset.tab);

  // Rewrite in-doc links to sibling .md files into tab switches
  document.querySelectorAll('main a[href$=".md"]').forEach(a => {{
    const href = a.getAttribute('href');
    const base = href.split('/').pop().replace(/\.md$/, '');
    const tabId = 'doc-' + base;
    if (document.getElementById(tabId)) {{
      a.addEventListener('click', (e) => {{
        e.preventDefault();
        history.replaceState(null, '', '#' + tabId);
        activate(tabId);
      }});
    }}
  }});
</script>
</body>
</html>
"""


def mermaid_fence(source, language, css_class, options, md, **kwargs):
    return f'<div class="mermaid">{source}</div>'


def render_body(src_text: str) -> str:
    md = markdown.Markdown(
        extensions=[
            "extra",
            "codehilite",
            "toc",
            "sane_lists",
            "pymdownx.tasklist",
            "pymdownx.superfences",
        ],
        extension_configs={
            "pymdownx.superfences": {
                "custom_fences": [
                    {"name": "mermaid", "class": "mermaid", "format": mermaid_fence}
                ]
            },
            "pymdownx.tasklist": {"custom_checkbox": True},
        },
    )
    return md.convert(src_text)


def tab_label(p: Path) -> str:
    stem = p.stem
    if stem.upper() == "README":
        return "Overview"
    # Numeric prefix: "07-priority-sequencing" → "07 · Priority sequencing"
    parts = stem.split("-", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return f"{parts[0]} · {parts[1].replace('-', ' ').capitalize()}"
    return stem.replace("-", " ").capitalize()


def sort_key(p: Path):
    stem = p.stem
    if stem.upper() == "README":
        return (0, "")
    parts = stem.split("-", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return (1, int(parts[0]))
    # Group: action-plan / reviews / validations / others
    if stem.startswith("action"):
        return (2, stem)
    if stem.endswith("-review"):
        return (3, stem)
    if stem.startswith("validation"):
        return (4, stem)
    return (5, stem)


def build(files: list[Path], title: str) -> str:
    files = sorted(files, key=sort_key)
    tabs_html = []
    docs_html = []
    for p in files:
        doc_id = "doc-" + p.stem
        label = tab_label(p)
        tabs_html.append(f'<button class="tab" data-tab="{doc_id}">{label}</button>')
        body = render_body(p.read_text(encoding="utf-8"))
        docs_html.append(f'<section class="doc" id="{doc_id}" data-src="{p.name}">\n{body}\n</section>')
    return SHELL.format(title=title, tabs="\n  ".join(tabs_html), docs="\n".join(docs_html))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("-t", "--title", default="Docs")
    args = ap.parse_args()

    files: list[Path] = []
    for inp in args.inputs:
        p = inp.resolve()
        if p.is_dir():
            files.extend(sorted(p.glob("*.md")))
        elif p.suffix == ".md":
            files.append(p)
        else:
            print(f"skip (not .md or dir): {p}", file=sys.stderr)
    if not files:
        print("error: no markdown files found", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    html = build(files, args.title)
    args.output.write_text(html, encoding="utf-8")
    print(f"✓ {len(files)} docs → {args.output} ({len(html):,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
