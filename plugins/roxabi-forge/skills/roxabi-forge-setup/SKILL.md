---
name: roxabi-forge-setup
description: >-
  Configure the separately installed MCP publisher for the Roxabi forge.
  Triggers: "roxabi forge setup", "roxabi-forge-setup". Operator-invoked only.
---

# Set up the Roxabi forge publisher

Only run when the operator asks. This configures a proposed local client
entry; it does not migrate an instance, source data, credentials or access.

1. Obtain the operator-approved instance ID, distinct HTTPS read and management
   origins, OAuth issuer and endpoint origin, and dedicated absolute source
   roots. `mcpResource` must be the management origin plus `/mcp`. If the
   Roxabi management endpoint or other required values are absent or not
   approved, stop and ask the instance administrator; do not invent them.
   `~/.roxabi/forge` is local source, not evidence of live contents.
2. The public source is [go-silex/unkillable-forge at the reviewed
   revision](https://github.com/go-silex/unkillable-forge/tree/4db8a1f0d28515c67875ff2bd0d662d730c7156b):
   marketplace `unkillable-forge`, plugin `unkillable-forge`, source
   `./plugins/unkillable-forge`. Follow its
   [package README](https://github.com/go-silex/unkillable-forge/blob/4db8a1f0d28515c67875ff2bd0d662d730c7156b/plugins/unkillable-forge/README.md)
   for distribution and setup. The reviewed revision identifies the source;
   it does not by itself pin an installation. Use the complete installed
   `dist/` and `LICENSE`, not this plugin's root. Node 22+ and the matching
   native payload are required on Linux glibc 2.28+ or macOS 11+, x64 or arm64.
   Select `claude-code`, `codex` or `omp` explicitly.
3. Propose an operator-controlled profile outside the release with
   `schemaVersion`, `profileId`, `instanceId`, `readOrigin`, `manageOrigin`,
   `mcpResource`, `approvedAuthorizationIssuer`, `approvedEndpointOrigin`,
   `roots` (IDs and absolute paths), and `authProfile`. Keep private state in an
   existing operator-owned `0700` directory outside the release. On macOS its
   state files and directories must have no extended ACL, including inherited
   or deny-only entries. Never reuse legacy credentials or place secrets in chat.
4. With absolute paths to Node, the installed `dist/forge.js`, profile and
   state, use the package README's `profile-check --profile … --client …
   --state-dir …`. A successful check validates the profile; it does not
   establish login or publication.
5. Only the operator explicitly runs `connect` with the same profile, client
   and state and completes native interactive authorization. Use
   `config-proposal` with those arguments plus `--name`, `--node`, `--bundle`
   and `--home`; present its output for review. It does not modify a client
   profile. The operator installs the entry while preserving unrelated settings.
6. After installation, report native-client tool discovery separately from
   authorization and any later publication receipt. No setup or discovery
   proves a publication.

If MCP is unavailable, stop. Do not run wrangler login, provision Cloudflare,
request a Cloudflare token, rebuild an index, or deploy a full snapshot. The
legacy publisher and its pinned engine remain a distinct path, never an
implicit fallback; retain existing access, destinations and shortlinks.
