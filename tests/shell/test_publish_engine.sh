#!/usr/bin/env bash
# Behavioral tests for the engine publish.sh deploys and the engine drift gate.
#
# What is locked here:
#   1. release mode clones the tag roxabi-forge/v<plugin version> — never main
#   2. a missing tag dies with a clear message, before any clone
#   3. an empty forge_repo is release mode on the public engine
#   4. a dev checkout on another version is refused before anything is archived
#   5. through the real CLI: production running a newer engine is refused before
#      any wrangler call; --allow-engine-downgrade lets it through and the
#      deploy carries the version stamp; an unreadable production version
#      refuses unless --allow-unverified, and --allow-engine-downgrade does not
#      lift that
#
# Isolation: git is a recording wrapper around the real binary, cloning a local
# file:// engine; wrangler and curl are recording stubs; python3 is a wrapper
# that answers only the Cloudflare reads (preflight, production stamp, live
# deployment, remote Pages vars) and runs every other call for real. Config,
# forge.env and the hub are temp files. No network, no ~/.config/roxabi/forge.
# bash 3.2-safe (no mapfile, no assoc arrays, no ${x^^}).
set -euo pipefail

# shellcheck source=tests/shell/lib/git-env-guard.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/git-env-guard.sh"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PUBLISH="${FORGE_PUBLISH_SH:-$ROOT/plugins/roxabi-forge/scripts/publish.sh}"
BASH_BIN="${FORGE_BASH:-bash}"

pass() { echo "  ok  $*"; }
fail() { echo "  FAIL $*" >&2; exit 1; }

echo "engine source + drift gate tests ($PUBLISH)"

PY_REAL="$(command -v python3)"
GIT_REAL="$(command -v git)"
P="$("$PY_REAL" -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' \
  "$ROOT/plugins/roxabi-forge/package.json")"
TAG="roxabi-forge/v$P"

TD="$(mktemp -d)"
trap 'rm -rf "$TD"' EXIT

gitq() { "$GIT_REAL" -c user.email=forge-test@example.com -c user.name="Forge Test" -c commit.gpgsign=false "$@"; }

# --- a local engine remote: the release tag, then a newer main ---------------
# main moves past the tag with a marker file, so a clone of main is visible.
mk_remote() {
  local dir="$1" with_tag="$2"
  mkdir -p "$dir/site" "$dir/functions"
  printf '404\n' > "$dir/site/404.html"
  printf 'export {};\n' > "$dir/functions/_middleware.ts"
  cp "$ROOT/wrangler.toml" "$dir/wrangler.toml"
  gitq -C "$dir" init -q
  gitq -C "$dir" add -A
  gitq -C "$dir" commit -q -m "engine release"
  if [ "$with_tag" = yes ]; then
    gitq -C "$dir" tag "$TAG"
  fi
  printf 'main only\n' > "$dir/site/MAIN-ONLY.html"
  gitq -C "$dir" add -A
  gitq -C "$dir" commit -q -m "unreleased work on main"
  gitq -C "$dir" branch -q -M main
}
mk_remote "$TD/remote" yes
mk_remote "$TD/untagged" no
TAG_SHA="$(gitq -C "$TD/remote" rev-parse "$TAG^{commit}")"
REMOTE_URL="file://$TD/remote"

# --- PATH stubs -----------------------------------------------------------------
mkdir -p "$TD/bin"
GIT_LOG="$TD/git.log"
WR_LOG="$TD/wrangler.log"
: > "$GIT_LOG"
: > "$WR_LOG"

