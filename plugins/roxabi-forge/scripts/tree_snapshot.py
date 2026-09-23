#!/usr/bin/env python3
"""Copy a project tree into a deploy snapshot. The share bar never touches the SSOT.

Page identity is the relative HTML path (`lyra/visuals/architecture.html`), so the
snapshot is a mirror of the data tree, not a slug directory. Two rules make the
publish safe to repeat:

  * the share bar is injected into the DEST copy only — the SSOT keeps its bytes,
    which is what lets Syncthing carry the tree between machines without conflicts;
  * the engine owns the site shell (catalogue, 404, login, brand). Those names are
    skipped at the tree root, so an old landing page sitting in the data tree can
    never overwrite the generated catalogue.

`manifest.json` is written for the worker only (the edge blocks it from clients)
and carries what the catalogue renders: title, date, size, colour, category and
whether a preview image sits next to the page. A fragment — HTML with no opening
`<html` tag, a tab body loaded by `data-src` or by a runtime-built fetch() URL —
is not a page: it is left out of the catalogue and out of the share bar, and
recorded as an asset of the page that loads it. A real page linked by href
keeps its own ACL and must never become an asset key, or a public page would
open a private one.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {".git", "_dist", ".wrangler", "_test-forge", "__pycache__", ".stversions"}
CORE = {
    "_shared/hero-base.css",
    "_shared/hero-base.js",
    "_shared/gallery-base.css",
    "_shared/gallery-base.js",
    "_shared/fgraph-base.css",
    "_shared/explainer-base.css",
}
# Engine-owned names at the tree root. The data tree may still hold its own
# legacy copies; the snapshot keeps the engine's.
ENGINE_SHELL = {
    "index.html",
    "404.html",
    "login.html",
    "robots.txt",
    "manifest.json",
    "_headers",
    "_redirects",
    "favicon.svg",
    "favicon-32.png",
    "favicon.ico",
    "apple-touch-icon.png",
}
# Operator scaffolding that is not an artifact.
ROOT_SKIP_PREFIXES = ("Makefile",)
# The data tree is a working directory, not a web root: it holds the sources a
# page was built from (prompts, training sets, model weights, raw renders) next
# to the page itself. Those never belonged on Pages, and the previous build
# excluded exactly these — the rules are carried over rather than reinvented.
SOURCE_DIR_PREFIXES = (
    "lyra/brand/prompts/",
    "lyra/avatar/prompts/",
    "lyra/avatar/embeddings",
    "lyra/avatar/lora-training-set/",
    "lyra/avatar/generated/",
    "lyra/avatar/workflows/",
    "lyra/avatar/scripts/",
)
SOURCE_SUFFIXES = (".py", ".safetensors", ".pt", ".npz", ".mp4")
# Cloudflare Pages refuses a file over 25 MiB. Skipping it here keeps the
# deploy honest: the builder reports what it left behind instead of letting
# the upload fail halfway.
MAX_FILE_BYTES = 25 * 1024 * 1024
# Files the size cap left behind on the last iter_files() pass, so the CLI can
# name them instead of letting them vanish silently.
OVERSIZE: list[str] = []
# Pages whose body is a "Removed" notice — kept in the data tree as a trace,
# never catalogued or deployed.
TOMBSTONES = {"metalyde/visuals/roadmap-performance-blocks.html"}
PALETTE = ("amber", "blue", "green", "purple", "orange", "cyan", "red", "gold")
THUMB_SUFFIXES = (".og.jpg", ".og.png")
# Catalogue cards are ~300 px wide; 600 covers a 2× screen.
THUMB_WIDTH = 600
THUMB_QUALITY = 74
THUMB_EXT = ".thumb.webp"
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
# Opening <html> is the whole discriminant between a page and a fragment.
# A fragment is a tab body; a page keeps its own ACL. The character class
# rejects a stray "html" token that is not a tag.
_HTML_DOC = re.compile(r"<html[\s>]", re.IGNORECASE)
# One classification per root. build_manifest and build_asset_owners both
# ask, and main() asks again to report the split — re-reading every HTML
# file each time is the cost this avoids. The tree is stable for that publish.
_FRAGMENTS: dict[Path, set[str]] = {}


# href="…", src="…" and css url(…) — the shapes a page uses to pull a file the
# edge then has to serve.
_REF = re.compile(
    r"""(?:href|src|data-src)\s*=\s*["']([^"']+)["']|url\(\s*["']?([^"')]+)["']?\s*\)""",
    re.IGNORECASE,
)
# <script src="…">: only same-origin scripts are read for tab loaders.
_SCRIPT_SRC = re.compile(r"""<script\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
# Tab loaders rarely spell the tab path in an attribute: they carry it in a JS
# string, or build it at runtime -- fetch('tabs/p/tab-' + id + '.html'),
# 'tabs/' + NAME + '/tab-' + id + '.html', `${guideBase()}tabs/${slug}/tab-${id}.html`
# -- often in a helper that is not the fetch() call itself. Only strings ending
# in `.html` are read: a tab is an HTML file, and the suffix keeps the scan off
# the rest of the script.
#
# A whole quoted `.html` string. Not one glued to a `+`: that is a piece of a
# concatenation, whose meaning depends on what it is glued to.
_HTML_LITERAL = re.compile(
    r"""(?<!\+)(?<!\+ )(["'`])([^"'`\s<>${}]+\.html)(?:[?#][^"'`\s<>]*)?\1"""
)
_JS_STR = r"""(?:"[^"\n]*"|'[^'\n]*')"""
# A plain operand: name, member access, call or index -- guideBase(), ids[i].
_JS_EXPR = r"""[\w$.]+(?:\([^()"'`\n]*\)|\[[^\]"'`\n]*\])*"""
_CONCAT_HTML = re.compile(
    rf"""(?:(?:{_JS_STR}|{_JS_EXPR})\s*\+\s*)+(?:"[^"\n]*\.html"|'[^'\n]*\.html')"""
)
_CONCAT_TOKEN = re.compile(rf""""([^"\n]*)"|'([^'\n]*)'|{_JS_EXPR}""")
_TEMPLATE_HTML = re.compile(r"`([^`\n]*\$\{[^`\n]*\.html)`")
_PLACEHOLDER = re.compile(r"\$\{[^}]*\}")
MAX_OWNERS = 4


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def dropped(rel: str) -> bool:
    if rel in CORE:
        return False
    # Tombstones: pages kept in the tree only to say the artefact is gone.
    # They carry no content and have no place in the catalogue.
    if rel in TOMBSTONES:
        return True
    if rel == "reference-gallery.html":
        return True
    parts = rel.split("/")
    if parts[0] == "references" and "examples" in parts:
        return True
    if rel == "references/showcases" or rel.startswith("references/showcases/"):
        return True
    if rel.startswith("_shared/") and rel.endswith(".html"):
        return True
    if rel.startswith("_shared/diagrams/") or rel.startswith("_shared/guides/"):
        return True
    if rel.startswith(SOURCE_DIR_PREFIXES):
        return True
    if rel.endswith(SOURCE_SUFFIXES):
        return True
    if "/graph-templates/" in f"/{rel}" and (rel.endswith(".html") or rel.endswith(".og.png")):
        return True
    if "/" not in rel:
        if rel in ENGINE_SHELL:
            return True
        if rel.startswith(ROOT_SKIP_PREFIXES):
            return True
    return False


