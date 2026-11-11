# Historical owner-file availability probe

**Status: prepared, not executed.** This prerequisite investigation does not close G1b, recover bytes, validate rights, import data, create a preview, or deploy. The `check-missing` POST is an internal Wrangler API; its side-effect freedom is **inference**, not proven. Do not describe the operation as strictly read-only.

## Authority and private inputs

The default preflight performs live GETs and requires authorization for use of the existing administrative token. `--probe` additionally requests an upload JWT and performs the internal POST. It requires **separate explicit operator approval for this exact operation and source commit**; F02/nonproduction approval does not cover it. A field in a JSON file is not human authorization. The operator must also independently review the exact commit and its CI results before approval. No call is made by adding this tool.

Prepare a private JSON target record from approved F01 evidence, not guessed values. Its keys are exactly the following, plus the optional keys shown; all are strings:

| Key | Provenance / constraint |
|---|---|
| `account_id` | Approved account, 32 lowercase hex characters |
| `project`, `public_host`, `production_branch` | Approved Pages project identity; hostname is bare lowercase |
| `source_deployment_id` | Historical deployment whose file map is to be checked |
| `expected_file_hash` | F01 opaque upload hash for `/asset-owners.json`, 32 lowercase hex characters |
| `expected_canonical_id`, `expected_latest_id` | Approved current project baseline IDs |
| `approved_source_sha` | Full lowercase commit SHA; required for `--probe` |
| `provenance` | Optional short non-secret label identifying the F01 evidence |

Do not put private values in Git, commands, tickets, logs, or this document. Inputs are explicit absolute paths to private regular files owned by the operator, mode `0600` or `0400`. Config and record JSON must not contain duplicate keys. The config must contain exactly matching `pages_project` and bare `public_host`; any configured `cloudflare_account_id` and `CLOUDFLARE_ACCOUNT_ID` in the env file or process environment must match the record. There is no project or host fallback. The two selected env keys are parsed as literal assignments, including quoted and `export` forms, never sourced; duplicates and malformed selected assignments are rejected. The existing `CLOUDFLARE_API_TOKEN` is required in the env file. The configured SHARES namespace is irrelevant here: it is not compared, read, changed, or used to infer ACLs.

## Execution, only after the relevant approval

Create an existing private evidence directory outside every Git worktree (mode `0700`). Choose a new absolute output path in that directory; it must not already exist or resolve into Git. Input files and existing configs are never modified.

```bash
python3 scripts/probe_owner_availability.py \
  --target-record /private/path/target.json \
  --config /private/path/forge.config.json \
  --env /private/path/forge.env \
  --output /private/path/preflight.json
```

This default preflight checks project identity and the historical file map, but does not request an upload JWT or POST. A successful preflight is not an availability result. For the separately approved probe, use the reviewed exact source SHA and a detached clean source worktree. For example, prepare the worktree before approval or execution:

```bash
git worktree add --detach /path/to/probe-worktree <approved-full-sha>
cd /path/to/probe-worktree
git rev-parse HEAD
git status --porcelain=v1 --untracked-files=all
```

The HEAD must equal the approved SHA and status must be empty. After explicit approval, run the same command from that worktree with a **new** output path and append `--probe`. The tool itself checks its source worktree is detached, clean, and at the full SHA in the private record; it cannot verify the human approval. Do not use a dirty worktree or an override. Git must be available.

Stdout reports only the outcome, evidence path, and SHA-256 of the evidence file. The private evidence is written atomically without overwriting, mode `0600`; it contains the target, safe request status metadata and outcome, but no JWT, token, response bodies or environment dump. `preflight`, `available`, and `missing` are completed outcomes; `missing` means stop. Failures exit nonzero and, when the API sequence has started and output is writable, retain safe partial diagnostics. Never paste private evidence into Git or public logs.

## Boundaries and stop policy

Only these fixed HTTPS API calls are used, once each, with TLS verification, no redirects, retries, alternate origin, or insecure override:

1. `GET /accounts/{account}/pages/projects/{project}`: exact name, production branch, approved host in domains, canonical and latest IDs must match.
2. `GET /accounts/{account}/pages/projects/{project}/deployments/{source_deployment_id}/files`: F01's `result.files` map must associate the fixed path with the approved opaque hash; an ambiguous or malformed map fails closed.
3. With `--probe` only: `GET .../upload-token`, then `POST /pages/assets/check-missing` with the upload JWT and exactly one expected hash. `[]` means available; `[expected hash]` means missing. Any other result fails closed.
4. With `--probe` only: repeat the project GET. Changed identity, canonical or latest deployment is concurrent drift: stop and preserve evidence. Never restore, roll back, reanchor, or overwrite another publication.

No KV calls, bytes retrieval, upload, upsert-hashes, deployment creation, deletion, or preview is implemented. Stop on mismatch, missing, malformed response, transport failure or drift; do not force a deployment. Availability is time-dependent and is not proof of recovered content or authorization. A subsequent preview/recovery operation, if still needed, is separately designed and separately approved; there is no one-shot retrieval URL here.

Protocol evidence: Wrangler **4.159.0** `wrangler-dist/cli.js` lines 301556–301560 (upload token) and 301574–301585 (check-missing request). These endpoints are internal and unstable. The file-map decoding convention is F01's `forge-inventory.py` (`result.files`). Neither Wrangler nor the probe was executed against Cloudflare as part of this preparation.
