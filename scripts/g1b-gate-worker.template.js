const ROUTE = "__G1B_ROUTE__"
const INTERNAL = "__G1B_INTERNAL__"
const TOKEN_SHA256 = "__G1B_TOKEN_SHA256__"
const NOT_AFTER_MS = __G1B_NOT_AFTER_MS__

function deny() {
  return new Response(null, {
    status: 404,
    headers: { "cache-control": "no-store", "x-recovery-gate": "deny" },
  })
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url)
    if (request.method !== "GET" || url.pathname !== ROUTE || url.search !== "" || Date.now() > NOT_AFTER_MS) {
      return deny()
    }

    let digest
    try {
      digest = new Uint8Array(await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(request.headers.get("x-recovery-key") || ""),
      ))
    } catch {
      return deny()
    }
    let difference = 0
    for (let i = 0; i < 32; i++) {
      difference |= digest[i] ^ parseInt(TOKEN_SHA256.slice(i * 2, i * 2 + 2), 16)
    }
    if (difference !== 0) return deny()

    try {
      const asset = await env.ASSETS.fetch(new Request(new URL(INTERNAL, url.origin), {
        method: "GET",
        redirect: "manual",
      }))
      if (asset.status !== 200) {
        return new Response(null, {
          status: 502,
          headers: { "cache-control": "no-store", "x-asset-status": String(asset.status) },
        })
      }
      return new Response(asset.body, {
        status: 200,
        headers: {
          "content-type": "application/octet-stream",
          "cache-control": "no-store, private",
          "x-robots-tag": "noindex",
        },
      })
    } catch {
      return new Response(null, { status: 502, headers: { "cache-control": "no-store" } })
    }
  },
}
