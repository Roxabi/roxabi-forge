#!/usr/bin/env python3
"""Offline, injected-transport tests for disposable owner-byte recovery."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import sys
import unittest
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
        self.created = False
        self.deleted = False
        self.deployments = 0
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
                return 404, b""
            if not self.created:
                return _envelope(identity) if self.collision else (404, b"")
            if self.cleanup_id is not None:
                identity["id"] = self.cleanup_id
            return _envelope(identity)
        if method == "POST" and path == collection:
            self.created = True
            if self.malformed_receipt:
                return _envelope({"name": identity["name"]}, 201)
            return (0, b"") if self.receipt_lost else _envelope(identity, 201)
        if method == "DELETE" and path == project:
            if self.cleanup_fails:
                return 500, b""
            self.deleted = True
            return _envelope({})
        if method == "GET" and path == project + "/upload-token":
            return _envelope({"jwt": "synthetic-disposable-upload-token"})
        if method == "POST" and path == "/pages/assets/check-missing":
            hashes = body["hashes"]
            hist = source["expected_file_hash"]
            return _envelope(hashes if self.missing_historical else [h for h in hashes if h != hist])
        if method == "POST" and path == "/pages/assets/upload":
            self.fixture = base64.b64decode(body[0]["value"])
            return _envelope({})
        if method == "POST" and path == project + "/deployments":
            self.deployments += 1
            return _envelope({
                "url": "https://d%d.disposable-fixture.pages.dev" % self.deployments,
                "aliases": [],
            }, 201)
        return 404, b""

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

    def run(self, execute=True):
        return recovery.recover_owner_bytes(
            self.record, template=TEMPLATE, source_request=self.source,
            admin_request=self.admin, pages_get=self.pages, persist=self.persist,
            hasher=_hash, now=lambda: 1_700_000_000, rng=self.rng,
            sleep=lambda _: None, execute=execute,
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


if __name__ == "__main__":
    unittest.main()
