#!/usr/bin/env python3
"""Load roxabi-forge config: local override → example fallback.

Resolution order for the config *file*:
  1) FORGE_CONFIG env (explicit path)
  2) ~/.config/roxabi/forge/forge.config.json  (machine-local, per person)
  3) <plugin>/forge.config.example.json  (committed defaults)

Keys from example are always the base; local file deep-merges on top.
hub_root may still be empty after merge — doctor then fails until setup.

hub_root bootstrap (if empty string in config):
  a) HUB_ROOT env
  b) ~/.config/roxabi/forge/hub-root (shared machine config)
  c) leave empty (incomplete)

Usage as library:
  from load_config import load_config, artifacts_root, doctor

CLI:
  python3 load_config.py [--json|--doctor|--print-artifacts|--print-hub-candidates|--print-engine-root]
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = PLUGIN_ROOT / "forge.config.example.json"
LOCAL_PATH = Path.home() / ".config/roxabi/forge/forge.config.json"
HUB_ROOT_FILE = Path.home() / ".config/roxabi/forge/hub-root"
FORGE_ENV_PATH = Path.home() / ".config/roxabi/forge/forge.env"
# The public tree-layout engine, and the default forge_repo: an empty value is
# release mode, which clones the tag roxabi-forge/v<plugin version> from here,
# so the engine always matches the scripts of the plugin that publishes.
CANONICAL_FORGE_REPO = "https://github.com/Roxabi/roxabi-forge.git"
# Same repository over SSH. Written back as the HTTPS form so every config
# names the engine one way and clones without an SSH key.
_CANONICAL_FORGE_REPO_ALIASES = frozenset({"git@github.com:Roxabi/roxabi-forge.git"})
# The archived pre-tree engine (roxabi-forge 0.x, renamed when this repository
# replaced it). A publish from it overwrites production with old code, so it
# is recognised only to be replaced by setup and refused by doctor.
_LEGACY_FORGE_REPOS = frozenset(
    {
        "https://github.com/Roxabi/roxabi-forge-legacy.git",
        "https://github.com/Roxabi/roxabi-forge-legacy",
        "git@github.com:Roxabi/roxabi-forge-legacy.git",
    }
)


REQUIRED_KEYS = (
    "version",
    "hub_root",
    "artifacts_dir",
    "public_host",
    # forge_repo is optional (empty = release mode), so it is not listed.
    "site_dir",
    "registry_dir",
    "internal_prefix",
)

_ENV_SECRET_KEYS = frozenset({"CLOUDFLARE_API_TOKEN", "CLOUDFLARE_API_KEY"})
_ENV_PUBLIC_KEYS = frozenset(
    {
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_EMAIL",
        "FORGE_SHARES_KV_ID",
        "CF_ACCESS_TEAM_DOMAIN",
        "CF_ACCESS_AUD",
        "SHLINK_API_URL",
        "PUBLIC_HOST",
        "FORGE_PAGES_PROJECT",
        "SHLINK_DOMAIN",
    }
)

# Absent or null vault_markers: no structure check, the hub only has to exist.
# This matches the shipped example config ([]), so a key dropped from a local
# config behaves exactly like the defaults every machine starts from.
DEFAULT_VAULT_MARKERS: tuple[str, ...] = ()

# The cockpit layout of a notes vault (artifacts under 00_COCKPIT/Forge/). Only
# infer_hub_layout() looks for it, so setup can recognise a hub being migrated
# from that layout instead of pointing it at an empty `forge/` tree.
COCKPIT_VAULT_MARKERS = ("00_COCKPIT", "01_COMPANY")

# publish.sh materializes a local engine with `git archive HEAD`. These files
# exist together only on the tree-layout engine; the pre-tree repository that
# forge_repo used to name has the site skeleton and not the plugin script, so
# a marker miss is how doctor catches a checkout that would overwrite production.
ENGINE_TREE_MARKERS = (
    "site/404.html",
    "functions/_middleware.ts",
    "plugins/roxabi-forge/scripts/tree_snapshot.py",
)

# og_tree.py accepts exactly these. "off" is a choice, not a missing key:
# a missing key means Browser Run, the production renderer.
OG_RENDERERS = ("browser-run", "playwright", "off")
DEFAULT_OG_RENDERER = "browser-run"

# Inherited from git hooks. `git -C` does not override these, so a doctor run
# from a hook would inspect the caller's repository instead of forge_repo.
_GIT_ENV_DROP = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_PREFIX",
        "GIT_COMMON_DIR",
        "GIT_QUARANTINE_PATH",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    }
)


class PagesEnvFetchError(Exception):
    """Pages project env fetch failed (API unreachable or denied)."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"config unreadable: {path}: {e}") from e
    if not isinstance(data, dict):
        raise SystemExit(f"config must be a JSON object: {path}")
    return data


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def config_paths() -> tuple[Path | None, Path]:
    """Return (active_local_or_env, example)."""
    env = os.environ.get("FORGE_CONFIG", "").strip()
    if env:
        return Path(env).expanduser(), EXAMPLE_PATH
    if LOCAL_PATH.is_file():
        return LOCAL_PATH, EXAMPLE_PATH
    return None, EXAMPLE_PATH


def _safe_home() -> Path | None:
    try:
        return Path.home()
    except (RuntimeError, KeyError, OSError):
        return None


def _safe_cwd() -> Path | None:
    try:
        return Path.cwd()
    except (FileNotFoundError, OSError):
        return None


def _safe_resolve(path: Path) -> Path | None:
    try:
        resolved = path.expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    try:
        if not resolved.exists():
            return None
    except OSError:
        return None
    return resolved


