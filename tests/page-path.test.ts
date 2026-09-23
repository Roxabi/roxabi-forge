import { describe, expect, it, vi } from "vitest"
import { onRequest } from "@functions/_middleware"
import type { ForgeEnv } from "@functions/_lib/access"
import { generateTestJwtKeys, installJwksFetch, signJwt } from "./helpers/jwt"
import { mockKv } from "./helpers/kv"

const PAGE = "/lyra/visuals/architecture.html"
const keys = generateTestJwtKeys()

function ctxFor(path: string, store: Record<string, string> = {}, team = false) {
  const next = vi.fn(async () => new Response("<html><body>page</body></html>", { status: 200 }))
  const headers = new Headers()
  if (team) {
    const now = Math.floor(Date.now() / 1000)
    headers.set(
      "Cf-Access-Jwt-Assertion",
      signJwt(keys.privateKeyPem, {
        exp: now + 3600,
        iss: "https://page-team.example.com",
        aud: "page-aud",
      }),
    )
  }
  const env: ForgeEnv = {
    SHARES: mockKv(store),
    ASSETS: { fetch: vi.fn() } as unknown as Fetcher,
    CF_ACCESS_TEAM_DOMAIN: "page-team.example.com",
    CF_ACCESS_AUD: "page-aud",
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

describe("tree page", () => {
  it("redirects a private nested page to login and does not serve it", async () => {
    const ctx = ctxFor(PAGE)
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toMatch(/^\/login(\?next=|$)/)
    expect(ctx.next).not.toHaveBeenCalled()
  })

  it("treats a missing visibility record as private", async () => {
    const ctx = ctxFor(PAGE, {})
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toMatch(/^\/login(\?next=|$)/)
  })

  it("serves the page to the team and includes the share bar", async () => {
    installJwksFetch([keys.publicJwk])
    const ctx = ctxFor(PAGE, {}, true)
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(200)
    expect(await res.text()).toContain("<!-- forge-share-bar -->")
    expect(ctx.next).toHaveBeenCalled()
  })

  it("serves a public page with no credential", async () => {
    const ctx = ctxFor(PAGE, { [`vis:${PAGE.slice(1)}`]: "public" })
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(200)
    expect(ctx.next).toHaveBeenCalled()
  })

  it("serves the technical core with no credential", async () => {
    for (const path of [
      "/_shared/hero-base.css",
      "/_shared/hero-base.js",
      "/_shared/gallery-base.css",
      "/_shared/gallery-base.js",
      "/_shared/fgraph-base.css",
      "/_shared/explainer-base.css",
    ]) {
      const ctx = ctxFor(path)
      const res = await onRequest(ctx as never)
      expect(res.status).toBe(200)
      expect(ctx.next).toHaveBeenCalled()
    }
  })

  it("refuses a non-core file under the old shared folder", async () => {
    const ctx = ctxFor("/_shared/diagrams/alphaclaw.html")
    const res = await onRequest(ctx as never)
    expect(res.status).not.toBe(200)
    expect(ctx.next).not.toHaveBeenCalled()
  })

  // Cloudflare Pages answers `/x.html` with a 308 to `/x`, so the extensionless
  // form is the URL a visitor actually lands on. It carries the same ACL.
  it("applies the page ACL to the extensionless canonical url", async () => {
    const open = ctxFor("/lyra/visuals/architecture", {
      "vis:lyra/visuals/architecture.html": "public",
    })
    const served = await onRequest(open as never)
    expect(served.status).toBe(200)
    expect(open.next).toHaveBeenCalled()

    const closed = ctxFor("/lyra/visuals/private-notes")
    const refused = await onRequest(closed as never)
    expect(refused.status).toBe(302)
    expect(refused.headers.get("location")).toMatch(/^\/login\?next=/)
    expect(closed.next).not.toHaveBeenCalled()
  })

  it("does not mistake an asset for a page", async () => {
    const ctx = ctxFor("/lyra/visuals/app.css")
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
    expect(ctx.next).not.toHaveBeenCalled()
  })

  it("never shows the team share bar to an anonymous visitor", async () => {
    const ctx = ctxFor("/lyra/visuals/architecture.html", {
      "vis:lyra/visuals/architecture.html": "public",
    })
    ctx.next = vi.fn(
      async () =>
        new Response(
          "<html><body>page\n<!-- forge-share-bar -->\n<script>window.__FORGE_SHARE__={};</script>\n<!-- /forge-share-bar -->\n</body></html>",
          { status: 200, headers: { "content-type": "text/html" } },
        ),
    )
    const res = await onRequest(ctx as never)
    const body = await res.text()
    expect(res.status).toBe(200)
    expect(body).toContain("page")
    expect(body).not.toContain("forge-share-bar")
  })

})
