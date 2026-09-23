/** Minimal in-memory KV mock for Pages Functions tests. */
export function mockKv(initial: Record<string, string> = {}): KVNamespace {
  const store = new Map(Object.entries(initial))
  const meta = new Map<string, unknown>()
  // Counted so a test can prove the catalogue stopped reading one key per page.
  const calls = { get: 0, list: 0 }

  return {
    get: async (key: string, type?: string) => {
      calls.get++
      const v = store.get(key)
      if (v === undefined) return null
      if (type === "json") return JSON.parse(v) as unknown
      if (type === "arrayBuffer") return new TextEncoder().encode(v).buffer
      if (type === "stream") {
        return new ReadableStream({
          start(c) {
            c.enqueue(new TextEncoder().encode(v))
            c.close()
          },
        })
      }
      return v
    },
    put: async (
      key: string,
      value: string | ArrayBuffer | ArrayBufferView | ReadableStream,
      options?: { metadata?: unknown },
    ) => {
      store.set(
        key,
        typeof value === "string" ? value : new TextDecoder().decode(value as ArrayBuffer),
      )
      if (options && "metadata" in options) meta.set(key, options.metadata ?? null)
    },
    delete: async (key: string) => {
      store.delete(key)
    },
    list: async (options?: { prefix?: string; cursor?: string; limit?: number }) => {
      calls.list++
      const prefix = options?.prefix || ""
      const names = [...store.keys()].filter((k) => k.startsWith(prefix)).sort()
      const start = options?.cursor ? Number(options.cursor) : 0
      const limit = options?.limit ?? 1000
      const page = names.slice(start, start + limit)
      const done = start + page.length >= names.length
      return {
        keys: page.map((name) => ({ name, metadata: meta.get(name) ?? null })),
        list_complete: done,
        ...(done ? {} : { cursor: String(start + page.length) }),
        cacheStatus: null,
      }
    },
    calls,
    getWithMetadata: async (key: string, type?: string) => {
      const v = store.get(key)
      if (v === undefined) {
        return { value: null, metadata: null, cacheStatus: null }
      }
      if (type === "json") {
        return {
          value: JSON.parse(v) as unknown,
          metadata: null,
          cacheStatus: null,
        }
      }
      return { value: v, metadata: null, cacheStatus: null }
    },
  } as unknown as KVNamespace
}

/** KV mock plus its call counters — no cast needed to read them. */
export function countingKv(initial: Record<string, string> = {}): {
  kv: KVNamespace
  calls: { get: number; list: number }
} {
  const kv = mockKv(initial)
  const calls: { get: number; list: number } = Reflect.get(kv, "calls")
  return { kv, calls }
}

export function failingKvAfter(
  initial: Record<string, string>,
  failKey: string,
): KVNamespace {
  const inner = mockKv(initial)
  return {
    ...inner,
    put: async (key, value) => {
      if (key === failKey) throw new Error(`kv_put_failed:${key}`)
      return inner.put(key, value)
    },
    delete: async (key) => {
      if (key === failKey) throw new Error(`kv_delete_failed:${key}`)
      return inner.delete(key)
    },
  }
}
