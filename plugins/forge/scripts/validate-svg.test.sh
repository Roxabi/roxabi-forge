#!/usr/bin/env bash
# validate-svg.test.sh — contract/negative tests for validate-svg.sh
#
# RED gate: all 4 assertions FAIL before placeholder-aware impl.
# GREEN gate: all 4 assertions PASS after impl adds:
#   - check_nonscaling_stroke skips files whose nss comes via {{FGRAPH_BASE}} placeholder
#   - check_paths skips d="{{…}}" placeholder values
#   - check_base_contract: fgraph-base.css must contain non-scaling-stroke

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VALIDATOR="$SCRIPT_DIR/validate-svg.sh"
TPL="$SCRIPT_DIR/../references/graph-templates"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

PASS_COUNT=0
FAIL_COUNT=0

pass() { printf 'PASS: %s\n' "$1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { printf 'FAIL: %s\n' "$1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# ─────────────────────────────────────────────────────────────────────────────
# A) placeholder satisfies non-scaling-stroke
#    The file has preserveAspectRatio="none" + marker-end but no literal
#    non-scaling-stroke. It does carry {{FGRAPH_BASE}} which would inline
#    fgraph-base.css (which contains non-scaling-stroke).
#    Pre-impl: check_nonscaling_stroke fires → exit 1 → assertion FAILs (RED).
#    Post-impl: validator recognises {{FGRAPH_BASE}} as a proxy for nss → exit 0.
# ─────────────────────────────────────────────────────────────────────────────
FIXTURE_A="$TMP/fixture_a.html"
cat > "$FIXTURE_A" <<'HTML'
<!DOCTYPE html>
<html><head><title>Test A</title></head><body>
<svg class="fgraph-edges" viewBox="0 0 100 100" preserveAspectRatio="none">
  <defs><marker id="a" markerWidth="6" markerHeight="6"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>
  <path class="fg-edge" d="M 10,10 L 90,90" marker-end="url(#a)"/>
</svg>
<style>/* {{FGRAPH_BASE}} — inline fgraph-base.css here */</style>
</body></html>
HTML

bash "$VALIDATOR" "$FIXTURE_A" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  pass "A: placeholder {{FGRAPH_BASE}} satisfies non-scaling-stroke (rc=$rc, expected 0)"
else
  fail "A: placeholder {{FGRAPH_BASE}} satisfies non-scaling-stroke (rc=$rc, expected 0)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# B) check_paths skips {{…}} placeholder values
#    The file has d="{{REL_1_PATH}}" — the placeholder has no numeric tokens.
#    There is no marker-end so nss check is N/A.
#    Pre-impl: check_paths sees 0 numeric tokens < 4 → exit 1 → FAIL (RED).
#    Post-impl: validator skips d-values matching {{…}} → exit 0.
# ─────────────────────────────────────────────────────────────────────────────
FIXTURE_B="$TMP/fixture_b.html"
cat > "$FIXTURE_B" <<'HTML'
<!DOCTYPE html>
<html><head><title>Test B</title></head><body>
<svg class="fgraph-edges" viewBox="0 0 100 100" preserveAspectRatio="none">
  <path class="fg-edge" d="{{REL_1_PATH}}"/>
</svg>
</body></html>
HTML

bash "$VALIDATOR" "$FIXTURE_B" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  pass "B: placeholder d={{REL_1_PATH}} skipped by check_paths (rc=$rc, expected 0)"
else
  fail "B: placeholder d={{REL_1_PATH}} skipped by check_paths (rc=$rc, expected 0)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# C) real relational corpus is green
#    All .html in graph-templates/ and graph-templates/examples/ plus
#    fgraph-base.css must pass the validator without errors.
#    Pre-impl: at least one placeholder in the corpus triggers a failure → RED.
#    Post-impl: all files pass → exit 0.
# ─────────────────────────────────────────────────────────────────────────────
CORPUS_FILES=()
while IFS= read -r f; do CORPUS_FILES+=("$f"); done < <(find "$TPL" -maxdepth 1 -name '*.html' 2>/dev/null | sort)
while IFS= read -r f; do CORPUS_FILES+=("$f"); done < <(find "$TPL/examples" -maxdepth 1 -name '*.html' 2>/dev/null | sort)
CORPUS_FILES+=("$TPL/fgraph-base.css")

if [ "${#CORPUS_FILES[@]}" -eq 0 ]; then
  fail "C: real corpus is green — no corpus files found under $TPL"
else
  bash "$VALIDATOR" "${CORPUS_FILES[@]}" >/dev/null 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    pass "C: real corpus is green (${#CORPUS_FILES[@]} files, rc=$rc, expected 0)"
  else
    fail "C: real corpus is green (${#CORPUS_FILES[@]} files, rc=$rc, expected 0)"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# D) base self-guard: stripped fgraph-base.css must fail with base-contract
#    Place the stripped file in a subdir so its basename is exactly
#    "fgraph-base.css" (matching the exact-name gate in check_base_contract).
#    Only strip non-scaling-stroke; fgraph-base.css has no preserveAspectRatio="none"
#    so check_nonscaling_stroke cannot fire — no marker-end stripping needed.
#    Sub-assertion: the failure message must mention "base-contract" and must NOT
#    mention "non-scaling-stroke" as a check_nonscaling_stroke violation.
#    Pre-impl: no check_base_contract → stripped file exits 0 → assertion FAILs (RED).
#    Post-impl: check_base_contract fires → exit 1 → assertion PASSes.
# ─────────────────────────────────────────────────────────────────────────────
REAL_BASE="$TPL/fgraph-base.css"
mkdir -p "$TMP/based"
grep -v 'non-scaling-stroke' "$REAL_BASE" > "$TMP/based/fgraph-base.css"

bash "$VALIDATOR" "$TMP/based/fgraph-base.css" >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
  pass "D: base self-guard fires on stripped fgraph-base.css (rc=$rc, expected non-zero)"
else
  fail "D: base self-guard fires on stripped fgraph-base.css (rc=$rc, expected non-zero — check_base_contract not yet implemented)"
fi

# D-sub: failure must be base-contract only, NOT a non-scaling-stroke check
d_out=$(bash "$VALIDATOR" "$TMP/based/fgraph-base.css" 2>&1 || true)
if printf '%s' "$d_out" | grep -q 'base-contract' \
   && ! printf '%s' "$d_out" | grep -q '✗ non-scaling-stroke'; then
  pass "D-sub: base-contract isolated — output mentions base-contract and no non-scaling-stroke failure"
else
  fail "D-sub: isolation broken — expected base-contract in output without ✗ non-scaling-stroke. Output: $d_out"
fi

# ═════════════════════════════════════════════════════════════════════════════
# T8 — Negative drift-vector tests (gates live)
#
# Each test:
#   1. Creates a tmp copy of a real template (dep-graph.html)
#   2. Corrupts it with a specific drift vector
#   3. Asserts the validator fires (rc≠0) — PASS if gate works
#   4. Asserts the clean (unmodified) copy still passes (rc=0) — sanity
#   5. Simulates the lefthook guard glob match
#
# These tests are GREEN from the start (gates already fire).
# Never mutates the real corpus.
# ═════════════════════════════════════════════════════════════════════════════

REAL_TPL="$TPL/dep-graph.html"
if [ ! -f "$REAL_TPL" ]; then
  fail "T8-setup: dep-graph.html not found at $REAL_TPL — cannot run drift tests"
  printf '\n%d passed, %d failed\n' "$PASS_COUNT" "$FAIL_COUNT"
  exit 1
fi

# All drift fixtures go under a path containing 'graph-templates/' so the
# lefthook guard regex  grep -E 'graph-templates/.*\.html$'  matches them.
DRIFT_DIR="$TMP/graph-templates"
mkdir -p "$DRIFT_DIR"

# Sanity: clean copy must pass
CLEAN="$DRIFT_DIR/clean.html"
cp "$REAL_TPL" "$CLEAN"
bash "$VALIDATOR" "$CLEAN" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  pass "T8-sanity: unmodified dep-graph.html copy exits 0 (rc=$rc)"
else
  fail "T8-sanity: unmodified dep-graph.html copy exits 0 (rc=$rc, expected 0)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# T8-a) nss drift: delete {{FGRAPH_BASE}} AND any literal non-scaling-stroke
#        check_nonscaling_stroke must fire → rc≠0
# ─────────────────────────────────────────────────────────────────────────────
NSS_DRIFT="$DRIFT_DIR/nss-drift.html"
grep -v 'FGRAPH_BASE\|non-scaling-stroke' "$REAL_TPL" > "$NSS_DRIFT"

bash "$VALIDATOR" "$NSS_DRIFT" >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
  pass "T8-a: nss drift fires check_nonscaling_stroke (rc=$rc, expected non-zero)"
else
  fail "T8-a: nss drift fires check_nonscaling_stroke (rc=$rc, expected non-zero — gate did not fire)"
fi

# guard simulation for T8-a
staged=$(printf '%s\n' "$NSS_DRIFT" | grep -E 'graph-templates/.*\.html$' || true)
if [ -n "$staged" ]; then
  bash "$VALIDATOR" "$staged" >/dev/null 2>&1
  guard_rc=$?
  if [ "$guard_rc" -ne 0 ]; then
    pass "T8-a-guard: lefthook guard blocks nss-drift commit (guard_rc=$guard_rc, expected non-zero)"
  else
    fail "T8-a-guard: lefthook guard blocks nss-drift commit (guard_rc=$guard_rc, expected non-zero)"
  fi
else
  fail "T8-a-guard: drift fixture path did not match graph-templates glob (path: $NSS_DRIFT)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# T8-b) marker-units drift: inject markerUnits="userSpaceOnUse" on edge markers
#        check_marker_units must fire → rc≠0
# ─────────────────────────────────────────────────────────────────────────────
MU_DRIFT="$DRIFT_DIR/mu-drift.html"
sed 's/markerWidth="6" markerHeight="6" orient/markerUnits="userSpaceOnUse" markerWidth="6" markerHeight="6" orient/' \
  "$REAL_TPL" > "$MU_DRIFT"

bash "$VALIDATOR" "$MU_DRIFT" >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
  pass "T8-b: marker-units drift fires check_marker_units (rc=$rc, expected non-zero)"
else
  fail "T8-b: marker-units drift fires check_marker_units (rc=$rc, expected non-zero — gate did not fire)"
fi

# revert sanity: clean copy still passes
bash "$VALIDATOR" "$CLEAN" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  pass "T8-b-revert: clean copy still passes after mu drift fixture created (rc=$rc)"
else
  fail "T8-b-revert: clean copy still passes after mu drift fixture created (rc=$rc, expected 0)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# T8-c) dangling marker ref: inject marker-end="url(#fg-arr-does-not-exist)"
#        check_markers must fire → rc≠0
# ─────────────────────────────────────────────────────────────────────────────
DANGLING_DRIFT="$DRIFT_DIR/dangling-drift.html"
sed 's/marker-end="url(#fg-arr-amber)"/marker-end="url(#fg-arr-does-not-exist)"/g' \
  "$REAL_TPL" > "$DANGLING_DRIFT"

bash "$VALIDATOR" "$DANGLING_DRIFT" >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
  pass "T8-c: dangling-ref drift fires check_markers (rc=$rc, expected non-zero)"
else
  fail "T8-c: dangling-ref drift fires check_markers (rc=$rc, expected non-zero — gate did not fire)"
fi

# revert sanity: clean copy still passes
bash "$VALIDATOR" "$CLEAN" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  pass "T8-c-revert: clean copy still passes after dangling-ref drift fixture created (rc=$rc)"
else
  fail "T8-c-revert: clean copy still passes after dangling-ref drift fixture created (rc=$rc, expected 0)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
printf '\n%d passed, %d failed\n' "$PASS_COUNT" "$FAIL_COUNT"
if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
exit 0
