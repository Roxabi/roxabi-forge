import { webcrypto } from "node:crypto"
import { readFile } from "node:fs/promises"
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest"

const route = `/${"a".repeat(64)}`
const internal = `/${"b".repeat(64)}.json`
const key = "synthetic-recovery-key"
const deadline = 2_000_000_000_000
const origin = "https://preview.example.pages.dev"

type Worker = { fetch(request: Request, env: { ASSETS: { fetch: (request: Request) => Promise<Response> } }): Promise<Response> }
let worker: Worker

beforeAll(async () => {
  const template = await readFile(new URL("../scripts/g1b-gate-worker.template.js", import.meta.url), "utf8")
  const hash = Buffer.from(await webcrypto.subtle.digest("SHA-256", new TextEncoder().encode(key))).toString("hex")
  const rendered = template
    .replace("__G1B_ROUTE__", route)
    .replace("__G1B_INTERNAL__", internal)
    .replace("__G1B_TOKEN_SHA256__", hash)
    .replace("__G1B_NOT_AFTER_MS__", String(deadline))
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(rendered).toString("base64")}`
  // The module is generated from runtime test values, so a static import cannot load it.
  worker = (await import(/* @vite-ignore */ moduleUrl)).default as Worker
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function setup(asset: (request: Request) => Promise<Response> = async () => new Response("private bytes")) {
  vi.stubGlobal("crypto", webcrypto)
  vi.spyOn(Date, "now").mockReturnValue(deadline)
  const fetch = vi.fn(asset)
  return { fetch, env: { ASSETS: { fetch } } }
}

function request(path = route, options: RequestInit = {}, host = origin) {
  return new Request(`${host}${path}`, options)
}

async function expectDenied(response: Response) {
  expect(response.status).toBe(404)
  expect(await response.text()).toBe("")
  expect(response.headers.get("cache-control")).toBe("no-store")
  expect(response.headers.get("x-recovery-gate")).toBe("deny")
}

describe("recovery gate", () => {
  it("serves only the body with fixed headers via an internal manual GET", async () => {
    const bytes = new Uint8Array([0, 255, 1, 42])
    const ctx = setup(async () => new Response(bytes, { headers: {
      "content-type": "text/html", "content-encoding": "gzip", location: "https://leak.example/",
      "x-upstream-secret": "do-not-forward", "set-cookie": "secret=1",
    } }))
    const response = await worker.fetch(request(route, { headers: { "x-recovery-key": key, "accept-encoding": "gzip" } }), ctx.env)
    expect(response.status).toBe(200)
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(bytes)
    expect(Object.fromEntries(response.headers)).toEqual({
      "cache-control": "no-store, private",
      "content-type": "application/octet-stream",
      "x-robots-tag": "noindex",
    })
    expect(ctx.fetch).toHaveBeenCalledTimes(1)
    const forwarded = ctx.fetch.mock.calls[0][0]
    expect(forwarded.url).toBe(`${origin}${internal}`)
    expect(forwarded.method).toBe("GET")
    expect(forwarded.redirect).toBe("manual")
    expect([...forwarded.headers]).toEqual([])
  })

  it.each([
    ["missing key", route, "GET", undefined],
    ["wrong key", route, "GET", "wrong"],
    ["similar key", route, "GET", `${key}x`],
    ["internal path", internal, "GET", key],
    ["different path", "/", "GET", key],
    ["trailing slash", `${route}/`, "GET", key],
    ["query", `${route}?x=1`, "GET", key],
    ["HEAD", route, "HEAD", key],
    ["same-length wrong key", route, "GET", `${key.slice(0, -1)}X`],
    ["POST", route, "POST", key],
  ])("denies %s without calling assets", async (_name, path, method, suppliedKey) => {
    const ctx = setup()
    const headers = suppliedKey === undefined ? {} : { "x-recovery-key": suppliedKey }
    const response = await worker.fetch(request(path, { method, headers }), ctx.env)
    await expectDenied(response)
    expect(ctx.fetch).not.toHaveBeenCalled()
  })

  it("applies the same gate on another host", async () => {
    const ctx = setup()
    const host = "https://alias.example.pages.dev"
    await expectDenied(await worker.fetch(request(internal, {}, host), ctx.env))
    const response = await worker.fetch(request(route, { headers: { "x-recovery-key": key } }, host), ctx.env)
    expect(response.status).toBe(200)
    expect(ctx.fetch.mock.calls[0][0].url).toBe(`${host}${internal}`)
  })

  it("accepts the deadline instant and rejects requests after it", async () => {
    const ctx = setup()
    const authorized = () => request(route, { headers: { "x-recovery-key": key } })
    expect((await worker.fetch(authorized(), ctx.env)).status).toBe(200)
    vi.spyOn(Date, "now").mockReturnValue(deadline + 1)
    await expectDenied(await worker.fetch(authorized(), ctx.env))
    expect(ctx.fetch).toHaveBeenCalledTimes(1)
  })

  it("denies access if hashing fails", async () => {
    const ctx = setup()
    vi.stubGlobal("crypto", { subtle: { digest: async () => { throw new Error("unavailable") } } })
    const response = await worker.fetch(request(route, { headers: { "x-recovery-key": key } }), ctx.env)
    await expectDenied(response)
    expect(ctx.fetch).not.toHaveBeenCalled()
  })

  it.each([301, 302, 304, 403, 404, 500])("converts asset status %i to an empty 502 without upstream headers", async status => {
    const ctx = setup(async () => new Response(status === 304 ? null : "upstream body", {
      status, headers: { location: "https://leak.example/", "x-secret": "secret", "x-recovery-gate": "deny" },
    }))
    const response = await worker.fetch(request(route, { headers: { "x-recovery-key": key } }), ctx.env)
    expect(response.status).toBe(502)
    expect(await response.text()).toBe("")
    expect(Object.fromEntries(response.headers)).toEqual({ "cache-control": "no-store", "x-asset-status": String(status) })
  })

  it("returns an empty 502 without exception details when assets throws", async () => {
    const ctx = setup(async () => { throw new Error("private upstream details") })
    const response = await worker.fetch(request(route, { headers: { "x-recovery-key": key } }), ctx.env)
    expect(response.status).toBe(502)
    expect(await response.text()).toBe("")
    expect(Object.fromEntries(response.headers)).toEqual({ "cache-control": "no-store" })
  })
})
