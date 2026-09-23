/**
 * GET  /api/visibility?slug=  → { slug, visibility, shareUrl? }  (team)
 * POST /api/visibility { slug, visibility } → set vis, mint/revoke share key
 * POST /api/visibility { slugs, visibility }
 *   → 200 { visibility, ok, failed } for up to 100 pages, even on partial success
 *
 * public | shared | private — mutually exclusive. Keys never in HTML.
 * POST requires JSON body + Origin/Referer matching canonical host (CSRF).
 */
import {
  type ForgeEnv,
  type Visibility,
  isArtefactRef,
  activateShare,
  getVisibility,
  isTeamRequest,
  json,
  mintKey,
  publicOrigin,
  revokeShare,
  setVisibility,
} from "../_lib/access"
import { artefactPath, assetExists } from "../_lib/assets"
import { enforceMutationGuard } from "../_lib/csrf"
import { upsertShortlink } from "../_lib/shlink"

const VIS: Visibility[] = ["private", "shared", "public"]

const BATCH_LIMIT = 100

// KV writes are binding I/O. A lot of 100 is up to two writes per page; firing
// every promise at once can stall the isolate and turn one slow call into a
// timeout for the whole lot. Chunks of 10 bound that without serialising every
// round-trip. Each page is caught on its own so one failure cannot reject the
// chunk and discard successes already settled beside it.
const WRITE_CONCURRENCY = 10

function isVisibility(value: unknown): value is Visibility {
  return value === "private" || value === "shared" || value === "public"
}

function isStringList(value: unknown[]): value is string[] {
  return value.every((item) => typeof item === "string")
}

/**
 * Catalogue paths (`f`, one leading slash stripped).
 *
 * One ASSETS fetch, then an in-memory membership test. `assetExists` is a
 * subrequest per page, and a lot of 100 would exhaust the Worker subrequest
 * budget. The manifest is the catalogue the landing acts on, so it is the
 * existence source for a batch. null means unreadable: the caller fails the
 * whole call and writes nothing.
 */
