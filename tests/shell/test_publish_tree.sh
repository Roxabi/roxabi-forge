#!/usr/bin/env bash
# Behavioral tests for `publish.sh --tree`: the data tree becomes the deploy
# snapshot, and the SSOT comes out byte-identical.
#
# Why this exists: the share bar is a control the TEAM sees on the served page.
# The old slug pipeline injected it into the hub copy, so the bar travelled back
# into the SSOT and every machine syncing that directory inherited it. Here the
# SSOT is read-only — the bar lives in $WORK/repo/site only — and that is the
# property this suite pins, together with the drift guard still refusing a
# snapshot that would delete a page the live record holds.
#
# Isolation: FORGE_CONFIG + FORGE_ENV point into mktemp -d and no Cloudflare
# credential is exported, so nothing here opens a socket. kv_get_key and
# live_deployment_json are redefined after the lib-only source, exactly as
# test_publish_snapshot.sh does.
# bash 3.2-safe (no mapfile, no declare -A).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PUBLISH="${FORGE_PUBLISH_SH:-$ROOT/plugins/roxabi-forge/scripts/publish.sh}"
SNAP="$ROOT/plugins/roxabi-forge/scripts/lib/snapshot.py"

pass() { echo "  ok  $*"; }
fail() { echo "  FAIL $*" >&2; exit 1; }

echo "tree publish tests ($PUBLISH)"

TD="$(mktemp -d)"
trap 'rm -rf "$TD"' EXIT

# --- a data tree, not a slug hub --------------------------------------------
mkdir -p "$TD/hub/forge/lyra/visuals" "$TD/hub/forge/metalyde" "$TD/hub/forge/_shared"
cat > "$TD/hub/forge/lyra/visuals/architecture.html" <<'EOF'
<html><head><title>Lyra architecture</title></head><body><h1>archi</h1></body></html>
EOF
cat > "$TD/hub/forge/metalyde/landing.html" <<'EOF'
<html><head><title>Metalyde</title></head><body><h1>landing</h1></body></html>
EOF
echo 'body{}' > "$TD/hub/forge/_shared/hero-base.css"
# The data tree carries its own legacy landing; the engine owns that name.
echo '<html><body>vieille landing</body></html>' > "$TD/hub/forge/index.html"

cat > "$TD/cfg.json" <<EOF
{"version": 1, "hub_root": "$TD/hub", "artifacts_dir": "forge", "layout": "tree",
 "site_dir": "site", "registry_dir": "registry", "internal_prefix": "a",
 "public_host": "forge.test.invalid", "pages_project": "forge-test-project"}
EOF
export FORGE_CONFIG="$TD/cfg.json"

: > "$TD/forge.env"
chmod 600 "$TD/forge.env"
export FORGE_ENV="$TD/forge.env"
export FORGE_ENV_FILE="$TD/forge.env"
unset CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID CLOUDFLARE_API_KEY CLOUDFLARE_EMAIL

PYQ="PYTHONPATH=$ROOT/plugins/roxabi-forge/scripts/lib"

iso=$(env "$PYQ" python3 -c '
import json
from load_config import forge_env_path, resolve_api_token
print(json.dumps({"env_path": str(forge_env_path()), "has_token": bool(resolve_api_token())}))') \
  || fail "could not probe credential isolation"
case "$iso" in
  *'"has_token": true'*) fail "a real Cloudflare token leaked into this suite" ;;
esac
case "$iso" in
  *"$TD/forge.env"*) ;;
  *) fail "FORGE_ENV not isolated: $iso" ;;
esac
pass "credentials isolated (no token, config + env in the temp dir)"

# --- the record is the tree's own pages, not top-level directories -----------
RECORD="$TD/record.json"
env "$PYQ" python3 "$SNAP" record \
  --deployment-id "dep-live-1" --engine-commit "abc1234" --by "tester@example.invalid" \
  > "$RECORD" || fail "record subcommand failed"
grep -q 'lyra/visuals/architecture.html' "$RECORD" \
  || fail "the record must key pages by path under layout tree: $(cat "$RECORD")"
