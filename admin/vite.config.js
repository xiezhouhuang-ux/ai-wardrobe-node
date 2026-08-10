import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 根据 .env 中的 VITE_API_BASE 自动切换：
// - 未配置 VITE_API_BASE（dev 默认）：前端请求 /wardrobe-admin/admin/* 落在同源，
//   由 vite 将 /wardrobe-admin 代理到后端 http://localhost:3000，并去掉 /wardrobe-admin 前缀
//   （实际转发到 http://localhost:3000/admin/*）
// - 已配置 VITE_API_BASE（生产 or preview）：VITE_API_BASE 指向线上域名（可含或不含前缀），
//   前端直接以其为 baseURL 拼接，不再走 vite 代理，由线上 nginx 将 /wardrobe-admin 反代到后端
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  const proxy = {}
   // dev：匹配 /wardrobe-admin，转发到后端并把前缀替换为空（去掉 /wardrobe-admin）
    proxy[env.VITE_API_BASE] = {
      target: env.VITE_API_TARGET || 'http://localhost:3000',
      changeOrigin: true,
      rewrite: (p) => p.replace(/^\/wardrobe-admin/, ''),
    }
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 5174,
      proxy,
    },
    preview: {
      port: 5174,
      proxy,
    },
  }
})
