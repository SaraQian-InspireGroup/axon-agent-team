import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // 与 scripts/dev-ports.sh MOCKUP_FRONTEND_PORT 一致；勿与 platform 前端 5173 冲突
    port: 5174,
    strictPort: true,
    proxy: {
      // Nova Chat → platform backend（8000），与 mockup API（5001）分离
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
