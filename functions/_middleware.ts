/**
 * ACL + pages.dev lock.
 *
 * forge.roxabi.dev (after Access Bypass on / and /a):
 *   /                    catalogue shell (no private titles in HTML)
 *   /api/catalogue       public OK (filtered)
 *   /a/<slug>/*          vis KV: public | shared | private  (+ JWT cookie)
 *   /s/*                 KV key + vis:shared (Function)
 *   /manifest.json       never to clients (worker reads via ASSETS)
 *
 * Fail-closed: missing/unknown vis = private (no share-key inference).
 * pages.dev: 403 on all paths (including /s) — production custom domain only.
 */
import {
  type ForgeEnv,
  extractSlugFromAPath,
  getVisibility,
  isTeamRequest,
  timingSafeEqualStr,
} from "./_lib/access"

const SHARE_PREFIX = "/s/"

function isPagesDev(host: string): boolean {
  return host === "pages.dev" || host.endsWith(".pages.dev")
}

function plain404(): Response {
  return new Response("Not found", {
    status: 404,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
      "x-robots-tag": "noindex, nofollow",
    },
  })
}

/**
 * Same-origin path to return to after login, or "/".
 *
 * Only a single-slash absolute path is accepted: "//evil.tld" is a
 * protocol-relative URL a browser resolves to another origin, and an absolute
 * URL would turn the login page into an open redirect.
 */
function safeNext(raw: string | null): string {
  if (!raw) return "/"
  if (!raw.startsWith("/") || raw.startsWith("//")) return "/"
  if (raw.includes("\\") || raw.includes("..")) return "/"
  return raw
}

function loginRedirect(next?: string): Response {
  const target = safeNext(next ?? null)
  const location = target === "/" ? "/login" : `/login?next=${encodeURIComponent(target)}`
  return new Response(null, {
    status: 302,
    headers: {
      location,
      "cache-control": "no-store",
    },
  })
}

function withAcl(res: Response): Response {
  const headers = new Headers(res.headers)
  headers.set("x-forge-acl", "vis-v4")
  headers.set("cache-control", "no-store")
  return new Response(res.body, { status: res.status, headers })
}
function isPublicShell(pathname: string): boolean {
  return (
    pathname === "/" ||
    pathname === "/index.html" ||
    pathname === "/login" ||
    pathname === "/login.html" ||
    pathname === "/robots.txt" ||
    pathname === "/favicon.ico" ||
    pathname === "/favicon.svg" ||
    pathname === "/favicon-32.png" ||
    pathname === "/apple-touch-icon.png"
  )
}
const SHARE_BAR_START = "<!-- forge-share-bar -->"
const CORE_PATHS: Record<string, true> = {
  "/_shared/hero-base.css": true,
  "/_shared/hero-base.js": true,
  "/_shared/gallery-base.css": true,
  "/_shared/gallery-base.js": true,
  "/_shared/fgraph-base.css": true,
  "/_shared/explainer-base.css": true,
}


/**
 * Page id for a request path, or null when the path is not a page.
 *
 * Both URL shapes map to the same page: Cloudflare Pages answers
 * `/lyra/visuals/architecture.html` with a 308 to the extensionless
 * `/lyra/visuals/architecture`, so a rule that only knows the `.html` form
 * hands the visitor a redirect and then 404s the target it just sent them to.
 * Identity stays the stored path — the `.html` id — whichever form was asked.
 */
function treePageId(path: string): string | null {
  if (path.includes("..") || path.endsWith("/")) return null
  if (isPublicShell(path)) return null
  if (path.startsWith("/api/") || path.startsWith("/s/") || path.startsWith("/a/")) return null
  if (path.endsWith(".html")) {
    return /^\/[A-Za-z0-9._/-]+\.html$/.test(path) ? path.slice(1) : null
  }
  // Extensionless: no dot in the last segment, so an asset like `app.css`
  // never gets mistaken for a page.
  const last = path.slice(path.lastIndexOf("/") + 1)
  if (!last || last.includes(".")) return null
  return /^\/[A-Za-z0-9._/-]+$/.test(path) ? `${path.slice(1)}.html` : null
}


