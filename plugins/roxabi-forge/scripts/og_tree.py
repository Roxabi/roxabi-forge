#!/usr/bin/env python3
"""Render catalogue OG previews into the SSOT, beside each page.

The deploy snapshot stays read-only: the share bar is injected into the copy
under the engine clone and must never land in the tree two machines sync.
A preview is the opposite kind of file. It is content, shared like the rest
of the tree, and tree_snapshot.thumb_for() looks for `<page>.og.png` next to
the page — that is where the existing cards already sit. Rendering anywhere
else would make the catalogue blind to the image this step just produced.

A missing card degrades one page. It must not fail the publish, so a renderer
that is absent, a network error, or a single-page crash is counted and the
batch continues. Exit 2 is reserved for a missing source or an unknown
renderer: those are operator errors, not a degraded card.

Idempotence keeps any newer `.og.png`. That is only safe if a crash cannot
leave a truncated file under that exact name, which a later run would then
treat as valid forever. Bytes are written to a dotfile sibling and renamed
into place; iter_files skips dotfiles, so a kill -9 leftover is also invisible
to the next catalogue.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_HERE / "lib") not in sys.path:
    sys.path.insert(0, str(_HERE / "lib"))

import tree_snapshot  # noqa: E402

RENDERERS = ("browser-run", "playwright", "off")

# Historical local capture (the pre-engine gen-og-images.py). A 1200×630
# viewport at 2× is the 2400×1260 card already sitting next to pages in the
# tree. networkidle plus a short settle is what made those cards stable;
# full_page would include the scrolled rest of the document and no longer
# match the OG frame. Browser Run is a different engine (og_render owns its
# viewport and returns a JPEG); this script only converts that JPEG to PNG
# so the filename contract stays one suffix.
PLAYWRIGHT_VIEWPORT = {"width": 1200, "height": 630}
PLAYWRIGHT_SCALE = 2
PLAYWRIGHT_WAIT = "networkidle"
PLAYWRIGHT_SETTLE_MS = 400
PLAYWRIGHT_TIMEOUT_MS = 30_000

# Entrance animations capture as blank if we shoot the first frame. The
# historical renderer forced them visible and waited out the font swap;
# dropping either regresses cards that already exist in the tree.
_FONTS_JS = "document.fonts ? document.fonts.ready.then(() => true) : true"
_REVEAL_JS = """() => {
  document.querySelectorAll('.reveal,[data-reveal]').forEach(el => {
    el.classList.add('revealed','in-view','visible','is-visible');
    el.style.opacity = '1';
    el.style.transform = 'none';
  });
}"""

_SECRET = re.compile(r"(?i)bearer\s+\S|api[_-]?token\s*[=:]\s*\S")
_SEQ = 0

RenderFn = Callable[[Path, Path], None]


def _next_seq() -> int:
    global _SEQ
    _SEQ += 1
    return _SEQ


def _safe(exc: BaseException) -> str:
    """One log line, never a credential. Browser Run errors name the missing
    key; they must not grow into a dump of the request that carried the token."""
    text = " ".join(str(exc).split())
    if not text or _SECRET.search(text):
        return exc.__class__.__name__
    if len(text) > 180:
        return text[:180] + "..."
    return text


def _summary(rendered: int, up_to_date: int, failed: int, skipped: int) -> str:
    return (
        f"og: {rendered} rendered, {up_to_date} up-to-date, "
        f"{failed} failed, {skipped} skipped"
    )


def _emit(rendered: int, up_to_date: int, failed: int, skipped: int, note: str = "") -> None:
    # The counts line is last on purpose: publish.sh relays the final og: line.
    if note:
        print(note, file=sys.stderr)
    print(_summary(rendered, up_to_date, failed, skipped), file=sys.stderr)


def og_png_for(page: Path) -> Path:
    """`a/b/page.html` → `a/b/page.og.png`, the name thumb_for() probes first."""
    return page.with_name(page.stem + ".og.png")


def _fresh(dest: Path, page: Path) -> bool:
    """True when dest is a non-empty file at least as new as the page.

    A zero-byte file is not a card: keeping it would freeze the broken state
    the atomic write exists to prevent, if an older pipeline left one behind.
    """
    try:
        st = dest.stat()
    except OSError:
        return False
    if not st.st_size:
        return False
    try:
        return st.st_mtime >= page.stat().st_mtime
    except OSError:
        return False


def _only_rel(source: Path, only: str) -> str | None:
    """Relative path inside source, or None when --only would escape it.

    Exit 2 is reserved for a missing root and an unknown renderer. An escaping
    --only is refused by selecting nothing: writing outside the SSOT is the
    failure, and a quiet no-op is safer than a second exit code.
    """
    rel = only.strip().replace("\\", "/").lstrip("/")
    if not rel or "\x00" in only:
        return None
    try:
        return (source / rel).resolve().relative_to(source).as_posix()
    except (OSError, ValueError):
        return None


def select_pages(source: Path, only: str | None = None) -> list[Path]:
    """Documents the snapshot catalogues: HTML iter_files kept, fragments out.

    dropped() is applied inside iter_files. A fragment is HTML with no opening
    <html> tag — a tab body, not a page — and fragments() is the same predicate
    the catalogue uses, including "a read error is not a fragment". The memo on
    that function is for one snapshot build; a second publish in this process
    must not reuse a classification of a tree that has since changed.
    """
    tree_snapshot._FRAGMENTS.pop(source, None)
    frags = tree_snapshot.fragments(source)
    wanted = _only_rel(source, only) if only else None
    if only and wanted is None:
        print("og: --only escapes the source, ignored", file=sys.stderr)
        return []
    pages: list[Path] = []
    for path in tree_snapshot.iter_files(source):
        rel = tree_snapshot._rel(source, path)
        if not rel.endswith(".html") or rel in frags:
            continue
        if wanted is not None and rel != wanted:
            continue
        pages.append(path)
    pages.sort(key=lambda p: tree_snapshot._rel(source, p))
    return pages


def publish_png(dest: Path, produce: RenderFn, page: Path) -> None:
    """Let produce write a sibling temp, then rename it onto dest.

    produce receives the temp path and must not touch dest. A raise — including
    one after a partial temp write — deletes the temp and leaves dest alone, so
    a previous good card survives and a missing one is not invented as a stub.
    """
    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.{_next_seq()}.tmp")
    try:
        produce(page, tmp)
        if not tmp.is_file() or tmp.stat().st_size <= 0:
            raise RuntimeError("renderer produced no preview")
        # fsync before the rename: replace publishes the inode. Without it a
        # crash can recover a directory entry whose bytes never hit disk, and
        # idempotence would then keep that empty card.
        with tmp.open("rb+") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, dest)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _import_playwright():
    from playwright.sync_api import sync_playwright

    return sync_playwright


def _jpeg_bytes_to_png(data: bytes) -> bytes:
    """og_render.render() returns a JPEG. The tree's card name is .og.png.

    Browsers that trust the extension reject a JPEG wearing that suffix, and
    the cards already in the tree are PNGs. Conversion stays here so og_render
    is called, not reimplemented.
    """
    import io

    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required to store a Browser Run JPEG as PNG") from exc
    with Image.open(io.BytesIO(data)) as im:
        buf = io.BytesIO()
        im.save(buf, format="PNG")
    return buf.getvalue()


def _browser_run_render(page: Path, tmp: Path) -> None:
    import og_render

    tmp.write_bytes(_jpeg_bytes_to_png(og_render.render(page)))


class _PlaywrightSession:
    def __init__(self, pw: object, browser: object, page: object) -> None:
        self._pw = pw
        self._browser = browser
        self._page = page

    def render(self, page: Path, tmp: Path) -> None:
        url = page.resolve().as_uri()
        # Diagram pages capture the hero frame, not the editor chrome. The
        # historical renderer appended this; without it those cards change
        # shape the day they are re-rendered.
        if "/references/diagrams/" in f"/{page.as_posix()}":
            url += "?embed=hero"
        shot = self._page
        shot.goto(url, wait_until=PLAYWRIGHT_WAIT, timeout=PLAYWRIGHT_TIMEOUT_MS)  # type: ignore[attr-defined]
        shot.evaluate(_FONTS_JS)  # type: ignore[attr-defined]
        shot.evaluate(_REVEAL_JS)  # type: ignore[attr-defined]
        shot.wait_for_timeout(PLAYWRIGHT_SETTLE_MS)  # type: ignore[attr-defined]
        shot.screenshot(path=str(tmp), full_page=False, type="png")  # type: ignore[attr-defined]

    def close(self) -> None:
        browser, pw = self._browser, self._pw
        self._browser = None
        self._pw = None
        self._page = None
        for closer, method in ((browser, "close"), (pw, "stop")):
            if closer is None:
                continue
            try:
                getattr(closer, method)()
            except Exception:
                pass


def _open_playwright() -> tuple[_PlaywrightSession | None, str]:
    pw = None
    browser = None
    try:
        sync_playwright = _import_playwright()
        pw = sync_playwright().start()
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport=PLAYWRIGHT_VIEWPORT,
            device_scale_factor=PLAYWRIGHT_SCALE,
        )
        page = context.new_page()
        page.set_default_timeout(PLAYWRIGHT_TIMEOUT_MS)
        return _PlaywrightSession(pw, browser, page), ""
    except Exception as exc:
        for closer, method in ((browser, "close"), (pw, "stop")):
            if closer is None:
                continue
            try:
                getattr(closer, method)()
            except Exception:
                pass
        return None, f"og: playwright unavailable ({_safe(exc)}) — previews skipped"


def _split(pages: list[Path], force: bool) -> tuple[list[Path], int]:
    pending: list[Path] = []
    fresh = 0
    for page in pages:
        dest = og_png_for(page)
        if not force and _fresh(dest, page):
            fresh += 1
        else:
            pending.append(page)
    return pending, fresh


def run(
    source: Path | str,
    *,
    renderer: str = "browser-run",
    force: bool = False,
    only: str | None = None,
    dry_run: bool = False,
    render: RenderFn | None = None,
) -> int:
    """Render catalogued pages. Returns 0 on a finished batch, 2 on a bad invocation.

    `render`, when passed, replaces the backend. Tests inject it so the suite
    never opens a browser or a socket. `off` ignores it: off means off.
    """
    root = Path(source).expanduser()
    if not root.is_dir():
        print(f"og: source not found: {root}", file=sys.stderr)
        return 2
    root = root.resolve()
    kind = (renderer or "").strip()
    if kind not in RENDERERS:
        print(f"og: unknown renderer: {renderer}", file=sys.stderr)
        return 2

    pages = select_pages(root, only)
    if kind == "off":
        note = "og: dry-run, renderer off, nothing written" if dry_run else ""
        _emit(0, 0, 0, len(pages), note)
        return 0

    pending, fresh = _split(pages, force)
    if dry_run:
        # Classify only. A dry run that launched Chromium or Browser Run would
        # write nothing and still bill a render, and the SSOT must not move.
        _emit(0, fresh, 0, len(pending), f"og: dry-run, would render {len(pending)}")
        return 0

    session: _PlaywrightSession | None = None
    note = ""
    backend = render
    if backend is None and kind == "playwright":
        session, note = _open_playwright()
        if session is None:
            _emit(0, fresh, 0, len(pending), note)
            return 0
        backend = session.render
    elif backend is None:
        backend = _browser_run_render

    rendered = 0
    failed = 0
    try:
        for page in pending:
            rel = tree_snapshot._rel(root, page)
            try:
                publish_png(og_png_for(page), backend, page)
                rendered += 1
            except Exception as exc:
                # One card. The next page still gets its turn, and the publish
                # that called us treats a non-zero here as a warning anyway.
                failed += 1
                print(f"og fail {rel}: {_safe(exc)}", file=sys.stderr)
    finally:
        if session is not None:
            session.close()
    _emit(rendered, fresh, failed, 0)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="og_tree.py",
        description="Render catalogue OG previews into the SSOT, beside each page.",
    )
    parser.add_argument("--source", required=True, help="SSOT root (the data tree)")
    parser.add_argument(
        "--renderer",
        default=os.environ.get("FORGE_OG_RENDERER", "browser-run"),
        choices=RENDERERS,
        help="browser-run (Cloudflare, via og_render), playwright (local), or off",
    )
    parser.add_argument("--force", action="store_true", help="re-render even when the PNG is newer")
    parser.add_argument("--only", default=None, help="one page, relative to --source")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="classify what would render; write nothing",
    )
    args = parser.parse_args(argv)
    return run(
        args.source,
        renderer=args.renderer,
        force=args.force,
        only=args.only,
        dry_run=args.dry_run,
    )


def _reexec_under_uv(argv: list[str]) -> int | None:
    """Re-run this script inside `uv run --with playwright`, once.

    The operator toolchain keeps Playwright out of the system interpreter --
    the historical pipeline always invoked it as `uv run --with playwright`.
    Without this, `--renderer playwright` degrades to "unavailable" on a
    machine that can in fact render, and the catalogue silently keeps its
    holes. The guard variable stops the child from recursing.
    """
    if os.environ.get("FORGE_OG_NO_UV"):
        return None
    uv = shutil.which("uv")
    if not uv:
        return None
    try:
        _import_playwright()
        return None  # already importable, nothing to delegate
    except Exception:
        pass
    env = dict(os.environ, FORGE_OG_NO_UV="1")
    cmd = [uv, "run", "--with", "playwright", "python3", str(Path(__file__).resolve()), *argv]
    print("og: playwright via uv", file=sys.stderr)
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    _argv = sys.argv[1:]
    if "playwright" in (os.environ.get("FORGE_OG_RENDERER", ""), *_argv):
        _rc = _reexec_under_uv(_argv)
        if _rc is not None:
            raise SystemExit(_rc)
    raise SystemExit(main())
