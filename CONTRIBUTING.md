# Contributing to roxabi-forge

Thanks for your interest in this project.

**roxabi-forge** is the **engine + plugin** for hosting team HTML artifacts on Cloudflare Pages (Claude, Grok, OMP, Codex).  
It is **not** the place for decks, talks, or client HTML — those live in the **hub** (outside git).

## What we accept

| In scope | Out of scope |
|---|---|
| `plugins/roxabi-forge/` (skills, scripts, hooks) | HTML under `site/a/` or `registry/` |
| `functions/` (Access, share, catalogue) | Secrets, tokens, KV IDs, Access AUDs |
| `site/` skeleton (`404`, `_headers`, …) | Cloudflare ops on the production Roxabi account |
| Docs in `docs/`, `README`, this file | Tools that generate the HTML |

## Before you start

1. Read [README.md](README.md) and [AGENTS.md](AGENTS.md)
2. If going public on a fork: [docs/public-release.md](docs/public-release.md)
3. Never commit `~/.config/roxabi/forge/forge.env` or real infrastructure IDs

## Development setup

### Install the plugin

Harness-specific install commands: [README.md → Install the plugin](README.md#install-the-plugin).

### Machine config (for publish tests)

Do **not** `cp .env.example ~/.config/roxabi/forge/forge.env`. `.env.example` is a
schema reference (key names + comments); copying it over a real file wipes
discovered values and would point your deploy at the wrong host. Derive the
credentials from Cloudflare instead:

```bash
wrangler login
plugins/roxabi-forge/scripts/forge-discover.sh --write   # → forge.env (chmod 600), key names only
plugins/roxabi-forge/scripts/forge-doctor.sh
```

Doctor exits `0` ready · `1` hub/config KO → run the `roxabi-forge-setup` skill · `2`
hub OK but deploy blocked → add the blockers it names (API token, account id,
KV id, Access vars, `forge.env` permissions). `publish.sh` refuses to deploy on
a `1`.

No forge on your Cloudflare account yet → `plugins/roxabi-forge/scripts/forge-provision.sh`
(interactive wizard, your own project). You still need a valid **hub**
path in `~/.config/roxabi/forge/forge.config.json`; do not invent paths — use
`roxabi-forge-setup`.

## Plugin layout

```
.claude-plugin/marketplace.json    # Claude marketplace catalog
.grok-plugin/marketplace.json      # Grok marketplace catalog
.omp-plugin/marketplace.json       # OMP marketplace catalog
.agents/plugins/marketplace.json   # Codex repo marketplace
plugins/roxabi-forge/
  plugin.json                      # Agent Plugins 1.0.0 (OMP marketplace skills)
  .claude-plugin/plugin.json       # Claude plugin manifest
  .grok-plugin/plugin.json         # Grok plugin manifest
  .omp-plugin/plugin.json          # OMP plugin manifest
  .codex-plugin/plugin.json        # Codex plugin manifest
  package.json                     # OMP package (link / omp-plugins)
  skills/roxabi-forge-publish/SKILL.md
  skills/roxabi-forge-setup/SKILL.md
  skills/roxabi-forge-setup/agents/openai.yaml  # Codex: no implicit invocation
  scripts/publish.sh
  scripts/forge-doctor.sh
  scripts/forge-discover.sh              # derive forge.env from an existing forge
  scripts/forge-provision.sh             # stand up a forge on your own account
  scripts/gen-og-images.sh
  scripts/build-site-from-hub.py
  scripts/lib/load_config.py
  scripts/lib/discover.py
  scripts/lib/forge_common.sh
  scripts/lib/patch_wrangler.py
  forge.config.example.json
```

When changing behavior, update **skills** if user-facing workflows change.

## Making changes

1. **Fork** and create a branch: `feat/…`, `fix/…`, or `docs/…`. If you work with the
   dev-core plugin loaded, do this in a worktree (`git worktree add ../roxabi-forge-… -b feat/… main`),
   not with `git checkout -b` on the principal clone — the plugin blocks switching the principal off `main`.
2. **Edit** engine code or docs (English for user-facing text)
3. **Run checks** locally — one entrypoint per gate, the same files CI runs:

   ```bash
   bash scripts/secret-scan.sh   # two TruffleHog passes, repo-pinned scanner
   bash scripts/lint-shell.sh    # ShellCheck
   bash scripts/test-all.sh      # vitest + python/shell + release plugin (needs npm ci)
   python3 plugins/roxabi-forge/scripts/lib/load_config.py --doctor  # needs local hub config
   ```

   `npm ci` installs the pre-push hook (lefthook, via the `prepare` script) unless
   `core.hooksPath` is already set — shared hooks win, we never overwrite them. The hook
   runs the three commands above before anything leaves your machine. Emergency skip,
   document why: `LEFTHOOK=0 git push`.

   The scanner is **repo-pinned** under `.cache/trufflehog/<version>/` and verified by
   sha256 from [`config/trufflehog.version`](config/trufflehog.version) — never taken from
   `PATH`, so a stale or stub binary cannot decide whether the gate runs. Bumping it is
   manual; the procedure is in that file's header.

4. **Update** [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]` or the target version
5. **Open a PR** — the template checklist must pass

### Version bumps

If you change the plugin surface (skills, scripts, manifests):

- Bump `version` in all version-bearing manifests (canon = root `plugin.json`):
  - `plugins/roxabi-forge/plugin.json` (Agent Plugins `$schema` 1.0.0 — OMP marketplace skills with `claude-plugins` off)
  - `plugins/roxabi-forge/.claude-plugin/plugin.json`
  - `plugins/roxabi-forge/.grok-plugin/plugin.json`
  - `plugins/roxabi-forge/.omp-plugin/plugin.json`
  - `plugins/roxabi-forge/.codex-plugin/plugin.json`
  - `plugins/roxabi-forge/package.json`
  - `.claude-plugin/marketplace.json` (catalog + plugin entry)
  - `.grok-plugin/marketplace.json` (catalog + plugin entry)
  - `.omp-plugin/marketplace.json` (`metadata.version` + plugin entry)
- Codex `.agents/plugins/marketplace.json` has no version field — version comes from `.codex-plugin/plugin.json`
- Add a CHANGELOG `## [X.Y.Z]` section (same SemVer). CI fails if any of the files above drift
- On merge to `main`, the `release` job tags `roxabi-forge/vX.Y.Z` and opens a GitHub Release from that CHANGELOG section **only when the tag does not exist**. It never moves a tag. A merge without a version bump is a green no-op. A processed PR merge is classified (`classify`) and does not re-run the test suite — only release effects run.

## Pull requests

- One logical change per PR when possible
- No drive-by refactors
- Link related issues if any
- **Do not** include HTML artifacts, `.env`, or `forge.config.json` with real paths/tokens
- CI must pass (shell syntax + Python smoke tests)

### Title format

PR titles and commits follow [Conventional Commits](https://www.conventionalcommits.org/):
`<type>(<scope>)?: <subject>`, with `type` one of
`feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`,
and no trailing period. `!` marks a breaking change (`feat(share)!: …`).

Checked by `.github/workflows/pr-title.yml` (advisory — not a required status
check; ruleset `PR_Main` requires `check` and `test` only). The reason is a
readable history, not wiring: authored commits already follow the convention
(GitHub merge commits `Merge pull request #N` do not, and the workflow never
sees them). The PR title is what a reviewer reads in `gh pr list` and what you
carry into the CHANGELOG section by hand. No tool parses it — `--print-notes`
reads `CHANGELOG.md`, and the Release title comes from the tag
(`roxabi-forge vX.Y.Z`). GitHub's Revert button (`Revert "…"`) is accepted.

Reviewers may ask you to update skills, docs, or CHANGELOG.

## Security

See [SECURITY.md](SECURITY.md). Do not open public issues for vulnerabilities.

## Questions

- **Setup / publish on Roxabi infra** → internal team channel (not a public support obligation)
- **Engine bugs / plugin install** → GitHub Issues
- **Hosted `forge.roxabi.dev` uptime** → Roxabi ops (see [SUPPORT.md](SUPPORT.md))

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
