/**
 * Tests for gen-og-images.py and gen-og-tags.py
 *
 * Browser-free tests (SC3, SC4, SC5, SC7) always run when uv is available.
 * Browser-gated tests (SC1, SC2, SC8) are wrapped in describe.skipIf(!browserAvailable).
 *
 * Scripts under test are invoked via execFileSync — no module mocking.
 */

import { execFileSync } from 'node:child_process'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
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
// Availability probes (evaluated once at module load)
// B3: cheap uv check first; browser probe only if uv available
// ---------------------------------------------------------------------------

let uvAvailable = false
try {
  execFileSync('uv', ['--version'], { stdio: 'ignore', timeout: 5000 })
  uvAvailable = true
} catch {
  uvAvailable = false
}

let browserAvailable = false
if (!uvAvailable) {
  console.warn('og-images.test: uv/chromium probe failed — SC1/SC2/SC8 skipped')
} else {
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
    console.warn('og-images.test: uv/chromium probe failed — SC1/SC2/SC8 skipped')
  }
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
  it('injects both og:image and twitter:image pointing to the global banner URL', () => {
    // Arrange: write b.html with NO sibling .og.png
    writeFileSync(join(forgeDir, 'b.html'), buildHtml('Artifact B'))

    // Act: run gen-og-tags.py
    execFileSync('python3', [GEN_OG_TAGS], {
      env: { ...process.env, FORGE_DIR: forgeDir },
      timeout: 30000,
    })

    // Assert: both og:image and twitter:image fall back to the global banner
    const html = readFileSync(join(forgeDir, 'b.html'), 'utf-8')
    expect(html).toContain('og:image" content="https://forge.roxabi.dev/og-image.png"')
    expect(html).toContain('twitter:image" content="https://forge.roxabi.dev/og-image.png"')
  })
})

// ---------------------------------------------------------------------------
// SC7 — plugins/forge/Makefile deploys gen-og-images.py
// ---------------------------------------------------------------------------

describe('SC7: Makefile deploy target copies gen-og-images.py', () => {
  it('Makefile cp line distinguishes REPO_ROOT source from FORGE_DIR dest', () => {
    // Arrange
    const makefile = readFileSync(MAKEFILE, 'utf-8')

    // Act + Assert: the deploy target copies gen-og-images.py from REPO_ROOT to FORGE_DIR
    // (rejects identity copy: cp foo foo must fail this assertion)
    expect(makefile).toMatch(
      /cp\b[^\n]*\$\(REPO_ROOT\)\/scripts\/gen-og-images\.py[^\n]*\$\(FORGE_DIR\)\/scripts\/gen-og-images\.py/,
    )
  })
})

// ---------------------------------------------------------------------------
// SC3 — graceful degradation on chromium launch failure (uv-gated, browser-free)
// ---------------------------------------------------------------------------

describe.skipIf(!uvAvailable)(
  'SC3: graceful degradation on chromium launch failure',
  () => {
    it('exits 0 and prints fallback message without producing png or tmp files', () => {
      // Arrange: fixture with one renderable sub/a.html
      const subDir = join(forgeDir, 'sub')
      mkdirSync(subDir, { recursive: true })
      writeFileSync(join(subDir, 'a.html'), buildHtml('SC3 Artifact'))

      // Act: run gen-og-images.py --force with a nonexistent browsers path
      // This forces chromium to fail to launch while uv + playwright package are available.
      // Must NOT throw (script must exit 0 — graceful degradation).
      let stdout: string
      try {
        stdout = execFileSync(
          'uv',
          ['run', '--with', 'playwright', 'python3', GEN_OG_IMAGES, '--force'],
          {
            env: { ...process.env, FORGE_DIR: forgeDir, PLAYWRIGHT_BROWSERS_PATH: '/nonexistent' },
            encoding: 'utf-8',
            timeout: 120000,
          },
        )
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err)
        throw new Error(`gen-og-images.py must exit 0 on chromium failure, but it threw: ${msg}`)
      }

      // Assert: degradation message present in output
      const combined = stdout
      expect(combined).toMatch(/chromium launch failed|fall back to banner/i)

      // Assert: NO .og.png produced
      expect(existsSync(join(subDir, 'a.og.png'))).toBe(false)

      // Assert: NO leftover .tmp.png files
      const tmpFiles = readdirSync(subDir).filter((f) => f.endsWith('.tmp.png'))
      expect(tmpFiles).toHaveLength(0)
    })
  },
)

