// @vitest-environment happy-dom

/**
 * Tests for gallery-base.js — shared utilities for forge gallery templates.
 *
 * gallery-base.js is a plain browser script (no ESM exports). We load it
 * via readFileSync + eval() inside the happy-dom environment so all functions
 * land as globals on `globalThis`, matching the runtime execution model.
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Bootstrap: evaluate gallery-base.js into the happy-dom globalThis
// ---------------------------------------------------------------------------

const SRC_PATH = join(
  import.meta.dirname,
  '../gallery-base.js',
)

beforeAll(() => {
  const src = readFileSync(SRC_PATH, 'utf-8')
  // eslint-disable-next-line no-eval
  ;(0, eval)(src)
})

// ---------------------------------------------------------------------------
// Helpers to access globals injected by gallery-base.js
// ---------------------------------------------------------------------------

const g = globalThis as Record<string, unknown>

function getGlobal<T = unknown>(name: string): T {
  return g[name] as T
}

// ---------------------------------------------------------------------------
// escHtml
// ---------------------------------------------------------------------------

describe('escHtml', () => {
  it('returns an empty string unchanged', () => {
    // Arrange
    const fn = getGlobal<(s: string) => string>('escHtml')
    // Act + Assert
    expect(fn('')).toBe('')
  })

  it('escapes & < > " and single-quote', () => {
    // Arrange
    const fn = getGlobal<(s: string) => string>('escHtml')
    // Act
    const result = fn(`& < > " '`)
    // Assert
    expect(result).toBe('&amp; &lt; &gt; &quot; &#39;')
  })

  it('escapes a script-injection payload (regression: dim label escaping)', () => {
    // Arrange
    const fn = getGlobal<(s: string) => string>('escHtml')
    // Act
    const result = fn('<script>alert(1)</script>')
    // Assert
    expect(result).not.toContain('<script>')
    expect(result).toContain('&lt;script&gt;')
  })

  it('coerces non-string to string before escaping', () => {
    // Arrange
    const fn = getGlobal<(s: unknown) => string>('escHtml')
    // Act + Assert
    expect(fn(42 as unknown as string)).toBe('42')
  })
})

// ---------------------------------------------------------------------------
// safeClass
// ---------------------------------------------------------------------------

describe('safeClass', () => {
  it('returns the input when it matches [a-zA-Z0-9_-]+', () => {
    const fn = getGlobal<(s: string) => string>('safeClass')
    expect(fn('toast-info')).toBe('toast-info')
    expect(fn('BatchA')).toBe('BatchA')
  })

  it('returns "unknown" for input containing spaces or special chars', () => {
    const fn = getGlobal<(s: string) => string>('safeClass')
    expect(fn('bad input')).toBe('unknown')
    expect(fn('<xss>')).toBe('unknown')
    expect(fn('')).toBe('unknown')
  })
})

// ---------------------------------------------------------------------------
// applyDimFilters
// ---------------------------------------------------------------------------

describe('applyDimFilters', () => {
  const dims = {
    rarity: { label: 'Rarity', fn: (it: { rarity: string }) => it.rarity },
    stage: { label: 'Stage', fn: (it: { stage: string }) => it.stage },
  }

  const items = [
    { rarity: 'common', stage: 'baby' },
    { rarity: 'rare', stage: 'adult' },
    { rarity: 'common', stage: 'adult' },
    { rarity: 'legendary', stage: 'baby' },
  ]

  it('returns all items when all filter Sets are empty (pass-through)', () => {
    // Arrange
    const applyDimFilters = getGlobal<Function>('applyDimFilters')
    const filters = { rarity: new Set(), stage: new Set() }
    // Act
    const result = applyDimFilters(items, dims, filters)
    // Assert
    expect(result).toHaveLength(4)
  })

  it('filters items matching a single active dim', () => {
    // Arrange
    const applyDimFilters = getGlobal<Function>('applyDimFilters')
    const filters = { rarity: new Set(['common']), stage: new Set() }
    // Act
    const result = applyDimFilters(items, dims, filters)
    // Assert
    expect(result).toHaveLength(2)
    expect(result.every((i: { rarity: string }) => i.rarity === 'common')).toBe(true)
  })

  it('applies AND logic across multiple active dims', () => {
    // Arrange
    const applyDimFilters = getGlobal<Function>('applyDimFilters')
    const filters = { rarity: new Set(['common']), stage: new Set(['baby']) }
    // Act
    const result = applyDimFilters(items, dims, filters)
    // Assert
    expect(result).toHaveLength(1)
    expect(result[0]).toEqual({ rarity: 'common', stage: 'baby' })
  })

  it('returns empty array when no items match active filter', () => {
    // Arrange
    const applyDimFilters = getGlobal<Function>('applyDimFilters')
    const filters = { rarity: new Set(['mythic']), stage: new Set() }
    // Act
    const result = applyDimFilters(items, dims, filters)
    // Assert
    expect(result).toHaveLength(0)
  })

  it('stale-key regression — dims={rarity,stage} vs dims={rarity,class,level}', () => {
    // Arrange: simulate Mode A filtered on stage=baby, then Mode B with different dims
    const applyDimFilters = getGlobal<Function>('applyDimFilters')
    const modeAFilters = { rarity: new Set<string>(), stage: new Set(['baby']) }

    // After filtering in Mode A, switch to Mode B with new dims that don't have "stage"
    const modeBDims = {
      rarity: { label: 'Rarity', fn: (it: { rarity: string }) => it.rarity },
      class: { label: 'Class', fn: (it: { class?: string }) => it.class ?? '' },
      level: { label: 'Level', fn: (it: { level?: string }) => it.level ?? '' },
    }
    const modeBItems = [
      { rarity: 'common', class: 'warrior', level: '1' },
      { rarity: 'rare', class: 'mage', level: '5' },
    ]
    // Mode B starts with fresh empty filters for its own dims
    const modeBFilters = { rarity: new Set<string>(), class: new Set<string>(), level: new Set<string>() }

    // Act: apply Mode B filters (stale stage key is NOT in modeBFilters)
    const result = applyDimFilters(modeBItems, modeBDims, modeBFilters)
    // Assert: full item set returned — no bleed from Mode A filters
    expect(result).toHaveLength(2)
  })

  it('skips a filter key not present in dims (stale key short-circuit)', () => {
    // Arrange
    const applyDimFilters = getGlobal<Function>('applyDimFilters')
    // filters has a "stage" key but dims has no "stage"
    const spareDims = { rarity: { label: 'Rarity', fn: (it: { rarity: string }) => it.rarity } }
    const filters = { rarity: new Set<string>(), stage: new Set(['baby']) }
    // Act — the "stage" key in filters references dims.stage which is undefined → fn is undefined → skip
    const result = applyDimFilters(items, spareDims, filters)
    // Assert: all items pass since only the rarity filter (empty) is processed
    expect(result).toHaveLength(4)
  })
})

// ---------------------------------------------------------------------------
// buildDimFilters
// ---------------------------------------------------------------------------

describe('buildDimFilters', () => {
  let bar: HTMLElement

  beforeEach(() => {
    bar = document.createElement('div')
    bar.id = 'testBar'
    document.body.appendChild(bar)
  })

  afterEach(() => {
    bar.remove()
  })

  it('dual-API with string items — creates check-btns for values with count ≥ 2', () => {
    // Arrange
    const buildDimFilters = getGlobal<Function>('buildDimFilters')
    const files = ['a-batch1.png', 'b-batch1.png', 'c-batch2.png']
    const dims = { batch: { label: 'Batch', fn: (f: string) => f.split('-')[1].replace('.png', '') } }
    const filters: Record<string, Set<string>> = {}
    const renderFn = vi.fn()
    // Act
    buildDimFilters(files, dims, filters, 'testBar', renderFn)
    // Assert: batch1 appears twice, batch2 once → only batch1 and batch2 together form ≥2 distinct values
    expect('batch' in filters).toBe(true)
    expect(bar.querySelectorAll('.check-btn').length).toBeGreaterThanOrEqual(2)
  })

  it('dual-API with object items — creates check-btns using dim.fn on objects', () => {
    // Arrange
    const buildDimFilters = getGlobal<Function>('buildDimFilters')
    const items = [
      { rarity: 'common' },
      { rarity: 'rare' },
      { rarity: 'common' },
    ]
    const dims = { rarity: { label: 'Rarity', fn: (it: { rarity: string }) => it.rarity } }
    const filters: Record<string, Set<string>> = {}
    const renderFn = vi.fn()
    // Act
    buildDimFilters(items, dims, filters, 'testBar', renderFn)
    // Assert
    expect('rarity' in filters).toBe(true)
    const btns = bar.querySelectorAll('.check-btn')
    expect(btns.length).toBe(2) // common, rare
  })

  it('skips a dimension with fewer than 2 distinct values', () => {
    // Arrange
    const buildDimFilters = getGlobal<Function>('buildDimFilters')
    const items = [{ rarity: 'common' }, { rarity: 'common' }]
    const dims = { rarity: { label: 'Rarity', fn: (it: { rarity: string }) => it.rarity } }
    const filters: Record<string, Set<string>> = {}
    const renderFn = vi.fn()
    // Act
    buildDimFilters(items, dims, filters, 'testBar', renderFn)
    // Assert: only 1 distinct value → no control rendered, key not populated in filters
    expect('rarity' in filters).toBe(false)
    expect(bar.querySelectorAll('.check-btn').length).toBe(0)
  })

  it('clicking a check-btn toggles .on class and calls renderFn', () => {
    // Arrange
    const buildDimFilters = getGlobal<Function>('buildDimFilters')
    const items = [{ rarity: 'common' }, { rarity: 'rare' }, { rarity: 'common' }]
    const dims = { rarity: { label: 'Rarity', fn: (it: { rarity: string }) => it.rarity } }
    const filters: Record<string, Set<string>> = {}
    const renderFn = vi.fn()
    buildDimFilters(items, dims, filters, 'testBar', renderFn)
    const btn = bar.querySelector('.check-btn') as HTMLButtonElement
    // Act
    btn.click()
    // Assert
    expect(btn.classList.contains('on')).toBe(true)
    expect(renderFn).toHaveBeenCalledOnce()
    // Act: toggle off
    btn.click()
    expect(btn.classList.contains('on')).toBe(false)
    expect(renderFn).toHaveBeenCalledTimes(2)
  })

  it('respects dim.order for custom sort', () => {
    // Arrange
    const buildDimFilters = getGlobal<Function>('buildDimFilters')
    const items = [
      { stage: 'adult' },
      { stage: 'baby' },
      { stage: 'adult' },
    ]
    const dims = { stage: { label: 'Stage', fn: (it: { stage: string }) => it.stage, order: ['baby', 'adult'] } }
    const filters: Record<string, Set<string>> = {}
    const renderFn = vi.fn()
    buildDimFilters(items, dims, filters, 'testBar', renderFn)
    const btns = bar.querySelectorAll('.check-btn')
    // Assert: baby first (matches order)
    expect((btns[0] as HTMLButtonElement).dataset.b).toBe('baby')
    expect((btns[1] as HTMLButtonElement).dataset.b).toBe('adult')
  })

  it('escapes XSS in dim label (regression: dim label escaping)', () => {
    // Arrange
    const buildDimFilters = getGlobal<Function>('buildDimFilters')
    const items = [{ x: 'a' }, { x: 'b' }]
    const dims = { x: { label: '<script>alert(1)</script>', fn: (it: { x: string }) => it.x } }
    const filters: Record<string, Set<string>> = {}
    const renderFn = vi.fn()
    // Act
    buildDimFilters(items, dims, filters, 'testBar', renderFn)
    // Assert: the raw <script> tag must NOT be present in bar innerHTML
    expect(bar.innerHTML).not.toContain('<script>')
    expect(bar.innerHTML).toContain('&lt;script&gt;')
  })
})

// ---------------------------------------------------------------------------
// wireSegs
// ---------------------------------------------------------------------------

describe('wireSegs', () => {
  let container: HTMLElement

  beforeEach(() => {
    container = document.createElement('div')
    container.id = 'testSegs'
    container.innerHTML = `
      <button class="seg on" data-v="none">None</button>
      <button class="seg" data-v="batch">Batch</button>
      <button class="seg" data-v="rarity">Rarity</button>
    `
    document.body.appendChild(container)
  })

  afterEach(() => {
    container.remove()
  })

  it('removes .on from all sibling segs and adds .on to clicked seg', () => {
    // Arrange
    const wireSegs = getGlobal<Function>('wireSegs')
    const handler = vi.fn()
    wireSegs('testSegs', handler)
    const btns = container.querySelectorAll('.seg')
    // Act: click "batch" (index 1)
    ;(btns[1] as HTMLButtonElement).click()
    // Assert
    expect(btns[0].classList.contains('on')).toBe(false)
    expect(btns[1].classList.contains('on')).toBe(true)
    expect(btns[2].classList.contains('on')).toBe(false)
  })

  it('calls handler with (value, button)', () => {
    // Arrange
    const wireSegs = getGlobal<Function>('wireSegs')
    const handler = vi.fn()
    wireSegs('testSegs', handler)
    const btn = container.querySelectorAll('.seg')[2] as HTMLButtonElement
    // Act
    btn.click()
    // Assert
    expect(handler).toHaveBeenCalledOnce()
    expect(handler).toHaveBeenCalledWith('rarity', btn)
  })
})

// ---------------------------------------------------------------------------
// buildPivotSegsFromDims
// ---------------------------------------------------------------------------

describe('buildPivotSegsFromDims', () => {
  let colBar: HTMLElement
  let rowBar: HTMLElement

  beforeEach(() => {
    colBar = document.createElement('div')
    colBar.id = 'pivotColBar'
    rowBar = document.createElement('div')
    rowBar.id = 'pivotRowBar'
    document.body.appendChild(colBar)
    document.body.appendChild(rowBar)
  })

  afterEach(() => {
    colBar.remove()
    rowBar.remove()
  })

  const dims = {
    batch: { label: 'Batch', fn: (it: unknown) => it },
    rarity: { label: 'Rarity', fn: (it: unknown) => it },
  }

  it('renders None + one button per dim in both col and row bars', () => {
    // Arrange
    const buildPivotSegsFromDims = getGlobal<Function>('buildPivotSegsFromDims')
    const onChange = vi.fn()
    // Act
    buildPivotSegsFromDims(dims, 'pivotColBar', 'pivotRowBar', onChange)
    // Assert: 1 None + 2 dims = 3 buttons each
    expect(colBar.querySelectorAll('.seg').length).toBe(3)
    expect(rowBar.querySelectorAll('.seg').length).toBe(3)
  })

  it('defaults to None active when no initial arg provided', () => {
    // Arrange
    const buildPivotSegsFromDims = getGlobal<Function>('buildPivotSegsFromDims')
    const onChange = vi.fn()
    // Act
    buildPivotSegsFromDims(dims, 'pivotColBar', 'pivotRowBar', onChange)
    // Assert: None button has .on in both bars
    const colNone = colBar.querySelector('.seg[data-v="none"]') as HTMLButtonElement
    const rowNone = rowBar.querySelector('.seg[data-v="none"]') as HTMLButtonElement
    expect(colNone.classList.contains('on')).toBe(true)
    expect(rowNone.classList.contains('on')).toBe(true)
  })

  it('restores initial active state from initial arg (pivot seg initial state regression)', () => {
    // Arrange
    const buildPivotSegsFromDims = getGlobal<Function>('buildPivotSegsFromDims')
    const onChange = vi.fn()
    // Act: initial = { col: 'none', row: 'batch' }
    buildPivotSegsFromDims(dims, 'pivotColBar', 'pivotRowBar', onChange, { col: 'none', row: 'batch' })
    // Assert
    const colNone = colBar.querySelector('.seg[data-v="none"]') as HTMLButtonElement
    const rowBatch = rowBar.querySelector('.seg[data-v="batch"]') as HTMLButtonElement
    const rowNone = rowBar.querySelector('.seg[data-v="none"]') as HTMLButtonElement
    expect(colNone.classList.contains('on')).toBe(true)
    expect(rowBatch.classList.contains('on')).toBe(true)
    expect(rowNone.classList.contains('on')).toBe(false)
  })

  it('calls onChange with axis and dimKey when a seg is clicked', () => {
    // Arrange
    const buildPivotSegsFromDims = getGlobal<Function>('buildPivotSegsFromDims')
    const onChange = vi.fn()
    buildPivotSegsFromDims(dims, 'pivotColBar', 'pivotRowBar', onChange)
    const colRarity = colBar.querySelector('.seg[data-v="rarity"]') as HTMLButtonElement
    // Act
    colRarity.click()
    // Assert
    expect(onChange).toHaveBeenCalledWith('col', 'rarity')
  })

  it('handles empty dims gracefully — only None button rendered', () => {
    // Arrange
    const buildPivotSegsFromDims = getGlobal<Function>('buildPivotSegsFromDims')
    const onChange = vi.fn()
    // Act
    buildPivotSegsFromDims({}, 'pivotColBar', 'pivotRowBar', onChange)
    // Assert: only the None button for each bar
    expect(colBar.querySelectorAll('.seg').length).toBe(1)
    expect(rowBar.querySelectorAll('.seg').length).toBe(1)
    expect(colBar.querySelector('.seg[data-v="none"]')).not.toBeNull()
  })

  it('returns early without error when containers are missing', () => {
    // Arrange
    const buildPivotSegsFromDims = getGlobal<Function>('buildPivotSegsFromDims')
    const onChange = vi.fn()
    // Act + Assert: no throw
    expect(() =>
      buildPivotSegsFromDims(dims, 'nonexistent-col', 'nonexistent-row', onChange),
    ).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// initDownloads
// ---------------------------------------------------------------------------

describe('initDownloads', () => {
  let wrap: HTMLElement
  let toggle: HTMLButtonElement
  let menu: HTMLElement

  const buildConfig = (entries = []) => ({
    dropdownId: 'dlWrap',
    toggleId: 'dlToggle',
    menuId: 'dlMenu',
    entries,
  })

  beforeEach(() => {
    wrap = document.createElement('div')
    wrap.id = 'dlWrap'
    toggle = document.createElement('button')
    toggle.id = 'dlToggle'
    menu = document.createElement('div')
    menu.id = 'dlMenu'
    wrap.appendChild(toggle)
    wrap.appendChild(menu)
    document.body.appendChild(wrap)
  })

  afterEach(() => {
    wrap.remove()
    vi.restoreAllMocks()
  })

  it('clicking toggle adds .open to menu', () => {
    // Arrange
    const initDownloads = getGlobal<Function>('initDownloads')
    initDownloads(buildConfig())
    // Act
    toggle.click()
    // Assert
    expect(menu.classList.contains('open')).toBe(true)
  })

  it('clicking toggle again removes .open from menu', () => {
    // Arrange
    const initDownloads = getGlobal<Function>('initDownloads')
    initDownloads(buildConfig())
    toggle.click()
    // Act
    toggle.click()
    // Assert
    expect(menu.classList.contains('open')).toBe(false)
  })

  it('sentinel guard prevents duplicate outside-click listener (listener leak regression)', () => {
    // Arrange
    const initDownloads = getGlobal<Function>('initDownloads')
    const spy = vi.spyOn(document, 'addEventListener')
    // Act: call twice
    initDownloads(buildConfig())
    initDownloads(buildConfig())
    // Assert: document.addEventListener('click', ...) called only once despite two inits
    const clickListenerCalls = spy.mock.calls.filter((call) => call[0] === 'click')
    expect(clickListenerCalls.length).toBe(1)
  })

  it('clicking outside the dropdown removes .open', () => {
    // Arrange
    const initDownloads = getGlobal<Function>('initDownloads')
    initDownloads(buildConfig())
    toggle.click() // open first
    // Act: click outside
    document.body.click()
    // Assert
    expect(menu.classList.contains('open')).toBe(false)
  })

  it('sets data-loading=true during handler execution', async () => {
    // Arrange
    const initDownloads = getGlobal<Function>('initDownloads')
    let resolveHandler!: () => void
    const handlerPromise = new Promise<void>((res) => { resolveHandler = res })
    const entries = [{ id: 'dl-csv', label: 'CSV', handler: () => handlerPromise }]
    initDownloads({ ...buildConfig(), entries })
    const btn = menu.querySelector('.dl-item') as HTMLButtonElement
    // Act: start click (don't await)
    const clickResult = btn.click()
    // Assert: data-loading set while in flight
    // Give microtask queue time to start
    await new Promise<void>((r) => setTimeout(r, 0))
    expect(btn.getAttribute('data-loading')).toBe('true')
    // Resolve and check cleanup
    resolveHandler()
    await new Promise<void>((r) => setTimeout(r, 0))
    expect(btn.getAttribute('data-loading')).toBe(null)
  })

  it('data-loading attribute cleared on reject (error cleanup regression)', async () => {
    // Arrange
    const initDownloads = getGlobal<Function>('initDownloads')
    const handler = vi.fn().mockRejectedValue(new Error('network error'))
    const entries = [{ id: 'dl-err', label: 'Fail', handler }]
    initDownloads({ ...buildConfig(), entries })
    const btn = menu.querySelector('.dl-item') as HTMLButtonElement
    // Act
    btn.click()
    await new Promise<void>((r) => setTimeout(r, 10))
    // Assert
    expect(btn.getAttribute('data-loading')).toBe(null)
  })

  it('does nothing when required DOM elements are absent', () => {
    // Arrange
    const initDownloads = getGlobal<Function>('initDownloads')
    // Act + Assert: no throw
    expect(() =>
      initDownloads({ dropdownId: 'x', toggleId: 'y', menuId: 'z', entries: [] }),
    ).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// showToast
// ---------------------------------------------------------------------------

describe('showToast', () => {
  afterEach(() => {
    // Clean up toast stack between tests
    document.getElementById('toast-stack')?.remove()
    vi.useRealTimers()
  })

  it('creates toast-stack on first call', () => {
    // Arrange
    const showToast = getGlobal<Function>('showToast')
    // Act
    showToast('hello')
    // Assert
    expect(document.getElementById('toast-stack')).not.toBeNull()
  })

  it('reuses existing toast-stack on subsequent calls', () => {
    // Arrange
    const showToast = getGlobal<Function>('showToast')
    showToast('first')
    // Act
    showToast('second')
    // Assert: only one toast-stack
    expect(document.querySelectorAll('#toast-stack').length).toBe(1)
  })

  it('toast-stack has aria-live=polite (a11y regression)', () => {
    // Arrange
    const showToast = getGlobal<Function>('showToast')
    // Act
    showToast('a11y test')
    // Assert
    const stack = document.getElementById('toast-stack')!
    expect(stack.getAttribute('aria-live')).toBe('polite')
  })

  it('info toast has class toast-info and no role=alert', () => {
    // Arrange
    const showToast = getGlobal<Function>('showToast')
    // Act
    showToast('info message', 'info')
    // Assert
    const toast = document.querySelector('.toast') as HTMLElement
    expect(toast.classList.contains('toast-info')).toBe(true)
    expect(toast.getAttribute('role')).toBeNull()
  })

  it('error toast has class toast-error and role=alert (a11y regression)', () => {
    // Arrange
    const showToast = getGlobal<Function>('showToast')
    // Act
    showToast('error message', 'error')
    // Assert
    const toast = document.querySelector('.toast') as HTMLElement
    expect(toast.classList.contains('toast-error')).toBe(true)
    expect(toast.getAttribute('role')).toBe('alert')
  })

  it('auto-dismisses toast after duration via setTimeout', () => {
    // Arrange
    vi.useFakeTimers()
    const showToast = getGlobal<Function>('showToast')
    showToast('auto-dismiss', 'info', 1000)
    const stack = document.getElementById('toast-stack')!
    expect(stack.children.length).toBe(1)
    // Act: advance past duration + leave transition
    vi.advanceTimersByTime(1200)
    // Assert
    expect(stack.children.length).toBe(0)
  })

  it('3 rapid showToast calls stack 3 children (stacking regression)', () => {
    // Arrange
    const showToast = getGlobal<Function>('showToast')
    // Act
    showToast('msg1')
    showToast('msg2')
    showToast('msg3')
    // Assert
    const stack = document.getElementById('toast-stack')!
    expect(stack.children.length).toBe(3)
  })
})

// ---------------------------------------------------------------------------
// discoverFiles + discoverBatch (img-manifest.json + /api/list/ fallback chain)
// ---------------------------------------------------------------------------

describe('discoverFiles', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns filenames from img-manifest.json filtered by ext, sorted', async () => {
    // Arrange
    const discoverFiles = getGlobal<Function>('discoverFiles')
    const manifest = [
      { name: 'zebra.png' },
      { name: 'alpha.png' },
      { name: 'readme.txt' },
    ]
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => manifest,
    }) as typeof fetch
    // Act
    const result = await discoverFiles('concepts/', '.png')
    // Assert
    expect(result).toEqual(['alpha.png', 'zebra.png'])
  })

  it('falls back to /api/list/ when img-manifest.json fetch fails', async () => {
    // Arrange
    const discoverFiles = getGlobal<Function>('discoverFiles')
    const apiListing = [{ name: 'img1.png' }, { name: 'doc.pdf' }, { name: 'img2.png' }]
    globalThis.fetch = vi.fn()
      .mockRejectedValueOnce(new Error('404')) // img-manifest.json fails
      .mockResolvedValueOnce({ ok: true, json: async () => apiListing }) as typeof fetch
    // Act
    const result = await discoverFiles('concepts/', '.png')
    // Assert
    expect(result).toEqual(['img1.png', 'img2.png'])
  })

  it('falls back to /api/list/ when img-manifest.json returns ok=false', async () => {
    // Arrange
    const discoverFiles = getGlobal<Function>('discoverFiles')
    const apiListing = [{ name: 'img1.png' }]
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: false }) // img-manifest.json not-ok
      .mockResolvedValueOnce({ ok: true, json: async () => apiListing }) as typeof fetch
    // Act
    const result = await discoverFiles('concepts/', '.png')
    // Assert
    expect(result).toEqual(['img1.png'])
  })

  it('returns empty array when both manifest and /api/list/ fail', async () => {
    // Arrange
    const discoverFiles = getGlobal<Function>('discoverFiles')
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network error')) as typeof fetch
    // Act
    const result = await discoverFiles('concepts/', '.png')
    // Assert
    expect(result).toEqual([])
  })
})

describe('discoverBatch', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('builds items from img-manifest.json with default itemBuilder', async () => {
    // Arrange
    const discoverBatch = getGlobal<Function>('discoverBatch')
    const manifest = [{ name: 'hero-v1.png' }, { name: 'hero-v2.png' }]
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => manifest,
    }) as typeof fetch
    const cfg = { id: 'b1', dir: 'batch1/', ext: '.png' }
    // Act
    const result = await discoverBatch(cfg)
    // Assert
    expect(result).toHaveLength(2)
    expect(result[0].stem).toBe('hero-v1')
    expect(result[0].batch).toBe('b1')
    expect(result[0].file).toBe('hero-v1.png')
  })

  it('falls back to /api/list/ when img-manifest.json is unavailable', async () => {
    // Arrange
    const discoverBatch = getGlobal<Function>('discoverBatch')
    const apiListing = [{ name: 'img-a.png' }, { name: 'img-b.png' }]
    globalThis.fetch = vi.fn()
      .mockRejectedValueOnce(new Error('fail')) // img-manifest.json
      .mockResolvedValueOnce({ ok: true, json: async () => apiListing }) as typeof fetch
    const cfg = { id: 'b2', dir: 'batch2/', ext: '.png' }
    // Act
    const result = await discoverBatch(cfg)
    // Assert
    expect(result).toHaveLength(2)
    expect(result.map((i: { stem: string }) => i.stem)).toEqual(['img-a', 'img-b'])
  })

  it('falls back to catalogue keys when both fetch paths fail', async () => {
    // Arrange
    const discoverBatch = getGlobal<Function>('discoverBatch')
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('offline')) as typeof fetch
    const cfg = {
      id: 'b3',
      dir: 'batch3/',
      ext: '.png',
      catalogue: {
        'portrait-a': { label: 'Portrait A', tags: ['hero'] },
        'portrait-b': { label: 'Portrait B', tags: [] },
      },
    }
    // Act
    const result = await discoverBatch(cfg)
    // Assert
    expect(result).toHaveLength(2)
    expect(result.map((i: { label: string }) => i.label).sort()).toEqual(['Portrait A', 'Portrait B'])
  })

  it('returns empty array when all discovery paths fail and no catalogue', async () => {
    // Arrange
    const discoverBatch = getGlobal<Function>('discoverBatch')
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('offline')) as typeof fetch
    // Act
    const result = await discoverBatch({ id: 'b4', dir: 'batch4/' })
    // Assert
    expect(result).toEqual([])
  })

  it('accepts a custom itemBuilder', async () => {
    // Arrange
    const discoverBatch = getGlobal<Function>('discoverBatch')
    const manifest = [{ name: 'x.png' }]
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => manifest,
    }) as typeof fetch
    const itemBuilder = vi.fn((stem: string, cfg: unknown) => ({ customStem: stem, cfg }))
    // Act
    const result = await discoverBatch({ id: 'b5', dir: 'batch5/', ext: '.png' }, itemBuilder)
    // Assert
    expect(itemBuilder).toHaveBeenCalledWith('x', expect.objectContaining({ id: 'b5' }))
    expect(result[0].customStem).toBe('x')
  })
})
