#!/usr/bin/env bash
# validate-svg.sh — mechanical SVG/HTML quality gate for forge outputs.
#
# Usage: validate-svg.sh <file.svg|file.html> [...more]
#
# Checks (in order):
#   1. Tag balance          — xmllint --noout (skipped if xmllint absent)
#   2. Attribute quotes     — rg for unquoted attributes in SVG/HTML open tags
#   3. Marker refs          — every url(#id) must have a matching id="id"
#   4. Path data            — each <path d="..."> has ≥ 2 points
#   5. Marker units         — fail markerUnits="userSpaceOnUse" on a stretched SVG (giant arrowheads)
#   6. Non-scaling stroke   — fail marker edges on a stretched SVG without vector-effect:non-scaling-stroke (giant arrowheads)
#   7. rsvg-convert smoke   — render to /dev/null (skipped if rsvg-convert absent)
#
# Behavior:
#   - Pass        → exit 0
#   - Fail        → exit 1, prints first failure per file
#   - Tool missing → prints "skipped: <tool>" and exits 0 for that check only
#
# Source: fireworks-tech-graph validate-svg.sh + gmdiagram Quality Checklist.

set -uo pipefail

RED=$(printf '\033[31m') ; GRN=$(printf '\033[32m') ; YEL=$(printf '\033[33m') ; DIM=$(printf '\033[2m') ; RST=$(printf '\033[0m')

have() { command -v "$1" >/dev/null 2>&1; }

note_skip() { printf '  %s⚠ skipped%s  %s\n' "$YEL" "$RST" "$1"; }
note_ok()   { printf '  %s✓%s  %s\n' "$GRN" "$RST" "$1"; }
note_fail() { printf '  %s✗%s  %s\n' "$RED" "$RST" "$1"; }

check_tags() {
  local f=$1
  if ! have xmllint; then
    note_skip "tag-balance ($f): xmllint missing"
    return 0
  fi
  # HTML mode for .html, recover for .svg (SVG is XML but sometimes missing xmlns)
  case "$f" in
    *.html|*.htm)
      if xmllint --noout --html "$f" 2>/dev/null; then
        note_ok "tag-balance ($f)"
        return 0
      fi ;;
    *)
      if xmllint --noout --recover "$f" 2>/dev/null; then
        note_ok "tag-balance ($f)"
        return 0
      fi ;;
  esac
  note_fail "tag-balance ($f): xmllint rejected"
  return 1
}

check_attrs() {
  local f=$1
  # xmllint (when present) already enforces quoted attributes in strict mode.
  # When it's absent, fall back to a regex scoped by file type:
  #   .svg  → widened tag-name pattern (catches text/animate/stop/gradients/filters too)
  #   .html → skip (greedy regex false-matches <meta content="a=b, c=d"> etc.;
  #           install xmllint for reliable HTML attr-quote enforcement)
  # A naive regex cannot tell "unquoted attr" from "key=value inside a quoted
  # string" without a real parser, so we don't pretend to.
  if have xmllint; then
    note_ok "attr-quotes ($f): delegated to xmllint"
    return 0
  fi
  case "$f" in
    *.html|*.htm)
      note_skip "attr-quotes ($f): install xmllint for HTML attr-quote checks"
      return 0 ;;
  esac
  if grep -nE '<[a-zA-Z][a-zA-Z0-9:-]*\b[^>]*[[:space:]][a-zA-Z-]+=[^"'"'"' >/]' "$f" >/dev/null 2>&1; then
    note_fail "attr-quotes ($f): unquoted attribute inside tag"
    return 1
  fi
  note_ok "attr-quotes ($f)"
}

check_markers() {
  local f=$1
  local refs ids missing=0 src
  # Strip /* */ and <!-- --> comments first: a url(#id) or id="" living inside a
  # documentation comment (e.g. an ER-marker usage example) is not a live edge,
  # and must not trip the dangling-ref check. Falls back to raw text if perl absent.
  if have perl; then
    src=$(perl -0777 -pe 's{/\*.*?\*/}{}gs; s{<!--.*?-->}{}gs' "$f" 2>/dev/null)
  else
    src=$(cat "$f" 2>/dev/null)
  fi
  refs=$(printf '%s' "$src" | grep -oE 'url\(#[A-Za-z0-9_-]+\)' 2>/dev/null | sed -E 's/url\(#(.*)\)/\1/' | sort -u)
  [ -z "$refs" ] && { note_ok "markers ($f): no url() refs"; return 0; }
  ids=$(printf '%s' "$src" | grep -oE '\bid="[A-Za-z0-9_-]+"' 2>/dev/null | sed -E 's/id="(.*)"/\1/' | sort -u)
  while IFS= read -r r; do
    [ -z "$r" ] && continue
    if ! grep -qxF "$r" <<<"$ids"; then
      note_fail "markers ($f): url(#$r) has no matching id"
      missing=1
    fi
  done <<<"$refs"
  [ "$missing" -eq 0 ] && note_ok "markers ($f)"
  return "$missing"
}