cat > "$TD/bin/git" <<EOS
#!/usr/bin/env bash
printf '%s\n' "\$*" >> "$GIT_LOG"
exec "$GIT_REAL" "\$@"
EOS
cat > "$TD/bin/wrangler" <<EOS
#!/usr/bin/env bash
printf '%s\n' "\$*" >> "$WR_LOG"
exit 0
EOS
# KV snapshot read: a genuine 404 (no record yet), so the hub drift guard
# decides from the live deployment below instead of retrying over OAuth.
cat > "$TD/bin/curl" <<'EOS'
#!/usr/bin/env bash
printf '404'
exit 0
EOS
printf '{"ok": true, "has_deployment": true, "stamp": ""}\n' > "$TD/prod-stamp.json"
cat > "$TD/bin/python3" <<EOS
#!/usr/bin/env bash
# Offline stand-in for the Cloudflare reads only; everything else is real.
args=()
for a in "\$@"; do
  case "\$a" in
    *preflight_mutations*)
      echo '{"ok": true, "errors": [], "warnings": [], "checks": {"token": "stub"}, "require_kv": false}'
      exit 0 ;;
    prod-stamp)
      cat "$TD/prod-stamp.json"
      exit 0 ;;
    live-deployment)
      echo '{"ok": false, "error_kind": "no_deployment", "error": "stub: empty project"}'
      exit 0 ;;
    --fetch-remote) continue ;;  # patch from local vars only: no Pages API read
  esac
  args+=("\$a")
done
exec "$PY_REAL" "\${args[@]}"
EOS
chmod +x "$TD/bin/"*
export PATH="$TD/bin:$PATH"

# --- config / env / hub -----------------------------------------------------------
mkdir -p "$TD/hub/forge/team"
printf '<html><head><title>Page</title></head><body>page</body></html>\n' \
  > "$TD/hub/forge/team/page.html"
write_cfg() {
  cat > "$TD/cfg.json" <<EOF
{"version": 1, "hub_root": "$TD/hub", "artifacts_dir": "forge", "layout": "tree",
 "site_dir": "site", "registry_dir": "registry", "internal_prefix": "a",
 "public_host": "forge.test.invalid", "pages_project": "engine-test-project",
 "og_renderer": "off", "vault_markers": [], "forge_repo": "$1"}
EOF
}
write_cfg "$REMOTE_URL"
{
  printf 'CLOUDFLARE_API_TOKEN=%s\n' "engine-test-fake-token"
  printf 'CLOUDFLARE_ACCOUNT_ID=0123456789abcdef0123456789abcdef\n'
  printf 'FORGE_SHARES_KV_ID=deadbeefdeadbeefdeadbeefdeadbeef\n'
  printf 'CF_ACCESS_TEAM_DOMAIN=engine.cloudflareaccess.com\n'
  printf 'CF_ACCESS_AUD=engine-aud\n'
} > "$TD/forge.env"
chmod 600 "$TD/forge.env"
export FORGE_CONFIG="$TD/cfg.json" FORGE_ENV="$TD/forge.env" FORGE_ENV_FILE="$TD/forge.env"
unset FORGE_REPO
# Belt and braces: a stray urllib call lands on a dead local port.
export http_proxy="http://127.0.0.1:9" https_proxy="http://127.0.0.1:9"

# Library-only run of one function in a subshell (publish.sh installs its own
# EXIT trap and die() exits), with FORGE_REPO pinned.
lib_run() {
  local repo="$1"
  shift
  (
    export FORGE_PUBLISH_LIB_ONLY=1
    # shellcheck source=/dev/null
    . "$PUBLISH"
    # shellcheck disable=SC2034  # read by the sourced publish.sh functions
    FORGE_REPO="$repo"
    "$@"
  )
}

show_engine() {
  WORK="$TD/work-$1"
  mkdir -p "$WORK"
  materialize_engine
  printf 'COMMIT=%s\nSTAMP=%s\nDIRTY=%s\n' "$ENGINE_COMMIT" "$ENGINE_STAMP" "$ENGINE_DIRTY"
  [ -e "$WORK/repo/site/MAIN-ONLY.html" ] && echo "HAS_MAIN_ONLY"
  WORK=""
}

