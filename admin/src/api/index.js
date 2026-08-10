import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE || ''

const http = axios.create({
  baseURL: BASE,
  timeout: 5 * 60 * 1000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response && err.response.status
    if (status === 401 || status === 403) {
      localStorage.removeItem('admin_token')
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    }
    const msg = (err.response && err.response.data && err.response.data.detail) || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  }
)

// 接口路径统一带 /wardrobe-admin 前缀（对外暴露的路径）：
// - dev 环境：vite.config.js 将 /wardrobe-admin 代理到后端 http://localhost:3000，并去掉前缀，
//   后端实际收到 /admin/*
// - 生产环境：配置 VITE_API_BASE（如 https://域名）后直接拼接，由线上 nginx 将 /wardrobe-admin 反代到后端
export const adminApi = {
  login: (username, password) =>
    http.post('/admin/login', { username, password }),
  stats: () => http.get('/admin/stats'),
  items: (page = 1, size = 20, keyword = '') =>
    http.get('/admin/items', { params: { page, size, keyword } }),
  deleteItem: (id) => http.delete(`/admin/items/${id}`),
  tryon: (page = 1, size = 20) =>
    http.get('/admin/tryon', { params: { page, size } }),
  deleteTryon: (id) => http.delete(`/admin/tryon/${id}`),
  outfits: (page = 1, size = 20) =>
    http.get('/admin/outfits', { params: { page, size } }),
  deleteOutfit: (date) => http.delete(`/admin/outfits/${date}`),
}

export default http
