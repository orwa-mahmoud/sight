import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// The dev server proxies the same paths nginx reverse-proxies in production
// (`/api`, `/webhooks`, `/metrics`), so the app can use same-origin relative
// URLs everywhere — keeping the auth cookie same-origin in dev too.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@app': fileURLToPath(new URL('./src/app', import.meta.url)),
      '@auth': fileURLToPath(new URL('./src/auth', import.meta.url)),
      '@core': fileURLToPath(new URL('./src/core', import.meta.url)),
      '@features': fileURLToPath(new URL('./src/features', import.meta.url)),
      '@shared': fileURLToPath(new URL('./src/shared', import.meta.url)),
      '@test': fileURLToPath(new URL('./src/test', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/webhooks': { target: 'http://localhost:8000', changeOrigin: true },
      '/metrics': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