# --- 1. release mode clones the plugin's tag, never main ------------------------
: > "$GIT_LOG"
out=$(lib_run "$REMOTE_URL" show_engine release 2>&1) || { echo "$out" >&2; fail "release materialize failed"; }
grep -q -- "clone --depth 1 --branch $TAG " "$GIT_LOG" \
  || { cat "$GIT_LOG" >&2; fail "release mode did not clone --branch $TAG"; }
if grep -q -- '--branch main' "$GIT_LOG"; then
  cat "$GIT_LOG" >&2
  fail "release mode cloned main"
fi
case "$out" in *HAS_MAIN_ONLY*) fail "the deployed engine carries main's unreleased commit" ;; esac
case "$out" in *"COMMIT=$TAG_SHA"*) ;; *) echo "$out" >&2; fail "ENGINE_COMMIT is not the tag's commit" ;; esac
case "$out" in *"STAMP=$TAG"$'\n'*) ;; *) echo "$out" >&2; fail "ENGINE_STAMP is not $TAG" ;; esac
case "$out" in *"DIRTY=false"*) ;; *) echo "$out" >&2; fail "a release engine must not be marked dirty" ;; esac
pass "release mode clones --branch $TAG (never main) and stamps the tag's commit"

# --- 2. a missing tag dies before any clone -------------------------------------
: > "$GIT_LOG"
if out=$(lib_run "file://$TD/untagged" show_engine untagged 2>&1); then
  fail "a remote without $TAG must not deploy"
fi
case "$out" in
  *"engine release $TAG not found"*"never falls back to main"*) ;;
  *) echo "$out" >&2; fail "the missing-tag refusal must name the tag and the no-main rule" ;;
esac
if grep -Eq '(^| )clone ' "$GIT_LOG"; then
  cat "$GIT_LOG" >&2
  fail "a missing tag still reached git clone"
fi
pass "missing tag: clear refusal, no clone, no fallback to main"

# --- 3. empty forge_repo = release mode on the public engine --------------------
show_resolution() {
  resolve_engine_source
  printf 'MODE=%s\nSOURCE=%s\nREF=%s\n' "$ENGINE_MODE" "$ENGINE_SOURCE" "$ENGINE_REF"
}
out=$(lib_run "" show_resolution 2>&1) || { echo "$out" >&2; fail "empty forge_repo did not resolve"; }
case "$out" in
  *"MODE=release"*"SOURCE=https://github.com/Roxabi/roxabi-forge.git"*"REF=$TAG"*) ;;
  *) echo "$out" >&2; fail "empty forge_repo must be release mode on the public engine tag" ;;
esac
pass "empty forge_repo resolves to $TAG of the public engine (no clone needed to decide)"

# --- 4. a dev checkout on another version is refused ------------------------------
mkdir -p "$TD/old-engine/site" "$TD/old-engine/plugins/roxabi-forge"
printf '404\n' > "$TD/old-engine/site/404.html"
printf '{"name": "roxabi-forge", "version": "0.0.1"}\n' > "$TD/old-engine/plugins/roxabi-forge/package.json"
gitq -C "$TD/old-engine" init -q
gitq -C "$TD/old-engine" add -A
gitq -C "$TD/old-engine" commit -q -m "old engine"
: > "$GIT_LOG"
if out=$(lib_run "$TD/old-engine" show_engine old 2>&1); then
  fail "a dev checkout at 0.0.1 must not deploy under plugin $P"
fi
case "$out" in
  *"0.0.1"*"$P"*) ;;
  *) echo "$out" >&2; fail "the dev-mode refusal must name both versions" ;;
esac
if grep -q 'archive' "$GIT_LOG"; then fail "the mismatched checkout was archived anyway"; fi
pass "dev checkout on another version: refused before git archive"

