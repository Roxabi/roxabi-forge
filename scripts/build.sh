#!/usr/bin/env bash
# build.sh — assemble _dist/ for static deployment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -n "${DIAGRAMS_DIR:-}" ] && [ -z "${FORGE_DIR:-}" ]; then
  echo "⚠ DIAGRAMS_DIR is deprecated — use FORGE_DIR" >&2
fi
export FORGE_DIR="${FORGE_DIR:-${DIAGRAMS_DIR:-$HOME/.roxabi/forge}}"
DIST="$FORGE_DIR/_dist"

echo "▸ Regenerating manifest.json…"
python3 "$SCRIPT_DIR/gen-manifest.py"

DEPS_JSON="$FORGE_DIR/lyra/visuals/deps/roadmap-deps.json"
if [ -f "$DEPS_JSON" ]; then
  echo "▸ Generating dependency tab from roadmap-deps.json…"
  python3 "$SCRIPT_DIR/gen-deps.py"
else
  echo "▸ Skipping dependency tab (no roadmap-deps.json)"
fi

echo "▸ Generating image gallery manifests…"
python3 "$SCRIPT_DIR/gen-image-manifests.py"

echo "▸ Injecting Open Graph meta tags…"
python3 "$SCRIPT_DIR/gen-og-tags.py"

echo "▸ Rendering per-artifact OG images…"
if command -v uv >/dev/null 2>&1; then
  # After og-tags so HTML mtimes are stable; non-fatal if playwright absent.
  timeout 600 uv run --with playwright python3 "$SCRIPT_DIR/gen-og-images.py" \
    || echo "  ⚠ OG image render skipped (rc=$?) — cards fall back to banner"
else
  echo "  ⚠ uv not found — skipping OG image render (cards fall back to banner)"
fi

echo "▸ Refreshing manifest.json (card preview flags)…"
python3 "$SCRIPT_DIR/gen-manifest.py"

if [ -x "$SCRIPT_DIR/gen-fd.py" ] && [ -f "$SCRIPT_DIR/validate-fd.py" ]; then
  FIXTURE="$SCRIPT_DIR/fixtures/lyra-stack-v2.json"
  EXPECT="$SCRIPT_DIR/fixtures/lyra-stack-v2.expect.json"
  if [ -f "$FIXTURE" ] && [ -f "$EXPECT" ]; then
    echo "▸ Validating fd-engine toolchain (lyra fixture)…"
    python3 "$SCRIPT_DIR/validate-descriptor.py" --in "$FIXTURE" --expect "$EXPECT"
    OUT="/tmp/forge-fd-check-$$.html"
    python3 "$SCRIPT_DIR/gen-fd.py" --in "$FIXTURE" --out "$OUT" --title "Lyra · Architecture"
    VALIDATE_ARGS=(--html "$OUT" --expect "$EXPECT")
    if command -v uv >/dev/null 2>&1 \
      && timeout 30 uv run --with playwright python3 -c "import playwright" >/dev/null 2>&1; then
      echo "  ▸ Running full Playwright fd layout gate…"
    else
      echo "  ⚠ Playwright unavailable — fd gate static-only (CI runs full browser checks)"
      VALIDATE_ARGS+=(--static-only)
    fi
    timeout 180 python3 "$SCRIPT_DIR/validate-fd.py" "${VALIDATE_ARGS[@]}"
    rm -f "$OUT"
  else
    echo "  ⚠ fd fixtures missing — skipping gen-fd gate"
  fi
else
  echo "▸ Skipping gen-fd gate (tooling not deployed)"
fi

echo "▸ Syncing to _dist/…"
mkdir -p "$DIST"
# Cloudflare Pages caps files at 25 MiB. Warn on oversize files so they're
# visible in build output before rsync silently skips them via --max-size.
MAX_SIZE_BYTES=$((25 * 1024 * 1024))
LARGE_FILES=$(find "$FORGE_DIR" -type f -size +${MAX_SIZE_BYTES}c \
  -not -path "*/_dist/*" -not -path "*/.git/*" -not -path "*/__pycache__/*" \
  -printf '  %s\t%p\n' 2>/dev/null | sort -rn || true)
if [ -n "$LARGE_FILES" ]; then
  echo "  ⚠ Excluding files > 25M (Cloudflare Pages limit):"
  echo "$LARGE_FILES" | awk -F'\t' '{printf "    %6.1f MB  %s\n", $1/1048576, $2}'
fi
# -L dereferences symlinks as real files so deployed _dist/ ships actual
# content rather than dangling symlinks. Required for galleries that
# symlink into external directories (e.g. ai-toolkit training output).
rsync -aL --delete --delete-excluded \
  --max-size=25M \
  --exclude='_dist/' \
  --exclude='*.py' \
  --exclude='graph-templates/*.html' \
  --exclude='graph-templates/*.og.png' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='.stignore' \
  --exclude='Makefile' \
  --exclude='.stversions/' \
  --exclude='lyra/brand/prompts/' \
  --exclude='lyra/avatar/prompts/' \
  --exclude='lyra/avatar/embeddings*/' \
  --exclude='lyra/avatar/lora-training-set/' \
  --exclude='lyra/avatar/generated/' \
  --exclude='lyra/avatar/workflows/' \
  --exclude='lyra/avatar/scripts/' \
  --exclude='*.safetensors' \
  --exclude='*.pt' \
  --exclude='*.npz' \
  --exclude='*.mp4' \
  "$FORGE_DIR/" "$DIST/" || {
    RC=$?
    # exit code 23 = partial transfer (e.g. dangling symlinks) — non-fatal
    [ $RC -eq 23 ] && echo "  ⚠ rsync: skipped some files (broken symlinks?) — continuing" || exit $RC
  }

# Defense-in-depth: _dist/ is deployed VERBATIM to public Cloudflare Pages, so a
# single missed --exclude leaks a secret. Hard-scrub secrets/operational files
# from the receiver regardless of exclude patterns, and drop a wrangler
# .assetsignore so the platform refuses to upload them even if they reappear.
rm -f "$DIST/.env" "$DIST"/.env.* "$DIST/Makefile" "$DIST/.stignore" 2>/dev/null || true
printf '.env\n.env.*\nMakefile\n.stignore\n.git\n' > "$DIST/.assetsignore"

# Purge oversize files left over in _dist/ from previous runs — rsync's
# --max-size skips transfer but doesn't delete existing receiver files.
find "$DIST" -type f -size +${MAX_SIZE_BYTES}c -delete 2>/dev/null || true

# Copy gallery UI from canonical forge location into _dist
cp "$FORGE_DIR/index.html" "$DIST/index.html"

FILE_COUNT=$(find "$DIST" -type f | wc -l)
SIZE=$(du -sh "$DIST" | cut -f1)
echo "▸ Build ready: $FILE_COUNT files, $SIZE → $DIST"
