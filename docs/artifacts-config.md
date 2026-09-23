# Artifacts + config + CF pipeline

## Why it used to be duplicated

| Layer | Historical role |
|---|---|
| `site/a/` + `registry/` **in git** | Deploy transport: push → GH Action → `wrangler pages deploy` without CF tokens on laptops |
| Hub notes | markdown pointers only |

Public engine repo + team HTML in git = leak.  
Git-connected payload branches are removed. Transport = Direct Upload.

## Current model (engine in git + HTML out of git)

| Layer | Location | Git? |
|---|---|---|
| **SSOT HTML + meta** | `$hub_root/$artifacts_dir/<slug>/` | **no** (shared vault) |
| **Engine** | `plugins/`, `functions/`, `wrangler.toml`, skeleton `site/` | **main** |
| **Live** | Pages project | **no** — `wrangler pages deploy` |

```
craft tool of your choice (slides / pages / diagrams)
        ↓ write
hub artifacts/<slug>/{index.html, meta.json}
        ↓ roxabi-forge-publish / publish.sh
build-site-from-hub.py  →  site/a + registry + catalogue  (temp, never commit)
        ↓ wrangler pages deploy site
forge.roxabi.dev
```

One Cloudflare account (via `forge.env`) + one hub + one host.  
Publish = doctor exit `0` (hub config sound **and** deploy credentials present).

## Sharing the artifacts directory

`$artifacts_dir` (under `hub_root`, from `forge.config.json`) **must be shared
between everyone who publishes to the same forge**. Every publish deploys a
**full** Pages snapshot rebuilt from that local copy, so publishing from a copy
that is behind **deletes** the artifacts the copy lacks — the live site has no
other source of truth (the Pages API exposes no per-file manifest).

How it is shared is the operator's choice: Google Drive, OneDrive, Dropbox,
Syncthing, rclone against any remote, a network share, … The repo assumes no
mechanism and talks to none of them.

None of them gives cross-machine exclusion, and a local lockfile cannot either.
The `snapshot:live` KV record is the enforcement point: it fingerprints the
local copy after each successful deploy, and the next publish refuses when it
would remove a recorded slug or cannot tell what is live. Refusal matrix and
overrides: `AGENTS.md` § Hub drift guard.

Two publishes from two machines can therefore overlap: a run spends minutes
building (engine clone, thumbnail rendering) between the guard's check and the
upload, and nothing serializes the two. The guard re-asserts the live
deployment id immediately before the upload, so an overlapping publish
**refuses** rather than deploying its older snapshot over the artifact the
other run just added. Publishing at the same time as a teammate is safe to
attempt — the loser simply re-runs.

## Machine config

```
~/.config/roxabi/forge/forge.config.json     # hub_root, pages_project, public_host, vault_markers, refused_targets
~/.config/roxabi/forge/forge.env             # credentials + CF_ACCESS_* + SHLINK_API_URL (chmod 600)
.env.example                          # schema reference (committed) — never cp'd onto forge.env
plugins/.../forge.config.example.json # defaults + code fallback
```

`pages_project` and `public_host` live **only** in `forge.config.json`.
`forge.env` holds credentials plus the Access/Shlink values that ship to Pages
as plain `[vars]`; it is not read for the host or the project name. The
direction of truth is config → `wrangler.toml` → Pages (`patch_wrangler.py` at
deploy), never Pages → config: a `forge.env` that disagreed with the config
used to decide which Pages project a deploy landed in.

Fill `forge.env` from Cloudflare, never from the example:

```bash
wrangler login
plugins/roxabi-forge/scripts/forge-discover.sh --write   # existing forge
plugins/roxabi-forge/scripts/forge-provision.sh          # your own account, no forge yet
```

Doctor: `plugins/roxabi-forge/scripts/forge-doctor.sh`  
Setup: `/roxabi-forge-setup` (user-invoked; owns creating `forge.config.json`).

| Doctor exit | Meaning | Next |
|---|---|---|
| `0` | ready | publish |
| `1` | hub / local config KO | `/roxabi-forge-setup` |
| `2` | hub OK, deploy blocked | fix the named blockers |

