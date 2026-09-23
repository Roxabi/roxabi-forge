# Changelog

All notable changes to the **roxabi-forge engine and plugin** are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versioning follows [Semantic Versioning](https://semver.org/) for the plugin surface (harness manifests / marketplaces / `package.json`). Releases are tagged `roxabi-forge/vX.Y.Z`.

**Out of scope for this file:** team HTML artifacts (hub + live deploy). Those are not versioned in git.

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
