#!/usr/bin/env python3
"""
migrate-fd-batch.py — regenerate fd-engine HTML from descriptor JSON siblings.

Reads an audit manifest (or scans --forge-dir) and runs gen-fd.py for entries
with a .json sibling. Dry-run by default.

Usage:
  python3 scripts/audit-forge-diagrams.py --out /tmp/audit.json
  python3 scripts/migrate-fd-batch.py --manifest /tmp/audit.json --apply
  python3 scripts/migrate-fd-batch.py --forge-dir ~/.roxabi/forge --limit 5 --apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
GEN_FD = _SCRIPTS_DIR / "gen-fd.py"
VALIDATE_FD = _SCRIPTS_DIR / "validate-fd.py"


def load_manifest(path: Path | None, forge_dir: Path) -> list[dict]:
    if path:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("entries") or []

    proc = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / "audit-forge-diagrams.py"), "--forge-dir", str(forge_dir)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout).get("entries") or []


def title_from_path(html_path: Path) -> str:
    stem = html_path.stem.replace("-", " ").replace("_", " ")
    return stem.title()


def migrate_entry(entry: dict, *, apply: bool, validate: bool) -> dict:
    html_path = Path(entry["path"])
    json_path = Path(entry["json_path"]) if entry.get("json_path") else html_path.with_suffix(".json")
    result = {"html": str(html_path), "json": str(json_path), "status": "skipped"}

    if not json_path.exists():
        result["status"] = "no-json"
        return result

    if entry.get("action") not in {"migrate-if-json", "validate", "needs-fd-data"}:
        result["status"] = "not-candidate"
        return result

    cmd = [
        sys.executable,
        str(GEN_FD),
        "--in",
        str(json_path),
        "--out",
        str(html_path),
        "--title",
        title_from_path(html_path),
    ]

    if not apply:
        result["status"] = "dry-run"
        result["cmd"] = cmd
        return result

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        result["status"] = "gen-failed"
        result["stderr"] = (proc.stderr or proc.stdout)[-500:]
        return result

    result["status"] = "generated"

    if validate:
        expect = json_path.with_suffix(".expect.json")
        vcmd = [sys.executable, str(VALIDATE_FD), "--html", str(html_path), "--static-only"]
        if expect.exists():
            vcmd.extend(["--expect", str(expect)])
        vproc = subprocess.run(vcmd, capture_output=True, text=True, check=False)
        if vproc.returncode != 0:
            result["status"] = "validate-failed"
            result["stderr"] = (vproc.stderr or vproc.stdout)[-500:]
        else:
            result["status"] = "validated"

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch migrate forge diagrams via gen-fd.py")
    parser.add_argument("--manifest", type=Path, default=None, help="Audit JSON from audit-forge-diagrams.py")
    parser.add_argument("--forge-dir", type=Path, default=Path.home() / ".roxabi" / "forge")
    parser.add_argument("--apply", action="store_true", help="Write HTML (default: dry-run)")
    parser.add_argument("--validate", action="store_true", help="Run validate-fd.py --static-only after gen")
    parser.add_argument("--limit", type=int, default=0, help="Max entries to process (0 = all)")
    args = parser.parse_args()

    entries = load_manifest(args.manifest, args.forge_dir.expanduser().resolve())
    candidates = [e for e in entries if e.get("json_path") and e.get("action") in {"migrate-if-json", "validate", "needs-fd-data"}]

    if args.limit > 0:
        candidates = candidates[: args.limit]

    results = [migrate_entry(e, apply=args.apply, validate=args.validate) for e in candidates]
    ok = sum(1 for r in results if r["status"] in {"dry-run", "generated", "validated"})
    failed = [r for r in results if r["status"].endswith("failed")]

    print(json.dumps({"processed": len(results), "ok": ok, "failed": len(failed), "results": results}, indent=2))

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()