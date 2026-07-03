import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // VITE_API_URL overrides the proxy target when set (e.g. pointing at a
  // deployed Render backend during local dev against prod).
  // Default: local backend at http://localhost:8000
  const backendTarget = env.VITE_API_URL || 'http://localhost:8000'

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      // Generate source maps for production debugging (excluded from final
      // bundle by Vercel's build system unless VITE_SOURCEMAPS=true).
      sourcemap: false,
      rollupOptions: {
          output: {
            // Manual chunk splitting keeps the initial bundle small.
            manualChunks(id) {
              if (id.includes('recharts')) return 'charts'
              if (id.includes('@tanstack/react-query')) return 'query'
              if (id.includes('react-router-dom') || (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/'))) return 'vendor'
              if (id.includes('@radix-ui')) return 'ui'
            },
          },
        },
    },
  }
})