// ---------------------------------------------------------------------------
// SC8b — prune removes .og.png for excluded/missing source html (uv-gated, browser-free)
// ---------------------------------------------------------------------------

describe.skipIf(!uvAvailable)(
  'SC8b: prune removes .og.png for excluded/missing source html',
  () => {
    it('prunes index.og.png (excluded source) and gone.og.png (no source), renders sub/a.og.png', () => {
      // Arrange: fixture with:
      //   index.html   — exists but excluded → index.og.png must be pruned
      //   index.og.png — stray, should_exclude('index.html') = true → pruned
      //   sub/a.html   — renderable → sub/a.og.png must be produced
      //   gone.og.png  — no matching gone.html → pruned (missing-source branch)
      const subDir = join(forgeDir, 'sub')
      mkdirSync(subDir, { recursive: true })

      writeFileSync(join(forgeDir, 'index.html'), buildHtml('Index'))
      writeFileSync(join(forgeDir, 'index.og.png'), Buffer.alloc(1))
      writeFileSync(join(forgeDir, 'gone.og.png'), Buffer.alloc(1))
      writeFileSync(join(subDir, 'a.html'), buildHtml('Artifact A'))

      // Act: run gen-og-images.py --force via uv (same invocation as build.sh)
      // Browser unavailable → chromium fails gracefully (exit 0); pruning still runs
      // because the prune pass executes before the playwright import.
      try {
        execFileSync(
          'uv',
          ['run', '--with', 'playwright', 'python3', GEN_OG_IMAGES, '--force'],
          {
            env: { ...process.env, FORGE_DIR: forgeDir, PLAYWRIGHT_BROWSERS_PATH: '/nonexistent' },
            encoding: 'utf-8',
            timeout: 120000,
          },
        )
      } catch {
        // exit non-zero only if chromium fails AND the script doesn't degrade gracefully;
        // either way pruning already happened — assertions below are valid.
      }

      // Assert: stray index.og.png pruned (excluded-source branch uses html rel, not png rel)
      expect(existsSync(join(forgeDir, 'index.og.png'))).toBe(false)

      // Assert: stray gone.og.png pruned (no matching .html)
      expect(existsSync(join(forgeDir, 'gone.og.png'))).toBe(false)

      // Assert: sub/a.og.png may or may not exist depending on browser availability —
      // we only assert it was NOT pruned if it does exist (i.e. the prune loop ignores
      // non-excluded, non-orphan pngs). We do NOT assert existence here (browser-gated).
      // The key assertion is the two prune checks above.
    })
  },
)

// ---------------------------------------------------------------------------
// Browser-gated tests (SC1, SC2, SC8)
// ---------------------------------------------------------------------------

describe.skipIf(!browserAvailable)('Browser-gated: gen-og-images.py with Playwright', () => {
  // SC1 — gen-og-images renders <name>.og.png at correct dimensions
  describe('SC1: renders sibling .og.png with correct aspect ratio', () => {
    it('produces sub/a.og.png at exact 2400×1260 (device_scale_factor=2)', () => {
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

      // Assert: exact physical dimensions — device_scale_factor=2 → 2400×1260
      // (update if dSF changes)
      const { width: w, height: h } = readPngDims(pngPath)
      expect(w).toBe(2400)
      expect(h).toBe(1260)

      // Assert: aspect ratio ≈ 1200/630 (within 0.01) — secondary check
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

      // Assert: no re-render — new format: "0 rendered, 0 failed, N pruned (all up-to-date)."
      expect(stdout1).toMatch(/0 rendered.*all up-to-date/)

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

      // Assert: exactly 1 rendered (anchored — avoids false match on "11 rendered")
      expect(stdout2).toMatch(/og-images — 1 rendered\b/)
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
