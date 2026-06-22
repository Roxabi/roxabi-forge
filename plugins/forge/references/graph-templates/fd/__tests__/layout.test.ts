/**
 * Layout CSS invariants for fd-engine — catches cascade bugs that break
 * declarative % positioning (e.g. .fd-card-premium overriding .fd-node).
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ENGINE_CSS = join(import.meta.dirname, '../../fd-engine.css')

function ruleBlock(css: string, selector: string): string | null {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const re = new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, 'm')
  const m = css.match(re)
  return m ? m[1] : null
}

function prop(block: string, name: string): string | null {
  const m = block.match(new RegExp(`${name}\\s*:\\s*([^;]+)`))
  return m ? m[1].trim() : null
}

describe('fd-engine.css layout invariants', () => {
  const css = readFileSync(ENGINE_CSS, 'utf8')

  it('.fd-node uses absolute positioning', () => {
    const block = ruleBlock(css, '.fd-node')
    expect(block).not.toBeNull()
    expect(prop(block!, 'position')).toBe('absolute')
  })

  it('.fd-node.fd-card-premium keeps absolute positioning (premium must not use relative)', () => {
    const block = ruleBlock(css, '.fd-node.fd-card-premium')
    expect(block).not.toBeNull()
    expect(prop(block!, 'position')).toBe('absolute')
  })

  it('.fd-card-premium alone does not set position: relative', () => {
    const block = ruleBlock(css, '.fd-card-premium')
    expect(block).not.toBeNull()
    const position = prop(block!, 'position')
    expect(position === null || position === 'absolute').toBe(true)
  })

  it('.fd-canvas is a positioned containing block', () => {
    const block = ruleBlock(css, '.fd-canvas')
    expect(block).not.toBeNull()
    expect(prop(block!, 'position')).toBe('relative')
  })

  it('.fd-zone uses absolute positioning', () => {
    const block = ruleBlock(css, '.fd-zone')
    expect(block).not.toBeNull()
    expect(prop(block!, 'position')).toBe('absolute')
  })
})