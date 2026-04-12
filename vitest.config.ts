import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    // Default environment is node; individual test files may override with
    // // @vitest-environment happy-dom
  },
})
