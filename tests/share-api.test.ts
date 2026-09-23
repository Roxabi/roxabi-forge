import { afterEach, describe, expect, it, vi } from "vitest"
import type { ForgeEnv } from "@functions/_lib/access"
import {
  onRequestDelete,
  onRequestGet,
  onRequestPost,
} from "@functions/api/share"
import { generateTestJwtKeys, installJwksFetch, signJwt } from "./helpers/jwt"
import { mockKv } from "./helpers/kv"

const keys = generateTestJwtKeys()
const PAGE = "lyra/visuals/architecture.html"

// Shape re-parsed by functions/s/[[path]].ts. Not imported: that route is
// owned by the parallel layout change, and this API must keep emitting it.
const SHARE_EXCHANGE = /^\/s\/(.+\.html)\/([^/]+)\/?$/

function teamJwt(): string {
  const now = Math.floor(Date.now() / 1000)
  return signJwt(keys.privateKeyPem, {
    exp: now + 3600,
    iss: "https://share-team.example.com",
    aud: "share-aud",
  })
}

function teamEnv(kv: KVNamespace): ForgeEnv {
  return {
    SHARES: kv,
    ASSETS: {
      fetch: vi.fn().mockResolvedValue(new Response("", { status: 200 })),
    } as unknown as Fetcher,
    CF_ACCESS_TEAM_DOMAIN: "share-team.example.com",
    CF_ACCESS_AUD: "share-aud",
    PUBLIC_HOST: "forge.example.com",
  }
}

function shareCtx(request: Request, env: ForgeEnv) {
  return {
    request,
    env,
    params: {},
    data: {},
    functionPath: "/api/share",
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

function jsonRequest(method: "POST" | "DELETE", slug: string): Request {
  return new Request("https://forge.example.com/api/share", {
    method,
    headers: {
      "content-type": "application/json",
      origin: "https://forge.example.com",
      "Cf-Access-Jwt-Assertion": teamJwt(),
    },
    body: JSON.stringify({ slug }),
  })
}

describe("share API page paths", () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it("reports an active grant stored under the tree page key", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv({ [`share:${PAGE}`]: "existing-share-key" })
    const url = new URL("https://forge.example.com/api/share")
    url.searchParams.set("slug", PAGE)
    const res = await onRequestGet(
      shareCtx(
        new Request(url, {
          headers: { "Cf-Access-Jwt-Assertion": teamJwt() },
        }),
        teamEnv(kv),
      ),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({ slug: PAGE, active: true })
  })

  it("mints a share URL the /s exchange can re-parse", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv()
    const res = await onRequestPost(shareCtx(jsonRequest("POST", PAGE), teamEnv(kv)))
    expect(res.status).toBe(200)
    const key = await kv.get(`share:${PAGE}`)
    expect(key).toEqual(expect.any(String))
    const sharePath = `/s/${PAGE}/${key}/`
    const exchange = sharePath.match(SHARE_EXCHANGE)
    expect(exchange?.[1]).toBe(PAGE)
    expect(exchange?.[2]).toBe(key)
    await expect(res.json()).resolves.toEqual({
      slug: PAGE,
      shareUrl: `https://forge.example.com${sharePath}`,
      shortUrl: null,
      rotated: false,
    })
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("shared")
  })

  it("revokes a tree page grant", async () => {
    installJwksFetch([keys.publicJwk])
    const kv = mockKv({
      [`vis:${PAGE}`]: "shared",
      [`share:${PAGE}`]: "existing-share-key",
    })
    const res = await onRequestDelete(
      shareCtx(jsonRequest("DELETE", PAGE), teamEnv(kv)),
    )
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({ slug: PAGE, active: false })
    await expect(kv.get(`vis:${PAGE}`)).resolves.toBe("private")
    await expect(kv.get(`share:${PAGE}`)).resolves.toBeNull()
  })

  it("refuses traversal and a leading slash without writing KV", async () => {
    installJwksFetch([keys.publicJwk])
    const { kv, writes } = recordingKv({
      [`vis:${PAGE}`]: "shared",
      [`share:${PAGE}`]: "existing-share-key",
    })
    const env = teamEnv(kv)
    for (const slug of ["lyra/../../etc/passwd.html", "/lyra/x.html"]) {
      const post = await onRequestPost(shareCtx(jsonRequest("POST", slug), env))
      expect({ slug, method: "POST", status: post.status }).toEqual({
        slug,
        method: "POST",
        status: 400,
      })
      const del = await onRequestDelete(shareCtx(jsonRequest("DELETE", slug), env))
      expect({ slug, method: "DELETE", status: del.status }).toEqual({
        slug,
        method: "DELETE",
        status: 400,
      })
    }
    expect(writes).toEqual([])
  })
})
