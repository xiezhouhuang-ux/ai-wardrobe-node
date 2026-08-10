import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:3000',
      // 静态资源统一收敛到 /uploads 下（photos / items / tryon_results 子目录）
      '/uploads': 'http://localhost:3000',
    },
  },
})
