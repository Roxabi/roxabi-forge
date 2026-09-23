import { describe, expect, it, vi } from "vitest"
import { onRequest } from "@functions/s/[[path]]"
import { mockKv } from "./helpers/kv"

function shareContext(path: string, store: Record<string, string> = {}) {
  const kv = mockKv(store)
  const assetsFetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes("/a/demo-deck/index.html")) {
      return new Response("<html>ok</html>", { status: 200 })
    }
    return new Response("missing", { status: 404 })
  })
  return {
    assetsFetch,
    request: new Request(`https://forge.example.com${path}`),
    env: { SHARES: kv, ASSETS: { fetch: assetsFetch } },
    next: vi.fn(),
    params: {},
    waitUntil: vi.fn(),
    passThroughOnException: vi.fn(),
    data: {},
  }
}

describe("/s share route", () => {
  it("serves asset when vis is shared and key matches", async () => {
    const ctx = shareContext("/s/demo-deck/good-key/", {
      "vis:demo-deck": "shared",
      "share:demo-deck": "good-key",
    })
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(200)
    expect(res.headers.get("x-forge-share")).toBe("1")
  })

  it("returns 404 for wrong share key", async () => {
    const ctx = shareContext("/s/demo-deck/wrong-key/", {
      "vis:demo-deck": "shared",
      "share:demo-deck": "good-key",
    })
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
  })

  it("returns 404 when vis is not shared", async () => {
    const ctx = shareContext("/s/demo-deck/good-key/", {
      "vis:demo-deck": "private",
      "share:demo-deck": "good-key",
    })
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
  })

  it("rejects dot-segment path traversal before ASSETS.fetch", async () => {
    const ctx = shareContext("/s/demo-deck/good-key/..%2f..%2fsecret", {
      "vis:demo-deck": "shared",
      "share:demo-deck": "good-key",
    })
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
    expect(ctx.assetsFetch).not.toHaveBeenCalled()
  })

  it("rejects encoded separators in slug segment", async () => {
    const ctx = shareContext("/s/demo%2fdeck/good-key/", {
      "vis:demo-deck": "shared",
      "share:demo-deck": "good-key",
    })
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
  })

  it("rewrites a legacy share page onto a keyed card", async () => {
    const html = `<html><head>
<meta property="og:url" content="https://forge.example.com/a/demo-deck/">
<meta property="og:image" content="https://forge.example.com/a/demo-deck/og.jpg">
<meta name="twitter:image" content="https://forge.example.com/a/demo-deck/og.jpg">
<meta name="robots" content="noindex, nofollow, noarchive">
</head><body>deck</body></html>`
    const assetsFetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith("/a/demo-deck/index.html")) {
        return new Response(html, { status: 200, headers: { "content-type": "text/html; charset=utf-8" } })
      }
      if (url.endsWith("/a/demo-deck/og.jpg")) {
        return new Response("jpeg-bytes", { status: 200, headers: { "content-type": "image/jpeg" } })
      }
      return new Response("missing", { status: 404 })
    })
    const store = { "vis:demo-deck": "shared", "share:demo-deck": "good-key" }
    const page = {
      ...shareContext("/s/demo-deck/good-key/", store),
      env: { SHARES: mockKv(store), ASSETS: { fetch: assetsFetch } },
    }
    const res = await onRequest(page as never)
    expect(res.status).toBe(200)
    const body = await res.text()
    expect(body).toContain('property="og:url" content="https://forge.example.com/s/demo-deck/good-key/"')
    expect(body).toContain('property="og:image" content="https://forge.example.com/s/demo-deck/og.jpg/good-key"')
    expect(body).not.toContain("/a/demo-deck/og.jpg")
    expect(body).not.toContain("noindex")

    const image = {
      ...shareContext("/s/demo-deck/og.jpg/good-key", store),
      env: { SHARES: mockKv(store), ASSETS: { fetch: assetsFetch } },
    }
    const card = await onRequest(image as never)
    expect(card.status).toBe(200)
    expect(card.headers.get("content-type")).toBe("image/jpeg")
    expect(await card.text()).toBe("jpeg-bytes")
  })
})
