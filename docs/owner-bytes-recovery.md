# Historical owner bytes: disposable Pages recovery

**New candidate only. The approval that covered `aa6b126` is consumed and is not reusable. No operation is authorized or executed. G1b remains open. The 2026-11-12 Stage 2 cause is unknown.** Verified bytes are not an ACL or rights reconciliation. A response class is a shape of one reply, not that cause and not an ACL. No source-project deployment, upload, ACL change, import, rollback, or reanchor is performed. Do not merge this operational helper into legacy main to execute it.

## Authority and preparation

A single explicit operator approval must cover the exact reviewed source commit (including driver, pinned public Worker template and lock), existing Pages Write token, private account and source profile, disposable project name, up to 20 Cloudflare API calls plus bounded Pages GETs, cleanup, and residual risks R1–R6 below. A JSON field is not human approval. No provider call is authorized now. The default invocation is entirely offline.

Create a private `0700` output directory outside Git. The private approval record, config, and env must be absolute paths to operator-owned `0600` or `0400` regular files. JSON duplicate or unknown keys are rejected. No input files or existing configuration are changed. The record has exactly these keys:

| Key | Meaning |
|---|---|
| `source` | Eight-key Stage 1 target from approved F01 evidence |
| `approved_source_sha` | Full lowercase commit SHA of the reviewed source |
| `disposable_project` | New non-identifying Pages name, distinct from source |
| `worker_template_sha256` | SHA-256 of the reviewed tracked Worker template |
| `compatibility_date` | ISO date used in disposable project configuration |
| `hash_calibration` | At least three objects `{"path": "/private/absolute/file.json", "extension": "json", "expected_pages_hash": "<private Wrangler hash>"}` from distinct private F01 original pairs; extension is without the dot |
| `bypass_residual_accepted` | Boolean recording the approved R1 choice; false stops before D2 |
| `provenance` | Non-secret F01 evidence label |

The tool cross-checks config host/project and every provided account ID with the source profile; it never reads KV or infers ACLs. It verifies a detached, clean worktree at the exact recorded SHA, validates the template digest, renders it offline, and calibrates `blake3==1.0.11` against the private original Wrangler pairs. A mismatch stops before any network operation. Run in a separately created detached worktree, with Python 3.11+ and the reviewed PEP 723 lock using `uv run --locked --script`:

```bash
git worktree add --detach /path/to/recovery-worktree <reviewed-full-sha>
cd /path/to/recovery-worktree
uv run --locked --script scripts/recover_owner_bytes.py \
  --approval-record /private/path/record.json \
  --config /private/path/forge.config.json \
  --env /private/path/forge.env \
  --output-dir /private/path/evidence
```

This is offline preparation only. After independent review, CI, calibration, and explicit human approval, run the same command with `--execute` and an unused evidence directory. No JSON value grants approval. Never run with a dirty source tree or use an override.


## Checkpoints

The journal covers disposable admin calls and the check-missing classification. It is not a universal trace and not an ACL. A source probe has one group intent, not a row per request. Pages readiness, negative checks, and the download are not checkpointed individually. Before each disposable admin call, and before a check-missing or upload guard raises, the helper writes a new `checkpoint-NNN.json` through the existing no-overwrite `0600` writer. A checkpoint may contain only phase, slot, method, whether the socket was invoked, status (`unknown` when no HTTP status was observed; never a synthetic `0`), content-type (`json`, `other`, or `absent`), body state, classification, the synthetic fixture hash, a count, and the two cross-project booleans when they are actually known. It does not contain the response body, the source hash, tokens, account or deployment ids, hostnames, worker bytes, or exception text.

That file is a disk write. It is not a power-failure, storage-stack, or provider attestation. If the checkpoint write fails before ownership, there is no further provider call and no delete. After ownership, cleanup still runs once: id and name must match, and the name must not be the source project. A returned cleanup class, including `decoder_depth`, is stored in memory before its checkpoint and does not authorize DELETE. An unexpected cleanup failure stays unknown manual intervention: no invented class, no delete, and no further provider call. A journal failure is sticky. Later successful writes do not resume upload, deploy, Pages probes, or the source-after indicator. A failed final evidence write does not retry cleanup. A 2xx create or D2 whose receipt was not durably recorded may exist and needs manual attention; that uncertainty is not authority to delete an unowned project or to call the source project.

