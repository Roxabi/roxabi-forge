#!/usr/bin/env bash
# forge_paths.test.sh — contract tests for forge_paths.py path resolution
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

PASS=0
FAIL=0
pass() { printf 'PASS: %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf 'FAIL: %s\n' "$1"; FAIL=$((FAIL + 1)); }

python3 - <<PY
import os, sys, tempfile
from pathlib import Path

sys.path.insert(0, "${SCRIPT_DIR}")
from forge_paths import resolve_forge_ref, default_expect_path, script_root

repo = Path("${REPO_ROOT}")
ref = resolve_forge_ref(repo)
assert (ref / "graph-templates/fd-shell.html").exists(), ref

expect = default_expect_path(repo)
assert expect is not None and expect.exists(), expect

# deployed layout: root/references/graph-templates/fd-shell.html
tmp = tempfile.mkdtemp()
refs = Path(tmp) / "references" / "graph-templates"
refs.mkdir(parents=True)
(refs / "fd-shell.html").write_text("<html></html>")
got = resolve_forge_ref(Path(tmp))
assert got == Path(tmp) / "references", got

# FORGE_REF override
override = tempfile.mkdtemp()
ov_refs = Path(override) / "graph-templates"
ov_refs.mkdir(parents=True)
(ov_refs / "fd-shell.html").write_text("<html></html>")
os.environ["FORGE_REF"] = override
try:
    got2 = resolve_forge_ref(Path("/tmp/unrelated"))
    assert got2 == Path(override), got2
finally:
    os.environ.pop("FORGE_REF", None)

os.environ["CI"] = "true"
os.environ["FORGE_REF"] = override
try:
    got3 = resolve_forge_ref(repo)
    assert got3 == ref, (got3, ref)
finally:
    os.environ.pop("CI", None)
    os.environ.pop("FORGE_REF", None)

print("ok")
PY
rc=$?
if [ "$rc" -eq 0 ]; then
  pass "forge_paths resolves repo, deployed, and FORGE_REF layouts"
else
  fail "forge_paths resolution checks (rc=$rc)"
fi

# script_root points at repo root from scripts/
ROOT=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from forge_paths import script_root; print(script_root('$SCRIPT_DIR/gen-fd.py'))")
if [ "$ROOT" = "$REPO_ROOT" ]; then
  pass "script_root returns repo root"
else
  fail "script_root expected $REPO_ROOT got $ROOT"
fi

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]