# --- 5. the gate through the real CLI ----------------------------------------------
cli() {
  # $1 = log file; the rest = publish.sh argv. Returns publish.sh's status.
  local log="$1"
  shift
  : > "$WR_LOG"
  : > "$GIT_LOG"
  FORGE_PUBLISH_LIB_ONLY='' "$BASH_BIN" "$PUBLISH" "$@" > "$log" 2>&1
}

printf '{"ok": true, "has_deployment": true, "stamp": "roxabi-forge/v99.0.0"}\n' > "$TD/prod-stamp.json"
if cli "$TD/newer.log" --tree; then
  cat "$TD/newer.log" >&2
  fail "publish proceeded although production runs a newer engine"
fi
grep -q "production runs roxabi-forge 99.0.0, this plugin is $P" "$TD/newer.log" \
  || { cat "$TD/newer.log" >&2; fail "the refusal must name both versions"; }
grep -q 'claude plugin marketplace update roxabi-forge' "$TD/newer.log" \
  || fail "the refusal must print the marketplace update command"
grep -q 'omp plugin upgrade roxabi-forge@roxabi-forge' "$TD/newer.log" \
  || fail "the refusal must print the OMP upgrade command"
[ ! -s "$WR_LOG" ] || { cat "$WR_LOG" >&2; fail "wrangler ran although the engine drift gate refused"; }
if grep -Eq '(^| )clone ' "$GIT_LOG"; then fail "the engine was cloned although the gate refused"; fi
pass "production newer than the plugin: refused with the update commands, before any wrangler call or clone"

if ! cli "$TD/downgrade.log" --tree --allow-engine-downgrade; then
  cat "$TD/downgrade.log" >&2
  fail "--allow-engine-downgrade must let the publish through"
fi
grep -q 'allow-engine-downgrade was passed' "$TD/downgrade.log" \
  || fail "the override must warn about the downgrade"
deploy_line=$(grep '^pages deploy site ' "$WR_LOG" || true)
[ -n "$deploy_line" ] || { cat "$TD/downgrade.log" "$WR_LOG" >&2; fail "wrangler pages deploy never ran"; }
case "$deploy_line" in
  *"--commit-hash=$TAG_SHA"*"--commit-message=$TAG "*"--commit-dirty=false"*) ;;
  *) echo "$deploy_line" >&2; fail "the deploy must carry the engine stamp (hash, message, dirty=false)" ;;
esac
grep -q -- "--branch $TAG " "$GIT_LOG" || fail "the publish did not clone $TAG"
pass "--allow-engine-downgrade: deploys, stamped --commit-message=$TAG --commit-hash=<tag commit>"

printf '{"ok": false, "error_kind": "unreachable", "error": "stub: timed out"}\n' > "$TD/prod-stamp.json"
if cli "$TD/unreachable.log" --tree --allow-engine-downgrade; then
  fail "--allow-engine-downgrade must not lift an unreadable production version"
fi
grep -q 'production engine version unverified (stub: timed out)' "$TD/unreachable.log" \
  || { cat "$TD/unreachable.log" >&2; fail "the refusal must name the API failure"; }
[ ! -s "$WR_LOG" ] || fail "wrangler ran with an unverified production engine"
pass "Pages API unreachable: refused before wrangler, --allow-engine-downgrade does not lift it"

if ! cli "$TD/unverified.log" --tree --allow-unverified; then
  cat "$TD/unverified.log" >&2
  fail "--allow-unverified must lift an unreadable production version"
fi
grep -q '^pages deploy site ' "$WR_LOG" || fail "--allow-unverified did not reach the deploy"
pass "Pages API unreachable + --allow-unverified: warns and deploys"

printf '{"ok": true, "has_deployment": true, "stamp": ""}\n' > "$TD/prod-stamp.json"
cli "$TD/usage.log" --help || true
grep -q -- '--allow-engine-downgrade' "$TD/usage.log" || fail "usage() does not advertise --allow-engine-downgrade"
pass "usage() advertises --allow-engine-downgrade"

echo "all engine source + drift gate checks passed"
