/**
 * A public page has to render for an anonymous visitor. The six core files are
 * not enough: the page's own css, images and preview must open too, and only
 * those — ownership comes from asset-owners.json, written at publish time.
 */
import { describe, expect, it, vi } from "vitest"
import { onRequest } from "@functions/_middleware"
import type { ForgeEnv } from "@functions/_lib/access"
import { mockKv } from "./helpers/kv"

const OWNERS = {
  "lyra/visuals/css/architecture.css": ["lyra/visuals/architecture.html"],
  "lyra/visuals/architecture.og.png": ["lyra/visuals/architecture.html"],
  "lyra/visuals/css/notes.css": ["lyra/visuals/private-notes.html"],
  "shared/logo.svg": ["lyra/visuals/private-notes.html", "lyra/visuals/architecture.html"],
}

function ctxFor(path: string, store: Record<string, string> = {}) {
  const next = vi.fn(async () => new Response("asset", { status: 200 }))
  const assets = vi.fn(async (input: string) =>
    String(input).endsWith("/asset-owners.json")
      ? new Response(JSON.stringify(OWNERS), { status: 200 })
      : new Response("missing", { status: 404 }),
  )
  const env: ForgeEnv = {
    SHARES: mockKv(store),
    ASSETS: { fetch: assets } as unknown as Fetcher,
  }
  return {
    next,
    assets,
    request: new Request(`https://forge.roxabi.dev${path}`),
    env,
    params: {},
    waitUntil: vi.fn(),
    passThroughOnException: vi.fn(),
    data: {},
  }
}

const PUBLIC_PAGE = { "vis:lyra/visuals/architecture.html": "public" }

describe("assets of a public page", () => {
  it("serves css a public page loads", async () => {
    const ctx = ctxFor("/lyra/visuals/css/architecture.css", PUBLIC_PAGE)
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(200)
    expect(ctx.next).toHaveBeenCalled()
  })

  it("serves the preview a public card shows", async () => {
    const ctx = ctxFor("/lyra/visuals/architecture.og.png", PUBLIC_PAGE)
    expect((await onRequest(ctx as never)).status).toBe(200)
  })

  it("refuses an asset only a private page loads", async () => {
    const ctx = ctxFor("/lyra/visuals/css/notes.css", PUBLIC_PAGE)
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
    expect(ctx.next).not.toHaveBeenCalled()
  })

  it("serves a shared asset as soon as one owner is public", async () => {
    const ctx = ctxFor("/shared/logo.svg", PUBLIC_PAGE)
    expect((await onRequest(ctx as never)).status).toBe(200)
  })

  it("refuses every asset when no owner is public", async () => {
    for (const path of [
      "/lyra/visuals/css/architecture.css",
      "/lyra/visuals/architecture.og.png",
      "/shared/logo.svg",
    ]) {
      const ctx = ctxFor(path)
      expect((await onRequest(ctx as never)).status).toBe(404)
    }
  })

  it("refuses a file no page references", async () => {
    const ctx = ctxFor("/lyra/visuals/secret.zip", PUBLIC_PAGE)
    expect((await onRequest(ctx as never)).status).toBe(404)
  })

  it("never serves the ownership map to a client", async () => {
    const ctx = ctxFor("/asset-owners.json", PUBLIC_PAGE)
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
    expect(ctx.next).not.toHaveBeenCalled()
  })

  it("does not open a sibling html through the asset rule", async () => {
    const ctx = ctxFor("/lyra/visuals/private-notes.html", PUBLIC_PAGE)
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain("/login")
  })
})
