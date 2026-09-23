#!/usr/bin/env python3
"""Archive excludes secrets, prune drops the test corpus, live tree is refused."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "roxabi-forge" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import prune_corpus  # noqa: E402
from prune_corpus import dropped, run  # noqa: E402


def _touch(root: Path, rel: str, text: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class PruneCorpusTests(unittest.TestCase):
    def test_cut_rules(self) -> None:
        self.assertTrue(dropped("_test-forge/voice-stack.html"))
        self.assertTrue(dropped("references/gallery-templates/examples/simple-gallery-preview.html"))
        self.assertTrue(dropped("references/showcases/showcase-chart.html"))
        self.assertTrue(dropped("reference-gallery.html"))
        self.assertTrue(dropped("_shared/diagrams/alphaclaw.html"))
        self.assertFalse(dropped("_shared/hero-base.css"))
        self.assertFalse(dropped("lyra/visuals/architecture.html"))
        self.assertFalse(dropped("lyra/visuals/architecture.og.png"))

    def test_archive_then_prune_on_a_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "forge"
            archive = Path(td) / "archive"
            _touch(root, "lyra/visuals/architecture.html", "<html>keep</html>")
            _touch(root, "lyra/visuals/architecture.og.png", "png")
            _touch(root, "_shared/hero-base.css", "css")
            _touch(root, "_shared/diagrams/alphaclaw.html", "<html>drop</html>")
            _touch(root, "_test-forge/voice-stack.html", "<html>test</html>")
            _touch(root, "references/showcases/showcase-chart.html", "<html>show</html>")
            _touch(root, "reference-gallery.html", "<html>idx</html>")
            _touch(root, ".env", "CLOUDFLARE_API_TOKEN=secret")
            _touch(root, "_dist/index.html", "built")
            code = run(root, archive, live=False)
            self.assertEqual(code, 0)
            self.assertTrue((root / "lyra/visuals/architecture.html").is_file())
            self.assertTrue((root / "lyra/visuals/architecture.og.png").is_file())
            self.assertTrue((root / "_shared/hero-base.css").is_file())
            self.assertFalse((root / "_shared/diagrams/alphaclaw.html").exists())
            self.assertFalse((root / "_test-forge/voice-stack.html").exists())
            self.assertFalse((root / "reference-gallery.html").exists())
            self.assertTrue((archive / "lyra/visuals/architecture.html").is_file())
            self.assertTrue((archive / "_shared/diagrams/alphaclaw.html").is_file())
            self.assertFalse((archive / ".env").exists())
            self.assertFalse((archive / "_dist/index.html").exists())

    def test_live_tree_is_refused_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "forge"
            root.mkdir()
            _touch(root, "lyra/keep.html", "keep")
            archive = Path(td) / "archive"
            previous = prune_corpus.LIVE_ROOT
            prune_corpus.LIVE_ROOT = root
            try:
                code = run(root, archive, live=False)
            finally:
                prune_corpus.LIVE_ROOT = previous
            self.assertEqual(code, 2)
            self.assertFalse(archive.exists())
            self.assertTrue((root / "lyra/keep.html").is_file())


if __name__ == "__main__":
    unittest.main()