async function ensureShareBar(res: Response, id: string): Promise<Response> {
  const html = await res.text()
  if (html.includes(SHARE_BAR_START)) {
    return new Response(html, { status: res.status, headers: res.headers })
  }
  // `slug` is the key share-bar.js reads; emitting `page` here would leave the
  // bar silently unconfigured on any page the publish did not inject.
  const snippet = `\n${SHARE_BAR_START}\n<script>window.__FORGE_SHARE__=${JSON.stringify({ slug: id })};</script>\n<!-- /forge-share-bar -->\n`
  const body = html.includes("</body>") ? html.replace("</body>", `${snippet}</body>`) : html + snippet
  const headers = new Headers(res.headers)
  headers.set("content-type", "text/html; charset=utf-8")
  return new Response(body, { status: res.status, headers })
}
function stripShareBar(html: string): string {
  return html.replace(/\n?<!-- forge-share-bar -->[\s\S]*?<!-- \/forge-share-bar -->\n?/g, "")
}

async function grantedPage(request: Request, env: ForgeEnv): Promise<string | null> {
  const header = request.headers.get("cookie") || ""
  const match = header.match(/(?:^|;\s*)forge_share=([^;]+)/)
  if (!match) return null
  let decoded = ""
  try {
    decoded = decodeURIComponent(match[1])
  } catch {
    return null
  }
  const cut = decoded.lastIndexOf("|")
  if (cut < 1) return null
  const page = decoded.slice(0, cut)
  const key = decoded.slice(cut + 1)
  if (!page.endsWith(".html") || page.includes("..")) return null
  const vis = await getVisibility(env.SHARES, page)
  if (vis !== "shared") return null
  const stored = await env.SHARES.get(`share:${page}`)
  if (!stored || !timingSafeEqualStr(stored, key)) return null
  return page
}

async function pageReferences(env: ForgeEnv, request: Request, page: string, assetPath: string): Promise<boolean> {
  const name = assetPath.split("/").pop() || ""
  if (!name || name.includes("..")) return false
  const assetUrl = new URL(`/${page}`, request.url)
  const res = await env.ASSETS.fetch(assetUrl.toString())
  if (!res.ok) return false
  return (await res.text()).includes(name)
}

/**
 * asset-owners.json: {asset path: pages that load it}, written by the publish.
 *
 * Cached against the ASSETS binding, which lives as long as the isolate. The
 * map ships inside the deployment, so a new publish is a new bundle with its
 * own binding — the cache can never describe another deployment's tree.
 */
const ASSET_OWNERS = new WeakMap<object, Record<string, string[]>>()

async function assetOwners(env: ForgeEnv, request: Request): Promise<Record<string, string[]>> {
  const key = env.ASSETS as unknown as object
  const cached = ASSET_OWNERS.get(key)
  if (cached) return cached
  let map: Record<string, string[]> = {}
  try {
    const res = await env.ASSETS.fetch(new URL("/asset-owners.json", request.url).toString())
    if (res?.ok) {
      const parsed = (await res.json()) as Record<string, string[]>
      if (parsed && typeof parsed === "object") map = parsed
    }
  } catch {
    // No map, no grant: an unreadable index closes assets rather than opening them.
    map = {}
  }
  ASSET_OWNERS.set(key, map)
  return map
}