check_paths() {
  local f=$1
  local bad=0
  # A path d="" must contain at least 2 coordinate pairs (min M+one more op).
  while IFS= read -r d; do
    local coords
    coords=$(printf '%s' "$d" | grep -oE '[-0-9.]+' | wc -l)
    if [ "$coords" -lt 4 ]; then
      note_fail "path-data ($f): path d=\"$d\" has <2 coord pairs"
      bad=1
      break
    fi
  done < <(grep -oE '[[:space:]]d="[^"]+"' "$f" 2>/dev/null | sed -E 's/.*d="(.*)"/\1/')
  [ "$bad" -eq 0 ] && note_ok "path-data ($f)"
  return "$bad"
}

check_marker_units() {
  local f=$1
  # GIANT-ARROWHEAD BUG: markerUnits="userSpaceOnUse" on a stretched SVG
  # (preserveAspectRatio="none", as every fgraph edge layer uses) sizes the
  # marker in the 0..100 user space, which the non-uniform scale blows up to
  # ~60-80px and distorts. Canonical markers omit markerUnits (→ strokeWidth
  # default) so they stay small + proportional via vector-effect:non-scaling-stroke.
  if grep -q 'preserveAspectRatio="none"' "$f" 2>/dev/null \
     && grep -q 'markerUnits="userSpaceOnUse"' "$f" 2>/dev/null; then
    note_fail "marker-units ($f): markerUnits=\"userSpaceOnUse\" on a preserveAspectRatio=\"none\" SVG → giant/distorted arrowheads. Remove markerUnits (use strokeWidth default), markerWidth/Height=6."
    return 1
  fi
  note_ok "marker-units ($f)"
  return 0
}

check_nonscaling_stroke() {
  local f=$1
  # GIANT-ARROWHEAD BUG (sibling of marker-units): on a stretched SVG
  # (preserveAspectRatio="none"), markers default to markerUnits="strokeWidth",
  # so marker size = markerWidth × stroke-width. Without
  # vector-effect:non-scaling-stroke the stroke-width is scaled by the non-uniform
  # viewport (×8+) → strokeWidth-relative markers blow up to giant distorted heads.
  # The fix that swaps userSpaceOnUse → strokeWidth (check 5) ONLY holds if the
  # stroke is non-scaling. So: any marker-ended edge on a stretched SVG MUST carry
  # vector-effect:non-scaling-stroke. (No marker edges → not applicable; pie/gantt.)
  if grep -q 'preserveAspectRatio="none"' "$f" 2>/dev/null \
     && grep -qE 'marker-(end|start)=' "$f" 2>/dev/null \
     && ! grep -q 'non-scaling-stroke' "$f" 2>/dev/null; then
    note_fail "non-scaling-stroke ($f): marker-ended edges on a preserveAspectRatio=\"none\" SVG but no vector-effect:non-scaling-stroke → giant/distorted arrowheads. Add \`.fg-edge { vector-effect: non-scaling-stroke; }\`."
    return 1
  fi
  note_ok "non-scaling-stroke ($f)"
  return 0
}

check_rsvg() {
  local f=$1
  # Only meaningful for pure SVG (HTML with <svg> fragments won't render alone).
  case "$f" in
    *.svg) ;;
    *) note_ok "rsvg-render ($f): not .svg, skipped"; return 0 ;;
  esac
  if ! have rsvg-convert; then
    note_skip "rsvg-render ($f): rsvg-convert missing"
    return 0
  fi
  if rsvg-convert -o /dev/null "$f" >/dev/null 2>&1; then
    note_ok "rsvg-render ($f)"
    return 0
  fi
  note_fail "rsvg-render ($f): rsvg-convert refused"
  return 1
}

main() {
  if [ "$#" -eq 0 ]; then
    printf 'usage: %s <file.svg|file.html> [...]\n' "$0" >&2
    return 2
  fi

  local overall=0
  for f in "$@"; do
    printf '%s── %s%s\n' "$DIM" "$f" "$RST"
    if [ ! -f "$f" ]; then
      note_fail "file not found"
      overall=1
      continue
    fi
    check_tags    "$f" || overall=1
    check_attrs   "$f" || overall=1
    check_markers "$f" || overall=1
    check_paths   "$f" || overall=1
    check_marker_units "$f" || overall=1
    check_nonscaling_stroke "$f" || overall=1
    check_rsvg    "$f" || overall=1
  done
  return "$overall"
}

main "$@"
