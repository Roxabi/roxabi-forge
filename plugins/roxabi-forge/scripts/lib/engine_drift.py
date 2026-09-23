#!/usr/bin/env python3
"""Which roxabi-forge engine a publish deploys, and whether production already
runs a newer one.

Why this exists: a deploy is the SSOT snapshot built by THIS plugin's scripts
plus an engine (functions/, site/, wrangler.toml) materialised from forge_repo.
Cloning `main` tied neither to the other, and production recorded nothing
about what it ran, so a machine with an old plugin could silently replace a
newer engine. Three rules close that:

  * release mode (default): the engine is the tag `roxabi-forge/v<P>`, where P
    is the version of the plugin running publish.sh — scripts and engine are
    the same release by construction;
  * dev mode (forge_repo names a local checkout): `git archive HEAD`, stamped
    `<version>+dev.<sha7>`, refused when the checkout's version differs from
    P unless publish.sh itself runs from that checkout;
  * every deploy stamps `roxabi-forge/v<version>` as the Pages commit message,
    and the gate refuses a publish whose version is older than that stamp.

Subcommands (all read-only):

  resolve     shell assignments ENGINE_* describing the engine to deploy
  prod-stamp  JSON: the version stamp of the production deployment
  gate        shell assignments DRIFT_*: the verdict for prod JSON on stdin
  summary     one doctor line: prod <L> · plugin <P> · <state>

Python 3.9 stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

# Module import, not `from load_config import ...`: tests patch attributes on
# load_config (detect_engine_checkout, _cf_api), and a from-import would bind
# the unpatched originals at import time.
import load_config as _lc  # noqa: E402

# Tag and deploy stamp share one prefix, so the stamp read back from
# production names exactly the tag a release-mode publish cloned.
STAMP_PREFIX = "roxabi-forge/v"
_STAMP_RE = re.compile(r"roxabi-forge/v(\d+\.\d+\.\d+)(\+dev\.[0-9a-f]+)?")
_SEMVER_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
# Where the engine's own plugin version lives inside a checkout. The same file
# check_plugin_versions.py keeps consistent with every harness manifest.
ENGINE_PACKAGE_JSON = "plugins/roxabi-forge/package.json"

# Printed with every "update the plugin" refusal. Verified against
# `claude plugin --help` / `claude plugin marketplace --help` and
# `omp plugin marketplace` (subcommands add, remove, update, list).
UPDATE_COMMANDS = (
    "claude plugin marketplace update roxabi-forge",
    "claude plugin update roxabi-forge@roxabi-forge",
    "omp plugin marketplace update roxabi-forge",
    "omp plugin upgrade roxabi-forge@roxabi-forge",
)


class EngineError(Exception):
    """The engine to deploy cannot be determined; publish must not guess."""


# ------------------------------------------------------------------ versions


def parse_version(text: str) -> tuple[int, int, int] | None:
    """X.Y.Z as an int triple, or None. Nothing else is a plugin version."""
    m = _SEMVER_RE.fullmatch((text or "").strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _version_from_package(raw: str, where: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EngineError(f"{where} is not valid JSON ({exc})") from exc
    version = data.get("version") if isinstance(data, dict) else None
    if not isinstance(version, str) or parse_version(version) is None:
        raise EngineError(f"{where} carries no X.Y.Z version (got {version!r})")
    return version


def read_plugin_version(root: Path | None = None) -> str:
    """Version of the plugin running this code (its package.json)."""
    path = (root or _lc.PLUGIN_ROOT) / "package.json"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EngineError(f"plugin version unreadable: {path} ({exc})") from exc
    return _version_from_package(raw, str(path))


def release_tag(version: str) -> str:
    return f"{STAMP_PREFIX}{version}"


def format_stamp(version: str, dev_sha7: str = "") -> str:
    """Pages commit message for a deploy of `version` (dev: `+dev.<sha7>`)."""
    return release_tag(version) + (f"+dev.{dev_sha7}" if dev_sha7 else "")


def parse_stamp(message: Any) -> dict[str, Any] | None:
    """Stamp fields, or None when `message` is not exactly one of our stamps.

    Full match on purpose: a dashboard deploy or a git-triggered build carries
    an arbitrary commit message, and reading a version out of the middle of it
    would invent a production engine version nobody stamped.
    """
    if not isinstance(message, str):
        return None
    m = _STAMP_RE.fullmatch(message.strip())
    if not m:
        return None
    version = m.group(1)
    return {
        "version": version,
        "base": parse_version(version),
        "dev": m.group(2) or "",
        "stamp": m.group(0),
    }


# ------------------------------------------------------------------- compare


def compare(prod: dict[str, Any], local_stamp: str) -> dict[str, Any]:
    """Classify production against the stamp this publish would write.

    `prod` is a prod-stamp payload with ok True. Returns verdict, level
    (ok/info/warn/refuse), a human message and the doctor label.
    """
    local = parse_stamp(local_stamp)
    if local is None:
        # The shell always builds this from format_stamp; anything else is a
        # caller bug and must not be compared as if it were a version.
        raise EngineError(f"local engine stamp is malformed: {local_stamp!r}")
    lv = local["version"]
    if not prod.get("has_deployment", True):
        return {
            "verdict": "no_deployment",
            "level": "info",
            "prod": None,
            "message": f"production has no deployment yet — this publish stamps {local['stamp']}",
            "label": "stamped on next publish",
        }
    remote = parse_stamp(prod.get("stamp"))
    if remote is None:
        return {
            "verdict": "unknown",
            "level": "warn",
            "prod": None,
            "message": (
                "production engine version unknown (deployed before version "
                f"stamping) — this publish stamps it as {local['stamp']}"
            ),
            "label": "stamped on next publish",
        }
    rv = remote["version"]
    base = {"verdict": "", "prod": remote["stamp"]}
    if remote["base"] > local["base"]:
        return {
            **base,
            "verdict": "newer_prod",
            "level": "refuse",
            "message": (
                f"production runs roxabi-forge {rv}, this plugin is {lv} — "
                "update the plugin:"
            ),
            "label": "update plugin",
        }
    if remote["base"] < local["base"]:
        return {
            **base,
            "verdict": "upgrade",
            "level": "info",
            "message": f"engine upgrade {rv} → {lv}",
            "label": "upgrade on next publish",
        }
    # Same X.Y.Z: only the dev suffix can differ.
    if remote["dev"] and not local["dev"]:
        return {
            **base,
            "verdict": "release_replaces_dev",
            "level": "info",
            "message": f"release replaces dev build ({remote['stamp']} → {local['stamp']})",
            "label": "release replaces dev build on next publish",
        }
    if local["dev"] and not remote["dev"]:
        return {
            **base,
            "verdict": "dev_replaces_release",
            "level": "warn",
            "message": (
                f"dev build replaces the {rv} release in production "
                f"({remote['stamp']} → {local['stamp']})"
            ),
            "label": "dev build would replace the release",
        }
    if remote["dev"] and remote["dev"] != local["dev"]:
        return {
            **base,
            "verdict": "aligned",
            "level": "info",
            "message": f"dev build replaces dev build ({remote['stamp']} → {local['stamp']})",
            "label": "aligned",
        }
    return {
        **base,
        "verdict": "aligned",
        "level": "ok",
        "message": f"engine aligned with production ({remote['stamp']})",
        "label": "aligned",
    }


def gate(
    prod: dict[str, Any] | None,
    local_stamp: str,
    *,
    allow_downgrade: bool = False,
    allow_unverified: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Publish policy over compare(): action proceed/refuse + level + message.

    Mirrors the hub drift guard: a proven downgrade refuses in a dry run too
    (the dry run is a gate), while an unverifiable production state becomes a
    "would refuse" warning there, because a dry run changes nothing.
    """
    if not prod or not prod.get("ok"):
        err = str((prod or {}).get("error") or "no answer from the Pages API")
        reason = f"production engine version unverified ({err})"
        # --allow-engine-downgrade never lifts this: it accepts a KNOWN older
        # engine, and nothing is known here. --allow-unverified is the flag
        # that already means "proceed although the live state cannot be read".
        if allow_unverified:
            return {
                "action": "proceed",
                "level": "warn",
                "verdict": "unverified",
                "message": f"{reason} — proceeding because --allow-unverified was passed",
            }
        if dry_run:
            return {
                "action": "proceed",
                "level": "warn",
                "verdict": "unverified",
                "message": (
                    f"would refuse: {reason} — a real publish needs the Pages "
                    "API to answer, or --allow-unverified"
                ),
            }
        return {
            "action": "refuse",
            "level": "refuse",
            "verdict": "unverified",
            "message": (
                f"{reason} — cannot prove this publish does not downgrade the "
                "production engine. Retry when the Pages API answers; or pass "
                "--allow-unverified to deploy anyway"
            ),
        }
    result = compare(prod, local_stamp)
    if result["verdict"] == "newer_prod":
        if allow_downgrade:
            return {
                "action": "proceed",
                "level": "warn",
                "verdict": "newer_prod",
                "message": (
                    f"engine downgrade {result['prod']} → {local_stamp} — "
                    "proceeding because --allow-engine-downgrade was passed"
                ),
            }
        lines = [result["message"]]
        lines += [f"    {cmd}" for cmd in UPDATE_COMMANDS]
        lines.append(
            "  then re-run the publish (or pass --allow-engine-downgrade to "
            "deploy the older engine on purpose)"
        )
        return {
            "action": "refuse",
            "level": "refuse",
            "verdict": "newer_prod",
            "message": "\n".join(lines),
        }
    return {
        "action": "proceed",
        "level": result["level"],
        "verdict": result["verdict"],
        "message": result["message"],
    }


