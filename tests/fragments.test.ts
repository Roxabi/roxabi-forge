/**
 * Tab bodies are fragments: HTML with no document envelope, loaded by a parent
 * via data-src. They are sub-resources of that parent. A private fragment of a
 * public page must open, and a fetch() must not be sent to /login.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { onRequest } from "@functions/_middleware"
import type { ForgeEnv } from "@functions/_lib/access"
import { generateTestJwtKeys, installJwksFetch, signJwt } from "./helpers/jwt"
import { mockKv } from "./helpers/kv"

const FRAGMENT = "diagrams/lyra-chimera/tabs/lyra-to-chimera/tab-blueprint.html"
const PARENT = "diagrams/lyra-chimera/lyra-chimera.html"
const OTHER = "lyra/visuals/other.html"
const ORPHAN = "diagrams/lyra-chimera/tabs/unused/tab-orphan.html"
const PRIVATE_PAGE = "lyra/visuals/private-notes.html"
const KEY = "good-key-value"
const FRAGMENT_HTML = "<section data-tab=\"blueprint\">lyra to chimera</section>"
const PAGE_HTML =
  "<html><body>page\n<!-- forge-share-bar -->\n<script>window.__FORGE_SHARE__={};</script>\n<!-- /forge-share-bar -->\n</body></html>"

const OWNERS = {
  [FRAGMENT]: [PARENT],
  // Publish records every fragment, orphans included: an empty list is what
  // closes it as a resource instead of letting it fall back to the page ACL.
  [ORPHAN]: [] as string[],
}

const keys = generateTestJwtKeys()

function shareCookie(page: string): string {
  return `forge_share=${encodeURIComponent(`${page}|${KEY}`)}`
}

function ctxFor(
  path: string,
  store: Record<string, string> = {},
  opts: { team?: boolean; cookie?: string; html?: string } = {},
) {
  const next = vi.fn(
    async () => new Response(opts.html ?? FRAGMENT_HTML, { status: 200 }),
  )
  const assets = vi.fn(async (input: string) =>
    String(input).endsWith("/asset-owners.json")
      ? new Response(JSON.stringify(OWNERS), { status: 200 })
      : new Response("missing", { status: 404 }),
  )
  const headers = new Headers()
  if (opts.team) {
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
  if (opts.cookie) headers.set("cookie", opts.cookie)
  const env: ForgeEnv = {
    SHARES: mockKv(store),
    ASSETS: { fetch: assets } as unknown as Fetcher,
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

describe("html fragments", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("serves a fragment whose owner is public, without a share bar", async () => {
    const ctx = ctxFor(`/${FRAGMENT}`, {
      [`vis:${PARENT}`]: "public",
      [`vis:${FRAGMENT}`]: "private",
    })
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(200)
    expect(res.headers.get("location")).toBeNull()
    const body = await res.text()
    expect(body).toContain("lyra to chimera")
    expect(body).not.toContain("forge-share-bar")
    expect(ctx.next).toHaveBeenCalled()
  })

  it("refuses a closed fragment as a resource, not a login redirect", async () => {
    const ctx = ctxFor(`/${FRAGMENT}`, {
      [`vis:${PARENT}`]: "private",
      [`vis:${FRAGMENT}`]: "private",
    })
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
    expect(res.headers.get("location") ?? "").not.toContain("/login")
    expect(ctx.next).not.toHaveBeenCalled()
  })

  it("closes an orphan fragment with 404 rather than the page ACL", async () => {
    const ctx = ctxFor(`/${ORPHAN}`, {})
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(404)
    expect(res.headers.get("location") ?? "").not.toContain("/login")
    expect(ctx.next).not.toHaveBeenCalled()
  })

  it("applies the same verdict to the extensionless form Pages redirects to", async () => {
    const bare = `/${FRAGMENT.replace(/\.html$/, "")}`
    const openStore = {
      [`vis:${PARENT}`]: "public",
      [`vis:${FRAGMENT}`]: "private",
    }
    const openHtml = await onRequest(ctxFor(`/${FRAGMENT}`, openStore) as never)
    const openBare = await onRequest(ctxFor(bare, openStore) as never)
    expect(openBare.status).toBe(openHtml.status)
    expect(openBare.status).toBe(200)
    expect(await openBare.text()).not.toContain("forge-share-bar")

    const closedStore = {
      [`vis:${PARENT}`]: "private",
      [`vis:${FRAGMENT}`]: "private",
    }
    const closedHtml = await onRequest(ctxFor(`/${FRAGMENT}`, closedStore) as never)
    const closedCtx = ctxFor(bare, closedStore)
    const closedBare = await onRequest(closedCtx as never)
    expect(closedBare.status).toBe(closedHtml.status)
    expect(closedBare.status).toBe(404)
    expect(closedBare.headers.get("location") ?? "").not.toContain("/login")
    expect(closedCtx.next).not.toHaveBeenCalled()
  })

  it("serves a private fragment to the team without injecting a share bar", async () => {
    installJwksFetch([keys.publicJwk])
    const ctx = ctxFor(
      `/${FRAGMENT}`,
      { [`vis:${FRAGMENT}`]: "private", [`vis:${PARENT}`]: "private" },
      { team: true },
    )
    const res = await onRequest(ctx as never)
    expect(res.status).toBe(200)
    const body = await res.text()
    expect(body).toContain("lyra to chimera")
    expect(body).not.toContain("forge-share-bar")
    expect(ctx.next).toHaveBeenCalled()
  })

  it("opens a fragment for a grant on its owner, not on another page", async () => {
    const owned = {
      [`vis:${PARENT}`]: "shared",
      [`share:${PARENT}`]: KEY,
      [`vis:${FRAGMENT}`]: "private",
    }
    const opened = ctxFor(`/${FRAGMENT}`, owned, { cookie: shareCookie(PARENT) })
    const openRes = await onRequest(opened as never)
    expect(openRes.status).toBe(200)
    expect(await openRes.text()).not.toContain("forge-share-bar")
    expect(opened.next).toHaveBeenCalled()

    const foreign = {
      [`vis:${OTHER}`]: "shared",
      [`share:${OTHER}`]: KEY,
      [`vis:${PARENT}`]: "private",
      [`vis:${FRAGMENT}`]: "private",
    }
    const refused = ctxFor(`/${FRAGMENT}`, foreign, { cookie: shareCookie(OTHER) })
    const refusedRes = await onRequest(refused as never)
    expect(refusedRes.status).toBe(404)
    expect(refusedRes.headers.get("location") ?? "").not.toContain("/login")
    expect(refused.next).not.toHaveBeenCalled()
  })

  it("keeps a real page on the page ACL when it is absent from the map", async () => {
    const locked = ctxFor(`/${PRIVATE_PAGE}`, {}, { html: PAGE_HTML })
    const lockedRes = await onRequest(locked as never)
    expect(lockedRes.status).toBe(302)
    expect(lockedRes.headers.get("location")).toContain("/login?next=")
    expect(locked.next).not.toHaveBeenCalled()

    const opened = ctxFor(
      `/${PARENT}`,
      { [`vis:${PARENT}`]: "public" },
      { html: PAGE_HTML },
    )
    const openedRes = await onRequest(opened as never)
    expect(openedRes.status).toBe(200)
    const body = await openedRes.text()
    expect(body).toContain("page")
    expect(body).not.toContain("forge-share-bar")
    expect(opened.next).toHaveBeenCalled()
  })
})
