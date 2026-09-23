/**
 * /login used to be a redirect loop: `_redirects` sent /login → /login.html and
 * Cloudflare Pages sent /login.html → /login, so a private page was unreachable
 * and the browser gave up after ~20 hops. These cases pin the way out.
 */
import { describe, expect, it, vi } from "vitest"
import { onRequest } from "@functions/_middleware"
import type { ForgeEnv } from "@functions/_lib/access"
import { generateTestJwtKeys, installJwksFetch, signJwt } from "./helpers/jwt"
import { mockKv } from "./helpers/kv"

const keys = generateTestJwtKeys()
installJwksFetch([keys.publicJwk])

function ctxFor(path: string, store: Record<string, string> = {}, team = false) {
  const next = vi.fn(async () => new Response("<html><body>login</body></html>", { status: 200 }))
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

/** Same context, but the host has no Access application wired yet. */
function ctxWithoutAccess(path: string) {
  const ctx = ctxFor(path)
  ctx.env = {
    SHARES: ctx.env.SHARES,
    ASSETS: ctx.env.ASSETS,
  } as ForgeEnv
  return ctx
}

describe("login", () => {
  it("serves the login page instead of redirecting an anonymous visitor onward", async () => {
    const ctx = ctxWithoutAccess("/login?next=%2Flyra%2Fvisuals%2Farchitecture.html")
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(200)
    expect(ctx.next).toHaveBeenCalled()
  })

  it("sends a refused visitor to login carrying the page they asked for", async () => {
    const ctx = ctxFor("/lyra/visuals/architecture.html")
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toBe(
      "/login?next=%2Flyra%2Fvisuals%2Farchitecture.html",
    )
  })

  it("returns an authenticated visitor to that page", async () => {
    const ctx = ctxFor("/login?next=%2Flyra%2Fvisuals%2Farchitecture.html", {}, true)
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toBe("/lyra/visuals/architecture.html")
    expect(ctx.next).not.toHaveBeenCalled()
  })

  it("never forwards to another origin", async () => {
    for (const evil of ["//evil.tld/x", "https://evil.tld/x", "/../../etc/passwd"]) {
      const ctx = ctxFor(`/login?next=${encodeURIComponent(evil)}`, {}, true)
      const res = await onRequest(ctx as never)
      expect(res.status).toBe(302)
      expect(res.headers.get("location")).toBe("/")
    }
  })

  it("does not loop: the login target is never itself a redirect to login", async () => {
    const team = ctxFor("/login", {}, true)
    const teamRes = await onRequest(team as never)
    expect(teamRes.headers.get("location")).toBe("/")

    const anon = ctxWithoutAccess("/login")
    const anonRes = await onRequest(anon as never)
    expect(anonRes.status).toBe(200)
  })

  it("hands an unauthenticated visitor to the Cloudflare Access login", async () => {
    const ctx = ctxFor("/login?next=%2Flyra%2Fvisuals%2Fprivate-notes.html")
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toBe(
      "https://page-team.example.com/cdn-cgi/access/login/forge.roxabi.dev" +
        "?redirect_url=https%3A%2F%2Fforge.roxabi.dev%2Flyra%2Fvisuals%2Fprivate-notes.html",
    )
    expect(ctx.next).not.toHaveBeenCalled()
  })

  it("serves the page when no Access application is wired", async () => {
    const ctx = ctxWithoutAccess("/login?next=%2Flyra%2Fvisuals%2Fprivate-notes.html")
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(200)
    expect(ctx.next).toHaveBeenCalled()
  })
})