def _inject():
    script = Path(__file__).resolve().parent / "inject-share-bar.py"
    spec = importlib.util.spec_from_file_location("inject_share_bar", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("inject-share-bar.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.inject


def iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    OVERSIZE.clear()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".") and not dropped(_rel(root, Path(dirpath) / d))
        ]
        for name in filenames:
            if name.startswith(".") or name in {".env"} or name.startswith(".env."):
                continue
            path = Path(dirpath) / name
            rel = _rel(root, path)
            if dropped(rel) or rel.startswith("_dist/") or rel.startswith(".wrangler/"):
                continue
            # os.walk lists a dangling symlink as a file. is_file() follows the
            # link, so a broken one is skipped and a live one is materialised by
            # the copy — a deploy snapshot has no use for the link itself.
            if not path.is_file():
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    OVERSIZE.append(rel)
                    continue
            except OSError:
                continue
            out.append(path)
    return out


def page_digests(root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in iter_files(root):
        rel = _rel(root, path)
        if not rel.endswith(".html"):
            continue
        digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def title_of(path: Path, rel: str) -> str:
    """<title> of the page, else the file stem turned into words."""
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:8192]
    except OSError:
        head = ""
    m = _TITLE.search(head)
    if m:
        text = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
        if text:
            return text
    stem = Path(rel).stem
    return stem.replace("-", " ").replace("_", " ").strip() or rel


