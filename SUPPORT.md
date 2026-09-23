# Support

## What this repository is

Open-source **engine + Claude plugin** for a team artifact host pattern:

- Cloudflare Pages + Functions
- Cloudflare Access
- Optional keyed share links (`/s/…`)
- Hub SSOT outside git

## What we support here (GitHub)

| Topic | Channel |
|---|---|
| Plugin install, skills, `publish.sh` bugs | [GitHub Issues](https://github.com/Roxabi/roxabi-forge/issues) |
| Documentation gaps | PR or Issue |
| Security | [SECURITY.md](SECURITY.md) |

## What we do not support publicly

| Topic | Why |
|---|---|
| **`forge.roxabi.dev` production** | Hosted Roxabi service — internal ops |
| **Your Cloudflare account / Access apps** | You own your fork’s infrastructure |
| **HTML craft** (slides, pages) | The tool that generated the HTML — this repo only uploads it |
| **Lost share keys** | Keys are in KV only; rotate via toolbar or `--share` |

## Self-service

1. [README.md](README.md) — overview
2. Skill **`roxabi-forge-setup`** — machine config
3. Skill **`roxabi-forge-publish`** — upload flow
4. [docs/](docs/) — Access, Pages, share model
5. `plugins/roxabi-forge/scripts/forge-doctor.sh` — config health

## Forking

You may fork and deploy your own host. You are responsible for:

- Cloudflare Pages project, Access, KV, secrets
- Purging sensitive data from git history ([docs/public-release.md](docs/public-release.md))
- Setting `PUBLIC_HOST` and Access env vars on Pages

Share URLs and catalogue behavior depend on **your** KV and Access setup, not on the Roxabi production forge.
