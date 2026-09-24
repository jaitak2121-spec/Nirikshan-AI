import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

/**
 * Build config for the page render test only.
 *
 * Bundles test/render.jsx for Node with the API client and the data hook
 * replaced by synchronous stubs, so pages can be rendered in their loaded state
 * without a running backend or a browser. The application source itself is
 * untouched — the substitution happens here, at the module boundary.
 */
const resolve = (p) => fileURLToPath(new URL(p, import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: /^(\.\.\/)+services\/api$/, replacement: resolve('./test/api-stub.js') },
      { find: /^(\.\.\/)+hooks\/useApi$/, replacement: resolve('./test/useApi-stub.js') },
      { find: /^\.\/services\/api$/, replacement: resolve('./test/api-stub.js') },
      { find: /^\.\/hooks\/useApi$/, replacement: resolve('./test/useApi-stub.js') },
    ],
  },
  build: {
    ssr: resolve('./test/render.jsx'),
    outDir: 'test/dist',
    emptyOutDir: true,
    target: 'node18',
    rollupOptions: { output: { format: 'esm', entryFileNames: 'render.mjs' } },
  },
})
