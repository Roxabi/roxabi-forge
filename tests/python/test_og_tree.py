#!/usr/bin/env python3
"""og_tree.py: catalogue selection, idempotence, and a publish that survives a bad card.

No network and no Chromium. The renderer is injected, because the publish must
keep going when Playwright or Browser Run is absent — a test that needed either
would be testing the machine, not the contract.
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "roxabi-forge" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "lib"))

import og_tree  # noqa: E402

OG = SCRIPTS / "og_tree.py"
PAGE = "<html><head><title>Page</title></head><body>ok</body></html>\n"
FRAGMENT = "<section><h2>tab body</h2></section>\n"
_COUNTS = re.compile(
    r"og: (\d+) rendered, (\d+) up-to-date, (\d+) failed, (\d+) skipped"
)


def _touch(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _counts(err: str) -> tuple[int, int, int, int]:
    matches = _COUNTS.findall(err)
    if not matches:
        raise AssertionError(f"no summary line in stderr:\n{err}")
    return tuple(int(n) for n in matches[-1])  # type: ignore[return-value]


class OgTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        # og_tree resolves the source root; on macOS /var is a symlink to
        # /private/var, so an unresolved temp path would never compare equal.
        self.td = Path(tempfile.mkdtemp(prefix="og-tree-")).resolve()
        self.source = self.td / "ssot"
        self.source.mkdir()

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.td, ignore_errors=True)

    def _run(self, **kwargs: object) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stderr(buf):
            code = og_tree.run(self.source, **kwargs)  # type: ignore[arg-type]
        return code, buf.getvalue()

    def _stamp(self, path: Path, mtime: float) -> None:
        os.utime(path, (mtime, mtime))

    def test_catalogued_page_is_rendered_fragment_and_dropped_are_not(self) -> None:
        page = _touch(self.source, "lyra/visuals/architecture.html", PAGE)
        fragment = _touch(self.source, "lyra/visuals/tabs/body.html", FRAGMENT)
        # Engine shell and a tombstone are HTML documents, and still not cards.
        _touch(self.source, "index.html", PAGE)
        _touch(self.source, "metalyde/visuals/roadmap-performance-blocks.html", PAGE)
        seen: list[str] = []

        def fake(html: Path, tmp: Path) -> None:
            seen.append(html.relative_to(self.source).as_posix())
            tmp.write_bytes(b"png-bytes")

        code, err = self._run(renderer="playwright", render=fake)
        self.assertEqual(code, 0)
        self.assertEqual(seen, ["lyra/visuals/architecture.html"])
        self.assertEqual((self.source / "lyra/visuals/architecture.og.png").read_bytes(), b"png-bytes")
        self.assertFalse(og_tree.og_png_for(fragment).exists())
        self.assertFalse((self.source / "index.og.png").exists())
        self.assertFalse(
            (self.source / "metalyde/visuals/roadmap-performance-blocks.og.png").exists()
        )
        self.assertEqual(_counts(err), (1, 0, 0, 0))
        self.assertEqual(page.read_text(encoding="utf-8"), PAGE)

    def test_newer_preview_is_kept_unless_forced(self) -> None:
        page = _touch(self.source, "lyra/a.html", PAGE)
        png = og_tree.og_png_for(page)
        png.write_bytes(b"KEEP")
        self._stamp(page, 1_000)
        self._stamp(png, 2_000)
        calls: list[str] = []

        def fake(html: Path, tmp: Path) -> None:
            calls.append(html.name)
            tmp.write_bytes(b"NEW")

        code, err = self._run(renderer="browser-run", render=fake)
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertEqual(png.read_bytes(), b"KEEP")
        self.assertEqual(_counts(err), (0, 1, 0, 0))

        code, err = self._run(renderer="browser-run", render=fake, force=True)
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["a.html"])
        self.assertEqual(png.read_bytes(), b"NEW")
        self.assertEqual(_counts(err), (1, 0, 0, 0))

    def test_renderer_off_writes_nothing(self) -> None:
        _touch(self.source, "lyra/a.html", PAGE)
        _touch(self.source, "lyra/tabs/body.html", FRAGMENT)

        def refuse(html: Path, tmp: Path) -> None:
            raise AssertionError(f"off must not render {html}")

        code, err = self._run(renderer="off", render=refuse)
        self.assertEqual(code, 0)
        self.assertEqual(_counts(err), (0, 0, 0, 1))
        self.assertEqual(list(self.source.rglob("*.og.png")), [])

    def test_a_failing_page_does_not_stop_the_batch(self) -> None:
        _touch(self.source, "lyra/bad.html", PAGE)
        _touch(self.source, "lyra/ok.html", PAGE)

        def fake(html: Path, tmp: Path) -> None:
            if html.name == "bad.html":
                raise RuntimeError("browser run unreachable: timed out")
            tmp.write_bytes(b"ok-png")

        code, err = self._run(renderer="browser-run", render=fake)
        self.assertEqual(code, 0)
        self.assertEqual(_counts(err), (1, 0, 1, 0))
        self.assertIn("og fail lyra/bad.html", err)
        self.assertFalse((self.source / "lyra/bad.og.png").exists())
        self.assertEqual((self.source / "lyra/ok.og.png").read_bytes(), b"ok-png")

    def test_a_failed_write_leaves_no_truncated_preview(self) -> None:
        page = _touch(self.source, "lyra/a.html", PAGE)
        dest = og_tree.og_png_for(page)

        def mid_write(html: Path, tmp: Path) -> None:
            self.assertNotEqual(tmp, dest)
            self.assertTrue(tmp.name.startswith("."))
            self.assertFalse(tmp.name.endswith(".og.png"))
            tmp.write_bytes(b"partial-png")
            raise RuntimeError("killed mid-write")

        code, err = self._run(renderer="playwright", render=mid_write)
        self.assertEqual(code, 0)
        self.assertEqual(_counts(err)[2], 1)
        self.assertFalse(dest.exists())
        leftovers = [
            p
            for p in self.source.rglob("*")
            if p.is_file() and (p.suffix == ".tmp" or ".og.png" in p.name)
        ]
        self.assertEqual(leftovers, [])

        dest.write_bytes(b"KEEP")
        self._stamp(page, 2_000)
        self._stamp(dest, 1_000)
        code, _err = self._run(renderer="playwright", render=mid_write)
        self.assertEqual(code, 0)
        self.assertEqual(dest.read_bytes(), b"KEEP")
        leftovers = [p for p in self.source.rglob("*") if p.is_file() and p.suffix == ".tmp"]
        self.assertEqual(leftovers, [])

    def test_dry_run_does_not_call_the_renderer(self) -> None:
        _touch(self.source, "lyra/a.html", PAGE)

        def refuse(html: Path, tmp: Path) -> None:
            raise AssertionError("dry-run must not render")

        code, err = self._run(renderer="browser-run", render=refuse, dry_run=True)
        self.assertEqual(code, 0)
        self.assertIn("would render 1", err)
        self.assertEqual(_counts(err), (0, 0, 0, 1))
        self.assertEqual(list(self.source.rglob("*.og.png")), [])

    def test_missing_playwright_skips_and_exits_0(self) -> None:
        _touch(self.source, "lyra/a.html", PAGE)
        fresh = _touch(self.source, "lyra/fresh.html", PAGE)
        png = og_tree.og_png_for(fresh)
        png.write_bytes(b"KEEP")
        self._stamp(fresh, 1_000)
        self._stamp(png, 2_000)
        with patch.object(og_tree, "_import_playwright", side_effect=ImportError("no module")):
            code, err = self._run(renderer="playwright")
        self.assertEqual(code, 0)
        self.assertIn("playwright unavailable", err)
        self.assertEqual(_counts(err), (0, 1, 0, 1))
        self.assertFalse((self.source / "lyra/a.og.png").exists())
        self.assertEqual(png.read_bytes(), b"KEEP")

    def test_browser_run_delegates_to_og_render(self) -> None:
        page = _touch(self.source, "lyra/a.html", PAGE)
        import og_render

        with (
            patch.object(og_render, "render", return_value=b"\xff\xd8\xff\x00") as got,
            patch.object(og_tree, "_jpeg_bytes_to_png", return_value=b"PNGDATA"),
        ):
            code, err = self._run(renderer="browser-run")
        self.assertEqual(code, 0)
        self.assertEqual(_counts(err), (1, 0, 0, 0))
        got.assert_called_once_with(page)
        self.assertEqual(og_tree.og_png_for(page).read_bytes(), b"PNGDATA")

    def test_missing_source_exits_2(self) -> None:
        missing = self.td / "nope"
        buf = io.StringIO()
        with redirect_stderr(buf):
            code = og_tree.run(missing, renderer="off")
        self.assertEqual(code, 2)
        self.assertIn("source not found", buf.getvalue())

        proc = subprocess.run(
            [sys.executable, str(OG), "--source", str(missing), "--renderer", "off"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("source not found", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_unknown_renderer_exits_2(self) -> None:
        _touch(self.source, "lyra/a.html", PAGE)
        buf = io.StringIO()
        with redirect_stderr(buf):
            code = og_tree.run(self.source, renderer="chrome")
        self.assertEqual(code, 2)
        self.assertFalse(list(self.source.rglob("*.og.png")))

        proc = subprocess.run(
            [sys.executable, str(OG), "--source", str(self.source), "--renderer", "chrome"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(list(self.source.rglob("*.og.png")), [])

    def test_cli_summary_is_the_last_stderr_line(self) -> None:
        _touch(self.source, "lyra/a.html", PAGE)
        proc = subprocess.run(
            [sys.executable, str(OG), "--source", str(self.source), "--renderer", "off"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(
            proc.stderr.strip().splitlines()[-1],
            "og: 0 rendered, 0 up-to-date, 0 failed, 1 skipped",
        )
        self.assertEqual(list(self.source.rglob("*.og.png")), [])


if __name__ == "__main__":
    unittest.main()