Continuation still requires the missing list to be exactly the synthetic fixture hash. Fixture upload must be an accepted application envelope before D1: `success` true, including a null result. An explicit rejection, a malformed envelope, or an unreadable body stops. The 20-minute D2 reserve is checked again after the D2 intent write and before that dispatch. Classes include `exact_fixture` (continue), `other_missing`, `historical_listed`, `result_shape`, `envelope_rejected`, `envelope_not_object`, `duplicate_key`, `unreadable_json`, `decoder_depth`, `body_read_failed`, `http_status`, and `not_observed`. `g1b_closed` stays false. `bytes_recovered` stays false when no verified file was saved. If verified bytes were already saved and a later journal write fails, those bytes stay recorded and the run is not a fully evidenced success.

## Bounded operation and stop conditions

1. Stage 1 checks source identity, historical map, availability and drift; only `available` proceeds. GET the new name and require 404. Create the disposable project once. A collision, lost receipt, or malformed creation receipt gives no ownership and is **never deleted automatically**.
2. With ownership established from the creation ID and name, obtain the disposable upload token. `check-missing` must say exactly the synthetic fixture is missing and the historical hash is present. Upload only the fixture. D1 uses a capability-gated Worker and the fixture; every actual D1 host must pass a positive authenticated check before the three marked empty-404 negative checks.
3. D2 is forbidden unless R1 is explicitly accepted and at least 20 minutes remain. D2 changes only the manifest to the historical hash, with identical Worker and routes. Its hash host must pass readiness and negative checks before one authenticated bounded download. The Pages hash must match. Verified bytes are durably written as `recovered-asset-owners.json` before cleanup; mismatched bytes are saved only as `unverified-download.bin`.
4. Every stop after ownership attempts cleanup **once**: GET the same project ID and name, DELETE once, then require GET 404. Mismatch or failure stops without retry or deletion of another resource. After D2 and successful DELETE, Stage 1 is repeated as a presence indicator only, not a service or no-GC proof. A failed indicator is an incident, not authority to restore.

All API calls use fixed HTTPS origin, verified TLS, no proxy, redirects, retry or fallback. Pages GETs accept only the runtime-approved host set, at most 30 readiness observations per host, 10 seconds apart, and at most 25 MiB per response. The program never logs secrets, capability paths, Worker contents, account/deployment IDs, hostnames, hashes from the source record, response bodies, or recovered bytes. Private evidence and downloaded files use `0600` atomic no-overwrite writes. Stdout gives only outcome, evidence path and evidence SHA-256. Retain evidence privately; do not put it in Git or public logs.

## Residual risks

- **R1:** if Functions are bypassed, the random 256-bit static capability path is the remaining barrier; account principals who can read deployment files or Worker code can see it. TTL does **not** protect a static bypass. Exposure lasts until successful project DELETE. `fail_open:false` is unproven defense in depth, not proof of fail-closed quota behavior. R1 must be explicitly accepted or D2 stops.
- **R2:** deleting the disposable project could affect a shared historical hash; the verified bytes are saved first, and the later presence indicator is neither a service check nor proof of causality.
- **R3–R6:** synthetic fixture retention is unknown; provider audit-log contents are inferred; lost receipts or failed cleanup require manual intervention; account principals with Pages Write may already reproduce cross-project recovery. The name-to-ID check has a residual race between GET and DELETE.

Endpoints and payloads are based on the documented [Cloudflare Pages API](https://developers.cloudflare.com/api/resources/pages/) and Wrangler 4.159.0. The existence and behavior of cross-project asset sharing, raw Worker deployment, readiness, and deletion effects remain runtime questions. Stop on any failed condition; no retries of mutations and no automatic source restoration.
