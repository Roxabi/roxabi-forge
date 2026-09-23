import { afterEach, describe, expect, it, vi } from "vitest"
import type { ForgeEnv } from "@functions/_lib/access"
import { onRequestGet, onRequestPost } from "@functions/api/visibility"
import { generateTestJwtKeys, installJwksFetch, signJwt } from "./helpers/jwt"
import { failingKvAfter, mockKv } from "./helpers/kv"

const keys = generateTestJwtKeys()

function contextFor(env: ForgeEnv, visibility: "public" | "shared" | "private") {
  const now = Math.floor(Date.now() / 1000)
  const token = signJwt(keys.privateKeyPem, {
    exp: now + 3600,
    iss: "https://visibility-team.example.com",
    aud: "visibility-aud",
  })
  const request = new Request("https://forge.example.com/api/visibility", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      origin: "https://forge.example.com",
      "Cf-Access-Jwt-Assertion": token,
    },
    body: JSON.stringify({ slug: "demo-deck", visibility }),
  })
  return {
    request,
    env,
    params: {},
    data: {},
    functionPath: "/api/visibility",
    waitUntil: vi.fn(),
    next: vi.fn(),
  } as unknown as EventContext<ForgeEnv, string, Record<string, unknown>>
}

describe("visibility shortlinks", () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it("upserts f-<slug> to the public /a/ URL and returns it for copying", async () => {
    const kv = mockKv({
      "vis:demo-deck": "shared",
      "share:demo-deck": "old-secret-key",
    })
    const env: ForgeEnv = {
      SHARES: kv,
      ASSETS: {
        fetch: vi.fn().mockResolvedValue(new Response("", { status: 200 })),
      } as unknown as Fetcher,
      CF_ACCESS_TEAM_DOMAIN: "visibility-team.example.com",
      CF_ACCESS_AUD: "visibility-aud",
      PUBLIC_HOST: "forge.example.com",
      SHLINK_API_KEY: "test-api-key",
      SHLINK_API_URL: "https://s.example/rest/v3/short-urls",
    }
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes("/cdn-cgi/access/certs")) {
        return new Response(JSON.stringify({ keys: [keys.publicJwk] }), {
          status: 200,
        })
      }
      if (
        url === "https://s.example/rest/v3/short-urls/f-demo-deck" &&
        init?.method === "PATCH"
      ) {
        expect(JSON.parse(String(init.body))).toEqual({
          longUrl: "https://forge.example.com/a/demo-deck/",
        })
        return new Response(
          JSON.stringify({ shortUrl: "https://s.example/f-demo-deck" }),
          { status: 200 },
        )
      }
      return new Response("not found", { status: 404 })
    })
    vi.stubGlobal("fetch", fetchMock)

    const response = await onRequestPost(contextFor(env, "public"))
    expect(response.status).toBe(200)
    await expect(response.json()).resolves.toEqual({
      slug: "demo-deck",
      visibility: "public",
      shareUrl: null,
      shortUrl: "https://s.example/f-demo-deck",
    })
    await expect(kv.get("vis:demo-deck")).resolves.toBe("public")
    await expect(kv.get("share:demo-deck")).resolves.toBeNull()
  })
})

const PAGE = "lyra/visuals/architecture.html"
const LEGACY_SLUG = "legacy-talk"
const PAGE_ROADMAP = "lyra/visuals/roadmap.html"
const PAGE_BRIEF = "metalyde/notes/brief.html"
// One past the write chunk of 10, so a dropped tail cannot hide in the first chunk.
const CHUNK_TAIL = Array.from({ length: 11 }, (_, i) => `lyra/chunk/p${i}.html`)

// Shape re-parsed by functions/s/[[path]].ts. Not imported: that route is
// owned by the parallel layout change, and the API must keep emitting it.
const SHARE_EXCHANGE = /^\/s\/(.+\.html)\/([^/]+)\/?$/

/**
 * A deployment that only contains what it contains. The previous mock answered
 * 200 to every URL, so `assetExists` could never fail a test -- which is how a
 * slug-shaped existence check (`/a/<id>/index.html`) survived the migration and
 * answered 404 not_found on every real page.
 */
