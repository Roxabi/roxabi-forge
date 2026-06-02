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
# D) base self-guard: stripped fgraph-base.css must fail
#    Copy fgraph-base.css, remove every line containing non-scaling-stroke.
#    Also remove lines that would trip the *existing* check_nonscaling_stroke
#    via comment-embedded SVG snippets (preserveAspectRatio="none" + marker-end=
#    without nss) so the ONLY reason to fail is the new check_base_contract.
#    Pre-impl: no check_base_contract → stripped file exits 0 → assertion FAILs (RED).
#    Post-impl: check_base_contract fires → exit 1 → assertion PASSes.
# ─────────────────────────────────────────────────────────────────────────────
STRIPPED="$TMP/fgraph-base-stripped.css"
grep -v 'non-scaling-stroke' "$TPL/fgraph-base.css" \
  | grep -v 'marker-end=' \
  | grep -v 'marker-start=' \
  > "$STRIPPED"

bash "$VALIDATOR" "$STRIPPED" >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
  pass "D: base self-guard fires on stripped fgraph-base.css (rc=$rc, expected non-zero)"
else
  fail "D: base self-guard fires on stripped fgraph-base.css (rc=$rc, expected non-zero — check_base_contract not yet implemented)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
printf '\n%d passed, %d failed\n' "$PASS_COUNT" "$FAIL_COUNT"
if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
exit 0
