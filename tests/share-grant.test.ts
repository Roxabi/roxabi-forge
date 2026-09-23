import { describe, expect, it, vi } from "vitest"
import { onRequest as onShare } from "@functions/s/[[path]]"
import { onRequest as onEdge } from "@functions/_middleware"
import type { ForgeEnv } from "@functions/_lib/access"
import { mockKv } from "./helpers/kv"

const PAGE = "lyra/visuals/architecture.html"
const KEY = "good-key-value"

function shareCtx(
  path: string,
  store: Record<string, string>,
  init: { headers?: HeadersInit; assets?: (input: RequestInfo | URL) => Promise<Response> } = {},
) {
  return {
    request: new Request(`https://forge.roxabi.dev${path}`, init.headers ? { headers: init.headers } : undefined),
    env: {
      SHARES: mockKv(store),
      ASSETS: { fetch: vi.fn(init.assets ?? (async () => new Response("missing", { status: 404 }))) },
    },
    next: vi.fn(),
    params: {},
    waitUntil: vi.fn(),
    passThroughOnException: vi.fn(),
    data: {},
  }
}

const BROWSER = { "sec-fetch-dest": "document" }

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
    const res = await onShare(shareCtx(`/s/${PAGE}/${KEY}`, shared, { headers: BROWSER }) as never)
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toBe("/lyra/visuals/architecture")
    expect(res.headers.get("location")).not.toContain(KEY)
    expect(res.headers.get("set-cookie")).toContain("forge_share=")
    expect(res.headers.get("set-cookie")).toContain("HttpOnly")
  })

  it("opens the page and a referenced asset, and not a sibling page", async () => {
    const exchange = await onShare(shareCtx(`/s/${PAGE}/${KEY}`, shared, { headers: BROWSER }) as never)
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

  // Pages answers `/talk/index.html` with a 308 to `/talk/`. That directory URL
  // is where the visitor lands, so the grant has to open it — and only it.
  it("opens an index.html page on the directory url Pages serves it at", async () => {
    const INDEX = "companyos-talk/index.html"
    const store = { [`vis:${INDEX}`]: "shared", [`share:${INDEX}`]: KEY }
    const exchange = await onShare(shareCtx(`/s/${INDEX}/${KEY}/`, store, { headers: BROWSER }) as never)
    expect(exchange.status).toBe(302)
    expect(exchange.headers.get("location")).toBe("/companyos-talk/")
    const cookie = (exchange.headers.get("set-cookie") || "").split(";")[0]

    const page = edgeCtx("/companyos-talk/", store, cookie)
    const pageRes = await onEdge(page as never)
    expect(pageRes.status).toBe(200)
    expect(page.next).toHaveBeenCalled()

    const other = edgeCtx("/other-talk/", store, cookie)
    const otherRes = await onEdge(other as never)
    expect(otherRes.status).not.toBe(200)
    expect(other.next).not.toHaveBeenCalled()
  })

  const SOLITO = "companyos-talk-solito/index.html"
  const DECK = `<!doctype html><html><head>
<meta name="robots" content="noindex, nofollow, noarchive">
<meta property="og:url" content="https://forge.roxabi.dev/a/companyos-talk-solito/">
<meta property="og:image" content="https://forge.roxabi.dev/a/companyos-talk-solito/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:image" content="https://forge.roxabi.dev/a/companyos-talk-solito/og.jpg">
</head><body>deck</body></html>`

  function files(map: Record<string, { body: string; type: string }>) {
    return async (input: RequestInfo | URL) => {
      const url = String(input)
      for (const [path, file] of Object.entries(map)) {
        if (url.endsWith(path)) {
          return new Response(file.body, { status: 200, headers: { "content-type": file.type } })
        }
      }
      return new Response("missing", { status: 404 })
    }
  }

  it("returns keyed og tags to a crawler and does not redirect", async () => {
    const store = { [`vis:${SOLITO}`]: "shared", [`share:${SOLITO}`]: KEY }
    const res = await onShare(
      shareCtx(`/s/${SOLITO}/${KEY}`, store, {
        assets: files({
          [`/${SOLITO}`]: { body: DECK, type: "text/html; charset=utf-8" },
          "/companyos-talk-solito/og.jpg": { body: "jpeg", type: "image/jpeg" },
        }),
      }) as never,
    )
    expect(res.status).toBe(200)
    expect(res.headers.get("location")).toBeNull()
    expect(res.headers.get("x-robots-tag")).toBeNull()
    const html = await res.text()
    expect(html).toContain(`property="og:url" content="https://forge.roxabi.dev/s/${SOLITO}/${KEY}/"`)
    expect(html).toContain(`property="og:image" content="https://forge.roxabi.dev/s/companyos-talk-solito/og.jpg/${KEY}"`)
    expect(html).toContain(`name="twitter:image" content="https://forge.roxabi.dev/s/companyos-talk-solito/og.jpg/${KEY}"`)
    expect(html).not.toContain("/a/companyos-talk-solito")
    expect(html).not.toContain("noindex")
    expect(html).not.toContain("index.og.jpg")
    expect(html).toContain('content="1200"')
    expect(html).toContain('<base href="https://forge.roxabi.dev/companyos-talk-solito/">')
  })

  it("serves the directory card without a cookie", async () => {
    const store = { [`vis:${SOLITO}`]: "shared", [`share:${SOLITO}`]: KEY }
    const fetch = vi.fn(files({
      "/companyos-talk-solito/og.jpg": { body: "jpeg-bytes", type: "image/jpeg" },
    }))
    const res = await onShare(
      shareCtx(`/s/companyos-talk-solito/og.jpg/${KEY}`, store, { assets: fetch }) as never,
    )
    expect(res.status).toBe(200)
    expect(res.headers.get("content-type")).toBe("image/jpeg")
    expect(res.headers.get("set-cookie")).toBeNull()
    expect(await res.text()).toBe("jpeg-bytes")
  })

  it("does not fetch a card for the wrong key", async () => {
    const store = { [`vis:${SOLITO}`]: "shared", [`share:${SOLITO}`]: KEY }
    const fetch = vi.fn(files({}))
    const res = await onShare(
      shareCtx("/s/companyos-talk-solito/og.jpg/not-the-key", store, { assets: fetch }) as never,
    )
    expect(res.status).toBe(404)
    expect(fetch).not.toHaveBeenCalled()
  })

  it("does not open another page's card with this key", async () => {
    const store = { [`vis:${SOLITO}`]: "shared", [`share:${SOLITO}`]: KEY }
    const fetch = vi.fn()
    const res = await onShare(
      shareCtx(`/s/other-talk/og.jpg/${KEY}`, store, { assets: fetch }) as never,
    )
    expect(res.status).toBe(404)
    expect(fetch).not.toHaveBeenCalled()
  })

  it("serves a non-index card beside the html stem", async () => {
    const fetch = vi.fn(files({
      "/lyra/visuals/architecture.og.jpg": { body: "card", type: "image/jpeg" },
    }))
    const res = await onShare(
      shareCtx(`/s/lyra/visuals/architecture.og.jpg/${KEY}`, shared, { assets: fetch }) as never,
    )
    expect(res.status).toBe(200)
    expect(await res.text()).toBe("card")
  })
})
