#!/usr/bin/env bash
# validate-descriptor.test.sh — contract tests for validate-descriptor.py
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
VALIDATOR="$SCRIPT_DIR/validate-descriptor.py"
FIXTURE="$REPO_ROOT/plugins/forge/skills/forge-chart/fixtures/lyra-stack-v2.json"
EXPECT="$REPO_ROOT/plugins/forge/skills/forge-chart/fixtures/lyra-stack-v2.expect.json"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
pass() { printf 'PASS: %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf 'FAIL: %s\n' "$1"; FAIL=$((FAIL + 1)); }

# A) lyra fixture passes at primary viewport
if python3 "$VALIDATOR" --in "$FIXTURE" --expect "$EXPECT" >/dev/null 2>&1; then
  pass "A: lyra-stack-v2 descriptor passes validation"
else
  fail "A: lyra-stack-v2 descriptor passes validation"
fi

# B) overlapping tg/dc coords fail at 1600px (strict)
BAD="$TMP/overlap.json"
python3 - <<'PY' "$FIXTURE" "$BAD"
import json, sys
from pathlib import Path
desc = json.loads(Path(sys.argv[1]).read_text())
for node in desc["nodes"]:
    if node["id"] == "tg":
        node["x"] = 7
    if node["id"] == "dc":
        node["x"] = 8
Path(sys.argv[2]).write_text(json.dumps(desc, indent=2))
PY
if python3 "$VALIDATOR" --in "$BAD" --expect "$EXPECT" >/dev/null 2>&1; then
  fail "B: overlapping tg/dc should fail min-gap at 1600px"
else
  pass "B: overlapping tg/dc fails min-gap at 1600px"
fi

# C) duplicate node id fails schema
DUP="$TMP/dup.json"
python3 - <<'PY' "$FIXTURE" "$DUP"
import json, sys
from pathlib import Path
desc = json.loads(Path(sys.argv[1]).read_text())
desc["nodes"].append(dict(desc["nodes"][0]))
Path(sys.argv[2]).write_text(json.dumps(desc, indent=2))
PY
if python3 "$VALIDATOR" --in "$DUP" --expect "$EXPECT" >/dev/null 2>&1; then
  fail "C: duplicate node id should fail"
else
  pass "C: duplicate node id fails schema check"
fi

# D) nodes-less type (gantt) passes — bespoke schema, exempt from node-graph checks
GANTT="$TMP/gantt.json"
cat > "$GANTT" <<'JSON'
{"type":"gantt","title":"t","theme":"lyra-v2","timeline":{"start":"2026-01-01","end":"2026-03-01"},"sections":[{"title":"s","bars":[{"label":"b","start":"2026-01-01","end":"2026-02-01"}]}]}
JSON
if python3 "$VALIDATOR" --in "$GANTT" >/dev/null 2>&1; then
  pass "D: nodes-less gantt descriptor passes (exempt from node-graph gate)"
else
  fail "D: nodes-less gantt descriptor passes (exempt from node-graph gate)"
fi

# E) node-graph type missing its nodes array still fails the gate
NONODES="$TMP/nonodes.json"
python3 - <<'PY' "$FIXTURE" "$NONODES"
import json, sys
from pathlib import Path
desc = json.loads(Path(sys.argv[1]).read_text())
desc.pop("nodes", None)
Path(sys.argv[2]).write_text(json.dumps(desc, indent=2))
PY
if python3 "$VALIDATOR" --in "$NONODES" --expect "$EXPECT" >/dev/null 2>&1; then
  fail "E: architecture descriptor missing nodes should still fail"
else
  pass "E: architecture descriptor missing nodes fails the gate"
fi

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]