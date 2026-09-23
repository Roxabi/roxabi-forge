#!/usr/bin/env python3
"""Doctor refuses a config that would deploy onto a target listed in refused_targets."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "plugins" / "roxabi-forge" / "scripts" / "lib"
sys.path.insert(0, str(LIB))

from load_config import doctor  # noqa: E402

REFUSED_HOST = "other-forge.example.com"
REFUSED_PROJECT = "other-forge"


def _cfg(hub: Path, **over: object) -> dict:
    base = {
        "version": 1,
        "hub_root": str(hub),
        "vault_markers": [],
        "artifacts_dir": "forge",
        "public_host": "forge.example.com",
        "forge_repo": "https://github.com/Roxabi/roxabi-forge.git",
        "site_dir": "site",
        "registry_dir": "registry",
        "internal_prefix": "a",
        "pages_project": "forge",
    }
    base.update(over)
    return base


class RefusedTargetsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.hub = Path(self._td.name)

    def tearDown(self) -> None:
        self._td.cleanup()

    def _assert_refused(self, d: dict, needle: str) -> None:
        # Both halves matter: the issue stops publish.sh at its doctor gate,
        # the blocker is what forge-doctor.sh and the deploy preflight report.
        self.assertFalse(d["ok"])
        self.assertFalse(d["deploy_ready"])
        self.assertIn("refused_target", d["deploy_blockers"])
        self.assertTrue(any(needle in issue for issue in d["issues"]), d["issues"])

    def test_refused_host_is_not_deployable(self) -> None:
        d = doctor(
            _cfg(
                self.hub,
                public_host=REFUSED_HOST,
                refused_targets={"hosts": [REFUSED_HOST]},
            )
        )
        self._assert_refused(d, REFUSED_HOST)

    def test_refused_project_is_not_deployable(self) -> None:
        d = doctor(
            _cfg(
                self.hub,
                pages_project=REFUSED_PROJECT,
                refused_targets={"pages_projects": [REFUSED_PROJECT]},
            )
        )
        self._assert_refused(d, REFUSED_PROJECT)

    def test_host_and_project_are_normalised(self) -> None:
        # The refusal is written one way, the config spells the target another.
        host = doctor(
            _cfg(
                self.hub,
                public_host="https://Other-Forge.Example.com:443/a/",
                refused_targets={"hosts": [f"  {REFUSED_HOST.upper()}/ "]},
            )
        )
        self._assert_refused(host, REFUSED_HOST)
        project = doctor(
            _cfg(
                self.hub,
                pages_project=" Other-Forge ",
                refused_targets={"pages_projects": ["OTHER-FORGE"]},
            )
        )
        self._assert_refused(project, REFUSED_PROJECT)

    def test_malformed_value_fails_closed(self) -> None:
        for raw in (
            ["other-forge.example.com"],
            "other-forge.example.com",
            {"hosts": "other-forge.example.com"},
            {"hosts": ["ok.example.com", 3]},
            {"pages_projects": [None]},
        ):
            with self.subTest(raw=raw):
                d = doctor(_cfg(self.hub, refused_targets=raw))
                self._assert_refused(d, "refused_targets")

    def test_absent_or_empty_key_allows(self) -> None:
        for over in (
            {},
            {"refused_targets": None},
            {"refused_targets": {}},
            {"refused_targets": {"hosts": [], "pages_projects": []}},
            {"refused_targets": {"hosts": [REFUSED_HOST], "pages_projects": [REFUSED_PROJECT]}},
        ):
            with self.subTest(over=over):
                d = doctor(_cfg(self.hub, **over))
                self.assertNotIn("refused_target", d["deploy_blockers"])
                self.assertFalse(
                    any("refused_targets" in issue for issue in d["issues"]), d["issues"]
                )


if __name__ == "__main__":
    unittest.main()
