import { describe, expect, it, vi } from "vitest"
import { onRequestGet, type CatalogueGroup, type CatalogueItem } from "@functions/api/catalogue"
import { type ForgeEnv, setVisibility } from "@functions/_lib/access"
import { onRequest } from "@functions/_middleware"
import { countingKv, mockKv } from "./helpers/kv"
import { generateTestJwtKeys, installJwksFetch, signJwt } from "./helpers/jwt"

/** One named shape for the parsed payload: the tests read `.items`/`.groups`
 * off it, and `res.json()` alone would hand them `unknown`. */
type CatalogueBody = { team: boolean; items: CatalogueItem[]; groups: CatalogueGroup[] }

async function catalogueBody(res: Response): Promise<CatalogueBody> {
  return (await res.json()) as CatalogueBody
}

const MANIFEST = [
  { f: "lyra/visuals/architecture.html", t: "Lyra architecture" },
  { f: "lyra/visuals/private-notes.html", t: "Secret lyra notes" },
  { f: "metalyde/landing.html", t: "Metalyde landing" },
]

function env(): ForgeEnv {
  return {
    SHARES: mockKv({
      "vis:lyra/visuals/architecture.html": "public",
      "vis:metalyde/landing.html": "public",
      "share:lyra/visuals/private-notes.html": "super-secret-key",
    }),
    ASSETS: {
      fetch: vi.fn(async () => new Response(JSON.stringify(MANIFEST), { status: 200 })),
    } as unknown as Fetcher,
  }
}

describe("grouped catalogue", () => {
  it("serves the public landing shell instead of an empty body", async () => {
    const next = vi.fn(async () => new Response("<html><div id=\"content\"></div></html>", { status: 200 }))
    const res = await onRequest({
      request: new Request("https://forge.roxabi.dev/"),
      env: env(),
      next,
      params: {},
      waitUntil: vi.fn(),
      data: {},
    } as never)
    expect(res.status).toBe(200)
    expect(next).toHaveBeenCalled()
    expect(res.headers.get("x-forge-acl")).toBe("vis-v4")
  })

  it("hides private titles from an anonymous catalogue", async () => {
    const res = await onRequestGet({
      request: new Request("https://forge.roxabi.dev/api/catalogue"),
      env: env(),
      next: vi.fn(),
      params: {},
      waitUntil: vi.fn(),
      data: {},
    } as never)
    const body = await catalogueBody(res)
    const titles = body.items.map((item: { t: string }) => item.t)
    expect(titles).toContain("Lyra architecture")
    expect(titles).toContain("Metalyde landing")
    expect(titles).not.toContain("Secret lyra notes")
    expect(JSON.stringify(body)).not.toContain("super-secret-key")
  })

  it("lists every page and its visibility for the team, never a share key", async () => {
    const keys = generateTestJwtKeys()
    installJwksFetch([keys.publicJwk])
    const now = Math.floor(Date.now() / 1000)
    const token = signJwt(keys.privateKeyPem, {
      exp: now + 3600,
      iss: "https://page-team.example.com",
      aud: "page-aud",
    })
    const request = new Request("https://forge.roxabi.dev/api/catalogue", {
      headers: { "Cf-Access-Jwt-Assertion": token },
    })
    const res = await onRequestGet({
      request,
      env: {
        ...env(),
        CF_ACCESS_TEAM_DOMAIN: "page-team.example.com",
        CF_ACCESS_AUD: "page-aud",
      },
      next: vi.fn(),
      params: {},
      waitUntil: vi.fn(),
      data: {},
    } as never)
    const body = await catalogueBody(res)
    expect(JSON.stringify(body)).toContain("Secret lyra notes")
    expect(JSON.stringify(body)).toContain("private")
    expect(JSON.stringify(body)).not.toContain("super-secret-key")
    expect(body.groups.map((group: { project: string }) => group.project)).toEqual(["lyra", "metalyde"])
  })

  // A per-page KV read cost 10 to 30 seconds on a 836-page catalogue: the
  // endpoint returned 37 bytes after 800 sequential round-trips. What matters
  // is that the cost stops growing with the number of pages.
  it("reads the visibility set once, not once per page", async () => {
    const pages = Array.from({ length: 300 }, (_, i) => ({
      f: `projet-${i % 10}/page-${i}.html`,
      t: `Artefact ${i}`,
    }))
    const { kv, calls } = countingKv({
      "vis:projet-0/page-0.html": "public",
      "share:projet-1/page-1.html": "secret-key",
    })

    const res = await onRequestGet({
      request: new Request("https://forge.roxabi.dev/api/catalogue"),
      env: {
        SHARES: kv,
        ASSETS: {
          fetch: vi.fn(async () => new Response(JSON.stringify(pages), { status: 200 })),
        } as unknown as Fetcher,
      } as ForgeEnv,
      next: vi.fn(),
      params: {},
      waitUntil: vi.fn(),
      data: {},
    } as never)
    const body = await catalogueBody(res)

    expect(body.items).toHaveLength(1)
    expect(body.items[0].f).toBe("/projet-0/page-0.html")
    expect(calls.list).toBe(1)
    // One legacy key without metadata is read individually; 300 pages are not.
    expect(calls.get).toBeLessThanOrEqual(2)
  })

  it("answers from the list when visibility was written with metadata", async () => {
    const { kv, calls } = countingKv()
    await setVisibility(kv, "lyra/visuals/architecture.html", "public")
    calls.get = 0

    const res = await onRequestGet({
      request: new Request("https://forge.roxabi.dev/api/catalogue"),
      env: {
        SHARES: kv,
        ASSETS: {
          fetch: vi.fn(
            async () =>
              new Response(
                JSON.stringify([{ f: "lyra/visuals/architecture.html", t: "Lyra" }]),
                { status: 200 },
              ),
          ),
        } as unknown as Fetcher,
      } as ForgeEnv,
      next: vi.fn(),
      params: {},
      waitUntil: vi.fn(),
      data: {},
    } as never)
    const body = await catalogueBody(res)

    expect(body.items).toHaveLength(1)
    expect(calls.get).toBe(0)
  })
})