def colour_of(project: str) -> str:
    digest = hashlib.sha1(project.encode("utf-8")).hexdigest()
    return PALETTE[int(digest[:8], 16) % len(PALETTE)]



def make_thumb(source_img: Path, dest_img: Path) -> bool:
    """Downscale a preview to card size. True when dest_img now exists.

    The OG images are 2400×1260 — right for a social card, eight times more
    pixels than the ~300 px catalogue card needs, and 114 MB across the tree.
    The catalogue loads the small one; the full-size OG stays deployed for
    social unfurls. Written into the snapshot only, never back to the SSOT.
    """
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        if dest_img.is_file() and dest_img.stat().st_mtime >= source_img.stat().st_mtime:
            return True
        with Image.open(source_img) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_WIDTH, THUMB_WIDTH), Image.LANCZOS)
            dest_img.parent.mkdir(parents=True, exist_ok=True)
            im.save(dest_img, "WEBP", quality=THUMB_QUALITY, method=4)
        return True
    except Exception:
        # A preview that will not resize must not fail the publish: the card
        # falls back to the full-size image.
        return False


def thumb_for(root: Path, rel: str) -> str:
    """Relative preview image sitting next to the page, or empty."""
    base = rel[:-5] if rel.endswith(".html") else rel
    for suffix in THUMB_SUFFIXES:
        if (root / f"{base}{suffix}").is_file():
            return f"/{base}{suffix}"
    return ""


def manifest_entry(root: Path, path: Path, rel: str, dest: Path | None = None) -> dict[str, object]:
    stat = path.stat()
    project = rel.split("/")[0] if "/" in rel else "racine"
    thumb = thumb_for(root, rel)
    card = thumb
    if thumb and dest is not None:
        small = f"{rel[:-5]}{THUMB_EXT}" if rel.endswith(".html") else f"{rel}{THUMB_EXT}"
        if make_thumb(root / thumb.lstrip("/"), dest / small):
            card = f"/{small}"
    entry: dict[str, object] = {
        "f": rel,
        "t": title_of(path, rel),
        "d": datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d"),
        "kb": max(1, round(stat.st_size / 1024)),
        "cat": project,
        "cl": project,
        "c": colour_of(project),
        "b": [],
        "p": bool(thumb),
    }
    if thumb:
        entry["thumb"] = card
    return entry


def is_fragment(text: str) -> bool:
    """True when text has no opening <html> tag, so it is not a document."""
    return _HTML_DOC.search(text) is None


