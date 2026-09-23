# Cloudflare Pages — Roxabi team-prod instance (forge.roxabi.dev)

**Scope:** this page describes the **Roxabi** production forge — Pages project
`roxabi-forge`, host `forge.roxabi.dev`. On your own Cloudflare account, do not
reproduce these values: run `plugins/roxabi-forge/scripts/forge-provision.sh`,
which creates the project, the KV namespace and the Access apps with your host
and writes `"vault_markers": []` — see
[artifacts-config.md](./artifacts-config.md).

## Target

| Field | Value |
|---|---|
| Pages project | `roxabi-forge` (your own forge: whatever `pages_project` says — the wizard defaults to `forge`) |
| Mode | **Direct Upload** (`wrangler pages deploy`) |
| Custom domain | `forge.roxabi.dev` → CNAME to the project `pages.dev` (proxied) |
| Production | wrangler `--branch=main` (label only — no git-connected deploy), `--commit-message=roxabi-forge/v<version>` + `--commit-hash=<engine commit>`: the engine version stamp the next publish's drift gate reads back |

## Why not Git Integration

The repo is meant to be **public** (engine / plugin). Team HTML stays in the **hub**. A payload branch in the same repo = leak.

```
hub / artifacts/<slug>/           SSOT — not git
        ↓ publish.sh (OG local + build)
temp clone engine, tag roxabi-forge/v<plugin version> (functions + skeleton)
        ↓ wrangler pages deploy
Pages project                     live
```

CF credentials = **laptop** (`~/.config/roxabi/forge/forge.env`), not GitHub secrets.

Deploying with the wrong Cloudflare account breaks production — pin `CLOUDFLARE_ACCOUNT_ID` in `forge.env`.

## Machine config

| File | Role |
|---|---|
| `~/.config/roxabi/forge/forge.config.json` | `hub_root`, `pages_project`, `public_host`, `vault_markers`, optional `forge_repo` (empty = release engine) — SSOT for the project name and host |
| `~/.config/roxabi/forge/forge.env` | **credentials only**: token + account + KV id + Access vars · chmod 600 |
| [`.env.example`](../.env.example) | schema reference (placeholders, safe to commit) — **never copy it over a real `forge.env`** |

Derive `forge.env` from Cloudflare instead of hand-filling it:

```bash
wrangler login
plugins/roxabi-forge/scripts/forge-discover.sh --write
```

`--write` fills `CLOUDFLARE_ACCOUNT_ID`, `FORGE_SHARES_KV_ID`,
`CF_ACCESS_TEAM_DOMAIN`, `CF_ACCESS_AUD`, `PUBLIC_HOST` and `SHLINK_API_URL`
(chmod 600, key names only), and persists the confirmed `pages_project` into an
existing `forge.config.json`. It cannot discover `CLOUDFLARE_API_TOKEN` (a
secret) or `hub_root` (a local path) — add those, then re-run doctor.

### Two credentials, two lists

| Credential | Used by | Needs |
|---|---|---|
| `wrangler login` OAuth | `forge-discover.sh`, `forge-provision.sh`, `--share` KV fallback | scopes `pages (write)`, `workers_kv (write)` |
| `CLOUDFLARE_API_TOKEN` | `publish.sh` — every deploy, KV REST | permissions Account · Cloudflare Pages · **Edit** · Account · Workers KV Storage · **Edit** · Account · Account Settings · **Read** |

A token minted from the OAuth scope list fails the publish preflight, and OAuth
alone cannot deploy. Keep them separate.

## Publish flow

```bash
plugins/roxabi-forge/scripts/forge-doctor.sh
plugins/roxabi-forge/scripts/publish.sh my-slug ./file.html --title "…"
plugins/roxabi-forge/scripts/publish.sh --rebuild-index
```

Doctor exit `0` ready · `1` hub/config KO (`/roxabi-forge-setup`) · `2` hub OK but
deploy blocked — it names each blocker with the command that clears it.
`publish.sh` hard-stops on a `1` rather than deploying with example defaults, so
a half-configured laptop can no longer push to the production host.

No HTML `git push`. No GitHub Action deploy.

`publish.sh` patches the cloned `wrangler.toml` before deploy:

- KV placeholder `YOUR_KV_NAMESPACE_ID` ← `FORGE_SHARES_KV_ID`
- plain `[vars]` ← `CF_ACCESS_TEAM_DOMAIN`, `CF_ACCESS_AUD`, `PUBLIC_HOST`, optional `SHLINK_API_URL` (fetched from Pages if missing locally)

Without that inject, `wrangler pages deploy` can wipe dashboard **plain** vars (secrets are kept).

## Pages env (Functions)

Set in the Cloudflare dashboard / API — **never commit values**.

| Var | Type | Role |
|---|---|---|
| `CF_ACCESS_TEAM_DOMAIN` | plain | Access team host |
| `CF_ACCESS_AUD` | plain | comma-separated application AUDs |
| `PUBLIC_HOST` | plain | canonical host for share URLs (e.g. `forge.roxabi.dev`) |
| `SHLINK_API_KEY` | secret | Shlink API key — shortlinks on share |
| `SHLINK_API_URL` | plain | full create URL — **no default** |
| `FORGE_SHARE_SECRET` | secret | ops bypass for **POST/DELETE `/api/share` only** |
| KV `SHARES` | binding | share keys (`share:<slug>`) + visibility |

Local key material for ops (not git): e.g. `~/.config/roxabi/forge/shlink-api-key`.

## Checklist

- [ ] Pages project + custom domain
- [ ] Functions deployed and answering `x-forge-acl: vis-v4` **before** any Access Bypass — [cloudflare-access.md](./cloudflare-access.md)
- [ ] Access apps (login Allow · Bypass on the Functions-gated paths · `pages.dev` Allow)
- [ ] `forge.env` on every publishing machine, built with `forge-discover.sh --write`
- [ ] `forge-doctor.sh` exits `0` on each of those machines (`2` = credentials still missing)
- [ ] No `CLOUDFLARE_*` secrets in GitHub Actions
- [ ] Pages env vars above set; `wrangler.toml` has no real IDs