async function hasPublicOwner(env: ForgeEnv, request: Request, path: string): Promise<boolean> {
  const asset = path.replace(/^\//, "")
  if (!asset || asset.includes("..")) return false
  const owners = (await assetOwners(env, request))[asset]
  if (!Array.isArray(owners)) return false
  for (const page of owners) {
    if (typeof page !== "string") continue
    if ((await getVisibility(env.SHARES, page)) === "public") return true
  }
  return false
}

/**
 * Owners of a page id publish recorded as a fragment, or null if it is not one.
 *
 * Publish is the only writer of asset-owners.json. An `.html` key is, by
 * construction, a fragment — HTML whose text has no opening `<html` tag —
 * and never a real page. A page linked by `href` from a public page is
 * therefore never a key, so serving a key cannot bypass that page's own ACL.
 * That discriminant is what makes opening the key as a sub-resource safe.
 */
async function fragmentOwners(
  env: ForgeEnv,
  request: Request,
  pageId: string,
): Promise<string[] | null> {
  if (!pageId.endsWith(".html") || pageId.includes("..")) return null
  const owners = (await assetOwners(env, request))[pageId]
  if (!Array.isArray(owners)) return null
  return owners
}



export const onRequest: PagesFunction<ForgeEnv> = async (context) => {
  const url = new URL(context.request.url)
  const host = url.hostname
  const path = url.pathname

  if (isPagesDev(host)) {
    return new Response(
      `Forbidden — use the production custom domain. This pages.dev origin does not serve forge content (including share links).`,
      {
        status: 403,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "no-store",
          "x-forge-origin-policy": "pages-dev-blocked",
          "x-robots-tag": "noindex, nofollow",
        },
      },
    )
  }

  // Full artefact index + asset ownership map — worker-only (ASSETS.fetch
  // bypasses this middleware, so the edge still reads them).
  if (
    path === "/manifest.json" ||
    path === "/asset-owners.json" ||
    path.startsWith("/registry/")
  ) {
    return plain404()
  }

  if (path.startsWith("/api/") || path.startsWith(SHARE_PREFIX) || path === "/s") {
    return context.next()
  }


  if (isPublicShell(path)) {
    // /login is the door. Three states, and only one of them shows the page:
    //   - team JWT already present → straight back to the page they wanted;
    //   - Access wired (CF_ACCESS_TEAM_DOMAIN) → hand over to Cloudflare's
    //     login endpoint, which is the only thing that can mint the JWT;
    //   - Access not wired → serve the page, which says so. Bouncing anywhere
    //     else here is what made this an infinite loop.
    if (path === "/login" || path === "/login.html") {
      const next = safeNext(url.searchParams.get("next"))
      if (await isTeamRequest(context.request, context.env)) {
        return new Response(null, {
          status: 302,
          headers: { location: next, "cache-control": "no-store" },
        })
      }
      const team = (context.env.CF_ACCESS_TEAM_DOMAIN || "").trim()
      if (team) {
        const teamHost = team.replace(/^https?:\/\//, "").replace(/\/+$/, "")
        const back = new URL(next, url.origin).toString()
        return new Response(null, {
          status: 302,
          headers: {
            location: `https://${teamHost}/cdn-cgi/access/login/${host}?redirect_url=${encodeURIComponent(back)}`,
            "cache-control": "no-store",
          },
        })
      }
    }
    const res = await context.next()
    return withAcl(res)
  }
  if (CORE_PATHS[path]) {
    return withAcl(await context.next())
  }

  const pageId = treePageId(path)
  if (pageId) {
    // Sub-resource of the pages that load it, not a page of its own. Its vis:
    // record is irrelevant — a private fragment of a public page is open — and
    // page ACL would 302 to /login, which the parent's fetch() follows and
    // breaks the tab. No share bar: this body is not a document. treePageId
    // already folds both URL forms onto this id.
    const owners = await fragmentOwners(context.env, context.request, pageId)
    if (owners !== null) {
      if (await isTeamRequest(context.request, context.env)) {
        return withAcl(await context.next())
      }
      const grant = await grantedPage(context.request, context.env)
      if (grant && owners.includes(grant)) {
        return withAcl(await context.next())
      }
      if (await hasPublicOwner(context.env, context.request, `/${pageId}`)) {
        return withAcl(await context.next())
      }
      return plain404()
    }
    const id = pageId
    const grant = await grantedPage(context.request, context.env)
    if (grant === id) {
      const res = await context.next()
      const html = stripShareBar(await res.text())
      return withAcl(new Response(html, { status: res.status, headers: res.headers }))
    }
    const team = await isTeamRequest(context.request, context.env)
    if (!team) {
      const vis = await getVisibility(context.env.SHARES, id)
      if (vis !== "public") return loginRedirect(path)
    }
    const res = await context.next()
    if (team) return withAcl(await ensureShareBar(res, id))
    // A public page ships the bar in the snapshot; it is a team control, so an
    // anonymous visitor gets the page without it — same rule as a share grant.
    return withAcl(
      new Response(stripShareBar(await res.text()), { status: res.status, headers: res.headers }),
    )
  }


  if (path.startsWith("/a/") || path === "/a") {
    const slug = extractSlugFromAPath(path)
    if (!slug) return plain404()

    const team = await isTeamRequest(context.request, context.env)
    if (team) {
      const res = await context.next()
      return withAcl(res)
    }

    const vis = await getVisibility(context.env.SHARES, slug)
    if (vis === "public") {
      const res = await context.next()
      return withAcl(res)
    }
    if (vis === "shared") return plain404()
    return loginRedirect(path)
  }

  // Other static (css leftover, random files): team or 404
  if (await isTeamRequest(context.request, context.env)) {
    const res = await context.next()
    return withAcl(res)
  }
  const grant = await grantedPage(context.request, context.env)
  if (
    grant &&
    !path.endsWith(".html") &&
    (await pageReferences(context.env, context.request, grant, path))
  ) {
    return withAcl(await context.next())
  }

  // A public page has to render for an anonymous visitor, which means its own
  // css, images and preview must open too — the six core files are not enough.
  // Ownership is decided at publish time (asset-owners.json) rather than by
  // proximity: a directory neighbour is not a reference, and guessing one would
  // open files no page ever loads.
  if (!path.endsWith(".html") && (await hasPublicOwner(context.env, context.request, path))) {
    return withAcl(await context.next())
  }

  return plain404()
}