async function cataloguedPaths(
  env: ForgeEnv,
  request: Request,
): Promise<Set<string> | null> {
  let res: Response
  try {
    res = await env.ASSETS.fetch(new URL("/manifest.json", request.url).toString())
  } catch {
    return null
  }
  if (!res.ok) return null
  let parsed: unknown
  try {
    parsed = await res.json()
  } catch {
    return null
  }
  if (!Array.isArray(parsed)) return null
  const paths = new Set<string>()
  for (const entry of parsed) {
    if (typeof entry !== "object" || entry === null || !("f" in entry)) continue
    const raw = entry.f
    if (typeof raw !== "string" || raw.length === 0) continue
    paths.add(raw.replace(/^\//, ""))
  }
  return paths
}

// Same KV writes as the single-page path. The shortener is one network call
// per page and is not configured for a lot, so this path never calls it.
async function applyBatchVisibility(
  kv: KVNamespace,
  slug: string,
  vis: Visibility,
): Promise<void> {
  if (vis === "shared") {
    // Reuse the live key so an existing /s URL keeps working. Mint only when
    // this page has never been shared.
    let key = await kv.get(`share:${slug}`)
    if (!key) key = mintKey()
    await activateShare(kv, slug, key)
    return
  }
  if (vis === "public") {
    await setVisibility(kv, slug, "public")
    await kv.delete(`share:${slug}`)
    return
  }
  await revokeShare(kv, slug)
}

async function writeInChunks(
  kv: KVNamespace,
  slugs: string[],
  vis: Visibility,
): Promise<Map<string, string>> {
  const errors = new Map<string, string>()
  for (let i = 0; i < slugs.length; i += WRITE_CONCURRENCY) {
    const chunk = slugs.slice(i, i + WRITE_CONCURRENCY)
    const outcomes = await Promise.all(
      chunk.map(async (slug) => {
        try {
          await applyBatchVisibility(kv, slug, vis)
          return { slug, error: "" }
        } catch {
          return { slug, error: "write_failed" }
        }
      }),
    )
    for (const outcome of outcomes) {
      if (outcome.error) errors.set(outcome.slug, outcome.error)
    }
  }
  return errors
}

async function onBatchPost(
  env: ForgeEnv,
  request: Request,
  slugs: unknown[],
  visibility: unknown,
): Promise<Response> {
  if (slugs.length === 0 || !isStringList(slugs)) {
    return json({ error: "invalid_slugs" }, 400)
  }
  if (slugs.length > BATCH_LIMIT) {
    return json({ error: "too_many" }, 400)
  }
  if (!isVisibility(visibility)) {
    return json({ error: "invalid_visibility" }, 400)
  }

  const catalogued = await cataloguedPaths(env, request)
  if (!catalogued) return json({ error: "manifest_unavailable" }, 500)

  const classified: Array<{ slug: string; error: string }> = []
  const apply: string[] = []
  const seen = new Set<string>()
  for (const slug of slugs) {
    if (!isArtefactRef(slug)) {
      classified.push({ slug, error: "invalid_slug" })
      continue
    }
    if (!catalogued.has(slug)) {
      classified.push({ slug, error: "not_found" })
      continue
    }
    classified.push({ slug, error: "" })
    // Same page twice must mint one share key, not two racing keys.
    if (!seen.has(slug)) {
      seen.add(slug)
      apply.push(slug)
    }
  }

  const writeErrors = await writeInChunks(env.SHARES, apply, visibility)
  const ok: string[] = []
  const failed: Array<{ slug: string; error: string }> = []
  for (const item of classified) {
    if (item.error) {
      failed.push(item)
      continue
    }
    const writeError = writeErrors.get(item.slug)
    if (writeError) {
      failed.push({ slug: item.slug, error: writeError })
      continue
    }
    ok.push(item.slug)
  }
  return json({ visibility, ok, failed })
}

export const onRequestGet: PagesFunction<ForgeEnv> = async (context) => {
  if (!(await isTeamRequest(context.request, context.env))) {
    return json({ error: "unauthorized" }, 401)
  }
  const slug = new URL(context.request.url).searchParams.get("slug") || ""
  if (!isArtefactRef(slug)) return json({ error: "invalid_slug" }, 400)
  const vis = await getVisibility(context.env.SHARES, slug)
  const key =
    vis === "shared" ? await context.env.SHARES.get(`share:${slug}`) : null
  let shareUrl: string | null = null
  if (key) {
    try {
      shareUrl = `${publicOrigin(context.env, context.request)}/s/${slug}/${key}/`
    } catch {
      shareUrl = null
    }
  }
  return json({ slug, visibility: vis, shareUrl })
}

export const onRequestPost: PagesFunction<ForgeEnv> = async (context) => {
  if (!(await isTeamRequest(context.request, context.env))) {
    return json({ error: "unauthorized" }, 401)
  }

  const csrf = enforceMutationGuard(context.request, context.env)
  if (csrf) return csrf

  let body: { slug?: string; visibility?: string; slugs?: unknown } = {}
  try {
    body = (await context.request.json()) as {
      slug?: string
      visibility?: string
      slugs?: unknown
    }
  } catch {
    return json({ error: "invalid_json" }, 400)
  }
  // An array `slugs` is the batch form. Anything else — missing, a string, a
  // single `{ slug }` — stays on the path the per-page share bar already calls.
  if (Array.isArray(body.slugs)) {
    return onBatchPost(context.env, context.request, body.slugs, body.visibility)
  }
  const slug = (body.slug || "").trim()
  const vis = body.visibility as Visibility
  if (!isArtefactRef(slug)) return json({ error: "invalid_slug" }, 400)
  if (!VIS.includes(vis)) return json({ error: "invalid_visibility" }, 400)

  const exists = await assetExists(context.env, context.request, slug)
  if (!exists) return json({ error: "not_found", slug }, 404)

  let shareUrl: string | null = null
  let shortUrl: string | null = null

  if (vis === "shared") {
    let key = await context.env.SHARES.get(`share:${slug}`)
    if (!key) key = mintKey()
    await activateShare(context.env.SHARES, slug, key)
    try {
      const origin = publicOrigin(context.env, context.request)
      shareUrl = `${origin}/s/${slug}/${key}/`
      shortUrl = (await upsertShortlink(context.env, shareUrl, slug)) || null
    } catch {
      return json({ error: "public_host_not_configured" }, 500)
    }
  } else if (vis === "public") {
    let publicUrl: string
    try {
      publicUrl = `${publicOrigin(context.env, context.request)}${artefactPath(slug)}`
    } catch {
      return json({ error: "public_host_not_configured" }, 500)
    }
    await setVisibility(context.env.SHARES, slug, "public")
    await context.env.SHARES.delete(`share:${slug}`)
    shortUrl = (await upsertShortlink(context.env, publicUrl, slug)) || null
  } else {
    await revokeShare(context.env.SHARES, slug)
  }

  return json({ slug, visibility: vis, shareUrl, shortUrl })
}
