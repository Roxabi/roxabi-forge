/**
 * GET /s/<page>.html/<key>  — browser: 302 + cookie; crawler: 200 HTML
 * GET /s/<card>/<key>       — card image, same KV key, no cookie
 * GET /s/<slug>/<key>/…     — legacy slug share (key is the second segment)
 *
 * Crawlers do not keep the share cookie. The HTML they read must already
 * name a keyed og:image, and that URL must 200 without a login.
 */
import {
  type ForgeEnv,
  getVisibility,
  isArtefactRef,
  PAGE_RE,
  timingSafeEqualStr,
} from "../_lib/access"
import { artefactPath } from "../_lib/assets"
import { parseShareRoute, SHARE_KEY_RE, shareAssetPath } from "../_lib/share-path"
import {
  assetBase,
  cardTargets,
  isBrowserNavigation,
  pagesForCard,
  parseKeyedTail,
  rewriteShareOg,
  shareCardUrl,
  shareDocUrl,
  type CardHit,
  type CardTarget,
} from "../_lib/share-unfurl"

async function plain404(): Promise<Response> {
  return new Response("Not found", {
    status: 404,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    },
  })
}

function shareCookie(page: string, key: string): string {
  return `forge_share=${encodeURIComponent(`${page}|${key}`)}; HttpOnly; Secure; SameSite=Lax; Path=/`
}

async function shareAuthorized(env: ForgeEnv, page: string, key: string): Promise<boolean> {
  if (!isArtefactRef(page) || !SHARE_KEY_RE.test(key)) return false
  if ((await getVisibility(env.SHARES, page)) !== "shared") return false
  const stored = await env.SHARES.get(`share:${page}`)
  return !!stored && timingSafeEqualStr(stored, key)
}

async function fetchAsset(env: ForgeEnv, origin: string, path: string): Promise<Response | null> {
  const res = await env.ASSETS.fetch(new URL(path, origin).toString())
  if (res.status !== 200) return null
  return res
}

async function firstCard(env: ForgeEnv, origin: string, page: string): Promise<CardTarget | null> {
  for (const target of cardTargets(page)) {
    const res = await fetchAsset(env, origin, target.assetPath)
    if (!res) continue
    const type = res.headers.get("content-type") || ""
    if (type.startsWith("image/")) return target
  }
  return null
}

function unfurlHeaders(cookie: string): Headers {
  const headers = new Headers()
  headers.set("content-type", "text/html; charset=utf-8")
  headers.set("cache-control", "no-store")
  headers.set("x-content-type-options", "nosniff")
  headers.set("x-forge-share", "1")
  headers.set("set-cookie", cookie)
  return headers
}

async function crawlerHtml(
  env: ForgeEnv,
  origin: string,
  page: string,
  key: string,
  htmlPath: string,
): Promise<Response> {
  const htmlRes = await fetchAsset(env, origin, htmlPath)
  if (!htmlRes) return plain404()
  const card = await firstCard(env, origin, page)
  const body = rewriteShareOg(
    await htmlRes.text(),
    shareDocUrl(origin, page, key),
    card ? shareCardUrl(origin, card.identity, key) : null,
    assetBase(origin, page),
  )
  return new Response(body, { status: 200, headers: unfurlHeaders(shareCookie(page, key)) })
}

function browserRedirect(page: string, key: string): Response {
  const headers = new Headers()
  headers.set("location", artefactPath(page))
  headers.set("cache-control", "no-store")
  headers.set("set-cookie", shareCookie(page, key))
  return new Response(null, { status: 302, headers })
}

async function serveCard(env: ForgeEnv, origin: string, hit: CardHit): Promise<Response> {
  const res = await fetchAsset(env, origin, hit.assetPath)
  if (!res) return plain404()
  const type = res.headers.get("content-type") || ""
  if (!type.startsWith("image/")) return plain404()
  const headers = new Headers()
  headers.set("content-type", type.split(";")[0])
  headers.set("cache-control", "no-store")
  headers.set("x-content-type-options", "nosniff")
  return new Response(res.body, { status: 200, headers })
}

export const onRequest: PagesFunction<ForgeEnv> = async (context) => {
  const request = context.request
  const url = new URL(request.url)
  const origin = url.origin
  const tail = parseKeyedTail(url.pathname, request.url)

  if (tail && tail.identity.endsWith(".html") && PAGE_RE.test(tail.identity)) {
    if (!(await shareAuthorized(context.env, tail.identity, tail.key))) return plain404()
    if (isBrowserNavigation(request)) return browserRedirect(tail.identity, tail.key)
    return crawlerHtml(context.env, origin, tail.identity, tail.key, `/${tail.identity}`)
  }

  if (tail) {
    const hits = pagesForCard(tail.identity)
    if (hits.length) {
      let hit: CardHit | null = null
      for (const candidate of hits) {
        if (await shareAuthorized(context.env, candidate.page, tail.key)) {
          hit = candidate
          break
        }
      }
      if (!hit) return plain404()
      return serveCard(context.env, origin, hit)
    }
  }

  const parsed = parseShareRoute(url, request.url)
  if (!parsed.ok) return plain404()

  const { slug, key, rest } = parsed.route
  if (!(await shareAuthorized(context.env, slug, key))) return plain404()

  const assetPath = shareAssetPath(slug, rest)
  const res = await context.env.ASSETS.fetch(new URL(assetPath, origin).toString())
  if (res.status === 404) return plain404()

  const type = res.headers.get("content-type") || ""
  if (type.includes("text/html") || assetPath.endsWith(".html")) {
    return crawlerHtml(context.env, origin, slug, key, assetPath)
  }

  const headers = new Headers(res.headers)
  headers.set("cache-control", "no-store")
  headers.set("x-robots-tag", "noindex, nofollow, noarchive")
  headers.set("x-forge-share", "1")
  headers.set("x-content-type-options", "nosniff")
  return new Response(res.body, { status: res.status, headers })
}