# ----------------------------------------------------------- production read


def production_stamp(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Version stamp of the production (canonical) Pages deployment.

    canonical_deployment, not latest_deployment: a preview-branch deploy can
    be the latest while production still serves an older engine, and the
    gate protects production. Never returns or logs the API token.
    """
    cfg = cfg or _lc.load_config()
    project = str(cfg.get("pages_project") or "forge")
    token = _lc.resolve_api_token()
    acct = _lc.resolved_account_id(cfg)
    if not token or not acct:
        missing = "CLOUDFLARE_API_TOKEN" if not token else "CLOUDFLARE_ACCOUNT_ID"
        return {"ok": False, "error_kind": "auth_missing", "error": f"{missing} missing"}
    code, data, err = _lc._cf_api("GET", f"/accounts/{acct}/pages/projects/{project}", token)
    if code == 0:
        return {"ok": False, "error_kind": "unreachable", "error": err or "network error"}
    if code != 200 or not data or not data.get("success"):
        return {
            "ok": False,
            "error_kind": "api_error",
            "error": f"HTTP {code}: {_lc._cf_err_msg(data, err)}",
        }
    canonical = (data.get("result") or {}).get("canonical_deployment")
    if not isinstance(canonical, dict) or not canonical.get("id"):
        return {"ok": True, "has_deployment": False, "deployment_id": "", "stamp": ""}
    meta = (canonical.get("deployment_trigger") or {}).get("metadata") or {}
    return {
        "ok": True,
        "has_deployment": True,
        "deployment_id": str(canonical.get("id") or ""),
        "stamp": str(meta.get("commit_message") or ""),
        "commit_hash": str(meta.get("commit_hash") or ""),
    }


# ------------------------------------------------------------ engine source


def _git_ok(repo: Path, *args: str) -> str | None:
    code, out = _lc._git(repo, *args)
    return out if code == 0 else None


def resolve_engine(forge_repo: str, *, plugin_version: str | None = None) -> dict[str, Any]:
    """The engine a publish with this forge_repo deploys. Raises EngineError.

    A URL (or nothing) is release mode. Anything else is a path, i.e. dev
    mode, and must be a committed git checkout: a mistyped path must never
    fall through to a clone of something else.
    """
    plugin_v = plugin_version or read_plugin_version()
    source = (forge_repo or "").strip() or _lc.CANONICAL_FORGE_REPO
    if _lc._is_repo_url(source):
        return {
            "mode": "release",
            "source": source,
            "version": plugin_v,
            "plugin_version": plugin_v,
            "ref": release_tag(plugin_v),
            "sha": "",
            "stamp": format_stamp(plugin_v),
            "dirty": False,
        }

    try:
        root = Path(source).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise EngineError(f"forge_repo path cannot be resolved: {source} ({exc})") from exc
    if not root.is_dir():
        raise EngineError(
            f"forge_repo path not found: {source} — dev mode deploys git archive "
            "HEAD of a checkout; clear forge_repo to deploy the plugin's release"
        )
    if _git_ok(root, "rev-parse", "--is-inside-work-tree") != "true":
        raise EngineError(
            f"forge_repo is not a git work tree: {source} — dev mode archives "
            "HEAD of a checkout; clear forge_repo to deploy the plugin's release"
        )
    sha = _git_ok(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if not sha:
        raise EngineError(f"forge_repo has no commit: {source} — dev mode deploys HEAD")
    sha = sha.splitlines()[0].strip()
    raw = _git_ok(root, "show", f"HEAD:{ENGINE_PACKAGE_JSON}")
    if raw is None:
        raise EngineError(
            f"forge_repo HEAD has no {ENGINE_PACKAGE_JSON}: {source} — "
            "not a roxabi-forge engine checkout"
        )
    version = _version_from_package(raw, f"{source} HEAD:{ENGINE_PACKAGE_JSON}")
    top = _git_ok(root, "rev-parse", "--show-toplevel")
    top_path = str(Path(top.splitlines()[0]).resolve()) if top else str(root)
    # The only way scripts and engine versions can legitimately differ is not
    # at all: when publish.sh runs from this very checkout they are the same
    # tree, so a mismatch there is just an uncommitted version bump.
    same_checkout = _lc.detect_engine_checkout() == top_path
    if version != plugin_v and not same_checkout:
        raise EngineError(
            f"forge_repo checkout {source} is roxabi-forge {version} at HEAD, but "
            f"this plugin is {plugin_v} — publish would run {plugin_v} scripts "
            f"against a {version} engine. Check out the matching commit, run "
            "publish.sh from that checkout, or clear forge_repo to deploy the "
            f"{plugin_v} release"
        )
    upstream = _git_ok(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream:
        # Local knowledge of the remote-tracking ref only: doctor and publish
        # never fetch, so "pushed" means "on the last fetched upstream".
        code, _ = _lc._git(root, "merge-base", "--is-ancestor", "HEAD", "@{u}")
        pushed: bool | None = code == 0
    else:
        pushed = None
    status = _git_ok(root, "status", "--porcelain")
    uncommitted = len([ln for ln in (status or "").splitlines() if ln.strip()])
    return {
        "mode": "dev",
        "source": str(root),
        "version": version,
        "plugin_version": plugin_v,
        "ref": "HEAD",
        "sha": sha,
        "stamp": format_stamp(version, sha[:7]),
        "dirty": True,
        "same_checkout": same_checkout,
        "upstream": upstream or "",
        "pushed": pushed,
        "uncommitted": uncommitted,
    }


def dev_warnings(engine: dict[str, Any]) -> list[str]:
    """Doctor warnings for a dev-mode engine: what will actually ship."""
    if engine.get("mode") != "dev":
        return []
    sha7 = engine["sha"][:7]
    out = [
        f"forge_repo is a local checkout (dev mode) — publish deploys HEAD "
        f"{sha7} of {engine['source']}, stamped {engine['stamp']}; "
        "clear forge_repo to deploy the plugin's release instead"
    ]
    if engine.get("uncommitted"):
        out.append(
            f"forge_repo has {engine['uncommitted']} uncommitted change(s) — "
            "they are NOT deployed (publish archives HEAD only)"
        )
    if engine.get("pushed") is False:
        out.append(
            f"forge_repo HEAD {sha7} is not on its upstream {engine['upstream']} "
            "— production would run a commit nobody else can check out; push it"
        )
    elif engine.get("pushed") is None:
        out.append(
            f"forge_repo HEAD {sha7} has no upstream — cannot tell whether "
            "production would run a pushed commit"
        )
    return out


def summary_line(cfg: dict[str, Any] | None = None, *, fetch: bool = True) -> dict[str, Any]:
    """Doctor --online line: `prod <L|unknown> · plugin <P> · <state>`.

    Never raises: the doctor must degrade to a report.
    """
    try:
        plugin_v = read_plugin_version()
    except EngineError as exc:
        return {"line": f"prod ? · plugin ? · {exc}", "verdict": "error"}
    cfg = cfg or _lc.load_config()
    try:
        local_stamp = resolve_engine(str(cfg.get("forge_repo") or ""), plugin_version=plugin_v)["stamp"]
    except EngineError:
        # The forge_repo problem is already a doctor issue; compare what the
        # plugin's own release would deploy.
        local_stamp = format_stamp(plugin_v)
    if not fetch:
        return {
            "line": f"prod unverified · plugin {plugin_v} · online preflight failed",
            "verdict": "unverified",
        }
    prod = production_stamp(cfg)
    if not prod.get("ok"):
        return {
            "line": f"prod unverified · plugin {plugin_v} · {prod.get('error') or 'Pages API error'}",
            "verdict": "unverified",
        }
    result = compare(prod, local_stamp)
    shown = result["prod"] or ("none" if result["verdict"] == "no_deployment" else "unknown")
    if shown.startswith(STAMP_PREFIX):
        shown = shown[len(STAMP_PREFIX):]
    return {
        "line": f"prod {shown} · plugin {plugin_v} · {result['label']}",
        "verdict": result["verdict"],
        "message": result["message"],
    }


# ------------------------------------------------------------------------ CLI


def _assign(pairs: dict[str, Any]) -> str:
    """KEY='value' lines for `eval` in bash; shlex.quote makes them inert."""
    return "".join(f"{k}={shlex.quote(str(v))}\n" for k, v in pairs.items())


def cmd_resolve(args: argparse.Namespace) -> int:
    # Exit 0 with ENGINE_ERROR set: the shell dies with the exact message
    # instead of a generic "python failed" that hides the reason.
    try:
        eng = resolve_engine(args.forge_repo)
    except EngineError as exc:
        sys.stdout.write(_assign({"ENGINE_ERROR": str(exc)}))
        return 0
    pushed = eng.get("pushed")
    sys.stdout.write(
        _assign(
            {
                "ENGINE_ERROR": "",
                "ENGINE_MODE": eng["mode"],
                "ENGINE_SOURCE": eng["source"],
                "ENGINE_VERSION": eng["version"],
                "ENGINE_REF": eng["ref"],
                "ENGINE_SHA": eng["sha"],
                "ENGINE_STAMP": eng["stamp"],
                "ENGINE_DIRTY": "true" if eng["dirty"] else "false",
                "ENGINE_PUSHED": "unknown" if pushed is None else ("yes" if pushed else "no"),
                "ENGINE_UPSTREAM": eng.get("upstream", ""),
                "ENGINE_UNCOMMITTED": eng.get("uncommitted", 0),
            }
        )
    )
    return 0


def cmd_prod_stamp(_args: argparse.Namespace) -> int:
    sys.stdout.write(json.dumps(production_stamp(), ensure_ascii=False) + "\n")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    raw = sys.stdin.read()
    try:
        prod = json.loads(raw) if raw.strip() else None
    except json.JSONDecodeError:
        prod = None  # unparseable = unverified: fail closed
    if prod is not None and not isinstance(prod, dict):
        prod = None
    try:
        verdict = gate(
            prod,
            args.stamp,
            allow_downgrade=args.allow_downgrade,
            allow_unverified=args.allow_unverified,
            dry_run=args.dry_run,
        )
    except EngineError as exc:
        verdict = {"action": "refuse", "level": "refuse", "verdict": "error", "message": str(exc)}
    sys.stdout.write(
        _assign(
            {
                "DRIFT_ACTION": verdict["action"],
                "DRIFT_LEVEL": verdict["level"],
                "DRIFT_VERDICT": verdict["verdict"],
                "DRIFT_MESSAGE": verdict["message"],
            }
        )
    )
    return 0


def cmd_summary(_args: argparse.Namespace) -> int:
    print(summary_line()["line"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="engine_drift.py", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    rs = sub.add_parser("resolve", help="ENGINE_* shell assignments")
    rs.add_argument("--forge-repo", default="")
    rs.set_defaults(func=cmd_resolve)
    sub.add_parser("prod-stamp", help="production version stamp JSON").set_defaults(
        func=cmd_prod_stamp
    )
    gt = sub.add_parser("gate", help="DRIFT_* shell assignments; prod JSON on stdin")
    gt.add_argument("--stamp", required=True, help="stamp this publish would write")
    gt.add_argument("--allow-downgrade", action="store_true")
    gt.add_argument("--allow-unverified", action="store_true")
    gt.add_argument("--dry-run", action="store_true")
    gt.set_defaults(func=cmd_gate)
    sub.add_parser("summary", help="doctor --online engine line").set_defaults(
        func=cmd_summary
    )
    return ap


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
