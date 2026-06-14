/**
 * Tests for gen-og-images.py and gen-og-tags.py
 *
 * Browser-free tests (SC4, SC5, SC7) always run.
 * Browser-gated tests (SC1, SC2, SC8) are wrapped in describe.skipIf(!browserAvailable).
 *
 * Scripts under test are invoked via execFileSync — no module mocking.
 */

import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

// ---------------------------------------------------------------------------
// Script paths (resolved relative to this test file)
// ---------------------------------------------------------------------------

const SCRIPTS_DIR = fileURLToPath(new URL('..', import.meta.url))
const GEN_OG_IMAGES = join(SCRIPTS_DIR, 'gen-og-images.py')
const GEN_OG_TAGS = join(SCRIPTS_DIR, 'gen-og-tags.py')

// Makefile path for SC7
const MAKEFILE = fileURLToPath(new URL('../../plugins/forge/Makefile', import.meta.url))

// ---------------------------------------------------------------------------
// Browser availability probe (evaluated once at module load)
// ---------------------------------------------------------------------------

let browserAvailable = false
try {
  execFileSync(
    'uv',
    [
      'run',
      '--with',
      'playwright',
      'python3',
      '-c',
      'from playwright.sync_api import sync_playwright as s; p=s().start(); b=p.chromium.launch(); b.close(); p.stop()',
    ],
    { stdio: 'ignore', timeout: 120000 },
  )
  browserAvailable = true
} catch {
  browserAvailable = false
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a minimal renderable HTML string with a viewport meta, title, and a
 * visible body div. gen-og-tags.py requires </head>, <title>, and viewport.
 */
function buildHtml(title: string, bodyText = 'Hello'): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
</head>
<body>
  <div style="width:1200px;height:630px;background:#1a1a2e;display:flex;align-items:center;justify-content:center;color:#fff;font-size:48px;">${bodyText}</div>
</body>
</html>`
}

/**
 * Read PNG dimensions from IHDR bytes.
 * Width: big-endian UInt32 at offset 16
 * Height: big-endian UInt32 at offset 20
 */
function readPngDims(pngPath: string): { width: number; height: number } {
  const b = readFileSync(pngPath)
  const width = b.readUInt32BE(16)
  const height = b.readUInt32BE(20)
  return { width, height }
}

// ---------------------------------------------------------------------------
// Per-test temp FORGE_DIR setup
// ---------------------------------------------------------------------------

let forgeDir: string

beforeEach(() => {
  forgeDir = mkdtempSync(join(tmpdir(), 'og-'))
})

afterEach(() => {
  rmSync(forgeDir, { recursive: true, force: true })
})

// ---------------------------------------------------------------------------
// SC4 — gen-og-tags injects per-artifact og:image when sibling .og.png exists
// ---------------------------------------------------------------------------

describe('SC4: gen-og-tags — per-artifact og:image when sibling .og.png exists', () => {
  it('injects og:image and twitter:image pointing to the artifact png URL', () => {
    // Arrange: write sub/a.html + dummy sub/a.og.png
    const subDir = join(forgeDir, 'sub')
    mkdirSync(subDir, { recursive: true })
    writeFileSync(join(subDir, 'a.html'), buildHtml('Artifact A'))
    // Dummy PNG (1-byte placeholder — gen-og-tags only checks existence, not validity)
    writeFileSync(join(subDir, 'a.og.png'), Buffer.alloc(1))

    // Act: run gen-og-tags.py
    execFileSync('python3', [GEN_OG_TAGS], {
      env: { ...process.env, FORGE_DIR: forgeDir },
      timeout: 30000,
    })

    // Assert: og:image and twitter:image point to the per-artifact URL
    const html = readFileSync(join(subDir, 'a.html'), 'utf-8')
    expect(html).toContain('og:image" content="https://forge.roxabi.dev/sub/a.og.png"')
    expect(html).toContain('twitter:image" content="https://forge.roxabi.dev/sub/a.og.png"')
  })
})

// ---------------------------------------------------------------------------
// SC5 — gen-og-tags falls back to global og-image.png when no sibling png
// ---------------------------------------------------------------------------

describe('SC5: gen-og-tags — fallback to global og-image.png when no sibling .og.png', () => {
  it('injects twitter:image pointing to the global banner URL', () => {
    // Arrange: write b.html with NO sibling .og.png
    writeFileSync(join(forgeDir, 'b.html'), buildHtml('Artifact B'))

    // Act: run gen-og-tags.py
    execFileSync('python3', [GEN_OG_TAGS], {
      env: { ...process.env, FORGE_DIR: forgeDir },
      timeout: 30000,
    })

    // Assert: twitter:image falls back to the global banner
    const html = readFileSync(join(forgeDir, 'b.html'), 'utf-8')
    expect(html).toContain('twitter:image" content="https://forge.roxabi.dev/og-image.png"')
  })
})

// ---------------------------------------------------------------------------
// SC7 — plugins/forge/Makefile deploys gen-og-images.py
// ---------------------------------------------------------------------------

describe('SC7: Makefile deploy target copies gen-og-images.py', () => {
  it('Makefile contains a cp line that deploys scripts/gen-og-images.py', () => {
    // Arrange
    const makefile = readFileSync(MAKEFILE, 'utf-8')

    // Act + Assert: the deploy target copies gen-og-images.py from scripts/ to scripts/
    expect(makefile).toMatch(/cp\b.*scripts\/gen-og-images\.py.*scripts\/gen-og-images\.py/)
  })
})

// ---------------------------------------------------------------------------
// Browser-gated tests (SC1, SC2, SC8)
// ---------------------------------------------------------------------------

describe.skipIf(!browserAvailable)('Browser-gated: gen-og-images.py with Playwright', () => {
  // SC1 — gen-og-images renders <name>.og.png at correct dimensions
  describe('SC1: renders sibling .og.png with correct aspect ratio', () => {
    it('produces sub/a.og.png at 1200×630 or 2×DPR (2400×1260)', () => {
      // Arrange: write a renderable sub/a.html
      const subDir = join(forgeDir, 'sub')
      mkdirSync(subDir, { recursive: true })
      writeFileSync(join(subDir, 'a.html'), buildHtml('SC1 Artifact'))

      // Act: run gen-og-images.py --force
      execFileSync(
        'uv',
        ['run', '--with', 'playwright', 'python3', GEN_OG_IMAGES, '--force'],
        {
          env: { ...process.env, FORGE_DIR: forgeDir },
          timeout: 120000,
        },
      )

      // Assert: sub/a.og.png exists
      const pngPath = join(subDir, 'a.og.png')
      expect(existsSync(pngPath)).toBe(true)

      // Assert: dimensions are correct
      const { width: w, height: h } = readPngDims(pngPath)
      const isLogicalDims = w === 1200 && h === 630
      const isPhysicalDims = w === 2400 && h === 1260
      expect(isLogicalDims || isPhysicalDims).toBe(true)

      // Assert: aspect ratio ≈ 1200/630 (within 0.01)
      const expectedRatio = 1200 / 630
      const actualRatio = w / h
      expect(Math.abs(actualRatio - expectedRatio)).toBeLessThan(0.01)
    })
  })

  // SC2 — mtime-based idempotency: up-to-date detection and --force re-render
  describe('SC2: mtime idempotency — up-to-date detection and --force re-render', () => {
    it('reports 0 rendered (all up-to-date) when png is fresh, 1 rendered with --force', () => {
      // Arrange: write and render sub/a.html
      const subDir = join(forgeDir, 'sub')
      mkdirSync(subDir, { recursive: true })
      writeFileSync(join(subDir, 'a.html'), buildHtml('SC2 Artifact'))

      // First render to produce the png
      execFileSync(
        'uv',
        ['run', '--with', 'playwright', 'python3', GEN_OG_IMAGES, '--force'],
        {
          env: { ...process.env, FORGE_DIR: forgeDir },
          timeout: 120000,
        },
      )

      // Act: run without --force → up-to-date
      const stdout1 = execFileSync(
        'uv',
        ['run', '--with', 'playwright', 'python3', GEN_OG_IMAGES],
        {
          env: { ...process.env, FORGE_DIR: forgeDir },
          timeout: 60000,
          encoding: 'utf-8',
        },
      )

      // Assert: no re-render
      expect(stdout1).toContain('0 rendered (all up-to-date)')

      // Act: run with --force → 1 re-rendered
      const stdout2 = execFileSync(
        'uv',
        ['run', '--with', 'playwright', 'python3', GEN_OG_IMAGES, '--force'],
        {
          env: { ...process.env, FORGE_DIR: forgeDir },
          timeout: 120000,
          encoding: 'utf-8',
        },
      )

      // Assert: 1 rendered
      expect(stdout2).toContain('1 rendered')
    })
  })

  // SC8 — exclusion logic: index.html and tabs/ paths are NOT rendered
  describe('SC8: exclusion logic — index.html and tabs/ paths are skipped', () => {
    it('skips index.html and tabs/x.html but renders sub/keep.html', () => {
      // Arrange: three HTML files with different exclusion scenarios
      const tabsDir = join(forgeDir, 'tabs')
      const subDir = join(forgeDir, 'sub')
      mkdirSync(tabsDir, { recursive: true })
      mkdirSync(subDir, { recursive: true })

      writeFileSync(join(forgeDir, 'index.html'), buildHtml('Index'))
      writeFileSync(join(tabsDir, 'x.html'), buildHtml('Tabs X'))
      writeFileSync(join(subDir, 'keep.html'), buildHtml('Keep This'))

      // Act: run gen-og-images.py --force
      execFileSync(
        'uv',
        ['run', '--with', 'playwright', 'python3', GEN_OG_IMAGES, '--force'],
        {
          env: { ...process.env, FORGE_DIR: forgeDir },
          timeout: 120000,
        },
      )

      // Assert: excluded files have NO .og.png
      expect(existsSync(join(forgeDir, 'index.og.png'))).toBe(false)
      expect(existsSync(join(tabsDir, 'x.og.png'))).toBe(false)

      // Assert: eligible file was rendered
      expect(existsSync(join(subDir, 'keep.og.png'))).toBe(true)
    })
  })
})
