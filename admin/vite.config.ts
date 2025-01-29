import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  return {
    plugins: [react()],
    server: {
        port: parseInt(env.ADMIN_PORT),
        proxy: {
          '/api': {
            target: `http://127.0.0.1:${env.BACKEND_PORT}`,
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api/, ''),
            secure: false,
            ws: true
          }
        },
        host: true,
        strictPort: true,
        hmr: {
          timeout: 30000
        }
    }
  }
}); 