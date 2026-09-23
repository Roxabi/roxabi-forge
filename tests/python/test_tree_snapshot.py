#!/usr/bin/env python3
"""Tree publish: bar in the snapshot, never in the SSOT, and a missing page is refused."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "roxabi-forge" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "lib"))

from snapshot import compare_record, fingerprint  # noqa: E402
from tree_snapshot import build_tree_snapshot  # noqa: E402


def _touch(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TreeSnapshotTests(unittest.TestCase):
    def test_bar_is_in_the_snapshot_and_not_the_ssot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            html = "<html><body><h1>Keep</h1></body></html>\n"
            _touch(source, "lyra/visuals/architecture.html", html)
            _touch(source, "_shared/hero-base.css", "body{}")
            first = build_tree_snapshot(source, dest)
            served = (dest / "lyra/visuals/architecture.html").read_text(encoding="utf-8")
            self.assertIn("<!-- forge-share-bar -->", served)
            self.assertEqual((source / "lyra/visuals/architecture.html").read_text(encoding="utf-8"), html)
            self.assertEqual((dest / "_shared/hero-base.css").read_text(encoding="utf-8"), "body{}")
            second = build_tree_snapshot(source, dest)
            self.assertEqual(second, first)
            self.assertEqual((dest / "lyra/visuals/architecture.html").read_text(encoding="utf-8"), served)

            manifest = (dest / "manifest.json").read_text(encoding="utf-8")
            self.assertIn("lyra/visuals/architecture.html", manifest)
            self.assertNotIn("share", manifest)

    def test_the_data_tree_never_overwrites_the_engine_shell(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(source, "index.html", "<html><body>vieille landing</body></html>")
            _touch(source, "404.html", "<html><body>vieux 404</body></html>")
            _touch(source, "robots.txt", "Disallow: /")
            _touch(source, "Makefile", "deploy:\n\techo no\n")
            _touch(source, "lyra/index.html", "<html><head><title>Lyra</title></head><body>ok</body></html>")
            _touch(dest, "index.html", "<html><body>catalogue engine</body></html>")
            _touch(dest, "404.html", "<html><body>404 engine</body></html>")

            digests = build_tree_snapshot(source, dest)

            self.assertEqual(
                (dest / "index.html").read_text(encoding="utf-8"),
                "<html><body>catalogue engine</body></html>",
            )
            self.assertEqual(
                (dest / "404.html").read_text(encoding="utf-8"),
                "<html><body>404 engine</body></html>",
            )
            self.assertFalse((dest / "robots.txt").exists())
            self.assertFalse((dest / "Makefile").exists())
            self.assertEqual(sorted(digests), ["lyra/index.html"])
            # A nested index.html is a real page and still ships.
            self.assertIn("<!-- forge-share-bar -->", (dest / "lyra/index.html").read_text(encoding="utf-8"))

    def test_manifest_carries_what_the_catalogue_renders(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(
                source,
                "lyra/visuals/architecture.html",
                "<html><head><title>Lyra &amp; l’archi</title></head><body>x</body></html>",
            )
            (source / "lyra/visuals/architecture.og.png").write_bytes(b"png")
            _touch(source, "metalyde/landing.html", "<html><body>sans titre</body></html>")

            build_tree_snapshot(source, dest)
            entries = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            by_path = {e["f"]: e for e in entries}

            archi = by_path["lyra/visuals/architecture.html"]
            self.assertEqual(archi["t"], "Lyra & l’archi")
            self.assertEqual(archi["cat"], "lyra")
            self.assertTrue(archi["p"])
            self.assertEqual(archi["thumb"], "/lyra/visuals/architecture.og.png")
            self.assertRegex(str(archi["d"]), r"^\d{4}-\d{2}-\d{2}$")
            self.assertGreaterEqual(int(archi["kb"]), 1)

            landing = by_path["metalyde/landing.html"]
            self.assertEqual(landing["t"], "landing")
            self.assertFalse(landing["p"])
            self.assertNotIn("thumb", landing)

    def test_tree_layout_fingerprints_paths_not_top_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            # A top-level dir holding index.html looks exactly like a legacy slug.
            _touch(source, "lyra/index.html", "<html><body>a</body></html>")
            _touch(source, "lyra/visuals/architecture.html", "<html><body>b</body></html>")

            tree = fingerprint(source, "tree")
            self.assertEqual(
                sorted(tree), ["lyra/index.html", "lyra/visuals/architecture.html"]
            )
            self.assertEqual(sorted(fingerprint(source, "slug")), ["lyra"])

    def test_a_broken_symlink_does_not_break_the_publish(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(source, "lyra/visuals/architecture.html", "<html><body>ok</body></html>")
            _touch(source, "lyra/assets/real.css", "body{}")
            (source / "lyra" / "gone").symlink_to(source / "lyra" / "missing-target")
            (source / "lyra" / "linked.css").symlink_to(source / "lyra" / "assets" / "real.css")

            digests = build_tree_snapshot(source, dest)

            self.assertEqual(sorted(digests), ["lyra/visuals/architecture.html"])
            self.assertFalse((dest / "lyra/gone").exists())
            # A live link is materialised as its content, not copied as a link.
            self.assertEqual((dest / "lyra/linked.css").read_text(encoding="utf-8"), "body{}")
            self.assertFalse((dest / "lyra/linked.css").is_symlink())

    def test_the_snapshot_records_which_page_loads_which_asset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(
                source,
                "lyra/visuals/architecture.html",
                """<html><head>
                <link rel="stylesheet" href="css/architecture.css">
                <link rel="stylesheet" href="../../_shared/hero-base.css">
                <link rel="stylesheet" href="https://fonts.example/x.css">
                <style>body{background:url('../img/bg.png')}</style>
                </head><body>
                <img src="/lyra/img/diagram.svg">
                <a href="sibling.html">voisin</a>
                <script src="js/app.js?v=3"></script>
                </body></html>""",
            )
            _touch(source, "lyra/visuals/sibling.html", "<html><body>voisin</body></html>")
            _touch(source, "lyra/visuals/css/architecture.css", "body{}")
            _touch(source, "lyra/visuals/js/app.js", "//")
            _touch(source, "lyra/img/bg.png", "x")
            _touch(source, "lyra/img/diagram.svg", "<svg/>")
            _touch(source, "_shared/hero-base.css", "body{}")
            (source / "lyra/visuals/architecture.og.png").write_bytes(b"png")

            build_tree_snapshot(source, dest)
            owners = json.loads((dest / "asset-owners.json").read_text(encoding="utf-8"))

            page = "lyra/visuals/architecture.html"
            # Relative, root-relative, css url() and the query-stringed script.
            self.assertEqual(owners["lyra/visuals/css/architecture.css"], [page])
            self.assertEqual(owners["lyra/visuals/js/app.js"], [page])
            self.assertEqual(owners["lyra/img/bg.png"], [page])
            self.assertEqual(owners["lyra/img/diagram.svg"], [page])
            # The catalogue card loads the preview, the page does not.
            self.assertEqual(owners["lyra/visuals/architecture.og.png"], [page])
            # Core is public already, another HTML keeps its own visibility, and
            # an external stylesheet is not ours to serve.
            self.assertNotIn("_shared/hero-base.css", owners)
            self.assertNotIn("lyra/visuals/sibling.html", owners)
            self.assertFalse([a for a in owners if a.startswith("http")])

    def test_sources_and_oversize_files_stay_out_of_the_deploy(self) -> None:
        import tree_snapshot

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(source, "lyra/visuals/architecture.html", "<html><body>ok</body></html>")
            _touch(source, "lyra/visuals/app.css", "body{}")
            # The tree is a working directory: page sources sit next to pages.
            _touch(source, "lyra/avatar/embeddings-test/001.pt", "weights")
            _touch(source, "lyra/avatar/prompts/brief.md", "prompt")
            _touch(source, "lyra/visuals/build.py", "print()")
            _touch(source, "lyra/visuals/demo.mp4", "video")
            _touch(source, "lyra/graph-templates/base.html", "<html></html>")
            _touch(source, ".stversions/old.html", "<html></html>")
            _touch(source, "indydev/audio/source.wav", "x" * (tree_snapshot.MAX_FILE_BYTES + 1))

            digests = build_tree_snapshot(source, dest)

            self.assertEqual(sorted(digests), ["lyra/visuals/architecture.html"])
            self.assertTrue((dest / "lyra/visuals/app.css").is_file())
            for gone in (
                "lyra/avatar/embeddings-test/001.pt",
                "lyra/avatar/prompts/brief.md",
                "lyra/visuals/build.py",
                "lyra/visuals/demo.mp4",
                "lyra/graph-templates/base.html",
                ".stversions/old.html",
                "indydev/audio/source.wav",
            ):
                self.assertFalse((dest / gone).exists(), gone)
            # The oversize file is reported, not silently dropped.
            self.assertIn("indydev/audio/source.wav", tree_snapshot.OVERSIZE)

    def test_a_tombstone_page_is_not_catalogued(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(source, "lyra/visuals/architecture.html", "<html><body>ok</body></html>")
            _touch(
                source,
                "metalyde/visuals/roadmap-performance-blocks.html",
                "<html><head><title>Removed</title></head><body>gone</body></html>",
            )
            digests = build_tree_snapshot(source, dest)
            self.assertEqual(sorted(digests), ["lyra/visuals/architecture.html"])
            self.assertFalse((dest / "metalyde/visuals/roadmap-performance-blocks.html").exists())
            manifest = (dest / "manifest.json").read_text(encoding="utf-8")
            self.assertNotIn("roadmap-performance-blocks", manifest)

    def test_cards_get_a_downscaled_preview(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent")
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(source, "lyra/visuals/architecture.html", "<html><body>ok</body></html>")
            big = source / "lyra/visuals/architecture.og.png"
            Image.new("RGB", (2400, 1260), (232, 160, 48)).save(big)

            build_tree_snapshot(source, dest)
            entry = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))[0]
            small = dest / "lyra/visuals/architecture.thumb.webp"

            self.assertEqual(entry["thumb"], "/lyra/visuals/architecture.thumb.webp")
            self.assertTrue(small.is_file())
            with Image.open(small) as im:
                self.assertEqual(im.width, 600)
            self.assertLess(small.stat().st_size, big.stat().st_size)
            # The full-size OG still ships: social unfurls read it.
            self.assertTrue((dest / "lyra/visuals/architecture.og.png").is_file())
            # Both are reachable for a visitor who may open the public page.
            owners = json.loads((dest / "asset-owners.json").read_text(encoding="utf-8"))
            self.assertIn("lyra/visuals/architecture.thumb.webp", owners)
            self.assertIn("lyra/visuals/architecture.og.png", owners)

    def test_a_missing_recorded_page_is_refused(self) -> None:
        local = {"lyra/visuals/architecture.html": "abc"}
        record = {
            "deployment_id": "dep-1",
            "slugs": {
                "lyra/visuals/architecture.html": "abc",
                "lyra/visuals/gone.html": "def",
            },
        }
        result = compare_record(record, local, "dep-1", [])
        self.assertFalse(result["ok"])
        self.assertIn("lyra/visuals/gone.html", result["unexpected_removals"])

    def test_a_fragment_is_a_subresource_not_a_catalogue_card(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            parent = "diagrams/lyra-chimera/lyra-chimera.html"
            fragment = "diagrams/lyra-chimera/tabs/lyra-to-chimera/tab-blueprint.html"
            _touch(
                source,
                parent,
                """<html><head><title>Lyra to Chimera</title></head><body>
                <div data-src="tabs/lyra-to-chimera/tab-blueprint.html"></div>
                </body></html>""",
            )
            _touch(source, fragment, "<section><h2>Blueprint</h2></section>\n")

            build_tree_snapshot(source, dest)
            paths = {e["f"] for e in json.loads((dest / "manifest.json").read_text(encoding="utf-8"))}
            owners = json.loads((dest / "asset-owners.json").read_text(encoding="utf-8"))
            served_parent = (dest / parent).read_text(encoding="utf-8")
            served_frag = (dest / fragment).read_text(encoding="utf-8")

            self.assertIn(parent, paths)
            self.assertNotIn(fragment, paths)
            self.assertEqual(owners[fragment], [parent])
            self.assertIn("<!-- forge-share-bar -->", served_parent)
            self.assertNotIn("forge-share-bar", served_frag)
            self.assertIn("Blueprint", served_frag)
            self.assertNotIn("forge-share-bar", (source / fragment).read_text(encoding="utf-8"))

    def test_a_linked_page_is_not_an_asset_key(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            parent = "diagrams/lyra-chimera/lyra-chimera.html"
            linked = "diagrams/lyra-chimera/sibling.html"
            # data-src does not make a document a fragment. The tag does.
            disguised = "diagrams/lyra-chimera/tabs/not-a-fragment.html"
            _touch(
                source,
                parent,
                """<html><body>
                <a href="sibling.html">full page</a>
                <div data-src="tabs/not-a-fragment.html"></div>
                </body></html>""",
            )
            _touch(
                source,
                linked,
                '<HTML lang="en"><head><title>Sibling</title></head><body>real</body></html>',
            )
            _touch(source, disguised, "<html><body>still a page</body></html>")

            build_tree_snapshot(source, dest)
            owners = json.loads((dest / "asset-owners.json").read_text(encoding="utf-8"))
            paths = {e["f"] for e in json.loads((dest / "manifest.json").read_text(encoding="utf-8"))}

            self.assertNotIn(linked, owners)
            self.assertNotIn(disguised, owners)
            self.assertIn(linked, paths)
            self.assertIn(disguised, paths)
            self.assertFalse([k for k in owners if k.endswith(".html")])

    def test_an_orphan_fragment_is_a_key_with_no_owner(self) -> None:
        """Not catalogued, but still a key: absence would send it back down the
        page path, where it answers 302 /login instead of closing as a resource."""
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            orphan = "diagrams/lyra-chimera/tabs/unused/tab-orphan.html"
            _touch(source, "diagrams/lyra-chimera/lyra-chimera.html", "<html><body>page</body></html>")
            _touch(source, orphan, "<section>nobody loads me</section>\n")

            build_tree_snapshot(source, dest)
            manifest = (dest / "manifest.json").read_text(encoding="utf-8")
            owners = json.loads((dest / "asset-owners.json").read_text(encoding="utf-8"))

            self.assertNotIn("tab-orphan.html", manifest)
            self.assertEqual(owners.get(orphan), [])
            self.assertNotIn("forge-share-bar", (dest / orphan).read_text(encoding="utf-8"))

    def test_an_asset_loaded_only_inside_a_tab_belongs_to_the_parent_page(self) -> None:
        """A fragment has no visibility of its own, so an image used only in a
        tab would never open on a public page if ownership stopped at the tab."""
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(
                source,
                "lyra/page.html",
                '<html><body><div data-src="tabs/tab.html"></div></body></html>',
            )
            _touch(source, "lyra/tabs/tab.html", '<section><img src="../shot.png"></section>')
            _touch(source, "lyra/shot.png", "png")

            build_tree_snapshot(source, dest)
            owners = json.loads((dest / "asset-owners.json").read_text(encoding="utf-8"))

            self.assertEqual(owners.get("lyra/shot.png"), ["lyra/page.html"])
            self.assertEqual(owners.get("lyra/tabs/tab.html"), ["lyra/page.html"])

    def test_a_tab_asset_resolves_against_the_parent_page_url(self) -> None:
        """innerHTML injection: the browser resolves a tab's relative URL against
        the parent page's URL. The fragment-dir reading still counts too."""
        owners = self._owners(
            {
                "p.html": "<html><body><script>fetch('tabs/p/tab-' + id + '.html')</script>"
                "</body></html>",
                "tabs/p/tab-a.html": '<section><img src="tabs/p/diagrams/x.svg">'
                '<img src="own.png"></section>',
                "tabs/p/diagrams/x.svg": "<svg/>",
                "tabs/p/own.png": "png",
            }
        )
        self.assertEqual(owners["tabs/p/diagrams/x.svg"], ["p.html"])
        self.assertEqual(owners["tabs/p/own.png"], ["p.html"])

    def _owners(self, files: dict[str, str]) -> dict[str, list[str]]:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            for rel, text in files.items():
                _touch(source, rel, text)
            build_tree_snapshot(source, dest)
            return json.loads((dest / "asset-owners.json").read_text(encoding="utf-8"))

    def test_a_concat_loader_in_an_external_script_owns_its_tabs(self) -> None:
        """No literal path to the tab exists: the URL is built at runtime."""
        owners = self._owners(
            {
                "p.html": '<html><body><script src="loader.js?v=2"></script></body></html>',
                "loader.js": "fetch(\"tabs/p/tab-\" + tabId + \".html\").then(r => r.text())",
                "tabs/p/tab-a.html": '<section><img src="../../shot.png"></section>',
                "shot.png": "png",
            }
        )
        self.assertEqual(owners["tabs/p/tab-a.html"], ["p.html"])
        # The tab's own assets follow it to the parent page.
        self.assertEqual(owners["shot.png"], ["p.html"])

    def test_a_template_literal_loader_inline_owns_its_tabs(self) -> None:
        owners = self._owners(
            {
                "lyra/p.html": "<html><body><script>fetch(`tabs/p/tab-${id}.html`)</script></body></html>",
                "lyra/tabs/p/tab-a.html": "<section>a</section>",
            }
        )
        self.assertEqual(owners["lyra/tabs/p/tab-a.html"], ["lyra/p.html"])

    def test_the_loader_prefix_resolves_from_the_page_not_the_script(self) -> None:
        """fetch() resolves against the document URL, wherever the script lives."""
        owners = self._owners(
            {
                "lyra/visuals/p.html": '<html><body><script src="js/p.js"></script></body></html>',
                "lyra/visuals/js/p.js": "fetch('tabs/p/tab-' + id + '.html')",
                "lyra/visuals/tabs/p/tab-a.html": "<section>a</section>",
                "lyra/visuals/js/tabs/p/tab-a.html": "<section>decoy</section>",
            }
        )
        self.assertEqual(owners["lyra/visuals/tabs/p/tab-a.html"], ["lyra/visuals/p.html"])
        self.assertEqual(owners["lyra/visuals/js/tabs/p/tab-a.html"], [])

    def test_the_variable_part_never_crosses_a_directory(self) -> None:
        owners = self._owners(
            {
                "p.html": "<html><body><script>fetch('tabs/v2/tab-' + id + '.html');"
                "fetch('panes/' + name + '.html')</script></body></html>",
                "tabs/v2/tab-a.html": "<section>v2</section>",
                "tabs/v1/tab-a.html": "<section>v1</section>",
                "panes/x.html": "<section>pane</section>",
                "panes/deep/x.html": "<section>too deep</section>",
            }
        )
        self.assertEqual(owners["tabs/v2/tab-a.html"], ["p.html"])
        self.assertEqual(owners["panes/x.html"], ["p.html"])
        self.assertEqual(owners["tabs/v1/tab-a.html"], [])
        self.assertEqual(owners["panes/deep/x.html"], [])

    def test_a_real_page_matching_a_loader_is_never_a_key(self) -> None:
        owners = self._owners(
            {
                "p.html": "<html><body><script>fetch(`tabs/p/tab-${id}.html`)</script></body></html>",
                "tabs/p/tab-a.html": "<section>a</section>",
                "tabs/p/tab-real.html": "<html><body>a page with its own ACL</body></html>",
            }
        )
        self.assertEqual(owners["tabs/p/tab-a.html"], ["p.html"])
        self.assertNotIn("tabs/p/tab-real.html", owners)

    def test_a_url_builder_outside_fetch_with_a_runtime_base_owns_its_tabs(self) -> None:
        """The URL is returned by a helper, starts with a runtime base, and the
        script is included by a root-absolute src with a cache-busting query."""
        owners = self._owners(
            {
                "personnalDev/_shared/guide-app.js": "function fragmentURL(id) {\n"
                "  return `${guideBase()}tabs/${slug}/${lang}/tab-${id}.html`;\n}\n",
                "personnalDev/enneagram/enneagram-guide.html": "<html><body>"
                '<script src="/personnalDev/_shared/guide-app.js?v=4"></script></body></html>',
                "personnalDev/enneagram/tabs/enneagram-guide/en/tab-how-it-works.html": "<section/>",
            }
        )
        self.assertEqual(
            owners["personnalDev/enneagram/tabs/enneagram-guide/en/tab-how-it-works.html"],
            ["personnalDev/enneagram/enneagram-guide.html"],
        )

    def test_a_loader_with_two_variable_parts_owns_its_tabs(self) -> None:
        owners = self._owners(
            {
                "g/p.html": '<html><body><script src="js/p.js"></script></body></html>',
                "g/js/p.js": "var NAME = 'p'\nfetch('tabs/' + NAME + '/tab-' + id + '.html')",
                "g/tabs/p/tab-a.html": "<section>a</section>",
                # One segment per variable part: a flat v1 tab is not reached.
                "g/tabs/tab-a.html": "<section>v1</section>",
            }
        )
        self.assertEqual(owners["g/tabs/p/tab-a.html"], ["g/p.html"])
        self.assertEqual(owners["g/tabs/tab-a.html"], [])

    def test_a_tab_path_held_in_a_string_owns_its_tab(self) -> None:
        """fetch(PANELS[id]) or fetch(panel.dataset.url): the path is a plain
        string, in a script or an attribute the asset scan does not read."""
        owners = self._owners(
            {
                "p.html": '<html><body><div data-url="tabs/p/tab-c.html"></div>'
                '<script src="p.js"></script></body></html>',
                "p.js": "const PANELS = {a: 'tabs/p/tab-a.html', b: \"tabs/p/tab-b.html?v=2\"}\n"
                "fetch(PANELS[id])",
                "tabs/p/tab-a.html": "<section>a</section>",
                "tabs/p/tab-b.html": "<section>b</section>",
                "tabs/p/tab-c.html": "<section>c</section>",
            }
        )
        for tab in ("a", "b", "c"):
            self.assertEqual(owners[f"tabs/p/tab-{tab}.html"], ["p.html"])

    def test_a_shared_loader_never_opens_a_sibling_pages_tabs(self) -> None:
        """Both pages match 'tabs/' + NAME + '/tab-' + id; each tab dir is named
        after its page, so the public page must not open the other's tabs."""
        loader = "<script>fetch('tabs/' + NAME + '/tab-' + id + '.html')</script>"
        owners = self._owners(
            {
                "pf/portfolio.html": f"<html><body>{loader}</body></html>",
                "pf/daily.html": f"<html><body>{loader}</body></html>",
                "pf/tabs/portfolio/tab-a.html": "<section>p</section>",
                "pf/tabs/daily/tab-a.html": '<section><img src="../../shot.png"></section>',
                "pf/shot.png": "png",
            }
        )
        self.assertEqual(owners["pf/tabs/portfolio/tab-a.html"], ["pf/portfolio.html"])
        self.assertEqual(owners["pf/tabs/daily/tab-a.html"], ["pf/daily.html"])
        self.assertEqual(owners["pf/shot.png"], ["pf/daily.html"])

    def test_a_template_that_is_only_a_variable_and_html_is_ignored(self) -> None:
        """`${name}.html` would match every fragment of the page directory."""
        owners = self._owners(
            {
                "p.html": "<html><body><script>fetch(`${name}.html`); load(name + '.html')"
                "</script></body></html>",
                "x.html": "<section>not loaded by p</section>",
            }
        )
        self.assertEqual(owners["x.html"], [])

    def test_the_cli_reports_pages_fragments_and_orphans(self) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        import tree_snapshot

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "ssot"
            dest = Path(td) / "site"
            _touch(
                source,
                "lyra/page.html",
                '<html><body><div data-src="tabs/tab.html"></div></body></html>',
            )
            _touch(source, "lyra/tabs/tab.html", "<section>tab</section>")
            _touch(source, "lyra/tabs/orphan.html", "<section>alone</section>")
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = tree_snapshot.main(
                    ["tree_snapshot.py", "--source", str(source), "--dest", str(dest)]
                )
            self.assertEqual(code, 0)
            text = err.getvalue()
            self.assertIn("snapshot: 1 page(s)", text)
            self.assertIn("snapshot: 2 fragment(s), 1 orphan(s)", text)


if __name__ == "__main__":
    unittest.main()
