import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'https://wardrobe.maidane.com',
      // 静态资源统一收敛到 /uploads 下（photos / items / tryon_results 子目录）
      '/uploads': 'https://wardrobe.maidane.com',
    },
  },
})