def detect_engine_checkout(start: Path | str | None = None) -> str | None:
    """Engine checkout this plugin runs from, or None.

    Never a forge_repo default: an empty forge_repo is release mode (the
    plugin's own tagged engine), and dev mode — `git archive HEAD` of a
    checkout — is an explicit operator choice. Setup uses this only to
    *suggest* dev mode, and publish uses it to recognise the one checkout
    whose version may differ from the plugin's: the one publish.sh runs from.
    The git top-level of `start` (default: this script's directory) is
    accepted only with a commit and the tree-engine markers doctor checks, so
    an installed plugin copy or an unrelated repository never matches.
    """
    here = Path(start) if start is not None else Path(__file__).resolve().parent
    code, top = _git(here, "rev-parse", "--show-toplevel")
    if code != 0 or not top:
        return None
    root = Path(top.splitlines()[0])
    code, head = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if code != 0 or not head:
        return None
    if _missing_engine_markers(root):
        return None
    try:
        return str(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return None


def is_legacy_forge_repo(value: str) -> bool:
    """True when value names the archived pre-tree engine."""
    return (value or "").strip() in _LEGACY_FORGE_REPOS


def pick_forge_repo(current: str) -> str:
    """forge_repo to write: explicit value → canonical URL (release mode).

    The legacy engine counts as unset, so a machine configured before the
    swap is moved off it. The SSH spelling of the canonical engine is
    written as the HTTPS URL. A checkout is never picked implicitly: that
    would silently put a machine in dev mode, deploying whatever HEAD that
    checkout sits on instead of the release matching the plugin.
    """
    current = (current or "").strip()
    if current in _CANONICAL_FORGE_REPO_ALIASES:
        return CANONICAL_FORGE_REPO
    if current and not is_legacy_forge_repo(current):
        return current
    return CANONICAL_FORGE_REPO


def _add_hub_candidate(
    out: list[tuple[str, str]],
    seen: set[str],
    raw: str,
    origin: str,
) -> None:
    raw = (raw or "").strip()
    if not raw:
        return
    resolved = _safe_resolve(Path(raw))
    if resolved is None:
        return
    key = str(resolved)
    if key in seen:
        return
    seen.add(key)
    out.append((key, origin))


def _walk_up_vault(markers: tuple[str, ...]) -> Path | None:
    cur = _safe_cwd()
    if cur is None:
        return None
    try:
        cur = cur.resolve()
    except (OSError, RuntimeError):
        return None
    seen: set[str] = set()
    while True:
        key = str(cur)
        if key in seen:
            return None
        seen.add(key)
        try:
            if vault_ok(cur, markers):
                return cur
        except OSError:
            pass
        parent = cur.parent
        if parent == cur:
            return None
        cur = parent


def hub_root_candidates(
    cfg: dict[str, Any] | None = None,
    include_search: bool = False,
) -> list[tuple[str, str]]:
    """Ordered (path, origin) hub_root candidates, best first.

    Origins: config, env, hub-root-file, walk-up, known-path.
    A path is kept only if it exists. Duplicates collapse on
    expanduser().resolve(), keeping the better (earlier) origin.
    Never raises: missing HOME or a deleted cwd yields an empty-ish list.

    include_search defaults to False so load_config() does not silently
    pick a guessed vault. Setup / provisioning pass include_search=True
    to also consider walk-up and known-path. Does not call load_config()
    when cfg is provided (avoids recursion through bootstrap).
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    if cfg is not None:
        _add_hub_candidate(
            out, seen, str(cfg.get("hub_root") or ""), "config"
        )

    _add_hub_candidate(
        out, seen, os.environ.get("HUB_ROOT", ""), "env"
    )

    try:
        home = _safe_home()
        if home is not None:
            hub_file = home / ".config/roxabi/forge/hub-root"
            if hub_file.is_file():
                line = hub_file.read_text(encoding="utf-8").strip()
                _add_hub_candidate(out, seen, line, "hub-root-file")
    except (OSError, RuntimeError):
        pass

    if include_search:
        markers, markers_issue = resolve_vault_markers(cfg)
        # Empty markers: vault_ok(dir, []) is true for every existing
        # directory, so walk-up would pick cwd/parent arbitrarily.
        # Skip walk-up unless markers actually identify a vault.
        if markers and not markers_issue:
            walked = _walk_up_vault(markers)
            if walked is not None:
                _add_hub_candidate(out, seen, str(walked), "walk-up")
        home = _safe_home()
        if home is not None:
            for rel in (
                ".roxabi",
                "projects/roxabi/.roxabi",
            ):
                _add_hub_candidate(
                    out, seen, str(home / rel), "known-path"
                )
    return out


def resolve_hub_root(
    cfg: dict[str, Any] | None = None,
    include_search: bool = False,
) -> tuple[str, str]:
    """First hub_root candidate, or ("", "none")."""
    cands = hub_root_candidates(cfg, include_search=include_search)
    if not cands:
        return "", "none"
    return cands[0]


def _bootstrap_hub_root(current: str) -> str:
    """Config / env / hub-root-file only — no walk-up or known-path."""
    path, _origin = resolve_hub_root(
        {"hub_root": current}, include_search=False
    )
    return path


def _merged_config() -> dict[str, Any]:
    if not EXAMPLE_PATH.is_file():
        raise SystemExit(f"missing defaults: {EXAMPLE_PATH}")
    base = _read_json(EXAMPLE_PATH)
    active, _ = config_paths()
    if active is not None and active.is_file():
        cfg = _deep_merge(base, _read_json(active))
        cfg["_config_source"] = str(active.resolve())
        cfg["_config_fallback"] = False
    else:
        cfg = dict(base)
        cfg["_config_source"] = str(EXAMPLE_PATH.resolve())
        cfg["_config_fallback"] = True
    cfg.setdefault("shlink_domain", "")
    cfg.setdefault("types", ["deck", "talk", "guide", "diagram", "gallery", "html", "other"])
    # Never default to a project named after another forge: a config that lost
    # its pages_project would otherwise aim a full-snapshot deploy at it.
    cfg.setdefault("pages_project", "forge")
    # Missing means the production renderer. An explicit playwright or off
    # must survive the merge; only an absent key is filled.
    cfg.setdefault("og_renderer", DEFAULT_OG_RENDERER)
    cfg.setdefault("cloudflare_account_id", "")
    cfg.setdefault("shares_kv_namespace_id", "")
    return cfg


def load_config() -> dict[str, Any]:
    cfg = _merged_config()
    cfg["hub_root"] = _bootstrap_hub_root(str(cfg.get("hub_root") or ""))
    if cfg["hub_root"]:
        cfg["hub_root"] = str(Path(cfg["hub_root"]).expanduser().resolve())
    return cfg


def forge_env_path() -> Path:
    env = os.environ.get("FORGE_ENV", "").strip()
    if env:
        return Path(env).expanduser()
    return FORGE_ENV_PATH


def parse_forge_env(path: Path | None = None) -> tuple[dict[str, str], bool]:
    """Return (non-secret keys, has_token). Never returns token values."""
    public: dict[str, str] = {}
    has_token = False
    p = path or forge_env_path()
    if not p.is_file():
        return public, False
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return public, False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip("'").strip('"')
        if k in _ENV_SECRET_KEYS:
            if v:
                has_token = True
        elif k in _ENV_PUBLIC_KEYS and v:
            public[k] = v
    return public, has_token


def token_present() -> bool:
    if os.environ.get("CLOUDFLARE_API_TOKEN", "").strip():
        return True
    if os.environ.get("CLOUDFLARE_API_KEY", "").strip() and os.environ.get(
        "CLOUDFLARE_EMAIL", ""
    ).strip():
        return True
    _, has = parse_forge_env()
    return has


def resolved_account_id(cfg: dict[str, Any] | None = None) -> str:
    env = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if env:
        return env
    public, _ = parse_forge_env()
    if public.get("CLOUDFLARE_ACCOUNT_ID"):
        return public["CLOUDFLARE_ACCOUNT_ID"]
    cfg = cfg or load_config()
    return str(cfg.get("cloudflare_account_id") or "").strip()


def resolved_shares_kv_id(cfg: dict[str, Any] | None = None) -> str:
    env = os.environ.get("FORGE_SHARES_KV_ID", "").strip()
    if env:
        return env
    public, _ = parse_forge_env()
    if public.get("FORGE_SHARES_KV_ID"):
        return public["FORGE_SHARES_KV_ID"]
    cfg = cfg or load_config()
    return str(cfg.get("shares_kv_namespace_id") or "").strip()


def artifacts_root(cfg: dict[str, Any] | None = None) -> Path | None:
    cfg = cfg or load_config()
    hub = (cfg.get("hub_root") or "").strip()
    rel = (cfg.get("artifacts_dir") or "").strip()
    if not hub or not rel:
        return None
    return (Path(hub) / rel).resolve()


def resolve_vault_markers(
    cfg: dict[str, Any] | None = None,
) -> tuple[tuple[str, ...] | None, str | None]:
    """Effective vault markers from cfg. Testable without files on disk.

    Absent or null → DEFAULT_VAULT_MARKERS (no structure check).
    [] → empty tuple (hub must only exist as a directory).
    Wrong type → (None, issue); caller must not apply structure checks.
    """
    if cfg is None or "vault_markers" not in cfg or cfg["vault_markers"] is None:
        return DEFAULT_VAULT_MARKERS, None
    raw = cfg["vault_markers"]
    if not isinstance(raw, list):
        return None, (
            "vault_markers must be a list of folder names "
            f"(got {type(raw).__name__})"
        )
    markers: list[str] = []
    for i, item in enumerate(raw):
        if not isinstance(item, str):
            return None, (
                f"vault_markers[{i}] must be a string "
                f"(got {type(item).__name__})"
            )
        markers.append(item)
    return tuple(markers), None


def vault_ok(
    hub: Path, markers: list[str] | tuple[str, ...] | None = None
) -> bool:
    if markers is None:
        markers = DEFAULT_VAULT_MARKERS
    return hub.is_dir() and all((hub / m).is_dir() for m in markers)


def _has_artifact_slugs(root: Path) -> bool:
    """True if root has a subdirectory containing index.html. Missing dir → False."""
    try:
        if not root.is_dir():
            return False
        for child in root.iterdir():
            try:
                if child.is_dir() and (child / "index.html").is_file():
                    return True
            except OSError:
                continue
    except OSError:
        return False
    return False


def infer_hub_layout(hub: Path | str) -> tuple[str, list[str]]:
    """Infer (artifacts_dir, vault_markers) from hub layout. Never raises on missing dirs.

    The Roxabi data root is a plain directory (`~/.roxabi`, artifacts in
    `forge/`) with no vault markers. A hub that still carries the cockpit
    layout of a notes vault is detected so an operator migrating one is not
    silently pointed at an empty tree.
    """
    hub_path = Path(hub)
    vault_dir = "00_COCKPIT/Forge/artifacts"
    forge_tree = (hub_path / "forge").is_dir()
    vault_slugs = _has_artifact_slugs(hub_path / vault_dir)
    if forge_tree and not vault_slugs:
        return "forge", []
    if vault_ok(hub_path, COCKPIT_VAULT_MARKERS) or vault_slugs:
        return vault_dir, list(COCKPIT_VAULT_MARKERS)
    return "forge", []


def forge_env_permissions(path: Path | None = None) -> dict[str, Any]:
    """Return {ok, mode, path, issue}. Publish requires 600 or 400."""
    p = path or forge_env_path()
    if not p.is_file():
        return {"ok": True, "mode": None, "path": str(p), "issue": None}
    try:
        mode = stat.S_IMODE(p.stat().st_mode)
    except OSError as e:
        return {"ok": False, "mode": None, "path": str(p), "issue": str(e)}
    mode_s = oct(mode)[-3:]
    if mode in (0o600, 0o400):
        return {"ok": True, "mode": mode_s, "path": str(p), "issue": None}
    return {
        "ok": False,
        "mode": mode_s,
        "path": str(p),
        "issue": f"forge.env mode {mode_s} — chmod 600 required before publish",
    }


def _read_secret_from_forge_env(key: str, path: Path | None = None) -> str:
    """Read a single secret key from forge.env (never log)."""
    p = path or forge_env_path()
    if not p.is_file():
        return ""
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip().strip("'").strip('"')
    return ""


def resolve_api_token() -> str:
    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if tok:
        return tok
    return _read_secret_from_forge_env("CLOUDFLARE_API_TOKEN")


def _cf_api(
    method: str,
    path: str,
    token: str,
    *,
    timeout: float = 20.0,
) -> tuple[int, dict[str, Any] | None, str]:
    url = f"https://api.cloudflare.com/client/v4{path}"
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        return 0, None, str(e.reason)
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return code, None, body[:200]
    if not isinstance(data, dict):
        return code, None, "invalid JSON response"
    return code, data, ""


def _cf_err_msg(data: dict[str, Any] | None, err: str) -> str:
    errors = (data or {}).get("errors") or [{}]
    first = errors[0] if errors else {}
    if isinstance(first, dict) and first.get("message"):
        return str(first["message"])
    return err or "unknown"


def _verify_api_token(token: str, acct: str) -> tuple[str | None, str]:
    """User tokens: GET /user/tokens/verify. Account-owned (cfat_): /accounts/{id}/tokens/verify."""
    code, data, err = _cf_api("GET", "/user/tokens/verify", token)
    if code == 200 and data and data.get("success"):
        return "user", ""
    user_code, user_msg = code, _cf_err_msg(data, err)
    code, data, err = _cf_api("GET", f"/accounts/{acct}/tokens/verify", token)
    if code == 200 and data and data.get("success"):
        return "account", ""
    return None, (
        f"token verify failed (user {user_code}: {user_msg}; "
        f"account {code}: {_cf_err_msg(data, err)})"
    )


def fetch_pages_project(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch Pages project payload. Returns structured result (never silent empty on API error)."""
    cfg = cfg or load_config()
    token = resolve_api_token()
    acct = resolved_account_id(cfg)
    project = str(cfg.get("pages_project") or "forge")
    if not token:
        return {
            "ok": False,
            "plain_vars": {},
            "error_kind": "auth_missing",
            "error": "CLOUDFLARE_API_TOKEN missing",
            "http_code": 0,
        }
    if not acct:
        return {
            "ok": False,
            "plain_vars": {},
            "error_kind": "auth_missing",
            "error": "CLOUDFLARE_ACCOUNT_ID missing",
            "http_code": 0,
        }
    code, data, err = _cf_api(
        "GET",
        f"/accounts/{acct}/pages/projects/{project}",
        token,
    )
    if code == 0:
        return {
            "ok": False,
            "plain_vars": {},
            "error_kind": "unreachable",
            "error": err or "network error",
            "http_code": code,
        }
    if code != 200 or not data or not data.get("success"):
        msg = (data or {}).get("errors", [{}])[0].get("message") if data else err
        return {
            "ok": False,
            "plain_vars": {},
            "error_kind": "api_error",
            "error": msg or f"HTTP {code}",
            "http_code": code,
        }
    ev = (
        (data.get("result") or {})
        .get("deployment_configs", {})
        .get("production", {})
        .get("env_vars")
        or {}
    )
    plain: dict[str, str] = {}
    for name, entry in ev.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "plain_text" and entry.get("value"):
            plain[str(name)] = str(entry["value"])
    return {
        "ok": True,
        "plain_vars": plain,
        "error_kind": None,
        "error": None,
        "http_code": code,
    }


def fetch_pages_plain_vars(cfg: dict[str, Any] | None = None) -> dict[str, str]:
    """All production plain_text Pages vars (never secrets). Raises PagesEnvFetchError on API failure."""
    result = fetch_pages_project(cfg)
    if not result["ok"]:
        raise PagesEnvFetchError(
            str(result["error_kind"]),
            str(result["error"]),
        )
    return dict(result["plain_vars"])


def fetch_pages_plain_var(name: str, cfg: dict[str, Any] | None = None) -> str:
    """Return one plain Pages var. Empty string if absent. Raises PagesEnvFetchError on API failure."""
    plain = fetch_pages_plain_vars(cfg)
    return plain.get(name, "")


def preflight_mutations(
    cfg: dict[str, Any] | None = None,
    *,
    require_kv: bool = False,
) -> dict[str, Any]:
    """Online preflight before KV/deploy mutations.

    Shell publish uses require_kv=False so REST KV denial can fall back to wrangler OAuth.
    doctor_online uses require_kv=True to verify token KV scope.
    """
    cfg = cfg or load_config()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, str] = {}
    perm = forge_env_permissions()
    if not perm["ok"]:
        errors.append(perm["issue"] or "forge.env permissions invalid")

    token = resolve_api_token()
    acct = resolved_account_id(cfg)
    kv = resolved_shares_kv_id(cfg)
    project = str(cfg.get("pages_project") or "forge")

    if not token:
        errors.append("CLOUDFLARE_API_TOKEN missing")
    if not acct:
        errors.append("CLOUDFLARE_ACCOUNT_ID missing")
    if not kv:
        errors.append("FORGE_SHARES_KV_ID missing")

    public, _ = parse_forge_env()
    for key in ("CF_ACCESS_TEAM_DOMAIN", "CF_ACCESS_AUD"):
        val = (os.environ.get(key) or public.get(key) or "").strip()
        if not val:
            errors.append(f"{key} missing — deploy would wipe Access JWT vars on Pages")

    if not token or not acct:
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "checks": checks,
            "require_kv": require_kv,
        }

    kind, verr = _verify_api_token(token, acct)
    if kind:
        checks["token"] = kind
    else:
        errors.append(verr)

    code, data, err = _cf_api("GET", f"/accounts/{acct}", token)
    if code == 200 and data and data.get("success"):
        checks["account"] = "ok"
    else:
        msg = (data or {}).get("errors", [{}])[0].get("message") if data else err
        errors.append(f"account {acct[:8]}… unreachable ({code}): {msg or err}")

    code, data, err = _cf_api(
        "GET", f"/accounts/{acct}/pages/projects/{project}", token
    )
    if code == 200 and data and data.get("success"):
        checks["pages_project"] = project
    else:
        msg = (data or {}).get("errors", [{}])[0].get("message") if data else err
        errors.append(f"pages project '{project}' missing ({code}): {msg or err}")

    if kv:
        code, data, err = _cf_api(
            "GET", f"/accounts/{acct}/storage/kv/namespaces/{kv}", token
        )
        if code == 200 and data and data.get("success"):
            checks["kv_namespace"] = kv[:8] + "…"
        elif require_kv:
            msg = (data or {}).get("errors", [{}])[0].get("message") if data else err
            errors.append(f"KV namespace unreachable ({code}): {msg or err}")
        else:
            checks["kv_namespace"] = "skipped (OAuth fallback OK)"
            warnings.append(
                "KV REST unreachable — publish --share will try wrangler OAuth if needed"
            )
    elif require_kv:
        errors.append("FORGE_SHARES_KV_ID missing")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "require_kv": require_kv,
    }


