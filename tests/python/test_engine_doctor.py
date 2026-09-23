#!/usr/bin/env python3
"""doctor() must refuse a forge_repo publish.sh cannot archive, and name the renderer."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

LIB = Path(__file__).resolve().parents[2] / "plugins" / "roxabi-forge" / "scripts" / "lib"
sys.path.insert(0, str(LIB))

from load_config import (  # noqa: E402
    ENGINE_TREE_MARKERS,
    detect_engine_checkout,
    doctor,
    doctor_online,
    export_env,
    load_config,
)

# git exports these to hooks, and they override `git -C`. A test that inherits
# them would commit into this repository instead of the fixture.
_GIT_DROP = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_PREFIX",
    "GIT_COMMON_DIR",
    "GIT_QUARANTINE_PATH",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_DROP}
    env.update(
        {
            "GIT_AUTHOR_NAME": "Forge Test",
            "GIT_AUTHOR_EMAIL": "forge-test@example.com",
            "GIT_COMMITTER_NAME": "Forge Test",
            "GIT_COMMITTER_EMAIL": "forge-test@example.com",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.stdout.strip()


# The version publish.sh derives the engine tag from. A dev-mode checkout must
# carry the same one, or doctor (like publish) refuses it.
PLUGIN_VERSION = json.loads((LIB.parents[1] / "package.json").read_text(encoding="utf-8"))["version"]


def _init_engine(
    root: Path,
    markers: tuple[str, ...] = ENGINE_TREE_MARKERS,
    *,
    commit: bool,
    version: str | None = PLUGIN_VERSION,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    for rel in markers:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")
    if version is not None:
        pkg = root / "plugins/roxabi-forge/package.json"
        pkg.parent.mkdir(parents=True, exist_ok=True)
        pkg.write_text(json.dumps({"name": "roxabi-forge", "version": version}), encoding="utf-8")
    if commit:
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "engine")


class EngineDoctorTests(unittest.TestCase):
    def _cfg(self, hub: Path, **over: object) -> dict:
        hub.mkdir(parents=True, exist_ok=True)
        cfg: dict = {
            "version": 1,
            "hub_root": str(hub),
            "vault_markers": [],
            "artifacts_dir": "artifacts",
            "public_host": "forge.example.com",
            "site_dir": "site",
            "registry_dir": "registry",
            "internal_prefix": "a",
            "pages_project": "forge",
            "layout": "tree",
        }
        cfg.update(over)
        return cfg

    def test_unborn_checkout_is_not_deployable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine = root / "engine"
            _init_engine(engine, commit=False)
            d = doctor(self._cfg(root / "hub", forge_repo=str(engine)))
        self.assertFalse(d["ok"])
        self.assertTrue(
            any("forge_repo" in issue and "git archive" in issue for issue in d["issues"]),
            d["issues"],
        )
        self.assertIn("forge_repo", d["deploy_blockers"])
        self.assertIsNone(d["engine"]["head"])

    def test_committed_checkout_missing_tree_marker_is_an_issue(self) -> None:
        kept = tuple(
            rel for rel in ENGINE_TREE_MARKERS if not rel.endswith("tree_snapshot.py")
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine = root / "engine"
            _init_engine(engine, kept, commit=True)
            d = doctor(self._cfg(root / "hub", forge_repo=str(engine)))
        self.assertFalse(d["ok"])
        self.assertTrue(any("tree_snapshot.py" in issue for issue in d["issues"]), d["issues"])
        self.assertFalse(d["engine"]["markers_ok"])
        self.assertIn("forge_repo", d["deploy_blockers"])
        self.assertIsNotNone(d["engine"]["head"])

    def test_committed_tree_engine_is_ok_and_names_head(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine = root / "engine"
            _init_engine(engine, commit=True)
            expected = _git(engine, "rev-parse", "--short", "HEAD")
            d = doctor(self._cfg(root / "hub", forge_repo=str(engine)))
        self.assertTrue(d["ok"], d["issues"])
        self.assertEqual(expected, d["engine"]["head"])
        self.assertEqual("path", d["engine"]["kind"])
        self.assertTrue(d["engine"]["markers_ok"])
        self.assertEqual(str(engine), d["engine"]["source"])
        self.assertEqual("dev", d["engine"]["mode"])
        self.assertEqual(f"roxabi-forge/v{PLUGIN_VERSION}+dev.{expected[:7]}", d["engine"]["stamp"])
        self.assertNotIn("forge_repo", d["deploy_blockers"])

    def test_dev_checkout_warns_what_will_actually_ship(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine = root / "engine"
            _init_engine(engine, commit=True)
            (engine / "wip.txt").write_text("not committed\n", encoding="utf-8")
            head = _git(engine, "rev-parse", "--short=7", "HEAD")
            d = doctor(self._cfg(root / "hub", forge_repo=str(engine)))
        self.assertTrue(d["ok"], d["issues"])
        warns = " | ".join(d["warnings"])
        self.assertIn(f"deploys HEAD {head}", warns)
        self.assertIn("uncommitted change(s)", warns)
        self.assertIn("NOT deployed", warns)
        self.assertIn("no upstream", warns)

    def test_dev_checkout_on_another_version_is_a_deploy_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine = root / "engine"
            _init_engine(engine, commit=True, version="0.0.1")
            d = doctor(self._cfg(root / "hub", forge_repo=str(engine)))
        self.assertFalse(d["ok"])
        self.assertTrue(
            any("0.0.1" in i and PLUGIN_VERSION in i for i in d["issues"]), d["issues"]
        )
        self.assertIn("forge_repo", d["deploy_blockers"])

    def test_empty_forge_repo_is_release_mode_on_the_plugin_tag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = doctor(self._cfg(Path(td), forge_repo=""))
        self.assertTrue(d["ok"], d["issues"])
        self.assertEqual("https://github.com/Roxabi/roxabi-forge.git", d["engine"]["source"])
        self.assertEqual("release", d["engine"]["mode"])
        self.assertEqual(f"roxabi-forge/v{PLUGIN_VERSION}", d["engine"]["stamp"])
        self.assertFalse(any("forge_repo" in w for w in d["warnings"]), d["warnings"])

    def test_tree_layout_url_warns_twice_and_does_not_issue(self) -> None:
        url = "https://example.invalid/roxabi-forge.git"
        with tempfile.TemporaryDirectory() as td:
            d = doctor(self._cfg(Path(td), forge_repo=url, layout="tree"))
        self.assertFalse(any("forge_repo" in issue for issue in d["issues"]), d["issues"])
        warns = [w for w in d["warnings"] if "forge_repo" in w]
        self.assertEqual(2, len(warns), warns)
        self.assertTrue(any("not verified offline" in w for w in warns), warns)
        self.assertTrue(any("overwrite production" in w for w in warns), warns)
        self.assertEqual(
            {
                "source": url,
                "kind": "url",
                "mode": "release",
                "stamp": f"roxabi-forge/v{PLUGIN_VERSION}",
                "head": None,
                "markers_ok": False,
            },
            d["engine"],
        )
        self.assertNotIn("forge_repo", d["deploy_blockers"])

    def test_url_without_tree_layout_has_only_the_offline_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = doctor(
                self._cfg(
                    Path(td),
                    forge_repo="git@example.com:org/forge.git",
                    layout="slug",
                )
            )
        warns = [w for w in d["warnings"] if "forge_repo" in w]
        self.assertEqual(1, len(warns), warns)
        self.assertIn("not verified offline", warns[0])
        self.assertNotIn("overwrite production", warns[0])
        self.assertEqual("url", d["engine"]["kind"])

    def test_legacy_engine_url_is_an_issue_and_blocks_deploy(self) -> None:
        for url in (
            "https://github.com/Roxabi/roxabi-forge-legacy.git",
            "git@github.com:Roxabi/roxabi-forge-legacy.git",
        ):
            with self.subTest(url=url), tempfile.TemporaryDirectory() as td:
                d = doctor(self._cfg(Path(td), forge_repo=url))
                self.assertFalse(d["ok"])
                self.assertTrue(
                    any("legacy" in issue and url in issue for issue in d["issues"]),
                    d["issues"],
                )
                self.assertIn("forge_repo", d["deploy_blockers"])

    def test_canonical_engine_url_is_not_an_issue(self) -> None:
        url = "https://github.com/Roxabi/roxabi-forge.git"
        with tempfile.TemporaryDirectory() as td:
            d = doctor(self._cfg(Path(td), forge_repo=url))
        self.assertFalse(any("forge_repo" in issue for issue in d["issues"]), d["issues"])
        self.assertNotIn("forge_repo", d["deploy_blockers"])

    def test_bogus_renderer_is_an_issue_and_absence_is_browser_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine = root / "engine"
            _init_engine(engine, commit=True)
            base = self._cfg(root / "hub", forge_repo=str(engine))
            bogus = doctor({**base, "og_renderer": "bogus"})
            absent = doctor(base)
            explicit = doctor({**base, "og_renderer": "off"})
        self.assertFalse(bogus["ok"])
        self.assertTrue(
            any("og_renderer" in issue and "bogus" in issue for issue in bogus["issues"]),
            bogus["issues"],
        )
        self.assertEqual("browser-run", absent["og_renderer"])
        self.assertFalse(any("og_renderer" in issue for issue in absent["issues"]))
        self.assertEqual("off", explicit["og_renderer"])
        self.assertTrue(explicit["ok"], explicit["issues"])

    def test_load_config_defaults_a_missing_renderer_and_keeps_an_explicit_one(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing = root / "missing.json"
            missing.write_text(
                json.dumps({"hub_root": str(root), "vault_markers": []}) + "\n",
                encoding="utf-8",
            )
            explicit = root / "explicit.json"
            explicit.write_text(
                json.dumps(
                    {"hub_root": str(root), "vault_markers": [], "og_renderer": "playwright"}
                )
                + "\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"FORGE_CONFIG": str(missing)}):
                self.assertEqual("browser-run", load_config()["og_renderer"])
            with patch.dict(os.environ, {"FORGE_CONFIG": str(explicit)}):
                self.assertEqual("playwright", load_config()["og_renderer"])

    def test_export_env_names_the_renderer(self) -> None:
        cfg = {
            "public_host": "forge.example.com",
            "forge_repo": "https://example.invalid/engine.git",
            "hub_root": "",
            "pages_project": "forge",
        }
        self.assertIn("FORGE_OG_RENDERER='browser-run'", export_env(cfg))
        cfg["og_renderer"] = "playwright"
        self.assertIn("FORGE_OG_RENDERER='playwright'", export_env(cfg))
        cfg["og_renderer"] = "off"
        self.assertIn("FORGE_OG_RENDERER='off'", export_env(cfg))

    def test_playwright_renderer_probes_the_local_toolchain_not_browser_run(self) -> None:
        pf = {"ok": True, "errors": [], "warnings": [], "checks": {}, "require_kv": True}
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(
                Path(td),
                forge_repo="https://example.invalid/engine.git",
                og_renderer="playwright",
            )
            prod = {"ok": True, "has_deployment": True, "stamp": ""}
            with patch("load_config.preflight_mutations", return_value=pf), patch(
                "engine_drift.production_stamp", return_value=prod
            ):
                with patch("load_config.browser_run_probe") as spy:
                    with patch("load_config.shutil.which", return_value=None):
                        with patch("load_config._playwright_importable", return_value=False):
                            missing = doctor_online(cfg)
                    with patch("load_config.shutil.which", return_value="/usr/bin/uv"):
                        present = doctor_online(cfg)
        self.assertEqual(0, spy.call_count)
        self.assertTrue(missing["ok"], missing["issues"])
        self.assertTrue(
            any(
                "playwright toolchain missing" in w and "publish still succeeds" in w
                for w in missing["online_warnings"]
            ),
            missing["online_warnings"],
        )
        self.assertFalse(any("toolchain missing" in w for w in present["online_warnings"]))
        self.assertFalse(missing["browser_run"]["checked"])


class OnlineEngineLineTests(unittest.TestCase):
    """forge-doctor.sh --online prints `prod <L|unknown> · plugin <P> · <state>`."""

    PF_OK = {"ok": True, "errors": [], "warnings": [], "checks": {}, "require_kv": True}

    def _online(self, prod: dict | None, *, pf: dict | None = None) -> dict:
        with tempfile.TemporaryDirectory() as td:
            cfg = EngineDoctorTests()._cfg(Path(td), forge_repo="", og_renderer="off")
            with patch("load_config.preflight_mutations", return_value=pf or self.PF_OK), patch(
                "engine_drift.production_stamp", return_value=prod
            ) as spy:
                d = doctor_online(cfg)
        self.stamp_calls = spy.call_count
        return d

    def test_each_production_state_is_one_line(self) -> None:
        p = PLUGIN_VERSION
        major, minor, patch_ = (int(x) for x in p.split("."))
        newer = f"{major}.{minor}.{patch_ + 1}"
        older = f"{major}.{minor}.{patch_ - 1}" if patch_ else f"{major - 1}.0.0"
        cases = (
            ({"ok": True, "has_deployment": True, "stamp": ""},
             f"prod unknown · plugin {p} · stamped on next publish"),
            ({"ok": True, "has_deployment": True, "stamp": f"roxabi-forge/v{p}"},
             f"prod {p} · plugin {p} · aligned"),
            ({"ok": True, "has_deployment": True, "stamp": f"roxabi-forge/v{newer}"},
             f"prod {newer} · plugin {p} · update plugin"),
            ({"ok": True, "has_deployment": True, "stamp": f"roxabi-forge/v{older}"},
             f"prod {older} · plugin {p} · upgrade on next publish"),
            ({"ok": False, "error": "HTTP 403: denied"},
             f"prod unverified · plugin {p} · HTTP 403: denied"),
        )
        for prod, line in cases:
            with self.subTest(line=line):
                self.assertEqual(line, self._online(prod)["engine_drift"]["line"])

    def test_newer_production_is_an_advisory_warning_not_an_exit_code(self) -> None:
        major, minor, patch_ = (int(x) for x in PLUGIN_VERSION.split("."))
        d = self._online(
            {"ok": True, "has_deployment": True, "stamp": f"roxabi-forge/v{major + 1}.0.0"}
        )
        self.assertTrue(d["online_ok"])
        self.assertTrue(
            any("omp plugin upgrade roxabi-forge@roxabi-forge" in w for w in d["online_warnings"]),
            d["online_warnings"],
        )

    def test_failed_preflight_spends_no_pages_call(self) -> None:
        pf = {**self.PF_OK, "ok": False, "errors": ["token invalid"]}
        d = self._online({"ok": True, "stamp": ""}, pf=pf)
        self.assertEqual(0, self.stamp_calls)
        self.assertIn("prod unverified", d["engine_drift"]["line"])


class EngineCheckoutDetectionTests(unittest.TestCase):
    """detect_engine_checkout is setup's dev-mode suggestion and publish's
    "runs from this checkout" test: it must only ever name a checkout doctor
    would accept, never a guess."""

    def test_committed_engine_is_found_from_the_plugin_lib_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "engine"
            _init_engine(root, commit=True)
            # The running script lives in plugins/roxabi-forge/scripts/.
            start = (root / ENGINE_TREE_MARKERS[-1]).parent
            self.assertEqual(str(root.resolve()), detect_engine_checkout(start))

    def test_non_repository_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plain = Path(td) / "plain"
            for rel in ENGINE_TREE_MARKERS:
                (plain / rel).parent.mkdir(parents=True, exist_ok=True)
                (plain / rel).write_text("ok\n", encoding="utf-8")
            self.assertIsNone(detect_engine_checkout(plain))

    def test_repository_without_markers_is_rejected(self) -> None:
        # The pre-tree repository: a committed checkout with the site
        # skeleton but not the tree-engine plugin.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "old"
            _init_engine(root, ("site/404.html",), commit=True)
            self.assertIsNone(detect_engine_checkout(root))

    def test_repository_without_commit_is_rejected(self) -> None:
        # publish.sh archives HEAD; an unborn branch has nothing to deploy.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "engine"
            _init_engine(root, commit=False)
            self.assertIsNone(detect_engine_checkout(root))


if __name__ == "__main__":
    unittest.main()