const DEPLOYED = new Set(["/lyra/visuals/architecture", "/a/legacy-talk/index.html"])
// Catalogue the landing selects from. One `f` keeps a leading slash: the batch
// lookup strips it, the same way the catalogue does, so a slashful entry still
// counts as deployed.
const CATALOGUED = [
  { f: PAGE },
  { f: PAGE_ROADMAP },
  { f: `/${PAGE_BRIEF}` },
  ...CHUNK_TAIL.map((f) => ({ f })),
]

function teamEnv(kv: KVNamespace): ForgeEnv {
  const fetch = vi.fn(async (input: RequestInfo | URL) => {
    // assetExists passes a Request; String() on one yields "[object Request]".
    const href = input instanceof Request ? input.url : String(input)
    const pathname = new URL(href).pathname
    if (pathname === "/manifest.json") {
      return new Response(JSON.stringify(CATALOGUED), {
        status: 200,
        headers: { "content-type": "application/json" },
      })
    }
    return new Response("", { status: DEPLOYED.has(pathname) ? 200 : 404 })
  })
  return {
    SHARES: kv,
    ASSETS: { fetch } as unknown as Fetcher,
    CF_ACCESS_TEAM_DOMAIN: "visibility-team.example.com",
    CF_ACCESS_AUD: "visibility-aud",
    PUBLIC_HOST: "forge.example.com",
  }
}

function teamJwt(): string {
  const now = Math.floor(Date.now() / 1000)
  return signJwt(keys.privateKeyPem, {
    exp: now + 3600,
    iss: "https://visibility-team.example.com",
    aud: "visibility-aud",
  })
}

function visibilityCtx(request: Request, env: ForgeEnv) {
  return {
    request,
    env,
    params: {},
    data: {},
    functionPath: "/api/visibility",
    waitUntil: vi.fn(),
    next: vi.fn(),
  } as unknown as EventContext<ForgeEnv, string, Record<string, unknown>>
}

function recordingKv(initial: Record<string, string> = {}) {
  const kv = mockKv(initial)
  const writes: string[] = []
  const put = kv.put.bind(kv)
  const remove = kv.delete.bind(kv)
  const recording = {
    ...kv,
    put: async (
      key: string,
      value: string | ArrayBuffer | ArrayBufferView | ReadableStream,
    ) => {
      writes.push(key)
      return put(key, value)
    },
    delete: async (key: string) => {
      writes.push(key)
      return remove(key)
    },
  }
  return { kv: recording as unknown as KVNamespace, writes }
}

function getRequest(slug: string, jwt = true): Request {
  const url = new URL("https://forge.example.com/api/visibility")
  url.searchParams.set("slug", slug)
  const headers = new Headers()
  if (jwt) headers.set("Cf-Access-Jwt-Assertion", teamJwt())
  return new Request(url, { headers })
}

function postRequest(slug: string, visibility: string, jwt = true): Request {
  const headers = new Headers({
    "content-type": "application/json",
    origin: "https://forge.example.com",
  })
  if (jwt) headers.set("Cf-Access-Jwt-Assertion", teamJwt())
  return new Request("https://forge.example.com/api/visibility", {
    method: "POST",
    headers,
    body: JSON.stringify({ slug, visibility }),
  })
}

function batchRequest(slugs: unknown, visibility: string, jwt = true): Request {
  const headers = new Headers({
    "content-type": "application/json",
    origin: "https://forge.example.com",
  })
  if (jwt) headers.set("Cf-Access-Jwt-Assertion", teamJwt())
  return new Request("https://forge.example.com/api/visibility", {
    method: "POST",
    headers,
    body: JSON.stringify({ slugs, visibility }),
  })
}

