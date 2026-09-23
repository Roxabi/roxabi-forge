/**
 * Serve-time unfurl for a share link. The key stays in KV.
 *
 * A browser navigation still lands on the pretty URL. Crawlers do not keep
 * the cookie and do not send Sec-Fetch-Dest, so they must get 200 HTML whose
 * og:url and og:image already carry the key. Publish-time tags stay on /a/.
 */

import { PAGE_RE, SLUG_RE } from "./access"
import { artefactPath } from "./assets"
import { isSafeAssetSegment, rawUrlPathHasEncodedSeparators, SHARE_KEY_RE } from "./share-path"

const CARD_EXTS = ["jpg", "jpeg", "png"] as const
const DIR_CARD = /^og\.(?:jpe?g|png)$/
const STEM_CARD = /^(.+)\.og\.(?:jpe?g|png)$/

export type KeyedTail = { identity: string; key: string }
export type CardHit = { page: string; assetPath: string }
export type CardTarget = { identity: string; assetPath: string }

export function isBrowserNavigation(request: Request): boolean {
  return request.headers.get("sec-fetch-dest") === "document"
}

/** Key is the last segment. Identity may contain slashes. */
export function parseKeyedTail(pathname: string, rawUrl: string): KeyedTail | null {
  if (rawUrlPathHasEncodedSeparators(rawUrl)) return null
  if (!pathname.startsWith("/s/")) return null
  const parts = pathname.replace(/^\/s\/?/, "").split("/").filter(Boolean)
  if (parts.length < 2) return null
  const key = parts[parts.length - 1]
  if (!SHARE_KEY_RE.test(key)) return null
  const identity = parts.slice(0, -1).join("/")
  if (!identity || identity.includes("..")) return null
  if (identity.split("/").some((segment) => !isSafeAssetSegment(segment))) return null
  return { identity, key }
}

/**
 * Page that owns a keyed card, and the ASSETS path of that file.
 *
 * `talk/og.jpg` is the card beside an index page (the live tree layout).
 * `talk/architecture.og.jpg` is the card beside `architecture.html`.
 * A single-segment `slug/og.jpg` may also be the legacy `/a/<slug>/og.jpg`.
 */
export function pagesForCard(asset: string): CardHit[] {
  if (!asset || asset.includes("..")) return []
  if (asset.split("/").some((segment) => !isSafeAssetSegment(segment))) return []
  const file = asset.slice(asset.lastIndexOf("/") + 1)
  const dir = asset.includes("/") ? asset.slice(0, asset.lastIndexOf("/")) : ""
  const hits: CardHit[] = []

  if (DIR_CARD.test(file)) {
    const treePage = dir ? `${dir}/index.html` : "index.html"
    if (PAGE_RE.test(treePage)) hits.push({ page: treePage, assetPath: `/${asset}` })
    if (dir && !dir.includes("/") && SLUG_RE.test(dir)) {
      hits.push({ page: dir, assetPath: `/a/${dir}/${file}` })
    }
    return hits
  }

  const stem = file.match(STEM_CARD)
  if (!stem) return []
  const page = dir ? `${dir}/${stem[1]}.html` : `${stem[1]}.html`
  if (PAGE_RE.test(page)) hits.push({ page, assetPath: `/${asset}` })
  return hits
}

/** Card files to probe, first hit wins. Index pages prefer `<dir>/og.jpg`. */
export function cardTargets(page: string): CardTarget[] {
  if (page === "index.html" || page.endsWith("/index.html")) {
    const dir = page === "index.html" ? "" : page.slice(0, -"index.html".length).replace(/\/$/, "")
    const names = [
      ...CARD_EXTS.map((ext) => `og.${ext}`),
      ...CARD_EXTS.map((ext) => `index.og.${ext}`),
    ]
    return names.map((name) => ({
      identity: dir ? `${dir}/${name}` : name,
      assetPath: dir ? `/${dir}/${name}` : `/${name}`,
    }))
  }
  if (page.endsWith(".html") && PAGE_RE.test(page)) {
    const stem = page.slice(0, -".html".length)
    return CARD_EXTS.map((ext) => ({
      identity: `${stem}.og.${ext}`,
      assetPath: `/${stem}.og.${ext}`,
    }))
  }
  if (SLUG_RE.test(page)) {
    return CARD_EXTS.map((ext) => ({
      identity: `${page}/og.${ext}`,
      assetPath: `/a/${page}/og.${ext}`,
    }))
  }
  return []
}

export function shareDocUrl(origin: string, page: string, key: string): string {
  return `${origin}/s/${page}/${key}/`
}

export function shareCardUrl(origin: string, identity: string, key: string): string {
  return `${origin}/s/${identity}/${key}`
}

/** Directory the deck's relative assets resolve against. */
export function assetBase(origin: string, page: string): string {
  if (page.endsWith(".html")) {
    const pretty = artefactPath(page)
    if (pretty.endsWith("/")) return `${origin}${pretty}`
    return `${origin}${pretty.slice(0, pretty.lastIndexOf("/") + 1)}`
  }
  return `${origin}${artefactPath(page)}`
}

function escapeAttr(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;")
}

function metaPattern(key: string): RegExp {
  return new RegExp(`<meta\\b[^>]*\\b(?:property|name)=["']${key}["'][^>]*>`, "gi")
}

function setMeta(html: string, attr: "property" | "name", key: string, content: string): string {
  const tag = `<meta ${attr}="${key}" content="${escapeAttr(content)}">`
  if (metaPattern(key).test(html)) return html.replace(metaPattern(key), () => tag)
  if (/<\/head>/i.test(html)) return html.replace(/<\/head>/i, `${tag}\n</head>`)
  return `${tag}\n${html}`
}

function removeMeta(html: string, key: string): string {
  return html.replace(metaPattern(key), "")
}

/**
 * Point og:url at the keyed document and og:image at the keyed card.
 * Drops robots noindex: the key is the access control, and a noindex
 * document is what some unfurlers refuse to card.
 */
export function rewriteShareOg(
  html: string,
  docUrl: string,
  imageUrl: string | null,
  baseHref: string,
): string {
  let out = setMeta(html, "property", "og:url", docUrl)
  if (imageUrl) {
    out = setMeta(out, "property", "og:image", imageUrl)
    out = setMeta(out, "name", "twitter:image", imageUrl)
    out = setMeta(out, "name", "twitter:card", "summary_large_image")
  } else {
    out = removeMeta(out, "og:image")
    out = removeMeta(out, "twitter:image")
    out = removeMeta(out, "og:image:width")
    out = removeMeta(out, "og:image:height")
  }
  out = removeMeta(out, "og:image:url")
  out = removeMeta(out, "og:image:secure_url")
  out = removeMeta(out, "twitter:image:src")
  out = removeMeta(out, "robots")
  if (!/<base\b/i.test(out)) {
    const tag = `<base href="${escapeAttr(baseHref)}">`
    out = /<head[^>]*>/i.test(out) ? out.replace(/<head[^>]*>/i, (open) => `${open}\n${tag}`) : `${tag}\n${out}`
  }
  return out
}
