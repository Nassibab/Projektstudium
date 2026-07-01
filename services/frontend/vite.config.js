import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/moderation': { 
        target: 'http://moderation:8000',
        changeOrigin: true
      },
      '/api': { 
        target: 'http://api:8080', // Point this to your API container's port!
        changeOrigin: true
      }
    }
  }
})