import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,  // Changed to avoid port conflict
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',  // Changed to new backend port
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  }
})

