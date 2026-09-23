/**
 * GET /api/catalogue
 * Anonymous → public pages only. Team → every page and its visibility.
 * Grouped by the first path segment. Share keys are never included.
 */
import {
  type ForgeEnv,
  type Visibility,
  isTeamRequest,
  json,
  visibilityMap,
} from "../_lib/access"

type ManifestItem = {
  f?: string
  t?: string
  d?: string
  kb?: number
  cat?: string
  cl?: string
  c?: string
  b?: string[]
  p?: boolean
  thumb?: string
}

export type CatalogueItem = {
  f: string
  t: string
  d?: string
  kb?: number
  cat?: string
  cl?: string
  c?: string
  b?: string[]
  p?: boolean
  thumb?: string
  visibility?: Visibility
}
export type CatalogueGroup = { project: string; items: CatalogueItem[] }

export async function buildCatalogue(
  env: ForgeEnv,
  request: Request,
): Promise<{ team: boolean; items: CatalogueItem[]; groups: CatalogueGroup[] }> {
  // The manifest and the visibility set are independent reads: one fetch and
  // one KV list, in parallel, instead of a read per catalogued page.
  const [team, res, visible] = await Promise.all([
    isTeamRequest(request, env),
    env.ASSETS.fetch(new URL("/manifest.json", request.url).toString()),
    visibilityMap(env.SHARES),
  ])
  let raw: ManifestItem[] = []
  if (res.ok) {
    try {
      const parsed = (await res.json()) as ManifestItem[]
      if (Array.isArray(parsed)) raw = parsed
    } catch {
      raw = []
    }
  }

  const groups = new Map<string, CatalogueItem[]>()
  for (const it of raw) {
    const page = String(it.f || "").replace(/^\//, "")
    if (!page.endsWith(".html") || page.includes("..")) continue
    const vis = visible.get(page) || "private"
    if (!team && vis !== "public") continue
    const project = page.split("/")[0] || page
    const item: CatalogueItem = {
      f: `/${page}`,
      t: it.t || page,
      d: it.d,
      kb: it.kb,
      cat: it.cat || project,
      cl: it.cl || project,
      c: it.c || "neutral",
      b: Array.isArray(it.b) ? it.b : [],
      p: Boolean(it.p),
    }
    if (it.thumb) item.thumb = it.thumb
    if (team) item.visibility = vis
    const bucket = groups.get(project) || []
    bucket.push(item)
    groups.set(project, bucket)
  }

  const groupsOut = [...groups.entries()].map(([project, items]) => ({ project, items }))
  return {
    team,
    items: groupsOut.flatMap((group) => group.items),
    groups: groupsOut,
  }
}

export function renderCatalogue(view: { groups: CatalogueGroup[] }): string {
  const sections = view.groups
    .map((group) => {
      const links = group.items
        .map((item) => `<li><a href="${item.f}">${item.t}</a></li>`)
        .join("")
      return `<section><h2>${group.project}</h2><ul>${links}</ul></section>`
    })
    .join("")
  return `<!doctype html><html><body>${sections}</body></html>`
}

export const onRequestGet: PagesFunction<ForgeEnv> = async (context) => {
  return json(await buildCatalogue(context.env, context.request))
}
