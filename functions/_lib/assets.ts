/** Hub artefact presence checks via ASSETS binding (fail-closed before vis mutations). */

import type { ForgeEnv } from "./access"

/**
 * Public URL path of an identifier.
 *
 * Two shapes, two locations: a tree page IS its path, served on the form Pages
 * settles on (`x.html` → `/x`, `x/index.html` → `/x/`; anything else gets a
 * 308). A legacy slug is a directory under `/a/`. Resolving both in one place
 * keeps every caller -- existence check, public URL, shortlink -- from having
 * to know which layout it is looking at.
 */
export function artefactPath(ref: string): string {
  if (ref === "index.html" || ref.endsWith("/index.html")) return `/${ref.slice(0, -"index.html".length)}`
  if (ref.endsWith(".html")) return `/${ref.slice(0, -".html".length)}`
  return `/a/${ref}/`
}

function assetUrlFor(ref: string): string {
  return ref.endsWith(".html") ? artefactPath(ref) : `/a/${ref}/index.html`
}

export async function assetExists(
  env: ForgeEnv,
  request: Request,
  slug: string,
): Promise<boolean> {
  const url = new URL(assetUrlFor(slug), request.url)
  const res = await env.ASSETS.fetch(new Request(url.toString()))
  return res.ok
}
