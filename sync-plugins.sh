#!/usr/bin/env bash
# sync-plugins.sh — Push, pull, and sync roxabi-forge across machines + caches
#
# Usage:
#   ./sync-plugins.sh              # sync everything (local + remote)
#   ./sync-plugins.sh --local      # sync local cache only
#   ./sync-plugins.sh --remote     # sync Machine 1 cache only
#
# Flow:
#   1. Push staging to origin
#   2. Pull staging into local marketplace clone
#   3. Rsync all plugins → all local cache dirs (semver + hex-hash)
#   4. Pull staging on Machine 1 marketplace
#   5. Rsync all plugins → all Machine 1 cache dirs

set -euo pipefail

# Config
REMOTE_HOST="${REMOTE_HOST:-mickael@192.168.1.16}"
MARKETPLACE_REPO="$HOME/.claude/plugins/marketplaces/roxabi-forge"
CACHE_BASE="$HOME/.claude/plugins/cache/roxabi-forge"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() { echo -e "${GREEN}→ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

# Parse flags
DO_LOCAL=true
DO_REMOTE=true
if [[ "${1:-}" == "--local" ]]; then DO_REMOTE=false; fi
if [[ "${1:-}" == "--remote" ]]; then DO_LOCAL=false; fi

# Step 1: Push current branch to origin
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
step "Pushing $CURRENT_BRANCH to origin..."
git push origin "$CURRENT_BRANCH"

# sync_cache REPO CACHE — rsync all plugins into all discovered cache dirs
sync_cache() {
    local repo="$1"
    local cache="$2"
    local count=0

    for plugin_dir in "$repo/plugins"/*/; do
        local plugin
        plugin=$(basename "$plugin_dir")
        [ -d "$cache/$plugin" ] || continue

        for hash_dir in "$cache/$plugin"/*/; do
            local name
            name=$(basename "$hash_dir")
            # Skip non-cache dirs — only sync into semver (0.1.0) or hex-hash (6011eb380f4f)
            [[ "$name" == ".claude-plugin" ]] && continue
            [[ ! "$name" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && ! "$name" =~ ^[0-9a-f]{12}$ ]] && continue

            rsync -a \
                --exclude='node_modules' \
                --exclude='.orphaned_at' \
                "$plugin_dir" "$hash_dir"

            echo "  synced $plugin → $name"
            (( count++ )) || true
        done
    done

    echo -e "${GREEN}  $count cache dir(s) updated${NC}"
}

# sync_cache_safe REPO CACHE — snapshot cache, sync, restore on failure
sync_cache_safe() {
    local repo="$1"
    local cache="$2"
    local backup
    backup="$(mktemp -d "${TMPDIR:-/tmp}/sync-forge-backup.XXXXXX")"

    _sync_rollback() {
        warn "Sync failed — rolling back cache from $backup"
        rsync -a --delete "$backup/" "$cache/"
        rm -rf "$backup"
        warn "Rollback complete — cache restored to pre-sync state"
        exit 1
    }

    step "Snapshotting cache to $backup before sync..."
    if [ -d "$cache" ]; then
        rsync -a "$cache/" "$backup/"
    else
        warn "Cache dir $cache does not exist — nothing to snapshot"
    fi

    trap _sync_rollback ERR INT
    sync_cache "$repo" "$cache"
    trap - ERR INT
    rm -rf "$backup"
    echo -e "${GREEN}  rollback snapshot discarded (sync succeeded)${NC}"
}

# Step 2-3: Local sync
if [[ "$DO_LOCAL" == true ]]; then
    step "Pulling $CURRENT_BRANCH into local marketplace..."
    # Explicit branch fetch — marketplace's default refspec tracks main only, so
    # feature branches need +refs/heads/<branch>:refs/remotes/origin/<branch>.
    git -C "$MARKETPLACE_REPO" fetch origin \
        "+refs/heads/$CURRENT_BRANCH:refs/remotes/origin/$CURRENT_BRANCH"
    if git -C "$MARKETPLACE_REPO" rev-parse --verify "$CURRENT_BRANCH" &>/dev/null; then
        git -C "$MARKETPLACE_REPO" checkout "$CURRENT_BRANCH"
        git -C "$MARKETPLACE_REPO" merge --ff-only "origin/$CURRENT_BRANCH"
    else
        git -C "$MARKETPLACE_REPO" checkout -b "$CURRENT_BRANCH" "origin/$CURRENT_BRANCH"
    fi

    step "Syncing all plugins → local cache (with rollback-on-failure)..."
    sync_cache_safe "$MARKETPLACE_REPO" "$CACHE_BASE"
    echo -e "${GREEN}✓ Local cache updated${NC}"
fi

# Step 4-5: Remote sync (Machine 1)
if [[ "$DO_REMOTE" == true ]]; then
    step "Pulling $CURRENT_BRANCH on Machine 1 marketplace..."
    ssh "$REMOTE_HOST" "cd '$MARKETPLACE_REPO' && git fetch origin && git checkout '$CURRENT_BRANCH' && git merge --ff-only 'origin/$CURRENT_BRANCH'"

    step "Syncing all plugins → Machine 1 cache..."
    ssh "$REMOTE_HOST" "
        set -euo pipefail
        repo='$MARKETPLACE_REPO'
        cache='$CACHE_BASE'
        count=0
        for plugin_dir in \"\$repo/plugins\"/*/; do
            plugin=\$(basename \"\$plugin_dir\")
            [ -d \"\$cache/\$plugin\" ] || continue
            for hash_dir in \"\$cache/\$plugin\"/*/; do
                name=\$(basename \"\$hash_dir\")
                [[ \"\$name\" == '.claude-plugin' ]] && continue
                [[ ! \"\$name\" =~ ^[0-9]+\.[0-9]+\.[0-9]+\$ && ! \"\$name\" =~ ^[0-9a-f]{12}\$ ]] && continue
                rsync -a \
                    --exclude='node_modules' \
                    --exclude='.orphaned_at' \
                    \"\$plugin_dir\" \"\$hash_dir\"
                echo \"  synced \$plugin → \$name\"
                (( count++ )) || true
            done
        done
        echo \"\$count cache dir(s) updated\"
    "
    echo -e "${GREEN}✓ Machine 1 cache updated${NC}"
fi

echo -e "${GREEN}✓ All done${NC}"