grep -q 'metalyde/landing.html' "$RECORD" || fail "record misses metalyde/landing.html"
pass "the snapshot record keys pages by path"

# --- load publish.sh as a library -------------------------------------------
export FORGE_PUBLISH_LIB_ONLY=1
# shellcheck source=/dev/null
. "$PUBLISH"
trap 'rm -rf "$TD"' EXIT

WORK="$TD/work"
mkdir -p "$WORK/repo/site"
ARTIFACTS_ROOT="$TD/hub/forge"
DRY_RUN=false

# The engine owns the shell: a catalogue already sits in the clone's site/.
echo '<html><body>catalogue engine</body></html>' > "$WORK/repo/site/index.html"

ssot_state() {
  find "$TD/hub/forge" -type f -exec sha256sum {} \; | sed "s#$TD##" | sort
}

BEFORE="$(ssot_state)"

build_tree_from_ssot >/dev/null 2>&1 || fail "build_tree_from_ssot failed"

AFTER="$(ssot_state)"
[ "$BEFORE" = "$AFTER" ] || fail "the SSOT changed during a tree publish"
pass "the SSOT is byte-identical after a publish"

grep -q 'forge-share-bar' "$WORK/repo/site/lyra/visuals/architecture.html" \
  || fail "the served snapshot has no share bar"
grep -q 'forge-share-bar' "$TD/hub/forge/lyra/visuals/architecture.html" \
  && fail "the share bar leaked into the SSOT"
pass "the share bar is in the snapshot and not in the SSOT"

grep -q 'catalogue engine' "$WORK/repo/site/index.html" \
  || fail "the data tree overwrote the engine catalogue shell"
pass "the engine catalogue shell survives the copy"

[ -f "$WORK/repo/site/_shared/hero-base.css" ] || fail "core css missing from the snapshot"
grep -q 'lyra/visuals/architecture.html' "$WORK/repo/site/manifest.json" \
  || fail "manifest missing the page"
pass "core files and the manifest ship with the snapshot"

SNAPSHOT_SHA="$(sha256sum "$WORK/repo/site/lyra/visuals/architecture.html" | cut -d' ' -f1)"
build_tree_from_ssot >/dev/null 2>&1 || fail "second build_tree_from_ssot failed"
[ "$(sha256sum "$WORK/repo/site/lyra/visuals/architecture.html" | cut -d' ' -f1)" = "$SNAPSHOT_SHA" ] \
  || fail "a second publish changed the snapshot bytes"
[ "$(ssot_state)" = "$BEFORE" ] || fail "a second publish changed the SSOT"
pass "a second publish is byte-stable, snapshot and SSOT"

# --- the drift guard still refuses a page the live record holds --------------
KV_RECORD="$RECORD"
KV_GET_STATUS="ok"
kv_get_key() {
  [ -n "$KV_RECORD" ] || return 1
  cat "$KV_RECORD"
}
LIVE_JSON='{"ok":true,"deployment_id":"dep-live-1","engine_commit":"abc1234"}'
live_deployment_json() { printf '%s\n' "$LIVE_JSON"; return 0; }

ALLOW_UNVERIFIED=false
ALLOW_REMOVALS=false
EXPECTED_REMOVALS=""

if ! ( snapshot_guard ) 2>"$TD/guard.err"; then
  cat "$TD/guard.err" >&2
  fail "a tree matching the record must pass the guard"
fi
pass "a tree matching the live record deploys"

rm "$TD/hub/forge/metalyde/landing.html"
if ( snapshot_guard ) 2>"$TD/guard.err"; then
  fail "a tree missing a recorded page must refuse"
fi
grep -q 'metalyde/landing.html' "$TD/guard.err" \
  || fail "the refusal must name the page that would be deleted: $(cat "$TD/guard.err")"
pass "a publish that would remove a recorded page is refused, and names it"

ALLOW_REMOVALS=true
if ! ( snapshot_guard ) 2>"$TD/guard.err"; then
  cat "$TD/guard.err" >&2
  fail "--allow-removals must let a deliberate deletion through"
fi
pass "--allow-removals is the explicit way through"

echo "tree publish: all cases pass"