def _exc_one_line(exc: BaseException) -> str:
    """Collapse an exception to one line: doctor may not traceback."""
    return " ".join(f"{exc.__class__.__name__}: {exc}".split())


def browser_run_probe(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Advisory: can this token render an OG thumbnail on Browser Run.

    Returns {ok, checked, reason} and never raises. The Browser Run · Edit
    permission cannot be read back from the token verify endpoint, so the
    check is one real render. It must never flip a verdict: a token without
    that permission still publishes and only loses its thumbnails.
    Reasoning and measurements: PR #55.
    """
    cfg = cfg or load_config()
    token = resolve_api_token()
    account = resolved_account_id(cfg)
    if not token or not account:
        # Nothing to test, and doctor already reports the missing value.
        return {
            "ok": False,
            "checked": False,
            "reason": "token or account id missing — already reported",
        }

    # Lazy: og_render imports load_config lazily too, so a module-level import
    # here would close the cycle.
    try:
        import og_render
    except Exception as exc:
        return {"ok": False, "checked": True, "reason": _exc_one_line(exc)}

    try:
        # The resolved pair travels with the call — resolved_account_id() reads
        # sources og_render does not.
        og_render.probe(token=token, account=account)
    except og_render.OgRenderError as exc:
        return {"ok": False, "checked": True, "reason": str(exc)}
    except Exception as exc:
        return {"ok": False, "checked": True, "reason": _exc_one_line(exc)}
    return {"ok": True, "checked": True, "reason": None}


def _playwright_importable() -> bool:
    try:
        import importlib

        importlib.import_module("playwright")
    except Exception:
        return False
    return True


def playwright_toolchain_probe() -> dict[str, Any]:
    """Advisory: a local Playwright render can start. Never raises.

    A missing thumbnail must not block publish. `uv` counts because the
    renderer can bootstrap Playwright without a preinstalled module.
    """
    if shutil.which("uv"):
        return {"ok": True, "checked": True, "reason": None}
    if _playwright_importable():
        return {"ok": True, "checked": True, "reason": None}
    return {
        "ok": False,
        "checked": True,
        "reason": "neither uv nor an importable playwright module",
    }


def doctor_online(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Optional online doctor: token, account, Pages project, KV namespace (KV
    required), plus the advisory render probe for the configured og_renderer."""
    base = doctor(cfg)
    pf = preflight_mutations(cfg, require_kv=True)
    online_issues = list(pf.get("errors") or [])
    online_checks = dict(pf.get("checks") or {})
    online_warnings = list(pf.get("warnings") or [])
    perm = forge_env_permissions()

    # Browser Run is advisory and gated on pf["ok"] because its warning says
    # "publish still succeeds", which holds only when the render permission is
    # the sole gap. Playwright is local, so it does not spend that request:
    # a missing toolchain skips thumbnails and must not be blamed on Cloudflare.
    renderer = str(base.get("og_renderer") or DEFAULT_OG_RENDERER)
    if renderer == "playwright":
        browser_run = {
            "ok": False,
            "checked": False,
            "reason": (
                "og_renderer is playwright — local toolchain probed "
                "instead of Browser Run"
            ),
        }
        toolchain = playwright_toolchain_probe()
        if not toolchain["ok"]:
            online_warnings.append(
                "playwright toolchain missing — OG thumbnails will be skipped "
                f"(publish still succeeds): {toolchain['reason']}"
            )
    elif renderer != "browser-run":
        # "off", or a value doctor() already rejected. No network call.
        browser_run = {
            "ok": False,
            "checked": False,
            "reason": f"og_renderer is {renderer} — render probe skipped",
        }
    elif pf["ok"]:
        browser_run = browser_run_probe(cfg)
    else:
        browser_run = {
            "ok": False,
            "checked": False,
            "reason": "online preflight failed — the credential is already reported",
        }
    if browser_run["ok"]:
        # "permission ok", not "ok": one blank page proves the token may
        # render, never that 33 real payloads will (size, settle, plan rate).
        online_checks["browser_run"] = "permission ok"
    elif browser_run["checked"]:
        online_warnings.append(
            "Browser Run unavailable — OG thumbnails will fail per slug "
            f"(publish still succeeds): {browser_run['reason']}"
        )

    # The engine line is read-only and advisory (no exit code): publish is
    # the gate that refuses. It spends a Pages API call only when the
    # credentials already passed the preflight, like the Browser Run probe.
    import engine_drift  # lazy: engine_drift imports this module

    engine_drift_summary = engine_drift.summary_line(cfg, fetch=bool(pf["ok"]))
    if engine_drift_summary.get("verdict") == "newer_prod":
        online_warnings.append(
            f"{engine_drift_summary.get('message')} "
            + " ; ".join(engine_drift.UPDATE_COMMANDS)
            + " — publish refuses until then"
        )

    return {
        **base,
        "online_ok": pf["ok"],
        "online_checks": online_checks,
        "online_issues": online_issues,
        "online_warnings": online_warnings,
        "browser_run": browser_run,
        "engine_drift": engine_drift_summary,
        "forge_env_permissions": perm,
        "deploy_ready": base.get("deploy_ready") and perm["ok"] and pf["ok"],
    }


def _normalize_host(value: str) -> str:
    """Bare lowercase host: no scheme, path, port or trailing dot.

    `https://Other-Forge.example.com:443/` and `other-forge.example.com` name
    the same deploy target; comparing raw strings would let one spelling slip
    past a refusal written in the other.
    """
    host = value.strip().lower()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    host = host.rsplit("@", 1)[-1].split(":", 1)[0]
    return host.rstrip(".")


def refused_target_issues(cfg: dict[str, Any]) -> list[str]:
    """Issues when this config would deploy onto a target it declares refused.

    `refused_targets` = {"hosts": [...], "pages_projects": [...]}, both optional.
    A machine that also publishes to another team's forge lists that forge
    here, so a config copied from the wrong machine cannot overwrite it: every
    publish is a full snapshot that deletes what the local hub lacks.

    A malformed value is an issue, never an empty list: a guard the operator
    believes is armed must not silently allow the deploy it was set to stop.
    """
    raw = cfg.get("refused_targets")
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return [
            "refused_targets must be an object with optional hosts / "
            f"pages_projects lists (got {type(raw).__name__}) — deploy refused "
            "until it is fixed"
        ]
    lists: dict[str, list[str]] = {}
    for key in ("hosts", "pages_projects"):
        entries = raw.get(key)
        if entries is None:
            lists[key] = []
            continue
        if not isinstance(entries, list) or not all(isinstance(e, str) for e in entries):
            return [
                f"refused_targets.{key} must be a list of strings — deploy "
                "refused until it is fixed"
            ]
        lists[key] = entries

    issues: list[str] = []
    host = _normalize_host(str(cfg.get("public_host") or ""))
    refused_hosts = {_normalize_host(h) for h in lists["hosts"]} - {""}
    if host and host in refused_hosts:
        issues.append(
            f"public_host {host} is listed in refused_targets.hosts — this "
            "config must not deploy there"
        )
    project = str(cfg.get("pages_project") or "").strip().lower()
    refused_projects = {p.strip().lower() for p in lists["pages_projects"]} - {""}
    if project and project in refused_projects:
        issues.append(
            f"pages_project {project} is listed in refused_targets.pages_projects "
            "— this config must not deploy there"
        )
    return issues


def _is_repo_url(value: str) -> bool:
    """Clone spec vs checkout path. Doctor must not fetch to tell them apart."""
    text = value.strip()
    return text.startswith("git@") or "://" in text


def _missing_engine_markers(root: Path) -> list[str]:
    """ENGINE_TREE_MARKERS absent under root. One gate for doctor and setup."""
    return [rel for rel in ENGINE_TREE_MARKERS if not (root / rel).is_file()]


def _git(repo: Path, *args: str) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_DROP}
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return 127, "git not installed"
    except subprocess.TimeoutExpired:
        return 124, "git timed out"
    except OSError as exc:
        return 1, _exc_one_line(exc)
    return proc.returncode, (proc.stdout or "").strip()