A missing `CLOUDFLARE_API_TOKEN` is still not a *hub* problem — generating an
artifact works, deploying does not. It is now exit `2` with an explicit blocker
line, instead of the silent `0` that let a token-less laptop look healthy.
`publish.sh` hard-stops on exit `1` and names `/roxabi-forge-setup`; it no longer falls
back to the example config.

### `hub_root` validation — `vault_markers`

`forge-doctor` checks that `hub_root` really is the vault, not a stray path.
Which directories prove that is configurable, because hubs have different
layouts.

| `vault_markers` | `hub_root` accepted when |
|---|---|
| absent / `null` | it is an existing directory — same as `[]`, the shipped default |
| `["A", "B"]` | it contains every named directory |
| `[]` | it is an existing directory — no structure check |
| anything else | never: doctor reports a config issue |

A malformed value is an issue rather than a silent fallback: falling back to
`[]` would skip a check the operator believed they had set.

### Deploy-target guard — `refused_targets`

A machine that publishes to more than one forge can name the targets a given
config must never deploy to. Every publish is a full snapshot that deletes what
the local hub lacks, so a config copied from the wrong machine would wipe the
other forge.

```json
"refused_targets": {
  "hosts": ["other-forge.example.com"],
  "pages_projects": ["other-forge"]
}
```

| Field | Refuses when |
|---|---|
| `hosts` | `public_host` matches an entry — case-insensitive, trimmed, compared without scheme, path, trailing slash or port |
| `pages_projects` | `pages_project` matches an entry — case-insensitive, trimmed |

Both lists are optional and default to empty; an absent key refuses nothing.
A match is a doctor **issue** (exit `1`) plus a `refused_target` deploy
blocker, so `publish.sh` stops at its doctor gate before any build or deploy.
A malformed value — not an object, a field that is not a list, a non-string
entry — is also an issue and a blocker: a guard the operator believes is armed
fails closed instead of silently allowing the deploy.

The plugin example config lists `other-forge.example.com` only to show the
shape; that reserved domain can never be a real host. Setting the key in a
local config replaces each list it names.

## A forge on your own Cloudflare account

This is the home for the client-owned case. The two Cloudflare docs
([cloudflare-pages.md](./cloudflare-pages.md),
[cloudflare-access.md](./cloudflare-access.md)) describe the **Roxabi team-prod**
instance — reproducing their values would configure *our* host, not yours.

```bash
plugins/roxabi-forge/scripts/forge-provision.sh
```

The wizard creates your Pages project (prompt default `forge`, not
`roxabi-forge`), the `SHARES` KV namespace, the API token, the custom domain, the
Zero Trust team and the three Access applications — and writes
`"vault_markers": []` into `forge.config.json` when that key is not already set,
so `hub_root` is checked only for existence. A re-run never overwrites an
existing `vault_markers`, `artifacts_dir` or `forge_repo`; it refreshes
`hub_root`, `public_host` and `pages_project` only.

Already have a forge (yours or Roxabi's) and just need to attach a machine →
`forge-discover.sh --write`, not the wizard.

## Commands

```bash
plugins/roxabi-forge/scripts/publish.sh my-slug --title "…" --type deck
plugins/roxabi-forge/scripts/publish.sh my-slug ./file.html --title "…" --type deck
plugins/roxabi-forge/scripts/publish.sh --share my-slug
plugins/roxabi-forge/scripts/publish.sh --unshare my-slug
plugins/roxabi-forge/scripts/publish.sh --list
plugins/roxabi-forge/scripts/publish.sh --remove my-slug
plugins/roxabi-forge/scripts/publish.sh --rebuild-index
```

## `main` must not contain

- `site/a/**` (live HTML)
- `site/index.html` (catalogue — generated by `gen-index.py` at publish)
- `registry/*.json`
- any payload branch
- Cloudflare account IDs, Access AUDs, or KV namespace IDs

Keep: `site/404.html`, `_headers`, `_redirects`, `robots.txt`, `images/`, `functions/`.
