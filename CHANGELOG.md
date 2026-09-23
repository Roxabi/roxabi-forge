# Changelog

All notable changes to the **roxabi-forge engine and plugin** are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versioning follows [Semantic Versioning](https://semver.org/) for the plugin surface (harness manifests / marketplaces / `package.json`). Releases are tagged `roxabi-forge/vX.Y.Z`.

**Out of scope for this file:** team HTML artifacts (hub + live deploy). Those are not versioned in git.

## [1.1.1] - 2026-09-23

### Fixed

- The hub drift report no longer says `✗ refusing to deploy` (with remediation hints) when `--allow-removals` lets the deploy proceed: it now says `- deleting N artifact(s) from the live site on purpose (--allow-removals): <slugs>`. The same holds for the untrusted-record refusal when `--allow-unverified` lets the deploy proceed. Exit codes and the `snapshot.py compare` JSON are unchanged.

### Changed

- TypeScript 5.9.3 → 7.0.2 (`baseUrl` removed from `tsconfig.json`; `paths` already resolved relative to it).
- Vitest 3.2.7 → 5.0.1.
- CI actions: `actions/checkout` v4 → v7, `actions/setup-node` v4 → v7, `actions/setup-python` v5 → v7.
- Minor dev-dependency updates: `@types/node` 26.2.0 → 26.6.2, `lefthook` 2.1.12 → 2.1.14.

## [1.1.0] - 2026-09-23

### Added

- Release-pinned engine: `publish.sh` deploys the engine tagged `roxabi-forge/v<plugin version>`, the same release as the scripts running it. A missing tag stops the publish with a clear message; there is no fallback to `main`.
- Deploy version stamp: every deploy records its engine on the Pages deployment (`--commit-hash` = engine commit, `--commit-message` = `roxabi-forge/v<version>`, dev builds `roxabi-forge/v<version>+dev.<sha7>` with `--commit-dirty=true`).
- Engine drift gate: before any Cloudflare mutation, and in `--dry-run`, `publish.sh` reads the production engine version and refuses to deploy an older one, printing the plugin update commands. `--allow-engine-downgrade` deploys the older engine on purpose. An unreadable production version refuses unless `--allow-unverified`; an unstamped production (deployed before 1.1.0) is a warning, and the publish stamps it.
- `forge-doctor.sh --online` prints `engine   : prod <L|unknown> · plugin <P> · <state>`.

### Changed

- `forge_repo` is optional: empty means the public engine `https://github.com/Roxabi/roxabi-forge.git` in release mode. Setup and `forge-provision.sh` no longer default it to a detected checkout.
- A local checkout in `forge_repo` is an explicit dev mode: `git archive HEAD`, stamped `<version>+dev.<sha7>`, refused when its version differs from the plugin's unless `publish.sh` runs from that checkout. The doctor warns which commit will deploy, whether it is pushed, and that uncommitted changes are not deployed.

## [1.0.0] - 2026-09-23

First release of the tree-layout engine at `Roxabi/roxabi-forge`. It replaces roxabi-forge 0.x (plugin `forge`), whose repository is now `Roxabi/roxabi-forge-legacy`, archived. Uninstall `forge@roxabi-forge`, update the `roxabi-forge` marketplace, then install `roxabi-forge@roxabi-forge`.

### Added

- Tree-layout engine: a page is served at its tree path (extensionless canonical URL), not under a per-slug `/a/<slug>/` directory.
- Per-page ACL, **private by default**; a share link sets a share cookie that grants the page it was issued for.
- Public pages serve their assets through asset owners, so a public page never exposes a private sibling's files.
- Fragments and tabs are owned by the page that embeds them, including tabs pulled in by runtime loaders; their assets resolve against the parent page URL.
- Landing catalogue of pages, with batch visibility changes.
- Open Graph previews rendered at publish time, renderer `playwright`, `browser-run` (default) or `off` (`og_renderer`).
- Doctor validates `forge_repo`: a local checkout needs a commit and the tree-engine markers; the archived legacy URL is an issue that blocks deploy. Default chain: explicit value → detected engine checkout → `https://github.com/Roxabi/roxabi-forge.git`.
- Optional `refused_targets` config key (`hosts`, `pages_projects`): the doctor reports an issue and a `refused_target` deploy blocker when `public_host` or `pages_project` is listed, so `publish.sh` stops before any deploy. A malformed value fails closed.
- Skill preambles resolve the plugin root from `ROXABI_FORGE_PLUGIN_ROOT` first, so a machine running another forge plugin never points them at its scripts.
- An absent or null `vault_markers` means "no structure check", the same as the shipped example's `[]`.

### Changed

- Skills renamed `roxabi-forge-publish` and `roxabi-forge-setup` so they do not collide with another forge plugin that exposes generic `forge-publish` / `forge-setup` skill names on the same machines.