def resolved_og_renderer(cfg: dict[str, Any]) -> str:
    """Configured renderer, or Browser Run when the key was left out."""
    raw = str(cfg.get("og_renderer") or "").strip()
    return raw or DEFAULT_OG_RENDERER


def engine_status(cfg: dict[str, Any]) -> dict[str, Any]:
    """Inspect forge_repo without cloning.

    Empty or a URL is release mode: publish.sh clones the tag
    roxabi-forge/v<plugin version>, so the engine matches the plugin's
    scripts. A local checkout is dev mode: publish.sh archives HEAD (no
    commit means that archive dies) and stamps it <version>+dev.<sha7>. A
    non-canonical URL cannot be checked offline; with layout tree that is the
    incident where the configured remote was still the pre-tree engine and a
    publish would have overwritten production.

    `issues` / `warnings` / `path_failed` feed doctor(). The report payload
    keeps source, kind, mode, stamp, head, markers_ok.
    """
    # Lazy: engine_drift imports this module.
    import engine_drift

    configured = str(cfg.get("forge_repo") or "").strip()
    source = configured or CANONICAL_FORGE_REPO
    status: dict[str, Any] = {
        "source": source,
        "kind": "url" if _is_repo_url(source) else "path",
        "mode": "release" if _is_repo_url(source) else "dev",
        "stamp": None,
        "head": None,
        "markers_ok": False,
        "issues": [],
        "warnings": [],
        "path_failed": False,
    }
    if is_legacy_forge_repo(source):
        # Checked before the generic URL warnings: this remote is known to be
        # the archived pre-tree engine, so there is nothing left to verify.
        # path_failed doubles as the deploy blocker for the engine source.
        status["issues"].append(
            f"forge_repo names the archived legacy engine ({source}) — "
            "publishing it would overwrite production with pre-tree code; "
            "clear forge_repo (release mode) or point it at an engine checkout "
            "(re-running roxabi-forge-setup does it)"
        )
        status["path_failed"] = True
        return status
    if status["kind"] == "url":
        try:
            version = engine_drift.read_plugin_version()
        except engine_drift.EngineError as exc:
            status["issues"].append(
                f"{exc} — release mode clones the tag of the plugin version; "
                "reinstall the roxabi-forge plugin"
            )
            status["path_failed"] = True
            return status
        tag = engine_drift.release_tag(version)
        status["stamp"] = engine_drift.format_stamp(version)
        if source == CANONICAL_FORGE_REPO:
            # The supported default: a pinned tag of the public engine. There
            # is nothing an offline doctor could add, so no warning.
            return status
        status["warnings"].append(
            f"forge_repo is a URL ({source}) — release mode clones tag {tag}; "
            "not verified offline; doctor does not clone, so a wrong remote "
            "or a missing tag stays invisible until publish"
        )
        if str(cfg.get("layout") or "").strip() == "tree":
            status["warnings"].append(
                "forge_repo URL with layout tree — nothing proves this remote "
                "carries the tree engine; cloning the wrong repository would "
                "overwrite production"
            )
        return status

    try:
        root = Path(source).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        status["issues"].append(
            f"forge_repo path cannot be resolved ({_exc_one_line(exc)}) — "
            "point it at a committed tree-layout engine checkout"
        )
        status["path_failed"] = True
        return status
    if not root.is_dir():
        status["issues"].append(
            f"forge_repo path not found: {source} — dev mode deploys a "
            "git archive HEAD of this checkout; point forge_repo at a "
            "committed tree-layout engine, or clear it for release mode"
        )
        status["path_failed"] = True
        return status

    code, inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if code == 127:
        status["issues"].append(
            "forge_repo cannot be checked: git is not installed — "
            "publish.sh deploys a git archive HEAD and needs git"
        )
        status["path_failed"] = True
    elif code != 0 or inside != "true":
        status["issues"].append(
            f"forge_repo is not a git work tree: {source} — dev mode "
            "archives HEAD of a checkout; use a git checkout, or clear "
            "forge_repo for release mode"
        )
        status["path_failed"] = True
    else:
        code, head = _git(root, "rev-parse", "--short", "HEAD")
        if code != 0 or not head:
            status["issues"].append(
                f"forge_repo has no commit: {source} — publish.sh deploys a "
                "git archive HEAD and will die here; commit the checkout, or "
                "point forge_repo at one that already has a commit"
            )
            status["path_failed"] = True
        else:
            status["head"] = head.splitlines()[0].strip()

    missing = _missing_engine_markers(root)
    status["markers_ok"] = not missing
    if missing:
        status["issues"].append(
            "forge_repo is missing tree-engine markers ("
            + ", ".join(missing)
            + ") — a checkout without these is not the tree-layout engine; "
            "point forge_repo at the engine, not the pre-tree repository"
        )
        status["path_failed"] = True
    if status["path_failed"]:
        return status
    # Same resolution publish.sh runs, so doctor refuses exactly what publish
    # would: a checkout whose version differs from the plugin running it.
    try:
        engine = engine_drift.resolve_engine(source)
    except engine_drift.EngineError as exc:
        status["issues"].append(str(exc))
        status["path_failed"] = True
        return status
    status["stamp"] = engine["stamp"]
    status["warnings"].extend(engine_drift.dev_warnings(engine))
    return status


