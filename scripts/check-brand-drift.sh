#!/usr/bin/env bash
# check-brand-drift.sh — fail if known off-brand hex values appear in
# forge's shared CSS bases or gallery/graph/explainer templates.
#
# Scope: brand drift in DEFAULT tokens only. Project-specific overrides
# (--accent swaps in consuming pages) are out of scope and permitted.
#
# Brand SSoT: ~/.roxabi/forge/roxabi-site/brand/BRAND-BOOK.md §6
# Known drift:
#   #0c0e16  — legacy --bg (correct: #0d1117)
#   #13161f  — legacy --surface (correct: #13191f)
#   #e8a030  — legacy --accent (correct: #f0b429)
#   #dde4f0  — legacy --text (correct: #f0ede6)
#   Plus Jakarta Sans — not in any brand book (correct: Inter / IBM Plex Sans)
#
# Usage:
#   scripts/check-brand-drift.sh                    # scan all defaults
#   scripts/check-brand-drift.sh file1.css file2... # scan specific files
#
# Exit codes: 0 = clean, 1 = drift found

set -euo pipefail

# Files to scan (shared bases — default tokens, not per-project overrides)
DEFAULT_TARGETS=(
  "plugins/forge/references/gallery-templates/gallery-base.css"
  "plugins/forge/references/graph-templates/fgraph-base.css"
  "plugins/forge/references/base/explainer-base.css"
)

# Forbidden patterns: known off-brand hexes + non-brand fonts.
# Match case-insensitive on hex; font names as literal strings.
FORBIDDEN=(
  '#0c0e16'
  '#13161f'
  '#e8a030'
  '#dde4f0'
  'Plus Jakarta Sans'
)

if [ "$#" -gt 0 ]; then
  TARGETS=("$@")
else
  TARGETS=("${DEFAULT_TARGETS[@]}")
fi

found=0
for f in "${TARGETS[@]}"; do
  [ -f "$f" ] || continue
  for pat in "${FORBIDDEN[@]}"; do
    if grep -inF -- "$pat" "$f" >/dev/null 2>&1; then
      if [ "$found" -eq 0 ]; then
        echo ""
        echo "  error: brand drift detected — off-palette tokens in shared bases"
        echo ""
      fi
      grep -inF --color=never -- "$pat" "$f" | sed "s|^|    $f:|"
      found=1
    fi
  done
done

if [ "$found" -ne 0 ]; then
  echo ""
  echo "  Fix: align to Roxabi brand (BRAND-BOOK.md §6) or override --accent"
  echo "  in the consuming page's <style>, not in the shared base."
  exit 1
fi

exit 0