def fragments(root: Path) -> set[str]:
    """Relative paths of HTML files that are fragments, not pages.

    Memoised on root. A read error is not a fragment: the file stays a page,
    so it stays private by default instead of being opened as a sub-resource.
    """
    cached = _FRAGMENTS.get(root)
    if cached is not None:
        return cached
    found: set[str] = set()
    for path in iter_files(root):
        rel = _rel(root, path)
        if not rel.endswith(".html"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if is_fragment(text):
            found.add(rel)
    _FRAGMENTS[root] = found
    return found


def build_manifest(root: Path, dest: Path | None = None) -> list[dict[str, object]]:
    entries = []
    # A fragment is a tab body, not a catalogue card. Listing it produces a
    # card with no preview and an ACL that fights the page that loads it.
    frags = fragments(root)
    for path in iter_files(root):
        rel = _rel(root, path)
        if rel.endswith(".html") and rel not in frags:
            entries.append(manifest_entry(root, path, rel, dest))
    entries.sort(key=lambda e: str(e["f"]))
    return entries


def _normalise(target: str) -> str:
    """Collapse `.`/`..`/empty segments. `..` stops at the root, never above it."""
    parts: list[str] = []
    for seg in target.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        parts.append(seg)
    return "/".join(parts)


def _base(rel: str) -> str:
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def _local_ref(ref: str, base: str) -> str:
    """Tree-relative path of a same-origin reference, or "" when it is not ours.

    External, protocol-relative and data URLs are not ours to serve.
    """
    ref = ref.strip()
    if not ref or ref.startswith(("#", "data:", "mailto:", "//")):
        return ""
    if "://" in ref:
        return ""
    ref = ref.split("#", 1)[0].split("?", 1)[0]
    if not ref or ref.endswith("/"):
        return ""
    target = ref[1:] if ref.startswith("/") else (f"{base}/{ref}" if base else ref)
    return _normalise(target)


def page_assets(html: str, rel: str) -> set[str]:
    """Local files this page loads, as tree-relative paths.

    HTML references are included. Sorting one into "page" (keeps its ACL) or
    "fragment" (no ACL of its own) belongs to build_asset_owners: doing it
    here would drop fragments and, worse, invite treating every linked page
    as an asset.
    """
    base = _base(rel)
    out: set[str] = set()
    for attr_ref, css_ref in _REF.findall(html):
        target = _local_ref(attr_ref or css_ref, base)
        if target:
            out.add(target)
    return out


def _canonical(literals: list[str]) -> tuple[str, ...]:
    """Literal parts with one variable part between each pair.

    Adjacent variable parts collapse into one (an empty literal between them
    carries nothing). Only the first literal may be empty: that marks a URL
    that starts with a variable part.
    """
    return (literals[0], *(lit for lit in literals[1:] if lit))


def _concat_literals(chain: str) -> list[str]:
    literals = [""]
    after_var = False
    for tok in _CONCAT_TOKEN.finditer(chain):
        text = tok.group(1) if tok.group(1) is not None else tok.group(2)
        if text is None:
            after_var = True
        elif after_var:
            literals.append(text)
            after_var = False
        else:
            literals[-1] += text
    return literals


def url_templates(text: str) -> set[tuple[str, ...]]:
    """Every `.html` URL spelled or built in text, as its literal parts.

    A one-part tuple is a literal path; k+1 parts carry k variable parts, one
    between each pair. Raw, unresolved strings: resolution depends on the
    document that runs the script, not on the file the script lives in.
    """
    found: set[tuple[str, ...]] = {(m.group(2),) for m in _HTML_LITERAL.finditer(text)}
    for m in _TEMPLATE_HTML.finditer(text):
        found.add(_canonical(_PLACEHOLDER.split(m.group(1))))
    for m in _CONCAT_HTML.finditer(text):
        found.add(_canonical(_concat_literals(m.group(0))))
    return found


def _resolve_prefix(prefix: str, base: str) -> str | None:
    """Tree-relative form of a URL prefix, keeping its trailing partial segment.

    `tabs/p/tab-` from a page in `lyra/` gives `lyra/tabs/p/tab-`. None when
    the prefix points off-site.
    """
    if prefix.startswith(("//", "data:")) or "://" in prefix:
        return None
    head, _, tail = prefix.rpartition("/")
    if prefix.startswith("/"):
        directory = _normalise(head)
    else:
        directory = _normalise(f"{base}/{head}" if base else head)
    return f"{directory}/{tail}" if directory else tail


def _foreign_tab(frag: str, rel: str, pages: set[str]) -> bool:
    """True when frag sits in `tabs/<S>/` next to a DIFFERENT page `<S>.html`.

    Pages of one directory often share a loader that takes the page name as a
    variable ('tabs/' + NAME + '/tab-' + id). The pattern then reaches the
    sibling's tabs too; owning them would open a private page's tabs from a
    public one. The `tabs/<page>/` convention names the real owner.
    """
    base = _base(rel)
    tabs = f"{base}/tabs/" if base else "tabs/"
    if not frag.startswith(tabs):
        return False
    stem, sep, _ = frag[len(tabs) :].partition("/")
    if not sep:
        return False
    sibling = f"{base}/{stem}.html" if base else f"{stem}.html"
    return sibling != rel and sibling in pages


def linked_fragments(
    templates: set[tuple[str, ...]], rel: str, frags: set[str], pages: set[str]
) -> set[str]:
    """Fragments page `rel` can load through the given URL templates.

    fetch() resolves against the document URL, so every template is taken
    from the PAGE's directory even when it sits in a script under `js/`. A
    leading variable part is a base URL picked at runtime (`${guideBase()}`):
    it is dropped and the rest is read as page-relative. Each other variable
    part matches exactly one non-empty segment: a loader aimed at `tabs/v2/`
    must not open `tabs/v1/`. Only fragments are candidates -- a real page
    matching a pattern keeps its own ACL.
    """
    base = _base(rel)
    out: set[str] = set()
    for parts in templates:
        literals = list(parts)
        if len(literals) > 1 and not literals[0]:
            literals = literals[1:]
            literals[0] = literals[0].lstrip("/")
        # `${name}.html` would match every fragment of the page directory.
        if "".join(literals) == ".html":
            continue
        start = _resolve_prefix(literals[0], base)
        if start is None:
            continue
        if len(literals) == 1:
            if start in frags:
                out.add(start)
            continue
        pattern = re.compile(
            re.escape(start) + "".join(f"[^/]+{re.escape(lit)}" for lit in literals[1:])
        )
        out.update(f for f in frags if f.startswith(start) and pattern.fullmatch(f))
    return {frag for frag in out if not _foreign_tab(frag, rel, pages)}


def _script_srcs(root: Path, html: str, rel: str) -> list[str]:
    """Tree-relative paths of the page's same-origin external scripts that exist."""
    base = _base(rel)
    resolved_root = root.resolve()
    found: list[str] = []
    for src in _SCRIPT_SRC.findall(html):
        target = _local_ref(src, base)
        if not target:
            continue
        path = root / target
        # A symlink could point the scan outside the tree; the edge only
        # serves what is inside it.
        try:
            if path.is_file() and path.resolve().is_relative_to(resolved_root):
                found.append(target)
        except OSError:
            continue
    return found


def _own(owners: dict[str, list[str]], asset: str, page: str) -> None:
    bucket = owners.setdefault(asset, [])
    if len(bucket) < MAX_OWNERS and page not in bucket:
        bucket.append(page)


def build_asset_owners(root: Path) -> dict[str, list[str]]:
    """{asset path: pages that load it}. The edge reads it to open a public page's assets.

    Capped at MAX_OWNERS: the edge only needs to find ONE public owner, and an
    uncapped list would put every page of a shared stylesheet in the index.

    Two rules make the `.html` keys total and safe:

      * EVERY fragment is a key, orphans included with an empty owner list.
        Absence is what would send it back down the page path, where a private
        fragment answers 302 /login -- the parent's fetch() follows that and
        the tab renders a login page. An empty list closes it as a resource.
      * A real page is NEVER a key, because an href from a public page would
        otherwise open it and bypass its own ACL. Only a fragment (no opening
        <html>, injected into a parent) is a sub-resource.
    """
    owners: dict[str, list[str]] = {}
    frags = fragments(root)
    refs_by_html: dict[str, set[str]] = {}
    frag_html: dict[str, str] = {}
    html_files = [(path, _rel(root, path)) for path in iter_files(root)]
    html_files = [(path, rel) for path, rel in html_files if rel.endswith(".html")]
    # The sibling pages a shared loader must not steal tabs from (_foreign_tab).
    catalogued = {rel for _, rel in html_files if rel not in frags}
    # Shared loaders (`_shared/*.js`) are included by many pages; read and
    # parse each script once per build rather than once per including page.
    script_templates: dict[str, set[tuple[str, ...]]] = {}

    def templates_of_script(src: str) -> set[tuple[str, ...]]:
        cached = script_templates.get(src)
        if cached is None:
            try:
                text = (root / src).read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            cached = script_templates[src] = url_templates(text)
        return cached

    for path, rel in html_files:
        try:
            html = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        refs = page_assets(html, rel)
        # The catalogue card loads the preview, not the page itself — both the
        # full-size OG (social unfurl) and the generated thumbnail.
        thumb = thumb_for(root, rel)
        if thumb:
            refs.add(thumb.lstrip("/"))
            refs.add(f"{rel[:-5]}{THUMB_EXT}")
        # Tabs named in a JS string or built at runtime have no attribute to
        # follow; without this they stay orphans and 404 on a public page. A
        # fragment does not load tabs of its own (one level), so only pages
        # are scanned.
        if rel in frags:
            # Kept to re-resolve its refs against each parent page (below).
            frag_html[rel] = html
        else:
            templates = url_templates(html)
            for src in _script_srcs(root, html, rel):
                templates |= templates_of_script(src)
            if templates:
                refs |= linked_fragments(templates, rel, frags, catalogued)
        refs_by_html[rel] = refs

    for rel in frags:
        owners.setdefault(rel, [])

    def servable(asset: str) -> bool:
        if asset.endswith(".html") and asset not in frags:
            return False
        if asset in CORE:
            return False
        return (root / asset).is_file() or asset.endswith(THUMB_EXT)

    for rel, refs in refs_by_html.items():
        if rel in frags:
            continue
        for asset in refs:
            if servable(asset):
                _own(owners, asset, rel)

    # A fragment has no visibility record of its own, so what IT loads has to
    # be attributed to the pages that load the fragment -- otherwise an image
    # used only inside a tab stays closed on a public page. One level deep: a
    # tab body is injected into a page, it does not inject another one.
    #
    # Injected through innerHTML, the fragment's relative URLs resolve against
    # the PARENT page's URL, not the fragment's location: that is the base the
    # browser really uses. The fragment-dir reading is kept as well, since some
    # loaders rebase and the file is named by that page's content either way.
    for rel in frags:
        parents = owners.get(rel, [])
        html = frag_html.get(rel)
        if not parents or html is None:
            continue
        own_dir_refs = refs_by_html[rel]
        for page in list(parents):
            for asset in own_dir_refs | page_assets(html, page):
                if asset.endswith(".html") or not servable(asset):
                    continue
                _own(owners, asset, page)

    return {asset: sorted(pages) for asset, pages in sorted(owners.items())}


def build_tree_snapshot(source: Path, dest: Path) -> dict[str, str]:
    """Copy source into dest. Inject the share bar only into dest pages."""
    inject = _inject()
    dest.mkdir(parents=True, exist_ok=True)
    digests = page_digests(source)
    # Thumbnails are written into dest, so the manifest is built against it.
    manifest = build_manifest(source, dest)
    frags = fragments(source)
    for path in iter_files(source):
        rel = _rel(source, path)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        # The bar is a team control of a page. A fragment is fetched and
        # inserted into its parent's DOM, so a bar here would be copied into
        # the parent — once per tab.
        if rel.endswith(".html") and rel not in frags:
            target.write_text(inject(target.read_text(encoding="utf-8"), rel), encoding="utf-8")
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (dest / "asset-owners.json").write_text(
        json.dumps(build_asset_owners(source), ensure_ascii=False) + "\n", encoding="utf-8"
    )

    return digests


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="tree_snapshot.py", description=__doc__)
    ap.add_argument("--source", required=True, help="SSOT data tree (never written)")
    ap.add_argument("--dest", required=True, help="deploy snapshot directory")
    args = ap.parse_args(argv[1:])
    source = Path(args.source).expanduser()
    if not source.is_dir():
        print(f"tree_snapshot: source not a directory: {source}", file=sys.stderr)
        return 1
    dest = Path(args.dest).expanduser()
    digests = build_tree_snapshot(source, dest)
    frags = fragments(source)
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    owners = json.loads((dest / "asset-owners.json").read_text(encoding="utf-8"))
    # Every fragment is a key now, so an orphan is one with an empty owner list.
    orphans = sum(1 for rel in frags if not owners.get(rel))
    print(json.dumps({"ok": True, "count": len(digests), "slugs": digests}, sort_keys=True))
    print(f"snapshot: {len(manifest)} page(s)", file=sys.stderr)
    print(f"snapshot: {len(frags)} fragment(s), {orphans} orphan(s)", file=sys.stderr)
    if OVERSIZE:
        print(
            f"snapshot: {len(OVERSIZE)} file(s) over 25 MiB left behind (Pages limit):",
            file=sys.stderr,
        )
        for rel in OVERSIZE[:10]:
            print(f"  {rel}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