def doctor(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return structured health check. ok=False ⇒ run roxabi-forge-setup."""
    cfg = cfg or load_config()
    issues: list[str] = []
    warnings: list[str] = []

    for k in REQUIRED_KEYS:
        if k not in cfg:
            issues.append(f"missing key: {k}")

    if cfg.get("_config_fallback"):
        issues.append(
            f"no local config — copy from example to {LOCAL_PATH}"
        )

    markers, markers_issue = resolve_vault_markers(cfg)
    if markers_issue:
        issues.append(markers_issue)

    hub_s = (cfg.get("hub_root") or "").strip()
    if not hub_s:
        issues.append("hub_root empty (absolute data-root path required)")
        hub = None
    else:
        hub = Path(hub_s)
        if not hub.is_dir():
            issues.append(f"hub_root not found: {hub}")
        elif markers is not None and not vault_ok(hub, markers):
            issues.append(
                f"hub_root is not the expected vault "
                f"(markers {', '.join(markers)}): {hub}"
            )

    art_rel = (cfg.get("artifacts_dir") or "").strip()
    if not art_rel:
        issues.append("artifacts_dir empty")
    art = artifacts_root(cfg)
    if art is not None and hub is not None and hub.is_dir():
        if not art.is_dir():
            warnings.append(f"artifacts_dir missing (created at setup): {art}")

    # forge_repo is absent on purpose: empty means release mode.
    for key in ("public_host", "site_dir", "registry_dir", "internal_prefix"):
        if not str(cfg.get(key) or "").strip():
            issues.append(f"{key} empty")
    refused = refused_target_issues(cfg)
    issues.extend(refused)
    engine = engine_status(cfg)
    issues.extend(engine["issues"])
    warnings.extend(engine["warnings"])
    og_renderer = resolved_og_renderer(cfg)
    if og_renderer not in OG_RENDERERS:
        issues.append(
            f"og_renderer must be one of {', '.join(OG_RENDERERS)} "
            f"(got {og_renderer!r})"
        )

    acct = resolved_account_id(cfg)
    if not acct:
        warnings.append(
            "CLOUDFLARE_ACCOUNT_ID missing — set in ~/.config/roxabi/forge/forge.env "
            "(see .env.example)"
        )
    kv = resolved_shares_kv_id(cfg)
    if not kv:
        warnings.append(
            "FORGE_SHARES_KV_ID missing — CLI --share needs it "
            "(forge.env or shares_kv_namespace_id in forge.config)"
        )
    public, _ = parse_forge_env()
    has_token = token_present()
    access_team = (os.environ.get("CF_ACCESS_TEAM_DOMAIN") or public.get("CF_ACCESS_TEAM_DOMAIN") or "").strip()
    access_aud = (os.environ.get("CF_ACCESS_AUD") or public.get("CF_ACCESS_AUD") or "").strip()
    for key, val in (
        ("CF_ACCESS_TEAM_DOMAIN", access_team),
        ("CF_ACCESS_AUD", access_aud),
    ):
        if not val:
            warnings.append(f"{key} missing in forge.env — deploy would wipe Access JWT vars")
    if not has_token:
        warnings.append(
            f"CF token missing — generate OK, publish KO. "
            f"Write {forge_env_path()} (chmod 600) via roxabi-forge-setup"
        )

    perm = forge_env_permissions()
    if not perm["ok"] and perm.get("issue"):
        warnings.append(perm["issue"])

    # Name only. Browser Run needs the network, and a missing Playwright
    # toolchain is a warning because a thumbnail must not block publish —
    # both probes live in doctor_online(), so this function stays offline.

    deploy_blockers: list[str] = []
    if not has_token:
        deploy_blockers.append("token")
    if not acct:
        deploy_blockers.append("account_id")
    if not kv:
        deploy_blockers.append("kv_id")
    if not access_team:
        deploy_blockers.append("CF_ACCESS_TEAM_DOMAIN")
    if not access_aud:
        deploy_blockers.append("CF_ACCESS_AUD")
    if not str(cfg.get("public_host") or "").strip():
        deploy_blockers.append("public_host")
    if not perm["ok"]:
        deploy_blockers.append("forge_env_permissions")
    if engine["path_failed"]:
        deploy_blockers.append("forge_repo")
    if refused:
        deploy_blockers.append("refused_target")

    payload = {
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "config_source": cfg.get("_config_source"),
        "fallback": bool(cfg.get("_config_fallback")),
        "hub_root": hub_s or None,
        "artifacts_root": str(art) if art else None,
        "local_path": str(LOCAL_PATH),
        "example_path": str(EXAMPLE_PATH),
        "forge_env": str(forge_env_path()),
        "has_token": has_token,
        "deploy_ready": len(deploy_blockers) == 0 and len(issues) == 0,
        "deploy_blockers": deploy_blockers,
        "cloudflare_account_id": acct or None,
        "shares_kv_namespace_id": kv or None,
        "pages_project": cfg.get("pages_project") or "forge",
        "og_renderer": og_renderer,
        "engine": {
            "source": engine["source"],
            "kind": engine["kind"],
            "mode": engine["mode"],
            "stamp": engine["stamp"],
            "head": engine["head"],
            "markers_ok": bool(engine["markers_ok"]),
        },
        "forge_env_permissions": perm,
        "skill": "roxabi-forge-setup",
    }
    if not hub_s:
        # Suggestions only — never flips ok. Setup uses these to propose a path.
        payload["hub_root_candidates"] = [
            [origin, path]
            for path, origin in hub_root_candidates(cfg, include_search=True)
        ]
    return payload


def export_env(cfg: dict[str, Any] | None = None) -> str:
    """Shell-friendly KEY=value lines for publish.sh sourcing."""
    cfg = cfg or load_config()
    art = artifacts_root(cfg)
    pairs = {
        "FORGE_PUBLIC_HOST": cfg.get("public_host", "forge.roxabi.dev"),
        "FORGE_REPO": cfg.get("forge_repo", ""),
        "FORGE_SHLINK_DOMAIN": cfg.get("shlink_domain", ""),
        "FORGE_HUB_ROOT": cfg.get("hub_root") or "",
        "FORGE_ARTIFACTS_DIR": cfg.get("artifacts_dir") or "",
        "FORGE_ARTIFACTS_ROOT": str(art) if art else "",
        "FORGE_SITE_DIR": cfg.get("site_dir", "site"),
        "FORGE_REGISTRY_DIR": cfg.get("registry_dir", "registry"),
        "FORGE_INTERNAL_PREFIX": cfg.get("internal_prefix", "a"),
        "FORGE_PAGES_PROJECT": cfg.get("pages_project") or "forge",
        "FORGE_OG_RENDERER": resolved_og_renderer(cfg),
        "CLOUDFLARE_ACCOUNT_ID": resolved_account_id(cfg),
        "FORGE_SHARES_KV_ID": resolved_shares_kv_id(cfg),
        "FORGE_ENV_FILE": str(forge_env_path()),
        "FORGE_CONFIG_SOURCE": cfg.get("_config_source", ""),
        "FORGE_CONFIG_FALLBACK": "1" if cfg.get("_config_fallback") else "0",
    }
    lines = []
    for k, v in pairs.items():
        # safe single-quote shell escape
        esc = str(v).replace("'", "'\"'\"'")
        lines.append(f"{k}='{esc}'")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--doctor-online" in args or "--online" in args:
        d = doctor_online()
        print(json.dumps(d, ensure_ascii=False, indent=2))
        ok = d.get("ok") and d.get("online_ok", False)
        return 0 if ok else 1
    if "--preflight" in args:
        require_kv = "--require-kv" in args
        pf = preflight_mutations(require_kv=require_kv)
        print(json.dumps(pf, ensure_ascii=False, indent=2))
        return 0 if pf["ok"] else 1
    if "--doctor" in args or "-c" in args or "--check" in args:
        d = doctor()
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0 if d["ok"] else 1
    if "--print-hub-candidates" in args:
        try:
            cfg = _merged_config()
        except SystemExit:
            cfg = None
        for path, origin in hub_root_candidates(cfg, include_search=True):
            print(f"{origin}\t{path}")
        return 0
    if "--print-engine-root" in args:
        root = detect_engine_checkout()
        if root:
            print(root)
        return 0
    if "--print-artifacts" in args:
        art = artifacts_root()
        if not art:
            print("", end="")
            return 1
        print(art)
        return 0
    if "--export-env" in args:
        sys.stdout.write(export_env())
        return 0
    # default: full merged config as JSON
    cfg = load_config()
    # strip internal keys for clean dump unless --all
    if "--all" not in args:
        cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
