import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Proxy API calls to FastAPI to avoid CORS issues in development
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            if (err.code === 'ECONNRESET' || err.code === 'EPIPE') {
              // Suppress harmless client disconnect logs for live MJPEG streams
              return;
            }
            console.error('Vite Proxy Error:', err.message);
          });
        },
      },
      '/cameras-api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/cameras-api/, ''),
      },
    },
  },
})
