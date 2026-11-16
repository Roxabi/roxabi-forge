---
name: roxabi-forge-publish
description: >-
  Publish a standalone HTML artifact to the Roxabi forge, forge.roxabi.dev
  (Cloudflare Access internally; optional share via /s/<slug>/<key>/).
  Triggers: "roxabi forge publish", "publish to roxabi forge", "put on
  forge.roxabi.dev", "forge.roxabi.dev", "roxabi-forge-publish". Not for
  any other forge host (another forge plugin may expose generic `forge-*`
  skills on the same machine).
---

# Publish to the Roxabi forge

Publish only to the explicitly selected, approved Roxabi instance using the
separately installed Unkillable Forge MCP publisher. `https://forge.roxabi.dev`
is the existing read destination, not evidence of an approved management
endpoint. Preserve existing URLs, access, assets and shortlinks.

1. Select the Roxabi profile and configured source root explicitly. Discover
   `forge_publish` in the selected client and use its advertised schema. If
   the profile, approved endpoint or tool is unavailable, stop and direct the
   operator to `roxabi-forge-setup`; never fall back to the legacy publisher.
2. Supply source references (`rootId`, `relativePath`) and metadata, not file
   bodies, tokens or share keys. Include the complete intended artifact and
   its assets using the tool's source and optional manifest inputs. Inspect the
   advertised schema for new routes, existing targets and asset mappings.
3. For an update, require the operator's working explicit baseline or protected
   checkpoint. Specify resource/page/ownership removals explicitly. A conflict
   or missing selected source stops the operation: preserve local work and ask
   the operator to reconcile; never adopt a newer revision silently.
4. Call `forge_publish`. Retain its operation ID even on an interrupted error;
   use `forge_operation_status` and `forge_resume` for that same operation.
   Resume preserves its original command and identity; use
   `forge_abort_operation` only on request. For enrichment, use
   `forge_enrichments` and, when available and requested,
   `forge_retry_enrichments`.
5. Report the committed receipt separately from enrichment observations or
   failures. Do not claim publication without a receipt, or expose share keys.

`~/.roxabi/forge` is local source, not a live inventory. Do not infer live
deletions from its contents or run a full snapshot, rebuild or index operation.
The retained legacy scripts are a separate pinned path, not an MCP fallback.
HTML is active same-origin content: exclude secrets and untrusted scripts.
