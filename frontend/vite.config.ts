import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// The dev server proxies the same paths nginx reverse-proxies in production
// (`/api`, `/webhooks`, `/metrics`), so the app can use same-origin relative
// URLs everywhere — keeping the auth cookie same-origin in dev too.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/webhooks': { target: 'http://localhost:8000', changeOrigin: true },
      '/metrics': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
