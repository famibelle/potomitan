// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // Si vous utilisez l’alias @ pour src/
      '@': path.resolve(__dirname, './src')
    }
  },
  optimizeDeps: {
    include: ['axios']    // <<< force Vite à transformer axios en ESM
  }
})
