#!/usr/bin/env python3
"""Offline, injected-transport tests for disposable owner-byte recovery."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "recover_owner_bytes", ROOT / "scripts" / "recover_owner_bytes.py"
)
assert _spec is not None and _spec.loader is not None
recovery = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(recovery)


def _hash(data, ext):
    return hashlib.sha256(base64.b64encode(data) + ext.encode("ascii")).hexdigest()[:32]


def _envelope(result, status=200):
    return status, json.dumps({"success": True, "result": result}).encode("utf-8")


def _admin(status, body, *, dispatched=True, content_type=None):
    if not dispatched:
        return recovery.AdminObservation(False, None, "absent", b"")
    if content_type is None:
        content_type = "json" if isinstance(status, int) and 200 <= status < 300 else "absent"
    return recovery.AdminObservation(True, status, content_type, body)


_ENV_NAME = "CLOUDFLARE_" + "API_TOKEN"
CANARY_NOTE = "Authorization Bearer " + _ENV_NAME + " RAW_BODY_CANARY synthetic-token-shape"
CANARIES = ("Authorization", "Bearer", _ENV_NAME, "RAW_BODY_CANARY", "synthetic-token-shape")


HISTORICAL = b'{"fixture":"historical-owners"}'
TEMPLATE = (b'"__G1B_ROUTE__" "__G1B_INTERNAL__" '
            b'"__G1B_TOKEN_SHA256__" __G1B_NOT_AFTER_MS__')


def _record():
    target = {
        "account_id": _hash(b"fixture-account", "json"),
        "project": "source-fixture",
        "public_host": "source.example.invalid",
        "production_branch": "main",
        "source_deployment_id": "source-history",
        "expected_file_hash": _hash(HISTORICAL, "json"),
        "expected_canonical_id": "source-canonical",
        "expected_latest_id": "source-latest",
    }
    return {
        "source": target,
        "approved_source_sha": hashlib.sha256(b"source fixture").hexdigest()[:40],
        "disposable_project": "owner-disposable-fixture",
        "worker_template_sha256": hashlib.sha256(TEMPLATE).hexdigest(),
        "compatibility_date": "2024-01-01",
        "hash_calibration": [
            {"path": "/fixture/calibration-%d.json" % i, "extension": "json",
             "expected_pages_hash": _hash(("calibration-%d" % i).encode("ascii"), "json")}
            for i in range(3)
        ],
        "bypass_residual_accepted": True,
        "provenance": "synthetic fixture",
    }


class Scenario:
    """Synthetic API universe; all callbacks are local and share an event log."""

    def __init__(self, *, collision=False, receipt_lost=False, malformed_receipt=False, cleanup_id=None,
                 missing_historical=False, bad_positive=False, mismatch=False,
                 persist_fails=False, cleanup_fails=False):
        self.record = _record()
        self.collision = collision
        self.receipt_lost = receipt_lost
        self.malformed_receipt = malformed_receipt
        self.cleanup_id = cleanup_id
        self.missing_historical = missing_historical
        self.bad_positive = bad_positive
        self.mismatch = mismatch
        self.persist_fails = persist_fails
        self.cleanup_fails = cleanup_fails
        self.events = []
        self.saved = {}
        self.checkpoints = []
        self.receipts = []
        self.on_admin = None
        self.canary_note = None
        self.created = False
        self.deleted = False
        self.deployments = 0
        self.manifests = []
        self.fixture = None
        self.page_counts = {}
        self.rng_counter = 0

    def rng(self, n):
        self.rng_counter += 1
        return bytes([self.rng_counter % 256]) * n

    def source(self, method, path, body=None, *, bearer=None):
        self.events.append(("source", method, path))
        source = self.record["source"]
        project = "/accounts/%s/pages/projects/%s" % (
            source["account_id"], source["project"]
        )
        if method == "GET" and path == project:
            return _envelope({
                "name": source["project"],
                "production_branch": source["production_branch"],
                "domains": [source["public_host"]],
                "canonical_deployment": {"id": source["expected_canonical_id"]},
                "latest_deployment": {"id": source["expected_latest_id"]},
            })
        if method == "GET" and path == project + "/deployments/source-history/files":
            return _envelope({"files": {"/asset-owners.json": source["expected_file_hash"]}})
        if method == "GET" and path == project + "/upload-token":
            return _envelope({"jwt": "synthetic-source-upload-token"})
        if method == "POST" and path == "/pages/assets/check-missing":
            return _envelope([])
        return 404, b""

    def admin(self, method, path, body=None, *, bearer=None):
        self.events.append(("admin", method, path))
        if self.on_admin is not None:
            self.on_admin(method, path)
        source = self.record["source"]
        collection = "/accounts/%s/pages/projects" % source["account_id"]
        project = collection + "/" + self.record["disposable_project"]
        identity = {
            "id": "owned-project-fixture",
            "name": self.record["disposable_project"],
            "subdomain": "disposable-fixture.pages.dev",
            "deployment_configs": {
                "production": {"fail_open": False},
                "preview": {"fail_open": False},
            },
        }
        if method == "GET" and path == project:
            if self.deleted:
                return _admin(404, b"")
            if not self.created:
                return _admin(*_envelope(identity)) if self.collision else _admin(404, b"")
            if self.cleanup_id is not None:
                identity["id"] = self.cleanup_id
            return _admin(*_envelope(identity))
        if method == "POST" and path == collection:
            self.created = True
            if self.malformed_receipt:
                return _admin(*_envelope({"name": identity["name"]}, 201))
            if self.receipt_lost:
                return _admin(0, b"", dispatched=False)
            return _admin(*_envelope(identity, 201))
        if method == "DELETE" and path == project:
            if self.cleanup_fails:
                return _admin(500, b"")
            self.deleted = True
            return _admin(*_envelope({}))
        if method == "GET" and path == project + "/upload-token":
            return _admin(*_envelope({"jwt": "synthetic-disposable-upload-token"}))
        if method == "POST" and path == "/pages/assets/check-missing":
            hashes = body["hashes"]
            hist = source["expected_file_hash"]
            result = hashes if self.missing_historical else [item for item in hashes if item != hist]
            payload = {"success": True, "result": result}
            if self.canary_note:
                payload["note"] = self.canary_note
            return _admin(200, json.dumps(payload).encode("utf-8"))
        if method == "POST" and path == "/pages/assets/upload":
            self.fixture = base64.b64decode(body[0]["value"])
            return _admin(*_envelope({}))
        if method == "POST" and path == project + "/deployments":
            self.deployments += 1
            self.manifests.append(dict(body["manifest"]))
            return _admin(*_envelope({
                "url": "https://d%d.disposable-fixture.pages.dev" % self.deployments,
                "aliases": [],
            }, 201))
        return _admin(404, b"")

    def pages(self, host, path, headers, *, allowed_hosts):
        self.events.append(("pages", self.deployments, host, path, bool(headers)))
        count = self.page_counts.get(host, 0)
        self.page_counts[host] = count + 1
        if self.deployments == 1 and count == 0:
            return 200, {}, b"incorrect fixture" if self.bad_positive else self.fixture
        if self.deployments == 2 and count >= 4:
            return 200, {}, b"unverified fixture" if self.mismatch else HISTORICAL
        return 404, {"x-recovery-gate": "deny"}, b""

    def persist(self, name, data):
        self.events.append(("persist", name))
        if self.persist_fails:
            raise OSError("synthetic write failure")
        self.saved[name] = data
        return {"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def run(self, execute=True, now=None, checkpoint=None, receipt=None):
        def _checkpoint(name, data):
            if checkpoint is not None:
                checkpoint(name, data)
            else:
                self.checkpoints.append((name, data))

        def _receipt(name, data):
            if receipt is not None:
                receipt(name, data)
            else:
                self.receipts.append((name, data))

        return recovery.recover_owner_bytes(
            self.record, template=TEMPLATE, source_request=self.source,
            admin_request=self.admin, pages_get=self.pages, persist=self.persist,
            hasher=_hash, now=now or (lambda: 1_700_000_000), rng=self.rng,
            sleep=lambda _: None, execute=execute, checkpoint=_checkpoint, receipt=_receipt,
        )

    def deletes(self):
        return [event for event in self.events if event[:2] == ("admin", "DELETE")]


class RecoveryPolicyTests(unittest.TestCase):
    def test_default_is_offline(self):
        scenario = Scenario()
        result = scenario.run(execute=False)
        self.assertFalse(result["bytes_recovered"])
        self.assertEqual(scenario.events, [])

    def test_never_delete_without_ownership_or_matching_id(self):
        for options in (
            {"collision": True},
            {"receipt_lost": True},
            {"malformed_receipt": True},
            {"cleanup_id": "different-project-id", "missing_historical": True},
        ):
            with self.subTest(case=next(iter(options))):
                scenario = Scenario(**options)
                result = scenario.run()
                self.assertFalse(result["bytes_recovered"])
                self.assertEqual(scenario.deletes(), [])
                self.assertEqual(scenario.deployments, 0)

    def test_missing_historical_stops_before_deploy_and_cleans_owned_project(self):
        scenario = Scenario(missing_historical=True)
        result = scenario.run()
        self.assertFalse(result["bytes_recovered"])
        self.assertEqual(scenario.deployments, 0)
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertTrue(scenario.deleted)
        self.assertEqual(scenario.saved, {})

    def test_positive_proves_gate_before_negative_observations(self):
        scenario = Scenario(bad_positive=True)
        result = scenario.run()
        self.assertFalse(result["bytes_recovered"])
        self.assertEqual(scenario.deployments, 1)
        pages = [event for event in scenario.events if event[0] == "pages"]
        self.assertEqual(len(pages), 1)
        self.assertTrue(pages[0][4], "the first observation must be authenticated")
        self.assertEqual(len(scenario.deletes()), 1)

    def _assert_d1_only_cleaned(self, scenario, result):
        self.assertFalse(result["bytes_recovered"])
        self.assertEqual(scenario.deployments, 1)
        self.assertEqual(len(scenario.manifests), 1)
        for manifest in scenario.manifests:
            self.assertNotIn(scenario.record["source"]["expected_file_hash"], manifest.values())
        d1 = [event for event in scenario.events if event[:2] == ("pages", 1)]
        hosts = {event[2] for event in d1}
        self.assertEqual(len(hosts), 2)
        for host in hosts:
            observations = [event for event in d1 if event[2] == host]
            self.assertEqual([event[4] for event in observations], [True, False, True, False])
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertTrue(scenario.deleted)
        self.assertEqual(scenario.saved, {})

    def test_unaccepted_residual_blocks_historical_deployment(self):
        scenario = Scenario()
        scenario.record["bypass_residual_accepted"] = False
        result = scenario.run()
        self._assert_d1_only_cleaned(scenario, result)

    def test_expired_deadline_after_d1_blocks_historical_deployment(self):
        scenario = Scenario()

        def clock():
            d1 = [event for event in scenario.events if event[:2] == ("pages", 1)]
            if len(d1) >= 8:
                scenario.events.append(("clock_expired",))
                return 1_700_000_000 + 24 * 60 * 60
            return 1_700_000_000

        result = scenario.run(now=clock)
        self.assertIn(("clock_expired",), scenario.events)
        self._assert_d1_only_cleaned(scenario, result)

    def test_verified_bytes_saved_before_deleting_owned_project(self):
        scenario = Scenario()
        result = scenario.run()
        self.assertTrue(result["bytes_recovered"])
        self.assertFalse(result["g1b_closed"])
        self.assertEqual(scenario.saved.get("recovered-asset-owners.json"), HISTORICAL)
        self.assertEqual(len(scenario.deletes()), 1)
        saved_index = next(i for i, event in enumerate(scenario.events) if event[0] == "persist")
        delete_index = scenario.events.index(scenario.deletes()[0])
        self.assertLess(saved_index, delete_index)
        self.assertTrue(scenario.deleted)
        d1 = [event for event in scenario.events if event[:2] == ("pages", 1)]
        hosts = {event[2] for event in d1}
        self.assertEqual(len(hosts), 2)
        for host in hosts:
            observations = [event for event in d1 if event[2] == host]
            self.assertEqual([event[4] for event in observations], [True, False, True, False])

    def test_mismatched_download_is_saved_unverified_then_cleaned(self):
        scenario = Scenario(mismatch=True)
        result = scenario.run()
        self.assertFalse(result["bytes_recovered"])
        self.assertEqual(scenario.saved.get("unverified-download.bin"), b"unverified fixture")
        self.assertNotIn("recovered-asset-owners.json", scenario.saved)
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertLess(
            next(i for i, event in enumerate(scenario.events) if event[0] == "persist"),
            scenario.events.index(scenario.deletes()[0]),
        )

    def test_persistence_failure_still_cleans_owned_project(self):
        scenario = Scenario(persist_fails=True)
        result = scenario.run()
        self.assertFalse(result["bytes_recovered"])
        self.assertEqual(scenario.saved, {})
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertTrue(scenario.deleted)

    def test_failed_cleanup_is_reported_not_success(self):
        scenario = Scenario(cleanup_fails=True)
        result = scenario.run()
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertFalse(scenario.deleted)
        self.assertIn("cleanup_failed", result["outcome"])


def _private_dir():
    path = Path(tempfile.mkdtemp(prefix="g1b-recovery-"))
    path.chmod(0o700)
    return path


def _writers(directory):
    def checkpoint(name, data):
        recovery.stage1._write_private(directory / name, data)

    def receipt(name, data):
        recovery.stage1._write_private(directory / name, data)

    return checkpoint, receipt


def _checkpoint_rows(directory):
    rows = []
    for path in sorted(directory.glob("checkpoint-*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def _joined(directory):
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(directory.iterdir()) if path.is_file())


class _Headers:
    def __init__(self, mapping):
        self._mapping = dict(mapping)

    def items(self):
        return list(self._mapping.items())


class _SocketResponse:
    def __init__(self, status, body, headers):
        self.status = status
        self.headers = _Headers(headers)
        self._body = io.BytesIO(body)

    def read(self, n):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _UnreadBody:
    def __init__(self, status, headers):
        self.status = status
        self.headers = _Headers(headers)
        self._held = CANARY_NOTE.encode("ascii")

    def read(self, _n):
        raise OSError("body unavailable")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _ScriptedOpener:
    """Local socket stand-in. Snapshots the private dir at the next admin call."""

    def __init__(self, record, kind, directory):
        self.record = record
        self.kind = kind
        self.directory = directory
        self.calls = []
        self.created = False
        self.deleted = False
        self.fixture_hash = None
        self.at_cleanup = None
        self.snapshot_rows = None

    def open(self, req, timeout=None):
        method = req.get_method()
        path = req.full_url.split("/client/v4", 1)[-1]
        self.calls.append((method, path))
        source = self.record["source"]
        project = "/accounts/%s/pages/projects/%s" % (source["account_id"], self.record["disposable_project"])
        collection = "/accounts/%s/pages/projects" % source["account_id"]
        identity = {
            "id": "owned-project-fixture",
            "name": self.record["disposable_project"],
            "subdomain": "disposable-fixture.pages.dev",
            "deployment_configs": {"production": {"fail_open": False}, "preview": {"fail_open": False}},
        }
        if method == "GET" and path == project:
            if self.deleted:
                return _SocketResponse(404, b"", {})
            if self.created and any(item[1] == "/pages/assets/check-missing" for item in self.calls[:-1]):
                self.snapshot_rows = _checkpoint_rows(self.directory)
                self.at_cleanup = _joined(self.directory)
            if not self.created:
                return _SocketResponse(404, b"", {})
            return _SocketResponse(200, json.dumps({"success": True, "result": identity, "note": CANARY_NOTE}).encode("utf-8"), {"Content-Type": "application/json; charset=utf-8"})
        if method == "POST" and path == collection:
            self.created = True
            return _SocketResponse(201, json.dumps({"success": True, "result": identity, "note": CANARY_NOTE}).encode("utf-8"), {"Content-Type": "application/json"})
        if method == "GET" and path == project + "/upload-token":
            return _SocketResponse(200, json.dumps({"success": True, "result": {"jwt": "synthetic-disposable-upload-token"}, "note": CANARY_NOTE}).encode("utf-8"), {"Content-Type": "application/json"})
        if method == "POST" and path == "/pages/assets/check-missing":
            parsed = json.loads(req.data.decode("ascii"))
            self.fixture_hash = [item for item in parsed["hashes"] if item != source["expected_file_hash"]][0]
            return self._missing(req)
        if method == "DELETE" and path == project:
            self.deleted = True
            return _SocketResponse(200, json.dumps({"success": True, "result": {}, "note": CANARY_NOTE}).encode("utf-8"), {"Content-Type": "application/json"})
        return _SocketResponse(404, b"", {})

    def _missing(self, req):
        fixture = self.fixture_hash
        historical = self.record["source"]["expected_file_hash"]
        header = {"Content-Type": "application/json; charset=utf-8"}
        if self.kind == "other_missing":
            body = {"success": True, "result": [fixture, "zz"], "note": CANARY_NOTE}
        elif self.kind == "historical_listed":
            body = {"success": True, "result": [historical, fixture], "note": CANARY_NOTE}
        elif self.kind == "result_shape":
            body = {"success": True, "result": {"not": "a-list"}, "note": CANARY_NOTE}
        elif self.kind == "envelope_rejected":
            body = {"success": False, "result": [fixture], "note": CANARY_NOTE}
        elif self.kind == "envelope_not_object":
            return _SocketResponse(200, json.dumps([fixture, CANARY_NOTE]).encode("utf-8"), header)
        elif self.kind == "duplicate_key":
            raw = ('{"success":true,"success":true,"result":["%s"],"note":"%s"}' % (fixture, CANARY_NOTE)).encode("ascii")
            return _SocketResponse(200, raw, header)
        elif self.kind == "unreadable_json":
            return _SocketResponse(200, b"{not-json " + CANARY_NOTE.encode("ascii") + b"}", header)
        elif self.kind == "http_status":
            raise urllib.error.HTTPError(req.full_url, 500, "synthetic", {"Content-Type": "text/plain"}, io.BytesIO(CANARY_NOTE.encode("ascii")))
        elif self.kind == "body_read_failed":
            return _UnreadBody(200, header)
        else:
            raise AssertionError("unknown class")
        return _SocketResponse(200, json.dumps(body).encode("utf-8"), header)


class RecoveryEvidenceTests(unittest.TestCase):
    def _assert_quiet(self, text, record):
        source = record["source"]
        for canary in CANARIES:
            self.assertNotIn(canary, text)
        self.assertNotIn(source["expected_file_hash"], text)
        self.assertNotIn(source["account_id"], text)
        self.assertNotIn(source["source_deployment_id"], text)
        self.assertNotIn(source["public_host"], text)
        self.assertNotIn("charset", text)

    def test_each_stop_class_is_checkpointed_before_cleanup(self):
        kinds = (
            "other_missing",
            "historical_listed",
            "result_shape",
            "envelope_rejected",
            "envelope_not_object",
            "duplicate_key",
            "unreadable_json",
            "http_status",
        )
        for kind in kinds:
            with self.subTest(kind=kind):
                directory = _private_dir()
                try:
                    scenario = Scenario()
                    opener = _ScriptedOpener(scenario.record, kind, directory)
                    transport = recovery.disposable_transport(
                        "synthetic-admin-token",
                        scenario.record["source"]["account_id"],
                        scenario.record["disposable_project"],
                        scenario.record["source"]["project"],
                        opener=opener,
                    )
                    pages = []
                    checkpoint, receipt = _writers(directory)
                    result = recovery.recover_owner_bytes(
                        scenario.record, template=TEMPLATE, source_request=scenario.source,
                        admin_request=transport, pages_get=lambda *a, **k: pages.append(a),
                        persist=scenario.persist, hasher=_hash, now=lambda: 1_700_000_000,
                        rng=scenario.rng, sleep=lambda _n: None, execute=True,
                        checkpoint=checkpoint, receipt=receipt,
                    )
                    self.assertFalse(result["bytes_recovered"])
                    self.assertFalse(result["g1b_closed"])
                    self.assertIsNone(result["source_after"])
                    self.assertEqual(result["classification"], kind)
                    self.assertEqual(pages, [])
                    self.assertEqual(scenario.deployments, 0)
                    self.assertNotIn(("/pages/assets/upload",), [(item[1],) for item in opener.calls if item[1].endswith("/upload")])
                    upload_calls = [item for item in opener.calls if item[1] == "/pages/assets/upload" or item[1].endswith("/deployments")]
                    self.assertEqual(upload_calls, [])
                    project = "/accounts/%s/pages/projects/%s" % (
                        scenario.record["source"]["account_id"], scenario.record["disposable_project"]
                    )
                    self.assertEqual(opener.calls, [
                        ("GET", project),
                        ("POST", "/accounts/%s/pages/projects" % scenario.record["source"]["account_id"]),
                        ("GET", project + "/upload-token"),
                        ("POST", "/pages/assets/check-missing"),
                        ("GET", project),
                        ("DELETE", project),
                        ("GET", project),
                    ])
                    self.assertIsNotNone(opener.at_cleanup)
                    self._assert_quiet(opener.at_cleanup, scenario.record)
                    self.assertIsNotNone(opener.snapshot_rows)
                    rows = [row for row in opener.snapshot_rows if row.get("phase") == "classification"]
                    self.assertEqual([row["classification"] for row in rows], [kind])
                    self.assertEqual(rows[0]["fixture_hash"], opener.fixture_hash)
                    self.assertEqual(rows[0]["slot"], "cross_project")
                    self.assertEqual(rows[0]["phase_failure"], "parse" if kind in ("duplicate_key", "unreadable_json", "envelope_not_object") else "guard")
                    if kind == "http_status":
                        self.assertEqual(rows[0]["status"], 500)
                        self.assertEqual(rows[0]["content_type"], "other")
                    else:
                        self.assertEqual(rows[0]["status"], 200)
                        self.assertEqual(rows[0]["content_type"], "json")
                    if kind == "other_missing":
                        self.assertTrue(rows[0]["historical_present"])
                        self.assertFalse(rows[0]["fixture_missing"])
                    elif kind == "historical_listed":
                        self.assertFalse(rows[0]["historical_present"])
                        self.assertFalse(rows[0]["fixture_missing"])
                    else:
                        self.assertIsNone(rows[0]["historical_present"])
                        self.assertIsNone(rows[0]["fixture_missing"])
                    receipt_text = (directory / "recovery-evidence.json").read_text(encoding="utf-8")
                    self._assert_quiet(receipt_text, scenario.record)
                    self.assertIn('"bytes_recovered": false', receipt_text)
                finally:
                    shutil.rmtree(directory)

    def test_success_real_writer_checkpoints_before_upload(self):
        directory = _private_dir()
        try:
            scenario = Scenario()
            scenario.canary_note = CANARY_NOTE
            seen = {}

            def on_admin(method, path):
                if method == "POST" and path == "/pages/assets/upload" and "text" not in seen:
                    seen["text"] = _joined(directory)

            scenario.on_admin = on_admin
            checkpoint, receipt = _writers(directory)
            result = scenario.run(checkpoint=checkpoint, receipt=receipt)
            self.assertTrue(result["bytes_recovered"])
            self.assertFalse(result["g1b_closed"])
            self.assertEqual(result["classification"], "exact_fixture")
            self.assertIn('"classification":"exact_fixture"', seen["text"])
            self.assertIn(result["fixture_hash"], seen["text"])
            self._assert_quiet(seen["text"], scenario.record)
            receipt_text = (directory / "recovery-evidence.json").read_text(encoding="utf-8")
            self._assert_quiet(receipt_text, scenario.record)
            self.assertIn('"bytes_recovered": true', receipt_text)
            self.assertIn('"g1b_closed": false', receipt_text)
            self.assertLess(
                next(i for i, event in enumerate(scenario.events) if event[:2] == ("admin", "POST") and event[2] == "/pages/assets/upload"),
                scenario.events.index(scenario.deletes()[0]),
            )
        finally:
            shutil.rmtree(directory)

    def test_tuple_return_is_not_observed_http(self):
        scenario = Scenario()
        original = scenario.admin

        def admin(method, path, body=None, *, bearer=None):
            if path == "/pages/assets/check-missing":
                scenario.events.append(("admin", method, path))
                return (200, json.dumps({"success": True, "result": [scenario.record["source"]["expected_file_hash"]]}).encode("utf-8"))
            return original(method, path, body, bearer=bearer)

        scenario.admin = admin
        result = scenario.run()
        self.assertEqual(result["classification"], "not_observed")
        self.assertEqual(scenario.deployments, 0)
        cross = [row for row in result["calls"] if row["stage"] == "cross_project"]
        self.assertEqual(cross, [{"stage": "cross_project", "method": "POST", "dispatched": False, "status": "unknown", "content_type": "absent"}])
        self.assertFalse(result["bytes_recovered"])

    def test_checkpoint_failure_after_ownership_still_cleans_once(self):
        scenario = Scenario()

        def checkpoint(_name, data):
            if b'"slot":"upload_token"' in data:
                raise OSError("synthetic checkpoint failure")

        result = scenario.run(checkpoint=checkpoint)
        self.assertNotEqual(result["outcome"], "recovered")
        self.assertFalse(result["bytes_recovered"])
        self.assertEqual(result["failure"], "operation_failed")
        self.assertEqual(result["phase_failure"], "persist")
        self.assertNotIn("synthetic checkpoint failure", json.dumps(result))
        self.assertEqual(scenario.deployments, 0)
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertIsNone(result["source_after"])
        self.assertEqual([event for event in scenario.events if event[0] == "pages"], [])
        self.assertEqual([event for event in scenario.events if event[:2] == ("admin", "POST") and event[2] == "/pages/assets/upload"], [])

    def test_checkpoint_failure_before_ownership_makes_no_further_call(self):
        scenario = Scenario()

        def checkpoint(_name, _data):
            raise OSError("synthetic checkpoint failure")

        result = scenario.run(checkpoint=checkpoint)
        self.assertEqual(scenario.events, [])
        self.assertEqual(scenario.deletes(), [])
        self.assertNotEqual(result["outcome"], "recovered")
        self.assertEqual(result["phase_failure"], "persist")
        self.assertEqual(result["failure"], "operation_failed")
        self.assertNotIn("synthetic checkpoint failure", json.dumps(result))

    def test_receipt_failure_after_cleanup_does_not_delete_again(self):
        scenario = Scenario(missing_historical=True)
        seen = {}

        def receipt(_name, data):
            seen["data"] = data
            raise OSError("synthetic receipt failure")

        with self.assertRaises(OSError):
            scenario.run(receipt=receipt)
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertEqual(scenario.deployments, 0)
        self.assertNotIn(b'"bytes_recovered": true', seen["data"])
        self.assertNotIn(b'"g1b_closed": true', seen["data"])
        self.assertIn(b'"bytes_recovered": false', seen["data"])

    def test_budget_refuse_is_not_observed_http(self):
        directory = _private_dir()
        try:
            scenario = Scenario()
            opener = _ScriptedOpener(scenario.record, "other_missing", directory)
            transport = recovery.disposable_transport(
                "synthetic-admin-token",
                scenario.record["source"]["account_id"],
                scenario.record["disposable_project"],
                scenario.record["source"]["project"],
                opener=opener,
            )
            burned = transport(
                "POST", "/pages/assets/check-missing",
                {"hashes": ["a" * 32, "b" * 32]},
                bearer="synthetic-upload-token",
            )
            self.assertTrue(burned.dispatched)
            self.assertEqual(burned.status, 200)
            missing_opens = [item for item in opener.calls if item[1] == "/pages/assets/check-missing"]
            self.assertEqual(len(missing_opens), 1)
            checkpoint, receipt = _writers(directory)
            result = recovery.recover_owner_bytes(
                scenario.record, template=TEMPLATE, source_request=scenario.source,
                admin_request=transport, pages_get=scenario.pages, persist=scenario.persist,
                hasher=_hash, now=lambda: 1_700_000_000, rng=scenario.rng,
                sleep=lambda _n: None, execute=True, checkpoint=checkpoint, receipt=receipt,
            )
            self.assertEqual([item for item in opener.calls if item[1] == "/pages/assets/check-missing"], missing_opens)
            self.assertEqual(result["classification"], "not_observed")
            self.assertFalse(result["bytes_recovered"])
            self.assertEqual(scenario.deployments, 0)
            rows = [row for row in _checkpoint_rows(directory) if row.get("slot") == "cross_project" and row.get("phase") == "classification"]
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]["dispatched"])
            self.assertEqual(rows[0]["status"], "unknown")
            self.assertNotEqual(rows[0]["status"], 0)
            self.assertNotEqual(rows[0]["status"], 200)
            self._assert_quiet(_joined(directory), scenario.record)
        finally:
            shutil.rmtree(directory)

    def test_cleanup_journal_fault_does_not_resume_source_probe(self):
        scenario = Scenario()
        later = {"n": None}

        def checkpoint(_name, data):
            if b'"slot":"cleanup_' in data:
                later["n"] = len([event for event in scenario.events if event[0] == "source"])
                raise OSError("cleanup journal")

        result = scenario.run(checkpoint=checkpoint)
        self.assertIsNotNone(later["n"])
        self.assertGreater(later["n"], 0)
        self.assertTrue(result["bytes_recovered"])
        self.assertIsNotNone(result.get("file"))
        self.assertNotEqual(result["outcome"], "recovered")
        self.assertFalse(result["evidence_complete"])
        self.assertIsNone(result["source_after"])
        self.assertEqual(len([event for event in scenario.events if event[0] == "source"]), later["n"])
        self.assertEqual(len(scenario.deletes()), 1)

    def test_d2_reserve_is_rechecked_after_intent_write(self):
        scenario = Scenario()
        advanced = {"on": False}

        def checkpoint(_name, data):
            if b'"slot":"d2"' in data and b'"phase":"intent"' in data:
                advanced["on"] = True

        def now():
            if advanced["on"]:
                return 1_700_000_000 + 24 * 60 * 60
            return 1_700_000_000

        result = scenario.run(now=now, checkpoint=checkpoint)
        self.assertTrue(advanced["on"])
        self.assertEqual(scenario.deployments, 1)
        self.assertFalse(result["bytes_recovered"])
        self.assertEqual(result["failure"], "deadline")
        self.assertEqual(len(scenario.deletes()), 1)

    def test_create_observed_write_failure_keeps_may_exist_without_delete(self):
        scenario = Scenario()

        def checkpoint(_name, data):
            if b'"slot":"create"' in data and b'"phase":"observed"' in data:
                raise OSError("observed create")

        result = scenario.run(checkpoint=checkpoint)
        self.assertTrue(result["create_may_exist"])
        self.assertTrue(result["manual_intervention"])
        self.assertEqual(scenario.deletes(), [])
        self.assertIsNone(result["source_after"])
        create = [row for row in result["calls"] if row["stage"] == "create"]
        self.assertEqual(create[0]["status"], 201)
        self.assertNotIn("observed create", json.dumps(result))

    def test_classification_is_in_receipt_when_class_write_fails(self):
        scenario = Scenario(missing_historical=True)

        def checkpoint(_name, data):
            if b'"phase":"classification"' in data:
                raise OSError("class copy")

        result = scenario.run(checkpoint=checkpoint)
        self.assertEqual(result["classification"], "historical_listed")
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertFalse(result["evidence_complete"])
        self.assertNotIn("class copy", json.dumps(result))

    def test_body_read_failure_keeps_observed_status(self):
        directory = _private_dir()
        try:
            scenario = Scenario()
            opener = _ScriptedOpener(scenario.record, "body_read_failed", directory)
            transport = recovery.disposable_transport(
                "synthetic-admin-token",
                scenario.record["source"]["account_id"],
                scenario.record["disposable_project"],
                scenario.record["source"]["project"],
                opener=opener,
            )
            checkpoint, receipt = _writers(directory)
            result = recovery.recover_owner_bytes(
                scenario.record, template=TEMPLATE, source_request=scenario.source,
                admin_request=transport, pages_get=scenario.pages, persist=scenario.persist,
                hasher=_hash, now=lambda: 1_700_000_000, rng=scenario.rng,
                sleep=lambda _n: None, execute=True, checkpoint=checkpoint, receipt=receipt,
            )
            self.assertEqual(result["classification"], "body_read_failed")
            self.assertNotEqual(result["classification"], "not_observed")
            rows = [row for row in opener.snapshot_rows if row.get("phase") == "classification"]
            self.assertEqual(rows[0]["status"], 200)
            self.assertEqual(rows[0]["content_type"], "json")
            self.assertEqual(rows[0]["body_state"], "read_failed")
            self.assertEqual(rows[0]["fixture_hash"], opener.fixture_hash)
            self._assert_quiet(opener.at_cleanup, scenario.record)
            disposable = "/accounts/%s/pages/projects/%s" % (scenario.record["source"]["account_id"], scenario.record["disposable_project"])
            self.assertEqual([item for item in opener.calls if item[0] == "DELETE"], [("DELETE", disposable)])
        finally:
            shutil.rmtree(directory)

    def test_decoder_depth_on_cleanup_writes_receipt_without_delete(self):
        scenario = Scenario()
        original = scenario.admin
        nested = "[" * 10000 + "0" + "]" * 10000
        deep = ('{"success":true,"result":%s}' % nested).encode("ascii")

        def admin(method, path, body=None, *, bearer=None):
            project = "/accounts/%s/pages/projects/%s" % (
                scenario.record["source"]["account_id"], scenario.record["disposable_project"]
            )
            if method == "GET" and path == project and scenario.created and not scenario.deleted:
                scenario.events.append(("admin", method, path))
                return recovery.AdminObservation(True, 200, "json", deep)
            return original(method, path, body, bearer=bearer)

        scenario.admin = admin
        result = scenario.run()
        self.assertEqual(result["classification"], "decoder_depth")
        self.assertEqual(scenario.deletes(), [])
        self.assertTrue(result["manual_intervention"])
        self.assertFalse(result["cleanup"]["pre_get_id_match"])
        self.assertNotIn("delete_status", result["cleanup"])
        self.assertEqual(len(scenario.receipts), 1)
        receipt = json.loads(scenario.receipts[0][1].decode("utf-8"))
        self.assertEqual(receipt["classification"], "decoder_depth")
        self.assertIs(receipt["manual_intervention"], True)
        self.assertIs(receipt["cleanup"]["pre_get_id_match"], False)
        self.assertNotIn("delete_status", receipt["cleanup"])

    def test_explicit_upload_rejection_stops_before_d1(self):
        scenario = Scenario()
        original = scenario.admin

        def admin(method, path, body=None, *, bearer=None):
            if method == "POST" and path == "/pages/assets/upload":
                scenario.events.append(("admin", method, path))
                return _admin(200, b'{"success":false,"result":null}')
            return original(method, path, body, bearer=bearer)

        scenario.admin = admin
        result = scenario.run()
        self.assertEqual(scenario.deployments, 0)
        self.assertEqual(result["classification"], "envelope_rejected")
        self.assertEqual(len(scenario.deletes()), 1)
        self.assertFalse(result["bytes_recovered"])

    def test_null_upload_result_is_not_treated_as_rejection(self):
        scenario = Scenario()
        original = scenario.admin

        def admin(method, path, body=None, *, bearer=None):
            if method == "POST" and path == "/pages/assets/upload":
                scenario.events.append(("admin", method, path))
                return _admin(200, b'{"success":true,"result":null}')
            if method == "POST" and path.endswith("/deployments"):
                scenario.events.append(("admin", method, path))
                scenario.deployments += 1
                return _admin(500, b"")
            return original(method, path, body, bearer=bearer)

        scenario.admin = admin
        result = scenario.run()
        self.assertEqual(scenario.deployments, 1)
        self.assertNotEqual(result["classification"], "envelope_rejected")
        self.assertEqual(len(scenario.deletes()), 1)


if __name__ == "__main__":
    unittest.main()