describe("tree page visibility", () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it("reads the visibility stored under the tree page key", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv({ [`vis:${PAGE}`]: "public" })
    const res = await onRequestGet(visibilityCtx(getRequest(PAGE), teamEnv(kv)))
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      slug: PAGE,
      visibility: "public",
      shareUrl: null,
    })
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("public")
  })

  it("stores public visibility under the tree page key", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv()
    const res = await onRequestPost(
      visibilityCtx(postRequest(PAGE, "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("public")
  })

  it("looks the page up on its canonical extensionless path", async () => {
    installJwksFetch([keys.publicJwk])
    const env = teamEnv(mockKv())
    await onRequestPost(visibilityCtx(postRequest(PAGE, "public"), env))
    const asked = vi.mocked(env.ASSETS.fetch).mock.calls.map((call) =>
      new URL(call[0] instanceof Request ? call[0].url : String(call[0])).pathname,
    )
    expect(asked).toContain("/lyra/visuals/architecture")
    expect(asked).not.toContain(`/a/${PAGE}/index.html`)
  })

  it("refuses a page the deployment does not contain, without touching KV", async () => {
    installJwksFetch([keys.publicJwk])
    const { kv, writes } = recordingKv()
    const res = await onRequestPost(
      visibilityCtx(postRequest("lyra/visuals/ghost.html", "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(404)
    await expect(res.json()).resolves.toMatchObject({ error: "not_found" })
    expect(writes).toEqual([])
  })

  it("mints a share URL the /s exchange can re-parse", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv()
    const res = await onRequestPost(
      visibilityCtx(postRequest(PAGE, "shared"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    const key = await kv.get(`share:${PAGE}`)
    expect(key).toEqual(expect.any(String))
    const sharePath = `/s/${PAGE}/${key}/`
    const exchange = sharePath.match(SHARE_EXCHANGE)
    expect(exchange?.[1]).toBe(PAGE)
    expect(exchange?.[2]).toBe(key)
    await expect(res.json()).resolves.toEqual({
      slug: PAGE,
      visibility: "shared",
      shareUrl: `https://forge.example.com${sharePath}`,
      shortUrl: null,
    })
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("shared")
  })

  it("refuses traversal and a leading slash without writing KV", async () => {
    installJwksFetch([keys.publicJwk])
    const { kv, writes } = recordingKv()
    const env = teamEnv(kv)
    for (const slug of ["lyra/../../etc/passwd.html", "/lyra/x.html"]) {
      const get = await onRequestGet(visibilityCtx(getRequest(slug), env))
      expect({ slug, method: "GET", status: get.status }).toEqual({
        slug,
        method: "GET",
        status: 400,
      })
      const post = await onRequestPost(
        visibilityCtx(postRequest(slug, "public"), env),
      )
      expect({ slug, method: "POST", status: post.status }).toEqual({
        slug,
        method: "POST",
        status: 400,
      })
    }
    expect(writes).toEqual([])
  })

  it("still accepts a legacy slug on GET and POST", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv({ [`vis:${LEGACY_SLUG}`]: "public" })
    const env = teamEnv(kv)
    const get = await onRequestGet(visibilityCtx(getRequest(LEGACY_SLUG), env))
    expect(get.status).toBe(200)
    await expect(get.json()).resolves.toEqual({
      slug: LEGACY_SLUG,
      visibility: "public",
      shareUrl: null,
    })
    const post = await onRequestPost(
      visibilityCtx(postRequest(LEGACY_SLUG, "private"), env),
    )
    expect(post.status).toBe(200)
    await expect(kv.get(`vis:${LEGACY_SLUG}`)).resolves.toBe("private")
  })

  it("returns 401, not 400, for a valid page path without a team JWT", async () => {
    const kv = mockKv()
    const env = teamEnv(kv)
    const get = await onRequestGet(visibilityCtx(getRequest(PAGE, false), env))
    expect(get.status).toBe(401)
    await expect(get.json()).resolves.toEqual({ error: "unauthorized" })
    const post = await onRequestPost(
      visibilityCtx(postRequest(PAGE, "public", false), env),
    )
    expect(post.status).toBe(401)
    await expect(post.json()).resolves.toEqual({ error: "unauthorized" })
  })
})

describe("batch visibility", () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it("sets public on every catalogued page from one manifest read", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv({ [`share:${PAGE}`]: "stale-share" })
    const env = teamEnv(kv)
    // A configured shortener must stay idle: the batch path does not call it.
    env.SHLINK_API_KEY = "k"
    env.SHLINK_API_URL = "https://s.example/rest/v3/short-urls"
    const slugs = [PAGE, PAGE_ROADMAP, PAGE_BRIEF]
    const res = await onRequestPost(
      visibilityCtx(batchRequest(slugs, "public"), env),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      visibility: "public",
      ok: slugs,
      failed: [],
    })
    for (const slug of slugs) {
      await expect(kv.get(`vis:${slug}`)).resolves.toBe("public")
      await expect(kv.get(`share:${slug}`)).resolves.toBeNull()
    }
    const asked = vi.mocked(env.ASSETS.fetch).mock.calls.map((call) =>
      new URL(call[0] instanceof Request ? call[0].url : String(call[0])).pathname,
    )
    expect(asked).toEqual(["/manifest.json"])
    const shlinkCalls = vi.mocked(fetch).mock.calls.filter((call) =>
      String(call[0]).includes("short-urls"),
    )
    expect(shlinkCalls).toEqual([])
  })

  it("reports a page missing from the manifest and does not write it", async () => {
    installJwksFetch([keys.publicJwk])
    const missing = "lyra/visuals/ghost.html"
    const { kv, writes } = recordingKv()
    const res = await onRequestPost(
      visibilityCtx(batchRequest([PAGE, missing, PAGE_ROADMAP], "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      visibility: "public",
      ok: [PAGE, PAGE_ROADMAP],
      failed: [{ slug: missing, error: "not_found" }],
    })
    expect(writes).not.toContain(`vis:${missing}`)
    expect(writes).not.toContain(`share:${missing}`)
    await expect(kv.get(`vis:${missing}`)).resolves.toBeNull()
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("public")
    await expect(kv.get(`vis:${PAGE_ROADMAP}`)).resolves.toBe("public")
  })

  it("parks a traversal in failed and still applies the valid pages", async () => {
    installJwksFetch([keys.publicJwk])
    const bad = "lyra/../../etc/passwd.html"
    const { kv, writes } = recordingKv()
    const res = await onRequestPost(
      visibilityCtx(batchRequest([bad, PAGE], "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      visibility: "public",
      ok: [PAGE],
      failed: [{ slug: bad, error: "invalid_slug" }],
    })
    expect(writes).toEqual([`vis:${PAGE}`, `share:${PAGE}`])
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("public")
  })

  it("rejects 101 identifiers before any KV write", async () => {
    installJwksFetch([keys.publicJwk])
    const slugs = Array.from({ length: 101 }, (_, i) => `lyra/batch-${i}.html`)
    const { kv, writes } = recordingKv()
    const res = await onRequestPost(
      visibilityCtx(batchRequest(slugs, "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(400)
    await expect(res.json()).resolves.toEqual({ error: "too_many" })
    expect(writes).toEqual([])
  })

  it("accepts exactly 100 identifiers", async () => {
    installJwksFetch([keys.publicJwk])
    const slugs = Array.from({ length: 100 }, (_, i) => `lyra/batch-${i}.html`)
    const { kv, writes } = recordingKv()
    const res = await onRequestPost(
      visibilityCtx(batchRequest(slugs, "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      visibility: "public",
      ok: [],
      failed: slugs.map((slug) => ({ slug, error: "not_found" })),
    })
    expect(writes).toEqual([])
  })

  it("rejects an empty slugs array", async () => {
    installJwksFetch([keys.publicJwk])
    const { kv, writes } = recordingKv()
    const res = await onRequestPost(
      visibilityCtx(batchRequest([], "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(400)
    await expect(res.json()).resolves.toEqual({ error: "invalid_slugs" })
    expect(writes).toEqual([])
  })

  it("rejects a slugs array that is not all strings", async () => {
    installJwksFetch([keys.publicJwk])
    const { kv, writes } = recordingKv()
    const res = await onRequestPost(
      visibilityCtx(batchRequest([PAGE, 1], "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(400)
    await expect(res.json()).resolves.toEqual({ error: "invalid_slugs" })
    expect(writes).toEqual([])
  })

  it("mints a distinct share key per page and reuses one that already exists", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv({ [`share:${PAGE}`]: "kept-key" })
    const slugs = [PAGE, PAGE_ROADMAP, PAGE_BRIEF]
    const res = await onRequestPost(
      visibilityCtx(batchRequest(slugs, "shared"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      visibility: "shared",
      ok: slugs,
      failed: [],
    })
    const shareKeys = await Promise.all(slugs.map((slug) => kv.get(`share:${slug}`)))
    expect(shareKeys[0]).toBe("kept-key")
    expect(shareKeys[1]).toEqual(expect.any(String))
    expect(shareKeys[2]).toEqual(expect.any(String))
    expect(new Set(shareKeys).size).toBe(3)
    for (const slug of slugs) {
      await expect(kv.get(`vis:${slug}`)).resolves.toBe("shared")
    }
  })

  it("revokes share keys when a lot goes private", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv({
      [`vis:${PAGE}`]: "shared",
      [`share:${PAGE}`]: "old-key",
      [`vis:${PAGE_ROADMAP}`]: "public",
    })
    const res = await onRequestPost(
      visibilityCtx(batchRequest([PAGE, PAGE_ROADMAP], "private"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      visibility: "private",
      ok: [PAGE, PAGE_ROADMAP],
      failed: [],
    })
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("private")
    await expect(kv.get(`share:${PAGE}`)).resolves.toBeNull()
    await expect(kv.get(`vis:${PAGE_ROADMAP}`)).resolves.toBe("private")
  })

  it("returns 401 and writes nothing when the lot has no team JWT", async () => {
    const { kv, writes } = recordingKv({ [`vis:${PAGE}`]: "public" })
    const res = await onRequestPost(
      visibilityCtx(batchRequest([PAGE, PAGE_ROADMAP], "private", false), teamEnv(kv)),
    )
    expect(res.status).toBe(401)
    await expect(res.json()).resolves.toEqual({ error: "unauthorized" })
    expect(writes).toEqual([])
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("public")
  })

  it("rejects an invalid visibility before any write", async () => {
    installJwksFetch([keys.publicJwk])
    const { kv, writes } = recordingKv()
    const res = await onRequestPost(
      visibilityCtx(batchRequest([PAGE], "nope"), teamEnv(kv)),
    )
    expect(res.status).toBe(400)
    await expect(res.json()).resolves.toEqual({ error: "invalid_visibility" })
    expect(writes).toEqual([])
  })

  it("fails closed when the manifest cannot be read", async () => {
    installJwksFetch([keys.publicJwk])
    const unreadable = [
      new Response("nope", { status: 500 }),
      new Response("not-json", { status: 200 }),
      new Response(JSON.stringify({ items: [] }), { status: 200 }),
    ]
    for (const manifest of unreadable) {
      const { kv, writes } = recordingKv()
      const env = teamEnv(kv)
      vi.mocked(env.ASSETS.fetch).mockResolvedValue(manifest)
      const res = await onRequestPost(
        visibilityCtx(batchRequest([PAGE], "public"), env),
      )
      expect(res.status).toBe(500)
      await expect(res.json()).resolves.toEqual({ error: "manifest_unavailable" })
      expect(writes).toEqual([])
    }
    const { kv, writes } = recordingKv()
    const env = teamEnv(kv)
    vi.mocked(env.ASSETS.fetch).mockRejectedValue(new Error("assets down"))
    const res = await onRequestPost(
      visibilityCtx(batchRequest([PAGE], "public"), env),
    )
    expect(res.status).toBe(500)
    await expect(res.json()).resolves.toEqual({ error: "manifest_unavailable" })
    expect(writes).toEqual([])
  })

  it("writes the page that falls in the next chunk", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv()
    const res = await onRequestPost(
      visibilityCtx(batchRequest(CHUNK_TAIL, "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      visibility: "public",
      ok: CHUNK_TAIL,
      failed: [],
    })
    await expect(kv.get(`vis:${CHUNK_TAIL[0]}`)).resolves.toBe("public")
    await expect(kv.get(`vis:${CHUNK_TAIL[10]}`)).resolves.toBe("public")
  })

  it("records a write failure without dropping the rest of the lot", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = failingKvAfter({}, `vis:${PAGE_ROADMAP}`)
    const res = await onRequestPost(
      visibilityCtx(batchRequest([PAGE, PAGE_ROADMAP, PAGE_BRIEF], "public"), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({
      visibility: "public",
      ok: [PAGE, PAGE_BRIEF],
      failed: [{ slug: PAGE_ROADMAP, error: "write_failed" }],
    })
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("public")
    await expect(kv.get(`vis:${PAGE_ROADMAP}`)).resolves.toBeNull()
    await expect(kv.get(`vis:${PAGE_BRIEF}`)).resolves.toBe("public")
  })
})
