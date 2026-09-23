import { describe, expect, it, vi } from "vitest"
import { onRequest as onShare } from "@functions/s/[[path]]"
import { onRequest as onEdge } from "@functions/_middleware"
import type { ForgeEnv } from "@functions/_lib/access"
import { mockKv } from "./helpers/kv"

const PAGE = "lyra/visuals/architecture.html"
const KEY = "good-key-value"

function shareCtx(path: string, store: Record<string, string>) {
  return {
    request: new Request(`https://forge.roxabi.dev${path}`),
    env: { SHARES: mockKv(store), ASSETS: { fetch: vi.fn() } },
    next: vi.fn(),
    params: {},
    waitUntil: vi.fn(),
    passThroughOnException: vi.fn(),
    data: {},
  }
}

function edgeCtx(path: string, store: Record<string, string>, cookie = "", html = "<html><body>page</body></html>") {
  const next = vi.fn(async () => new Response(html, { status: 200 }))
  const assetsFetch = vi.fn(async () => new Response('<html><img src="shot.png"></html>', { status: 200 }))
  const headers = new Headers()
  if (cookie) headers.set("cookie", cookie)
  const env: ForgeEnv = {
    SHARES: mockKv(store),
    ASSETS: { fetch: assetsFetch } as unknown as Fetcher,
  }
  return {
    next,
    request: new Request(`https://forge.roxabi.dev${path}`, { headers }),
    env,
    params: {},
    waitUntil: vi.fn(),
    passThroughOnException: vi.fn(),
    data: {},
  }
}

const shared = {
  [`vis:${PAGE}`]: "shared",
  [`share:${PAGE}`]: KEY,
}

describe("page share grant", () => {
  it("sets a cookie and redirects to the real path without the key", async () => {
    const res = await onShare(shareCtx(`/s/${PAGE}/${KEY}`, shared) as never)
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toBe(`/${PAGE}`)
    expect(res.headers.get("location")).not.toContain(KEY)
    expect(res.headers.get("set-cookie")).toContain("forge_share=")
    expect(res.headers.get("set-cookie")).toContain("HttpOnly")
  })

  it("opens the page and a referenced asset, and not a sibling page", async () => {
    const exchange = await onShare(shareCtx(`/s/${PAGE}/${KEY}`, shared) as never)
    const cookie = (exchange.headers.get("set-cookie") || "").split(";")[0]
    const page = edgeCtx(`/${PAGE}`, shared, cookie, "<html><!-- forge-share-bar -->bar<!-- /forge-share-bar --><body>page</body></html>")
    const pageRes = await onEdge(page as never)
    expect(pageRes.status).toBe(200)
    expect(await pageRes.text()).not.toContain("forge-share-bar")

    const asset = edgeCtx("/lyra/visuals/shot.png", shared, cookie)
    const assetRes = await onEdge(asset as never)
    expect(assetRes.status).toBe(200)
    expect(asset.next).toHaveBeenCalled()

    const sibling = edgeCtx("/lyra/visuals/other.html", shared, cookie)
    const siblingRes = await onEdge(sibling as never)
    expect(siblingRes.status).not.toBe(200)
    expect(sibling.next).not.toHaveBeenCalled()
  })

  it("sets no cookie for an unknown, revoked, or orphan key", async () => {
    const unknown = await onShare(shareCtx(`/s/${PAGE}/not-the-key`, shared) as never)
    expect(unknown.status).toBe(404)
    expect(unknown.headers.get("set-cookie")).toBeNull()

    const revoked = await onShare(
      shareCtx(`/s/${PAGE}/${KEY}`, { [`vis:${PAGE}`]: "private", [`share:${PAGE}`]: KEY }) as never,
    )
    expect(revoked.status).toBe(404)
    expect(revoked.headers.get("set-cookie")).toBeNull()

    const orphan = await onShare(shareCtx(`/s/${PAGE}/${KEY}`, { [`share:${PAGE}`]: KEY }) as never)
    expect(orphan.status).toBe(404)
    expect(orphan.headers.get("set-cookie")).toBeNull()
  })
})
