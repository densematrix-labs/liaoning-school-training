import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'lcov', 'html'],
      thresholds: {
        statements: 95,
        lines: 95,
      },
      exclude: [
        'node_modules/',
        'src/test/',
        'src/main.tsx',
        'src/i18n/',
        'postcss.config.js',
        'tailwind.config.js',
        '**/*.d.ts',
        'vite.config.ts',
        'vitest.config.ts',
      ],
    },
  },
})
