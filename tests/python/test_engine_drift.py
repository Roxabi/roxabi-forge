#!/usr/bin/env python3
"""engine_drift: which engine a publish deploys, and the production drift gate.

The gate is the only thing standing between an outdated plugin and a
production engine rollback, so every verdict branch is pinned here: parse,
compare, the flag policy, the Pages API read, the forge_repo resolution, and
the shell-assignment output publish.sh evals.
"""
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

import engine_drift  # noqa: E402
from engine_drift import (  # noqa: E402
    UPDATE_COMMANDS,
    EngineError,
    compare,
    format_stamp,
    gate,
    parse_stamp,
    production_stamp,
    read_plugin_version,
    resolve_engine,
)

PLUGIN_ROOT = LIB.parents[1]
CANONICAL = "https://github.com/Roxabi/roxabi-forge.git"

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
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def _checkout(root: Path, version: str | None) -> str:
    """Committed engine checkout carrying `version` in its plugin package.json."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    (root / "site").mkdir()
    (root / "site/404.html").write_text("404\n", encoding="utf-8")
    if version is not None:
        pkg = root / "plugins/roxabi-forge/package.json"
        pkg.parent.mkdir(parents=True)
        pkg.write_text(json.dumps({"name": "roxabi-forge", "version": version}), encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "engine")
    return _git(root, "rev-parse", "HEAD")


def _prod(stamp: str | None = "", *, has_deployment: bool = True) -> dict:
    return {"ok": True, "has_deployment": has_deployment, "stamp": stamp}


class ParseStampTests(unittest.TestCase):
    def test_release_and_dev_stamps(self) -> None:
        rel = parse_stamp("roxabi-forge/v1.10.2")
        self.assertEqual((1, 10, 2), rel["base"])
        self.assertEqual("", rel["dev"])
        dev = parse_stamp("  roxabi-forge/v1.1.0+dev.a1b2c3d\n")
        self.assertEqual("1.1.0", dev["version"])
        self.assertEqual("+dev.a1b2c3d", dev["dev"])

    def test_anything_else_is_not_a_stamp(self) -> None:
        # A dashboard or git-triggered deploy carries an arbitrary commit
        # message; reading a version out of it would invent a production engine.
        for message in (
            "",
            None,
            42,
            "roxabi-forge/v1.1",
            "roxabi-forge/v1.1.0-rc1",
            "roxabi-forge/v1.1.0+dev.",
            "roxabi-forge/v1.1.0+dev.XYZ",
            "roxabi-forge/1.1.0",
            "deploy roxabi-forge/v1.1.0",
            "roxabi-forge/v1.1.0 hotfix",
            "other-forge/v1.1.0",
        ):
            with self.subTest(message=message):
                self.assertIsNone(parse_stamp(message))

    def test_format_round_trips(self) -> None:
        self.assertEqual("roxabi-forge/v1.1.0", format_stamp("1.1.0"))
        self.assertEqual("roxabi-forge/v1.1.0+dev.abcdef0", format_stamp("1.1.0", "abcdef0"))
        self.assertEqual("1.1.0", parse_stamp(format_stamp("1.1.0", "abcdef0"))["version"])


class CompareTests(unittest.TestCase):
    def test_newer_production_is_a_refusal(self) -> None:
        for prod, local in (
            ("roxabi-forge/v2.0.0", "roxabi-forge/v1.9.9"),
            ("roxabi-forge/v1.2.0", "roxabi-forge/v1.1.9"),
            ("roxabi-forge/v1.1.1", "roxabi-forge/v1.1.0"),
            # Numeric, not lexical: "1.10.0" < "1.9.0" as strings.
            ("roxabi-forge/v1.10.0", "roxabi-forge/v1.9.0"),
            ("roxabi-forge/v1.2.0+dev.abc1234", "roxabi-forge/v1.1.0"),
            ("roxabi-forge/v1.2.0", "roxabi-forge/v1.1.0+dev.abc1234"),
        ):
            with self.subTest(prod=prod, local=local):
                r = compare(_prod(prod), local)
                self.assertEqual("newer_prod", r["verdict"])
                self.assertEqual("refuse", r["level"])
                self.assertEqual("update plugin", r["label"])

    def test_older_production_is_an_upgrade(self) -> None:
        r = compare(_prod("roxabi-forge/v1.9.0"), "roxabi-forge/v1.10.0")
        self.assertEqual(("upgrade", "info"), (r["verdict"], r["level"]))
        self.assertIn("1.9.0 → 1.10.0", r["message"])
        self.assertEqual("upgrade on next publish", r["label"])

    def test_same_version(self) -> None:
        cases = (
            ("roxabi-forge/v1.1.0", "roxabi-forge/v1.1.0", "aligned", "ok"),
            ("roxabi-forge/v1.1.0+dev.abc1234", "roxabi-forge/v1.1.0", "release_replaces_dev", "info"),
            ("roxabi-forge/v1.1.0", "roxabi-forge/v1.1.0+dev.abc1234", "dev_replaces_release", "warn"),
            ("roxabi-forge/v1.1.0+dev.abc1234", "roxabi-forge/v1.1.0+dev.def5678", "aligned", "info"),
            ("roxabi-forge/v1.1.0+dev.abc1234", "roxabi-forge/v1.1.0+dev.abc1234", "aligned", "ok"),
        )
        for prod, local, verdict, level in cases:
            with self.subTest(prod=prod, local=local):
                r = compare(_prod(prod), local)
                self.assertEqual((verdict, level), (r["verdict"], r["level"]))

    def test_unstamped_production_is_unknown_not_a_refusal(self) -> None:
        # Today's production: deployed before stamping, commit_message "".
        for stamp in ("", None, "Merge branch main", "roxabi-forge/vX"):
            with self.subTest(stamp=stamp):
                r = compare(_prod(stamp), "roxabi-forge/v1.1.0")
                self.assertEqual(("unknown", "warn"), (r["verdict"], r["level"]))
                self.assertIn("production engine version unknown", r["message"])
                self.assertIn("stamps it", r["message"])

    def test_project_without_deployment(self) -> None:
        r = compare(_prod("", has_deployment=False), "roxabi-forge/v1.1.0")
        self.assertEqual(("no_deployment", "info"), (r["verdict"], r["level"]))

    def test_malformed_local_stamp_is_a_caller_bug(self) -> None:
        with self.assertRaises(EngineError):
            compare(_prod("roxabi-forge/v1.0.0"), "1.1.0")


class GateTests(unittest.TestCase):
    NEWER = _prod("roxabi-forge/v1.2.0")
    LOCAL = "roxabi-forge/v1.1.0"

    def test_newer_production_refuses_with_update_commands(self) -> None:
        v = gate(self.NEWER, self.LOCAL)
        self.assertEqual("refuse", v["action"])
        self.assertIn("production runs roxabi-forge 1.2.0, this plugin is 1.1.0", v["message"])
        self.assertIn("update the plugin", v["message"])
        for cmd in UPDATE_COMMANDS:
            self.assertIn(cmd, v["message"])
        self.assertIn("--allow-engine-downgrade", v["message"])

    def test_update_commands_cover_both_harnesses(self) -> None:
        self.assertIn("claude plugin marketplace update roxabi-forge", UPDATE_COMMANDS)
        self.assertIn("claude plugin update roxabi-forge@roxabi-forge", UPDATE_COMMANDS)
        self.assertIn("omp plugin marketplace update roxabi-forge", UPDATE_COMMANDS)
        self.assertIn("omp plugin upgrade roxabi-forge@roxabi-forge", UPDATE_COMMANDS)

    def test_downgrade_refuses_in_a_dry_run_too(self) -> None:
        # A proven verdict: the dry run is a gate, like the hub guard's exit 3.
        self.assertEqual("refuse", gate(self.NEWER, self.LOCAL, dry_run=True)["action"])

    def test_allow_downgrade_lets_a_known_older_engine_through(self) -> None:
        v = gate(self.NEWER, self.LOCAL, allow_downgrade=True)
        self.assertEqual(("proceed", "warn"), (v["action"], v["level"]))
        self.assertIn("--allow-engine-downgrade", v["message"])

    def test_allow_unverified_does_not_lift_a_proven_downgrade(self) -> None:
        self.assertEqual("refuse", gate(self.NEWER, self.LOCAL, allow_unverified=True)["action"])

    def test_unreachable_api_fails_closed(self) -> None:
        for prod in (
            None,
            {},
            {"ok": False, "error_kind": "unreachable", "error": "timed out"},
            {"ok": False, "error_kind": "api_error", "error": "HTTP 403: denied"},
        ):
            with self.subTest(prod=prod):
                v = gate(prod, self.LOCAL)
                self.assertEqual("refuse", v["action"])
                self.assertIn("unverified", v["message"])
                self.assertIn("--allow-unverified", v["message"])

    def test_allow_downgrade_does_not_lift_an_unreachable_api(self) -> None:
        prod = {"ok": False, "error": "timed out"}
        self.assertEqual("refuse", gate(prod, self.LOCAL, allow_downgrade=True)["action"])

    def test_allow_unverified_lifts_an_unreachable_api(self) -> None:
        v = gate({"ok": False, "error": "timed out"}, self.LOCAL, allow_unverified=True)
        self.assertEqual(("proceed", "warn"), (v["action"], v["level"]))
        self.assertIn("timed out", v["message"])

    def test_unreachable_api_in_a_dry_run_is_a_would_refuse_warning(self) -> None:
        v = gate({"ok": False, "error": "timed out"}, self.LOCAL, dry_run=True)
        self.assertEqual(("proceed", "warn"), (v["action"], v["level"]))
        self.assertIn("would refuse", v["message"])

    def test_non_refusing_verdicts_proceed(self) -> None:
        for prod, level in (
            (_prod("roxabi-forge/v1.0.0"), "info"),
            (_prod("roxabi-forge/v1.1.0"), "ok"),
            (_prod(""), "warn"),
            (_prod("", has_deployment=False), "info"),
        ):
            with self.subTest(prod=prod):
                v = gate(prod, self.LOCAL)
                self.assertEqual(("proceed", level), (v["action"], v["level"]))


class ProductionStampTests(unittest.TestCase):
    CFG = {"pages_project": "forge-test", "cloudflare_account_id": "acct"}

    def _run(self, response: tuple) -> tuple[dict, list]:
        calls: list = []

        def fake(method, path, token, **_kw):
            calls.append((method, path))
            return response

        with patch("load_config.resolve_api_token", return_value="tok"), patch(
            "load_config.resolved_account_id", return_value="acct"
        ), patch("load_config._cf_api", side_effect=fake):
            return production_stamp(self.CFG), calls

    def test_reads_the_canonical_deployment_not_the_latest(self) -> None:
        body = {
            "success": True,
            "result": {
                "canonical_deployment": {
                    "id": "dep-prod",
                    "deployment_trigger": {
                        "metadata": {"commit_message": "roxabi-forge/v1.1.0", "commit_hash": "abc"}
                    },
                },
                # A preview deploy can be the latest; it is not production.
                "latest_deployment": {
                    "id": "dep-preview",
                    "deployment_trigger": {"metadata": {"commit_message": "roxabi-forge/v9.9.9"}},
                },
            },
        }
        got, calls = self._run((200, body, ""))
        self.assertEqual([("GET", "/accounts/acct/pages/projects/forge-test")], calls)
        self.assertEqual(
            {"ok": True, "has_deployment": True, "deployment_id": "dep-prod",
             "stamp": "roxabi-forge/v1.1.0", "commit_hash": "abc"},
            got,
        )

    def test_unstamped_production_is_read_as_an_empty_stamp(self) -> None:
        body = {
            "success": True,
            "result": {
                "canonical_deployment": {
                    "id": "dep-prod",
                    "deployment_trigger": {
                        "metadata": {"branch": "main", "commit_hash": "", "commit_message": "", "commit_dirty": True}
                    },
                }
            },
        }
        got, _ = self._run((200, body, ""))
        self.assertTrue(got["ok"])
        self.assertEqual("", got["stamp"])
        self.assertEqual("unknown", compare(got, "roxabi-forge/v1.1.0")["verdict"])

    def test_project_without_canonical_deployment(self) -> None:
        got, _ = self._run((200, {"success": True, "result": {"canonical_deployment": None}}, ""))
        self.assertEqual((True, False), (got["ok"], got["has_deployment"]))

    def test_api_failures_are_not_ok(self) -> None:
        unreachable, _ = self._run((0, None, "timed out"))
        self.assertEqual(("unreachable", False), (unreachable["error_kind"], unreachable["ok"]))
        denied, _ = self._run((403, {"success": False, "errors": [{"message": "denied"}]}, ""))
        self.assertEqual("api_error", denied["error_kind"])
        self.assertIn("denied", denied["error"])

    def test_missing_credentials_never_call_the_api(self) -> None:
        with patch("load_config.resolve_api_token", return_value=""), patch(
            "load_config._cf_api"
        ) as spy:
            got = production_stamp(self.CFG)
        self.assertEqual("auth_missing", got["error_kind"])
        self.assertEqual(0, spy.call_count)


class ResolveEngineTests(unittest.TestCase):
    def test_plugin_version_is_the_manifest_version(self) -> None:
        # The tag publish clones is derived from this; it must be the version
        # check_plugin_versions.py keeps consistent across every manifest.
        canon = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertEqual(canon, read_plugin_version())

    def test_empty_or_url_is_release_mode_on_the_plugin_tag(self) -> None:
        for repo, source in (("", CANONICAL), ("  ", CANONICAL),
                             ("https://example.invalid/forge.git", "https://example.invalid/forge.git")):
            with self.subTest(repo=repo):
                eng = resolve_engine(repo, plugin_version="1.4.2")
                self.assertEqual("release", eng["mode"])
                self.assertEqual(source, eng["source"])
                self.assertEqual("roxabi-forge/v1.4.2", eng["ref"])
                self.assertEqual("roxabi-forge/v1.4.2", eng["stamp"])
                self.assertFalse(eng["dirty"])

    def test_matching_checkout_is_dev_mode_stamped_with_its_head(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "engine"
            sha = _checkout(root, "1.4.2")
            (root / "scratch.txt").write_text("x\n", encoding="utf-8")
            eng = resolve_engine(str(root), plugin_version="1.4.2")
        self.assertEqual("dev", eng["mode"])
        self.assertEqual(sha, eng["sha"])
        self.assertEqual(f"roxabi-forge/v1.4.2+dev.{sha[:7]}", eng["stamp"])
        self.assertTrue(eng["dirty"])
        self.assertEqual(1, eng["uncommitted"])
        self.assertIsNone(eng["pushed"])  # no upstream configured

    def test_version_is_read_from_head_not_the_worktree(self) -> None:
        # git archive HEAD is what ships; an uncommitted bump must not relabel it.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "engine"
            _checkout(root, "1.4.2")
            (root / "plugins/roxabi-forge/package.json").write_text(
                json.dumps({"version": "9.9.9"}), encoding="utf-8"
            )
            eng = resolve_engine(str(root), plugin_version="1.4.2")
        self.assertEqual("1.4.2", eng["version"])

    def test_mismatched_checkout_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "engine"
            _checkout(root, "1.3.0")
            with patch("load_config.detect_engine_checkout", return_value=None):
                with self.assertRaises(EngineError) as ctx:
                    resolve_engine(str(root), plugin_version="1.4.2")
        msg = str(ctx.exception)
        self.assertIn("1.3.0", msg)
        self.assertIn("1.4.2", msg)

    def test_mismatch_is_allowed_when_publish_runs_from_that_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "engine"
            _checkout(root, "1.3.0")
            with patch("load_config.detect_engine_checkout", return_value=str(root.resolve())):
                eng = resolve_engine(str(root), plugin_version="1.4.2")
        self.assertEqual("roxabi-forge/v1.3.0", eng["stamp"].split("+")[0])

    def test_unusable_paths_are_refused_never_cloned(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plain = Path(td) / "plain"
            plain.mkdir()
            nopkg = Path(td) / "nopkg"
            _checkout(nopkg, None)
            unborn = Path(td) / "unborn"
            unborn.mkdir()
            _git(unborn, "init", "-q")
            for path, needle in (
                (Path(td) / "missing", "not found"),
                (plain, "not a git work tree"),
                (unborn, "no commit"),
                (nopkg, "package.json"),
            ):
                with self.subTest(path=path.name):
                    with self.assertRaises(EngineError) as ctx:
                        resolve_engine(str(path), plugin_version="1.4.2")
                    self.assertIn(needle, str(ctx.exception))

    def test_pushed_reflects_the_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            remote = Path(td) / "remote.git"
            remote.mkdir()
            _git(remote, "init", "-q", "--bare")
            root = Path(td) / "engine"
            _checkout(root, "1.4.2")
            _git(root, "remote", "add", "origin", str(remote))
            _git(root, "push", "-q", "-u", "origin", "HEAD:main")
            _git(root, "branch", "-q", "--set-upstream-to=origin/main")
            pushed = resolve_engine(str(root), plugin_version="1.4.2")
            (root / "site/404.html").write_text("changed\n", encoding="utf-8")
            _git(root, "-c", "commit.gpgsign=false", "commit", "-q", "-am", "local only")
            ahead = resolve_engine(str(root), plugin_version="1.4.2")
        self.assertTrue(pushed["pushed"])
        self.assertFalse(ahead["pushed"])
        self.assertTrue(any("not on its upstream" in w for w in engine_drift.dev_warnings(ahead)))


class CliTests(unittest.TestCase):
    SCRIPT = LIB / "engine_drift.py"

    def _gate_in_bash(self, prod_json: str, *flags: str) -> subprocess.CompletedProcess:
        # Exactly how publish.sh consumes it: eval the assignments.
        script = (
            'out=$(printf "%s" "$PROD" | python3 "$SCRIPT" gate --stamp roxabi-forge/v1.1.0 "$@")'
            ' || exit 9; eval "$out"; printf "%s|%s\\n%s" "$DRIFT_ACTION" "$DRIFT_LEVEL" "$DRIFT_MESSAGE"'
        )
        return subprocess.run(
            ["bash", "-c", script, "gate", *flags],
            capture_output=True,
            text=True,
            env={**os.environ, "PROD": prod_json, "SCRIPT": str(self.SCRIPT)},
            check=False,
        )

    def test_gate_output_is_inert_under_eval(self) -> None:
        # Error text comes from the Cloudflare API; eval must never run it.
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / "pwned"
            hostile = f"x'; touch {marker}; echo '$(touch {marker})`touch {marker}`"
            proc = self._gate_in_bash(json.dumps({"ok": False, "error": hostile}))
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertFalse(marker.exists())
        self.assertTrue(proc.stdout.startswith("refuse|refuse\n"), proc.stdout)
        self.assertIn(hostile, proc.stdout)

    def test_unparseable_prod_json_fails_closed(self) -> None:
        for raw in ("", "not json", "[1, 2]"):
            with self.subTest(raw=raw):
                proc = self._gate_in_bash(raw)
                self.assertTrue(proc.stdout.startswith("refuse|refuse"), proc.stdout)

    def test_flags_reach_the_policy(self) -> None:
        newer = json.dumps(_prod("roxabi-forge/v1.2.0"))
        self.assertTrue(self._gate_in_bash(newer).stdout.startswith("refuse|"))
        self.assertTrue(
            self._gate_in_bash(newer, "--allow-downgrade").stdout.startswith("proceed|warn")
        )

    def test_resolve_reports_errors_as_an_assignment(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(self.SCRIPT), "resolve", "--forge-repo", "/nonexistent/engine"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("ENGINE_ERROR=", proc.stdout)
        self.assertIn("not found", proc.stdout)
        self.assertNotIn("ENGINE_MODE", proc.stdout)


if __name__ == "__main__":
    unittest.main()
