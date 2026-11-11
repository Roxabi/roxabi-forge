#!/usr/bin/env python3
"""Owner-availability probe: fail closed before mint, and never roll back.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "probe_owner_availability.py"

_spec = importlib.util.spec_from_file_location("probe_owner_availability", SCRIPT)
assert _spec is not None and _spec.loader is not None
probe_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe_mod)

probe_owner_availability = probe_mod.probe_owner_availability
ProbeError = probe_mod.ProbeError

_UPLOAD_JWT = "upload-jwt-fixture"
_CHECK_MISSING = "/pages/assets/check-missing"
_ASSET = "/asset-owners.json"


def _id32(label: str) -> str:
    digest = hashlib.sha256(
        b"g1b-owner-availability-fixture\0" + label.encode("ascii")
    )
    return digest.hexdigest()[:32]


def _target(**over: str) -> dict:
    base = {
        "account_id": _id32("account"),
        "project": "fixture-owners",
        "public_host": "owners.fixture.example",
        "production_branch": "production",
        "source_deployment_id": "src-hist-fixture",
        "expected_file_hash": _id32("asset-owners"),
        "expected_canonical_id": "canon-live-fixture",
        "expected_latest_id": "latest-live-fixture",
    }
    base.update(over)
    return base


def _seg(value: str) -> str:
    return quote(value, safe="")


def _project_path(target: dict) -> str:
    return "/accounts/%s/pages/projects/%s" % (
        _seg(target["account_id"]),
        _seg(target["project"]),
    )


def _files_path(target: dict) -> str:
    return "%s/deployments/%s/files" % (
        _project_path(target),
        _seg(target["source_deployment_id"]),
    )


def _token_path(target: dict) -> str:
    return _project_path(target) + "/upload-token"


def _ok(result: object) -> tuple[int, bytes]:
    payload = {
        "success": True,
        "errors": [],
        "messages": [],
        "result": result,
    }
    return 200, json.dumps(payload).encode("utf-8")


def _project(target: dict, **over: object) -> dict:
    body = {
        "name": target["project"],
        "production_branch": target["production_branch"],
        "subdomain": "not-the-approved-host",
        "domains": [target["public_host"], "fixture.pages.dev"],
        "canonical_deployment": {
            "id": target["expected_canonical_id"],
            "environment": "production",
        },
        "latest_deployment": {
            "id": target["expected_latest_id"],
            "environment": "preview",
        },
    }
    body.update(over)
    return body


def _files(target: dict, *, mapping: dict | None = None) -> dict:
    files = {
        _ASSET: target["expected_file_hash"],
        "/manifest.json": _id32("manifest-neighbor"),
    }
    if mapping is not None:
        files = mapping
    return {"id": target["source_deployment_id"], "files": files}


def _records_drift(exc: BaseException) -> bool:
    if getattr(exc, "drift", None) is True:
        return True
    parts = [str(exc)]
    for name in ("code", "kind", "reason"):
        parts.append(str(getattr(exc, name, "")))
    diagnostics = getattr(exc, "diagnostics", None)
    if isinstance(diagnostics, dict):
        parts.append(json.dumps(diagnostics, sort_keys=True))
    return "drift" in " ".join(parts).lower()


def _mentions(exc: BaseException, secret: str) -> bool:
    parts = [str(exc), repr(exc)]
    for name in dir(exc):
        if name.startswith("_"):
            continue
        try:
            parts.append(repr(getattr(exc, name)))
        except Exception:
            continue
    return secret in "\n".join(parts)


class _Transport:
    """In-memory Cloudflare stand-in. Responses never echo bearers."""

    def __init__(
        self,
        target: dict,
        *,
        projects: list,
        files: object,
        missing: object = (200, []),
        token: str | None = _UPLOAD_JWT,
    ) -> None:
        self.target = target
        self.projects = projects
        self.files = files
        self.missing = missing
        self.token = token
        self.calls: list[dict] = []
        self._project_i = 0

    def __call__(self, method, api_path, body=None, *, bearer=None):
        if not isinstance(method, str) or not isinstance(api_path, str):
            raise TypeError("request contract requires method and api_path strings")
        self.calls.append(
            {
                "method": method,
                "path": api_path,
                "body": body,
                "bearer": bearer,
            }
        )
        method_u = method.upper()
        if (
            "?" in api_path
            or api_path.startswith("http://")
            or api_path.startswith("https://")
        ):
            return 404, b""
        if method_u == "GET" and api_path == _project_path(self.target):
            return self._take_project()
        if method_u == "GET" and api_path == _files_path(self.target):
            return self._pack(self.files)
        if method_u == "GET" and api_path == _token_path(self.target):
            result = {} if self.token is None else {"jwt": self.token}
            return _ok(result)
        if method_u == "POST" and api_path == _CHECK_MISSING:
            return self._pack(self.missing)
        return 404, b""

    def _take_project(self) -> tuple[int, bytes]:
        item = self.projects[min(self._project_i, len(self.projects) - 1)]
        self._project_i += 1
        return self._pack(item)

    @staticmethod
    def _pack(item: object) -> tuple[int, bytes]:
        if (
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], int)
        ):
            status, payload = item
            if isinstance(payload, (bytes, bytearray)):
                return status, bytes(payload)
            if status != 200:
                return status, b""
            return _ok(payload)
        return _ok(item)


def _parsed_body(body: object) -> object:
    if isinstance(body, dict):
        return body
    if isinstance(body, bytes):
        return json.loads(body.decode("utf-8"))
    if isinstance(body, str):
        return json.loads(body)
    raise AssertionError(type(body).__name__)


def _posts(calls: list[dict]) -> list[dict]:
    return [call for call in calls if str(call["method"]).upper() == "POST"]


def _minted(calls: list[dict]) -> bool:
    for call in calls:
        path = str(call["path"])
        if path.rstrip("/").endswith("/upload-token"):
            return True
        if str(call["method"]).upper() == "POST":
            return True
    return False


def _rollback(calls: list[dict]) -> list[str]:
    bad = []
    for call in calls:
        method = str(call["method"]).upper()
        path = str(call["path"]).split("?", 1)[0]
        if method in {"DELETE", "PUT", "PATCH"}:
            bad.append(method + " " + path)
        elif method == "POST" and path != _CHECK_MISSING:
            bad.append(method + " " + path)
        elif "upsert-hashes" in path or path.rstrip("/").endswith("/upload"):
            bad.append(method + " " + path)
        elif "reanchor" in path or path.rstrip("/").endswith("/rollback"):
            bad.append(method + " " + path)
    return bad


class OwnerAvailabilityTests(unittest.TestCase):
    def _run(
        self,
        target: dict | None = None,
        *,
        execute: bool = False,
        projects: list | None = None,
        files: object | None = None,
        missing: object = (200, []),
        token: str | None = _UPLOAD_JWT,
        pass_execute: bool = True,
    ):
        target = _target() if target is None else target
        if projects is None:
            projects = [_project(target)]
        if files is None:
            files = _files(target)
        transport = _Transport(
            target,
            projects=projects,
            files=files,
            missing=missing,
            token=token,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        caught = None
        result = None
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                if pass_execute:
                    result = probe_owner_availability(
                        target, transport, execute=execute
                    )
                else:
                    result = probe_owner_availability(target, transport)
            except ProbeError as exc:
                caught = exc
        leaked = stdout.getvalue() + stderr.getvalue()
        return result, caught, transport, leaked

    def _assert_no_mint(self, transport: _Transport, label: str) -> None:
        self.assertFalse(_minted(transport.calls), label)
        self.assertEqual(_rollback(transport.calls), [], label)

    def _assert_quiet(self, leaked: str, target: dict) -> None:
        self.assertNotIn(_UPLOAD_JWT, leaked)
        self.assertNotIn(target["account_id"], leaked)
        self.assertNotIn(target["expected_file_hash"], leaked)

    def test_wrong_identity_branch_and_deployment_fail_before_mint(self) -> None:
        target = _target()
        project = _project(target)
        cases = {
            "project": _project(target, name="other-project"),
            "domain": _project(target, domains=["other.fixture.example"]),
            "host-suffix": _project(
                target,
                domains=["not-" + target["public_host"], "fixture.pages.dev"],
            ),
            "host-port": _project(target, domains=[target["public_host"] + ":443"]),
            "branch": _project(target, production_branch="main"),
            "branch-missing": {
                key: value
                for key, value in project.items()
                if key != "production_branch"
            },
            "canonical": _project(
                target,
                canonical_deployment={
                    "id": "other-canon-fixture",
                    "environment": "production",
                },
            ),
            "canonical-missing": _project(target, canonical_deployment=None),
            "latest": _project(
                target,
                latest_deployment={
                    "id": "other-latest-fixture",
                    "environment": "preview",
                },
            ),
            "latest-missing": _project(target, latest_deployment=None),
        }
        for label, page in cases.items():
            with self.subTest(label=label):
                result, caught, transport, leaked = self._run(
                    target, execute=True, projects=[page]
                )
                self.assertIsNone(result)
                self.assertIsInstance(caught, ProbeError)
                self._assert_no_mint(transport, label)
                self._assert_quiet(leaked, target)
                self.assertFalse(_mentions(caught, _UPLOAD_JWT))

    def test_hash_mismatch_or_malformed_map_fails_before_mint(self) -> None:
        target = _target()
        other = _id32("other-file")
        cases = {
            "mismatch": _files(
                target,
                mapping={
                    _ASSET: other,
                    "/manifest.json": _id32("manifest-neighbor"),
                },
            ),
            "missing-key": _files(
                target, mapping={"/manifest.json": target["expected_file_hash"]}
            ),
            "relative-key": _files(
                target, mapping={"asset-owners.json": target["expected_file_hash"]}
            ),
            "list-shape": {"id": target["source_deployment_id"], "files": []},
            "non-string-hash": _files(
                target, mapping={_ASSET: [target["expected_file_hash"]]}
            ),
            "raw-json": (200, b"{"),
            "rejected": (200, b'{"success": false, "result": {}}'),
            "http": (500, b""),
        }
        for label, files in cases.items():
            with self.subTest(label=label):
                _result, caught, transport, leaked = self._run(
                    target, execute=True, files=files
                )
                self.assertIsInstance(caught, ProbeError)
                self._assert_no_mint(transport, label)
                self._assert_quiet(leaked, target)

    def test_unsafe_target_makes_no_request(self) -> None:
        valid = _target()
        cases = {
            "account": {**valid, "account_id": "not-an-account"},
            "hash-case": {
                **valid,
                "expected_file_hash": valid["expected_file_hash"].upper(),
            },
            "hash-short": {
                **valid,
                "expected_file_hash": valid["expected_file_hash"][:-1],
            },
            "host-url": {**valid, "public_host": "https://" + valid["public_host"]},
            "project-slash": {**valid, "project": "fixture/owners"},
            "deployment-dotdot": {**valid, "source_deployment_id": "../other"},
            "missing-key": {
                key: value for key, value in valid.items() if key != "project"
            },
            "extra-key": {**valid, "namespace_id": "not-used"},
        }
        for label, target in cases.items():
            with self.subTest(label=label):
                _result, caught, transport, leaked = self._run(
                    target, execute=True, projects=[_project(valid)], files=_files(valid)
                )
                self.assertIsInstance(caught, ProbeError)
                self.assertEqual(transport.calls, [])
                self._assert_quiet(leaked, valid)

    def test_default_preflight_does_not_mutate(self) -> None:
        target = _target()
        result, caught, transport, leaked = self._run(target, pass_execute=False)
        self.assertIsNone(caught)
        self.assertIsInstance(result, dict)
        self.assertIn("availability", result)
        self.assertIsNone(result["availability"])
        self._assert_no_mint(transport, "preflight")
        self.assertTrue(transport.calls)
        self.assertTrue(all(call["bearer"] is None for call in transport.calls))
        self._assert_quiet(leaked, target)
        methods = {str(call["method"]).upper() for call in transport.calls}
        self.assertEqual(methods, {"GET"})
        self.assertIn(_files_path(target), [call["path"] for call in transport.calls])
        mismatched = _files(
            target, mapping={"/manifest.json": target["expected_file_hash"]}
        )
        bad, bad_err, bad_io, bad_out = self._run(
            target, pass_execute=False, files=mismatched
        )
        self.assertIsNone(bad)
        self.assertIsInstance(bad_err, ProbeError)
        self._assert_no_mint(bad_io, "preflight-mismatch")
        self._assert_quiet(bad_out, target)

    def _assert_probe_calls(self, transport: _Transport, target: dict) -> None:
        self.assertEqual(_rollback(transport.calls), [])
        posts = _posts(transport.calls)
        self.assertEqual(len(posts), 1)
        post = posts[0]
        self.assertEqual(post["path"], _CHECK_MISSING)
        self.assertTrue(post["bearer"] == _UPLOAD_JWT)
        body = _parsed_body(post["body"])
        self.assertIsInstance(body, dict)
        self.assertEqual(list(body), ["hashes"])
        self.assertEqual(body["hashes"], [target["expected_file_hash"]])
        self.assertNotIn(_id32("manifest-neighbor"), body["hashes"])
        admin = [call for call in transport.calls if call is not post]
        self.assertTrue(all(call["bearer"] is None for call in admin))
        paths = [call["path"] for call in transport.calls]
        self.assertIn(_files_path(target), paths)
        canonical_files = "%s/deployments/%s/files" % (
            _project_path(target),
            _seg(target["expected_canonical_id"]),
        )
        self.assertNotIn(canonical_files, paths)
        project_at = [
            index
            for index, path in enumerate(paths)
            if path == _project_path(target)
        ]
        post_at = paths.index(_CHECK_MISSING)
        self.assertGreaterEqual(len(project_at), 2)
        self.assertGreater(max(project_at), post_at)

    def test_available_and_missing_are_distinct(self) -> None:
        target = _target()
        available, available_err, available_io, available_out = self._run(
            target, execute=True, missing=(200, [])
        )
        missing, missing_err, missing_io, missing_out = self._run(
            target,
            execute=True,
            missing=(200, [target["expected_file_hash"]]),
        )
        self.assertIsNone(available_err)
        self.assertIsNone(missing_err)
        self.assertEqual(available["availability"], "available")
        self.assertEqual(missing["availability"], "missing")
        self.assertNotEqual(available["availability"], missing["availability"])
        self.assertNotIn(_UPLOAD_JWT, json.dumps(available, default=str))
        self.assertNotIn(_UPLOAD_JWT, json.dumps(missing, default=str))
        self._assert_probe_calls(available_io, target)
        self._assert_probe_calls(missing_io, target)
        self._assert_quiet(available_out, target)
        self._assert_quiet(missing_out, target)

    def test_malformed_or_foreign_missing_hash_fails_closed(self) -> None:
        target = _target()
        foreign = _id32("foreign-missing")
        cases = {
            "foreign": (200, [foreign]),
            "foreign-plus-expected": (
                200,
                [target["expected_file_hash"], foreign],
            ),
            "duplicate": (
                200,
                [target["expected_file_hash"], target["expected_file_hash"]],
            ),
            "upper": (200, [target["expected_file_hash"].upper()]),
            "padded": (200, [" " + target["expected_file_hash"]]),
            "string": (200, target["expected_file_hash"]),
            "object": (200, {"hashes": []}),
            "null": (200, None),
            "rejected": (200, b'{"success": false, "result": []}'),
            "raw-json": (200, b"{"),
            "http": (500, b""),
            "empty-jwt": "empty-jwt",
        }
        for label, missing in cases.items():
            with self.subTest(label=label):
                token = "" if label == "empty-jwt" else _UPLOAD_JWT
                payload = (200, []) if label == "empty-jwt" else missing
                result, caught, transport, leaked = self._run(
                    target, execute=True, missing=payload, token=token
                )
                self.assertIsNone(result)
                self.assertIsInstance(caught, ProbeError)
                self.assertEqual(_rollback(transport.calls), [])
                self.assertLessEqual(len(_posts(transport.calls)), 1)
                if label == "empty-jwt":
                    self.assertEqual(_posts(transport.calls), [])
                    self.assertTrue(
                        any(
                            str(call["path"]).rstrip("/").endswith("/upload-token")
                            for call in transport.calls
                        )
                    )
                self._assert_quiet(leaked, target)
                self.assertFalse(_mentions(caught, _UPLOAD_JWT))
                self.assertFalse(_mentions(caught, foreign))

    def test_post_probe_drift_fails_without_rollback(self) -> None:
        target = _target()
        first = _project(target)
        drifted = {
            "canonical": _project(
                target,
                canonical_deployment={
                    "id": "canon-moved-fixture",
                    "environment": "production",
                },
            ),
            "latest": _project(
                target,
                latest_deployment={
                    "id": "latest-moved-fixture",
                    "environment": "preview",
                },
            ),
            "name": _project(target, name="renamed-fixture"),
            "host": _project(target, domains=["other.fixture.example"]),
            "branch": _project(target, production_branch="main"),
        }
        outcomes = ((200, []), (200, [target["expected_file_hash"]]))
        for label, page in drifted.items():
            for missing in outcomes:
                with self.subTest(label=label, available=missing[1] == []):
                    result, caught, transport, leaked = self._run(
                        target,
                        execute=True,
                        projects=[first, page],
                        missing=missing,
                    )
                    self.assertIsNone(result)
                    self.assertIsInstance(caught, ProbeError)
                    self.assertTrue(_records_drift(caught))
                    self.assertEqual(_rollback(transport.calls), [])
                    posts = _posts(transport.calls)
                    self.assertEqual(len(posts), 1)
                    self.assertEqual(posts[0]["path"], _CHECK_MISSING)
                    self._assert_quiet(leaked, target)
                    self.assertFalse(_mentions(caught, _UPLOAD_JWT))

        result, caught, transport, leaked = self._run(
            target,
            execute=True,
            projects=[first, (500, b"")],
            missing=(200, []),
        )
        self.assertIsNone(result)
        self.assertIsInstance(caught, ProbeError)
        self.assertEqual(_rollback(transport.calls), [])
        self.assertEqual(len(_posts(transport.calls)), 1)
        self._assert_quiet(leaked, target)


class OwnerAvailabilityCliInputTests(unittest.TestCase):
    """Exercise private input guards through the public CLI without network."""

    def _invoke(self, config_text: str, record_text: str):
        target = _target()
        with tempfile.TemporaryDirectory(prefix="owner-probe-") as directory:
            root = Path(directory)
            root.chmod(0o700)
            config = root / "config.json"
            record = root / "record.json"
            env_file = root / "forge.env"
            output = root / "evidence.json"
            for path, text in (
                (config, config_text),
                (record, record_text),
                (
                    env_file,
                    "CLOUDFLARE_ACCOUNT_ID=%s\nCLOUDFLARE_API_TOKEN=fixture-admin-token\n"
                    % target["account_id"],
                ),
            ):
                path.write_text(text, encoding="utf-8")
                path.chmod(0o600)

            calls = []

            class Response(io.BytesIO):
                status = 200

            class Opener:
                def open(self, request, timeout=None):
                    path = request.full_url.removeprefix(
                        "https://api.cloudflare.com/client/v4"
                    )
                    calls.append((request.get_method(), path))
                    if path == _project_path(target):
                        return Response(_ok(_project(target))[1])
                    if path == _files_path(target):
                        return Response(_ok(_files(target))[1])
                    raise AssertionError("Unexpected HTTP request")

            stdout, stderr = io.StringIO(), io.StringIO()
            environment = {
                "PATH": os.environ.get("PATH", ""),
                "CLOUDFLARE_ACCOUNT_ID": target["account_id"],
            }
            args = [
                "--target-record", str(record),
                "--config", str(config),
                "--env", str(env_file),
                "--output", str(output),
            ]
            with (
                patch.dict(os.environ, environment, clear=True),
                patch("urllib.request.build_opener", return_value=Opener()),
                patch("socket.socket.connect", side_effect=AssertionError("network forbidden")),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                status = probe_mod.main(args)
            evidence = json.loads(output.read_text()) if output.exists() else None
            return status, stdout.getvalue(), stderr.getvalue(), calls, evidence

    def _valid_inputs(self):
        target = _target()
        config = {
            "pages_project": target["project"],
            "public_host": target["public_host"],
            "cloudflare_account_id": target["account_id"],
        }
        return config, target

    def _assert_valid_control(self, config: dict, record: dict) -> None:
        status, _stdout, _stderr, calls, evidence = self._invoke(
            json.dumps(config), json.dumps(record)
        )
        self.assertEqual(status, 0)
        self.assertEqual(
            calls,
            [("GET", _project_path(record)), ("GET", _files_path(record))],
        )
        self.assertIsInstance(evidence, dict)
        self.assertEqual(evidence["outcome"], "preflight")

    def test_cli_rejects_nonexact_configured_identity(self) -> None:
        config, record = self._valid_inputs()
        self._assert_valid_control(config, record)
        cases = {
            "host-port": {"public_host": record["public_host"] + ":443"},
            "host-query": {"public_host": record["public_host"] + "?x"},
            "host-path-query": {"public_host": record["public_host"] + "/?x"},
            "project-whitespace": {"pages_project": " " + record["project"] + " "},
        }
        for label, change in cases.items():
            with self.subTest(label=label):
                status, stdout, stderr, calls, evidence = self._invoke(
                    json.dumps({**config, **change}), json.dumps(record)
                )
                self.assertNotEqual(status, 0)
                self.assertIn("config", stderr.lower())
                self.assertEqual(stdout, "")
                self.assertEqual(calls, [])
                self.assertIsNone(evidence)

    def test_cli_rejects_duplicate_private_json_keys(self) -> None:
        config, record = self._valid_inputs()
        self._assert_valid_control(config, record)
        config_json = json.dumps(config)
        record_json = json.dumps(record)
        duplicate_config = config_json[:-1] + ", " + json.dumps(
            "public_host"
        ) + ": " + json.dumps(config["public_host"]) + "}"
        duplicate_record = record_json[:-1] + ", " + json.dumps(
            "project"
        ) + ": " + json.dumps(record["project"]) + "}"
        for label, config_text, record_text in (
            ("config", duplicate_config, record_json),
            ("record", config_json, duplicate_record),
        ):
            with self.subTest(label=label):
                status, stdout, stderr, calls, evidence = self._invoke(
                    config_text, record_text
                )
                self.assertNotEqual(status, 0)
                self.assertIn(label, stderr.lower())
                self.assertEqual(stdout, "")
                self.assertEqual(calls, [])
                self.assertIsNone(evidence)


if __name__ == "__main__":
    unittest.main()