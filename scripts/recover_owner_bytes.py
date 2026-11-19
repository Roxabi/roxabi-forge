#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["blake3==1.0.11"]
# ///
"""Prepare or execute an explicitly approved disposable Pages recovery.

The default is offline. No approval is implied by a record or by this code.
G1b remains open. A response class is not a cause, an ACL, or a rights finding.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

import probe_owner_availability as stage1

MAX_ASSET = 25 * 1024 * 1024
ROUTES = b'{"version":1,"include":["/*"],"exclude":[]}'
MARKERS = (b"__G1B_ROUTE__", b"__G1B_INTERNAL__", b"__G1B_TOKEN_SHA256__", b"__G1B_NOT_AFTER_MS__")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RECORD_KEYS = {"source", "approved_source_sha", "disposable_project", "worker_template_sha256", "compatibility_date", "hash_calibration", "bypass_residual_accepted", "provenance"}
CONTINUE_CLASS = "exact_fixture"
PARSE_CLASSES = {"duplicate_key", "unreadable_json", "envelope_not_object"}
CHECKPOINT_KEYS = {"phase", "slot", "method", "dispatched", "status", "content_type", "classification", "fixture_hash", "count", "historical_present", "fixture_missing", "phase_failure"}


class RecoveryError(Exception):
    """A sanitized, fixed recovery failure classification."""


def pages_hash(data: bytes, ext: str, *, impl: Any = None) -> str:
    if not isinstance(data, bytes) or not isinstance(ext, str) or not re.fullmatch(r"[A-Za-z0-9]+", ext):
        raise RecoveryError("hash_input")
    if impl is None:
        from blake3 import blake3
        impl = blake3
    return impl(base64.b64encode(data) + ext.encode("ascii")).hexdigest()[:32]


def render_worker(template: bytes, *, route: str, internal: str, token_sha256: str, not_after_ms: int) -> bytes:
    if (not isinstance(template, bytes) or not isinstance(route, str) or not re.fullmatch(r"/[0-9a-f]{64}", route)
        or not isinstance(internal, str) or not re.fullmatch(r"/[0-9a-f]{64}\.json", internal)
        or not isinstance(token_sha256, str) or not HEX64.fullmatch(token_sha256)
        or isinstance(not_after_ms, bool) or not isinstance(not_after_ms, int) or not 0 < not_after_ms < 10**16):
        raise RecoveryError("worker_input")
    if any(template.count(marker) != 1 for marker in MARKERS):
        raise RecoveryError("worker_template")
    rendered = template
    for marker, value in zip(MARKERS, (route, internal, token_sha256, str(not_after_ms))):
        rendered = rendered.replace(marker, value.encode("ascii"))
    if b"__G1B_" in rendered:
        raise RecoveryError("worker_template")
    try:
        rendered.decode("ascii")
    except UnicodeError as exc:
        raise RecoveryError("worker_template") from exc
    return rendered


def _validate_record(record: Any) -> dict:
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        raise RecoveryError("record")
    try:
        source = stage1._validate_target(record["source"])
    except stage1.ProbeError as exc:
        raise RecoveryError("record") from exc
    name = record["disposable_project"]
    if (not isinstance(name, str) or not stage1._PROJECT_RE.fullmatch(name) or name == source["project"]
        or not isinstance(record["approved_source_sha"], str) or not stage1._SHA40.fullmatch(record["approved_source_sha"])
        or not isinstance(record["worker_template_sha256"], str) or not HEX64.fullmatch(record["worker_template_sha256"])
        or not isinstance(record["bypass_residual_accepted"], bool)
        or not isinstance(record["provenance"], str) or not record["provenance"]):
        raise RecoveryError("record")
    try:
        if date.fromisoformat(record["compatibility_date"]).isoformat() != record["compatibility_date"]:
            raise ValueError()
    except (ValueError, TypeError):
        raise RecoveryError("record") from None
    calibration = record["hash_calibration"]
    if not isinstance(calibration, list) or len(calibration) < 3:
        raise RecoveryError("record")
    for item in calibration:
        if (not isinstance(item, dict) or set(item) != {"path", "extension", "expected_pages_hash"}
            or not isinstance(item["path"], str) or not Path(item["path"]).is_absolute()
            or not isinstance(item["extension"], str) or not re.fullmatch(r"[A-Za-z0-9]+", item["extension"])
            or not isinstance(item["expected_pages_hash"], str) or not stage1._HEX32.fullmatch(item["expected_pages_hash"])):
            raise RecoveryError("record")
    if len({item["path"] for item in calibration}) < 3:
        raise RecoveryError("record")
    return record


class _CheckpointFailed(Exception):
    """Checkpoint or receipt write failed. The message is never persisted."""


class AdminObservation:
    """Admin transport result. ``status`` is an HTTP status, or None if none was observed."""

    __slots__ = ("dispatched", "status", "content_type", "body")

    def __init__(self, dispatched, status, content_type, body):
        if not isinstance(dispatched, bool) or content_type not in ("json", "other", "absent") or not isinstance(body, bytes):
            raise RecoveryError("transport")
        if isinstance(status, bool) or status is None or not isinstance(status, int) or status <= 0 or status > 599:
            status = None
        elif not dispatched:
            status = None
        self.dispatched = dispatched
        self.status = status
        self.content_type = content_type
        self.body = body


def _content_type_enum(headers):
    if headers is None:
        return "absent"
    try:
        pairs = list(headers.items())
    except Exception:
        return "absent"
    raw = None
    for key, value in pairs:
        if str(key).lower() == "content-type":
            raw = value
            break
    if raw is None or not str(raw).strip():
        return "absent"
    media = str(raw).split(";", 1)[0].strip().lower()
    if media == "application/json":
        return "json"
    return "other"


def _status_field(status):
    if isinstance(status, bool) or not isinstance(status, int) or status <= 0 or status > 599:
        return "unknown"
    return status


def _observe(request, method, path, body=None, *, bearer=None):
    try:
        value = request(method, path, body, bearer=bearer) if bearer is not None else request(method, path, body)
    except Exception:
        return AdminObservation(False, None, "absent", b"")
    if not isinstance(value, AdminObservation):
        return AdminObservation(False, None, "absent", b"")
    return value


def _envelope_class(obs):
    body = obs.body
    obs.body = b""
    if not obs.dispatched or obs.status is None:
        return "not_observed", None
    if not 200 <= obs.status < 300:
        return "http_status", None
    try:
        doc = stage1._loads(body)
    except stage1._DuplicateKey:
        return "duplicate_key", None
    except (ValueError, UnicodeError):
        return "unreadable_json", None
    if not isinstance(doc, dict):
        return "envelope_not_object", None
    if doc.get("success") is not True:
        return "envelope_rejected", None
    return "ok", doc.get("result")


def _missing_class(result, fixture_hash, historical_hash):
    if not isinstance(result, list) or not all(isinstance(item, str) for item in result):
        return "result_shape", None, None, None
    historical_present = historical_hash not in result
    fixture_missing = result == [fixture_hash]
    if result == [fixture_hash]:
        klass = CONTINUE_CLASS
    elif historical_hash in result:
        klass = "historical_listed"
    else:
        klass = "other_missing"
    return klass, historical_present, fixture_missing, len(result)


def _phase_failure_for(klass):
    if klass == CONTINUE_CLASS:
        return None
    if klass in PARSE_CLASSES:
        return "parse"
    return "guard"


def _checkpoint_bytes(fields, forbidden):
    if not isinstance(fields, dict) or set(fields) - CHECKPOINT_KEYS:
        raise RecoveryError("evidence")
    payload = {}
    for key in ("phase", "slot", "method", "dispatched", "status", "content_type", "classification", "fixture_hash", "count", "historical_present", "fixture_missing", "phase_failure"):
        if key not in fields:
            continue
        value = fields[key]
        if value is None and key not in ("historical_present", "fixture_missing", "count"):
            continue
        payload[key] = value
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n"
    for item in forbidden:
        if item and item in raw:
            raise RecoveryError("evidence")
    return raw


def _evidence_bytes(evidence):
    return json.dumps(evidence, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _local_refuse():
    return AdminObservation(False, None, "absent", b"")

def _url_host(value, subdomain):
    if not isinstance(value, str):
        raise RecoveryError("deployment_url")
    try:
        url = urllib.parse.urlsplit(value)
        host = url.hostname
        if (url.scheme != "https" or not host or url.username or url.password or url.port not in (None, 443)
            or url.path not in ("", "/") or url.query or url.fragment
            or not (host == subdomain or host.endswith("." + subdomain))
            or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", x) for x in host.split("."))):
            raise ValueError()
    except (ValueError, TypeError):
        raise RecoveryError("deployment_url") from None
    return host


def _project_subdomain(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.pages\.dev", value):
        raise RecoveryError("project_receipt")
    return value


def _deployment_hosts(result, subdomain):
    if not isinstance(result, dict):
        raise RecoveryError("deployment_receipt")
    host = _url_host(result.get("url"), subdomain)
    aliases = result.get("aliases", [])
    if not isinstance(aliases, list):
        raise RecoveryError("deployment_receipt")
    return host, [_url_host(item, subdomain) for item in aliases]


def _bytes_rng(rng, n):
    value = rng(n)
    if not isinstance(value, bytes) or len(value) != n:
        raise RecoveryError("randomness")
    return value


def recover_owner_bytes(record, *, template, source_request, admin_request, pages_get, persist, hasher, now, rng, sleep, execute=False, checkpoint=None, receipt=None) -> dict:
    """Run the bounded policy; injected I/O follows the documented callbacks.

    Intent, observed transport facts, and the response class are checkpointed
    before the next recovery call and before a guard raises. A class is not a cause.
    """
    _validate_record(record)
    if not isinstance(execute, bool) or not isinstance(template, bytes):
        raise RecoveryError("input")
    if execute and not callable(checkpoint):
        raise RecoveryError("input")
    if hashlib.sha256(template).hexdigest() != record["worker_template_sha256"]:
        raise RecoveryError("template_hash")
    render_worker(template, route="/" + "0" * 64, internal="/" + "1" * 64 + ".json", token_sha256="2" * 64, not_after_ms=1)
    evidence = {"outcome": "offline", "bytes_recovered": False, "g1b_closed": False,
                "template_sha256": record["worker_template_sha256"], "stages": [], "calls": [], "probes": [],
                "cleanup": {}, "source_after": None, "rendered_identical_d1_d2": False}
    if not execute:
        if receipt is not None:
            receipt("recovery-evidence.json", _evidence_bytes(evidence))
        return evidence
    source = record["source"]
    project = record["disposable_project"]
    base = stage1._api_path(source["account_id"], project)
    collection = "/accounts/%s/pages/projects" % stage1._quote(source["account_id"])
    owned_id = None
    d2_created = False
    delete_success = False
    outcome = "stopped"
    saved = None
    start = now()
    deadline = int((start + 90 * 60) * 1000)
    route = "/" + _bytes_rng(rng, 32).hex()
    internal = "/" + _bytes_rng(rng, 32).hex() + ".json"
    key = base64.urlsafe_b64encode(_bytes_rng(rng, 32)).rstrip(b"=").decode("ascii")
    wrong = base64.urlsafe_b64encode(_bytes_rng(rng, 32)).rstrip(b"=").decode("ascii")
    fixture = json.dumps({"g1b_fixture": _bytes_rng(rng, 32).hex()}, separators=(",", ":")).encode("ascii")
    worker = render_worker(template, route=route, internal=internal, token_sha256=hashlib.sha256(key.encode("ascii")).hexdigest(), not_after_ms=deadline)
    fixture_hash = hasher(fixture, "json")
    if not isinstance(fixture_hash, str) or not stage1._HEX32.fullmatch(fixture_hash) or fixture_hash == source["expected_file_hash"]:
        raise RecoveryError("fixture_hash")
    evidence["fixture_hash"] = fixture_hash
    forbidden = (
        source["expected_file_hash"].encode("ascii"),
        source["account_id"].encode("ascii"),
        source["source_deployment_id"].encode("ascii"),
        source["public_host"].encode("ascii"),
        b"Authorization",
        b"Bearer",
        b"CLOUDFLARE_",
    )
    seq = [0]

    def _save(fields, *, required):
        try:
            raw = _checkpoint_bytes(fields, forbidden)
            checkpoint("checkpoint-%03d.json" % (seq[0] + 1), raw)
            seq[0] += 1
        except _CheckpointFailed:
            if required:
                raise
        except Exception:
            if required:
                raise _CheckpointFailed()

    def api(slot, method, path, body=None, bearer=None, *, progress=True):
        _save({"phase": "intent", "slot": slot, "method": method, "fixture_hash": fixture_hash, "count": seq[0] + 1}, required=progress)
        obs = _observe(admin_request, method, path, body, bearer=bearer)
        evidence["calls"].append({"stage": slot, "method": method, "dispatched": obs.dispatched, "status": _status_field(obs.status), "content_type": obs.content_type})
        _save({"phase": "observed", "slot": slot, "method": method, "dispatched": obs.dispatched, "status": _status_field(obs.status), "content_type": obs.content_type, "fixture_hash": fixture_hash, "count": seq[0] + 1}, required=progress)
        return obs

    def note_class(obs, slot, method, klass, historical_present, fixture_missing, count, *, required=True):
        failure = _phase_failure_for(klass)
        _save({"phase": "classification", "slot": slot, "method": method, "dispatched": obs.dispatched, "status": _status_field(obs.status), "content_type": obs.content_type, "classification": klass, "fixture_hash": fixture_hash, "count": count, "historical_present": historical_present, "fixture_missing": fixture_missing, "phase_failure": failure}, required=required)
        evidence["classification"] = klass
        if failure is not None:
            evidence["phase_failure"] = failure

    def source_probe(slot):
        try:
            result = stage1.probe_owner_availability(source, source_request, execute=True)
        except Exception:
            evidence["stages"].append(slot + "_failed")
            return {"availability": None, "drift": None}
        evidence["stages"].append(slot)
        return {"availability": result.get("availability"), "drift": result.get("drift")}

    def observe(host, path, headers, allowed, role, probe):
        try:
            status, headers_out, data = pages_get(host, path, headers, allowed_hosts=allowed)
            if isinstance(status, bool) or not isinstance(status, int) or not isinstance(headers_out, dict) or not isinstance(data, bytes) or len(data) > MAX_ASSET:
                raise ValueError()
            lowered = {str(k).lower(): str(v) for k, v in headers_out.items()}
        except Exception:
            status, lowered, data = 0, {}, b""
        marker = lowered.get("x-recovery-gate") == "deny"
        evidence["probes"].append({"role": role, "probe": probe, "status": status, "length": len(data), "marker": marker})
        return status, lowered, data

    def deny(host, path, headers, allowed, role, label):
        status, headers_out, data = observe(host, path, headers, allowed, role, label)
        if status != 404 or data != b"" or headers_out.get("x-recovery-gate") != "deny" or "location" in headers_out:
            raise RecoveryError("negative_probe")

    def negatives(host, allowed, role):
        deny(host, route, {}, allowed, role, "n1")
        deny(host, route, {"x-recovery-key": wrong}, allowed, role, "n2")
        deny(host, internal, {}, allowed, role, "n3")

    def ready(host, allowed, role, positive):
        for attempt in range(30):
            status, headers_out, data = observe(host, route, {"x-recovery-key": key} if positive else {}, allowed, role, "ready")
            if positive and status == 200:
                if "location" in headers_out or "x-recovery-gate" in headers_out or data != fixture:
                    raise RecoveryError("positive_probe")
                return
            if not positive and status == 404 and not data and headers_out.get("x-recovery-gate") == "deny" and "location" not in headers_out:
                return
            if 300 <= status < 400 or "location" in headers_out:
                raise RecoveryError("redirect")
            if attempt < 29:
                sleep(10)
        raise RecoveryError("readiness")

    try:
        _save({"phase": "intent", "slot": "source_before", "method": "GET", "fixture_hash": fixture_hash, "count": seq[0] + 1}, required=True)
        initial = source_probe("source_before")
        if initial != {"availability": "available", "drift": False}:
            raise RecoveryError("source_unavailable")
        obs = api("project_absent", "GET", base)
        if obs.status != 404:
            outcome = "stopped_unowned"
            raise RecoveryError("project_collision")
        config = {"compatibility_date": record["compatibility_date"], "fail_open": False}
        obs = api("create", "POST", collection, {"name": project, "production_branch": "main", "deployment_configs": {"production": dict(config), "preview": dict(config)}})
        klass, parsed = _envelope_class(obs)
        lost = not obs.dispatched or obs.status is None or obs.status >= 500 or (obs.status is not None and 200 <= obs.status < 300)
        if klass != "ok" or not isinstance(parsed, dict) or parsed.get("name") != project or not isinstance(parsed.get("id"), str) or not stage1._ID_RE.fullmatch(parsed["id"]) or ".." in parsed["id"]:
            outcome = "stopped_receipt_lost" if lost else "stopped_unowned"
            if klass != "ok":
                note_class(obs, "create", "POST", klass, None, None, None)
            raise RecoveryError("create_receipt")
        owned_id = parsed["id"]
        subdomain = _project_subdomain(parsed.get("subdomain"))
        configs = parsed.get("deployment_configs")
        if not isinstance(configs, dict) or any(not isinstance(configs.get(k), dict) or configs[k].get("fail_open") is not False for k in ("production", "preview")):
            raise RecoveryError("create_config")
        evidence["stages"].append("owned")
        obs = api("upload_token", "GET", base + "/upload-token")
        klass, parsed = _envelope_class(obs)
        jwt = parsed.get("jwt") if klass == "ok" and isinstance(parsed, dict) else None
        if not isinstance(jwt, str) or not stage1._TOKEN_RE.fullmatch(jwt):
            if klass != "ok":
                note_class(obs, "upload_token", "GET", klass, None, None, None)
            raise RecoveryError("upload_token")
        obs = api("cross_project", "POST", stage1.CHECK_MISSING_PATH, {"hashes": [source["expected_file_hash"], fixture_hash]}, bearer=jwt)
        env_class, parsed = _envelope_class(obs)
        if env_class != "ok":
            klass, historical_present, fixture_missing, count, missing = env_class, None, None, None, None
        else:
            klass, historical_present, fixture_missing, count = _missing_class(parsed, fixture_hash, source["expected_file_hash"])
            missing = parsed if klass != "result_shape" else None
        evidence["cross_project"] = {"historical_present": historical_present, "fixture_missing": fixture_missing}
        note_class(obs, "cross_project", "POST", klass, historical_present, fixture_missing, count)
        if klass != CONTINUE_CLASS or missing != [fixture_hash]:
            raise RecoveryError("cross_project")
        upload = [{"key": fixture_hash, "value": base64.b64encode(fixture).decode("ascii"), "metadata": {"contentType": "application/json"}, "base64": True}]
        obs = api("fixture_upload", "POST", "/pages/assets/upload", upload, bearer=jwt)
        if obs.status is None or not 200 <= obs.status < 300:
            env_class, _parsed = _envelope_class(obs)
            note_class(obs, "fixture_upload", "POST", env_class, None, None, None)
            raise RecoveryError("fixture_upload")
        d1 = {"manifest": {internal: fixture_hash}, "_worker.js": worker, "_routes.json": ROUTES}
        obs = api("d1", "POST", base + "/deployments", d1)
        env_class, parsed = _envelope_class(obs)
        if env_class != "ok":
            note_class(obs, "d1", "POST", env_class, None, None, None)
        d1_host, aliases = _deployment_hosts(parsed, subdomain)
        allowed = frozenset([subdomain, d1_host] + aliases)
        ordered = [("d1_subdomain", subdomain), ("d1_url", d1_host)] + [("d1_alias_%d" % i, host) for i, host in enumerate(aliases)]
        seen = set()
        for role, host in ordered:
            if host in seen:
                continue
            seen.add(host)
            ready(host, allowed, role, True)
            negatives(host, allowed, role)
        if record["bypass_residual_accepted"] is not True:
            raise RecoveryError("r1_not_accepted")
        if deadline - int(now() * 1000) < 20 * 60 * 1000:
            raise RecoveryError("deadline")
        d2 = {"manifest": {internal: source["expected_file_hash"]}, "_worker.js": worker, "_routes.json": ROUTES}
        evidence["rendered_identical_d1_d2"] = d1["_worker.js"] == d2["_worker.js"] and d1["_routes.json"] == d2["_routes.json"]
        if not evidence["rendered_identical_d1_d2"]:
            raise RecoveryError("worker_drift")
        obs = api("d2", "POST", base + "/deployments", d2)
        d2_created = obs.status is not None and 200 <= obs.status < 300
        env_class, parsed = _envelope_class(obs)
        if env_class != "ok":
            note_class(obs, "d2", "POST", env_class, None, None, None)
        d2_host, _aliases = _deployment_hosts(parsed, subdomain)
        allowed = frozenset([d2_host])
        ready(d2_host, allowed, "d2_url", False)
        negatives(d2_host, allowed, "d2_url")
        status, headers_out, data = observe(d2_host, route, {"x-recovery-key": key}, allowed, "d2_url", "download")
        if status != 200 or "location" in headers_out or "x-recovery-gate" in headers_out:
            raise RecoveryError("download")
        matches = hasher(data, "json") == source["expected_file_hash"]
        filename = "recovered-asset-owners.json" if matches else "unverified-download.bin"
        metadata = persist(filename, data)
        if (not isinstance(metadata, dict) or set(metadata) != {"name", "size", "sha256"} or metadata["name"] != filename
            or metadata["size"] != len(data) or metadata["sha256"] != hashlib.sha256(data).hexdigest()):
            raise RecoveryError("persistence")
        saved = {"name": filename, "size": len(data), "sha256": metadata["sha256"], "pages_hash_match": matches}
        evidence["file"] = saved
        evidence["bytes_recovered"] = matches
        outcome = "recovered" if matches else "unverified"
    except _CheckpointFailed:
        evidence["phase_failure"] = "persist"
        evidence["failure"] = "operation_failed"
    except Exception as exc:
        safe_failures = {"source_unavailable", "project_collision", "create_receipt", "project_receipt",
                         "create_config", "upload_token", "cross_project", "fixture_upload",
                         "deployment_receipt", "deployment_url", "negative_probe", "positive_probe",
                         "r1_not_accepted", "deadline", "worker_drift", "download", "persistence",
                         "redirect", "readiness"}
        evidence["failure"] = str(exc) if isinstance(exc, RecoveryError) and str(exc) in safe_failures else "operation_failed"
    finally:
        if owned_id is not None:
            obs = api("cleanup_pre_get", "GET", base, progress=False)
            env_class, current = _envelope_class(obs)
            match = env_class == "ok" and isinstance(current, dict) and current.get("id") == owned_id and current.get("name") == project and project != source["project"]
            evidence["cleanup"]["pre_get_id_match"] = match
            if match:
                obs = api("cleanup_delete", "DELETE", base, progress=False)
                evidence["cleanup"]["delete_status"] = _status_field(obs.status)
                if obs.status is not None and 200 <= obs.status < 300:
                    delete_success = True
                    obs = api("cleanup_final_get", "GET", base, progress=False)
                    evidence["cleanup"]["final_status"] = _status_field(obs.status)
                    if obs.status != 404:
                        outcome += "_cleanup_failed"
                else:
                    outcome += "_cleanup_failed"
            else:
                outcome += "_cleanup_failed"
        if d2_created and delete_success:
            try:
                _save({"phase": "intent", "slot": "source_after", "method": "GET", "fixture_hash": fixture_hash, "count": seq[0] + 1}, required=True)
            except _CheckpointFailed:
                evidence["phase_failure"] = "persist"
                evidence["failure"] = "operation_failed"
                if outcome == "recovered":
                    outcome = "stopped"
            else:
                evidence["source_after"] = source_probe("source_after")
                if evidence["source_after"] != {"availability": "available", "drift": False}:
                    outcome += "_source_indicator_failed"
    evidence["outcome"] = outcome
    if receipt is not None:
        payload = _evidence_bytes(evidence)
        for item in forbidden:
            if item and item in payload:
                raise _CheckpointFailed()
        receipt("recovery-evidence.json", payload)
    return evidence


def _read_response(response, cap):
    chunks = []
    total = 0
    while True:
        chunk = response.read(65536)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > cap:
            raise RecoveryError("response_limit")
        chunks.append(chunk)


def disposable_transport(token, account, name, source_project, *, opener=None):
    if not stage1._TOKEN_RE.fullmatch(token) or not stage1._HEX32.fullmatch(account) or not stage1._PROJECT_RE.fullmatch(name) or name == source_project:
        raise RecoveryError("transport")
    project = stage1._api_path(account, name)
    collection = "/accounts/%s/pages/projects" % stage1._quote(account)
    budget = {("GET", project): 3, ("POST", collection): 1, ("GET", project + "/upload-token"): 1,
              ("POST", stage1.CHECK_MISSING_PATH): 1, ("POST", "/pages/assets/upload"): 1,
              ("POST", project + "/deployments"): 2, ("DELETE", project): 1}
    if opener is None:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), stage1._NoRedirect())

    def request(method, path, body=None, *, bearer=None):
        slot = (method, path)
        if slot not in budget or budget[slot] <= 0:
            return _local_refuse()
        budget[slot] -= 1
        if method in ("GET", "DELETE") and (body is not None or bearer is not None):
            return _local_refuse()
        if path in (stage1.CHECK_MISSING_PATH, "/pages/assets/upload"):
            if not isinstance(bearer, str) or not stage1._TOKEN_RE.fullmatch(bearer):
                return _local_refuse()
        elif bearer is not None:
            return _local_refuse()
        credential = bearer if bearer is not None else token
        headers = {"Authorization": "Bearer " + credential, "Accept": "application/json"}
        data = None
        if path == project + "/deployments" and method == "POST":
            if not isinstance(body, dict) or set(body) != {"manifest", "_worker.js", "_routes.json"} or not isinstance(body["manifest"], dict) or not isinstance(body["_worker.js"], bytes) or body["_routes.json"] != ROUTES:
                return _local_refuse()
            boundary = "g1b-" + secrets.token_hex(24)
            sections = []
            for field, value in (("manifest", json.dumps(body["manifest"], separators=(",", ":")).encode("ascii")), ("_worker.js", body["_worker.js"]), ("_routes.json", body["_routes.json"])):
                disposition = 'Content-Disposition: form-data; name="%s"' % field
                if field != "manifest":
                    disposition += '; filename="%s"' % field
                sections.append(("--%s\r\n%s\r\nContent-Type: %s\r\n\r\n" % (
                    boundary, disposition, "application/json" if field == "manifest" else "application/octet-stream"
                )).encode("ascii") + value + b"\r\n")
            data = b"".join(sections) + ("--%s--\r\n" % boundary).encode("ascii")
            headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        elif body is not None:
            try:
                data = json.dumps(body, separators=(",", ":")).encode("ascii")
            except (ValueError, TypeError, UnicodeError):
                return _local_refuse()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(stage1.API_ORIGIN + stage1.API_PREFIX + path, data=data, method=method, headers=headers)
        try:
            with opener.open(req, timeout=60) as response:
                status = response.status
                if isinstance(status, bool) or not isinstance(status, int) or status <= 0 or status > 599:
                    status = None
                return AdminObservation(True, status, _content_type_enum(response.headers), _read_response(response, stage1.MAX_BODY))
        except urllib.error.HTTPError as exc:
            try:
                code = exc.code if isinstance(exc.code, int) and not isinstance(exc.code, bool) and 0 < exc.code <= 599 else None
                return AdminObservation(True, code, _content_type_enum(getattr(exc, "headers", None)), b"")
            finally:
                exc.close()
        except Exception:
            return AdminObservation(True, None, "absent", b"")
    return request


def native_pages_get(host, path, headers, *, allowed_hosts):
    if (not isinstance(host, str) or host not in allowed_hosts or not isinstance(path, str)
        or not re.fullmatch(r"/[0-9a-f]{64}(?:\.json)?", path) or not isinstance(headers, dict)
        or set(headers) - {"x-recovery-key"}):
        return 0, {}, b""
    if any(not isinstance(v, str) or not stage1._TOKEN_RE.fullmatch(v) for v in headers.values()):
        return 0, {}, b""
    try:
        _url_host("https://" + host, host)
    except RecoveryError:
        return 0, {}, b""
    request_headers = {"Accept-Encoding": "identity", **headers}
    req = urllib.request.Request("https://" + host + path, method="GET", headers=request_headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), stage1._NoRedirect())
    try:
        with opener.open(req, timeout=60) as response:
            return response.status, dict(response.headers.items()), _read_response(response, MAX_ASSET)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, dict(exc.headers.items()), _read_response(exc, MAX_ASSET)
        except Exception:
            return 0, {}, b""
        finally:
            exc.close()
    except Exception:
        return 0, {}, b""


def _read_calibration(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not __import__("stat").S_ISREG(info.st_mode) or info.st_size > MAX_ASSET:
                raise RecoveryError("calibration")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                return _read_response(stream, MAX_ASSET)
        finally:
            os.close(fd)
    except OSError as exc:
        raise RecoveryError("calibration") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline preparation for separately approved owner-byte recovery.", allow_abbrev=False)
    for flag in ("--approval-record", "--config", "--env", "--output-dir"):
        parser.add_argument(flag, required=True)
    parser.add_argument("--execute", action="store_true", help="Run only after explicit approval of the exact SHA and operation")
    def usage(_message):
        print("recover_owner_bytes: usage", file=sys.stderr)
        raise SystemExit(1)
    parser.error = usage
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1
    output_dir = Path(args.output_dir).expanduser()
    evidence_path = output_dir / "recovery-evidence.json"
    try:
        fd = stage1._output_parent(evidence_path)
        os.close(fd)
        for name in ("recovered-asset-owners.json", "unverified-download.bin"):
            fd = stage1._output_parent(output_dir / name)
            os.close(fd)
        record = _validate_record(stage1._load_json_object(stage1._read_private_text(Path(args.approval_record).expanduser())))
        config = stage1._load_json_object(stage1._read_private_text(Path(args.config).expanduser()))
        env = stage1.parse_env(stage1._read_private_text(Path(args.env).expanduser()))
        stage1._cross_check(config, env, record["source"])
        credential = env.get("CLOUDFLARE_API_TOKEN", "")
        if not stage1._TOKEN_RE.fullmatch(credential):
            raise RecoveryError("credential")
        stage1._require_approved_source(record["approved_source_sha"])
        template = (Path(__file__).resolve().parent / "g1b-gate-worker.template.js").read_bytes()
        for entry in record["hash_calibration"]:
            if pages_hash(_read_calibration(entry["path"]), entry["extension"]) != entry["expected_pages_hash"]:
                raise RecoveryError("calibration")
        target = record["source"]
        project_path = stage1._api_path(target["account_id"], target["project"])
        allowed = frozenset((project_path, project_path + "/deployments/%s/files" % stage1._quote(target["source_deployment_id"]), project_path + "/upload-token", stage1.CHECK_MISSING_PATH))
        source_request = stage1._admin_request(credential, allowed)
        admin_request = disposable_transport(credential, target["account_id"], record["disposable_project"], target["project"])
        def persist(name, data):
            stage1._write_private(output_dir / name, data)
            return {"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        def checkpoint(name, data):
            stage1._write_private(output_dir / name, data)
        def receipt(_name, data):
            stage1._write_private(evidence_path, data)
        result = recover_owner_bytes(record, template=template, source_request=source_request, admin_request=admin_request,
                                     pages_get=native_pages_get, persist=persist, hasher=pages_hash, now=time.time,
                                     rng=secrets.token_bytes, sleep=time.sleep, execute=args.execute,
                                     checkpoint=checkpoint, receipt=receipt)
        encoded = _evidence_bytes(result)
        print("outcome=%s evidence=%s evidence_sha256=%s" % (result["outcome"], evidence_path, hashlib.sha256(encoded).hexdigest()))
        return 0 if result["outcome"] in ("offline", "recovered") else 1
    except Exception:
        print("recover_owner_bytes: preparation or evidence failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
