#!/usr/bin/env python3
"""Bounded Pages availability probe for historical /asset-owners.json.

This is a prerequisite investigation, not a closure of the historical
ownership gate. It does not recover bytes, validate rights, deploy, upload,
roll back, or reanchor. Default execution is preflight only.

The upload-token GET and the internal POST /pages/assets/check-missing are a
separate operation. Side-effect freedom of that POST is an inference from
Wrangler, not a proven property. Do not describe the probe as strictly
read-only.

Core:
    probe_owner_availability(target, request, *, execute=False) -> dict

request(method, api_path, body=None, *, bearer=None) -> (http_status, bytes)
Relative API paths only. bearer=None means the admin token stays in the
transport closure. A supplied bearer is the upload JWT and must not be stored.
POST body is the dict {"hashes": [<expected 32-hex hash>]} and nothing else.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


API_ORIGIN = "https://api.cloudflare.com"
API_PREFIX = "/client/v4"
ASSET_OWNERS_PATH = "/asset-owners.json"
CHECK_MISSING_PATH = "/pages/assets/check-missing"
MAX_BODY = 8 * 1024 * 1024
TIMEOUT_SECONDS = 60

TARGET_KEYS = (
    "account_id",
    "project",
    "public_host",
    "production_branch",
    "source_deployment_id",
    "expected_file_hash",
    "expected_canonical_id",
    "expected_latest_id",
)
RECORD_EXTRA = frozenset({"approved_source_sha", "provenance"})

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_HEX32_RUN = re.compile(r"[0-9a-fA-F]{32}")
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_PROJECT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
_BRANCH_RE = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._/-]{0,254}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PROVENANCE_RE = re.compile(r"^[A-Za-z0-9 .:_/-]{1,160}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9._~+/=-]{1,4096}$")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

Request = Callable[..., tuple[Any, Any]]


class ProbeError(Exception):
    """Unsafe target, mismatched evidence, API failure, or concurrent drift.

    str(self) is the stable code only. No response body, token, or JWT.
    drift is True only when a post-probe re-read observed an identity change.
    """

    def __init__(
        self,
        code: str,
        *,
        stage: str,
        drift: bool = False,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.stage = stage
        self.drift = True if drift else False
        self.diagnostics = diagnostics if diagnostics is not None else {}
        super().__init__(code)


class _DuplicateKey(Exception):
    pass


class _CliRefuse(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quote(part: str) -> str:
    return urllib.parse.quote(part, safe="")




def _deployment_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    dep = value.get("id")
    if isinstance(dep, str) and dep:
        return dep
    return None




def _domain_set(project: dict[str, Any]) -> frozenset[str] | None:
    raw = project.get("domains")
    if not isinstance(raw, list):
        return None
    names = []
    for item in raw:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            found = False
            for key in ("name", "domain", "hostname"):
                if isinstance(item.get(key), str):
                    names.append(item[key])
                    found = True
                    break
            if not found:
                return None
        else:
            return None
    return frozenset(name for name in names if name)


def _identity(project: dict[str, Any]) -> dict[str, Any] | None:
    name = project.get("name")
    branch = project.get("production_branch")
    domains = _domain_set(project)
    canonical = _deployment_id(project.get("canonical_deployment"))
    latest = _deployment_id(project.get("latest_deployment"))
    if not isinstance(name, str) or not isinstance(branch, str) or domains is None:
        return None
    if canonical is None or latest is None:
        return None
    return {
        "name": name,
        "production_branch": branch,
        "domains": domains,
        "canonical_id": canonical,
        "latest_id": latest,
    }


def _object_pairs(pairs: list[tuple[Any, Any]]) -> dict[Any, Any]:
    obj: dict[Any, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise _DuplicateKey()
        obj[key] = value
    return obj


def _loads(body: bytes) -> Any:
    text = body.decode("utf-8")
    return json.loads(text, object_pairs_hook=_object_pairs)




def _fail(
    code: str,
    stage: str,
    stages: list[str],
    http: list[dict[str, Any]],
    *,
    drift: bool = False,
    reason: str | None = None,
    phase: str,
) -> None:
    diagnostics = {
        "stages": list(stages),
        "http": [dict(row) for row in http],
        "drift": drift,
        "phase": phase,
    }
    if reason is not None:
        diagnostics["reason"] = reason
    raise ProbeError(code, stage=stage, drift=drift, diagnostics=diagnostics)


def _validate_target(target: Any) -> dict[str, str]:
    if not isinstance(target, dict) or set(target) != set(TARGET_KEYS):
        raise ProbeError("unsafe_target", stage="target", diagnostics={"reason": "keys"})
    out: dict[str, str] = {}
    for key in TARGET_KEYS:
        value = target[key]
        if not isinstance(value, str) or value != value.strip() or not value:
            raise ProbeError(
                "unsafe_target", stage="target", diagnostics={"reason": "value"}
            )
        out[key] = value
    if not _HEX32.fullmatch(out["account_id"]) or not _HEX32.fullmatch(
        out["expected_file_hash"]
    ):
        raise ProbeError("unsafe_target", stage="target", diagnostics={"reason": "hex"})
    if not _PROJECT_RE.fullmatch(out["project"]) or not _HOST_RE.fullmatch(
        out["public_host"]
    ):
        raise ProbeError(
            "unsafe_target", stage="target", diagnostics={"reason": "name"}
        )
    if (
        not _BRANCH_RE.fullmatch(out["production_branch"])
        or ".." in out["production_branch"].split("/")
        or out["production_branch"].startswith("/")
        or out["production_branch"].endswith("/")
    ):
        raise ProbeError(
            "unsafe_target", stage="target", diagnostics={"reason": "branch"}
        )
    for key in (
        "source_deployment_id",
        "expected_canonical_id",
        "expected_latest_id",
    ):
        if not _ID_RE.fullmatch(out[key]) or ".." in out[key]:
            raise ProbeError(
                "unsafe_target", stage="target", diagnostics={"reason": "id"}
            )
    return out


def _api_path(account: str, project: str, *suffix: str) -> str:
    path = "/accounts/%s/pages/projects/%s" % (_quote(account), _quote(project))
    for part in suffix:
        path += "/" + _quote(part)
    return path


def _path_ok(path: str) -> bool:
    return (
        isinstance(path, str)
        and path.startswith("/")
        and "://" not in path
        and "\\" not in path
        and "\n" not in path
        and "\r" not in path
        and "\x00" not in path
        and "?" not in path
        and "#" not in path
        and ".." not in path.split("/")
    )


def _envelope(
    request: Request,
    method: str,
    path: str,
    slot: str,
    stages: list[str],
    http: list[dict[str, Any]],
    *,
    body: Any = None,
    bearer: str | None = None,
    phase: str,
) -> dict[str, Any]:
    if method not in ("GET", "POST") or not _path_ok(path):
        _fail("api_failure", slot, stages, http, reason="path", phase=phase)
    if method == "GET" and (body is not None or bearer is not None):
        _fail("api_failure", slot, stages, http, reason="path", phase=phase)
    if method == "POST" and path != CHECK_MISSING_PATH:
        _fail("api_failure", slot, stages, http, reason="path", phase=phase)
    try:
        if bearer is None:
            status, payload = request(method, path, body)
        else:
            status, payload = request(method, path, body, bearer=bearer)
    except ProbeError:
        raise
    except Exception:
        http.append({"slot": slot, "method": method, "status": 0})
        _fail("api_failure", slot, stages, http, reason="network", phase=phase)
    if isinstance(status, bool) or not isinstance(status, int) or not isinstance(
        payload, (bytes, bytearray)
    ):
        http.append({"slot": slot, "method": method, "status": 0})
        _fail("api_failure", slot, stages, http, reason="network", phase=phase)
    status_int = int(status)
    http.append({"slot": slot, "method": method, "status": status_int})
    if status_int != 200:
        _fail("api_failure", slot, stages, http, reason="http_status", phase=phase)
    payload = bytes(payload)
    try:
        data = _loads(payload)
    except _DuplicateKey:
        _fail(
            "malformed_response", slot, stages, http, reason="duplicate_key", phase=phase
        )
    except (UnicodeError, json.JSONDecodeError):
        _fail("malformed_response", slot, stages, http, reason="json", phase=phase)
    if not isinstance(data, dict) or data.get("success") is not True:
        code = "malformed_response" if not isinstance(data, dict) else "api_failure"
        reason = "json" if code == "malformed_response" else "rejected"
        _fail(code, slot, stages, http, reason=reason, phase=phase)
    return data


def _require_project(
    result: dict[str, Any],
    target: dict[str, str],
    stages: list[str],
    http: list[dict[str, Any]],
    *,
    phase: str,
) -> dict[str, Any]:
    if not isinstance(result, dict):
        _fail("malformed_response", "project", stages, http, reason="json", phase=phase)
    identity = _identity(result)
    if identity is None:
        _fail(
            "malformed_response",
            "project",
            stages,
            http,
            reason="identity",
            phase=phase,
        )
    assert identity is not None
    if identity["name"] != target["project"]:
        _fail(
            "mismatched_evidence",
            "project",
            stages,
            http,
            reason="project_name",
            phase=phase,
        )
    if identity["production_branch"] != target["production_branch"]:
        _fail(
            "mismatched_evidence",
            "project",
            stages,
            http,
            reason="production_branch",
            phase=phase,
        )
    if target["public_host"] not in identity["domains"]:
        _fail(
            "mismatched_evidence",
            "project",
            stages,
            http,
            reason="public_host",
            phase=phase,
        )
    if identity["canonical_id"] != target["expected_canonical_id"]:
        _fail(
            "mismatched_evidence",
            "project",
            stages,
            http,
            reason="canonical_id",
            phase=phase,
        )
    if identity["latest_id"] != target["expected_latest_id"]:
        _fail(
            "mismatched_evidence",
            "project",
            stages,
            http,
            reason="latest_id",
            phase=phase,
        )
    return identity


def _canonicalize_key(key: str) -> str | None:
    if (
        not isinstance(key, str)
        or "\\" in key
        or "\x00" in key
        or "\n" in key
        or "\r" in key
    ):
        return None
    text = key
    if not text.startswith("/"):
        text = "/" + text
    parts = [part for part in text.split("/") if part != ""]
    if any(part in (".", "..") for part in parts):
        return None
    return "/" + "/".join(parts)


def _require_file(
    deployment: Any,
    target: dict[str, str],
    stages: list[str],
    http: list[dict[str, Any]],
    *,
    phase: str,
) -> None:
    files = deployment.get("files") if isinstance(deployment, dict) else None
    if not isinstance(files, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in files.items()
    ):
        _fail(
            "malformed_response",
            "file_map",
            stages,
            http,
            reason="files",
            phase=phase,
        )
    assert isinstance(files, dict)
    aliases = []
    for key in files:
        canon = _canonicalize_key(key)
        if canon is None:
            _fail(
                "malformed_response",
                "file_map",
                stages,
                http,
                reason="files",
                phase=phase,
            )
        if key != ASSET_OWNERS_PATH and canon == ASSET_OWNERS_PATH:
            aliases.append(key)
    if aliases:
        _fail(
            "mismatched_evidence",
            "file_map",
            stages,
            http,
            reason="file_ambiguous",
            phase=phase,
        )
    if ASSET_OWNERS_PATH not in files:
        _fail(
            "mismatched_evidence",
            "file_map",
            stages,
            http,
            reason="file_missing",
            phase=phase,
        )
    if files[ASSET_OWNERS_PATH] != target["expected_file_hash"]:
        _fail(
            "mismatched_evidence",
            "file_map",
            stages,
            http,
            reason="file_hash",
            phase=phase,
        )


def _result_info_complete(payload: dict[str, Any]) -> bool:
    if "result_info" not in payload:
        return True
    info = payload.get("result_info")
    if not isinstance(info, dict):
        return False
    cursor = info.get("cursor") if "cursor" in info else ""
    if cursor not in (None, ""):
        return False
    total = info.get("total_pages")
    page = info.get("page")
    if total is not None or page is not None:
        if not isinstance(total, int) or isinstance(total, bool):
            return False
        if not isinstance(page, int) or isinstance(page, bool):
            return False
        if total != 1 or page != 1:
            return False
    return True


def probe_owner_availability(
    target: Any,
    request: Request,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    """Return preflight or probe outcome. Never mints a token unless execute is True.

    Success keys include availability: None, "available", or "missing".
    Failures raise ProbeError. Post-probe identity change raises ProbeError
    with drift=True and code concurrent_drift. This function never calls a
    deployment, upload, upsert-hashes, delete, or rollback endpoint.
    """
    stages: list[str] = []
    http: list[dict[str, Any]] = []
    phase = "probe" if execute is True else "preflight"
    if execute is not True and execute is not False:
        _fail("unsafe_target", "target", stages, http, reason="execute", phase="preflight")
    if not callable(request):
        _fail("unsafe_target", "target", stages, http, reason="request", phase=phase)
    normalized = _validate_target(target)
    project_path = _api_path(normalized["account_id"], normalized["project"])
    files_path = (
        project_path
        + "/deployments/%s/files" % _quote(normalized["source_deployment_id"])
    )
    token_path = project_path + "/upload-token"

    project_payload = _envelope(
        request, "GET", project_path, "project", stages, http, phase=phase
    )
    if not _result_info_complete(project_payload):
        _fail(
            "malformed_response",
            "project",
            stages,
            http,
            reason="incomplete",
            phase=phase,
        )
    result = project_payload.get("result")
    identity = _require_project(result, normalized, stages, http, phase=phase)
    stages.append("project")

    files_payload = _envelope(
        request, "GET", files_path, "file_map", stages, http, phase=phase
    )
    if not _result_info_complete(files_payload):
        _fail(
            "malformed_response",
            "file_map",
            stages,
            http,
            reason="incomplete",
            phase=phase,
        )
    _require_file(
        files_payload.get("result"), normalized, stages, http, phase=phase
    )
    stages.append("file_map")

    if execute is False:
        return {
            "availability": None,
            "phase": "preflight",
            "drift": False,
            "file": ASSET_OWNERS_PATH,
            "stages": list(stages),
            "http": [dict(row) for row in http],
        }

    token_payload = _envelope(
        request, "GET", token_path, "upload_token", stages, http, phase=phase
    )
    token_result = token_payload.get("result")
    jwt = token_result.get("jwt") if isinstance(token_result, dict) else None
    if not isinstance(jwt, str) or not jwt or any(ch.isspace() for ch in jwt):
        _fail(
            "malformed_response",
            "upload_token",
            stages,
            http,
            reason="jwt",
            phase=phase,
        )
    assert isinstance(jwt, str)
    stages.append("upload_token")
    try:
        missing_payload = _envelope(
            request,
            "POST",
            CHECK_MISSING_PATH,
            "check_missing",
            stages,
            http,
            body={"hashes": [normalized["expected_file_hash"]]},
            bearer=jwt,
            phase=phase,
        )
    finally:
        jwt = ""
        del jwt
    missing = missing_payload.get("result")
    if not isinstance(missing, list) or not all(isinstance(item, str) for item in missing):
        _fail(
            "malformed_response",
            "check_missing",
            stages,
            http,
            reason="check_missing",
            phase=phase,
        )
    assert isinstance(missing, list)
    expected = normalized["expected_file_hash"]
    if missing == []:
        availability = "available"
    elif missing == [expected]:
        availability = "missing"
    else:
        _fail(
            "malformed_response",
            "check_missing",
            stages,
            http,
            reason="check_missing",
            phase=phase,
        )
    stages.append("check_missing")

    recheck_payload = _envelope(
        request, "GET", project_path, "project_recheck", stages, http, phase=phase
    )
    if not _result_info_complete(recheck_payload):
        _fail(
            "malformed_response",
            "project_recheck",
            stages,
            http,
            reason="incomplete",
            phase=phase,
        )
    recheck_result = recheck_payload.get("result")
    if not isinstance(recheck_result, dict):
        _fail(
            "malformed_response",
            "project_recheck",
            stages,
            http,
            reason="json",
            phase=phase,
        )
    recheck = _identity(recheck_result)
    if recheck is None or recheck != identity:
        _fail(
            "concurrent_drift",
            "project_recheck",
            stages,
            http,
            drift=True,
            reason="identity",
            phase=phase,
        )
    stages.append("project_recheck")
    return {
        "availability": availability,
        "phase": "probe",
        "drift": False,
        "file": ASSET_OWNERS_PATH,
        "stages": list(stages),
        "http": [dict(row) for row in http],
    }


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _git_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["LC_ALL"] = "C"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        env=_git_env(),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def _require_approved_source(sha: str) -> None:
    root = _source_root()
    try:
        top = _git(root, ["rev-parse", "--show-toplevel"])
        symbolic = _git(root, ["symbolic-ref", "--quiet", "HEAD"])
        head = _git(root, ["rev-parse", "--verify", "HEAD"])
        status = _git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
        git_dir = _git(root, ["rev-parse", "--absolute-git-dir"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise _CliRefuse("source worktree is not approved") from exc
    if (
        top.returncode != 0
        or head.returncode != 0
        or status.returncode != 0
        or git_dir.returncode != 0
    ):
        raise _CliRefuse("source worktree is not approved")
    try:
        top_path = Path(top.stdout.strip()).resolve()
    except OSError as exc:
        raise _CliRefuse("source worktree is not approved") from exc
    if top_path != root:
        raise _CliRefuse("source worktree is not approved")
    if symbolic.returncode != 1:
        raise _CliRefuse("source worktree is not approved")
    if head.stdout.strip() != sha or status.stdout != "":
        raise _CliRefuse("source worktree is not approved")
    git_path = Path(git_dir.stdout.strip())
    for name in (
        "rebase-merge",
        "rebase-apply",
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "BISECT_LOG",
    ):
        if (git_path / name).exists():
            raise _CliRefuse("source worktree is not approved")


def parse_env(text: str) -> dict[str, str]:
    """Read only the two literal Cloudflare assignments, without shell evaluation."""
    out: dict[str, str] = {}
    selected = re.compile(r"^(?:export\s+)?(CLOUDFLARE_ACCOUNT_ID|CLOUDFLARE_API_TOKEN)(?=$|[^A-Za-z0-9_])")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = selected.match(line)
        if match is None:
            continue
        key = match.group(1)
        rest = line[match.end():].lstrip()
        if key in out or not rest.startswith("=") or raw.endswith("\\") or "\x00" in raw:
            raise _CliRefuse("env syntax is unexpected")
        value = rest[1:].strip()
        if any(ch in value for ch in "$`;|&<>"):
            raise _CliRefuse("env syntax is unexpected")
        try:
            tokens = shlex.split(value, comments=True, posix=True)
        except ValueError as exc:
            raise _CliRefuse("env syntax is unexpected") from exc
        if len(tokens) > 1:
            raise _CliRefuse("env syntax is unexpected")
        out[key] = tokens[0] if tokens else ""
    return out


def _read_private_text(path: Path) -> str:
    if not path.is_absolute():
        raise _CliRefuse("path is not a private file")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise _CliRefuse("path is not a private file") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise _CliRefuse("path is not a private file")
        if stat.S_IMODE(info.st_mode) not in (0o600, 0o400):
            raise _CliRefuse("path is not a private file")
        if info.st_size > 1024 * 1024:
            raise _CliRefuse("path is unreadable")
        data = os.read(fd, info.st_size)
    finally:
        os.close(fd)
    try:
        return data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise _CliRefuse("path is unreadable") from exc


def _load_json_object(text: str) -> dict[str, Any]:
    try:
        data = _loads(text.encode("utf-8")) if text.strip() else None
    except (json.JSONDecodeError, _DuplicateKey, UnicodeError) as exc:
        raise _CliRefuse("record is unreadable") from exc
    if not isinstance(data, dict):
        raise _CliRefuse("record is unreadable")
    return data


def _present(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _cross_check(
    config: dict[str, Any], env: dict[str, str], target: dict[str, str]
) -> None:
    project = config.get("pages_project")
    host = config.get("public_host")
    if not isinstance(project, str) or project != target["project"]:
        raise _CliRefuse("config does not match the target record")
    if not isinstance(host, str) or host != target["public_host"]:
        raise _CliRefuse("config does not match the target record")
    for raw in (os.environ.get("CLOUDFLARE_ACCOUNT_ID"), env.get("CLOUDFLARE_ACCOUNT_ID"), config.get("cloudflare_account_id")):
        present = _present(raw) if isinstance(raw, str) or raw is None else None
        if raw is not None and not isinstance(raw, str):
            raise _CliRefuse("account does not match the target record")
        if present is None:
            continue
        if present != target["account_id"]:
            raise _CliRefuse("account does not match the target record")


def _load_record(path: Path, *, probe: bool) -> dict[str, Any]:
    try:
        data = _load_json_object(_read_private_text(path))
    except _CliRefuse as exc:
        if exc.reason == "record is unreadable":
            raise
        raise _CliRefuse("record is unreadable") from exc
    unknown = set(data) - set(TARGET_KEYS) - RECORD_EXTRA
    if unknown:
        raise _CliRefuse("record is unreadable")
    missing = [key for key in TARGET_KEYS if key not in data]
    if missing:
        raise _CliRefuse("record is unreadable")
    target = {key: data[key] for key in TARGET_KEYS}
    _validate_target(target)
    sha = data.get("approved_source_sha")
    if sha is not None and (not isinstance(sha, str) or not _SHA40.fullmatch(sha)):
        raise _CliRefuse("record is unreadable")
    if probe and not isinstance(sha, str):
        raise _CliRefuse("record is unreadable")
    provenance = data.get("provenance")
    if provenance is not None:
        if (
            not isinstance(provenance, str)
            or not _PROVENANCE_RE.fullmatch(provenance)
            or _HEX32_RUN.search(provenance)
        ):
            raise _CliRefuse("record is unreadable")
    return data


def _inside_git(path: Path) -> bool:
    raw = path
    cur = raw
    seen = set()
    while cur not in seen:
        seen.add(cur)
        marker = cur / ".git"
        if marker.is_file() or marker.is_dir() or marker.is_symlink():
            return True
        if cur.parent == cur:
            break
        cur = cur.parent
    env = _git_env()
    try:
        proc = subprocess.run(
            ["git", "-C", str(raw), "rev-parse", "--is-inside-work-tree"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _fd_has_git(dir_fd: int) -> bool:
    cur = os.dup(dir_fd)
    try:
        while True:
            try:
                os.lstat(".git", dir_fd=cur)
                return True
            except OSError:
                pass
            try:
                parent = os.open("..", _DIR_FLAGS, dir_fd=cur)
            except OSError:
                return True
            try:
                if os.path.samestat(os.fstat(cur), os.fstat(parent)):
                    os.close(parent)
                    return False
            except OSError:
                os.close(parent)
                return True
            os.close(cur)
            cur = parent
    finally:
        try:
            os.close(cur)
        except OSError:
            pass


def _output_parent(path: Path) -> int:
    if not path.is_absolute() or not path.name or path.name in (".", ".."):
        raise _CliRefuse("output is unreadable")
    if "/" in path.name or "\0" in path.name or "\n" in path.name or "\r" in path.name:
        raise _CliRefuse("output is unreadable")
    if _HEX32_RUN.search(str(path)):
        raise _CliRefuse("output is unreadable")
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        raise _CliRefuse("output parent is not private")
    try:
        resolved = Path(os.path.realpath(parent))
    except OSError as exc:
        raise _CliRefuse("output parent is not private") from exc
    source = _source_root()
    if _is_inside(resolved, source) or _inside_git(resolved):
        raise _CliRefuse("output is inside a git worktree")
    try:
        info = parent.stat()
    except OSError as exc:
        raise _CliRefuse("output parent is not private") from exc
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise _CliRefuse("output parent is not private")
    try:
        fd = _open_resolved(str(resolved))
    except OSError as exc:
        raise _CliRefuse("output parent is not private") from exc
    try:
        held = os.fstat(fd)
        if (
            not stat.S_ISDIR(held.st_mode)
            or held.st_uid != os.geteuid()
            or stat.S_IMODE(held.st_mode) != 0o700
            or _fd_has_git(fd)
        ):
            raise _CliRefuse("output parent is not private")
        try:
            os.lstat(path.name, dir_fd=fd)
        except FileNotFoundError:
            pass
        else:
            raise _CliRefuse("output already exists")
        return fd
    except Exception:
        os.close(fd)
        raise


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _open_resolved(raw: str) -> int:
    parts = [part for part in raw.split("/") if part]
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts:
            if part in (".", "..") or "/" in part or "\0" in part:
                raise OSError("path component is not a real directory")
            nxt = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nxt
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("not a directory")
        return fd
    except Exception:
        os.close(fd)
        raise


def _write_private(path: Path, payload: bytes) -> None:
    parent_fd = _output_parent(path)
    tmp_name = None
    try:
        fd = None
        for _ in range(8):
            candidate = ".owner-availability." + os.urandom(8).hex()
            try:
                fd = os.open(
                    candidate,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=parent_fd,
                )
            except FileExistsError:
                continue
            tmp_name = candidate
            break
        if fd is None or tmp_name is None:
            raise _CliRefuse("output is unreadable")
        try:
            offset = 0
            while offset < len(payload):
                wrote = os.write(fd, payload[offset:])
                if wrote <= 0:
                    raise OSError("short write")
                offset += wrote
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(
                tmp_name,
                path.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise _CliRefuse("output already exists") from exc
        os.fsync(parent_fd)
        final = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        try:
            info = os.fstat(final)
            if stat.S_IMODE(info.st_mode) != 0o600 or not stat.S_ISREG(info.st_mode):
                raise _CliRefuse("output is unreadable")
        finally:
            os.close(final)
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name, dir_fd=parent_fd)
            except OSError:
                pass
        os.close(parent_fd)




class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def _admin_request(token: str, allowed: frozenset[str]) -> Request:
    def request(
        method: str,
        api_path: str,
        body: Any = None,
        *,
        bearer: str | None = None,
    ) -> tuple[int, bytes]:
        if method not in ("GET", "POST") or api_path not in allowed or not _path_ok(api_path):
            return 0, b""
        if method == "POST" and api_path != CHECK_MISSING_PATH:
            return 0, b""
        if method == "GET" and body is not None:
            return 0, b""
        secret = token if bearer is None else bearer
        if not isinstance(secret, str) or not _TOKEN_RE.fullmatch(secret):
            return 0, b""
        url = API_ORIGIN + API_PREFIX + api_path
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.cloudflare.com"
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            return 0, b""
        data = None
        headers = {"Authorization": "Bearer " + secret, "Accept": "application/json"}
        if body is not None:
            if not isinstance(body, dict):
                return 0, b""
            try:
                data = json.dumps(body, separators=(",", ":"), sort_keys=True).encode(
                    "ascii"
                )
            except (TypeError, UnicodeError, ValueError):
                return 0, b""
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirect(),
        )
        try:
            with opener.open(req, timeout=TIMEOUT_SECONDS) as response:
                return response.status, _read_limited(response)
        except urllib.error.HTTPError as exc:
            try:
                return exc.code if isinstance(exc.code, int) else 0, b""
            finally:
                exc.close()
        except Exception:
            return 0, b""

    return request


def _read_limited(response: Any) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = response.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_BODY:
            return b""
        chunks.append(chunk)
    return b"".join(chunks)




def _stdout(outcome: str, output: Path, digest: str) -> None:
    line = "outcome=%s evidence=%s evidence_sha256=%s" % (
        outcome,
        shlex.quote(str(output)),
        digest,
    )
    print(line)


def _refuse(reason: str) -> int:
    print("probe_owner_availability: %s" % reason, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="probe_owner_availability.py",
        description="Check the approved historical owner-file mapping; preflight is the default.",
        allow_abbrev=False,
    )
    parser.add_argument("--target-record", required=True, help="Private approved target record")
    parser.add_argument("--config", required=True, help="Private forge config")
    parser.add_argument("--env", required=True, help="Private forge environment file")
    parser.add_argument("--output", required=True, help="New private evidence file outside Git")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Request upload token and check availability; separate operator approval required",
    )

    def _usage(_message: str | None = None) -> None:
        print("probe_owner_availability: usage", file=sys.stderr)
        raise SystemExit(1)

    parser.error = _usage  # type: ignore[method-assign]
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        if exc.code not in (0, None):
            return 1
        return 0
    output = Path(args.output).expanduser()
    try:
        parent_fd = _output_parent(output)
    except _CliRefuse as exc:
        return _refuse(exc.reason)
    os.close(parent_fd)
    try:
        config_text = _read_private_text(Path(args.config).expanduser())
        env_text = _read_private_text(Path(args.env).expanduser())
        record = _load_record(Path(args.target_record).expanduser(), probe=args.probe)
        try:
            config = _load_json_object(config_text)
        except _CliRefuse as exc:
            raise _CliRefuse("config is unreadable") from exc
        env = parse_env(env_text)
        target = {key: record[key] for key in TARGET_KEYS}
        _cross_check(config, env, target)
        if args.probe:
            _require_approved_source(record["approved_source_sha"])
        token = env.get("CLOUDFLARE_API_TOKEN", "")
        if not _TOKEN_RE.fullmatch(token):
            raise _CliRefuse("credential missing")
    except _CliRefuse as exc:
        return _refuse(exc.reason)
    except ProbeError:
        return _refuse("record is unreadable")

    allowed = frozenset(
        (
            _api_path(target["account_id"], target["project"]),
            _api_path(target["account_id"], target["project"])
            + "/deployments/%s/files" % _quote(target["source_deployment_id"]),
            _api_path(target["account_id"], target["project"]) + "/upload-token",
            CHECK_MISSING_PATH,
        )
    )
    transport = _admin_request(token, allowed)
    del token
    source_checked = bool(args.probe)
    provenance = record.get("provenance") if isinstance(record.get("provenance"), str) else None
    try:
        result = probe_owner_availability(
            target, transport, execute=True if args.probe else False
        )
    except ProbeError as exc:
        diag = exc.diagnostics if isinstance(exc.diagnostics, dict) else {}
        outcome = "failed"
        availability = None
        drift = exc.drift is True
        failure_code = exc.code
        stage = exc.stage
        reason = diag.get("reason") if isinstance(diag.get("reason"), str) else None
        code = 1
    else:
        diag = result
        availability = result.get("availability")
        outcome = "preflight" if availability is None else str(availability)
        drift = False
        failure_code = stage = reason = None
        code = 0
    payload = {
        "schema_version": 1,
        "kind": "owner-availability-probe",
        "collected_at": _utc_now(),
        "phase": diag.get("phase") if isinstance(diag.get("phase"), str) else None,
        "outcome": outcome,
        "availability": availability,
        "drift": drift,
        "failure_code": failure_code,
        "stage": stage,
        "reason": reason,
        "file": ASSET_OWNERS_PATH,
        "stages": list(diag.get("stages") or []),
        "http": list(diag.get("http") or []),
        "source_sha_checked": source_checked,
        "g1b_closed": False,
        "bytes_recovered": False,
        "side_effect_freedom": "inference",
    }
    if provenance is not None:
        payload["provenance"] = provenance
    payload["target"] = target
    if args.probe:
        payload["approved_source_sha"] = record["approved_source_sha"]
    encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    try:
        _write_private(output, encoded)
    except _CliRefuse as exc:
        return _refuse(exc.reason)
    except OSError:
        return _refuse("output is unreadable")
    digest = hashlib.sha256(encoded).hexdigest()
    _stdout(outcome, output, digest)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
