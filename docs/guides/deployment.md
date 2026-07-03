# Deployment Guide

Project-specific deployment procedures. Agents read this via `{standards.deployment}`.

> Universal patterns (CI/CD pipeline stages, Docker best practices, secret management) are embedded in the `devops` agent.
> This file documents **your project's specific** deployment setup.

## Environments

| Environment | URL | Deploy trigger | Auto-deploy? |
|-------------|-----|-----------------|:---:|
| Production  | forge.roxabi.dev (Cloudflare Pages, `--branch=main`) | Manual, from M₂ (roxabitower) only | No |

There is no CI-driven deploy: `.github/workflows/ci.yml` runs lint/py_compile/mermaid/SVG checks only — it does **not** run `build.sh`. Rendering (Open Graph images) and the Cloudflare Pages push happen only when a human runs the deploy chain below, on M₂. M₂ is required because it has `uv` 0.11.1 + a cached Chromium (`~/.cache/ms-playwright`) for Playwright-based OG rendering.

## Deploy Process

Ship code changes to `plugins/forge/` + `scripts/` all the way to the live `_dist/` on Cloudflare Pages via a 4-step chain, run from `~/.roxabi/forge/` on M₂:

1. **ff `staging` in the main checkout first.**
   ```bash
   git -C ~/projects/roxabi-forge pull --ff-only origin staging
   ```
   GOTCHA: step 2 (`make -C plugins/forge deploy`) copies `$(REPO_ROOT)/scripts/*` → `~/.roxabi/forge/scripts/`. If the checkout is behind `staging`, the deploy silently ships **stale scripts** — no error, just old logic running in prod.
2. **Deploy plugin files → `~/.roxabi/forge/`:**
   ```bash
   make -C plugins/forge deploy
   ```
   Copies `gen-og-*.py`, `_og_common.py`, `build.sh`, `Makefile`, and the rest of `scripts/` from the repo into the runtime dir.
3. **Build:**
   ```bash
   make -C ~/.roxabi/forge build
   ```
   Runs `build.sh`: renders per-artifact `.og.png` OG images, injects OG/Twitter meta tags, then rsyncs everything into `_dist/` (~14.5k files / 7.5G; files >25MB are auto-excluded; `.og.png` ships, only `*.py` and `_dist/` itself are excluded).
4. **Deploy:**
   ```bash
   make -C ~/.roxabi/forge deploy
   ```
   Runs `build` again, then `npx wrangler pages deploy _dist --project-name=forge --branch=main` → production (forge.roxabi.dev). Wrangler hash-dedups, so only the delta actually uploads.

**Verify live:**
```bash
curl forge.roxabi.dev/<path>   # og:image / twitter:image should point at the per-artifact .og.png
```
HEAD the `.og.png` URL directly → expect `200 image/png`. X dropped its card validator — re-share the link with `?v=1` appended to bust X's own cache when checking a card render.

**Known limitation:** heavy-animation artifacts can exceed the OG renderer's 30s Playwright timeout (e.g. `lyra/landing/lyra-landing-lattice-ignition-v0.1.0.html`) and silently fall back to the generic banner image instead of a real per-artifact card. If an artifact needs a true card, bump the per-artifact timeout in `scripts/gen-og-images.py`.

Provenance: per-artifact OG images shipped 2026-06-14 via #83 / #84 (merged `b3d4f62`).

## Monitoring & Health Checks

<!-- Document how you monitor deployments. Examples:
  - Health endpoint: GET /api/health (returns 200 + version)
  - Error tracking: Sentry (auto-captured)
  - Uptime: Vercel Analytics
-->

TODO: Document monitoring setup.
